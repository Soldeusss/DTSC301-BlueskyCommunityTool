from collections import Counter
from pathlib import Path

import networkx as nx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.db import get_conn, init_db

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
WEB_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Bluesky Community Tool API", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def root_ui():
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="web/index.html not found")
    return FileResponse(str(index_path))


@app.get("/wordcloud")
def wordcloud_data(
    topic_id: str = Query(..., description="Canonical topic id"),
    top_words: int = Query(50, ge=10, le=200),
) -> dict:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM topic WHERE topic_id = ?;", (topic_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Unknown topic_id '{topic_id}'")

    cur.execute(
        """
    SELECT k.keyword
    FROM post_topic pt
    JOIN keyword k ON k.post_uri = pt.post_uri
    WHERE pt.topic_id = ?;
    """,
        (topic_id,),
    )
    rows = cur.fetchall()
    conn.close()

    counter = Counter(
        (r[0] or "").strip().lower() for r in rows if (r[0] or "").strip()
    )
    most_common = counter.most_common(top_words)

    return {
        "topic_id": topic_id,
        "count": len(most_common),
        "words": [{"text": w, "value": c} for w, c in most_common],
    }


@app.get("/graph")
def graph_data(
    topic_id: str = Query(..., description="Canonical topic id"),
    top_feeds: int = Query(12, ge=5, le=40),
    min_related_weight: int = Query(2, ge=1, le=10),
) -> dict:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT topic_id, label FROM topic WHERE topic_id = ?;", (topic_id,))
    topic_row = cur.fetchone()
    if not topic_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Unknown topic_id '{topic_id}'")

    # Top ranked feeds for this topic
    cur.execute(
        """
    SELECT r.feed_id, r.score, COALESCE(pr.display_name, pr.handle, r.feed_id) AS feed_label
    FROM topic_feed_rank r
    LEFT JOIN profile pr ON pr.did = r.feed_id
    WHERE r.topic_id = ?
    ORDER BY r.score DESC
    LIMIT ?;
    """,
        (topic_id, top_feeds),
    )
    feed_rows = cur.fetchall()

    feed_ids = [r[0] for r in feed_rows]
    score_map = {r[0]: float(r[1]) for r in feed_rows}
    label_map = {}
    for fid, _, flabel in feed_rows:
        if (not flabel) or str(flabel).startswith("did:plc:"):
            flabel = f"{fid[:18]}..."
        label_map[fid] = flabel

    # Build post counts once for relatedness proxy
    counts = {}
    for fid in feed_ids:
        cur.execute(
            """
        SELECT COUNT(*)
        FROM post_topic pt
        JOIN post p ON p.post_uri = pt.post_uri
        WHERE pt.topic_id = ? AND p.author_did = ?;
        """,
            (topic_id, fid),
        )
        counts[fid] = cur.fetchone()[0] or 0

    conn.close()

    nodes = [
        {
            "id": topic_id,
            "kind": "topic",
            "label": topic_row[1],
            "score": 1.0,
        }
    ]

    # Primary edges topic -> feed (keep)
    edges = []
    for fid in feed_ids:
        nodes.append(
            {
                "id": fid,
                "kind": "feed",
                "label": label_map[fid],
                "score": score_map.get(fid, 0.0),
                "raw_id": fid,
            }
        )
        edges.append(
            {
                "source": topic_id,
                "target": fid,
                "weight": score_map.get(fid, 0.0),
                "relation": "topic_link",
            }
        )

    # Secondary feed-feed edges (prune aggressively)
    # only if both have nontrivial activity and overlap proxy >= threshold
    for i in range(len(feed_ids)):
        for j in range(i + 1, len(feed_ids)):
            f1, f2 = feed_ids[i], feed_ids[j]
            overlap_proxy = min(counts.get(f1, 0), counts.get(f2, 0))
            if overlap_proxy >= min_related_weight:
                edges.append(
                    {
                        "source": f1,
                        "target": f2,
                        "weight": float(overlap_proxy),
                        "relation": "related",
                    }
                )

    return {
        "topic": {"topic_id": topic_row[0], "label": topic_row[1]},
        "nodes": nodes,
        "edges": edges,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/topics")
def list_topics() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT topic_id, label FROM topic ORDER BY topic_id;")
    rows = cur.fetchall()
    conn.close()

    return {
        "count": len(rows),
        "topics": [{"topic_id": r[0], "label": r[1]} for r in rows],
    }


@app.get("/recommendations")
def recommendations(
    topic_id: str = Query(..., description="Canonical topic id, e.g. ai_ml"),
    top: int = Query(10, ge=1, le=100),
) -> dict:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT topic_id, label FROM topic WHERE topic_id = ?;", (topic_id,))
    topic_row = cur.fetchone()
    if not topic_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Unknown topic_id '{topic_id}'")

    cur.execute(
        """
        SELECT
          r.feed_id,
          COALESCE(pr.display_name, pr.handle, r.feed_id) AS feed_label,
          pr.handle,
          r.score,
          r.post_norm,
          r.like_norm,
          r.engagement_norm,
          r.explanation,
          m.post_count,
          m.like_count,
          m.engagement_count
        FROM topic_feed_rank r
        LEFT JOIN topic_feed_metrics m
          ON m.topic_id = r.topic_id AND m.feed_id = r.feed_id
        LEFT JOIN profile pr
          ON pr.did = r.feed_id
        WHERE r.topic_id = ?
        ORDER BY r.score DESC
        LIMIT ?;
        """,
        (topic_id, top),
    )

    rows = cur.fetchall()
    conn.close()

    items = []
    for row in rows:
        items.append(
            {
                "feed_id": row[0],
                "feed_label": row[1],
                "handle": row[2],
                "score": row[3],
                "post_norm": row[4],
                "like_norm": row[5],
                "engagement_norm": row[6],
                "explanation": row[7],
                "post_count": row[8] or 0,
                "like_count": row[9] or 0,
                "engagement_count": row[10] or 0,
            }
        )

    return {
        "topic": {"topic_id": topic_row[0], "label": topic_row[1]},
        "count": len(items),
        "recommendations": items,
    }
