from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # always load repo-root .env

DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR / DATA_DIR  # force relative paths to repo root

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "bluesky_tool.db"

JETSTREAM_URL = os.getenv(
    "JETSTREAM_URL",
    "wss://jetstream2.us-east.bsky.network/subscribe"
)

INGEST_TOPICS = [
    t.strip().lower()
    for t in os.getenv("INGEST_TOPICS", "python,ai,datascience").split(",")
    if t.strip()
]

INGEST_MAX_RECORDS = int(os.getenv("INGEST_MAX_RECORDS", "1000"))