
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Bookmark, User

load_dotenv()

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    if not SECRET_KEY:
        raise HTTPException(status_code=500, detail="Authentication is not configured.")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


class BookmarkRequest(BaseModel):
    article_url: HttpUrl
    title: str = Field(min_length=1, max_length=1000)
    source: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    image: HttpUrl | None = None


def serialize_bookmark(item):
    return {
        "id": item.id,
        "article_url": item.article_url,
        "title": item.title,
        "source": item.source,
        "category": item.category,
        "description": item.description,
        "image": item.image,
        "created_at": item.created_at,
    }


@router.get("")
def list_bookmarks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == user.id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    return [serialize_bookmark(item) for item in items]


@router.post("")
def add_bookmark(
    request: BookmarkRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url = str(request.article_url)

    existing = db.query(Bookmark).filter_by(
        user_id=user.id,
        article_url=url,
    ).first()

    if existing:
        if request.image:
            existing.image = str(request.image)
            db.commit()
        return {"message": "Article already bookmarked", "id": existing.id}

    item = Bookmark(
        user_id=user.id,
        article_url=url,
        title=request.title,
        source=request.source,
        category=request.category,
        description=request.description,
        image=str(request.image) if request.image else None,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {"message": "Bookmark saved", "id": item.id}


@router.delete("/{bookmark_id}")
def remove_bookmark(
    bookmark_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Bookmark).filter_by(
        id=bookmark_id,
        user_id=user.id,
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Bookmark not found",
        )

    db.delete(item)
    db.commit()

    return {"message": "Bookmark removed"}
