import asyncio
import json
import websockets
from typing import Optional
from rich import print
from websockets.exceptions import ConnectionClosed

from src.config import INGEST_MAX_RECORDS, INGEST_TOPICS, JETSTREAM_URL
from src.db import (
    finish_ingestion_run,
    init_db,
    insert_post_and_hashtags,
    start_ingestion_run,
)
from src.normalize import normalize_jetstream_message


def matches_topics(text: str, topics: list[str]) -> bool:
    if not topics:
        return True
    t = (text or "").lower()
    return any(topic in t for topic in topics)


async def run_jetstream_ingest(
    max_records: int = INGEST_MAX_RECORDS,
    url: str = JETSTREAM_URL,
    max_reconnect_attempts: int = 8,
) -> dict:
    init_db()
    accepted = 0
    dropped = 0
    scanned = 0
    reconnects = 0

    run_id = start_ingestion_run(
        source="jetstream",
        notes=f"url={url}; topics={','.join(INGEST_TOPICS)}; max_records={max_records}",
    )

    print(f"[cyan]Connecting[/cyan] to {url}")
    print(f"[cyan]Topic filters:[/cyan] {INGEST_TOPICS}")
    print(f"[cyan]Max accepted records:[/cyan] {max_records}")

    try:
        while accepted < max_records:
            try:
                async with websockets.connect(
                    url, ping_interval=20, ping_timeout=20
                ) as ws:
                    while accepted < max_records:
                        raw = await ws.recv()
                        scanned += 1

                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            dropped += 1
                            continue

                        normalized: Optional = normalize_jetstream_message(msg)
                        if not normalized:
                            dropped += 1
                            continue

                        if not matches_topics(normalized.post.text, INGEST_TOPICS):
                            continue

                        insert_post_and_hashtags(normalized.post, normalized.hashtags)
                        accepted += 1

                        if accepted % 25 == 0:
                            print(
                                f"[green]Accepted[/green] {accepted} | "
                                f"[yellow]Scanned[/yellow] {scanned} | "
                                f"[red]Dropped[/red] {dropped} | "
                                f"[magenta]Reconnects[/magenta] {reconnects}"
                            )

            except (ConnectionClosed, OSError) as e:
                reconnects += 1
                if reconnects > max_reconnect_attempts:
                    raise RuntimeError(
                        f"Exceeded reconnect attempts ({max_reconnect_attempts}). Last error: {e}"
                    ) from e
                backoff = min(2**reconnects, 30)
                print(
                    f"[yellow]Connection dropped[/yellow]. Reconnecting in {backoff}s (attempt {reconnects}/{max_reconnect_attempts})..."
                )
                await asyncio.sleep(backoff)

        finish_ingestion_run(
            run_id,
            accepted,
            scanned,
            dropped,
            status="completed",
            notes=f"reconnects={reconnects}",
        )
        return {
            "accepted": accepted,
            "scanned": scanned,
            "dropped": dropped,
            "reconnects": reconnects,
        }

    except Exception as e:
        finish_ingestion_run(
            run_id, accepted, scanned, dropped, status="failed", notes=str(e)
        )
        raise


def main() -> None:
    result = asyncio.run(run_jetstream_ingest())
    print(f"[bold green]Done[/bold green] {result}")


if __name__ == "__main__":
    main()
