import json
import os
from urllib.parse import quote

from dotenv import load_dotenv

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import SessionLocal, Base, engine


from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from models import Bookmark, User, UserPreference
from bookmarks import router as bookmarks_router
import feedparser
import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
load_dotenv()

app = FastAPI(
    title="NewsIQ API",
    description="AI-powered cloud-native news platform",
    version="0.2.0",
)
Base.metadata.create_all(bind=engine)
app.include_router(bookmarks_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY must be configured in the environment.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

INTEREST_CATEGORIES = {
    "Technology", "Business", "Science", "World", "Sports", "Other"
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(user_id: int):
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


RSS_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "Sports": (
        "https://news.google.com/rss/search?"
        "q=India+Sports&hl=en-IN&gl=IN&ceid=IN:en"
    ),
}


def build_topic_feed(topic):
    """Build a Google News RSS search URL for a custom topic."""
    query = quote(topic, safe="")
    return (
        "https://news.google.com/rss/search?"
        f"q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    )


def extract_article_image(entry):
    # 1. Try media:content and media:thumbnail
    for key in ("media_content", "media_thumbnail"):
        media_items = entry.get(key, [])
        if isinstance(media_items, dict):
            media_items = [media_items]

        for media in media_items:
            url = media.get("url")
            if url and url.startswith(("https://", "http://")):
                return url

    # 2. Try enclosure
    enclosure = entry.get("enclosures", [])
    for item in enclosure:
        url = item.get("href") or item.get("url")
        media_type = item.get("type", "")
        if url and (
            media_type.startswith("image/")
            or url.lower().split("?")[0].endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            )
        ):
            return url

    # 3. Try an image inside the RSS description
    from bs4 import BeautifulSoup

    html = entry.get("summary", "") or entry.get("description", "")
    soup = BeautifulSoup(html, "html.parser")
    img = soup.find("img")

    if img:
        url = img.get("src")
        if url and url.startswith(("https://", "http://")):
            return url

    return None


def extract_page_image(url):
    if not url:
        return None

    try:
        response = httpx.get(
            url,
            timeout=4.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")
        for selector in [
            {"property": "og:image"},
            {"name": "twitter:image"},
        ]:
            tag = soup.find("meta", attrs=selector)
            if tag and tag.get("content"):
                image_url = tag["content"].strip()
                if image_url.startswith("https://") or image_url.startswith("http://"):
                    return image_url
    except Exception as exc:
        print(f"Article image lookup failed: {exc}")

    return None


@app.get("/")
def root():
    return {
        "name": "NewsIQ",
        "message": "Your News, Simplified",
        "status": "running",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def fetch_feed(category, url):
    try:
        response = httpx.get(
            url,
            timeout=12.0,
            follow_redirects=True,
            headers={"User-Agent": "NewsIQ/0.2"},
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)

        articles = []

        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            summary = entry.get("summary", "")
            published = entry.get("published", "")

            articles.append({
                "id": link,
                "title": title,
                "description": summary,
                "source": parsed.feed.get("title", category),
                "category": category,
                "url": link,
                "published": published,
                "image": (
                    extract_article_image(entry)
                ),
            })

        return articles

    except Exception as exc:
        print(f"RSS feed error ({category}): {exc}")
        return []


@app.get("/api/news")
def get_news(
    category: str = Query(default="All News"),
    q: str = Query(default=""),
    topic: str = Query(default=""),
):
    selected_feeds = dict(RSS_FEEDS)

    if topic.strip() and topic.lower() not in {
        name.lower() for name in RSS_FEEDS
    }:
        selected_feeds[topic] = build_topic_feed(topic)

    # If a particular category is requested, fetch only that topic.
    if category.lower() != "all news":
        matched = next(
            (
                (name, url)
                for name, url in selected_feeds.items()
                if name.lower() == category.lower()
            ),
            None,
        )
        if matched:
            selected_feeds = {matched[0]: matched[1]}
        else:
            selected_feeds = {category: build_topic_feed(category)}

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(
            lambda item: fetch_feed(item[0], item[1]),
            selected_feeds.items(),
        )

        articles = [
            article
            for feed_articles in results
            for article in feed_articles
        ]

    # Remove duplicate links.
    unique_articles = list({
        article["url"]: article for article in articles
    }.values())

    # Filter by article title, description or publisher.
    if q.strip():
        term = q.strip().lower()
        unique_articles = [
            article for article in unique_articles
            if term in article["title"].lower()
            or term in article["description"].lower()
            or term in article["source"].lower()
        ]

    return {
        "total": len(unique_articles),
        "articles": unique_articles,
        "source_type": "RSS",
    }


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    categories: list[str] = ["Technology", "Business"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PreferencesRequest(BaseModel):
    categories: list[str]


def validate_categories(categories: list[str]):
    normalized = []
    seen = set()
    for category in categories:
        topic = category.strip()
        if not topic:
            continue
        if len(topic) > 40:
            raise HTTPException(
                status_code=400,
                detail="Each interest must be 40 characters or fewer.",
            )

        key = topic.casefold()
        standard = next(
            (
                item
                for item in INTEREST_CATEGORIES
                if item.casefold() == key
            ),
            None,
        )
        topic = standard or topic
        if key not in seen:
            normalized.append(topic)
            seen.add(key)

    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Choose at least one news interest.",
        )

    return normalized


@app.post("/api/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    email = str(request.email).strip().lower()

    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    categories = validate_categories(request.categories)
    user = User(
        email=email,
        password_hash=pwd_context.hash(request.password),
    )
    db.add(user)
    db.flush()

    db.add(UserPreference(
        user_id=user.id,
        categories=",".join(categories),
    ))
    db.commit()
    db.refresh(user)

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email},
        "categories": categories,
    }


@app.post("/api/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    email = str(request.email).strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    preference = db.query(UserPreference).filter(
        UserPreference.user_id == user.id
    ).first()
    categories = (
        preference.categories.split(",")
        if preference and preference.categories
        else ["Technology", "Business"]
    )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email},
        "categories": categories,
    }


