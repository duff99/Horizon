"""Endpoints admin pour la page UI Sauvegardes.

3 endpoints, tous admin-only :
- GET  /api/admin/backups            → 50 derniers, sortés desc
- GET  /api/admin/backups/disk       → stats disque du dossier backups
- POST /api/admin/backups/trigger    → déclenche un backup manuel ou
                                        un test de restore

Le trigger ne lance PAS le script directement (le backend tourne en non-root,
sans accès docker). Il insère une row 'pending' en DB et dépose un fichier
JSON dans /data/triggers (volume bind-mount partagé avec le service systemd
horizon-backup-trigger qui tourne en root sur l'hôte). C'est le watcher qui
exécute backup-db.sh / verify-restore.sh avec --row-id.

Verrou anti-doublon : refuse si une row pending|running existe déjà.
"""
from __future__ import annotations

import json
import os
import shutil
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.backup_history import BackupHistory
from app.schemas.backup_history import (
    BackupDiskStats,
    BackupHistoryRead,
    BackupTriggerRequest,
    BackupTriggerResponse,
)

router = APIRouter(
    prefix="/api/admin/backups",
    tags=["admin-backups"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[BackupHistoryRead])
def list_backups(db: Session = Depends(get_db)) -> list[BackupHistory]:
    """50 derniers backups, du plus récent au plus ancien."""
    return list(
        db.scalars(
            select(BackupHistory)
            .order_by(BackupHistory.started_at.desc())
            .limit(50)
        )
    )


@router.get("/disk", response_model=BackupDiskStats)
def get_disk_stats() -> BackupDiskStats:
    """Espace disque du volume où sont stockés les backups.

    Référence : /var/lib/horizon-backup-triggers est sur la même partition
    que les autres données du serveur. On regarde / pour avoir une vue
    représentative (le dossier backups/ du repo Horizon est sur cette même
    partition).
    """
    mount = "/"
    threshold_pct = int(os.environ.get("HORIZON_DISK_THRESHOLD", "85"))
    usage = shutil.disk_usage(mount)
    used_pct = round(usage.used / usage.total * 100)
    return BackupDiskStats(
        mount=mount,
        size_gb=usage.total // (1024**3),
        used_gb=usage.used // (1024**3),
        avail_gb=usage.free // (1024**3),
        used_pct=used_pct,
        threshold_pct=threshold_pct,
        status="alert" if used_pct >= threshold_pct else "ok",
    )


# Le dossier triggers est partagé avec systemd via bind mount Docker. Configurable
# via HORIZON_TRIGGER_DIR (défaut /data/triggers, chemin du container backend).
_TRIGGER_DIR = os.environ.get("HORIZON_TRIGGER_DIR", "/data/triggers")

_ALLOWED_TRIGGER_TYPES = {"manual", "restore-test"}


@router.post(
    "/trigger",
    response_model=BackupTriggerResponse,
    status_code=status.HTTP_201_CREATED,
)
def trigger_backup(
    payload: BackupTriggerRequest,
    db: Session = Depends(get_db),
) -> BackupTriggerResponse:
    """Demande l'exécution d'un backup manuel ou d'un test de restore.

    Effets :
    1. Vérifie qu'aucune opération n'est déjà en cours (pending|running)
       — sinon 409. Une seule opération à la fois (le watcher traite la
       queue en série et chaque op prend ~5s, donc pas de problème UX).
    2. Insère une row backup_history (status='pending', type=payload.type).
    3. Écrit /data/triggers/<row_id>.json avec le row_id et le type.
    4. Le watcher systemd lit le fichier dans ≤ 2s et lance le script.
    """
    if payload.type not in _ALLOWED_TRIGGER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"type doit être l'un de {sorted(_ALLOWED_TRIGGER_TYPES)} "
                f"(reçu : {payload.type!r})"
            ),
        )

    in_flight = db.scalar(
        select(BackupHistory)
        .where(BackupHistory.status.in_(["pending", "running"]))
        .limit(1)
    )
    if in_flight is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Une opération est déjà en cours (status={in_flight.status!r}, "
                f"type={in_flight.type!r}). Patientez quelques secondes."
            ),
        )

    row = BackupHistory(
        status="pending",
        type=payload.type,
        # file_path sera mis à jour par le script ; on met un placeholder
        # car la colonne est NOT NULL.
        file_path="pending",
    )
    db.add(row)
    db.flush()
    row_id = row.id
    db.commit()

    # Écriture du trigger : nom = <uuid>.json. Si l'écriture échoue (FS plein,
    # bind mount manquant), on supprime la row pending pour ne pas laisser
    # l'UI bloquée par un faux pending.
    os.makedirs(_TRIGGER_DIR, exist_ok=True)
    trigger_path = os.path.join(_TRIGGER_DIR, f"{row_id}.json")
    payload_dict = {"row_id": str(row_id), "type": payload.type}
    try:
        with open(trigger_path, "w", encoding="utf-8") as fh:
            json.dump(payload_dict, fh)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError as exc:
        # Cleanup : on remet la row en failed plutôt que de la laisser pending.
        row.status = "failed"
        row.error_message = f"Trigger write KO: {exc}"
        row.error_step = "write_trigger"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Impossible d'écrire le trigger ({exc})",
        ) from exc

    return BackupTriggerResponse(row_id=row_id)
