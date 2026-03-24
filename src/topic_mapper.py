from datetime import datetime, timezone
from collections import defaultdict

from src.db import (
    init_db,
    get_conn,
    upsert_topic,
    upsert_topic_rule,
    upsert_post_topic,
)
from src.topic_rules import TOPIC_RULES

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def seed_topic_rules() -> None:
    init_db()
    for topic_id, meta in TOPIC_RULES.items():
        upsert_topic(topic_id, meta["label"])
        for term in meta["terms"]:
            upsert_topic_rule(topic_id, term, weight=1.0, source="keyword")

def map_posts_to_topics(limit: int = 10000, min_score: float = 1.0) -> dict:
    init_db()
    conn = get_conn()
    cur = conn.cursor()

    # Gather post terms from hashtag + keyword
    cur.execute("""
    SELECT p.post_uri,
           GROUP_CONCAT(DISTINCT h.tag) AS hashtags,
           GROUP_CONCAT(DISTINCT k.keyword) AS keywords
    FROM post p
    LEFT JOIN hashtag h ON p.post_uri = h.post_uri
    LEFT JOIN keyword k ON p.post_uri = k.post_uri
    GROUP BY p.post_uri
    LIMIT ?;
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    mapped = 0
    ts = utcnow_iso()

    # Pre-normalize rules
    rules = {
        topic_id: set(term.lower() for term in meta["terms"])
        for topic_id, meta in TOPIC_RULES.items()
    }

    for post_uri, hashtags_csv, keywords_csv in rows:
        terms = set()
        if hashtags_csv:
            terms.update(t.strip().lower() for t in hashtags_csv.split(",") if t.strip())
        if keywords_csv:
            terms.update(t.strip().lower() for t in keywords_csv.split(",") if t.strip())

        if not terms:
            continue

        topic_scores = defaultdict(float)
        topic_matches = defaultdict(list)

        for topic_id, topic_terms in rules.items():
            for term in terms:
                if term in topic_terms:
                    topic_scores[topic_id] += 1.0
                    topic_matches[topic_id].append(term)

        for topic_id, score in topic_scores.items():
            if score >= min_score:
                matched = ",".join(sorted(set(topic_matches[topic_id])))
                upsert_post_topic(post_uri, topic_id, score, matched, ts)
                mapped += 1

    return {"mapped_rows": mapped, "posts_scanned": len(rows)}

if __name__ == "__main__":
    seed_topic_rules()
    print(map_posts_to_topics())
