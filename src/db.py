import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from src.config import DB_PATH
from src.models import EngagementSnapshot, HashtagRecord, PostRecord


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post (
        post_uri TEXT PRIMARY KEY,
        author_did TEXT NOT NULL,
        feed_id TEXT,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        indexed_at TEXT NOT NULL,
        like_count INTEGER NOT NULL DEFAULT 0,
        repost_count INTEGER NOT NULL DEFAULT 0,
        reply_count INTEGER NOT NULL DEFAULT 0,
        quote_count INTEGER NOT NULL DEFAULT 0
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hashtag (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_uri TEXT NOT NULL,
        tag TEXT NOT NULL,
        indexed_at TEXT NOT NULL,
        FOREIGN KEY(post_uri) REFERENCES post(post_uri) ON DELETE CASCADE
    );
    """)

    # Prevent duplicate hashtag rows for same post/tag
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_hashtag_post_tag
    ON hashtag(post_uri, tag);
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_post_created_at ON post(created_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hashtag_tag ON hashtag(tag);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hashtag_post_uri ON hashtag(post_uri);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS engagement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_uri TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        metric_value INTEGER NOT NULL,
        observed_at TEXT NOT NULL,
        FOREIGN KEY(post_uri) REFERENCES post(post_uri) ON DELETE CASCADE
    );
    """)

    # Track each ingestion run
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_run (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        source TEXT NOT NULL,
        accepted INTEGER NOT NULL DEFAULT 0,
        scanned INTEGER NOT NULL DEFAULT 0,
        dropped INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'running',
        notes TEXT
    );
    """)
    
    # Keyword extraction
    cur.execute("""
    CREATE TABLE IF NOT EXISTS keyword (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_uri TEXT NOT NULL,
        keyword TEXT NOT NULL,
        indexed_at TEXT NOT NULL,
        FOREIGN KEY(post_uri) REFERENCES post(post_uri) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_keyword_post_keyword
    ON keyword(post_uri, keyword);
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_keyword_keyword ON keyword(keyword);")

    # Topic tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topic (
        topic_id TEXT PRIMARY KEY,
        label TEXT NOT NULL
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topic_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id TEXT NOT NULL,
        term TEXT NOT NULL,
        weight REAL NOT NULL DEFAULT 1.0,
        source TEXT NOT NULL DEFAULT 'keyword',
        FOREIGN KEY(topic_id) REFERENCES topic(topic_id) ON DELETE CASCADE
    );
    """)
    
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_topic_rule_topic_term_source
    ON topic_rule(topic_id, term, source);
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_topic (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_uri TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        score REAL NOT NULL,
        matched_terms TEXT NOT NULL,
        indexed_at TEXT NOT NULL,
        FOREIGN KEY(post_uri) REFERENCES post(post_uri) ON DELETE CASCADE,
        FOREIGN KEY(topic_id) REFERENCES topic(topic_id) ON DELETE CASCADE
    );
    """)
    
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_post_topic
    ON post_topic(post_uri, topic_id);
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_post_topic_topic_id ON post_topic(topic_id);")
    
    # Aggregate metrics for quick retrieval
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topic_metrics (
        topic_id TEXT PRIMARY KEY,
        post_count INTEGER NOT NULL,
        like_count INTEGER NOT NULL,
        engagement_count INTEGER NOT NULL,
        unique_authors INTEGER NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(topic_id) REFERENCES topic(topic_id) ON DELETE CASCADE
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topic_feed_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id TEXT NOT NULL,
        feed_id TEXT NOT NULL, -- for now: author_did proxy until custom feed ingestion is added
        post_count INTEGER NOT NULL,
        like_count INTEGER NOT NULL,
        engagement_count INTEGER NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(topic_id) REFERENCES topic(topic_id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_topic_feed_metrics
    ON topic_feed_metrics(topic_id, feed_id);
    """)
    
    # Ranking tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topic_feed_rank (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id TEXT NOT NULL,
        feed_id TEXT NOT NULL,
        score REAL NOT NULL,
        post_norm REAL NOT NULL,
        like_norm REAL NOT NULL,
        engagement_norm REAL NOT NULL,
        explanation TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_topic_feed_rank
    ON topic_feed_rank(topic_id, feed_id);
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_topic_feed_rank_topic_score ON topic_feed_rank(topic_id, score DESC);")

    # Profile table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        did TEXT PRIMARY KEY,
        handle TEXT,
        display_name TEXT,
        avatar_url TEXT,
        last_seen_at TEXT NOT NULL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_profile_handle ON profile(handle);")


    conn.commit()
    conn.close()


def start_ingestion_run(source: str, notes: str | None = None) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ingestion_run (started_at, source, status, notes) VALUES (?, ?, 'running', ?);",
        (utcnow_iso(), source, notes),
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(run_id)


def finish_ingestion_run(
    run_id: int,
    accepted: int,
    scanned: int,
    dropped: int,
    status: str = "completed",
    notes: str | None = None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
    UPDATE ingestion_run
    SET ended_at = ?, accepted = ?, scanned = ?, dropped = ?, status = ?, notes = COALESCE(?, notes)
    WHERE id = ?;
    """,
        (utcnow_iso(), accepted, scanned, dropped, status, notes, run_id),
    )
    conn.commit()
    conn.close()


def insert_post_and_hashtags(
    post: PostRecord, hashtags: Iterable[HashtagRecord]
) -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
    INSERT OR REPLACE INTO post (
        post_uri, author_did, feed_id, text, created_at, indexed_at,
        like_count, repost_count, reply_count, quote_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        (
            post.post_uri,
            post.author_did,
            post.feed_id,
            post.text,
            post.created_at.isoformat(),
            post.indexed_at.isoformat(),
            post.like_count,
            post.repost_count,
            post.reply_count,
            post.quote_count,
        ),
    )

    for h in hashtags:
        cur.execute(
            "INSERT OR IGNORE INTO hashtag (post_uri, tag, indexed_at) VALUES (?, ?, ?);",
            (h.post_uri, h.tag, h.indexed_at.isoformat()),
        )

    conn.commit()
    conn.close()


def insert_engagement(rows: Iterable[EngagementSnapshot]) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO engagement (post_uri, metric_type, metric_value, observed_at) VALUES (?, ?, ?, ?);",
        [
            (r.post_uri, r.metric_type, r.metric_value, r.observed_at.isoformat())
            for r in rows
        ],
    )
    conn.commit()
    conn.close()
    
