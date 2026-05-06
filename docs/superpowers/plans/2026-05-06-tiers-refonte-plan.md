# Plan A — Refonte Tiers (Clients & fournisseurs) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre la page Tiers en "Clients & fournisseurs" : supprimer les actions sans effet, exposer les agrégats utiles (volume, # transactions, # engagements), permettre fusion de doublons et création manuelle, corriger le bug `IGNORED → PENDING` à l'import.

**Architecture :** Backend FastAPI + SQLAlchemy : extension du endpoint list avec agrégats SQL (LEFT JOIN + GROUP BY), nouveaux endpoints `merge-preview`/`merge`/`POST` création, fix dans `services/imports.py`. Frontend React + react-query : refonte complète de `CounterpartiesPage`, nouveau dialog de fusion avec preview, dialog de création, bandeau d'introduction permanent, tooltips contextuels.

**Tech Stack :** FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest, React 18, react-query, TypeScript, Tailwind, composants UI maison.

**Spec source :** `docs/superpowers/specs/2026-05-06-tiers-engagements-refonte-design.md` (sections "Page 1" + cross-cutting doc).

---

## Phase 0 — Cross-cutting foundation

### Task 1 : Règle d'équipe et format documentation

**Files:**
- Modify: `/srv/prod/tools/horizon/CLAUDE.md` (ajouter une section "Doc d'impact")
- Modify: `/srv/prod/tools/horizon/frontend/src/content/documentation.ts` (ajouter le format type `FeatureDoc`)

- [ ] **Step 1: Ajouter la section dans CLAUDE.md**

Ajouter à la fin du fichier `CLAUDE.md` (créer s'il n'existe pas) :

```markdown
## Documentation d'impact obligatoire

Toute nouvelle action UI à effet (création, modification, suppression
d'état, déclenchement d'un workflow) doit livrer dans la même PR :

1. Un bandeau d'introduction permanent sur la page concernée si le concept est nouveau
2. Un tooltip "?" sur l'action elle-même (composant `<HelpTooltip>` ou équivalent), expliquant en une phrase ce qu'elle déclenche
3. Une section dans `frontend/src/content/documentation.ts` au format `FeatureDoc` :
   - "À quoi ça sert" (intention métier)
   - "Ce que ça change quand tu cliques" (effets backend + UI)
   - "Ce que ça ne change pas" (pour casser les fausses intuitions)
   - "Quand l'utiliser" (cas d'usage typiques)

Une PR sans ces trois éléments est incomplète.
```

- [ ] **Step 2: Ajouter le type `FeatureDoc` dans documentation.ts**

Vérifier d'abord la structure existante du fichier puis ajouter en haut :

```ts
export type FeatureDoc = {
  id: string;
  title: string;
  whatItDoes: string;
  whatItChanges: string[];
  whatItDoesNotChange: string[];
  whenToUse: string[];
};
```

Ne pas encore remplir de contenu — sera fait dans les tasks UI dédiées.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md frontend/src/content/documentation.ts
git commit -m "docs: règle d'équipe documentation d'impact + type FeatureDoc"
```

---

## Phase 1 — Backend Tiers

### Task 2 : Fix bug `match_or_create_counterparty` (réutilisation des `IGNORED`)

**Files:**
- Modify: `backend/app/services/imports.py:112-159` (fonction `match_or_create_counterparty`)
- Modify: `backend/tests/test_service_imports_counterparty.py` (ajouter tests)

**Contexte du bug** : la requête actuelle `Counterparty.status != IGNORED` exclut les ignorés, donc l'import recrée un nouveau `pending` alors qu'un ignoré matchant existe déjà. Fix : élargir la query, mais si le match retombe sur un ignoré, le retourner tel quel (sans le réactiver) — la transaction est rattachée mais le tiers reste ignoré.

- [ ] **Step 1: Ajouter le test du fix**

Ajouter à `backend/tests/test_service_imports_counterparty.py` :

```python
def test_match_returns_existing_ignored_does_not_create_duplicate(
    db_session: Session,
) -> None:
    """Un tiers IGNORED matchant doit être réutilisé, pas dupliqué en PENDING."""
    e = _make_entity(db_session)
    ignored = Counterparty(
        entity_id=e.id, name="SPAM SARL", normalized_name="SPAM SARL",
        status=CounterpartyStatus.IGNORED,
    )
    db_session.add(ignored)
    db_session.flush()

    cp, created = match_or_create_counterparty(
        db_session, entity_id=e.id, hint="SPAM SARL"
    )

    assert cp is not None
    assert cp.id == ignored.id
    assert cp.status == CounterpartyStatus.IGNORED  # statut préservé
    assert created is False
    # Aucun doublon créé
    all_cp = db_session.query(Counterparty).filter_by(entity_id=e.id).all()
    assert len(all_cp) == 1
```

- [ ] **Step 2: Lancer le test, vérifier qu'il échoue**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_service_imports_counterparty.py::test_match_returns_existing_ignored_does_not_create_duplicate -xvs
```

Attendu : FAIL — le code crée un nouveau `pending` au lieu de réutiliser l'ignoré.

- [ ] **Step 3: Appliquer le fix**

Dans `backend/app/services/imports.py:134-139`, remplacer :

```python
    existing = session.execute(
        select(Counterparty).where(
            Counterparty.entity_id == entity_id,
            Counterparty.status != CounterpartyStatus.IGNORED,
        )
    ).scalars().all()
```

par :

```python
    existing = session.execute(
        select(Counterparty).where(
            Counterparty.entity_id == entity_id,
        )
    ).scalars().all()
```

Mettre à jour la docstring lignes 118-128 pour refléter le nouveau comportement :

```python
    """Retourne (Counterparty, was_created).

    - (None, False) si hint est vide.
    - (existing, False) si match fuzzy >= 90 % (token_set_ratio) sur
      `normalized_name` parmi TOUTES les contreparties de l'entité, y
      compris les IGNORED. Un match sur IGNORED retourne le tiers tel
      quel (statut préservé, pas de réactivation).
    - (new, True) si aucune correspondance : création auto en statut `pending`.
    """
```

- [ ] **Step 4: Relancer le test, vérifier qu'il passe**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_service_imports_counterparty.py -xvs
```

Attendu : tous les tests passent (les 5 anciens + le nouveau).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/imports.py backend/tests/test_service_imports_counterparty.py
git commit -m "fix(imports): réutiliser les tiers IGNORED au lieu de créer un doublon PENDING"
```

