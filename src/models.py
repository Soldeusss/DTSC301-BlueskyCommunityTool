from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class FeedRecord(BaseModel):
    feed_id: str
    display_name: Optional[str] = None
    creator_did: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    subscribers_count: Optional[int] = None
    indexed_at: datetime = Field(default_factory=utcnow)

class PostRecord(BaseModel):
    post_uri: str
    author_did: str
    feed_id: Optional[str] = None
    text: str = ""
    created_at: datetime
    indexed_at: datetime = Field(default_factory=utcnow)
    like_count: int = 0
    repost_count: int = 0
    reply_count: int = 0
    quote_count: int = 0

class HashtagRecord(BaseModel):
    post_uri: str
    tag: str
    indexed_at: datetime = Field(default_factory=utcnow)

    @field_validator("tag")
    @classmethod
    def normalize_tag(cls, v: str) -> str:
        v = v.strip().lower()
        if v.startswith("#"):
            v = v[1:]
        return v

class EngagementSnapshot(BaseModel):
    post_uri: str
    metric_type: str
    metric_value: int
    observed_at: datetime = Field(default_factory=utcnow)

class NormalizedEvent(BaseModel):
    post: PostRecord
    hashtags: List[HashtagRecord] = []