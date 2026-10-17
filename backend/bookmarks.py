
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Bookmark

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BookmarkRequest(BaseModel):
    article_url: HttpUrl
    title: str = Field(min_length=1, max_length=1000)
    source: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None


@router.get("")
def list_bookmarks(db: Session = Depends(get_db)):
    items = db.query(Bookmark).order_by(Bookmark.created_at.desc()).all()
    return [
        {
            "id": item.id,
            "article_url": item.article_url,
            "title": item.title,
            "source": item.source,
            "category": item.category,
            "description": item.description,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.post("")
def add_bookmark(request: BookmarkRequest, db: Session = Depends(get_db)):
    url = str(request.article_url)
    existing = db.query(Bookmark).filter_by(article_url=url).first()

    if existing:
        return {"message": "Article already bookmarked", "id": existing.id}

    item = Bookmark(
        article_url=url,
        title=request.title,
        source=request.source,
        category=request.category,
        description=request.description,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {"message": "Bookmark saved", "id": item.id}


@router.delete("/{bookmark_id}")
def remove_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    item = db.query(Bookmark).filter_by(id=bookmark_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(item)
    db.commit()

    return {"message": "Bookmark removed"}
