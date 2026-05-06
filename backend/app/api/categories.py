"""Endpoints /api/categories.

Lecture libre pour tout utilisateur connecté ; création / modification /
suppression réservée aux administrateurs et limitée aux catégories
non-système. On ne permet pas de créer des racines via l'API : les
catégories utilisateur sont toujours des sous-catégories d'une racine
seed existante (Charges externes, Encaissements, etc.).
"""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.categorization_rule import CategorizationRule
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User, UserRole
from app.schemas.category import (
    CategoryCreate,
    CategoryListItem,
    CategoryUpdate,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _slugify(name: str) -> str:
    """Slug ASCII-lowercase-tirets pour identifiant unique stable."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-") or "categorie"


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Droits administrateur requis")


@router.get("", response_model=list[CategoryListItem])
def list_categories(
    entity_id: int | None = Query(None),  # noqa: ARG001 — no-op, compat future
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Category]:
    """Liste des catégories.

    Les catégories sont globales (pas de rattachement à une entité).
    Le paramètre `entity_id` est accepté mais ignoré pour compatibilité
    future ; la réponse est identique qu'il soit fourni ou non.
    """
    stmt = select(Category).order_by(Category.name)
    return list(session.execute(stmt).scalars().all())


@router.post("", response_model=CategoryListItem, status_code=201)
def create_category(
    payload: CategoryCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Category:
    """Crée une sous-catégorie utilisateur sous une racine existante."""
    _require_admin(user)

    parent = session.get(Category, payload.parent_category_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="Catégorie parent introuvable")

    base_slug = _slugify(payload.name)
    slug = base_slug
    n = 2
    while session.execute(
        select(Category.id).where(Category.slug == slug)
    ).scalar_one_or_none() is not None:
        slug = f"{base_slug}-{n}"
        n += 1

    cat = Category(
        name=payload.name.strip(),
        slug=slug,
        color=payload.color or parent.color,
        parent_category_id=parent.id,
        is_system=False,
    )
    session.add(cat)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Conflit lors de la création")
    session.refresh(cat)
    return cat


@router.patch("/{category_id}", response_model=CategoryListItem)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Category:
    _require_admin(user)
    cat = session.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    if cat.is_system:
        raise HTTPException(
            status_code=403,
            detail="Catégorie système : nom et couleur figés.",
        )
    if payload.name is not None:
        cat.name = payload.name.strip()
    if payload.color is not None:
        cat.color = payload.color
    session.commit()
    session.refresh(cat)
    return cat


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    reassign_to_parent: bool = Query(
        False,
        description=(
            "Si true, reclasse les transactions et règles de cette catégorie "
            "vers la catégorie parente avant de supprimer. Sans ce flag, la "
            "suppression est refusée (409) tant qu'il reste des références."
        ),
    ),
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Supprime une sous-catégorie utilisateur.

    Comportement par défaut (`reassign_to_parent=false`) : refuse la
    suppression si des transactions ou des règles pointent encore vers la
    catégorie. Le détail du 409 est structuré pour que le front affiche
    une UI de confirmation explicite (« X tx + Y règles seront déplacées
    vers <parent>. Confirmer ? »).

    Avec `reassign_to_parent=true` : reclasse en cascade vers la catégorie
    parente puis supprime, le tout dans une seule transaction SQL. Reste
    bloqué si la catégorie a elle-même des sous-catégories (l'admin doit
    les supprimer d'abord pour éviter d'aplatir l'arborescence).
    """
    _require_admin(user)
    cat = session.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    if cat.is_system:
        raise HTTPException(
            status_code=403, detail="Catégorie système : suppression interdite."
        )

    children_count = session.execute(
        select(func.count(Category.id)).where(Category.parent_category_id == category_id)
    ).scalar_one()
    if children_count > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CHILDREN_BLOCKING",
                "message": (
                    f"{children_count} sous-catégorie(s) attachée(s). "
                    "Supprimez-les d'abord."
                ),
                "children_count": children_count,
            },
        )

    tx_count = session.execute(
        select(func.count(Transaction.id)).where(Transaction.category_id == category_id)
    ).scalar_one()
    rule_count = session.execute(
        select(func.count(CategorizationRule.id)).where(
            CategorizationRule.category_id == category_id
        )
    ).scalar_one()

    if (tx_count > 0 or rule_count > 0) and not reassign_to_parent:
        parent = (
            session.get(Category, cat.parent_category_id)
            if cat.parent_category_id is not None
            else None
        )
        bits: list[str] = []
        if tx_count > 0:
            bits.append(f"{tx_count} transaction(s)")
        if rule_count > 0:
            bits.append(f"{rule_count} règle(s)")
        target = parent.name if parent is not None else "la racine"
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REFS_BLOCKING",
                "message": (
                    f"{' et '.join(bits)} référencent encore cette catégorie. "
                    f"Confirmez la reclassification vers « {target} »."
                ),
                "tx_count": tx_count,
                "rule_count": rule_count,
                "parent_id": cat.parent_category_id,
                "parent_name": parent.name if parent is not None else None,
            },
        )

    if reassign_to_parent and (tx_count > 0 or rule_count > 0):
        if cat.parent_category_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Catégorie sans parent : impossible de reclasser. "
                    "Réassignez manuellement avant suppression."
                ),
            )
        parent_id = cat.parent_category_id
        if tx_count > 0:
            session.execute(
                update(Transaction)
                .where(Transaction.category_id == category_id)
                .values(category_id=parent_id)
            )
        if rule_count > 0:
            session.execute(
                update(CategorizationRule)
                .where(CategorizationRule.category_id == category_id)
                .values(category_id=parent_id)
            )

    session.delete(cat)
    session.commit()
