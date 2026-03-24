from datetime import datetime, timezone
import requests
from src.db import init_db, get_conn, upsert_profile

PROFILE_ENDPOINT = "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile"

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def short_did(did: str) -> str:
    if did.startswith("did:plc:"):
        return did[:18] + "..."
    return did

def fetch_profile(did: str) -> dict | None:
    try:
        r = requests.get(PROFILE_ENDPOINT, params={"actor": did}, timeout=15)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

def enrich_profiles(limit: int = 300) -> dict:
    init_db()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT feed_id
    FROM topic_feed_rank
    WHERE feed_id LIKE 'did:%'
    LIMIT ?;
    """, (limit,))
    did_rows = cur.fetchall()
    conn.close()

    dids = [r[0] for r in did_rows]
    if not dids:
        return {"scanned": 0, "updated": 0, "resolved": 0, "fallback_only": 0}

    updated = 0
    resolved = 0
    fallback_only = 0
    ts = utcnow_iso()

    for did in dids:
        data = fetch_profile(did)
        if data:
            handle = data.get("handle")
            display_name = data.get("displayName") or data.get("display_name")
            avatar = data.get("avatar")
            upsert_profile(did, handle, display_name, avatar, ts)
            updated += 1
            if handle or display_name:
                resolved += 1
            else:
                fallback_only += 1
        else:
            upsert_profile(did, None, short_did(did), None, ts)
            fallback_only += 1

    return {
        "scanned": len(dids),
        "updated": updated,
        "resolved": resolved,
        "fallback_only": fallback_only,
    }

if __name__ == "__main__":
    print(enrich_profiles())
