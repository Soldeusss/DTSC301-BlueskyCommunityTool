from datetime import datetime, timezone
from src.db import get_conn, init_db, insert_keywords
from src.keywords import extract_keywords

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def run(limit: int = 5000) -> dict:
    init_db()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT p.post_uri, p.text
    FROM post p
    LEFT JOIN keyword k ON p.post_uri = k.post_uri
    WHERE k.post_uri IS NULL
    LIMIT ?;
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    inserted_posts = 0
    inserted_keywords = 0
    ts = utcnow_iso()

    for post_uri, text in rows:
        kws = extract_keywords(text or "")
        insert_keywords(post_uri, kws, ts)
        inserted_posts += 1
        inserted_keywords += len(kws)

    return {
        "processed_posts": inserted_posts,
        "inserted_keywords": inserted_keywords
    }

if __name__ == "__main__":
    print(run())
