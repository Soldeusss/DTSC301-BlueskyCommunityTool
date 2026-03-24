from datetime import datetime, timezone
from src.db import init_db, get_conn

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def compute_metrics() -> dict:
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    ts = utcnow_iso()

    # Topic-level metrics
    cur.execute("""
    SELECT
      pt.topic_id,
      COUNT(DISTINCT p.post_uri) AS post_count,
      COALESCE(SUM(p.like_count), 0) AS like_count,
      COALESCE(SUM(p.like_count + p.repost_count + p.reply_count + p.quote_count), 0) AS engagement_count,
      COUNT(DISTINCT p.author_did) AS unique_authors
    FROM post_topic pt
    JOIN post p ON p.post_uri = pt.post_uri
    GROUP BY pt.topic_id;
    """)
    topic_rows = cur.fetchall()

    for topic_id, post_count, like_count, engagement_count, unique_authors in topic_rows:
        cur.execute("""
        INSERT INTO topic_metrics (topic_id, post_count, like_count, engagement_count, unique_authors, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(topic_id) DO UPDATE SET
          post_count=excluded.post_count,
          like_count=excluded.like_count,
          engagement_count=excluded.engagement_count,
          unique_authors=excluded.unique_authors,
          updated_at=excluded.updated_at;
        """, (topic_id, post_count, like_count, engagement_count, unique_authors, ts))

    # Topic + feed proxy metrics (using author_did as temporary feed_id proxy)
    cur.execute("""
    SELECT
      pt.topic_id,
      p.author_did AS feed_id,
      COUNT(*) AS post_count,
      COALESCE(SUM(p.like_count), 0) AS like_count,
      COALESCE(SUM(p.like_count + p.repost_count + p.reply_count + p.quote_count), 0) AS engagement_count
    FROM post_topic pt
    JOIN post p ON p.post_uri = pt.post_uri
    GROUP BY pt.topic_id, p.author_did;
    """)
    tf_rows = cur.fetchall()

    for topic_id, feed_id, post_count, like_count, engagement_count in tf_rows:
        cur.execute("""
        INSERT INTO topic_feed_metrics (topic_id, feed_id, post_count, like_count, engagement_count, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(topic_id, feed_id) DO UPDATE SET
          post_count=excluded.post_count,
          like_count=excluded.like_count,
          engagement_count=excluded.engagement_count,
          updated_at=excluded.updated_at;
        """, (topic_id, feed_id, post_count, like_count, engagement_count, ts))

    conn.commit()
    conn.close()

    return {
        "topics_aggregated": len(topic_rows),
        "topic_feed_rows": len(tf_rows),
    }

if __name__ == "__main__":
    print(compute_metrics())