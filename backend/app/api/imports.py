"""Endpoints /api/imports."""
from __future__ import annotations

import magic
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.bank_account import BankAccount
from app.models.import_record import ImportRecord
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.parsers.errors import ParserError, UnknownBankError
from app.schemas.import_record import ImportRecordRead
from app.services.imports import (
    FileTooLargeError,
    TooManyPagesError,
    TooManyTransactionsError,
    import_pdf_bytes,
)

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("", response_model=ImportRecordRead, status_code=status.HTTP_201_CREATED)
async def create_import(
    bank_account_id: int = Form(...),
    file: UploadFile = File(...),
    override_duplicates: bool = Form(False),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ImportRecordRead:
    ba = session.get(BankAccount, bank_account_id)
    if ba is None:
        raise HTTPException(status_code=404, detail="Compte bancaire introuvable")

    # 403 si l'utilisateur n'a pas accès à l'entité
    require_entity_access(session=session, user=user, entity_id=ba.entity_id)

    content = await file.read()
    mime = magic.from_buffer(content, mime=True)
    if mime != "application/pdf":
        raise HTTPException(
            status_code=400, detail=f"Fichier non PDF (type détecté : {mime})"
        )

    try:
        rec = import_pdf_bytes(
            session,
            bank_account_id=bank_account_id,
            pdf_bytes=content,
            filename=file.filename or "upload.pdf",
            override_duplicates=override_duplicates,
            uploaded_by_id=user.id,
        )
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except (TooManyPagesError, TooManyTransactionsError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except UnknownBankError:
        raise HTTPException(
            status_code=400,
            detail="Banque non reconnue. Seul Delubac est supporté pour l'instant.",
        )
    except ParserError as exc:
        raise HTTPException(status_code=422, detail=f"Erreur d'analyse : {exc}")

    session.commit()
    session.refresh(rec)
    return ImportRecordRead.model_validate(rec)


@router.get("", response_model=list[ImportRecordRead])
def list_imports(
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[ImportRecordRead]:
    # Imports accessibles = ceux dont le bank_account appartient à une entity où user a accès
    accessible_entity_ids = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )
    stmt = (
        select(ImportRecord)
        .join(BankAccount, BankAccount.id == ImportRecord.bank_account_id)
        .where(BankAccount.entity_id.in_(accessible_entity_ids))
    )
    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        stmt = stmt.where(BankAccount.entity_id == entity_id)
    rows = session.execute(
        stmt.order_by(ImportRecord.created_at.desc())
    ).scalars().all()
    return [ImportRecordRead.model_validate(r) for r in rows]


@router.get("/{import_id}", response_model=ImportRecordRead)
def get_import(
    import_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ImportRecordRead:
    rec = session.get(ImportRecord, import_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Import introuvable")

    ba = session.get(BankAccount, rec.bank_account_id)
    require_entity_access(session=session, user=user, entity_id=ba.entity_id)
    return ImportRecordRead.model_validate(rec)


@router.get("/{import_id}/file")
def get_import_file(
    import_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    """Stream le PDF original d'un import (permission = accès à l'entité)."""
    from app.services.import_storage import read_pdf

    rec = session.get(ImportRecord, import_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Import introuvable")

    ba = session.get(BankAccount, rec.bank_account_id)
    require_entity_access(session=session, user=user, entity_id=ba.entity_id)

    if not rec.file_sha256:
        raise HTTPException(status_code=404, detail="Fichier non disponible pour cet import")

    data = read_pdf(rec.file_sha256)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Le fichier n'a pas été conservé (import antérieur à l'activation du stockage)",
        )

    filename = rec.filename or f"import_{rec.id}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
