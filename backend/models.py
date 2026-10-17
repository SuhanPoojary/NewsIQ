
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    article_url = Column(String(2048), unique=True, nullable=False, index=True)
    title = Column(String(1000), nullable=False)
    source = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