---

### Task 3 : Endpoint GET enrichi avec agrégats

**Files:**
- Modify: `backend/app/schemas/counterparty.py` (nouveau schéma `CounterpartyWithAggregates`)
- Modify: `backend/app/api/counterparties.py` (extension de `list_counterparties`)
- Create: `backend/tests/test_api_counterparties_aggregates.py`

- [ ] **Step 1: Ajouter le schéma de sortie enrichi**

Modifier `backend/app/schemas/counterparty.py` :

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CounterpartyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entity_id: int
    name: str
    status: Literal["pending", "active", "ignored"]


class CounterpartyWithAggregates(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entity_id: int
    name: str
    status: Literal["pending", "active", "ignored"]
    transaction_count: int
    volume_cumulated: float  # somme des |amount| des transactions liées
    last_operation_date: datetime | None
    pending_commitment_count: int


class CounterpartyUpdate(BaseModel):
    status: Literal["active", "ignored"] | None = None
    name: str | None = None


class CounterpartyCreate(BaseModel):
    entity_id: int
    name: str
```

- [ ] **Step 2: Écrire le test du nouveau endpoint**

Créer `backend/tests/test_api_counterparties_aggregates.py` :

```python
"""GET /api/counterparties retourne les agrégats par tiers."""
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.transaction import Transaction


def test_list_counterparties_returns_aggregates(
    client: TestClient,
    db_session: Session,
    auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    entity_id = ba.entity_id

    cp = Counterparty(
        entity_id=entity_id, name="ACME", normalized_name="ACME",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add(cp)
    db_session.flush()

    db_session.add_all([
        Transaction(
            bank_account_id=ba.id, entity_id=entity_id,
            counterparty_id=cp.id,
            operation_date=date(2026, 4, 1),
            label="X", amount=Decimal("100"),
            dedup_key="dk1",
        ),
        Transaction(
            bank_account_id=ba.id, entity_id=entity_id,
            counterparty_id=cp.id,
            operation_date=date(2026, 4, 15),
            label="Y", amount=Decimal("-50"),
            dedup_key="dk2",
        ),
    ])
    db_session.add(Commitment(
        entity_id=entity_id, counterparty_id=cp.id,
        direction=CommitmentDirection.IN,
        amount=Decimal("200"),
        emission_date=date(2026, 4, 1),
        expected_date=date(2026, 5, 1),
        status=CommitmentStatus.PENDING,
    ))
    db_session.commit()

    resp = client.get("/api/counterparties", params={"entity_id": entity_id})
    assert resp.status_code == 200
    body = resp.json()
    row = next(r for r in body if r["id"] == cp.id)
    assert row["transaction_count"] == 2
    assert row["volume_cumulated"] == 150.0  # |100| + |-50|
    assert row["last_operation_date"] is not None
    assert row["pending_commitment_count"] == 1
```

- [ ] **Step 3: Lancer le test, vérifier qu'il échoue**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_api_counterparties_aggregates.py -xvs
```

Attendu : FAIL — le schéma de réponse ne contient pas encore les champs agrégés.

- [ ] **Step 4: Implémenter le endpoint enrichi**

Remplacer `list_counterparties` dans `backend/app/api/counterparties.py` :

```python
from sqlalchemy import select, func, case, and_

from app.models.commitment import Commitment, CommitmentStatus
from app.models.transaction import Transaction
from app.schemas.counterparty import (
    CounterpartyRead,
    CounterpartyUpdate,
    CounterpartyWithAggregates,
)


@router.get("", response_model=list[CounterpartyWithAggregates])
def list_counterparties(
    entity_id: int | None = Query(default=None),
    include_ignored: bool = Query(default=False),
    search: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CounterpartyWithAggregates]:
    accessible = accessible_entity_ids_subquery(session=session, user=user)

    tx_count = func.count(Transaction.id.distinct())
    tx_volume = func.coalesce(func.sum(func.abs(Transaction.amount)), 0)
    tx_last = func.max(Transaction.operation_date)
    pending_commit_count = func.count(
        case((Commitment.status == CommitmentStatus.PENDING, Commitment.id))
    )

    q = (
        select(
            Counterparty.id,
            Counterparty.entity_id,
            Counterparty.name,
            Counterparty.status,
            tx_count.label("transaction_count"),
            tx_volume.label("volume_cumulated"),
            tx_last.label("last_operation_date"),
            pending_commit_count.label("pending_commitment_count"),
        )
        .select_from(Counterparty)
        .outerjoin(Transaction, Transaction.counterparty_id == Counterparty.id)
        .outerjoin(Commitment, Commitment.counterparty_id == Counterparty.id)
        .where(Counterparty.entity_id.in_(accessible))
        .group_by(Counterparty.id)
    )

    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        q = q.where(Counterparty.entity_id == entity_id)
    if not include_ignored:
        q = q.where(Counterparty.status != CounterpartyStatus.IGNORED)
    if search:
        q = q.where(Counterparty.name.ilike(f"%{search}%"))

    q = q.order_by(tx_volume.desc(), Counterparty.name.asc())

    rows = session.execute(q).all()
    return [
        CounterpartyWithAggregates(
            id=r.id, entity_id=r.entity_id, name=r.name, status=r.status.value,
            transaction_count=r.transaction_count,
            volume_cumulated=float(r.volume_cumulated),
            last_operation_date=r.last_operation_date,
            pending_commitment_count=r.pending_commitment_count,
        )
        for r in rows
    ]
```

- [ ] **Step 5: Adapter l'ancien test `test_api_counterparties.py`**

Le test existant `test_list_counterparties_includes_pending` filtrait par `status=pending`. Comme le paramètre `status` est supprimé, remplacer par :

```python
def test_list_counterparties_returns_imported_tiers(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    resp = client.get("/api/counterparties")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert "transaction_count" in body[0]
    assert "volume_cumulated" in body[0]
```

- [ ] **Step 6: Lancer tous les tests counterparties**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_api_counterparties.py tests/test_api_counterparties_aggregates.py -xvs
```

Attendu : tous passent.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/counterparties.py backend/app/schemas/counterparty.py backend/tests/test_api_counterparties.py backend/tests/test_api_counterparties_aggregates.py
git commit -m "feat(api): /api/counterparties retourne agrégats (volume, tx, engagements) + filtre include_ignored"
```

---

### Task 4 : Endpoint POST création manuelle

**Files:**
- Modify: `backend/app/api/counterparties.py` (ajouter route POST)
- Create: `backend/tests/test_api_counterparties_create.py`

- [ ] **Step 1: Écrire le test**

Créer `backend/tests/test_api_counterparties_create.py` :

```python
"""POST /api/counterparties création manuelle."""
from fastapi.testclient import TestClient


def test_create_counterparty_manual(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    entity_id = auth_user_with_bank_account["bank_account"].entity_id
    resp = client.post(
        "/api/counterparties",
        json={"entity_id": entity_id, "name": "Manual Tier SAS"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Manual Tier SAS"
    assert body["status"] == "active"


def test_create_counterparty_rejects_duplicate_normalized_name(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    entity_id = auth_user_with_bank_account["bank_account"].entity_id
    client.post(
        "/api/counterparties",
        json={"entity_id": entity_id, "name": "ACME SAS"},
    )
    resp = client.post(
        "/api/counterparties",
        json={"entity_id": entity_id, "name": "ACME S.A.S."},  # même normalized
    )
    assert resp.status_code == 409
```

- [ ] **Step 2: Vérifier l'échec**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_api_counterparties_create.py -xvs
```

Attendu : FAIL (404 — route inexistante).

- [ ] **Step 3: Implémenter la route**

Ajouter à `backend/app/api/counterparties.py` :

```python
from fastapi import status as http_status
from sqlalchemy.exc import IntegrityError

from app.schemas.counterparty import CounterpartyCreate
from app.services.imports import _normalize_counterparty_name


@router.post(
    "",
    response_model=CounterpartyRead,
    status_code=http_status.HTTP_201_CREATED,
)
def create_counterparty(
    payload: CounterpartyCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CounterpartyRead:
    require_entity_access(session=session, user=user, entity_id=payload.entity_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom requis")
    cp = Counterparty(
        entity_id=payload.entity_id,
        name=name,
        normalized_name=_normalize_counterparty_name(name),
        status=CounterpartyStatus.ACTIVE,
    )
    session.add(cp)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Un tiers avec ce nom existe déjà"
        )
    record_audit(
        session, user=user, action="create", entity=cp,
        before=None, after=to_dict_for_audit(cp), request=request,
    )
    session.commit()
    session.refresh(cp)
    return CounterpartyRead.model_validate(cp)
```

- [ ] **Step 4: Vérifier le passage**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_api_counterparties_create.py -xvs
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/counterparties.py backend/tests/test_api_counterparties_create.py
git commit -m "feat(api): POST /api/counterparties création manuelle d'un tiers"
```

---

### Task 5 : Endpoint preview de fusion

**Files:**
- Create: `backend/app/services/counterparty_merge.py`
- Modify: `backend/app/schemas/counterparty.py` (ajouter `MergePreview`)
- Modify: `backend/app/api/counterparties.py` (route GET preview)
- Create: `backend/tests/test_service_counterparty_merge.py`

- [ ] **Step 1: Ajouter les schémas Pydantic**

Ajouter à `backend/app/schemas/counterparty.py` :

```python
class MergeImpactRule(BaseModel):
    id: int
    label: str | None
    category_id: int | None


class MergeImpactCommitment(BaseModel):
    id: int
    direction: Literal["in", "out"]
    amount: float
    expected_date: str  # ISO date


class CounterpartyMergePreview(BaseModel):
    source_id: int
    source_name: str
    target_id: int
    target_name: str
    transaction_count: int
    forecast_entry_count: int
    rules: list[MergeImpactRule]
    commitments: list[MergeImpactCommitment]
```

- [ ] **Step 2: Écrire le test du service**

Créer `backend/tests/test_service_counterparty_merge.py` :

```python
"""Service de fusion de contreparties — preview et exécution."""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.models.transaction import Transaction
from app.services.counterparty_merge import build_merge_preview, execute_merge


def _entity(session: Session) -> Entity:
    e = Entity(name="E", legal_name="E SARL")
    session.add(e); session.flush(); return e


def _cp(session, e, name, status=CounterpartyStatus.ACTIVE):
    cp = Counterparty(
        entity_id=e.id, name=name, normalized_name=name.upper(), status=status,
    )
    session.add(cp); session.flush(); return cp


def test_preview_counts_impacted_rows(db_session: Session, auth_user_with_bank_account) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    src = Counterparty(
        entity_id=e_id, name="CARREFOUR", normalized_name="CARREFOUR",
        status=CounterpartyStatus.ACTIVE,
    )
    tgt = Counterparty(
        entity_id=e_id, name="Carrefour Proxi", normalized_name="CARREFOUR PROXI",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add_all([src, tgt]); db_session.flush()

    db_session.add(Transaction(
        bank_account_id=ba.id, entity_id=e_id, counterparty_id=src.id,
        operation_date=date(2026, 4, 1), label="X", amount=Decimal("10"),
        dedup_key="dk1",
    ))
    db_session.add(Commitment(
        entity_id=e_id, counterparty_id=src.id,
        direction=CommitmentDirection.OUT, amount=Decimal("100"),
        emission_date=date(2026, 4, 1), expected_date=date(2026, 5, 1),
        status=CommitmentStatus.PENDING,
    ))
    db_session.commit()

    preview = build_merge_preview(db_session, source_id=src.id, target_id=tgt.id)
    assert preview.source_id == src.id
    assert preview.target_id == tgt.id
    assert preview.transaction_count == 1
    assert len(preview.commitments) == 1


def test_execute_merge_reattaches_and_deletes_source(
    db_session: Session, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    src = Counterparty(
        entity_id=e_id, name="A", normalized_name="A",
        status=CounterpartyStatus.ACTIVE,
    )
    tgt = Counterparty(
        entity_id=e_id, name="B", normalized_name="B",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add_all([src, tgt]); db_session.flush()
    db_session.add(Transaction(
        bank_account_id=ba.id, entity_id=e_id, counterparty_id=src.id,
        operation_date=date(2026, 4, 1), label="X", amount=Decimal("10"),
        dedup_key="dk1",
    ))
    db_session.commit()

    execute_merge(db_session, source_id=src.id, target_id=tgt.id)
    db_session.commit()

    assert db_session.get(Counterparty, src.id) is None
    tgt_txs = db_session.query(Transaction).filter_by(counterparty_id=tgt.id).count()
    assert tgt_txs == 1


def test_execute_merge_rejects_cross_entity(
    db_session: Session, auth_user_with_bank_account,
) -> None:
    e1 = auth_user_with_bank_account["bank_account"].entity_id
    e2 = _entity(db_session).id
    src = _cp(db_session, type("X", (), {"id": e1})(), "A")
    tgt = _cp(db_session, type("X", (), {"id": e2})(), "B")
    db_session.commit()
    with pytest.raises(ValueError, match="entity"):
        execute_merge(db_session, source_id=src.id, target_id=tgt.id)
```

- [ ] **Step 3: Implémenter le service**

Créer `backend/app/services/counterparty_merge.py` :

```python
"""Fusion de contreparties : réattache transactions, engagements, règles, forecast entries."""
from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule
from app.models.commitment import Commitment
from app.models.counterparty import Counterparty
from app.models.forecast_entry import ForecastEntry
from app.models.transaction import Transaction
from app.schemas.counterparty import (
    CounterpartyMergePreview,
    MergeImpactCommitment,
    MergeImpactRule,
)


def _get_pair(session: Session, source_id: int, target_id: int) -> tuple[Counterparty, Counterparty]:
    src = session.get(Counterparty, source_id)
    tgt = session.get(Counterparty, target_id)
    if src is None or tgt is None:
        raise ValueError("source ou cible introuvable")
    if src.entity_id != tgt.entity_id:
        raise ValueError("fusion impossible entre entity différentes")
    if src.id == tgt.id:
        raise ValueError("source et cible identiques")
    return src, tgt


def build_merge_preview(
    session: Session, *, source_id: int, target_id: int,
) -> CounterpartyMergePreview:
    src, tgt = _get_pair(session, source_id, target_id)

    tx_count = session.query(Transaction).filter_by(counterparty_id=src.id).count()
    fe_count = session.query(ForecastEntry).filter_by(counterparty_id=src.id).count()

    rules = (
        session.query(CategorizationRule)
        .filter_by(counterparty_id=src.id)
        .all()
    )
    commitments = (
        session.query(Commitment).filter_by(counterparty_id=src.id).all()
    )

    return CounterpartyMergePreview(
        source_id=src.id, source_name=src.name,
        target_id=tgt.id, target_name=tgt.name,
        transaction_count=tx_count,
        forecast_entry_count=fe_count,
        rules=[
            MergeImpactRule(id=r.id, label=getattr(r, "label", None),
                            category_id=getattr(r, "category_id", None))
            for r in rules
        ],
        commitments=[
            MergeImpactCommitment(
                id=c.id, direction=c.direction.value,
                amount=float(c.amount),
                expected_date=c.expected_date.isoformat(),
            )
            for c in commitments
        ],
    )


def execute_merge(session: Session, *, source_id: int, target_id: int) -> None:
    """Réattache toutes les FK source → target puis supprime source. Atomique."""
    src, tgt = _get_pair(session, source_id, target_id)

    session.execute(
        update(Transaction)
        .where(Transaction.counterparty_id == src.id)
        .values(counterparty_id=tgt.id)
    )
    session.execute(
        update(Commitment)
        .where(Commitment.counterparty_id == src.id)
        .values(counterparty_id=tgt.id)
    )
    session.execute(
        update(CategorizationRule)
        .where(CategorizationRule.counterparty_id == src.id)
        .values(counterparty_id=tgt.id)
    )
    session.execute(
        update(ForecastEntry)
        .where(ForecastEntry.counterparty_id == src.id)
        .values(counterparty_id=tgt.id)
    )
    session.delete(src)
    session.flush()
```

- [ ] **Step 4: Lancer les tests du service**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_service_counterparty_merge.py -xvs
```

Attendu : PASS.

- [ ] **Step 5: Ajouter la route preview**

Ajouter à `backend/app/api/counterparties.py` :

```python
from app.schemas.counterparty import CounterpartyMergePreview
from app.services.counterparty_merge import build_merge_preview, execute_merge


@router.get("/{counterparty_id}/merge-preview", response_model=CounterpartyMergePreview)
def merge_preview(
    counterparty_id: int,
    target_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CounterpartyMergePreview:
    src = session.get(Counterparty, counterparty_id)
    if src is None:
        raise HTTPException(status_code=404, detail="Source introuvable")
    require_entity_access(session=session, user=user, entity_id=src.entity_id)
    try:
        return build_merge_preview(
            session, source_id=counterparty_id, target_id=target_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

- [ ] **Step 6: Test API rapide du preview**

Ajouter à `backend/tests/test_service_counterparty_merge.py` un test d'API :

```python
def test_api_merge_preview_endpoint(
    client, db_session: Session, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    src = Counterparty(entity_id=e_id, name="A", normalized_name="A",
                       status=CounterpartyStatus.ACTIVE)
    tgt = Counterparty(entity_id=e_id, name="B", normalized_name="B",
                       status=CounterpartyStatus.ACTIVE)
    db_session.add_all([src, tgt]); db_session.commit()

    resp = client.get(
        f"/api/counterparties/{src.id}/merge-preview",
        params={"target_id": tgt.id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source_id"] == src.id
    assert body["target_id"] == tgt.id
```

- [ ] **Step 7: Lancer et commit**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_service_counterparty_merge.py -xvs
```

```bash
git add backend/app/services/counterparty_merge.py backend/app/schemas/counterparty.py backend/app/api/counterparties.py backend/tests/test_service_counterparty_merge.py
git commit -m "feat(counterparties): service merge + endpoint preview"
```

---

### Task 6 : Endpoint POST merge (exécution)

**Files:**
- Modify: `backend/app/api/counterparties.py` (route POST merge)
- Modify: `backend/tests/test_service_counterparty_merge.py` (test API exec)

- [ ] **Step 1: Écrire le test API**

Ajouter à `backend/tests/test_service_counterparty_merge.py` :

```python
def test_api_merge_execute_endpoint(
    client, db_session: Session, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    src = Counterparty(entity_id=e_id, name="A", normalized_name="A",
                       status=CounterpartyStatus.ACTIVE)
    tgt = Counterparty(entity_id=e_id, name="B", normalized_name="B",
                       status=CounterpartyStatus.ACTIVE)
    db_session.add_all([src, tgt]); db_session.flush()
    db_session.add(Transaction(
        bank_account_id=ba.id, entity_id=e_id, counterparty_id=src.id,
        operation_date=date(2026, 4, 1), label="X",
        amount=Decimal("10"), dedup_key="dk1",
    ))
    db_session.commit()
    src_id = src.id

    resp = client.post(
        f"/api/counterparties/{src.id}/merge",
        json={"target_id": tgt.id},
    )
    assert resp.status_code == 204
    assert db_session.get(Counterparty, src_id) is None
    assert db_session.query(Transaction).filter_by(counterparty_id=tgt.id).count() == 1
```

- [ ] **Step 2: Vérifier l'échec**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_service_counterparty_merge.py::test_api_merge_execute_endpoint -xvs
```

Attendu : FAIL (route 404).

- [ ] **Step 3: Implémenter la route**

Ajouter à `backend/app/api/counterparties.py` :

```python
from pydantic import BaseModel


class MergeRequest(BaseModel):
    target_id: int


@router.post(
    "/{counterparty_id}/merge",
    status_code=http_status.HTTP_204_NO_CONTENT,
)
def merge_counterparty(
    counterparty_id: int,
    payload: MergeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    src = session.get(Counterparty, counterparty_id)
    if src is None:
        raise HTTPException(status_code=404, detail="Source introuvable")
    require_entity_access(session=session, user=user, entity_id=src.entity_id)
    before = to_dict_for_audit(src)
    try:
        execute_merge(session, source_id=counterparty_id, target_id=payload.target_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record_audit(
        session, user=user, action="merge", entity=src,
        before=before,
        after={"merged_into": payload.target_id},
        request=request,
    )
    session.commit()
```

- [ ] **Step 4: Lancer le test**

```bash
cd /srv/prod/tools/horizon/backend && pytest tests/test_service_counterparty_merge.py -xvs
```

Attendu : tous PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/counterparties.py backend/tests/test_service_counterparty_merge.py
git commit -m "feat(api): POST /api/counterparties/{id}/merge exécute la fusion"
```

---

## Phase 2 — Frontend Tiers

### Task 7 : Update API client

**Files:**
- Modify: `frontend/src/api/counterparties.ts`
- Modify: `frontend/src/types/api.ts` (étendre `Counterparty`)

- [ ] **Step 1: Étendre les types**

Repérer dans `frontend/src/types/api.ts` le type `Counterparty` existant et l'étendre :

```ts
export type Counterparty = {
  id: number;
  entity_id: number;
  name: string;
  status: "pending" | "active" | "ignored";
};

export type CounterpartyWithAggregates = Counterparty & {
  transaction_count: number;
  volume_cumulated: number;
  last_operation_date: string | null;
  pending_commitment_count: number;
};

export type MergePreview = {
  source_id: number;
  source_name: string;
  target_id: number;
  target_name: string;
  transaction_count: number;
  forecast_entry_count: number;
  rules: { id: number; label: string | null; category_id: number | null }[];
  commitments: {
    id: number;
    direction: "in" | "out";
    amount: number;
    expected_date: string;
  }[];
};
```

- [ ] **Step 2: Refondre `frontend/src/api/counterparties.ts`**

Remplacer entièrement le fichier :

```ts
import { useQuery } from "@tanstack/react-query";
import type { CounterpartyWithAggregates, MergePreview } from "../types/api";

export type ListParams = {
  entityId?: number | null;
  includeIgnored?: boolean;
  search?: string;
};

export async function fetchCounterparties(
  args: ListParams = {},
): Promise<CounterpartyWithAggregates[]> {
  const params = new URLSearchParams();
  if (args.entityId != null) params.set("entity_id", String(args.entityId));
  if (args.includeIgnored) params.set("include_ignored", "true");
  if (args.search) params.set("search", args.search);
  const qs = params.toString() ? `?${params}` : "";
  const resp = await fetch(`/api/counterparties${qs}`, { credentials: "include" });
  if (!resp.ok) throw new Error(`GET /api/counterparties → ${resp.status}`);
  return resp.json();
}

export async function updateCounterparty(
  id: number,
  patch: { status?: "active" | "ignored"; name?: string },
): Promise<CounterpartyWithAggregates> {
  const resp = await fetch(`/api/counterparties/${id}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!resp.ok) throw new Error(`PATCH → ${resp.status}`);
  return resp.json();
}

export async function createCounterparty(
  payload: { entity_id: number; name: string },
): Promise<CounterpartyWithAggregates> {
  const resp = await fetch(`/api/counterparties`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`POST /api/counterparties → ${resp.status} ${txt}`);
  }
  return resp.json();
}

export async function fetchMergePreview(
  sourceId: number, targetId: number,
): Promise<MergePreview> {
  const resp = await fetch(
    `/api/counterparties/${sourceId}/merge-preview?target_id=${targetId}`,
    { credentials: "include" },
  );
  if (!resp.ok) throw new Error(`merge-preview → ${resp.status}`);
  return resp.json();
}

export async function executeMerge(
  sourceId: number, targetId: number,
): Promise<void> {
  const resp = await fetch(`/api/counterparties/${sourceId}/merge`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_id: targetId }),
  });
  if (!resp.ok) throw new Error(`merge → ${resp.status}`);
}

export function useCounterparties(filters: ListParams = {}) {
  return useQuery({
    queryKey: ["counterparties", filters],
    queryFn: () => fetchCounterparties(filters),
  });
}
```

- [ ] **Step 3: Vérifier le typecheck**

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit
```

Attendu : peut échouer sur `CounterpartiesPage.tsx` (qui utilise encore l'ancien shape) — c'est normal, on le refera Task 8. Vérifier que les autres fichiers compilent.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/counterparties.ts frontend/src/types/api.ts
git commit -m "feat(frontend/api): client counterparties enrichi (agrégats, fusion, création)"
```

---

### Task 8 : Refonte CounterpartiesPage (liste enrichie)

**Files:**
- Modify: `frontend/src/pages/CounterpartiesPage.tsx` (réécriture complète)
- Rename in nav: `frontend/src/components/Sidebar.tsx:109` (label "Tiers" → "Clients & fournisseurs")

- [ ] **Step 1: Renommer dans la sidebar**

Modifier `frontend/src/components/Sidebar.tsx:109` :

```tsx
    label: 'Clients & fournisseurs',
```

(Conserver la route `/counterparties` pour ne pas casser les liens existants.)

- [ ] **Step 2: Réécrire CounterpartiesPage**

Remplacer entièrement `frontend/src/pages/CounterpartiesPage.tsx` :

```tsx
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchCounterparties,
  updateCounterparty,
} from "../api/counterparties";
import { Button } from "@/components/ui/button";
import { useEntityFilter } from "../stores/entityFilter";
import { EntitySelector } from "@/components/EntitySelector";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { CounterpartyMergeDialog } from "@/components/CounterpartyMergeDialog";
import { CounterpartyCreateDialog } from "@/components/CounterpartyCreateDialog";
import type { CounterpartyWithAggregates } from "../types/api";

const fmtEur = (n: number) =>
  new Intl.NumberFormat("fr-FR", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(n);

const fmtDate = (iso: string | null) =>
  iso ? new Intl.DateTimeFormat("fr-FR").format(new Date(iso)) : "—";

export function CounterpartiesPage() {
  const qc = useQueryClient();
  const entityId = useEntityFilter((s) => s.entityId);
  const [search, setSearch] = useState("");
  const [includeIgnored, setIncludeIgnored] = useState(false);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [mergeSource, setMergeSource] = useState<CounterpartyWithAggregates | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [confirmIgnore, setConfirmIgnore] =
    useState<CounterpartyWithAggregates | null>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: ["counterparties", { entityId, includeIgnored, search }],
    queryFn: () =>
      fetchCounterparties({ entityId, includeIgnored, search: search.trim() || undefined }),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: { status?: "active" | "ignored"; name?: string } }) =>
      updateCounterparty(id, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["counterparties"] }),
  });

  const visible = useMemo(() => data, [data]);

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Clients & fournisseurs
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Tiers détectés à partir de tes imports bancaires.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <EntitySelector />
          <Button onClick={() => setCreateOpen(true)}>Nouveau tiers</Button>
        </div>
      </div>

      {/* Bandeau d'introduction permanent */}
      <div className="rounded-xl border border-line-soft bg-panel-2 p-4 text-[13px] text-muted-foreground">
        <strong className="text-ink">À quoi ça sert.</strong>{" "}
        Cette page liste tous les tiers (clients, fournisseurs, salariés…)
        détectés à partir de tes imports bancaires. Tu peux les renommer,
        fusionner les doublons, et ignorer ceux qui polluent les sélecteurs.
        Pour voir les opérations d'un tiers, clique sur son nom.
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher un tiers…"
          className="flex-1 min-w-[220px] rounded-md border border-line-soft bg-panel px-3 py-2 text-[13px]"
        />
        <label className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <input
            type="checkbox"
            checked={includeIgnored}
            onChange={(e) => setIncludeIgnored(e.target.checked)}
          />
          Inclure les tiers ignorés
        </label>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement…
        </div>
      ) : visible.length === 0 ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          {search
            ? `Aucun résultat pour "${search}".`
            : "Aucun tiers. Les tiers sont créés automatiquement à chaque import bancaire. Tu peux aussi en créer un manuellement."}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-2.5 text-left">Nom</th>
                <th className="px-4 py-2.5 text-right">Volume cumulé</th>
                <th className="px-4 py-2.5 text-right"># Tx</th>
                <th className="px-4 py-2.5 text-left">Dernière opé</th>
                <th className="px-4 py-2.5 text-right">Engagts en cours</th>
                <th className="px-4 py-2.5 text-left">Statut</th>
                <th className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((cp) => (
                <tr
                  key={cp.id}
                  className="border-b border-line-soft transition-colors hover:bg-panel-2"
                >
                  <td className="px-4 py-3 text-[13px]">
                    {renamingId === cp.id ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => {
                          if (renameValue.trim() && renameValue !== cp.name) {
                            updateMut.mutate({ id: cp.id, patch: { name: renameValue.trim() } });
                          }
                          setRenamingId(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        className="w-full rounded-md border border-line-soft bg-panel px-2 py-1 text-[13px]"
                      />
                    ) : (
                      <a
                        href={`/transactions?counterparty=${cp.id}`}
                        className="font-medium text-ink hover:underline"
                      >
                        {cp.name}
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-[13px] tabular-nums">
                    {fmtEur(cp.volume_cumulated)}
                  </td>
                  <td className="px-4 py-3 text-right text-[13px] tabular-nums">
                    {cp.transaction_count}
                  </td>
                  <td className="px-4 py-3 text-[13px] text-muted-foreground">
                    {fmtDate(cp.last_operation_date)}
                  </td>
                  <td className="px-4 py-3 text-right text-[13px] tabular-nums">
                    {cp.pending_commitment_count}
                  </td>
                  <td className="px-4 py-3 text-[13px]">
                    {cp.status === "ignored" ? (
                      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-amber-700 text-[11px]">
                        Ignoré
                      </span>
                    ) : (
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700 text-[11px]">
                        Actif
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setRenamingId(cp.id);
                          setRenameValue(cp.name);
                        }}
                      >
                        Renommer
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setMergeSource(cp)}
                      >
                        Fusionner…
                      </Button>
                      {cp.status === "ignored" ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            updateMut.mutate({ id: cp.id, patch: { status: "active" } })
                          }
                          title="Réactive ce tiers : il réapparaît dans les sélecteurs et la détection de récurrence."
                        >
                          Réactiver
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setConfirmIgnore(cp)}
                          title="Le tiers reste en base mais disparaît des sélecteurs et des prédictions de récurrence. Pour un tiers récurrent, mieux vaut le renommer."
                        >
                          Ignorer
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createOpen && (
        <CounterpartyCreateDialog
          entityId={entityId}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            qc.invalidateQueries({ queryKey: ["counterparties"] });
            setCreateOpen(false);
          }}
        />
      )}

      {mergeSource && (
        <CounterpartyMergeDialog
          source={mergeSource}
          allCounterparties={visible}
          onClose={() => setMergeSource(null)}
          onMerged={() => {
            qc.invalidateQueries({ queryKey: ["counterparties"] });
            setMergeSource(null);
          }}
        />
      )}

      {confirmIgnore && (
        <ConfirmDialog
          title="Ignorer ce tiers ?"
          description={
            `"${confirmIgnore.name}" sera masqué des sélecteurs et exclu des prédictions ` +
            `de récurrence du prévisionnel. Les transactions liées restent visibles. ` +
            `Pour un tiers récurrent, préfère le renommer.`
          }
          confirmLabel="Ignorer"
          onCancel={() => setConfirmIgnore(null)}
          onConfirm={() => {
            updateMut.mutate({ id: confirmIgnore.id, patch: { status: "ignored" } });
            setConfirmIgnore(null);
          }}
        />
      )}
    </section>
  );
}
```

- [ ] **Step 3: Vérifier le typecheck (sera vert après tasks 9 et 10 qui créent les composants manquants)**

Pour cette task, on tolère les imports non résolus de `CounterpartyMergeDialog` et `CounterpartyCreateDialog` qui seront créés ensuite. Lancer :

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit 2>&1 | grep -v "CounterpartyMergeDialog\|CounterpartyCreateDialog"
```

Attendu : pas d'autres erreurs.

- [ ] **Step 4: Commit (incluant le placeholder pour les composants manquants)**

```bash
git add frontend/src/components/Sidebar.tsx frontend/src/pages/CounterpartiesPage.tsx
git commit -m "feat(tiers): refonte page liste — agrégats, recherche, filtre ignorés, action rename"
```

---

### Task 9 : Composant `CounterpartyMergeDialog`

**Files:**
- Create: `frontend/src/components/CounterpartyMergeDialog.tsx`

- [ ] **Step 1: Créer le composant**

Créer `frontend/src/components/CounterpartyMergeDialog.tsx` :

```tsx
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { fetchMergePreview, executeMerge } from "../api/counterparties";
import type { CounterpartyWithAggregates, MergePreview } from "../types/api";

type Props = {
  source: CounterpartyWithAggregates;
  allCounterparties: CounterpartyWithAggregates[];
  onClose: () => void;
  onMerged: () => void;
};

export function CounterpartyMergeDialog({
  source, allCounterparties, onClose, onMerged,
}: Props) {
  const [targetId, setTargetId] = useState<number | null>(null);

  const candidates = allCounterparties.filter(
    (cp) => cp.id !== source.id && cp.entity_id === source.entity_id,
  );

  const previewQ = useQuery<MergePreview>({
    queryKey: ["merge-preview", source.id, targetId],
    queryFn: () => fetchMergePreview(source.id, targetId!),
    enabled: targetId != null,
  });

  const mergeMut = useMutation({
    mutationFn: () => executeMerge(source.id, targetId!),
    onSuccess: () => onMerged(),
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-[560px] max-w-[90vw] rounded-xl bg-panel p-6 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-[16px] font-semibold text-ink">
          Fusionner "{source.name}" vers…
        </h2>
        <p className="mt-1 text-[12px] text-muted-foreground">
          Toutes les transactions, engagements, règles et lignes de prévisionnel
          seront réattachés au tiers cible. Le tiers source sera supprimé.
          <strong className="text-ink"> Action irréversible.</strong>
        </p>

        <div className="mt-4">
          <label className="block text-[12px] font-medium text-ink">
            Tiers cible
          </label>
          <select
            value={targetId ?? ""}
            onChange={(e) => setTargetId(e.target.value ? Number(e.target.value) : null)}
            className="mt-1 w-full rounded-md border border-line-soft bg-panel px-3 py-2 text-[13px]"
          >
            <option value="">— Choisir —</option>
            {candidates.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.transaction_count} tx)
              </option>
            ))}
          </select>
        </div>

        {targetId != null && previewQ.data && (
          <div className="mt-4 rounded-md border border-line-soft bg-panel-2 p-3 text-[13px]">
            <p className="font-medium text-ink">Récapitulatif :</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              <li>{previewQ.data.transaction_count} transaction(s) réattachée(s)</li>
              <li>{previewQ.data.commitments.length} engagement(s) réattaché(s)</li>
              <li>{previewQ.data.rules.length} règle(s) de catégorisation mise(s) à jour</li>
              <li>{previewQ.data.forecast_entry_count} ligne(s) de prévisionnel mise(s) à jour</li>
            </ul>
            {previewQ.data.commitments.length > 0 && (
              <details className="mt-3">
                <summary className="cursor-pointer text-[12px] text-ink">
                  Détail des engagements
                </summary>
                <ul className="mt-2 space-y-1 text-[12px] text-muted-foreground">
                  {previewQ.data.commitments.map((c) => (
                    <li key={c.id}>
                      #{c.id} · {c.direction === "in" ? "à encaisser" : "à payer"}{" "}
                      {c.amount}€ · prévu {c.expected_date}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}

        {mergeMut.isError && (
          <p className="mt-3 text-[12px] text-red-600">
            Échec de la fusion. Réessaie ou vérifie les permissions.
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Annuler
          </Button>
          <Button
            disabled={targetId == null || previewQ.isLoading || mergeMut.isPending}
            onClick={() => mergeMut.mutate()}
          >
            {mergeMut.isPending ? "Fusion en cours…" : "Confirmer la fusion"}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Vérifier le typecheck**

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit 2>&1 | grep "CounterpartyMergeDialog"
```

Attendu : aucune erreur sur `CounterpartyMergeDialog`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CounterpartyMergeDialog.tsx
git commit -m "feat(tiers): dialog fusion avec preview de l'impact"
```

---

### Task 10 : Composant `CounterpartyCreateDialog` + section documentation

**Files:**
- Create: `frontend/src/components/CounterpartyCreateDialog.tsx`
- Modify: `frontend/src/content/documentation.ts` (section Clients & fournisseurs)

- [ ] **Step 1: Créer le dialog de création**

Créer `frontend/src/components/CounterpartyCreateDialog.tsx` :

```tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { createCounterparty } from "../api/counterparties";

type Props = {
  entityId: number | null;
  onClose: () => void;
  onCreated: () => void;
};

export function CounterpartyCreateDialog({ entityId, onClose, onCreated }: Props) {
  const [name, setName] = useState("");

  const mut = useMutation({
    mutationFn: () => {
      if (entityId == null) throw new Error("Entité requise");
      return createCounterparty({ entity_id: entityId, name: name.trim() });
    },
    onSuccess: () => onCreated(),
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-[440px] max-w-[90vw] rounded-xl bg-panel p-6 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-[16px] font-semibold text-ink">Nouveau tiers</h2>
        <p className="mt-1 text-[12px] text-muted-foreground">
          Crée manuellement un client ou fournisseur. Utile pour préparer un
          tiers avant le premier import.
        </p>

        {entityId == null && (
          <p className="mt-3 text-[12px] text-amber-700">
            Sélectionne d'abord une entité dans le sélecteur en haut de la page.
          </p>
        )}

        <div className="mt-4">
          <label className="block text-[12px] font-medium text-ink">Nom</label>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-md border border-line-soft bg-panel px-3 py-2 text-[13px]"
            placeholder="Ex : Carrefour Proxi 75011"
          />
        </div>

        {mut.isError && (
          <p className="mt-3 text-[12px] text-red-600">
            {(mut.error as Error)?.message?.includes("409")
              ? "Un tiers avec ce nom existe déjà."
              : "Échec de la création."}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Annuler</Button>
          <Button
            disabled={!name.trim() || entityId == null || mut.isPending}
            onClick={() => mut.mutate()}
          >
            {mut.isPending ? "Création…" : "Créer"}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Ajouter la section dans `documentation.ts`**

Repérer la section "Tiers" existante dans `frontend/src/content/documentation.ts` et la remplacer par :

```ts
// Section "Clients & fournisseurs" — format FeatureDoc imposé
{
  id: "clients-fournisseurs",
  title: "Clients & fournisseurs",
  whatItDoes:
    "Cette page liste tous les tiers détectés dans tes imports bancaires (clients, fournisseurs, salariés, organismes). C'est ton annuaire de référence pour piloter ta trésorerie.",
  whatItChanges: [
    "Renommer un tiers : met à jour son nom dans toute l'application (transactions, engagements, règles).",
    "Fusionner deux tiers : réattache automatiquement toutes les transactions, engagements, règles et lignes de prévisionnel vers le tiers cible, puis supprime le tiers source. Action irréversible.",
    "Ignorer un tiers : il disparaît des sélecteurs (formulaires d'engagement, règles) et des prédictions de récurrence du prévisionnel. Les transactions liées restent visibles.",
    "Réactiver un tiers ignoré : il réapparaît dans les sélecteurs et la détection de récurrence.",
    "Créer un tiers manuellement : utile pour préparer un client/fournisseur avant le premier import.",
  ],
  whatItDoesNotChange: [
    "Ignorer un tiers ne supprime PAS les transactions liées : elles restent visibles dans la page Transactions et comptent toujours dans le dashboard et les analyses.",
    "Le statut d'un tiers (Actif/Ignoré) n'influence PAS la catégorisation par règles : les règles continuent de s'appliquer.",
    "Le statut n'influence PAS le matching d'engagements : un engagement créé peut viser un tiers actif comme ignoré.",
  ],
  whenToUse: [
    "Après un import : vérifier que les nouveaux tiers détectés ont des noms propres, fusionner les doublons typographiques (CARREFOUR vs Carrefour Proxi).",
    "Quand un libellé bancaire pourri non récurrent pollue les sélecteurs : Ignorer.",
    "Quand deux tiers représentent la même entité réelle : Fusionner.",
    "Avant un premier import sur une nouvelle entité : créer manuellement les principaux tiers attendus.",
  ],
},
```

(Si la structure existante du fichier diffère, intégrer la section au bon endroit selon le format en place. La forme des autres sections reste prioritaire ; ce contenu est la matière à incorporer.)

- [ ] **Step 3: Vérifier le rendu front complet**

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit
```

Attendu : aucune erreur.

```bash
cd /srv/prod/tools/horizon && docker compose -f docker-compose.prod.yml restart horizon-frontend horizon-backend
```

Puis ouvrir l'app dans un navigateur, naviguer sur "Clients & fournisseurs", vérifier :
- Le bandeau d'introduction s'affiche
- Le bouton "Nouveau tiers" ouvre le dialog
- La recherche filtre la liste
- La case "Inclure les ignorés" change la liste
- Renommer en cliquant sur "Renommer" puis Entrée fonctionne
- "Fusionner…" ouvre le dialog avec preview
- "Ignorer" ouvre la confirmation et bascule le statut
- La page Aide affiche la nouvelle section "Clients & fournisseurs"

- [ ] **Step 4: Commit final**

```bash
git add frontend/src/components/CounterpartyCreateDialog.tsx frontend/src/content/documentation.ts
git commit -m "feat(tiers): dialog création + section documentation au format FeatureDoc"
```

---

## Self-review (à effectuer avant exécution)

Vérifications inline du plan vs spec :

- [x] Suppression onglet "À valider" : Task 8 (réécriture sans `tab` state)
- [x] Suppression onglet "Ignorés" remplacé par filtre : Task 8 (case `includeIgnored`)
- [x] Renommage nav : Task 8 step 1
- [x] Liste enrichie (volume, # tx, dernière opé, # engagements) : Task 3 + Task 8 colonnes
- [x] Renommer inline : Task 8
- [x] Fusion avec preview : Task 5 + Task 9
- [x] Création manuelle : Task 4 + Task 10
- [x] Fix bug IGNORED → PENDING : Task 2
- [x] Bandeau d'introduction permanent : Task 8
- [x] Tooltips sur Ignorer/Réactiver : Task 8 (attribut `title` ; à upgrader en composant `<HelpTooltip>` quand celui-ci sera créé pour Plan B)
- [x] Section documentation.ts : Task 10
- [x] Règle d'équipe CLAUDE.md + type FeatureDoc : Task 1
- [x] Recherche + filtre : Task 8
- [x] Lien "Voir les transactions" : Task 8 (ancre `/transactions?counterparty=ID` — vérifier que la page Transactions accepte ce paramètre, sinon Plan B ajoutera le support)

**Type cohérence vérifiée :** `CounterpartyWithAggregates` utilisé identiquement dans `types/api.ts`, `api/counterparties.ts`, `pages/CounterpartiesPage.tsx`, `components/CounterpartyMergeDialog.tsx`. `MergePreview` idem.

**Pas de placeholders détectés.**

## Hors scope (rappel)

- Tooltip composant `<HelpTooltip>` formel (utilise `title` HTML pour V1, à upgrader quand Plan B introduira le composant)
- Page Engagements : Plan B
- Multi-types de tiers (client / fournisseur / salarié distincts)
- Page admin dédiée