@app.get("/api/preferences")
def get_preferences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == user.id
    ).first()
    categories = (
        preference.categories.split(",")
        if preference and preference.categories
        else ["Technology", "Business"]
    )
    return {"categories": categories}


@app.put("/api/preferences")
def update_preferences(
    request: PreferencesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categories = validate_categories(request.categories)
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == user.id
    ).first()

    if not preference:
        preference = UserPreference(user_id=user.id, categories=",".join(categories))
        db.add(preference)
    else:
        preference.categories = ",".join(categories)

    db.commit()
    return {"categories": categories}





class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    title: str = ""
    source: str = ""


@app.post("/api/summarize")
def summarize_article(request: SummarizeRequest):
    article_text = " ".join(request.text.split())

    if not article_text:
        raise HTTPException(
            status_code=400,
            detail="Article text cannot be empty."
        )

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Groq API key is not configured on the backend."
        )

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    from groq import Groq, APIError

    client = Groq(api_key=api_key)

    

    article_input = (
        f"Article title: {request.title}\n\n"
        f"Article source: {request.source}\n\n"
        f"Article content:\n{request.text}"
    )

    system_prompt = """
You are NewsIQ, a neutral and context-aware news summarization assistant.

Help an ordinary reader understand the news story from the supplied text.

Requirements:
- Aim for 120-180 words when sufficient information is available.
- Explain what happened, who was involved, where and when it happened.
- Include relevant background, important facts, outcomes, and why the story matters,
  but only when supported by the supplied text.
- Use clear, natural language that an ordinary reader can understand.
- Preserve important names, dates, numbers, and factual details.
- Do not invent facts or present speculation as established truth.
- If the supplied text is brief, write a proportionately shorter summary.
- Provide 3-5 concise key takeaways when the source supports them.
- Return valid JSON with exactly these fields:
  "summary": a string
  "key_takeaways": an array of strings
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": article_input,
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_completion_tokens=700,
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("The model returned an empty response.")

        result = json.loads(content)
        summary = result.get("summary")
        takeaways = result.get("key_takeaways")

        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("The model returned an invalid summary.")

        if not isinstance(takeaways, list):
            raise ValueError("The model returned invalid key takeaways.")

        return {
            "summary": summary.strip(),
            "key_takeaways": [
                item.strip()
                for item in takeaways
                if isinstance(item, str) and item.strip()
            ],
            "method": "groq",
        }

    except APIError as e:
        print(f"Groq API error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Groq API error: {type(e).__name__}",
        )

    except (ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=502,
            detail="Groq returned an invalid summary. Please try again.",
        )


class AskArticleRequest(BaseModel):
    title: str
    source: str = ""
    text: str
    question: str


@app.post("/api/ask-article")
def ask_article(request: AskArticleRequest):
    article_text = " ".join(request.text.split())
    question = request.question.strip()

    if not article_text or not question:
        raise HTTPException(
            status_code=400,
            detail="Article text and question are required.",
        )

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Groq API key is not configured.",
        )

    try:
        from groq import Groq, APIError

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are NewsIQ, a neutral news analysis assistant. "
                        "Answer the user's question using only the supplied "
                        "article context. Be clear and concise, and do not "
                        "invent facts or present speculation as established truth."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Article title: {request.title}\n\n"
                        f"Article source: {request.source}\n\n"
                        f"Article content:\n{article_text}\n\n"
                        f"Question: {question}"
                    ),
                },
            ],
            temperature=0.2,
            max_completion_tokens=500,
        )

        answer = response.choices[0].message.content
        if not answer or not answer.strip():
            raise ValueError("The model returned an empty answer.")

        return {"answer": answer.strip()}

    except APIError as exc:
        print(f"Groq API error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"Groq API error: {type(exc).__name__}",
        )
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Groq returned an invalid answer. Please try again.",
        )


class DailyBriefingRequest(BaseModel):
    articles: list[dict]


@app.post("/api/daily-briefing")
def generate_daily_briefing(request: DailyBriefingRequest):
    articles = request.articles[:10]

    if not articles:
        raise HTTPException(
            status_code=400,
            detail="No articles available for the daily briefing.",
        )

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Groq API key is not configured.",
        )

    news_context = "\n\n".join(
        f"Story {i}:\n"
        f"Title: {item.get('title', 'Untitled')}\n"
        f"Category: {item.get('category', 'General')}\n"
        f"Source: {item.get('source', 'Unknown')}\n"
        f"Description: {item.get('description', '')[:1200]}"
        for i, item in enumerate(articles, start=1)
    )

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            messages=[
                {
                    "role": "system",
                    "content": """
You are NewsIQ's daily news editor.
Use ONLY the supplied article information.
Return valid JSON only, without markdown fences, using this structure:
{
  "headline": "Short briefing title",
  "overview": "A concise overview of the main developments",
  "why_it_matters": "Why these developments matter",
  "top_stories": [
    {
      "title": "Article title",
      "category": "Article category",
      "source": "Publisher",
      "takeaway": "Key takeaway supported by the article"
    }
  ]
}
Include up to 5 supplied stories.
Do not invent facts or unsupported connections.
If the articles provide insufficient information, say so clearly.
""",
                },
                {
                    "role": "user",
                    "content": (
                        "Prepare today's briefing from these stories:\n\n"
                        f"{news_context}"
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=1200,
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as exc:
        print(f"Daily briefing error: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Could not generate the daily briefing. Please try again.",
        )
