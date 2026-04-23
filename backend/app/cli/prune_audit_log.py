"""CLI de maintenance : supprime les lignes audit_log plus anciennes que N jours.

Usage (dans le container backend) :
    python -m app.cli.prune_audit_log           # défaut : 365 jours
    python -m app.cli.prune_audit_log --days 30 # autre cutoff

Ne PAS exécuter ce script automatiquement — il est destiné à un déclenchement
manuel (admin) ou à un cron soigneusement configuré. L'endpoint
`POST /api/admin/audit-log/prune` expose la même logique pour les admins.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.db import get_session_factory
from app.models.audit_log import AuditLog

logger = logging.getLogger("prune_audit_log")


def prune(days: int) -> int:
    if days < 30:
        raise ValueError("Refusé : days < 30 (garde-fou rétention minimale)")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    factory = get_session_factory()
    session = factory()
    try:
        result = session.execute(delete(AuditLog).where(AuditLog.occurred_at < cutoff))
        deleted = result.rowcount or 0
        session.commit()
    finally:
        session.close()
    logger.info("pruned audit_log rows older than %s days: %s", days, deleted)
    return deleted


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Purge audit_log rows older than N days.")
    parser.add_argument("--days", type=int, default=365, help="Cutoff age in days (default 365)")
    args = parser.parse_args(argv)
    deleted = prune(args.days)
    print(f"deleted={deleted} cutoff_days={args.days}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
