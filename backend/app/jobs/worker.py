"""Background job worker.

Usage:
    python -m app.jobs.worker --once
    python -m app.jobs.worker --loop --interval 10

Processes queued ingestion and deletion-purge jobs. Intended as a separate process in
deployment (see docs/operations.md); it is not started automatically by the API.
"""

from __future__ import annotations

import argparse
import logging
import time

from app.core.config import settings
from app.core.logging import configure_logging
from app.db import SessionLocal
from app.services import privacy
from app.services.ingestion import run_queue

logger = logging.getLogger("hva.worker")


def tick() -> list[str]:
    with SessionLocal() as db:
        results = run_queue(db, limit=10)
        purged = privacy.purge_expired_accounts(db)
        if purged:
            results.append(f"deletion_purge:purged={purged}")
        db.commit()
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="HVA background job worker")
    parser.add_argument("--once", action="store_true", help="process the queue once and exit")
    parser.add_argument("--loop", action="store_true", help="keep polling")
    parser.add_argument("--interval", type=int, default=10, help="seconds between polls")
    args = parser.parse_args()
    configure_logging(settings.log_level)

    if args.once or not args.loop:
        results = tick()
        logger.info("processed %d jobs: %s", len(results), results)
        return

    logger.info("worker started (interval=%ss)", args.interval)
    while True:
        try:
            results = tick()
            if results:
                logger.info("processed jobs: %s", results)
        except Exception:  # noqa: BLE001 - keep the worker alive, log the failure
            logger.exception("worker tick failed")
        time.sleep(max(2, args.interval))


if __name__ == "__main__":
    main()
