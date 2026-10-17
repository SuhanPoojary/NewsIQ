import json
import os

from dotenv import load_dotenv


from pydantic import BaseModel, Field
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from database import Base, engine
from models import Bookmark
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



RSS_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
}


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
                "image": None,
            })

        return articles

    except Exception as exc:
        print(f"RSS feed error ({category}): {exc}")
        return []


@app.get("/api/news")
def get_news(
    category: str = Query(default="All News"),
    q: str = Query(default=""),
):
    selected_feeds = RSS_FEEDS.items()

    if category != "All News":
        selected_feeds = [
            (name, url)
            for name, url in RSS_FEEDS.items()
            if name.lower() == category.lower()
        ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(
            lambda item: fetch_feed(item[0], item[1]),
            selected_feeds,
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
        "Summarize this news article. Return JSON containing "
        "a concise summary and a list of key_takeaways.\n"
        f"Title: {request.title or 'Not provided'}\n"
        f"Source: {request.source or 'Not provided'}\n"
        f"Article text:\n{article_text}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are NewsIQ, a neutral news summarization assistant. "
                        "Use only the supplied article; do not invent facts. "
                        "Return valid JSON with exactly these fields: "
                        '{"summary": "string", "key_takeaways": ["string"]}.'
                    ),
                },
                {"role": "user", "content": article_input},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_completion_tokens=500,
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
            "method": "groq"
        }

    except APIError as e:
        print(f"Groq API error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Groq API error: {type(e).__name__}"
        )

    except (ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=502,
            detail="Groq returned an invalid summary. Please try again."
        )



