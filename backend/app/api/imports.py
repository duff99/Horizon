"""Endpoints /api/imports."""
from __future__ import annotations

import magic
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.bank_account import BankAccount
from app.models.user import User
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
