import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from src.models import PostRecord, HashtagRecord, NormalizedEvent
from typing import Optional

HASHTAG_RE = re.compile(r"#([A-Za-z0-9_]+)")

def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now(timezone.utc)

def extract_hashtags(text: str) -> List[str]:
    return sorted(set(tag.lower() for tag in HASHTAG_RE.findall(text or "")))

def normalize_post_event(raw: Dict[str, Any]) -> NormalizedEvent | None:
    """
    Expects a minimally shaped dict like:
    {
      "uri": "...",
      "author_did": "...",
      "text": "...",
      "created_at": "...ISO..."
    }
    """
    uri = raw.get("uri")
    author = raw.get("author_did")
    if not uri or not author:
        return None

    text = (raw.get("text") or "").strip()
    created_at = parse_datetime(raw.get("created_at"))

    post = PostRecord(
        post_uri=uri,
        author_did=author,
        feed_id=raw.get("feed_id"),
        text=text,
        created_at=created_at,
        like_count=int(raw.get("like_count") or 0),
        repost_count=int(raw.get("repost_count") or 0),
        reply_count=int(raw.get("reply_count") or 0),
        quote_count=int(raw.get("quote_count") or 0),
    )

    hashtags = [HashtagRecord(post_uri=uri, tag=t) for t in extract_hashtags(text)]
    return NormalizedEvent(post=post, hashtags=hashtags)

def normalize_jetstream_message(msg: Dict[str, Any]) -> Optional[NormalizedEvent]:
    """
    Normalize a Jetstream event into our minimal Post + Hashtag records.

    Expected rough shape (varies):
    {
        "kind": "...",
        "did": "did:plc:...",
        "time_us": ...,
        "commit": {
        "collection": "app.bsky.feed.post",
        "operation": "create",
        "rkey": "...",
        "record": {
            "text": "...",
            "createdAt": "..."
        }
        }
    }
    """
    commit = msg.get("commit") or {}
    collection = commit.get("collection")
    operation = commit.get("operation")

    # Only keep newly created posts
    if collection != "app.bsky.feed.post" or operation != "create":
        return None

    did = msg.get("did")
    rkey = commit.get("rkey")
    record = commit.get("record") or {}

    if not did or not rkey:
        return None

    uri = f"at://{did}/app.bsky.feed.post/{rkey}"
    text = (record.get("text") or "").strip()
    created_at = parse_datetime(record.get("createdAt"))

    post = PostRecord(
        post_uri=uri,
        author_did=did,
        feed_id=None,  # we can map feed/topic later
        text=text,
        created_at=created_at,
        like_count=0,
        repost_count=0,
        reply_count=0,
        quote_count=0,
    )

    hashtags = [HashtagRecord(post_uri=uri, tag=t) for t in extract_hashtags(text)]
    return NormalizedEvent(post=post, hashtags=hashtags)
