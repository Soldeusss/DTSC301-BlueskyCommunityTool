# DTSC301-BlueskyCommunityTool

A Bluesky community analysis tool built for a data science course.
The project ingests live Bluesky activity, maps posts to technology topic clusters, computes popularity metrics, ranks feed recommendations, and presents results through an interactive web GUI.

---

## Current Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Foundation | Complete |
| Phase 2 | Core Intelligence | Complete |
| Phase 3 | User-Facing Output | Complete |
| Phase 4 | Visual Deliverables | Complete |
| Phase 5 | Validation & Demo Readiness | In Progress |

---

## What the Project Does (End-to-End)

1. Connects to Bluesky Jetstream and ingests live post events filtered by topic keywords.
2. Validates and normalizes incoming data using Pydantic models (clean-first, store second).
3. Stores only cleaned, minimal records in a local SQLite database.
4. Extracts hashtags and keywords from post text.
5. Maps posts to canonical topic clusters using rule-based term matching.
6. Computes topic and feed-level popularity metrics (post volume, likes, engagement).
7. Builds a transparent, weighted ranking score for each topic/feed combination.
8. Enriches author DIDs with human-readable handles and display names via the Bluesky public API.
9. Serves a FastAPI backend with endpoints for topics, recommendations, word cloud data, and graph data.
10. Displays an interactive web GUI with:
    - Top feed recommendations with score explanations
    - Keyword frequency word-cloud chart
    - Interactive feed relation graph

---

## Implemented MVP Scope

- Live data ingestion from Bluesky Jetstream (AT Protocol).
- Feed/topic mapping via hashtag and keyword rule matching.
- Popularity statistics: post count, like count, engagement proxy.
- Topic-based recommendation API with explainable weighted scores.
- Profile enrichment for readable display names and handles.
- Keyword word-cloud visualization.
- Interactive feed relation graph.
- Pipeline orchestrator script for full or partial runs.

---

## Project Structure

```
DTSC301-BlueskyCommunityTool/
  src/
    __init__.py
    config.py              # environment + path config
    models.py              # Pydantic models for validation
    db.py                  # SQLite schema + helper functions
    normalize.py           # clean/transform ingested events
    ingest.py              # sample/test ingest runner
    jetstream_ingest.py    # live Jetstream ingest pipeline
    backfill_keywords.py   # keyword extraction backfill
    topic_rules.py         # canonical topic definitions
    topic_mapper.py        # post-to-topic mapping
    metrics.py             # popularity metrics aggregation
    ranking.py             # feed ranking score computation
    enrich_profiles.py     # DID to handle/display name resolution
    api.py                 # FastAPI backend + GUI serving
  web/
    index.html             # interactive web GUI
  data/
    bluesky_tool.db        # SQLite database (generated at runtime)
  run.py                   # full pipeline orchestrator
  main.py                  # API server entrypoint
  requirements.txt
  .env                     # local config (not committed)
  .env.example             # safe config template
  Checklist.md
  README.md
```

---

## Data Model

### Core Tables

| Table | Description |
|-------|-------------|
| `post` | Normalized post records |
| `hashtag` | Extracted hashtags per post |
| `keyword` | Extracted keywords per post |
| `topic` | Canonical topic definitions |
| `topic_rule` | Term matching rules per topic |
| `post_topic` | Post-to-topic assignments with score and matched terms |
| `topic_metrics` | Aggregate metrics per topic |
| `topic_feed_metrics` | Aggregate metrics per topic/feed proxy |
| `topic_feed_rank` | Final ranked recommendations with explanation |
| `profile` | DID to handle/display name enrichment |
| `ingestion_run` | Run metadata: accepted, scanned, dropped, status |
| `engagement` | Engagement snapshot storage |

---

## Ranking Formula

For each `topic_id + feed_id` pair, the ranking score is computed as:

    score = 0.35 * post_norm + 0.30 * like_norm + 0.35 * engagement_norm

Where each metric is normalized by the maximum value within the same topic group.

Each recommendation includes a full explanation string showing:
- normalized component values
- weight multipliers
- final score

---

## API Endpoints