def insert_keywords(post_uri: str, keywords: list[str], indexed_at: str) -> None:
    if not keywords:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(
        "INSERT OR IGNORE INTO keyword (post_uri, keyword, indexed_at) VALUES (?, ?, ?);",
        [(post_uri, k, indexed_at) for k in keywords]
    )
    conn.commit()
    conn.close()

def upsert_topic(topic_id: str, label: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO topic (topic_id, label) VALUES (?, ?) ON CONFLICT(topic_id) DO UPDATE SET label=excluded.label;",
        (topic_id, label),
    )
    conn.commit()
    conn.close()

def upsert_topic_rule(topic_id: str, term: str, weight: float = 1.0, source: str = "keyword") -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO topic_rule (topic_id, term, weight, source)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(topic_id, term, source) DO UPDATE SET weight=excluded.weight;
    """, (topic_id, term.lower(), weight, source))
    conn.commit()
    conn.close()

def upsert_post_topic(post_uri: str, topic_id: str, score: float, matched_terms: str, indexed_at: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO post_topic (post_uri, topic_id, score, matched_terms, indexed_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(post_uri, topic_id)
    DO UPDATE SET score=excluded.score, matched_terms=excluded.matched_terms, indexed_at=excluded.indexed_at;
    """, (post_uri, topic_id, score, matched_terms, indexed_at))
    conn.commit()
    conn.close()

def upsert_profile(did: str, handle: str | None, display_name: str | None, avatar_url: str | None, last_seen_at: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO profile (did, handle, display_name, avatar_url, last_seen_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(did) DO UPDATE SET
      handle=COALESCE(excluded.handle, profile.handle),
      display_name=COALESCE(excluded.display_name, profile.display_name),
      avatar_url=COALESCE(excluded.avatar_url, profile.avatar_url),
      last_seen_at=excluded.last_seen_at;
    """, (did, handle, display_name, avatar_url, last_seen_at))
    conn.commit()
    conn.close()
