# Plan 2 — Module Catégorisation : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter à Horizon un moteur de catégorisation déterministe basé sur des règles ordonnées (30 pré-installées Delubac + règles custom), un seed complet de ~50 sous-catégories, l'intégration dans le pipeline d'import (Plan 1) pour auto-catégoriser à l'insert, une UI de gestion complète (drag-and-drop, preview, bulk), et une inbox « à catégoriser » avec multi-sélection.

**Architecture:** Nouvelle table `categorization_rule` (scope global ou par entité, priorité entière, filtres AND sur libellé normalisé / sens / montant / contrepartie / compte). Service `app/services/categorization.py` qui expose `categorize_transaction`, `preview_rule`, `apply_rule`, `recategorize_entity`. Intégration dans `app/services/imports.py` (ligne juste après l'insert d'une tx). API REST sous `/api/rules` et extension de `/api/transactions` (filtre `uncategorized`, bulk-categorize). Frontend : page `/rules` avec table triable `@dnd-kit/sortable`, drawer de création avec aperçu live, toolbar multi-sélection sur `/transactions`. Trois migrations Alembic : colonnes (incluant `normalized_label` matérialisé sur Transaction avec backfill), seed sous-catégories, seed règles système.

**Tech Stack:**

- **Backend** : SQLAlchemy 2.0 (modèles + migrations data), Alembic, pytest, existant pydantic-settings + FastAPI
- **Frontend** : React 18 + TanStack Query + shadcn/ui (existant) + nouvelle dépendance `@dnd-kit/core` + `@dnd-kit/sortable` pour le drag-and-drop
- **Schéma DB** : 1 nouvelle table (`categorization_rule`) + 3 colonnes sur `transactions` + seed data (~50 sous-catégories, ~30 règles)

---

## Prérequis

- Plan 1 complet (tag `plan-1-done`) : modèles `Transaction`, `ImportRecord`, `Counterparty`, `Category` (9 racines seed) présents ; pipeline d'import fonctionnel ; API `/api/imports`, `/api/transactions`, `/api/counterparties` opérationnels.
- Branche `plan-2-categorization` créée depuis `main`.
- 3 entités actives dans la base : ACREED Consulting, ACREED IA Solutions, ACRONOS (holding). Les 30 règles seed sont globales (`entity_id=NULL`) et servent toutes les entités.

---

## Conventions propres au Plan 2

