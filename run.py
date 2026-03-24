import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def run_cmd(cmd: list[str], env: dict | None = None) -> None:
    print(f"\n[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def reset_data_dir() -> None:
    if DATA_DIR.exists():
        print(f"[INFO] Removing {DATA_DIR}")
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Created {DATA_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restart and run Bluesky Community Tool pipeline."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate data/ before running pipeline.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Override INGEST_MAX_RECORDS for this run (e.g. 10000).",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip live ingest step and only run downstream pipeline.",
    )
    parser.add_argument(
        "--skip-keywords",
        action="store_true",
        help="Skip keyword backfill step.",
    )
    parser.add_argument(
        "--skip-mapping",
        action="store_true",
        help="Skip topic mapping step.",
    )
    parser.add_argument(
        "--skip-metrics",
        action="store_true",
        help="Skip metrics step.",
    )
    parser.add_argument(
        "--skip-ranking",
        action="store_true",
        help="Skip ranking step.",
    )
    args = parser.parse_args()

    if args.reset:
        reset_data_dir()

    env = os.environ.copy()
    if args.max_records is not None:
        env["INGEST_MAX_RECORDS"] = str(args.max_records)
        print(f"[INFO] INGEST_MAX_RECORDS override = {env['INGEST_MAX_RECORDS']}")

    # 1) Ingest
    if not args.skip_ingest:
        run_cmd([sys.executable, "-m", "src.jetstream_ingest"], env=env)

    # 2) Keywords
    if not args.skip_keywords:
        run_cmd([sys.executable, "-m", "src.backfill_keywords"], env=env)

    # 3) Topic mapping (seeds rules + maps)
    if not args.skip_mapping:
        run_cmd([sys.executable, "-m", "src.topic_mapper"], env=env)

    # 4) Metrics
    if not args.skip_metrics:
        run_cmd([sys.executable, "-m", "src.metrics"], env=env)

    # 5) Ranking
    if not args.skip_ranking:
        run_cmd([sys.executable, "-m", "src.ranking"], env=env)

    print("\n[DONE] Pipeline complete.")
    print("[TIP] Verify with:")
    print('  sqlite3 data/bluesky_tool.db "SELECT COUNT(*) FROM post;"')
    print(
        '  sqlite3 data/bluesky_tool.db "SELECT topic_id, COUNT(*) FROM post_topic GROUP BY topic_id ORDER BY 2 DESC;"'
    )


if __name__ == "__main__":
    main()