Base URL (local): `http://127.0.0.1:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/topics` | List all available topics |
| GET | `/recommendations?topic_id=<id>&top=<n>` | Top ranked feeds for a topic |
| GET | `/wordcloud?topic_id=<id>&top_words=<n>` | Keyword frequency data |
| GET | `/graph?topic_id=<id>&top_feeds=<n>&min_related_weight=<n>` | Graph nodes and edges |
| GET | `/` | Web GUI |
| GET | `/docs` | Swagger / OpenAPI documentation |

---

## How to Run

### 1) Prerequisites

- Python 3.10 or higher (3.11 recommended)
- macOS or Linux
- `sqlite3` CLI (optional, for manual inspection)

### 2) Clone the repository

    git clone https://github.com/luc14n/DTSC301-BlueskyCommunityTool.git
    cd DTSC301-BlueskyCommunityTool

### 3) Create and activate virtual environment

    python3 -m venv .venv
    source .venv/bin/activate

### 4) Install dependencies

    python -m pip install --upgrade pip setuptools wheel
    python -m pip install atproto requests pandas python-dotenv pydantic rich websockets fastapi uvicorn networkx

Or if a requirements.txt is present:

    python -m pip install -r requirements.txt

### 5) Create your .env file

Create a file named `.env` in the repo root with the following contents:

    JETSTREAM_URL=wss://jetstream2.us-east.bsky.network/subscribe
    INGEST_TOPICS=ai,machinelearning,datascience,python,javascript,typescript,java,golang,rust,webdev,frontend,backend,devops,cloud,cybersecurity,blockchain,opensource,startups,uxdesign,gamedev
    INGEST_MAX_RECORDS=10000
    DATA_DIR=./data

### 6) Run the full pipeline (fresh start)

Use the pipeline orchestrator:

    python run.py --reset --max-records 10000

This performs the following steps in order:
1. Deletes and recreates the `data/` directory
2. Ingests live posts from Jetstream
3. Runs keyword extraction backfill
4. Seeds topic rules and maps posts to topics
5. Computes topic and feed-level metrics
6. Builds ranking scores

### 7) Enrich profile labels (recommended)

Resolves DIDs to readable handles and display names:

    python -m src.enrich_profiles

### 8) Start the API and web GUI

    python -m uvicorn src.api:app --reload

Then open in your browser:

- Web GUI:    http://127.0.0.1:8000/
- API docs:   http://127.0.0.1:8000/docs

---

## Operational Commands

### Recompute analytics without re-ingesting

    python run.py --skip-ingest

### Ingest only, skip downstream

    python run.py --skip-keywords --skip-mapping --skip-metrics --skip-ranking

### Inspect database row counts

    sqlite3 data/bluesky_tool.db "SELECT COUNT(*) FROM post;"
    sqlite3 data/bluesky_tool.db "SELECT COUNT(*) FROM keyword;"
    sqlite3 data/bluesky_tool.db "SELECT topic_id, COUNT(*) FROM post_topic GROUP BY topic_id ORDER BY 2 DESC;"

### Inspect top ranked feeds

    sqlite3 data/bluesky_tool.db "SELECT topic_id, feed_id, ROUND(score,4) FROM topic_feed_rank ORDER BY score DESC LIMIT 20;"

### Check ingestion run history

    sqlite3 data/bluesky_tool.db "SELECT id, source, accepted, scanned, dropped, status, started_at FROM ingestion_run ORDER BY id DESC LIMIT 5;"

---

## Known MVP Limitations

- Ingestion is real-time stream based. Historical backfill is limited.
- Feed identity in ranking uses author DID as a proxy; custom feed ID resolution is a future improvement.
- Some engagement fields may be sparse depending on Jetstream event payload content.
- Graph relatedness uses a lightweight post-count heuristic; full semantic graph modeling is a future improvement.
- Profile enrichment is best-effort and may return sparse results for low-activity accounts.

---

## Next Steps (Phase 5)

- Add unit tests for normalization, keyword extraction, topic mapping, and ranking math.
- Add an automated end-to-end pipeline validation script.
- Validate recommendation quality across 3 to 5 representative topic queries.
- Prepare demo runbook and sample output screenshots.

---

## Checklist Summary

See `Checklist.md` for the full task-level tracking.

- Phase 1 (Foundation): complete
- Phase 2 (Core Intelligence): complete
- Phase 3 (User-Facing Output): complete
- Phase 4 (Visual Deliverables): complete
- Phase 5 (Validation and Demo): in progress

---

## License

Course project / academic use.