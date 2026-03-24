from datetime import datetime, timezone
from collections import defaultdict
from src.db import init_db, get_conn

W_POST = 0.35
W_LIKE = 0.30
W_ENG = 0.35

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_norm(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return value / max_value

def build_rankings() -> dict:
    init_db()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT topic_id, feed_id, post_count, like_count, engagement_count
    FROM topic_feed_metrics;
    """)
    rows = cur.fetchall()

    by_topic = defaultdict(list)
    for topic_id, feed_id, post_count, like_count, engagement_count in rows:
        by_topic[topic_id].append({
            "feed_id": feed_id,
            "post_count": float(post_count),
            "like_count": float(like_count),
            "engagement_count": float(engagement_count),
        })

    ts = utcnow_iso()
    upserts = 0

    for topic_id, items in by_topic.items():
        max_post = max(i["post_count"] for i in items) if items else 0.0
        max_like = max(i["like_count"] for i in items) if items else 0.0
        max_eng = max(i["engagement_count"] for i in items) if items else 0.0

        for i in items:
            post_norm = safe_norm(i["post_count"], max_post)
            like_norm = safe_norm(i["like_count"], max_like)
            eng_norm = safe_norm(i["engagement_count"], max_eng)

            score = (W_POST * post_norm) + (W_LIKE * like_norm) + (W_ENG * eng_norm)

            explanation = (
                f"score={score:.4f}; "
                f"post_norm={post_norm:.4f}*{W_POST}, "
                f"like_norm={like_norm:.4f}*{W_LIKE}, "
                f"engagement_norm={eng_norm:.4f}*{W_ENG}"
            )

            cur.execute("""
            INSERT INTO topic_feed_rank (
                topic_id, feed_id, score, post_norm, like_norm, engagement_norm, explanation, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic_id, feed_id) DO UPDATE SET
                score=excluded.score,
                post_norm=excluded.post_norm,
                like_norm=excluded.like_norm,
                engagement_norm=excluded.engagement_norm,
                explanation=excluded.explanation,
                updated_at=excluded.updated_at;
            """, (
                topic_id,
                i["feed_id"],
                score,
                post_norm,
                like_norm,
                eng_norm,
                explanation,
                ts,
            ))
            upserts += 1

    conn.commit()
    conn.close()

    return {"topics_ranked": len(by_topic), "rows_ranked": upserts}

if __name__ == "__main__":
    print(build_rankings())