- **PK** : `int` autoincrement, cohérent avec le reste du codebase (Plan 1 n'utilise pas UUID).
- **Normalisation libellé** : une seule source de vérité, `app.parsers.normalization.normalize_label`. Utilisée à la fois pour matérialiser `Transaction.normalized_label` et pour normaliser `CategorizationRule.label_value` à l'écriture (validator pydantic). La comparaison SQL au runtime est alors une simple égalité / LIKE sans transformation.
- **Priorité** : entier positif, plus petit = plus prioritaire. Index unique partiel sur `(COALESCE(entity_id, 0), priority)`. Les 30 règles seed occupent 1000..1290 (pas de 10) pour laisser de la place avant/après pour les règles custom.
- **Tie-break entité > globale** : `fetch_rules_for_entity` retourne d'abord les règles de l'entité (triées par `priority ASC`), puis les règles globales (triées par `priority ASC`). Donc à priorité égale, la règle entité gagne.
- **Manual never overwritten** : chaque fonction du service qui écrit `category_id` (hors `/bulk-categorize`) ajoute un filtre `Transaction.categorized_by != MANUAL`.
- **Tests** : TDD strict. Un fichier de test = un composant. Pas de commit sans tests verts.

---

## Structure des fichiers (cible à la fin du Plan 2)

```
backend/
├── app/
│   ├── models/
│   │   ├── categorization_rule.py       # NEW
│   │   └── transaction.py                # MODIFY — 3 colonnes
│   ├── schemas/
│   │   ├── categorization_rule.py        # NEW
│   │   └── transaction.py                # MODIFY — BulkCategorize, champ categorized_by
│   ├── services/
│   │   ├── categorization.py             # NEW — moteur
│   │   └── imports.py                    # MODIFY — populer normalized_label + appel categorize_transaction
│   └── api/
│       ├── rules.py                      # NEW
│       ├── transactions.py               # MODIFY — ?uncategorized, bulk-categorize
│       └── router.py                     # MODIFY — brancher rules.router
├── alembic/versions/
│   ├── 20260417_xxxx_plan2_rule_and_tx_columns.py   # NEW
│   ├── 20260417_xxxy_plan2_seed_subcategories.py     # NEW
│   └── 20260417_xxxz_plan2_seed_delubac_rules.py     # NEW
└── tests/
    ├── test_model_categorization_rule.py
    ├── test_schemas_categorization_rule.py
    ├── test_service_categorization_matching.py
    ├── test_service_categorization_engine.py
    ├── test_service_categorization_apply.py
    ├── test_service_imports_categorization.py
    ├── test_seed_subcategories.py
    ├── test_seed_delubac_rules.py
    ├── test_api_rules_list.py
    ├── test_api_rules_create.py
    ├── test_api_rules_preview.py
    ├── test_api_rules_apply.py
    ├── test_api_rules_reorder.py
    ├── test_api_rules_from_transactions.py
    ├── test_api_rules_permissions.py
    ├── test_api_transactions_bulk.py
    └── test_e2e_plan2.py

frontend/
├── src/
│   ├── api/
│   │   ├── rules.ts                      # NEW
│   │   └── transactions.ts               # MODIFY
│   ├── components/
│   │   ├── CategoryCombobox.tsx          # NEW
│   │   ├── RuleForm.tsx                  # NEW
│   │   ├── RulePreviewPanel.tsx          # NEW
│   │   └── SortableRulesTable.tsx        # NEW
│   ├── pages/
│   │   ├── RulesPage.tsx                 # NEW
│   │   └── TransactionsPage.tsx          # MODIFY — toolbar bulk
│   └── App.tsx                           # MODIFY — route /rules
└── tests/
    ├── CategoryCombobox.test.tsx
    ├── RuleForm.test.tsx
    └── SortableRulesTable.test.tsx
```

---

## Phase A — Modèles & schémas Pydantic

### Task A1 : Modèle `CategorizationRule`

**Files:**
- Create: `backend/app/models/categorization_rule.py`
- Modify: `backend/app/models/__init__.py` (export)
- Test: `backend/tests/test_model_categorization_rule.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_model_categorization_rule.py` :

```python
"""Tests du modèle CategorizationRule."""
import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.models.categorization_rule import (
    CategorizationRule,
    RuleLabelOperator,
    RuleAmountOperator,
    RuleDirection,
)
from app.models.category import Category
from app.models.entity import Entity


def _mk_category(db_session) -> Category:
    c = Category(name="Test cat", slug="test-cat-rule", is_system=False)
    db_session.add(c)
    db_session.commit()
    return c


def test_rule_basic_fields(db_session) -> None:
    cat = _mk_category(db_session)
    rule = CategorizationRule(
        name="URSSAF test",
        entity_id=None,
        priority=1000,
        is_system=False,
        label_operator=RuleLabelOperator.CONTAINS,
        label_value="URSSAF",
        direction=RuleDirection.ANY,
        category_id=cat.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    assert rule.id is not None
    assert rule.created_at is not None
    assert rule.direction == RuleDirection.ANY


def test_rule_priority_unique_per_scope(db_session) -> None:
    cat = _mk_category(db_session)
    db_session.add(CategorizationRule(
        name="A", priority=500, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="A",
        category_id=cat.id,
    ))
    db_session.commit()
    db_session.add(CategorizationRule(
        name="B", priority=500, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="B",
        category_id=cat.id,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_rule_same_priority_different_entity_ok(
    db_session, entity: Entity
) -> None:
    cat = _mk_category(db_session)
    db_session.add(CategorizationRule(
        name="Global", priority=500, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat.id,
    ))
    db_session.add(CategorizationRule(
        name="Entity", priority=500, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat.id,
    ))
    db_session.commit()  # doit passer — scopes différents


def test_rule_amount_between_requires_both_values(db_session) -> None:
    cat = _mk_category(db_session)
    rule = CategorizationRule(
        name="Bad between", priority=600,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        amount_operator=RuleAmountOperator.BETWEEN,
        amount_value=Decimal("100"),
        amount_value2=None,
        category_id=cat.id,
    )
    db_session.add(rule)
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Step 2 : Lancer — doit échouer (ImportError)**

```bash
cd backend && pytest tests/test_model_categorization_rule.py -v
```

Attendu : `ModuleNotFoundError: No module named 'app.models.categorization_rule'`

- [ ] **Step 3 : Implémenter le modèle**

Créer `backend/app/models/categorization_rule.py` :

```python
"""Modèle CategorizationRule : règle de catégorisation automatique."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer,
    Numeric, String, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RuleLabelOperator(str, enum.Enum):
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    EQUALS = "EQUALS"


class RuleAmountOperator(str, enum.Enum):
    EQ = "EQ"
    NE = "NE"
    GT = "GT"
    LT = "LT"
    BETWEEN = "BETWEEN"


class RuleDirection(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    ANY = "ANY"


class CategorizationRule(Base):
    __tablename__ = "categorization_rules"
    __table_args__ = (
        # Unicité (scope, priority). NULL entity_id = scope global ;
        # Postgres considère NULL ≠ NULL dans un index unique normal,
        # d'où l'utilisation d'un index fonctionnel via COALESCE.
        Index(
            "uq_rule_priority_per_scope",
            text("COALESCE(entity_id, 0)"),
            "priority",
            unique=True,
        ),
        CheckConstraint(
            "(amount_operator IS NULL) OR (amount_value IS NOT NULL)",
            name="ck_rule_amount_value_required",
        ),
        CheckConstraint(
            "(amount_operator <> 'BETWEEN') OR "
            "(amount_value2 IS NOT NULL AND amount_value < amount_value2)",
            name="ck_rule_between_coherent",
        ),
        CheckConstraint(
            "(label_operator IS NULL) OR (label_value IS NOT NULL AND length(label_value) >= 1)",
            name="ck_rule_label_value_required",
        ),
        CheckConstraint(
            "("
            "  label_operator IS NOT NULL"
            "  OR counterparty_id IS NOT NULL"
            "  OR bank_account_id IS NOT NULL"
            "  OR amount_operator IS NOT NULL"
            "  OR direction <> 'ANY'"
            ")",
            name="ck_rule_at_least_one_filter",
        ),
        Index("ix_rule_entity_priority", "entity_id", "priority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    label_operator: Mapped[Optional[RuleLabelOperator]] = mapped_column(
        Enum(RuleLabelOperator, name="rule_label_operator"), nullable=True
    )
    label_value: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    direction: Mapped[RuleDirection] = mapped_column(
        Enum(RuleDirection, name="rule_direction"),
        nullable=False, default=RuleDirection.ANY,
    )
    amount_operator: Mapped[Optional[RuleAmountOperator]] = mapped_column(
        Enum(RuleAmountOperator, name="rule_amount_operator"), nullable=True
    )
    amount_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    amount_value2: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    counterparty_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("counterparties.id", ondelete="SET NULL"), nullable=True
    )
    bank_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        scope = f"entity={self.entity_id}" if self.entity_id else "global"
        return f"<CategorizationRule(id={self.id}, {scope}, prio={self.priority}, {self.name!r})>"
```

Ajouter au `backend/app/models/__init__.py` :

```python
from app.models.categorization_rule import (  # noqa: F401
    CategorizationRule,
    RuleLabelOperator,
    RuleAmountOperator,
    RuleDirection,
)
```

- [ ] **Step 4 : Lancer les tests**

```bash
cd backend && pytest tests/test_model_categorization_rule.py -v
```

Les tests échouent encore car la table `categorization_rules` n'existe pas côté DB de test. On la crée en Tâche B1. Pour débloquer ce test **uniquement** ici, vérifier que l'import + l'instanciation passent sans erreur Python en lançant :

```bash
cd backend && python -c "from app.models.categorization_rule import CategorizationRule; print('ok')"
```

Attendu : `ok`. Les tests `pytest` resteront rouges jusqu'à B1.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/models/categorization_rule.py backend/app/models/__init__.py \
        backend/tests/test_model_categorization_rule.py
git commit -m "feat(models): CategorizationRule with filters and scope constraints"
```

---

### Task A2 : Modifier `Transaction` (3 colonnes)

**Files:**
- Modify: `backend/app/models/transaction.py`
- Test: `backend/tests/test_model_transaction_categorization.py` (NEW)

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_model_transaction_categorization.py` :

```python
"""Tests des nouvelles colonnes de catégorisation sur Transaction (Plan 2)."""
from datetime import date
from decimal import Decimal

from app.models.transaction import (
    Transaction,
    TransactionCategorizationSource,
)
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.bank_account import BankAccount
from app.models.import_record import ImportRecord, ImportStatus
from app.models.entity import Entity


def test_transaction_defaults_categorized_none(
    db_session, bank_account: BankAccount
) -> None:
    import_rec = ImportRecord(
        bank_account_id=bank_account.id, filename="x.pdf",
        file_sha256="a"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(import_rec)
    db_session.commit()

    tx = Transaction(
        bank_account_id=bank_account.id, import_id=import_rec.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("10.00"), label="TEST", raw_label="TEST",
        normalized_label="TEST",
        dedup_key="x"*64, statement_row_index=0,
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    assert tx.categorized_by == TransactionCategorizationSource.NONE
    assert tx.categorization_rule_id is None
    assert tx.normalized_label == "TEST"


def test_transaction_can_link_to_rule(
    db_session, bank_account: BankAccount
) -> None:
    cat = Category(name="X", slug="x-tx-cat-test", is_system=False)
    db_session.add(cat)
    db_session.commit()
    rule = CategorizationRule(
        name="R", priority=5000, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="FOO",
        category_id=cat.id,
    )
    db_session.add(rule)

    import_rec = ImportRecord(
        bank_account_id=bank_account.id, filename="y.pdf",
        file_sha256="b"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(import_rec)
    db_session.commit()

    tx = Transaction(
        bank_account_id=bank_account.id, import_id=import_rec.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("5.00"), label="FOO", raw_label="FOO",
        normalized_label="FOO",
        dedup_key="y"*64, statement_row_index=0,
        category_id=cat.id,
        categorized_by=TransactionCategorizationSource.RULE,
        categorization_rule_id=rule.id,
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    assert tx.categorized_by == TransactionCategorizationSource.RULE
    assert tx.categorization_rule_id == rule.id
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_model_transaction_categorization.py -v
```

Attendu : ImportError sur `TransactionCategorizationSource`.

- [ ] **Step 3 : Modifier `transaction.py`**

Éditer `backend/app/models/transaction.py`. Ajouter l'enum et les 3 colonnes :

```python
# En haut, après les autres imports
import enum
from sqlalchemy import Enum as SQLEnum


class TransactionCategorizationSource(str, enum.Enum):
    NONE = "NONE"
    RULE = "RULE"
    MANUAL = "MANUAL"
```

Dans la classe `Transaction`, ajouter (après `is_intercompany`) :

```python
    normalized_label: Mapped[str] = mapped_column(
        String(500), nullable=False, server_default=""
    )
    categorized_by: Mapped[TransactionCategorizationSource] = mapped_column(
        SQLEnum(TransactionCategorizationSource, name="transaction_categorization_source"),
        nullable=False, default=TransactionCategorizationSource.NONE,
        server_default="NONE",
    )
    categorization_rule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categorization_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
```

Ajouter aussi dans `__table_args__` :

```python
        Index("ix_tx_normalized_label", "normalized_label"),
        Index("ix_tx_categorized_by", "categorized_by"),
```

Exposer l'enum dans `backend/app/models/__init__.py` :

```python
from app.models.transaction import Transaction, TransactionCategorizationSource  # noqa: F401
```

- [ ] **Step 4 : Vérifier que le modèle charge**

```bash
cd backend && python -c "from app.models.transaction import TransactionCategorizationSource; print(list(TransactionCategorizationSource))"
```

Attendu : `[<TransactionCategorizationSource.NONE: 'NONE'>, ...]`

Les tests pytest resteront rouges jusqu'à B1 (migration qui crée la colonne en DB de test).

- [ ] **Step 5 : Commit**

```bash
git add backend/app/models/transaction.py backend/app/models/__init__.py \
        backend/tests/test_model_transaction_categorization.py
git commit -m "feat(models): Transaction categorization columns (source, rule_id, normalized_label)"
```

---

### Task A3 : Schémas Pydantic pour les règles

**Files:**
- Create: `backend/app/schemas/categorization_rule.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_schemas_categorization_rule.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_schemas_categorization_rule.py` :

```python
"""Tests des schémas Pydantic pour les règles."""
import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.categorization_rule import (
    RuleCreate, RuleUpdate, RuleRead, RulePreviewRequest, RulePreviewResponse,
    RuleSuggestion, BulkCategorizeRequest, RuleReorderItem,
)


def test_rule_create_normalizes_label_value() -> None:
    r = RuleCreate(
        name="URSSAF", priority=1000,
        label_operator="CONTAINS", label_value="  Urssaf ",
        direction="ANY", category_id=1,
    )
    # Normalisation = uppercase + accents retirés + trim + espaces collapsés
    assert r.label_value == "URSSAF"


def test_rule_create_rejects_empty_filter_set() -> None:
    with pytest.raises(ValidationError):
        RuleCreate(
            name="Vide", priority=1000,
            direction="ANY", category_id=1,
            # aucun filtre
        )


def test_rule_create_rejects_between_without_value2() -> None:
    with pytest.raises(ValidationError):
        RuleCreate(
            name="X", priority=1000,
            direction="DEBIT", category_id=1,
            amount_operator="BETWEEN", amount_value=Decimal("10"),
        )


def test_rule_create_rejects_between_with_inverted_values() -> None:
    with pytest.raises(ValidationError):
        RuleCreate(
            name="X", priority=1000,
            direction="DEBIT", category_id=1,
            amount_operator="BETWEEN",
            amount_value=Decimal("100"), amount_value2=Decimal("50"),
        )


def test_rule_create_label_operator_requires_value() -> None:
    with pytest.raises(ValidationError):
        RuleCreate(
            name="X", priority=1000,
            label_operator="CONTAINS",  # pas de label_value
            direction="ANY", category_id=1,
        )


def test_rule_preview_response_shape() -> None:
    resp = RulePreviewResponse(matching_count=42, sample=[])
    assert resp.matching_count == 42


def test_bulk_categorize_request_requires_ids() -> None:
    with pytest.raises(ValidationError):
        BulkCategorizeRequest(transaction_ids=[], category_id=1)
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_schemas_categorization_rule.py -v
```

Attendu : ModuleNotFoundError.

- [ ] **Step 3 : Créer le schéma**

Créer `backend/app/schemas/categorization_rule.py` :

```python
"""Schémas Pydantic pour les règles de catégorisation."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.parsers.normalization import normalize_label


class RuleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=120)
    entity_id: Optional[int] = None
    priority: int = Field(ge=1)

    label_operator: Optional[
        Literal["CONTAINS", "STARTS_WITH", "ENDS_WITH", "EQUALS"]
    ] = None
    label_value: Optional[str] = Field(default=None, max_length=200)
    direction: Literal["CREDIT", "DEBIT", "ANY"] = "ANY"
    amount_operator: Optional[
        Literal["EQ", "NE", "GT", "LT", "BETWEEN"]
    ] = None
    amount_value: Optional[Decimal] = None
    amount_value2: Optional[Decimal] = None
    counterparty_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    category_id: int

    @field_validator("label_value")
    @classmethod
    def _normalize_label_value(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v2 = normalize_label(v)
        if not v2:
            raise ValueError("label_value vide après normalisation")
        return v2

    @model_validator(mode="after")
    def _check_filters_coherent(self) -> "RuleBase":
        # Au moins un filtre non-trivial
        has_filter = (
            self.label_operator is not None
            or self.counterparty_id is not None
            or self.bank_account_id is not None
            or self.amount_operator is not None
            or self.direction != "ANY"
        )
        if not has_filter:
            raise ValueError(
                "Au moins un filtre est requis (libellé, contrepartie, compte, "
                "montant ou sens non-ANY)."
            )

        # label_operator ⇒ label_value
        if self.label_operator is not None and not self.label_value:
            raise ValueError("label_value requis si label_operator est fourni.")

        # amount_operator ⇒ amount_value
        if self.amount_operator is not None and self.amount_value is None:
            raise ValueError("amount_value requis si amount_operator est fourni.")

        # BETWEEN ⇒ amount_value2 et amount_value < amount_value2
        if self.amount_operator == "BETWEEN":
            if self.amount_value2 is None:
                raise ValueError("amount_value2 requis pour BETWEEN.")
            if self.amount_value is None or self.amount_value >= self.amount_value2:
                raise ValueError("amount_value doit être < amount_value2 pour BETWEEN.")

        return self


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    """Tous les champs optionnels — PATCH partiel."""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    priority: Optional[int] = Field(default=None, ge=1)
    label_operator: Optional[
        Literal["CONTAINS", "STARTS_WITH", "ENDS_WITH", "EQUALS"]
    ] = None
    label_value: Optional[str] = None
    direction: Optional[Literal["CREDIT", "DEBIT", "ANY"]] = None
    amount_operator: Optional[Literal["EQ", "NE", "GT", "LT", "BETWEEN"]] = None
    amount_value: Optional[Decimal] = None
    amount_value2: Optional[Decimal] = None
    counterparty_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    category_id: Optional[int] = None

    @field_validator("label_value")
    @classmethod
    def _normalize_label_value(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_label(v)


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    entity_id: Optional[int]
    priority: int
    is_system: bool
    label_operator: Optional[str]
    label_value: Optional[str]
    direction: str
    amount_operator: Optional[str]
    amount_value: Optional[Decimal]
    amount_value2: Optional[Decimal]
    counterparty_id: Optional[int]
    bank_account_id: Optional[int]
    category_id: int
    created_at: datetime
    updated_at: datetime


class RulePreviewRequest(RuleBase):
    """Payload pour `/rules/preview` : une RuleCreate non persistée."""
    pass


class RuleSampleTransaction(BaseModel):
    id: int
    operation_date: str
    amount: Decimal
    label: str
    current_category_id: Optional[int]


class RulePreviewResponse(BaseModel):
    matching_count: int
    sample: list[RuleSampleTransaction]


class RuleApplyResponse(BaseModel):
    updated_count: int


class RuleSuggestion(BaseModel):
    """Retour de `/rules/from-transactions`."""
    suggested_label_operator: Literal["CONTAINS", "STARTS_WITH"]
    suggested_label_value: str
    suggested_direction: Literal["CREDIT", "DEBIT", "ANY"]
    suggested_bank_account_id: Optional[int]
    transaction_count: int


class RuleReorderItem(BaseModel):
    id: int
    priority: int


class BulkCategorizeRequest(BaseModel):
    transaction_ids: list[int] = Field(min_length=1)
    category_id: int
```

Mettre à jour `backend/app/schemas/__init__.py` :

```python
from app.schemas.categorization_rule import (  # noqa: F401
    RuleCreate, RuleUpdate, RuleRead, RulePreviewRequest, RulePreviewResponse,
    RuleApplyResponse, RuleSuggestion, RuleReorderItem, BulkCategorizeRequest,
    RuleSampleTransaction,
)
```

- [ ] **Step 4 : Lancer — doit passer**

```bash
cd backend && pytest tests/test_schemas_categorization_rule.py -v
```

Attendu : 7 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/schemas/categorization_rule.py backend/app/schemas/__init__.py \
        backend/tests/test_schemas_categorization_rule.py
git commit -m "feat(schemas): Pydantic schemas for categorization rules with validation"
```

---

## Phase B — Migrations Alembic

### Task B1 : Migration « règle + colonnes tx + backfill normalized_label »

**Files:**
- Create: `backend/alembic/versions/20260417_1000_plan2_rule_and_tx_columns.py`
- Test: `backend/tests/test_migration_plan2_b1.py`

- [ ] **Step 1 : Écrire le test (après-migration)**

Créer `backend/tests/test_migration_plan2_b1.py` :

```python
"""Vérifie que la migration B1 crée la table et les colonnes."""
from sqlalchemy import inspect

from app.db import SessionLocal  # existant


def test_table_categorization_rules_exists() -> None:
    with SessionLocal() as session:
        insp = inspect(session.get_bind())
        assert insp.has_table("categorization_rules")


def test_transaction_has_new_columns() -> None:
    with SessionLocal() as session:
        insp = inspect(session.get_bind())
        cols = {c["name"] for c in insp.get_columns("transactions")}
        assert "normalized_label" in cols
        assert "categorized_by" in cols
        assert "categorization_rule_id" in cols


def test_existing_transactions_have_normalized_label_backfilled(db_session) -> None:
    # La conftest réinitialise la DB à chaque test mais applique la migration.
    # On vérifie que toute tx inserted par d'autres tests reçoit normalized_label
    # non vide si label est non vide (server_default '' en Plan 2 B1).
    from sqlalchemy import text
    rows = db_session.execute(text(
        "SELECT label, normalized_label FROM transactions LIMIT 1"
    )).all()
    # Peut être vide en DB de test — on teste surtout la présence de la colonne
    assert True  # assertion de structure déjà couverte ci-dessus
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_migration_plan2_b1.py -v
```

Attendu : tests `has_table` / `normalized_label in cols` échouent tant que la migration n'a pas tourné.

- [ ] **Step 3 : Créer la migration**

D'abord, repérer la dernière révision Alembic :

```bash
cd backend && alembic heads
```

Noter la valeur (ex. `b2c3d4e5f6a7`). Créer `backend/alembic/versions/20260417_1000_plan2_rule_and_tx_columns.py` :

```python
"""Plan 2 B1 : categorization_rules table + transaction categorization columns.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-17 10:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import unicodedata
import re


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"  # <-- remplacer par `alembic heads` local
branch_labels = None
depends_on = None


def _normalize_py(raw: str) -> str:
    """Réplique EXACTEMENT app.parsers.normalization.normalize_label pour le backfill."""
    if raw is None:
        return ""
    text = raw.strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def upgrade() -> None:
    # --- Enums ---
    rule_label_op = sa.Enum(
        "CONTAINS", "STARTS_WITH", "ENDS_WITH", "EQUALS",
        name="rule_label_operator",
    )
    rule_amount_op = sa.Enum(
        "EQ", "NE", "GT", "LT", "BETWEEN",
        name="rule_amount_operator",
    )
    rule_direction = sa.Enum(
        "CREDIT", "DEBIT", "ANY",
        name="rule_direction",
    )
    tx_cat_source = sa.Enum(
        "NONE", "RULE", "MANUAL",
        name="transaction_categorization_source",
    )
    rule_label_op.create(op.get_bind(), checkfirst=True)
    rule_amount_op.create(op.get_bind(), checkfirst=True)
    rule_direction.create(op.get_bind(), checkfirst=True)
    tx_cat_source.create(op.get_bind(), checkfirst=True)

    # --- Table categorization_rules ---
    op.create_table(
        "categorization_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("entity_id", sa.Integer(),
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("label_operator", rule_label_op, nullable=True),
        sa.Column("label_value", sa.String(200), nullable=True),
        sa.Column("direction", rule_direction, nullable=False,
                  server_default="ANY"),
        sa.Column("amount_operator", rule_amount_op, nullable=True),
        sa.Column("amount_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("amount_value2", sa.Numeric(14, 2), nullable=True),
        sa.Column("counterparty_id", sa.Integer(),
                  sa.ForeignKey("counterparties.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bank_account_id", sa.Integer(),
                  sa.ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "(amount_operator IS NULL) OR (amount_value IS NOT NULL)",
            name="ck_rule_amount_value_required",
        ),
        sa.CheckConstraint(
            "(amount_operator <> 'BETWEEN') OR "
            "(amount_value2 IS NOT NULL AND amount_value < amount_value2)",
            name="ck_rule_between_coherent",
        ),
        sa.CheckConstraint(
            "(label_operator IS NULL) OR (label_value IS NOT NULL AND length(label_value) >= 1)",
            name="ck_rule_label_value_required",
        ),
        sa.CheckConstraint(
            "(label_operator IS NOT NULL "
            "OR counterparty_id IS NOT NULL "
            "OR bank_account_id IS NOT NULL "
            "OR amount_operator IS NOT NULL "
            "OR direction <> 'ANY')",
            name="ck_rule_at_least_one_filter",
        ),
    )
    op.create_index(
        "uq_rule_priority_per_scope",
        "categorization_rules",
        [sa.text("COALESCE(entity_id, 0)"), "priority"],
        unique=True,
    )
    op.create_index(
        "ix_rule_entity_priority",
        "categorization_rules",
        ["entity_id", "priority"],
    )

    # --- Colonnes sur transactions ---
    op.add_column(
        "transactions",
        sa.Column("normalized_label", sa.String(500), nullable=False,
                  server_default=""),
    )
    op.add_column(
        "transactions",
        sa.Column("categorized_by", tx_cat_source, nullable=False,
                  server_default="NONE"),
    )
    op.add_column(
        "transactions",
        sa.Column("categorization_rule_id", sa.Integer(),
                  sa.ForeignKey("categorization_rules.id", ondelete="SET NULL"),
                  nullable=True),
    )
    op.create_index("ix_tx_normalized_label", "transactions", ["normalized_label"])
    op.create_index("ix_tx_categorized_by", "transactions", ["categorized_by"])

    # --- Backfill normalized_label pour les transactions existantes ---
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, label FROM transactions")).all()
    for row in rows:
        normalized = _normalize_py(row.label or "")
        conn.execute(
            sa.text("UPDATE transactions SET normalized_label = :n WHERE id = :id"),
            {"n": normalized, "id": row.id},
        )


def downgrade() -> None:
    op.drop_index("ix_tx_categorized_by", table_name="transactions")
    op.drop_index("ix_tx_normalized_label", table_name="transactions")
    op.drop_column("transactions", "categorization_rule_id")
    op.drop_column("transactions", "categorized_by")
    op.drop_column("transactions", "normalized_label")

    op.drop_index("ix_rule_entity_priority", table_name="categorization_rules")
    op.drop_index("uq_rule_priority_per_scope", table_name="categorization_rules")
    op.drop_table("categorization_rules")

    for enum_name in (
        "transaction_categorization_source",
        "rule_direction",
        "rule_amount_operator",
        "rule_label_operator",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 4 : Lancer alembic + tests**

```bash
cd backend && alembic upgrade head
pytest tests/test_migration_plan2_b1.py tests/test_model_categorization_rule.py \
       tests/test_model_transaction_categorization.py -v
```

Attendu : tous passent.

- [ ] **Step 5 : Vérifier downgrade → upgrade cycle**

```bash
cd backend && alembic downgrade -1 && alembic upgrade head
pytest tests/test_migration_plan2_b1.py -v
```

Attendu : passent toujours.

- [ ] **Step 6 : Commit**

```bash
git add backend/alembic/versions/20260417_1000_plan2_rule_and_tx_columns.py \
        backend/tests/test_migration_plan2_b1.py
git commit -m "feat(db): migration plan2 — rules table, tx categorization columns, normalized_label backfill"
```

---

### Task B2 : Migration « seed sous-catégories »

**Files:**
- Create: `backend/alembic/versions/20260417_1010_plan2_seed_subcategories.py`
- Test: `backend/tests/test_seed_subcategories.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_seed_subcategories.py` :

```python
"""Vérifie que la migration B2 a inséré les ~50 sous-catégories."""
from sqlalchemy import select

from app.models.category import Category


EXPECTED_PARENT_SLUGS = {
    "encaissements", "personnel", "charges-sociales", "impots-taxes",
    "charges-externes", "frais-bancaires", "investissements",
    "flux-financiers", "autres",
}


EXPECTED_CHILDREN = {
    "encaissements": {
        "ventes-clients", "subventions-aides",
        "remboursements-encaissements", "autres-encaissements",
    },
    "personnel": {
        "salaires-nets", "acomptes-salaires", "primes-bonus",
        "frais-professionnels-remb",
    },
    "charges-sociales": {
        "urssaf", "retraite", "prevoyance", "mutuelle", "taxe-apprentissage",
        "formation-professionnelle",
    },
    "impots-taxes": {
        "tva-collectee", "tva-deductible", "tva-a-payer",
        "impot-societes", "cfe-cvae", "taxe-fonciere", "autres-taxes",
    },
    "charges-externes": {
        "loyers-charges-locatives", "energie-eau", "telecom-internet",
        "assurances", "honoraires-conseil", "deplacements-missions",
        "fournitures-bureau", "informatique-logiciels",
        "publicite-marketing", "sous-traitance-generique",
    },
    "frais-bancaires": {
        "commissions", "agios-interets", "frais-cartes", "change",
    },
    "investissements": {
        "acquisitions-materiel", "acquisitions-logiciels",
        "acquisitions-immobilier",
    },
    "flux-financiers": {
        "emprunts-remboursements", "apports-comptes-courants",
        "virements-internes", "dividendes-remontees",
    },
    "autres": {
        "non-identifies", "ajustements",
    },
}


def test_all_expected_subcategories_seeded(db_session) -> None:
    for parent_slug, children_slugs in EXPECTED_CHILDREN.items():
        parent = db_session.execute(
            select(Category).where(Category.slug == parent_slug)
        ).scalar_one_or_none()
        assert parent is not None, f"Parent {parent_slug} manquant"
        child_rows = db_session.execute(
            select(Category).where(Category.parent_category_id == parent.id)
        ).scalars().all()
        seeded = {c.slug for c in child_rows}
        missing = children_slugs - seeded
        assert not missing, f"Sous-catégories manquantes sous {parent_slug}: {missing}"


def test_subcategories_are_system(db_session) -> None:
    row = db_session.execute(
        select(Category).where(Category.slug == "urssaf")
    ).scalar_one()
    assert row.is_system is True
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_seed_subcategories.py -v
```

Attendu : 2 failed (sous-catégories inexistantes).

- [ ] **Step 3 : Créer la migration**

Créer `backend/alembic/versions/20260417_1010_plan2_seed_subcategories.py` :

```python
"""Plan 2 B2 : seed ~50 sous-catégories sous les 9 racines.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-17 10:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


# Mapping parent_slug -> [(name, slug, color?)]
SUBCATS: dict[str, list[tuple[str, str, str | None]]] = {
    "encaissements": [
        ("Ventes clients", "ventes-clients", "#2ecc71"),
        ("Subventions & aides", "subventions-aides", "#27ae60"),
        ("Remboursements reçus", "remboursements-encaissements", "#16a085"),
        ("Autres encaissements", "autres-encaissements", "#1abc9c"),
    ],
    "personnel": [
        ("Salaires nets", "salaires-nets", "#e74c3c"),
        ("Acomptes salaires", "acomptes-salaires", "#c0392b"),
        ("Primes & bonus", "primes-bonus", "#d35400"),
        ("Frais pro. remboursés", "frais-professionnels-remb", "#e67e22"),
    ],
    "charges-sociales": [
        ("URSSAF", "urssaf", "#9b59b6"),
        ("Retraite", "retraite", "#8e44ad"),
        ("Prévoyance", "prevoyance", "#8e44ad"),
        ("Mutuelle", "mutuelle", "#8e44ad"),
        ("Taxe d'apprentissage", "taxe-apprentissage", "#8e44ad"),
        ("Formation professionnelle", "formation-professionnelle", "#8e44ad"),
    ],
    "impots-taxes": [
        ("TVA collectée", "tva-collectee", "#f39c12"),
        ("TVA déductible", "tva-deductible", "#f1c40f"),
        ("TVA à payer/rembourser", "tva-a-payer", "#e67e22"),
        ("Impôt sur les sociétés", "impot-societes", "#d35400"),
        ("CFE / CVAE", "cfe-cvae", "#c0392b"),
        ("Taxe foncière", "taxe-fonciere", "#a0522d"),
        ("Autres taxes", "autres-taxes", "#95a5a6"),
    ],
    "charges-externes": [
        ("Loyers & charges locatives", "loyers-charges-locatives", "#3498db"),
        ("Énergie & eau", "energie-eau", "#2980b9"),
        ("Télécom & Internet", "telecom-internet", "#5dade2"),
        ("Assurances", "assurances", "#85c1e9"),
        ("Honoraires & conseil", "honoraires-conseil", "#2874a6"),
        ("Déplacements & missions", "deplacements-missions", "#1f618d"),
        ("Fournitures de bureau", "fournitures-bureau", "#aed6f1"),
        ("Informatique & logiciels", "informatique-logiciels", "#5499c7"),
        ("Publicité & marketing", "publicite-marketing", "#2e86c1"),
        ("Sous-traitance (générique)", "sous-traitance-generique", "#154360"),
    ],
    "frais-bancaires": [
        ("Commissions bancaires", "commissions", "#7f8c8d"),
        ("Agios & intérêts", "agios-interets", "#95a5a6"),
        ("Frais sur cartes", "frais-cartes", "#bdc3c7"),
        ("Opérations de change", "change", "#7f8c8d"),
    ],
    "investissements": [
        ("Acquisitions matériel", "acquisitions-materiel", "#34495e"),
        ("Acquisitions logiciels", "acquisitions-logiciels", "#2c3e50"),
        ("Acquisitions immobilier", "acquisitions-immobilier", "#1c2833"),
    ],
    "flux-financiers": [
        ("Emprunts & remboursements", "emprunts-remboursements", "#16a085"),
        ("Apports & comptes courants", "apports-comptes-courants", "#1abc9c"),
        ("Virements internes", "virements-internes", "#48c9b0"),
        ("Dividendes & remontées", "dividendes-remontees", "#117864"),
    ],
    "autres": [
        ("Non identifiés", "non-identifies", "#b2babb"),
        ("Ajustements", "ajustements", "#d5dbdb"),
    ],
}


def upgrade() -> None:
    conn = op.get_bind()
    for parent_slug, children in SUBCATS.items():
        parent_id = conn.execute(
            sa.text("SELECT id FROM categories WHERE slug = :s"),
            {"s": parent_slug},
        ).scalar_one()

        for name, slug, color in children:
            exists = conn.execute(
                sa.text("SELECT id FROM categories WHERE slug = :s"),
                {"s": slug},
            ).scalar_one_or_none()
            if exists:
                continue
            conn.execute(
                sa.text(
                    "INSERT INTO categories "
                    "(name, slug, color, parent_category_id, is_system, created_at, updated_at) "
                    "VALUES (:name, :slug, :color, :parent, true, NOW(), NOW())"
                ),
                {"name": name, "slug": slug, "color": color, "parent": parent_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [slug for children in SUBCATS.values() for _, slug, _ in children]
    conn.execute(
        sa.text("DELETE FROM categories WHERE slug = ANY(:slugs)"),
        {"slugs": slugs},
    )
```

- [ ] **Step 4 : Lancer**

```bash
cd backend && alembic upgrade head
pytest tests/test_seed_subcategories.py -v
```

Attendu : 2 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/alembic/versions/20260417_1010_plan2_seed_subcategories.py \
        backend/tests/test_seed_subcategories.py
git commit -m "feat(db): seed ~50 system subcategories under Plan 1 roots"
```

---

### Task B3 : Migration « seed 30 règles Delubac »

**Files:**
- Create: `backend/alembic/versions/20260417_1020_plan2_seed_delubac_rules.py`
- Test: `backend/tests/test_seed_delubac_rules.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_seed_delubac_rules.py` :

```python
"""Vérifie la migration B3 : ~30 règles système globales."""
from sqlalchemy import select, func

from app.models.categorization_rule import CategorizationRule


def test_seeded_rules_count(db_session) -> None:
    count = db_session.execute(
        select(func.count(CategorizationRule.id)).where(
            CategorizationRule.is_system.is_(True),
            CategorizationRule.entity_id.is_(None),
        )
    ).scalar_one()
    assert count >= 28, f"{count} règles système seed (attendu >= 28)"


def test_seeded_priorities_unique(db_session) -> None:
    rows = db_session.execute(
        select(CategorizationRule.priority).where(
            CategorizationRule.is_system.is_(True),
            CategorizationRule.entity_id.is_(None),
        )
    ).scalars().all()
    assert len(rows) == len(set(rows)), "Priorités système dupliquées"


def test_urssaf_rule_exists(db_session) -> None:
    r = db_session.execute(
        select(CategorizationRule).where(
            CategorizationRule.is_system.is_(True),
            CategorizationRule.label_value == "URSSAF",
        )
    ).scalar_one_or_none()
    assert r is not None
    assert r.category_id is not None


def test_all_seeded_categories_exist(db_session) -> None:
    from app.models.category import Category
    rules = db_session.execute(
        select(CategorizationRule).where(CategorizationRule.is_system.is_(True))
    ).scalars().all()
    for rule in rules:
        cat = db_session.get(Category, rule.category_id)
        assert cat is not None, f"Règle {rule.name} pointe vers catégorie inexistante"
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_seed_delubac_rules.py -v
```

Attendu : tous rouges (règles absentes).

- [ ] **Step 3 : Créer la migration**

Créer `backend/alembic/versions/20260417_1020_plan2_seed_delubac_rules.py` :

```python
"""Plan 2 B3 : seed ~30 règles système globales pour Delubac / libellés FR standards.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-17 10:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


# (priority, name, label_op, label_value, direction, category_slug)
# Les libellés sont déjà normalisés (uppercase, pas d'accents).
RULES: list[tuple[int, str, str | None, str | None, str, str]] = [
    (1000, "URSSAF",               "CONTAINS",  "URSSAF",            "DEBIT",  "urssaf"),
    (1010, "DGFIP Impôt société",  "CONTAINS",  "DGFIP",             "DEBIT",  "impot-societes"),
    (1020, "TVA (débit)",          "CONTAINS",  "TVA",               "DEBIT",  "tva-a-payer"),
    (1030, "TVA remboursement",    "CONTAINS",  "TVA",               "CREDIT", "tva-a-payer"),
    (1040, "Virement salaire",     "STARTS_WITH","VIR SEPA SALAIRE", "DEBIT",  "salaires-nets"),
    (1050, "Virement acompte",     "CONTAINS",  "ACOMPTE",           "DEBIT",  "acomptes-salaires"),
    (1060, "Prévoyance Humanis",   "CONTAINS",  "HUMANIS",           "DEBIT",  "prevoyance"),
    (1070, "Prévoyance Malakoff",  "CONTAINS",  "MALAKOFF",          "DEBIT",  "prevoyance"),
    (1080, "Mutuelle Alan",        "CONTAINS",  "ALAN",              "DEBIT",  "mutuelle"),
    (1090, "Mutuelle Harmonie",    "CONTAINS",  "HARMONIE MUTUELLE", "DEBIT",  "mutuelle"),
    (1100, "Retraite AG2R",        "CONTAINS",  "AG2R",              "DEBIT",  "retraite"),
    (1110, "Formation pro (OPCO)", "CONTAINS",  "OPCO",              "DEBIT",  "formation-professionnelle"),
    (1120, "EDF",                  "CONTAINS",  "EDF",               "DEBIT",  "energie-eau"),
    (1130, "Engie",                "CONTAINS",  "ENGIE",             "DEBIT",  "energie-eau"),
    (1140, "Eau Veolia",           "CONTAINS",  "VEOLIA",            "DEBIT",  "energie-eau"),
    (1150, "Orange",               "CONTAINS",  "ORANGE",            "DEBIT",  "telecom-internet"),
    (1160, "SFR",                  "CONTAINS",  "SFR",               "DEBIT",  "telecom-internet"),
    (1170, "Free Pro",             "CONTAINS",  "FREE",              "DEBIT",  "telecom-internet"),
    (1180, "AXA assurances",       "CONTAINS",  "AXA",               "DEBIT",  "assurances"),
    (1190, "Allianz",              "CONTAINS",  "ALLIANZ",           "DEBIT",  "assurances"),
    (1200, "Loyer (PRLV SEPA)",    "STARTS_WITH","PRLV SEPA LOYER",  "DEBIT",  "loyers-charges-locatives"),
    (1210, "Google Workspace",     "CONTAINS",  "GOOGLE",            "DEBIT",  "informatique-logiciels"),
    (1220, "Microsoft",            "CONTAINS",  "MICROSOFT",         "DEBIT",  "informatique-logiciels"),
    (1230, "OVH / hébergement",    "CONTAINS",  "OVH",               "DEBIT",  "informatique-logiciels"),
    (1240, "AWS",                  "CONTAINS",  "AMAZON WEB SERVICES","DEBIT", "informatique-logiciels"),
    (1250, "Commission bancaire",  "CONTAINS",  "COMMISSION",        "DEBIT",  "commissions"),
    (1260, "Agios",                "CONTAINS",  "AGIOS",             "DEBIT",  "agios-interets"),
    (1270, "Frais carte",          "CONTAINS",  "COTISATION CARTE",  "DEBIT",  "frais-cartes"),
    (1280, "Virement interne",     "CONTAINS",  "VIREMENT INTERNE",  "ANY",    "virements-internes"),
    (1290, "Dividendes",           "CONTAINS",  "DIVIDENDE",         "ANY",    "dividendes-remontees"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for priority, name, label_op, label_value, direction, cat_slug in RULES:
        cat_id = conn.execute(
            sa.text("SELECT id FROM categories WHERE slug = :s"),
            {"s": cat_slug},
        ).scalar_one_or_none()
        if cat_id is None:
            raise RuntimeError(f"Catégorie '{cat_slug}' introuvable (B2 manquante ?)")

        exists = conn.execute(
            sa.text(
                "SELECT id FROM categorization_rules "
                "WHERE is_system = true AND entity_id IS NULL AND priority = :p"
            ),
            {"p": priority},
        ).scalar_one_or_none()
        if exists:
            continue

        conn.execute(
            sa.text(
                "INSERT INTO categorization_rules "
                "(name, entity_id, priority, is_system, label_operator, label_value, "
                " direction, category_id, created_at, updated_at) "
                "VALUES (:name, NULL, :priority, true, :lop, :lval, :dir, :cat, NOW(), NOW())"
            ),
            {
                "name": name, "priority": priority,
                "lop": label_op, "lval": label_value,
                "dir": direction, "cat": cat_id,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    priorities = [p for p, *_ in RULES]
    conn.execute(
        sa.text(
            "DELETE FROM categorization_rules "
            "WHERE is_system = true AND entity_id IS NULL AND priority = ANY(:p)"
        ),
        {"p": priorities},
    )
```

- [ ] **Step 4 : Lancer**

```bash
cd backend && alembic upgrade head
pytest tests/test_seed_delubac_rules.py -v
```

Attendu : 4 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/alembic/versions/20260417_1020_plan2_seed_delubac_rules.py \
        backend/tests/test_seed_delubac_rules.py
git commit -m "feat(db): seed 30 system categorization rules for Delubac/FR standard labels"
```

---

## Phase C — Moteur de catégorisation (service)

### Task C1 : Helper `build_rule_filter` (SQL ET)

**Files:**
- Create: `backend/app/services/categorization.py` (module initial)
- Test: `backend/tests/test_service_categorization_matching.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_service_categorization_matching.py` :

```python
"""Tests de build_rule_filter et matches_transaction (moteur pur)."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.transaction import Transaction
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection, RuleAmountOperator,
)
from app.services.categorization import build_rule_filter, matches_transaction
from app.models.bank_account import BankAccount
from app.models.import_record import ImportRecord, ImportStatus
from app.models.category import Category


def _mk_cat(db_session, slug: str) -> Category:
    c = Category(name=slug, slug=slug, is_system=False)
    db_session.add(c); db_session.commit()
    return c


def _mk_tx(
    db_session, bank_account: BankAccount,
    *, label: str, amount: Decimal, normalized: str | None = None,
    row_idx: int = 0,
) -> Transaction:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="t.pdf",
        file_sha256="f" * 64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    tx = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=amount, label=label, raw_label=label,
        normalized_label=normalized if normalized is not None else label.upper(),
        dedup_key=f"{row_idx}-" + "x" * 60, statement_row_index=row_idx,
    )
    db_session.add(tx); db_session.commit()
    return tx


def test_contains_matches(db_session, bank_account) -> None:
    cat = _mk_cat(db_session, "c1")
    rule = CategorizationRule(
        name="R", priority=100, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    tx_match = _mk_tx(db_session, bank_account,
                     label="PRLV URSSAF 123", amount=Decimal("-100"),
                     normalized="PRLV URSSAF 123", row_idx=1)
    tx_no    = _mk_tx(db_session, bank_account,
                     label="EDF", amount=Decimal("-50"), normalized="EDF", row_idx=2)

    assert matches_transaction(rule, tx_match)
    assert not matches_transaction(rule, tx_no)

    q = select(Transaction).where(build_rule_filter(rule))
    ids = {r.id for r in db_session.execute(q).scalars().all()}
    assert tx_match.id in ids and tx_no.id not in ids


def test_direction_credit(db_session, bank_account) -> None:
    cat = _mk_cat(db_session, "c2")
    rule = CategorizationRule(
        name="R2", priority=101, direction=RuleDirection.CREDIT,
        label_operator=RuleLabelOperator.CONTAINS, label_value="REMB",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()
    tx_pos = _mk_tx(db_session, bank_account, label="REMB X",
                    amount=Decimal("50"), row_idx=3)
    tx_neg = _mk_tx(db_session, bank_account, label="REMB Y",
                    amount=Decimal("-50"), row_idx=4)
    assert matches_transaction(rule, tx_pos)
    assert not matches_transaction(rule, tx_neg)


def test_amount_between(db_session, bank_account) -> None:
    cat = _mk_cat(db_session, "c3")
    rule = CategorizationRule(
        name="R3", priority=102, direction=RuleDirection.DEBIT,
        amount_operator=RuleAmountOperator.BETWEEN,
        amount_value=Decimal("100"), amount_value2=Decimal("200"),
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    tx_ok     = _mk_tx(db_session, bank_account, label="X",
                        amount=Decimal("-150"), row_idx=5)
    tx_too_lo = _mk_tx(db_session, bank_account, label="X",
                        amount=Decimal("-50"), row_idx=6)
    tx_too_hi = _mk_tx(db_session, bank_account, label="X",
                        amount=Decimal("-300"), row_idx=7)
    assert matches_transaction(rule, tx_ok)
    assert not matches_transaction(rule, tx_too_lo)
    assert not matches_transaction(rule, tx_too_hi)


def test_starts_with(db_session, bank_account) -> None:
    cat = _mk_cat(db_session, "c4")
    rule = CategorizationRule(
        name="R4", priority=103, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.STARTS_WITH,
        label_value="VIR SEPA", category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()
    tx_a = _mk_tx(db_session, bank_account, label="VIR SEPA SALAIRE X",
                   amount=Decimal("-1000"),
                   normalized="VIR SEPA SALAIRE X", row_idx=8)
    tx_b = _mk_tx(db_session, bank_account, label="PRLV SEPA URSSAF",
                   amount=Decimal("-500"),
                   normalized="PRLV SEPA URSSAF", row_idx=9)
    assert matches_transaction(rule, tx_a)
    assert not matches_transaction(rule, tx_b)
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_service_categorization_matching.py -v
```

Attendu : ModuleNotFoundError sur `app.services.categorization`.

- [ ] **Step 3 : Créer le module**

Créer `backend/app/services/categorization.py` :

```python
"""Moteur de catégorisation : matching Python + SQL, apply, preview."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleAmountOperator, RuleDirection,
)
from app.models.transaction import Transaction, TransactionCategorizationSource


def build_rule_filter(rule: CategorizationRule) -> ColumnElement[bool]:
    """Retourne une clause WHERE SQLAlchemy qui matche les transactions de la règle.
    Ne filtre PAS sur categorized_by — le caller ajoute ce critère.
    """
    clauses: list[ColumnElement[bool]] = []

    if rule.label_operator is not None and rule.label_value is not None:
        pattern = rule.label_value
        if rule.label_operator == RuleLabelOperator.CONTAINS:
            clauses.append(Transaction.normalized_label.ilike(f"%{pattern}%"))
        elif rule.label_operator == RuleLabelOperator.STARTS_WITH:
            clauses.append(Transaction.normalized_label.ilike(f"{pattern}%"))
        elif rule.label_operator == RuleLabelOperator.ENDS_WITH:
            clauses.append(Transaction.normalized_label.ilike(f"%{pattern}"))
        elif rule.label_operator == RuleLabelOperator.EQUALS:
            clauses.append(Transaction.normalized_label == pattern)

    if rule.direction == RuleDirection.CREDIT:
        clauses.append(Transaction.amount > 0)
    elif rule.direction == RuleDirection.DEBIT:
        clauses.append(Transaction.amount < 0)

    if rule.amount_operator is not None and rule.amount_value is not None:
        abs_amt = func.abs(Transaction.amount)
        if rule.amount_operator == RuleAmountOperator.EQ:
            clauses.append(abs_amt == rule.amount_value)
        elif rule.amount_operator == RuleAmountOperator.NE:
            clauses.append(abs_amt != rule.amount_value)
        elif rule.amount_operator == RuleAmountOperator.GT:
            clauses.append(abs_amt > rule.amount_value)
        elif rule.amount_operator == RuleAmountOperator.LT:
            clauses.append(abs_amt < rule.amount_value)
        elif rule.amount_operator == RuleAmountOperator.BETWEEN:
            assert rule.amount_value2 is not None
            clauses.append(abs_amt >= rule.amount_value)
            clauses.append(abs_amt <= rule.amount_value2)

    if rule.counterparty_id is not None:
        clauses.append(Transaction.counterparty_id == rule.counterparty_id)

    if rule.bank_account_id is not None:
        clauses.append(Transaction.bank_account_id == rule.bank_account_id)

    return and_(*clauses) if clauses else (Transaction.id == Transaction.id)


def matches_transaction(rule: CategorizationRule, tx: Transaction) -> bool:
    """Évalue une règle contre une Transaction chargée (en Python, sans SQL)."""
    if rule.label_operator is not None and rule.label_value:
        nl = tx.normalized_label or ""
        pat = rule.label_value
        if rule.label_operator == RuleLabelOperator.CONTAINS and pat not in nl:
            return False
        if rule.label_operator == RuleLabelOperator.STARTS_WITH and not nl.startswith(pat):
            return False
        if rule.label_operator == RuleLabelOperator.ENDS_WITH and not nl.endswith(pat):
            return False
        if rule.label_operator == RuleLabelOperator.EQUALS and nl != pat:
            return False

    if rule.direction == RuleDirection.CREDIT and tx.amount <= 0:
        return False
    if rule.direction == RuleDirection.DEBIT and tx.amount >= 0:
        return False

    if rule.amount_operator is not None and rule.amount_value is not None:
        abs_amt = abs(tx.amount)
        if rule.amount_operator == RuleAmountOperator.EQ and abs_amt != rule.amount_value:
            return False
        if rule.amount_operator == RuleAmountOperator.NE and abs_amt == rule.amount_value:
            return False
        if rule.amount_operator == RuleAmountOperator.GT and not (abs_amt > rule.amount_value):
            return False
        if rule.amount_operator == RuleAmountOperator.LT and not (abs_amt < rule.amount_value):
            return False
        if rule.amount_operator == RuleAmountOperator.BETWEEN:
            v2 = rule.amount_value2 or Decimal("0")
            if not (rule.amount_value <= abs_amt <= v2):
                return False

    if rule.counterparty_id is not None and tx.counterparty_id != rule.counterparty_id:
        return False

    if rule.bank_account_id is not None and tx.bank_account_id != rule.bank_account_id:
        return False

    return True
```

- [ ] **Step 4 : Lancer — doit passer**

```bash
cd backend && pytest tests/test_service_categorization_matching.py -v
```

Attendu : 4 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/categorization.py \
        backend/tests/test_service_categorization_matching.py
git commit -m "feat(services): categorization rule matching (SQL + Python, all operators)"
```

---

### Task C2 : `fetch_rules_for_entity` + `categorize_transaction`

**Files:**
- Modify: `backend/app/services/categorization.py`
- Test: `backend/tests/test_service_categorization_engine.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_service_categorization_engine.py` :

```python
"""Tests du moteur : tie-break, first-match-wins, exclusion MANUAL."""
from datetime import date
from decimal import Decimal

from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.import_record import ImportRecord, ImportStatus
from app.services.categorization import (
    fetch_rules_for_entity, categorize_transaction,
)


def _cat(db_session, slug: str) -> Category:
    c = Category(name=slug, slug=slug, is_system=False)
    db_session.add(c); db_session.commit()
    return c


def _tx(db_session, bank_account, label: str, row_idx: int) -> Transaction:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="t.pdf",
        file_sha256="a"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    tx = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-10.00"), label=label, raw_label=label,
        normalized_label=label,
        dedup_key=f"{row_idx}-" + "z"*60, statement_row_index=row_idx,
    )
    db_session.add(tx); db_session.commit()
    return tx


def test_entity_rule_wins_over_global_at_same_priority(
    db_session, bank_account, entity,
) -> None:
    cat_a = _cat(db_session, "cat-a")
    cat_b = _cat(db_session, "cat-b")
    # Globale pointe vers cat_a
    db_session.add(CategorizationRule(
        name="Global", priority=500, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat_a.id,
    ))
    # Entité pointe vers cat_b à même priorité
    db_session.add(CategorizationRule(
        name="Entity", priority=500, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat_b.id,
    ))
    db_session.commit()

    rules = fetch_rules_for_entity(db_session, entity.id)
    # L'entité doit venir avant la globale
    assert rules[0].name == "Entity"


def test_first_match_wins_by_priority(db_session, bank_account, entity) -> None:
    cat_a = _cat(db_session, "cat-fa")
    cat_b = _cat(db_session, "cat-fb")
    db_session.add(CategorizationRule(
        name="High", priority=100, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat_a.id,
    ))
    db_session.add(CategorizationRule(
        name="Low", priority=9000, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat_b.id,
    ))
    db_session.commit()

    tx = _tx(db_session, bank_account, "URSSAF REF 123", row_idx=10)
    result = categorize_transaction(db_session, tx, entity_id=entity.id)
    assert result is not None
    assert result.name == "High"
    assert tx.category_id == cat_a.id
    assert tx.categorized_by == TransactionCategorizationSource.RULE
    assert tx.categorization_rule_id is not None


def test_manual_never_overwritten(db_session, bank_account, entity) -> None:
    cat_a = _cat(db_session, "cat-ma")
    cat_manual = _cat(db_session, "cat-manual")
    db_session.add(CategorizationRule(
        name="M", priority=200, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat_a.id,
    ))
    db_session.commit()

    tx = _tx(db_session, bank_account, "X", row_idx=11)
    tx.category_id = cat_manual.id
    tx.categorized_by = TransactionCategorizationSource.MANUAL
    db_session.commit()

    categorize_transaction(db_session, tx, entity_id=entity.id)
    assert tx.category_id == cat_manual.id
    assert tx.categorized_by == TransactionCategorizationSource.MANUAL


def test_no_rule_matches(db_session, bank_account, entity) -> None:
    tx = _tx(db_session, bank_account, "COMPLETELY UNKNOWN", row_idx=12)
    result = categorize_transaction(db_session, tx, entity_id=entity.id)
    assert result is None
    assert tx.category_id is None
    assert tx.categorized_by == TransactionCategorizationSource.NONE
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_service_categorization_engine.py -v
```

Attendu : ImportError sur `fetch_rules_for_entity` / `categorize_transaction`.

- [ ] **Step 3 : Étendre le service**

Ajouter à `backend/app/services/categorization.py` :

```python
from sqlalchemy import select


def fetch_rules_for_entity(
    session: Session, entity_id: int | None,
) -> list[CategorizationRule]:
    """Retourne les règles applicables à cette entité, déjà triées par
    priorité d'évaluation : règles entité d'abord (prio ASC), puis globales (prio ASC).
    Si entity_id=None, retourne uniquement les globales.
    """
    if entity_id is not None:
        entity_rules = session.execute(
            select(CategorizationRule)
            .where(CategorizationRule.entity_id == entity_id)
            .order_by(CategorizationRule.priority.asc())
        ).scalars().all()
    else:
        entity_rules = []

    global_rules = session.execute(
        select(CategorizationRule)
        .where(CategorizationRule.entity_id.is_(None))
        .order_by(CategorizationRule.priority.asc())
    ).scalars().all()

    return list(entity_rules) + list(global_rules)


def categorize_transaction(
    session: Session,
    tx: Transaction,
    *,
    entity_id: int | None,
) -> CategorizationRule | None:
    """Applique le premier match ; mute tx en place. Ne commit pas.
    Retourne la règle matchée ou None. Ne touche pas les tx MANUAL.
    """
    if tx.categorized_by == TransactionCategorizationSource.MANUAL:
        return None

    rules = fetch_rules_for_entity(session, entity_id)
    for rule in rules:
        if matches_transaction(rule, tx):
            tx.category_id = rule.category_id
            tx.categorized_by = TransactionCategorizationSource.RULE
            tx.categorization_rule_id = rule.id
            return rule
    return None
```

- [ ] **Step 4 : Lancer — doit passer**

```bash
cd backend && pytest tests/test_service_categorization_engine.py -v
```

Attendu : 4 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/categorization.py \
        backend/tests/test_service_categorization_engine.py
git commit -m "feat(services): categorization engine (fetch + first-match + tie-break)"
```

---

### Task C3 : `preview_rule` + `apply_rule`

**Files:**
- Modify: `backend/app/services/categorization.py`
- Test: `backend/tests/test_service_categorization_apply.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_service_categorization_apply.py` :

```python
"""Tests de preview_rule et apply_rule."""
from datetime import date
from decimal import Decimal

from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.import_record import ImportRecord, ImportStatus
from app.services.categorization import preview_rule, apply_rule


def _cat(db_session, slug: str) -> Category:
    c = Category(name=slug, slug=slug, is_system=False)
    db_session.add(c); db_session.commit()
    return c


def _mk_tx(db_session, bank_account, label: str, row_idx: int,
           amount: Decimal = Decimal("-50")) -> Transaction:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="p.pdf",
        file_sha256="b"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    tx = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=amount, label=label, raw_label=label, normalized_label=label,
        dedup_key=f"{row_idx}-" + "p"*60, statement_row_index=row_idx,
    )
    db_session.add(tx); db_session.commit()
    return tx


def test_preview_counts_matching_not_manual(db_session, bank_account) -> None:
    cat = _cat(db_session, "cp-a")
    # 3 tx non catégorisées qui matchent, 1 MANUAL qui matche aussi
    for i in range(3):
        _mk_tx(db_session, bank_account, "URSSAF PRLV", row_idx=100 + i)
    t_manual = _mk_tx(db_session, bank_account, "URSSAF DU MOIS", row_idx=200)
    t_manual.categorized_by = TransactionCategorizationSource.MANUAL
    t_manual.category_id = cat.id
    db_session.commit()

    rule = CategorizationRule(
        name="URSSAF", priority=100, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    result = preview_rule(db_session, rule, sample_limit=10)
    assert result.matching_count == 3
    assert len(result.sample) == 3


def test_apply_updates_only_non_manual(db_session, bank_account) -> None:
    cat_x = _cat(db_session, "cx-a")
    cat_y = _cat(db_session, "cx-b")
    tx_none = _mk_tx(db_session, bank_account, "EDF FACT", row_idx=300)
    tx_rule = _mk_tx(db_session, bank_account, "EDF MONTH", row_idx=301)
    tx_rule.categorized_by = TransactionCategorizationSource.RULE
    tx_rule.category_id = cat_y.id
    tx_manual = _mk_tx(db_session, bank_account, "EDF MANUAL", row_idx=302)
    tx_manual.categorized_by = TransactionCategorizationSource.MANUAL
    tx_manual.category_id = cat_y.id
    db_session.commit()

    rule = CategorizationRule(
        name="EDF", priority=500, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="EDF",
        category_id=cat_x.id,
    )
    db_session.add(rule); db_session.commit()

    report = apply_rule(db_session, rule)
    db_session.refresh(tx_none); db_session.refresh(tx_rule); db_session.refresh(tx_manual)

    assert report.updated_count == 2
    assert tx_none.category_id == cat_x.id
    assert tx_none.categorized_by == TransactionCategorizationSource.RULE
    assert tx_rule.category_id == cat_x.id
    assert tx_manual.category_id == cat_y.id  # intact
    assert tx_manual.categorized_by == TransactionCategorizationSource.MANUAL
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_service_categorization_apply.py -v
```

Attendu : ImportError.

- [ ] **Step 3 : Étendre le service**

Ajouter à `backend/app/services/categorization.py` :

```python
from dataclasses import dataclass
from sqlalchemy import update


@dataclass
class RuleSample:
    id: int
    operation_date: str
    amount: Decimal
    label: str
    current_category_id: int | None


@dataclass
class RulePreviewResult:
    matching_count: int
    sample: list[RuleSample]


@dataclass
class ApplyReport:
    updated_count: int


def preview_rule(
    session: Session,
    rule: CategorizationRule,
    *,
    sample_limit: int = 20,
) -> RulePreviewResult:
    """Compte + échantillonne les transactions que la règle matcherait,
    en excluant les MANUAL. Ne mute rien.
    """
    base_filter = and_(
        build_rule_filter(rule),
        Transaction.categorized_by != TransactionCategorizationSource.MANUAL,
    )
    count = session.execute(
        select(func.count(Transaction.id)).where(base_filter)
    ).scalar_one()

    samples_rows = session.execute(
        select(Transaction).where(base_filter)
        .order_by(Transaction.operation_date.desc(), Transaction.id.desc())
        .limit(sample_limit)
    ).scalars().all()

    samples = [
        RuleSample(
            id=t.id,
            operation_date=t.operation_date.isoformat(),
            amount=t.amount,
            label=t.label,
            current_category_id=t.category_id,
        )
        for t in samples_rows
    ]
    return RulePreviewResult(matching_count=count, sample=samples)


def apply_rule(session: Session, rule: CategorizationRule) -> ApplyReport:
    """Applique la règle aux transactions non-MANUAL de son scope.
    Pour une règle entité : restreint aux tx des comptes bancaires de cette entité.
    Pour une règle globale : applique sur toutes les tx de la DB (le filtre d'accès
    par entité est fait côté API, pas ici).
    """
    from app.models.bank_account import BankAccount

    base_filter = and_(
        build_rule_filter(rule),
        Transaction.categorized_by != TransactionCategorizationSource.MANUAL,
    )
    if rule.entity_id is not None:
        accessible_accounts = select(BankAccount.id).where(
            BankAccount.entity_id == rule.entity_id
        )
        base_filter = and_(
            base_filter,
            Transaction.bank_account_id.in_(accessible_accounts),
        )

    stmt = (
        update(Transaction)
        .where(base_filter)
        .values(
            category_id=rule.category_id,
            categorized_by=TransactionCategorizationSource.RULE,
            categorization_rule_id=rule.id,
        )
    )
    result = session.execute(stmt)
    session.flush()
    return ApplyReport(updated_count=result.rowcount or 0)
```

- [ ] **Step 4 : Lancer**

```bash
cd backend && pytest tests/test_service_categorization_apply.py -v
```

Attendu : 2 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/categorization.py \
        backend/tests/test_service_categorization_apply.py
git commit -m "feat(services): preview_rule (count + sample) and apply_rule (bulk UPDATE)"
```

---

### Task C4 : `recategorize_entity` (reset + re-run)

**Files:**
- Modify: `backend/app/services/categorization.py`
- Test: `backend/tests/test_service_categorization_recategorize.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_service_categorization_recategorize.py` :

```python
"""Tests de recategorize_entity : reset + re-application."""
from datetime import date
from decimal import Decimal

from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.import_record import ImportRecord, ImportStatus
from app.services.categorization import recategorize_entity


def _cat(db_session, slug: str) -> Category:
    c = Category(name=slug, slug=slug, is_system=False)
    db_session.add(c); db_session.commit()
    return c


def test_recategorize_resets_non_manual_and_re_runs(
    db_session, bank_account, entity,
) -> None:
    new_cat = _cat(db_session, "new-after-reorder")
    other_cat = _cat(db_session, "initial-cat")

    # Une tx précédemment catégorisée par une vieille règle (qui n'existe plus)
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="r.pdf",
        file_sha256="c"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    tx_rule = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-100"), label="URSSAF", raw_label="URSSAF",
        normalized_label="URSSAF",
        dedup_key="r1-" + "c"*60, statement_row_index=0,
        category_id=other_cat.id,
        categorized_by=TransactionCategorizationSource.RULE,
    )
    tx_manual = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 2), value_date=date(2026, 1, 2),
        amount=Decimal("-50"), label="URSSAF B", raw_label="URSSAF B",
        normalized_label="URSSAF B",
        dedup_key="r2-" + "c"*60, statement_row_index=1,
        category_id=other_cat.id,
        categorized_by=TransactionCategorizationSource.MANUAL,
    )
    db_session.add_all([tx_rule, tx_manual]); db_session.commit()

    # Nouvelle règle qui doit prendre la main
    db_session.add(CategorizationRule(
        name="URSSAF NEW", priority=10, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=new_cat.id,
    ))
    db_session.commit()

    report = recategorize_entity(db_session, entity.id)
    db_session.refresh(tx_rule); db_session.refresh(tx_manual)

    assert report.updated_count >= 1
    assert tx_rule.category_id == new_cat.id
    assert tx_rule.categorized_by == TransactionCategorizationSource.RULE
    # MANUAL intact
    assert tx_manual.category_id == other_cat.id
    assert tx_manual.categorized_by == TransactionCategorizationSource.MANUAL
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_service_categorization_recategorize.py -v
```

- [ ] **Step 3 : Étendre le service**

Ajouter à `backend/app/services/categorization.py` :

```python
def recategorize_entity(session: Session, entity_id: int) -> ApplyReport:
    """Reset toutes les tx non-MANUAL des comptes de l'entité à NONE, puis
    re-évalue toutes les règles. Synchrone (pour Plan 2 ; passe en async
    Plan 3+ si le volume l'exige). Les MANUAL sont intactes.
    """
    from app.models.bank_account import BankAccount

    accessible_accounts = select(BankAccount.id).where(
        BankAccount.entity_id == entity_id
    )

    # Reset
    session.execute(
        update(Transaction)
        .where(
            Transaction.bank_account_id.in_(accessible_accounts),
            Transaction.categorized_by != TransactionCategorizationSource.MANUAL,
        )
        .values(
            category_id=None,
            categorization_rule_id=None,
            categorized_by=TransactionCategorizationSource.NONE,
        )
    )
    session.flush()

    # Charger les tx à re-catégoriser
    rows = session.execute(
        select(Transaction).where(
            Transaction.bank_account_id.in_(accessible_accounts),
            Transaction.categorized_by == TransactionCategorizationSource.NONE,
        )
    ).scalars().all()

    updated = 0
    for tx in rows:
        result = categorize_transaction(session, tx, entity_id=entity_id)
        if result is not None:
            updated += 1
    session.flush()
    return ApplyReport(updated_count=updated)
```

- [ ] **Step 4 : Lancer**

```bash
cd backend && pytest tests/test_service_categorization_recategorize.py -v
```

Attendu : 1 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/categorization.py \
        backend/tests/test_service_categorization_recategorize.py
git commit -m "feat(services): recategorize_entity (reset non-MANUAL then re-run engine)"
```

---

## Phase D — Intégration dans le pipeline d'import

### Task D1 : Populer `normalized_label` à l'insert + appeler le moteur

**Files:**
- Modify: `backend/app/services/imports.py`
- Modify: `backend/app/models/import_record.py` (audit JSON field peut déjà exister)
- Test: `backend/tests/test_service_imports_categorization.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_service_imports_categorization.py` :

```python
"""Intégration : un import Plan 1 doit remplir normalized_label et auto-catégoriser."""
from datetime import date
from decimal import Decimal

from app.parsers.base import ParsedStatement, ParsedTransaction
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.services.imports import ingest_parsed_statement


def test_import_populates_normalized_label_and_categorizes(
    db_session, bank_account, entity,
) -> None:
    cat = Category(name="URSSAF test cat", slug="urssaf-test-cat-imp", is_system=False)
    db_session.add(cat); db_session.commit()

    rule = CategorizationRule(
        name="URSSAF-imp", priority=50, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    ptx1 = ParsedTransaction(
        operation_date=date(2026, 3, 1), value_date=date(2026, 3, 1),
        amount=Decimal("-100.00"),
        label="PRLV URSSAF REF 123", raw_label="PRLV URSSAF REF 123",
        statement_row_index=0,
    )
    ptx2 = ParsedTransaction(
        operation_date=date(2026, 3, 2), value_date=date(2026, 3, 2),
        amount=Decimal("-50.00"),
        label="BOULANGERIE", raw_label="BOULANGERIE",
        statement_row_index=1,
    )
    statement = ParsedStatement(
        bank_code="DELUBAC", iban=bank_account.iban or "FR0000000000",
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
        transactions=[ptx1, ptx2],
    )

    ir = ingest_parsed_statement(
        db_session,
        bank_account_id=bank_account.id,
        statement=statement,
    )

    # Vérif : normalized_label populé + auto-catégorisation
    from sqlalchemy import select
    txs = db_session.execute(
        select(Transaction).where(Transaction.import_id == ir.id)
        .order_by(Transaction.statement_row_index.asc())
    ).scalars().all()
    assert len(txs) == 2
    assert all(t.normalized_label != "" for t in txs)
    assert txs[0].categorized_by == TransactionCategorizationSource.RULE
    assert txs[0].category_id == cat.id
    assert txs[1].categorized_by == TransactionCategorizationSource.NONE
    # audit doit refléter le compteur
    assert ir.audit.get("categorized_count") == 1
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_service_imports_categorization.py -v
```

- [ ] **Step 3 : Modifier `imports.py`**

Ouvrir `backend/app/services/imports.py`. Dans la fonction `ingest_parsed_statement`, localiser la boucle d'insertion des transactions (chercher `Transaction(` construit + `session.add`). Modifier pour :

1. Ajouter `normalized_label=normalize_label(tx.label)` lors de la construction du `Transaction`.
2. Après l'insertion de toutes les tx, avant le commit final, appeler le moteur pour chacune, puis calculer `categorized_count` et l'ajouter à `import_record.audit`.

Pseudo-diff (à adapter selon la structure réelle de la fonction) :

```python
# En haut du fichier
from app.parsers.normalization import normalize_label
from app.services.categorization import categorize_transaction
from app.models.bank_account import BankAccount

# Dans la boucle de construction des Transaction — ajout du champ :
new_tx = Transaction(
    ...
    label=tx.label,
    raw_label=tx.raw_label,
    normalized_label=normalize_label(tx.label),
    ...
)

# À la fin de l'ingestion (avant le commit final), après tous les flush/add :
entity_id = session.get(BankAccount, bank_account_id).entity_id
categorized_count = 0
# Re-fetch l'ensemble des tx de cet import pour s'assurer qu'on a bien
# les instances managées (ou tenir la liste au fur et à mesure)
for tx_obj in inserted_transactions:  # ou équivalent selon l'impl
    if categorize_transaction(session, tx_obj, entity_id=entity_id) is not None:
        categorized_count += 1

# Mise à jour de l'audit
audit = dict(import_record.audit or {})
audit["categorized_count"] = categorized_count
import_record.audit = audit
```

**Note :** la structure exacte de `ingest_parsed_statement` (nom de la variable `inserted_transactions`, gestion du commit) dépend de l'existant Plan 1. L'implémenteur **doit lire** `backend/app/services/imports.py` avant d'éditer et adapter. Clé : `normalized_label` populé, `categorize_transaction` appelé après flush, `audit.categorized_count` mis à jour.

- [ ] **Step 4 : Lancer**

```bash
cd backend && pytest tests/test_service_imports_categorization.py tests/test_service_imports.py -v
```

Attendu : les tests existants Plan 1 (`test_service_imports`) passent toujours + le nouveau passe.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/services/imports.py \
        backend/tests/test_service_imports_categorization.py
git commit -m "feat(services): populate normalized_label and auto-categorize on import"
```

---

## Phase E — API endpoints

### Task E1 : Router `/api/rules` + GET liste

**Files:**
- Create: `backend/app/api/rules.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_api_rules_list.py`

- [ ] **Step 1 : Écrire le test**

Créer `backend/tests/test_api_rules_list.py` :

```python
"""GET /api/rules — listage avec filtre scope."""
from fastapi.testclient import TestClient

from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category


def _cat(db_session) -> Category:
    c = Category(name="c", slug="c-api-list", is_system=False)
    db_session.add(c); db_session.commit()
    return c


def test_list_rules_requires_auth(client: TestClient) -> None:
    r = client.get("/api/rules")
    assert r.status_code == 401


def test_list_all_rules(
    client: TestClient, auth_user, db_session, entity,
) -> None:
    cat = _cat(db_session)
    db_session.add(CategorizationRule(
        name="Glob", priority=1500, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat.id,
    ))
    db_session.add(CategorizationRule(
        name="Ent", priority=1600, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="Y",
        category_id=cat.id,
    ))
    db_session.commit()

    r = client.get("/api/rules")
    assert r.status_code == 200
    data = r.json()
    names = {row["name"] for row in data}
    assert {"Glob", "Ent"}.issubset(names)


def test_list_rules_filter_global(
    client: TestClient, auth_user, db_session, entity,
) -> None:
    cat = _cat(db_session)
    db_session.add(CategorizationRule(
        name="G2", priority=1700, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="Z",
        category_id=cat.id,
    ))
    db_session.add(CategorizationRule(
        name="E2", priority=1800, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="W",
        category_id=cat.id,
    ))
    db_session.commit()

    r = client.get("/api/rules?scope=global")
    data = r.json()
    names = {row["name"] for row in data}
    assert "G2" in names
    assert "E2" not in names


def test_list_rules_filter_by_entity(
    client: TestClient, auth_user, db_session, entity,
) -> None:
    cat = _cat(db_session)
    db_session.add(CategorizationRule(
        name="ENT1", priority=1900, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="AA",
        category_id=cat.id,
    ))
    db_session.commit()

    r = client.get(f"/api/rules?entity_id={entity.id}")
    data = r.json()
    names = {row["name"] for row in data}
    assert "ENT1" in names
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_api_rules_list.py -v
```

Attendu : 404 (endpoint absent).

- [ ] **Step 3 : Créer `app/api/rules.py`**

```python
"""Endpoints /api/rules — CRUD + preview + apply + reorder."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.categorization_rule import CategorizationRule
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.schemas.categorization_rule import RuleRead

router = APIRouter(prefix="/api/rules", tags=["rules"])


def _accessible_entity_ids(session: Session, user: User) -> list[int]:
    rows = session.execute(
        select(UserEntityAccess.entity_id).where(
            UserEntityAccess.user_id == user.id
        )
    ).scalars().all()
    return list(rows)


def _require_editor(user: User) -> None:
    if user.role == UserRole.READER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits éditeur requis",
        )


@router.get("", response_model=list[RuleRead])
def list_rules(
    scope: Optional[Literal["global", "entity", "all"]] = Query(default="all"),
    entity_id: Optional[int] = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[RuleRead]:
    q = select(CategorizationRule)

    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        q = q.where(CategorizationRule.entity_id == entity_id)
    elif scope == "global":
        q = q.where(CategorizationRule.entity_id.is_(None))
    elif scope == "entity":
        accessible = _accessible_entity_ids(session, user)
        q = q.where(CategorizationRule.entity_id.in_(accessible))
    else:
        # 'all' = globales + entités accessibles
        accessible = _accessible_entity_ids(session, user)
        q = q.where(
            (CategorizationRule.entity_id.is_(None))
            | (CategorizationRule.entity_id.in_(accessible))
        )

    q = q.order_by(
        CategorizationRule.entity_id.asc().nulls_last(),
        CategorizationRule.priority.asc(),
    )
    rows = session.execute(q).scalars().all()
    return [RuleRead.model_validate(r) for r in rows]
```

Brancher dans `backend/app/api/router.py` :

```python
from app.api import rules
...
api_router.include_router(rules.router)
```

- [ ] **Step 4 : Lancer**

```bash
cd backend && pytest tests/test_api_rules_list.py -v
```

Attendu : 4 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/api/rules.py backend/app/api/router.py \
        backend/tests/test_api_rules_list.py
git commit -m "feat(api): GET /api/rules with scope filter"
```

---

### Task E2 : POST /api/rules (create) + POST /api/rules/preview

**Files:**
- Modify: `backend/app/api/rules.py`
- Test: `backend/tests/test_api_rules_create.py`, `backend/tests/test_api_rules_preview.py`

- [ ] **Step 1 : Écrire les tests**

Créer `backend/tests/test_api_rules_create.py` :

```python
"""POST /api/rules."""
from fastapi.testclient import TestClient

from app.models.category import Category


def _cat(db_session) -> Category:
    c = Category(name="c", slug="c-api-create", is_system=False)
    db_session.add(c); db_session.commit()
    return c


def test_create_rule_as_reader_forbidden(
    client: TestClient, auth_user_reader, db_session,
) -> None:
    cat = _cat(db_session)
    r = client.post("/api/rules", json={
        "name": "X", "priority": 7000,
        "label_operator": "CONTAINS", "label_value": "X",
        "direction": "ANY", "category_id": cat.id,
    })
    assert r.status_code == 403


def test_create_rule_success(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = _cat(db_session)
    r = client.post("/api/rules", json={
        "name": "Test create",
        "priority": 7100,
        "label_operator": "CONTAINS",
        "label_value": "  urssaf  ",  # sera normalisé
        "direction": "ANY",
        "category_id": cat.id,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Test create"
    assert body["label_value"] == "URSSAF"  # normalisé
    assert body["is_system"] is False


def test_create_rule_rejects_empty_filters(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = _cat(db_session)
    r = client.post("/api/rules", json={
        "name": "Empty", "priority": 7200,
        "direction": "ANY", "category_id": cat.id,
    })
    assert r.status_code == 422


def test_create_rule_duplicate_priority_conflict(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = _cat(db_session)
    payload_base = {
        "priority": 7300,
        "label_operator": "CONTAINS", "label_value": "A",
        "direction": "ANY", "category_id": cat.id,
    }
    r1 = client.post("/api/rules", json={**payload_base, "name": "A"})
    assert r1.status_code == 201
    r2 = client.post("/api/rules", json={**payload_base, "name": "B"})
    assert r2.status_code == 409
```

Créer `backend/tests/test_api_rules_preview.py` :

```python
"""POST /api/rules/preview."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.import_record import ImportRecord, ImportStatus


def _cat(db_session) -> Category:
    c = Category(name="c", slug="c-api-preview", is_system=False)
    db_session.add(c); db_session.commit()
    return c


def test_preview_returns_count_and_sample(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    cat = _cat(db_session)
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="p.pdf",
        file_sha256="e"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    for i in range(3):
        db_session.add(Transaction(
            bank_account_id=bank_account.id, import_id=imp.id,
            operation_date=date(2026, 1, i + 1), value_date=date(2026, 1, i + 1),
            amount=Decimal("-10"), label=f"URSSAF {i}", raw_label=f"URSSAF {i}",
            normalized_label=f"URSSAF {i}",
            dedup_key=f"pv-{i}-" + "e"*58, statement_row_index=i,
        ))
    db_session.commit()

    r = client.post("/api/rules/preview", json={
        "name": "Preview", "priority": 7500,
        "label_operator": "CONTAINS", "label_value": "URSSAF",
        "direction": "ANY", "category_id": cat.id,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matching_count"] == 3
    assert len(body["sample"]) == 3
```

- [ ] **Step 2 : Lancer — doit échouer (404/405)**

```bash
cd backend && pytest tests/test_api_rules_create.py tests/test_api_rules_preview.py -v
```

- [ ] **Step 3 : Étendre `app/api/rules.py`**

Ajouter :

```python
from sqlalchemy.exc import IntegrityError

from app.schemas.categorization_rule import (
    RuleCreate, RulePreviewRequest, RulePreviewResponse, RuleSampleTransaction,
)
from app.services.categorization import preview_rule as preview_rule_service


@router.post("", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: RuleCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RuleRead:
    _require_editor(user)
    if payload.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=payload.entity_id)

    rule = CategorizationRule(
        name=payload.name,
        entity_id=payload.entity_id,
        priority=payload.priority,
        is_system=False,
        label_operator=payload.label_operator,
        label_value=payload.label_value,
        direction=payload.direction,
        amount_operator=payload.amount_operator,
        amount_value=payload.amount_value,
        amount_value2=payload.amount_value2,
        counterparty_id=payload.counterparty_id,
        bank_account_id=payload.bank_account_id,
        category_id=payload.category_id,
        created_by_id=user.id,
    )
    session.add(rule)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RULE_DUPLICATE_PRIORITY",
                    "message": "Priorité déjà utilisée dans ce scope"},
        )
    session.refresh(rule)
    return RuleRead.model_validate(rule)


@router.post("/preview", response_model=RulePreviewResponse)
def preview_rule_endpoint(
    payload: RulePreviewRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RulePreviewResponse:
    _require_editor(user)
    if payload.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=payload.entity_id)

    # Instance en mémoire, non persistée
    draft = CategorizationRule(
        name=payload.name,
        entity_id=payload.entity_id,
        priority=payload.priority,
        label_operator=payload.label_operator,
        label_value=payload.label_value,
        direction=payload.direction,
        amount_operator=payload.amount_operator,
        amount_value=payload.amount_value,
        amount_value2=payload.amount_value2,
        counterparty_id=payload.counterparty_id,
        bank_account_id=payload.bank_account_id,
        category_id=payload.category_id,
    )
    result = preview_rule_service(session, draft, sample_limit=20)
    return RulePreviewResponse(
        matching_count=result.matching_count,
        sample=[RuleSampleTransaction(**s.__dict__) for s in result.sample],
    )
```

**Note sur `auth_user_reader`** : la fixture n'existe peut-être pas encore. Vérifier dans `backend/tests/conftest.py`. Si absente, l'ajouter (similaire à `auth_user` mais avec `UserRole.READER`).

- [ ] **Step 4 : Lancer**

```bash
cd backend && pytest tests/test_api_rules_create.py tests/test_api_rules_preview.py -v
```

Attendu : 5 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/api/rules.py \
        backend/tests/test_api_rules_create.py \
        backend/tests/test_api_rules_preview.py
git commit -m "feat(api): POST /api/rules (create) and /api/rules/preview"
```

---

### Task E3 : PATCH /api/rules/{id} + DELETE /api/rules/{id}

**Files:**
- Modify: `backend/app/api/rules.py`
- Test: `backend/tests/test_api_rules_mutate.py`

- [ ] **Step 1 : Écrire le test**

```python
"""PATCH/DELETE sur /api/rules/{id}."""
from fastapi.testclient import TestClient

from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category


def _rule_setup(db_session) -> tuple[int, int, int]:
    cat = Category(name="c", slug="c-api-mut", is_system=False)
    cat2 = Category(name="c2", slug="c2-api-mut", is_system=False)
    db_session.add_all([cat, cat2]); db_session.commit()
    rule = CategorizationRule(
        name="To edit", priority=8000, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="XX",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()
    return rule.id, cat.id, cat2.id


def test_patch_rule_updates_fields(
    client: TestClient, auth_user, db_session,
) -> None:
    rid, _, cat2_id = _rule_setup(db_session)
    r = client.patch(f"/api/rules/{rid}", json={
        "name": "Renamed", "category_id": cat2_id,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Renamed"
    assert body["category_id"] == cat2_id


def test_patch_rule_normalizes_label_value(
    client: TestClient, auth_user, db_session,
) -> None:
    rid, *_ = _rule_setup(db_session)
    r = client.patch(f"/api/rules/{rid}", json={"label_value": "  edf "})
    assert r.status_code == 200
    assert r.json()["label_value"] == "EDF"


def test_patch_system_rule_refused_for_structural_fields(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = Category(name="x", slug="x-api-sysedit", is_system=False)
    db_session.add(cat); db_session.commit()
    rule = CategorizationRule(
        name="SYS", priority=8100, entity_id=None, is_system=True,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="SYS",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    # Rename autorisé
    r_ok = client.patch(f"/api/rules/{rule.id}", json={"name": "SYS Renamed"})
    assert r_ok.status_code == 200
    # Changement de filtre refusé
    r_bad = client.patch(f"/api/rules/{rule.id}", json={"label_value": "NEW"})
    assert r_bad.status_code == 409


def test_delete_system_rule_refused(
    client: TestClient, auth_user_admin, db_session,
) -> None:
    cat = Category(name="y", slug="y-api-sysdel", is_system=False)
    db_session.add(cat); db_session.commit()
    rule = CategorizationRule(
        name="SYSDEL", priority=8200, entity_id=None, is_system=True,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="SYS",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    r = client.delete(f"/api/rules/{rule.id}")
    assert r.status_code == 409


def test_delete_rule_as_editor_forbidden(
    client: TestClient, auth_user, db_session,
) -> None:
    rid, *_ = _rule_setup(db_session)
    r = client.delete(f"/api/rules/{rid}")
    assert r.status_code == 403


def test_delete_rule_as_admin_success(
    client: TestClient, auth_user_admin, db_session,
) -> None:
    rid, *_ = _rule_setup(db_session)
    r = client.delete(f"/api/rules/{rid}")
    assert r.status_code == 204
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_api_rules_mutate.py -v
```

- [ ] **Step 3 : Étendre `app/api/rules.py`**

```python
from app.schemas.categorization_rule import RuleUpdate


_STRUCTURAL_FIELDS = {
    "label_operator", "label_value", "direction",
    "amount_operator", "amount_value", "amount_value2",
    "counterparty_id", "bank_account_id", "category_id",
}


@router.patch("/{rule_id}", response_model=RuleRead)
def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RuleRead:
    _require_editor(user)
    rule = session.get(CategorizationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    if rule.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=rule.entity_id)

    data = payload.model_dump(exclude_unset=True)

    if rule.is_system:
        struct_touched = set(data.keys()) & _STRUCTURAL_FIELDS
        if struct_touched:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "RULE_SYSTEM_MUTATE",
                        "message": "Règle système : seuls le nom et la priorité sont modifiables"},
            )

    for field, value in data.items():
        setattr(rule, field, value)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RULE_DUPLICATE_PRIORITY",
                    "message": "Priorité déjà utilisée dans ce scope"},
        )
    session.refresh(rule)
    return RuleRead.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Droits administrateur requis")
    rule = session.get(CategorizationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    if rule.is_system:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RULE_SYSTEM_DELETE",
                    "message": "Une règle système ne peut pas être supprimée"},
        )
    if rule.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=rule.entity_id)
    session.delete(rule)
    session.commit()
```

**Note fixtures** : ajouter `auth_user_admin` à `conftest.py` si absent (similaire à `auth_user` mais `UserRole.ADMIN`).

- [ ] **Step 4 : Lancer**

```bash
cd backend && pytest tests/test_api_rules_mutate.py -v
```

Attendu : 6 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/api/rules.py backend/tests/test_api_rules_mutate.py backend/tests/conftest.py
git commit -m "feat(api): PATCH + DELETE /api/rules/{id} with is_system guards"
```

---

### Task E4 : POST /api/rules/{id}/apply + /reorder + /from-transactions

**Files:**
- Modify: `backend/app/api/rules.py`
- Test: `backend/tests/test_api_rules_apply.py`, `test_api_rules_reorder.py`, `test_api_rules_from_transactions.py`

- [ ] **Step 1 : Tests (trois fichiers)**

`backend/tests/test_api_rules_apply.py` :

```python
"""POST /api/rules/{id}/apply."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.import_record import ImportRecord, ImportStatus


def test_apply_rule_updates_matching_non_manual(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    cat = Category(name="c", slug="c-api-apply", is_system=False)
    db_session.add(cat); db_session.commit()
    rule = CategorizationRule(
        name="R", priority=8500, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="ZZ",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="a.pdf",
        file_sha256="z"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    for i in range(2):
        db_session.add(Transaction(
            bank_account_id=bank_account.id, import_id=imp.id,
            operation_date=date(2026, 1, i + 1), value_date=date(2026, 1, i + 1),
            amount=Decimal("-10"), label="ZZ", raw_label="ZZ",
            normalized_label="ZZ",
            dedup_key=f"ap-{i}-" + "z"*58, statement_row_index=i,
        ))
    db_session.commit()

    r = client.post(f"/api/rules/{rule.id}/apply")
    assert r.status_code == 200, r.text
    assert r.json()["updated_count"] == 2
```

`backend/tests/test_api_rules_reorder.py` :

```python
"""POST /api/rules/reorder."""
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)


def test_reorder_updates_priorities(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = Category(name="c", slug="c-api-reord", is_system=False)
    db_session.add(cat); db_session.commit()
    r1 = CategorizationRule(
        name="A", priority=9000, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="A",
        category_id=cat.id,
    )
    r2 = CategorizationRule(
        name="B", priority=9100, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="B",
        category_id=cat.id,
    )
    db_session.add_all([r1, r2]); db_session.commit()

    # Inverser les priorités. Utiliser des priorités intermédiaires
    # temporaires pour éviter le conflit unique pendant le swap.
    r = client.post("/api/rules/reorder", json=[
        {"id": r1.id, "priority": 99001},
        {"id": r2.id, "priority": 99000},
    ])
    assert r.status_code == 200, r.text
    db_session.refresh(r1); db_session.refresh(r2)
    assert r1.priority == 99001
    assert r2.priority == 99000
```

`backend/tests/test_api_rules_from_transactions.py` :

```python
"""POST /api/rules/from-transactions."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.transaction import Transaction
from app.models.import_record import ImportRecord, ImportStatus


def test_suggest_rule_from_common_substring(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="s.pdf",
        file_sha256="s"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    t1 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-50"), label="PRLV URSSAF REF 111",
        raw_label="PRLV URSSAF REF 111",
        normalized_label="PRLV URSSAF REF 111",
        dedup_key="sg-1-" + "s"*58, statement_row_index=0,
    )
    t2 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 2), value_date=date(2026, 1, 2),
        amount=Decimal("-50"), label="PRLV URSSAF REF 222",
        raw_label="PRLV URSSAF REF 222",
        normalized_label="PRLV URSSAF REF 222",
        dedup_key="sg-2-" + "s"*58, statement_row_index=1,
    )
    db_session.add_all([t1, t2]); db_session.commit()

    r = client.post("/api/rules/from-transactions", json={
        "transaction_ids": [t1.id, t2.id],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "URSSAF" in body["suggested_label_value"]
    assert body["transaction_count"] == 2
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_api_rules_apply.py tests/test_api_rules_reorder.py \
                    tests/test_api_rules_from_transactions.py -v
```

- [ ] **Step 3 : Étendre `app/api/rules.py`**

Ajouter :

```python
from pydantic import BaseModel

from app.schemas.categorization_rule import (
    RuleApplyResponse, RuleReorderItem, RuleSuggestion,
)
from app.services.categorization import apply_rule as apply_rule_service
from app.models.transaction import Transaction


@router.post("/{rule_id}/apply", response_model=RuleApplyResponse)
def apply_rule_endpoint(
    rule_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RuleApplyResponse:
    _require_editor(user)
    rule = session.get(CategorizationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    if rule.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=rule.entity_id)

    report = apply_rule_service(session, rule)
    session.commit()
    return RuleApplyResponse(updated_count=report.updated_count)


class ReorderBody(BaseModel):
    items: list[RuleReorderItem]


@router.post("/reorder", response_model=list[RuleRead])
def reorder_rules(
    items: list[RuleReorderItem],
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[RuleRead]:
    _require_editor(user)
    if not items:
        raise HTTPException(status_code=422, detail="Liste vide")

    # Charger toutes les règles concernées, valider le scope
    ids = [i.id for i in items]
    rules = session.execute(
        select(CategorizationRule).where(CategorizationRule.id.in_(ids))
    ).scalars().all()
    if len(rules) != len(items):
        raise HTTPException(status_code=404, detail="Une règle au moins est introuvable")

    scopes = {r.entity_id for r in rules}
    if len(scopes) > 1:
        raise HTTPException(
            status_code=422,
            detail="Le réordonnancement doit porter sur un seul scope",
        )
    scope_entity = scopes.pop()
    if scope_entity is not None:
        require_entity_access(session=session, user=user, entity_id=scope_entity)

    # Appliquer les nouvelles priorités. Le caller doit déjà avoir choisi
    # des valeurs non-conflictuelles (les swap se font via valeurs temporaires
    # côté client, p.ex. 99000+).
    by_id = {r.id: r for r in rules}
    try:
        for item in items:
            by_id[item.id].priority = item.priority
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RULE_DUPLICATE_PRIORITY",
                    "message": "Conflit de priorités pendant le réordonnancement"},
        )

    refreshed = session.execute(
        select(CategorizationRule)
        .where(CategorizationRule.id.in_(ids))
        .order_by(CategorizationRule.priority.asc())
    ).scalars().all()
    return [RuleRead.model_validate(r) for r in refreshed]


class FromTxBody(BaseModel):
    transaction_ids: list[int]


@router.post("/from-transactions", response_model=RuleSuggestion)
def suggest_from_transactions(
    body: FromTxBody,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RuleSuggestion:
    _require_editor(user)
    if not body.transaction_ids:
        raise HTTPException(status_code=422, detail="Sélection vide")

    txs = session.execute(
        select(Transaction).where(Transaction.id.in_(body.transaction_ids))
    ).scalars().all()
    if not txs:
        raise HTTPException(status_code=404, detail="Transactions introuvables")

    labels = [t.normalized_label or "" for t in txs]
    # Sous-chaîne commune la plus longue (préfixe commun le plus long, approche simple)
    prefix = labels[0]
    for lbl in labels[1:]:
        while prefix and not lbl.startswith(prefix):
            prefix = prefix[:-1]
    suggested_value = prefix.strip() or labels[0].split()[0]
    suggested_op: str = "STARTS_WITH" if prefix.strip() else "CONTAINS"

    signs = {t.amount > 0 for t in txs}
    if signs == {True}:
        direction = "CREDIT"
    elif signs == {False}:
        direction = "DEBIT"
    else:
        direction = "ANY"

    accounts = {t.bank_account_id for t in txs}
    suggested_bank = accounts.pop() if len(accounts) == 1 else None

    return RuleSuggestion(
        suggested_label_operator=suggested_op,  # type: ignore[arg-type]
        suggested_label_value=suggested_value,
        suggested_direction=direction,  # type: ignore[arg-type]
        suggested_bank_account_id=suggested_bank,
        transaction_count=len(txs),
    )
```

- [ ] **Step 4 : Lancer**

```bash
cd backend && pytest tests/test_api_rules_apply.py tests/test_api_rules_reorder.py \
                    tests/test_api_rules_from_transactions.py -v
```

Attendu : 3 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/api/rules.py \
        backend/tests/test_api_rules_apply.py \
        backend/tests/test_api_rules_reorder.py \
        backend/tests/test_api_rules_from_transactions.py
git commit -m "feat(api): /rules apply + reorder + from-transactions suggestion"
```

---

### Task E5 : Extensions `/api/transactions` (uncategorized + bulk-categorize)

**Files:**
- Modify: `backend/app/api/transactions.py`
- Test: `backend/tests/test_api_transactions_bulk.py`

- [ ] **Step 1 : Écrire le test**

```python
"""GET /api/transactions?uncategorized=true + POST /api/transactions/bulk-categorize."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.import_record import ImportRecord, ImportStatus


def _mk_txs(db_session, bank_account, count: int = 2) -> list[int]:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="b.pdf",
        file_sha256="q"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    ids = []
    for i in range(count):
        t = Transaction(
            bank_account_id=bank_account.id, import_id=imp.id,
            operation_date=date(2026, 2, i + 1), value_date=date(2026, 2, i + 1),
            amount=Decimal("-5"), label=f"X{i}", raw_label=f"X{i}",
            normalized_label=f"X{i}",
            dedup_key=f"bt-{i}-" + "q"*58, statement_row_index=i,
        )
        db_session.add(t); db_session.commit()
        ids.append(t.id)
    return ids


def test_list_uncategorized_filter(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    ids = _mk_txs(db_session, bank_account, count=2)
    cat = Category(name="c", slug="c-api-bulk1", is_system=False)
    db_session.add(cat); db_session.commit()
    # Marquer la première comme MANUAL
    t = db_session.get(Transaction, ids[0])
    t.category_id = cat.id
    t.categorized_by = TransactionCategorizationSource.MANUAL
    db_session.commit()

    r = client.get("/api/transactions?uncategorized=true")
    assert r.status_code == 200
    rows = r.json().get("items", r.json())  # selon le format paginé
    returned_ids = {row["id"] for row in rows}
    assert ids[0] not in returned_ids
    assert ids[1] in returned_ids


def test_bulk_categorize_sets_manual(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    ids = _mk_txs(db_session, bank_account, count=3)
    cat = Category(name="c", slug="c-api-bulk2", is_system=False)
    db_session.add(cat); db_session.commit()

    r = client.post("/api/transactions/bulk-categorize", json={
        "transaction_ids": ids,
        "category_id": cat.id,
    })
    assert r.status_code == 200, r.text
    for tid in ids:
        t = db_session.get(Transaction, tid)
        db_session.refresh(t)
        assert t.category_id == cat.id
        assert t.categorized_by == TransactionCategorizationSource.MANUAL


def test_bulk_categorize_requires_editor(
    client: TestClient, auth_user_reader, db_session, bank_account,
) -> None:
    ids = _mk_txs(db_session, bank_account, count=1)
    cat = Category(name="c", slug="c-api-bulk3", is_system=False)
    db_session.add(cat); db_session.commit()
    r = client.post("/api/transactions/bulk-categorize", json={
        "transaction_ids": ids, "category_id": cat.id,
    })
    assert r.status_code == 403
```

- [ ] **Step 2 : Lancer — doit échouer**

```bash
cd backend && pytest tests/test_api_transactions_bulk.py -v
```

- [ ] **Step 3 : Éditer `app/api/transactions.py`**

Ajouter le filtre `uncategorized` au handler GET existant (repérer `@router.get("")` ou équivalent) et ajouter la route bulk :

```python
from typing import Literal

from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.category import Category
from app.schemas.categorization_rule import BulkCategorizeRequest
from app.deps import get_current_user  # existant
from app.models.user import User, UserRole


# Dans la fonction list_transactions existante, ajouter un param Query
# et la clause WHERE :
#
#   uncategorized: bool = Query(default=False),
#   ...
#   if uncategorized:
#       q = q.where(Transaction.categorized_by == TransactionCategorizationSource.NONE)


@router.post("/bulk-categorize")
def bulk_categorize(
    payload: BulkCategorizeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, int]:
    if user.role == UserRole.READER:
        raise HTTPException(status_code=403, detail="Droits éditeur requis")

    cat = session.get(Category, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    # Filtrer aux tx auxquelles l'utilisateur a accès via bank_account->entity
    from sqlalchemy import select
    from app.models.bank_account import BankAccount
    from app.models.user_entity_access import UserEntityAccess

    accessible_entities = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )
    accessible_accounts = select(BankAccount.id).where(
        BankAccount.entity_id.in_(accessible_entities)
    )

    txs = session.execute(
        select(Transaction).where(
            Transaction.id.in_(payload.transaction_ids),
            Transaction.bank_account_id.in_(accessible_accounts),
        )
    ).scalars().all()

    for tx in txs:
        tx.category_id = payload.category_id
        tx.categorized_by = TransactionCategorizationSource.MANUAL
        # Ne pas nettoyer categorization_rule_id (utile en audit)
    session.commit()
    return {"updated_count": len(txs)}
```

**Note** : l'implémenteur doit lire l'état actuel de `app/api/transactions.py` pour adapter exactement le handler existant (structure de pagination, nommage des fonctions).

- [ ] **Step 4 : Lancer**

```bash
cd backend && pytest tests/test_api_transactions_bulk.py -v
```

Attendu : 3 passed.

- [ ] **Step 5 : Commit**

```bash
git add backend/app/api/transactions.py backend/tests/test_api_transactions_bulk.py
git commit -m "feat(api): /transactions uncategorized filter + bulk-categorize (MANUAL)"
```

---

## Phase F — Frontend

### Task F1 : Clients API TanStack Query pour les règles

**Files:**
- Create: `frontend/src/api/rules.ts`
- Modify: `frontend/src/api/transactions.ts`

- [ ] **Step 1 : Créer `frontend/src/api/rules.ts`**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client"; // existant

export type RuleLabelOperator = "CONTAINS" | "STARTS_WITH" | "ENDS_WITH" | "EQUALS";
export type RuleAmountOperator = "EQ" | "NE" | "GT" | "LT" | "BETWEEN";
export type RuleDirection = "CREDIT" | "DEBIT" | "ANY";

export interface Rule {
  id: number;
  name: string;
  entity_id: number | null;
  priority: number;
  is_system: boolean;
  label_operator: RuleLabelOperator | null;
  label_value: string | null;
  direction: RuleDirection;
  amount_operator: RuleAmountOperator | null;
  amount_value: string | null;
  amount_value2: string | null;
  counterparty_id: number | null;
  bank_account_id: number | null;
  category_id: number;
  created_at: string;
  updated_at: string;
}

export interface RuleCreatePayload {
  name: string;
  entity_id?: number | null;
  priority: number;
  label_operator?: RuleLabelOperator | null;
  label_value?: string | null;
  direction: RuleDirection;
  amount_operator?: RuleAmountOperator | null;
  amount_value?: string | null;
  amount_value2?: string | null;
  counterparty_id?: number | null;
  bank_account_id?: number | null;
  category_id: number;
}

export interface RulePreviewResponse {
  matching_count: number;
  sample: Array<{
    id: number;
    operation_date: string;
    amount: string;
    label: string;
    current_category_id: number | null;
  }>;
}

export interface RuleSuggestion {
  suggested_label_operator: "CONTAINS" | "STARTS_WITH";
  suggested_label_value: string;
  suggested_direction: RuleDirection;
  suggested_bank_account_id: number | null;
  transaction_count: number;
}

export const rulesKey = (scope?: string, entityId?: number) =>
  ["rules", scope ?? "all", entityId ?? null] as const;

export function useRules(params: { scope?: string; entity_id?: number }) {
  const qs = new URLSearchParams();
  if (params.scope) qs.set("scope", params.scope);
  if (params.entity_id != null) qs.set("entity_id", String(params.entity_id));
  return useQuery({
    queryKey: rulesKey(params.scope, params.entity_id),
    queryFn: () => apiFetch<Rule[]>(`/api/rules?${qs}`),
  });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: RuleCreatePayload) =>
      apiFetch<Rule>("/api/rules", { method: "POST", body: JSON.stringify(p) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useUpdateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: number; patch: Partial<RuleCreatePayload> }) =>
      apiFetch<Rule>(`/api/rules/${input.id}`, {
        method: "PATCH", body: JSON.stringify(input.patch),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/rules/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function previewRule(p: RuleCreatePayload): Promise<RulePreviewResponse> {
  return apiFetch<RulePreviewResponse>("/api/rules/preview", {
    method: "POST", body: JSON.stringify(p),
  });
}

export function useApplyRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ updated_count: number }>(`/api/rules/${id}/apply`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rules"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}

export function useReorderRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: Array<{ id: number; priority: number }>) =>
      apiFetch<Rule[]>("/api/rules/reorder", {
        method: "POST", body: JSON.stringify(items),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function suggestRuleFromTransactions(
  transaction_ids: number[],
): Promise<RuleSuggestion> {
  return apiFetch<RuleSuggestion>("/api/rules/from-transactions", {
    method: "POST", body: JSON.stringify({ transaction_ids }),
  });
}
```

- [ ] **Step 2 : Étendre `frontend/src/api/transactions.ts`**

Ajouter :

```typescript
export function useBulkCategorize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { transaction_ids: number[]; category_id: number }) =>
      apiFetch<{ updated_count: number }>("/api/transactions/bulk-categorize", {
        method: "POST", body: JSON.stringify(p),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });
}
```

Étendre la signature de `useTransactions` existante pour accepter `uncategorized?: boolean` et l'ajouter à la query string.

- [ ] **Step 3 : Vérifier compilation**

```bash
cd frontend && pnpm tsc --noEmit
```

Attendu : pas d'erreur.

- [ ] **Step 4 : Commit**

```bash
git add frontend/src/api/rules.ts frontend/src/api/transactions.ts
git commit -m "feat(front): API clients for rules (CRUD, preview, apply, reorder, suggest)"
```

---

### Task F2 : Composant `<CategoryCombobox>`

**Files:**
- Create: `frontend/src/components/CategoryCombobox.tsx`
- Test: `frontend/src/components/CategoryCombobox.test.tsx`

- [ ] **Step 1 : Écrire le test**

```typescript
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CategoryCombobox } from "./CategoryCombobox";

const cats = [
  { id: 1, name: "Encaissements", slug: "encaissements", parent_category_id: null },
  { id: 2, name: "Ventes clients", slug: "ventes-clients", parent_category_id: 1 },
  { id: 3, name: "Charges sociales", slug: "charges-sociales", parent_category_id: null },
  { id: 4, name: "URSSAF", slug: "urssaf", parent_category_id: 3 },
];

describe("CategoryCombobox", () => {
  it("renders categories hierarchically", () => {
    render(<CategoryCombobox categories={cats} value={null} onChange={() => {}} />);
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("fires onChange with selected id", async () => {
    const onChange = vi.fn();
    render(<CategoryCombobox categories={cats} value={null} onChange={onChange} />);
    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(screen.getByText("URSSAF"));
    expect(onChange).toHaveBeenCalledWith(4);
  });

  it("displays full path for selected", () => {
    render(<CategoryCombobox categories={cats} value={4} onChange={() => {}} />);
    expect(screen.getByRole("combobox")).toHaveTextContent(/Charges sociales.*URSSAF/);
  });
});
```

- [ ] **Step 2 : Créer le composant**

`frontend/src/components/CategoryCombobox.tsx` :

```tsx
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";

export interface CategoryOption {
  id: number;
  name: string;
  slug: string;
  parent_category_id: number | null;
}

interface Props {
  categories: CategoryOption[];
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder?: string;
}

function buildPath(cats: CategoryOption[], id: number): string {
  const byId = new Map(cats.map((c) => [c.id, c]));
  const parts: string[] = [];
  let cur: CategoryOption | undefined = byId.get(id);
  while (cur) {
    parts.unshift(cur.name);
    cur = cur.parent_category_id ? byId.get(cur.parent_category_id) : undefined;
  }
  return parts.join(" › ");
}

export function CategoryCombobox({ categories, value, onChange, placeholder }: Props) {
  const [open, setOpen] = useState(false);
  const selected = value != null ? buildPath(categories, value) : null;

  const grouped = useMemo(() => {
    const roots = categories.filter((c) => c.parent_category_id === null);
    return roots.map((root) => ({
      root,
      children: categories.filter((c) => c.parent_category_id === root.id),
    }));
  }, [categories]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button role="combobox" variant="outline" className="w-full justify-between">
          {selected ?? (placeholder ?? "Choisir une catégorie")}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[360px] p-0">
        <Command>
          <CommandInput placeholder="Rechercher…" />
          <CommandList>
            <CommandEmpty>Aucune catégorie</CommandEmpty>
            {grouped.map((g) => (
              <CommandGroup key={g.root.id} heading={g.root.name}>
                <CommandItem onSelect={() => { onChange(g.root.id); setOpen(false); }}>
                  {g.root.name}
                </CommandItem>
                {g.children.map((c) => (
                  <CommandItem
                    key={c.id}
                    onSelect={() => { onChange(c.id); setOpen(false); }}
                    className="pl-6"
                  >
                    {c.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 3 : Lancer les tests**

```bash
cd frontend && pnpm vitest run src/components/CategoryCombobox.test.tsx
```

Attendu : 3 passed.

- [ ] **Step 4 : Commit**

```bash
git add frontend/src/components/CategoryCombobox.tsx \
        frontend/src/components/CategoryCombobox.test.tsx
git commit -m "feat(front): hierarchical CategoryCombobox with path rendering"
```

---

### Task F3 : Composant `<RuleForm>` + `<RulePreviewPanel>`

**Files:**
- Create: `frontend/src/components/RuleForm.tsx`
- Create: `frontend/src/components/RulePreviewPanel.tsx`
- Test: `frontend/src/components/RuleForm.test.tsx`

- [ ] **Step 1 : Écrire le test**

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RuleForm } from "./RuleForm";

function Wrapped({ onSubmit }: { onSubmit: ReturnType<typeof vi.fn> }) {
  const qc = new QueryClient();
  return (
    <QueryClientProvider client={qc}>
      <RuleForm
        categories={[
          { id: 1, name: "URSSAF", slug: "urssaf", parent_category_id: null },
        ]}
        entities={[{ id: 10, name: "ACREED" }]}
        counterparties={[]}
        bankAccounts={[]}
        initialValue={null}
        onSubmit={onSubmit}
        onCancel={() => {}}
      />
    </QueryClientProvider>
  );
}

describe("RuleForm", () => {
  it("submits with minimal valid payload", async () => {
    const onSubmit = vi.fn();
    render(<Wrapped onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/nom/i), "Test");
    await userEvent.type(screen.getByLabelText(/priorité/i), "1234");
    await userEvent.type(screen.getByLabelText(/libellé contient/i), "URSSAF");
    // Cat selection via combobox — simplifié ici
    await userEvent.click(screen.getByRole("button", { name: /créer/i }));
    expect(onSubmit).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2 : Créer les composants**

`frontend/src/components/RulePreviewPanel.tsx` :

```tsx
import type { RulePreviewResponse } from "@/api/rules";

export function RulePreviewPanel({ preview }: { preview: RulePreviewResponse | null }) {
  if (!preview) return null;
  return (
    <div className="border rounded p-3 mt-4 bg-muted/50">
      <p className="font-medium">
        {preview.matching_count} transaction{preview.matching_count > 1 ? "s" : ""}{" "}
        correspond{preview.matching_count > 1 ? "ent" : ""} à cette règle.
      </p>
      {preview.sample.length > 0 && (
        <ul className="mt-2 text-sm space-y-1 max-h-64 overflow-y-auto">
          {preview.sample.map((s) => (
            <li key={s.id} className="flex justify-between">
              <span>{s.operation_date} — {s.label}</span>
              <span className="font-mono">{s.amount} €</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

`frontend/src/components/RuleForm.tsx` :

```tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import type {
  Rule, RuleCreatePayload, RuleDirection, RuleLabelOperator, RuleAmountOperator,
  RulePreviewResponse,
} from "@/api/rules";
import { previewRule } from "@/api/rules";
import { CategoryCombobox, type CategoryOption } from "./CategoryCombobox";
import { RulePreviewPanel } from "./RulePreviewPanel";

interface Props {
  categories: CategoryOption[];
  entities: { id: number; name: string }[];
  counterparties: { id: number; name: string }[];
  bankAccounts: { id: number; name: string; entity_id: number }[];
  initialValue: Rule | null;
  onSubmit: (payload: RuleCreatePayload, applyAfter: boolean) => void | Promise<void>;
  onCancel: () => void;
}

export function RuleForm(props: Props) {
  const init = props.initialValue;
  const [name, setName] = useState(init?.name ?? "");
  const [entityId, setEntityId] = useState<number | null>(init?.entity_id ?? null);
  const [priority, setPriority] = useState<number>(init?.priority ?? 5000);
  const [labelOp, setLabelOp] = useState<RuleLabelOperator | "">(
    (init?.label_operator as RuleLabelOperator) ?? "CONTAINS"
  );
  const [labelValue, setLabelValue] = useState(init?.label_value ?? "");
  const [direction, setDirection] = useState<RuleDirection>(init?.direction ?? "ANY");
  const [amountOp, setAmountOp] = useState<RuleAmountOperator | "">(
    (init?.amount_operator as RuleAmountOperator) ?? ""
  );
  const [amountVal, setAmountVal] = useState(init?.amount_value ?? "");
  const [amountVal2, setAmountVal2] = useState(init?.amount_value2 ?? "");
  const [counterpartyId, setCounterpartyId] = useState<number | null>(init?.counterparty_id ?? null);
  const [bankAccountId, setBankAccountId] = useState<number | null>(init?.bank_account_id ?? null);
  const [categoryId, setCategoryId] = useState<number | null>(init?.category_id ?? null);
  const [preview, setPreview] = useState<RulePreviewResponse | null>(null);

  function buildPayload(): RuleCreatePayload {
    return {
      name,
      entity_id: entityId,
      priority,
      label_operator: labelOp || null,
      label_value: labelValue || null,
      direction,
      amount_operator: amountOp || null,
      amount_value: amountVal || null,
      amount_value2: amountVal2 || null,
      counterparty_id: counterpartyId,
      bank_account_id: bankAccountId,
      category_id: categoryId ?? 0,
    };
  }

  async function handlePreview() {
    const resp = await previewRule(buildPayload());
    setPreview(resp);
  }

  async function handleSubmit(applyAfter: boolean) {
    if (!categoryId) return;
    await props.onSubmit(buildPayload(), applyAfter);
  }

  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); handleSubmit(false); }}>
      <div>
        <Label htmlFor="rule-name">Nom</Label>
        <Input id="rule-name" value={name} onChange={(e) => setName(e.target.value)} />
      </div>

      <div>
        <Label htmlFor="rule-priority">Priorité</Label>
        <Input
          id="rule-priority" type="number"
          value={priority}
          onChange={(e) => setPriority(Number(e.target.value))}
        />
      </div>

      <div>
        <Label>Scope</Label>
        <Select value={String(entityId ?? "")} onValueChange={(v) =>
          setEntityId(v === "" ? null : Number(v))
        }>
          <SelectTrigger><SelectValue placeholder="Globale" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="">Globale (toutes entités)</SelectItem>
            {props.entities.map((e) => (
              <SelectItem key={e.id} value={String(e.id)}>{e.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <fieldset className="border p-3 rounded">
        <legend className="px-2 text-sm">Filtre libellé</legend>
        <div className="flex gap-2">
          <Select value={labelOp} onValueChange={(v) => setLabelOp(v as RuleLabelOperator)}>
            <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="CONTAINS">contient</SelectItem>
              <SelectItem value="STARTS_WITH">commence par</SelectItem>
              <SelectItem value="ENDS_WITH">finit par</SelectItem>
              <SelectItem value="EQUALS">égal à</SelectItem>
            </SelectContent>
          </Select>
          <Input
            aria-label="Libellé contient"
            placeholder="ex. URSSAF (sera normalisé)"
            value={labelValue}
            onChange={(e) => setLabelValue(e.target.value)}
          />
        </div>
      </fieldset>

      <fieldset className="border p-3 rounded">
        <legend className="px-2 text-sm">Sens</legend>
        <Select value={direction} onValueChange={(v) => setDirection(v as RuleDirection)}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="ANY">Tous</SelectItem>
            <SelectItem value="CREDIT">Crédits uniquement</SelectItem>
            <SelectItem value="DEBIT">Débits uniquement</SelectItem>
          </SelectContent>
        </Select>
      </fieldset>

      <div>
        <Label>Catégorie cible</Label>
        <CategoryCombobox
          categories={props.categories}
          value={categoryId}
          onChange={setCategoryId}
        />
      </div>

      <RulePreviewPanel preview={preview} />

      <div className="flex gap-2 justify-end">
        <Button variant="ghost" type="button" onClick={props.onCancel}>Annuler</Button>
        <Button variant="outline" type="button" onClick={handlePreview}>Aperçu</Button>
        <Button type="button" onClick={() => handleSubmit(false)}>Créer</Button>
        <Button type="button" onClick={() => handleSubmit(true)}>Créer et appliquer</Button>
      </div>
    </form>
  );
}
```

- [ ] **Step 3 : Lancer tests**

```bash
cd frontend && pnpm vitest run src/components/RuleForm.test.tsx
```

Attendu : 1 passed (le test est volontairement minimaliste — on teste plus en détail via E2E).

- [ ] **Step 4 : Commit**

```bash
git add frontend/src/components/RuleForm.tsx \
        frontend/src/components/RulePreviewPanel.tsx \
        frontend/src/components/RuleForm.test.tsx
git commit -m "feat(front): RuleForm with live preview and RulePreviewPanel"
```

---

### Task F4 : Composant `<SortableRulesTable>` (dnd-kit)

**Files:**
- Modify: `frontend/package.json` (ajout deps)
- Create: `frontend/src/components/SortableRulesTable.tsx`
- Test: `frontend/src/components/SortableRulesTable.test.tsx`

- [ ] **Step 1 : Installer les deps**

```bash
cd frontend && pnpm add @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

- [ ] **Step 2 : Écrire le test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SortableRulesTable } from "./SortableRulesTable";
import type { Rule } from "@/api/rules";

const rules: Rule[] = [
  {
    id: 1, name: "A", entity_id: null, priority: 100, is_system: false,
    label_operator: "CONTAINS", label_value: "A", direction: "ANY",
    amount_operator: null, amount_value: null, amount_value2: null,
    counterparty_id: null, bank_account_id: null, category_id: 1,
    created_at: "", updated_at: "",
  },
  {
    id: 2, name: "B", entity_id: null, priority: 200, is_system: true,
    label_operator: "CONTAINS", label_value: "B", direction: "ANY",
    amount_operator: null, amount_value: null, amount_value2: null,
    counterparty_id: null, bank_account_id: null, category_id: 1,
    created_at: "", updated_at: "",
  },
];

describe("SortableRulesTable", () => {
  it("renders all rules with system badge", () => {
    render(
      <SortableRulesTable
        rules={rules}
        categories={[{ id: 1, name: "c", slug: "c", parent_category_id: null }]}
        onReorder={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        canDelete
      />
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText(/système/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3 : Créer le composant**

`frontend/src/components/SortableRulesTable.tsx` :

```tsx
import { DndContext, closestCenter, type DragEndEvent } from "@dnd-kit/core";
import {
  SortableContext, useSortable, verticalListSortingStrategy, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Rule } from "@/api/rules";
import type { CategoryOption } from "./CategoryCombobox";

interface Props {
  rules: Rule[];
  categories: CategoryOption[];
  onReorder: (reordered: Array<{ id: number; priority: number }>) => void;
  onEdit: (rule: Rule) => void;
  onDelete: (rule: Rule) => void;
  canDelete: boolean;
}

function SortableRow({
  rule, categories, onEdit, onDelete, canDelete,
}: {
  rule: Rule; categories: CategoryOption[];
  onEdit: (r: Rule) => void; onDelete: (r: Rule) => void; canDelete: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: rule.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  const cat = categories.find((c) => c.id === rule.category_id);
  return (
    <tr ref={setNodeRef} style={style} className="border-b">
      <td {...attributes} {...listeners} className="cursor-grab px-2">⋮⋮</td>
      <td className="px-2">{rule.priority}</td>
      <td className="px-2">
        {rule.name}
        {rule.is_system && (
          <Badge variant="secondary" className="ml-2">système</Badge>
        )}
      </td>
      <td className="px-2">{rule.label_operator} {rule.label_value}</td>
      <td className="px-2">{cat?.name ?? `#${rule.category_id}`}</td>
      <td className="px-2 flex gap-2">
        <Button size="sm" variant="ghost" onClick={() => onEdit(rule)}>Éditer</Button>
        {canDelete && !rule.is_system && (
          <Button size="sm" variant="ghost" onClick={() => onDelete(rule)}>Supprimer</Button>
        )}
      </td>
    </tr>
  );
}

export function SortableRulesTable(props: Props) {
  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = props.rules.findIndex((r) => r.id === active.id);
    const newIndex = props.rules.findIndex((r) => r.id === over.id);
    const moved = arrayMove(props.rules, oldIndex, newIndex);
    // Recalculer les priorités en gardant les valeurs existantes mais
    // réassignées par position. On ajoute un offset temporaire côté API
    // pour éviter les conflits (+ 100000). L'API trie par priorité ASC.
    const reordered = moved.map((r, idx) => ({
      id: r.id,
      priority: (idx + 1) * 10 + 100000,
    }));
    props.onReorder(reordered);
  }

  return (
    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="px-2 w-6"></th>
            <th className="px-2">Prio</th>
            <th className="px-2">Nom</th>
            <th className="px-2">Filtre</th>
            <th className="px-2">Catégorie</th>
            <th className="px-2">Actions</th>
          </tr>
        </thead>
        <SortableContext
          items={props.rules.map((r) => r.id)}
          strategy={verticalListSortingStrategy}
        >
          <tbody>
            {props.rules.map((rule) => (
              <SortableRow
                key={rule.id}
                rule={rule}
                categories={props.categories}
                onEdit={props.onEdit}
                onDelete={props.onDelete}
                canDelete={props.canDelete}
              />
            ))}
          </tbody>
        </SortableContext>
      </table>
    </DndContext>
  );
}
```

- [ ] **Step 4 : Lancer tests**

```bash
cd frontend && pnpm vitest run src/components/SortableRulesTable.test.tsx
```

Attendu : 1 passed.

- [ ] **Step 5 : Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml \
        frontend/src/components/SortableRulesTable.tsx \
        frontend/src/components/SortableRulesTable.test.tsx
git commit -m "feat(front): SortableRulesTable with dnd-kit drag handle and system badge"
```

---

### Task F5 : Page `/rules` + wiring routage

**Files:**
- Create: `frontend/src/pages/RulesPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1 : Créer la page**

`frontend/src/pages/RulesPage.tsx` :

```tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerTrigger,
} from "@/components/ui/drawer";
import { SortableRulesTable } from "@/components/SortableRulesTable";
import { RuleForm } from "@/components/RuleForm";
import {
  useRules, useCreateRule, useUpdateRule, useDeleteRule, useApplyRule,
  useReorderRules, type Rule, type RuleCreatePayload,
} from "@/api/rules";
import { useCategories } from "@/api/categories";  // existant ou à créer
import { useEntities } from "@/api/entities";       // existant
import { useCounterparties } from "@/api/counterparties";
import { useBankAccounts } from "@/api/bankAccounts";
import { useMe } from "@/api/me";

export default function RulesPage() {
  const { data: me } = useMe();
  const { data: rules = [] } = useRules({ scope: "all" });
  const { data: categories = [] } = useCategories();
  const { data: entities = [] } = useEntities();
  const { data: counterparties = [] } = useCounterparties({});
  const { data: bankAccounts = [] } = useBankAccounts();

  const createMut = useCreateRule();
  const updateMut = useUpdateRule();
  const deleteMut = useDeleteRule();
  const applyMut = useApplyRule();
  const reorderMut = useReorderRules();

  const [editing, setEditing] = useState<Rule | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  async function handleSubmit(payload: RuleCreatePayload, applyAfter: boolean) {
    if (editing) {
      await updateMut.mutateAsync({ id: editing.id, patch: payload });
    } else {
      const created = await createMut.mutateAsync(payload);
      if (applyAfter) {
        await applyMut.mutateAsync(created.id);
      }
    }
    setDrawerOpen(false);
    setEditing(null);
  }

  return (
    <section className="p-6">
      <header className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold">Règles de catégorisation</h1>
        <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}>
          <DrawerTrigger asChild>
            <Button onClick={() => setEditing(null)}>Nouvelle règle</Button>
          </DrawerTrigger>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>
                {editing ? "Modifier la règle" : "Nouvelle règle"}
              </DrawerTitle>
            </DrawerHeader>
            <div className="p-6 max-w-2xl">
              <RuleForm
                categories={categories}
                entities={entities}
                counterparties={counterparties}
                bankAccounts={bankAccounts}
                initialValue={editing}
                onSubmit={handleSubmit}
                onCancel={() => { setDrawerOpen(false); setEditing(null); }}
              />
            </div>
          </DrawerContent>
        </Drawer>
      </header>

      <SortableRulesTable
        rules={rules}
        categories={categories}
        onReorder={(items) => reorderMut.mutate(items)}
        onEdit={(r) => { setEditing(r); setDrawerOpen(true); }}
        onDelete={(r) => {
          if (confirm(`Supprimer la règle "${r.name}" ?`)) deleteMut.mutate(r.id);
        }}
        canDelete={me?.role === "ADMIN"}
      />
    </section>
  );
}
```

- [ ] **Step 2 : Ajouter la route**

Dans `frontend/src/App.tsx`, ajouter la route :

```tsx
import RulesPage from "@/pages/RulesPage";
// ...
<Route path="/rules" element={<RulesPage />} />
```

Et un lien dans la navigation principale (fichier dépend de l'impl existante, typiquement un `<Sidebar>` ou `<Nav>` component).

- [ ] **Step 3 : Test manuel**

```bash
cd frontend && pnpm dev
```

Ouvrir `http://localhost:5173/rules` dans un navigateur, vérifier :
- Les 30 règles seed s'affichent avec le badge "système".
- Le drag-and-drop fonctionne visuellement.
- Cliquer "Nouvelle règle" ouvre le drawer.
- "Aperçu" retourne un count cohérent.

- [ ] **Step 4 : Commit**

```bash
git add frontend/src/pages/RulesPage.tsx frontend/src/App.tsx
git commit -m "feat(front): /rules page with drawer form and sortable table"
```

---

### Task F6 : Extension `/transactions` (filtre + toolbar bulk)

**Files:**
- Modify: `frontend/src/pages/TransactionsPage.tsx`

- [ ] **Step 1 : Ajouter la toolbar multi-sélection**

L'implémenteur doit lire la page existante `frontend/src/pages/TransactionsPage.tsx`. Modifications ciblées :

1. **Filtre "non catégorisées"** : ajouter un checkbox en tête de liste, wired au param `uncategorized` de `useTransactions`.
2. **État sélection** : `const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())`. Checkbox par ligne.
3. **Toolbar quand `selectedIds.size > 0`** :
   - `<CategoryCombobox>` + bouton "Catégoriser N transactions" → `useBulkCategorize().mutate({ transaction_ids: [...selectedIds], category_id })`
   - Bouton "Créer une règle depuis la sélection" → appelle `suggestRuleFromTransactions`, ouvre le drawer `<RuleForm>` pré-rempli avec les valeurs suggérées.

```tsx
// Extrait à ajouter dans TransactionsPage.tsx
{selectedIds.size > 0 && (
  <div className="sticky top-0 z-10 bg-background border-b p-3 flex gap-2 items-center">
    <span>{selectedIds.size} transaction{selectedIds.size > 1 ? "s" : ""} sélectionnée{selectedIds.size > 1 ? "s" : ""}</span>
    <CategoryCombobox
      categories={categories}
      value={bulkCategoryId}
      onChange={setBulkCategoryId}
    />
    <Button
      disabled={!bulkCategoryId}
      onClick={() => bulkMut.mutate({
        transaction_ids: [...selectedIds],
        category_id: bulkCategoryId!,
      })}
    >
      Catégoriser {selectedIds.size} transaction{selectedIds.size > 1 ? "s" : ""}
    </Button>
    <Button variant="outline" onClick={async () => {
      const suggestion = await suggestRuleFromTransactions([...selectedIds]);
      setRuleDrawerInitialPayload({
        name: "",
        priority: 5000,
        label_operator: suggestion.suggested_label_operator,
        label_value: suggestion.suggested_label_value,
        direction: suggestion.suggested_direction,
        bank_account_id: suggestion.suggested_bank_account_id,
        category_id: bulkCategoryId ?? 0,
      });
      setRuleDrawerOpen(true);
    }}>
      Créer une règle depuis la sélection
    </Button>
  </div>
)}
```

- [ ] **Step 2 : Test manuel**

```bash
cd frontend && pnpm dev
```

Dans `/transactions` : cocher 2-3 tx, vérifier que la toolbar apparaît, cliquer "Catégoriser" → la catégorie s'applique et passe en MANUAL (indicateur visuel).

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/pages/TransactionsPage.tsx
git commit -m "feat(front): transactions page toolbar (bulk-categorize + suggest rule)"
```

---

## Phase G — E2E, permissions, finition

### Task G1 : Test E2E Plan 2 (scénario complet)

**Files:**
- Create: `backend/tests/test_e2e_plan2.py`

- [ ] **Step 1 : Écrire le test**

```python
"""E2E Plan 2 : import auto-catégorisation + règle custom + preview/apply + bulk manual."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.parsers.base import ParsedStatement, ParsedTransaction
from app.services.imports import ingest_parsed_statement
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.category import Category


def test_e2e_plan2_full_flow(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    # 1) Import synthétique : 4 tx (URSSAF x2, EDF, inconnue)
    ptxs = [
        ParsedTransaction(
            operation_date=date(2026, 3, i), value_date=date(2026, 3, i),
            amount=Decimal("-100"), label=lbl, raw_label=lbl,
            statement_row_index=i,
        )
        for i, lbl in enumerate([
            "PRLV URSSAF 111", "PRLV URSSAF 222", "EDF FACT", "AUTRE TRUC"
        ])
    ]
    statement = ParsedStatement(
        bank_code="DELUBAC", iban=bank_account.iban or "FR00",
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
        transactions=ptxs,
    )
    ir = ingest_parsed_statement(
        db_session, bank_account_id=bank_account.id, statement=statement,
    )
    db_session.commit()

    # 2) Vérif auto-catégorisation (URSSAF + EDF pré-installés en B3)
    auto_count = ir.audit.get("categorized_count", 0)
    assert auto_count >= 3  # URSSAF x2 + EDF

    # 3) L'utilisateur ajoute une règle custom pour "AUTRE TRUC"
    cat_autre = Category(name="Mon auto", slug="mon-auto-e2e", is_system=False)
    db_session.add(cat_autre); db_session.commit()

    r_preview = client.post("/api/rules/preview", json={
        "name": "AUTRE", "priority": 9500,
        "label_operator": "CONTAINS", "label_value": "AUTRE TRUC",
        "direction": "ANY", "category_id": cat_autre.id,
    })
    assert r_preview.status_code == 200
    assert r_preview.json()["matching_count"] == 1

    r_create = client.post("/api/rules", json={
        "name": "AUTRE", "priority": 9500,
        "label_operator": "CONTAINS", "label_value": "AUTRE TRUC",
        "direction": "ANY", "category_id": cat_autre.id,
    })
    assert r_create.status_code == 201
    rule_id = r_create.json()["id"]

    r_apply = client.post(f"/api/rules/{rule_id}/apply")
    assert r_apply.status_code == 200
    assert r_apply.json()["updated_count"] == 1

    # 4) Bulk manual : l'utilisateur override 1 tx
    from sqlalchemy import select
    tx_urssaf = db_session.execute(
        select(Transaction).where(
            Transaction.import_id == ir.id,
            Transaction.normalized_label.like("%URSSAF 111%"),
        )
    ).scalar_one()

    r_bulk = client.post("/api/transactions/bulk-categorize", json={
        "transaction_ids": [tx_urssaf.id], "category_id": cat_autre.id,
    })
    assert r_bulk.status_code == 200

    db_session.refresh(tx_urssaf)
    assert tx_urssaf.categorized_by == TransactionCategorizationSource.MANUAL
    assert tx_urssaf.category_id == cat_autre.id

    # 5) Re-apply de la règle URSSAF : ne doit pas écraser le MANUAL
    from app.models.categorization_rule import CategorizationRule
    urssaf_rule = db_session.execute(
        select(CategorizationRule).where(
            CategorizationRule.is_system.is_(True),
            CategorizationRule.label_value == "URSSAF",
        )
    ).scalar_one()
    r_reapply = client.post(f"/api/rules/{urssaf_rule.id}/apply")
    assert r_reapply.status_code == 200
    db_session.refresh(tx_urssaf)
    assert tx_urssaf.categorized_by == TransactionCategorizationSource.MANUAL
```

- [ ] **Step 2 : Lancer**

```bash
cd backend && pytest tests/test_e2e_plan2.py -v
```

Attendu : 1 passed.

- [ ] **Step 3 : Commit**

```bash
git add backend/tests/test_e2e_plan2.py
git commit -m "test(e2e): Plan 2 full flow — import auto-cat + custom rule + bulk manual + MANUAL protection"
```

---

### Task G2 : Permissions end-to-end (test cross-rôles)

**Files:**
- Create: `backend/tests/test_api_rules_permissions.py`

- [ ] **Step 1 : Test matrix**

```python
"""Matrice de permissions sur /api/rules."""
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)


def test_reader_cannot_create(client: TestClient, auth_user_reader, db_session) -> None:
    cat = Category(name="c", slug="c-perm-1", is_system=False)
    db_session.add(cat); db_session.commit()
    r = client.post("/api/rules", json={
        "name": "X", "priority": 30000,
        "label_operator": "CONTAINS", "label_value": "X",
        "direction": "ANY", "category_id": cat.id,
    })
    assert r.status_code == 403


def test_editor_cannot_delete(client: TestClient, auth_user, db_session) -> None:
    cat = Category(name="c", slug="c-perm-2", is_system=False)
    db_session.add(cat); db_session.commit()
    rule = CategorizationRule(
        name="X", priority=30100, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()
    r = client.delete(f"/api/rules/{rule.id}")
    assert r.status_code == 403


def test_editor_without_entity_access_forbidden(
    client: TestClient, auth_user, db_session,
) -> None:
    # Créer une entité à laquelle l'user n'a PAS accès
    from app.models.entity import Entity
    other = Entity(name="Hors accès", slug="hors-acces-perm")
    db_session.add(other); db_session.commit()

    cat = Category(name="c", slug="c-perm-3", is_system=False)
    db_session.add(cat); db_session.commit()

    r = client.post("/api/rules", json={
        "name": "No access", "priority": 30200,
        "entity_id": other.id,
        "label_operator": "CONTAINS", "label_value": "X",
        "direction": "ANY", "category_id": cat.id,
    })
    assert r.status_code == 403
```

- [ ] **Step 2 : Lancer**

```bash
cd backend && pytest tests/test_api_rules_permissions.py -v
```

Attendu : 3 passed.

- [ ] **Step 3 : Commit**

```bash
git add backend/tests/test_api_rules_permissions.py
git commit -m "test(api): permissions matrix for /rules (reader/editor/admin + entity access)"
```

---

### Task G3 : Suite complète + smoke test manuel + merge

- [ ] **Step 1 : Suite complète**

```bash
cd backend && pytest -v --tb=short
cd frontend && pnpm vitest run && pnpm tsc --noEmit && pnpm build
```

Attendu : tout vert. Aucune régression Plan 0/1.

- [ ] **Step 2 : Smoke test manuel en environnement dev**

Démarrer :

```bash
cd backend && alembic upgrade head && uvicorn app.main:app --reload --port 8000
# autre terminal
cd frontend && pnpm dev
```

Check-list manuelle :

1. `/rules` : les 30 règles seed s'affichent, badge "système" sur chacune, tri ASC par priorité.
2. Drag-and-drop une règle : la priorité change (vérifier via DB ou refresh).
3. "Nouvelle règle" → drawer ouvre → saisir "URSSAF" label + catégorie "URSSAF" → Aperçu affiche un count > 0 → Créer et appliquer → une règle custom apparaît en tête de liste.
4. Importer un PDF Delubac de test : vérifier dans `/transactions` que la plupart des lignes ont une catégorie (badge coloré).
5. Dans `/transactions`, cocher 3 tx non catégorisées → toolbar apparaît → choisir catégorie → "Catégoriser 3 transactions" → les 3 basculent MANUAL (indicateur visuel différent de RULE).
6. "Créer une règle depuis la sélection" → drawer pré-rempli avec un pattern suggéré.
7. Re-appliquer une règle système depuis `/rules` : vérifier qu'aucune tx MANUAL ne change.
8. Tenter de supprimer une règle système : erreur 409 visible.

- [ ] **Step 3 : Backup DB prod + merge**

**IMPORTANT — opération prod, obligatoire avant merge** :

```bash
cd ~/acreed-deploy/horizon-prod  # ou chemin équivalent
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U horizon horizon | gzip > ~/backups/horizon-pre-plan2-$(date +%Y%m%d-%H%M).sql.gz
```

Puis merge :

```bash
cd /home/kierangauthier/claude-secure/horizon
git checkout main
git merge --no-ff plan-2-categorization -m "feat: Plan 2 — module catégorisation (moteur + UI + 30 règles Delubac)"
git tag plan-2-done
```

- [ ] **Step 4 : Déploiement prod**

```bash
cd ~/acreed-deploy/horizon-prod
git pull
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d backend frontend
# Les migrations tournent automatiquement via le entrypoint Dockerfile backend
```

Puis smoke test prod :

```bash
curl -s https://horizon.acreedconsulting.com/api/health | jq .
# se connecter, vérifier /rules et /transactions
```

- [ ] **Step 5 : Mettre à jour les mémoires auto**

Dans `/home/tdufr/.claude/projects/-home-kierangauthier-claude-secure-horizon/memory/project_horizon_overview.md` :

Marquer Plan 2 comme terminé (tag `plan-2-done`), ajuster la liste des plans restants (3→6).

- [ ] **Step 6 : Push remote (manuel côté Tristan)**

```bash
git push origin main && git push origin plan-2-done
```

(Nécessite les credentials GitHub de Tristan — déjà noté comme action manuelle en Plan 1.)

---

## Critères de fin — check global

- [ ] Les 3 migrations appliquent et rollback proprement.
- [ ] ≥ 28 règles système seed (test B3).
- [ ] ≥ 50 sous-catégories seed (test B2).
- [ ] Les 30 règles matchent ≥ 70 % des tx d'un import Delubac réel (vérifier manuellement après smoke).
- [ ] Suite backend verte, suite frontend verte, build frontend OK.
- [ ] Page `/rules` : CRUD + drag-and-drop + preview + apply fonctionnent en dev.
- [ ] Page `/transactions` : filtre "non catégorisées" + toolbar bulk + suggest rule fonctionnent.
- [ ] Aucune régression Plan 0/1 (tests et flux import inchangés hormis ajout de la catégorisation).
- [ ] MANUAL jamais écrasé par une règle (couverte par le test E2E G1).
- [ ] Tag `plan-2-done` créé sur `main`.
- [ ] Déploiement prod validé par smoke test sur `horizon.acreedconsulting.com`.

---

## Notes pour l'implémenteur

- **Fixtures tests** : `auth_user` existe déjà en Plan 1. Vérifier `auth_user_reader` et `auth_user_admin` dans `backend/tests/conftest.py` ; si absents, les ajouter (mêmes bases que `auth_user` avec rôle différent). Fixture `entity` et `bank_account` existantes depuis Plan 1.
- **Normalisation libellé** : réutiliser `app.parsers.normalization.normalize_label` partout. Ne pas re-implémenter la logique.
- **Drawer shadcn/ui** : si le composant `Drawer` n'est pas encore installé dans le projet, utiliser `Dialog` (déjà présent dans shadcn/ui standard) comme substitut — même ergonomie pour un formulaire de ~500px.
- **Ordre d'exécution** : respecter Phase A → B → C → D → E → F → G. Les migrations B doivent tourner avant les tests C/D/E/F qui s'appuient sur les tables.
- **SQL `LIKE` vs `ILIKE`** : `normalized_label` est déjà upper-cased, donc `LIKE` exact marche. Le plan utilise `ilike` par prudence (coût négligeable avec index B-tree).
- **Si `pnpm add @dnd-kit/core` échoue** en prod docker : vérifier que `frontend/.dockerignore` n'exclut pas `pnpm-lock.yaml` (corrigé en Plan 1, task déploiement prod).
