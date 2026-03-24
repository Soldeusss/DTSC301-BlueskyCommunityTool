from typing import Iterable, Dict, Any
from rich import print
from src.db import init_db, insert_post_and_hashtags
from src.normalize import normalize_post_event

def ingest_events(events: Iterable[Dict[str, Any]], max_records: int = 1000) -> dict:
    init_db()
    accepted = 0
    dropped = 0

    for i, raw in enumerate(events):
        if i >= max_records:
            break
        normalized = normalize_post_event(raw)
        if not normalized:
            dropped += 1
            continue

        insert_post_and_hashtags(normalized.post, normalized.hashtags)
        accepted += 1

    return {"accepted": accepted, "dropped": dropped}

def sample_events() -> list[dict]:
    return [
        {
            "uri": "at://did:plc:111/app.bsky.feed.post/abc",
            "author_did": "did:plc:111",
            "text": "Loving #Python and #DataScience on Bluesky!",
            "created_at": "2026-01-20T10:00:00Z",
            "like_count": 12,
            "repost_count": 2,
            "reply_count": 1,
            "quote_count": 0,
        },
        {
            "uri": "at://did:plc:222/app.bsky.feed.post/xyz",
            "author_did": "did:plc:222",
            "text": "Graph ideas for #AI communities #Python",
            "created_at": "2026-01-20T11:00:00Z",
            "like_count": 8,
        },
    ]

if __name__ == "__main__":
    result = ingest_events(sample_events())
    print(f"[green]Ingestion complete[/green]: {result}")
