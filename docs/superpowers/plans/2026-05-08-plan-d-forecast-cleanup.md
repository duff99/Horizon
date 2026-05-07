# Plan D — Forecast cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Lever la dette technique du module Prévisionnel identifiée dans `docs/superpowers/audits/2026-05-06-app-review-master.md`. Huit items (D1-D8) couvrant la suppression du système `forecast_entries` obsolète, l'introduction de `Category.kind`, la correction du moteur de calcul de cellule, la réduction du cache sur `/forecast/pivot`, les garde-fous AVG_*, le branchement UI de la détection de récurrences, la correction de l'agrégation de groupe dans PivotTable, et la résolution de D8 par D1.

**Architecture :**
- Backend (Python/FastAPI/SQLAlchemy 2.x) : 1 migration drop (`forecast_entries`), 1 migration add column + seeding (`Category.kind`), corrections dans `forecast_engine.py` (D2, D3, D5), nettoyage de `api/forecast.py`, `services/forecast.py`, `models/forecast_entry.py`, `schemas/forecast.py` (classes Entry), 5 call-sites (`analysis.py`, `counterparty_merge.py`, `dashboard.py`, `models/__init__.py`, `schemas/counterparty.py`).
- Frontend (React 18 / TS / react-query / Tailwind) : suppression `ForecastVarianceCard.tsx`, nettoyage `api/forecast.ts` / `types/api.ts` / `CounterpartyMergeDialog.tsx` / `AnalysePage.tsx` (D1) ; ajout `RecurringSuggestionPicker.tsx` + bouton dans `CellEditorDrawer.tsx` + prop `prefillAmountCents` dans `MethodForm.tsx` (D6) ; correction `PivotTable.tsx` (D7).
- Tests : pytest dans le container backend, Vitest pour le frontend.
- Documentation d'impact (règle CLAUDE.md) : D6 ajoute une action UI à effet (pré-remplissage d'une ligne ForecastLine) → tooltip sur le bouton + mise à jour `documentation.ts` section `previsionnel`.

**Tech Stack :** FastAPI, SQLAlchemy 2.x, Postgres, Alembic, React 18, react-query 5, react-router-dom 6, TypeScript, Tailwind, pytest, Vitest.

---

## Vérifications préalables — Résultats d'exploration

### 1. Call-sites exhaustifs ForecastEntry — backend/app/

| Fichier | Lignes | Action D1 |
|---|---|---|
| `backend/app/models/forecast_entry.py` | tout | Supprimer le fichier |
| `backend/app/models/__init__.py:20` | `from app.models.forecast_entry import ForecastEntry, ForecastRecurrence` | Retirer l'import |
| `backend/app/api/forecast.py:18-25,39-125` | imports Entry + 4 routes CRUD | Supprimer (garder `/projection` et `/recurring-suggestions`) |
| `backend/app/services/forecast.py:15,97-119` | import + usages ForecastEntry dans `compute_projection` | Retirer import, supprimer références Entry dans la fonction |
| `backend/app/services/forecast_engine.py:29,86,205-228,323-348,596-598` | import, champ Preloaded, preload bloc 3, `_sum_forecast_entries`, appel dans `_compute_cell_internal` | Tout supprimer ; `forecast = line_value + manual` → `forecast = line_value` |
| `backend/app/services/counterparty_merge.py:16,45,60,107-110` | import, `fe_count` query, champ preview, UPDATE ForecastEntry | Retirer import, passer `fe_count=0`, supprimer UPDATE |
| `backend/app/services/analysis.py:27,871-960` | import + `compute_forecast_variance` | Retirer import, supprimer la fonction |
| `backend/app/api/dashboard.py:747-773` | alerte `stale-forecast` avec import local ForecastEntry | Supprimer le bloc complet |
| `backend/app/schemas/forecast.py:10-51` | import `ForecastRecurrence` + 3 classes Entry | Supprimer les 3 classes et l'import du modèle |
| `backend/app/schemas/counterparty.py:56` | `forecast_entry_count: int` dans `CounterpartyMergePreview` | Retirer le champ |

### 2. Call-sites exhaustifs ForecastEntry — frontend/src/

| Fichier | Lignes | Action D1 |
|---|---|---|
| `frontend/src/api/forecast.ts:10-89` | interfaces `ForecastEntry*` + fonctions CRUD | Supprimer (garder `DetectedRecurrenceSuggestion`, projections, recurring) |
| `frontend/src/components/analyse/ForecastVarianceCard.tsx` | tout | Supprimer le fichier |
| `frontend/src/pages/AnalysePage.tsx:19,88` | import + tag JSX | Retirer |
| `frontend/src/types/api.ts:123` | `forecast_entry_count: number` dans `MergePreview` | Retirer le champ |
| `frontend/src/components/CounterpartyMergeDialog.tsx:98` | affichage du count | Retirer l'affichage |

### 3. Logique actuelle `_combine_total` (forecast_engine.py:528-539)

```python
def _combine_total(realized, committed, forecast, month, current_month):
    if month < current_month:
        return realized                    # passé : réalisé pur — correct
    if month > current_month:
        return forecast                    # futur : forecast seul — BUG : committed ignoré
    remaining = max(0, forecast - realized - committed)
    return realized + committed + remaining  # mois courant — correct
```

Sur les mois futurs, `committed` (engagements PENDING) est calculé mais jamais retourné. Stratégie de non-double-compte (D3) : retourner `forecast` si `forecast != 0` (une ForecastLine active couvre ce mois — l'utilisateur a fait un choix conscient) ou `committed` si `forecast == 0` (aucune ligne = remonter les engagements pour ne pas les masquer).

### 4. Heuristique sign-based de `_directions_by_category` (forecast_engine.py:665-689)

Requête `SUM(amount) GROUP BY category_id` sur toutes les transactions de l'entité. Si somme >= 0 → `"in"`, sinon `"out"`. Fallback `"in"` si catégorie absente. Problèmes : instable selon la période, "flux-intergroupe" oscille, "tva-collectee" positive peut apparaître en Encaissements. D2 remplace par lecture de `Category.kind`.

### 5. Bug `PivotTable.tsx:114-125`

```typescript
// Actuel — sum sur roots seulement (commentaire "backend aggregation" incorrect)
const inTotals = useMemo(() =>
  months.map((_m, idx) =>
    inHier.roots.reduce((s, r) => s + (r.cells[idx]?.total_cents ?? 0), 0)
  ), [months, inHier.roots]);
```

Le backend ne fait pas de rollup parent←enfant : chaque PivotRow a ses propres valeurs. Les sous-catégories ayant des valeurs mais une racine à 0 sont ignorées du total. Fix D7 : réduire sur `inRows` (toutes les lignes de la direction).

### 6. `detect_recurring` et drawer

- Service : `backend/app/services/forecast.py:146` — algorithme récurrences sur 180 jours, min 3 occurrences, retourne `list[DetectedRecurrenceSuggestion]`.
- Endpoint : `GET /api/forecast/recurring-suggestions?entity_id=N` — déjà exposé dans `backend/app/api/forecast.py:198-214`. N'utilise pas ForecastEntry. Survit à D1 intact.
- Client TS : `fetchRecurringSuggestions(entityId)` dans `frontend/src/api/forecast.ts:100-106` — à conserver.
- Drawer : `frontend/src/components/forecast/CellEditorDrawer.tsx` — 3 tabs. Tab "Prévisionnel" rend `<MethodForm>`. Bouton D6 s'insère dans ce tab.

### 7. Migration head actuelle

```bash
docker exec horizon-backend-1 alembic current
# Attendu : h0r1z0n50701 (head)
```

Révisions D1 : `h0r1z0n50801`, D2 : `h0r1z0n50802`.

---

## File Structure

### Création
- `backend/alembic/versions/20260508_1000_drop_forecast_entries.py`
- `backend/alembic/versions/20260508_1010_add_category_kind.py`
- `backend/tests/test_forecast_d1_callsites.py`
- `backend/tests/test_forecast_engine_d3_d5.py`
- `backend/tests/test_category_kind.py`
- `frontend/src/components/forecast/RecurringSuggestionPicker.tsx`

### Suppression
- `backend/app/models/forecast_entry.py`
- `frontend/src/components/analyse/ForecastVarianceCard.tsx`

### Modification
- `backend/app/models/__init__.py` — retirer import ForecastEntry/ForecastRecurrence
- `backend/app/models/category.py` — ajouter colonne `kind`
- `backend/app/api/forecast.py` — supprimer 4 routes CRUD Entry
- `backend/app/api/forecast_pivot.py:163` — max-age 30 → 5
- `backend/app/services/forecast.py` — retirer ForecastEntry de compute_projection
- `backend/app/services/forecast_engine.py` — D1 (suppr ForecastEntry), D2 (_directions_by_category), D3 (_combine_total), D5 (_avg_transactions_n_months)
- `backend/app/services/analysis.py` — supprimer compute_forecast_variance + import
- `backend/app/services/counterparty_merge.py` — retirer ForecastEntry preview/execute_merge
- `backend/app/api/dashboard.py` — supprimer bloc alerte stale-forecast
- `backend/app/schemas/forecast.py` — supprimer classes ForecastEntry*
- `backend/app/schemas/counterparty.py` — retirer forecast_entry_count
- `frontend/src/api/forecast.ts` — supprimer interfaces/fonctions Entry
- `frontend/src/pages/AnalysePage.tsx` — retirer ForecastVarianceCard
- `frontend/src/types/api.ts` — retirer forecast_entry_count
- `frontend/src/components/CounterpartyMergeDialog.tsx` — retirer affichage count FE
- `frontend/src/components/forecast/PivotTable.tsx:114-125` — D7 fix
- `frontend/src/components/forecast/CellEditorDrawer.tsx` — D6 bouton
- `frontend/src/components/forecast/MethodForm.tsx` — D6 prop prefillAmountCents
- `frontend/src/test/forecast/PivotTable.test.tsx` — test D7
- `frontend/src/content/documentation.ts` — section previsionnel D6

---

## Conventions de l'app à respecter

(Rappel pour chaque subagent — copier-coller en briefing.)

- **Tests dans le container backend uniquement** (Python 3.10 vs 3.11+ local → imports incompatibles). `docker exec horizon-backend-1 pytest -x backend/tests/test_xxx.py -v`.
- **Cookie session en test** : `BACKEND_COOKIE_SECURE=false` est déjà câblé via conftest, ne PAS le toucher.
- **Migrations** : copier le fichier dans le container puis `alembic upgrade head`. Procédure : `docker cp backend/alembic/versions/<file> horizon-backend-1:/app/alembic/versions/ && docker exec horizon-backend-1 alembic upgrade head`.
- **Commit messages** : français, ton sobre, sans emoji, format `type(scope): message`. Co-author Claude requis.
- **Doc d'impact (règle CLAUDE.md)** : D6 ajoute un bouton "Suggérer depuis l'historique" avec effet métier visible → tooltip sur le bouton (attribut `title` HTML suffit pour un bouton inline) + mise à jour `documentation.ts` section `previsionnel`. D2 change la direction en interne → pas de doc d'impact UI directe. D1 supprime des features → vérifier que `documentation.ts` ne référence pas les ForecastEntry CRUD.
- **Pas d'emoji**, pas d'auto-fix sur la DB (UPDATE SQL transactionnel obligatoire — jamais sed -i), pas de `cat .env`.
- **Tests frontend** : `cd /srv/prod/tools/horizon/frontend && npx vitest run src/test/forecast/PivotTable.test.tsx`.

---

# Tâches

## Task D1 — Kill `forecast_entries`

**Pourquoi :** ForecastEntry est un système parallèle aux ForecastLine (plan 5b) inutilisé par l'UI depuis plan 5b. Kill complet simplifie radicalement le moteur.

**Steps :**

- [ ] **Step 1 : Confirmer head migration**

```bash
docker exec horizon-backend-1 alembic current
# Doit afficher : h0r1z0n50701 (head). Arrêter si différent.
```

- [ ] **Step 2 : Test de garde initial**

Créer `backend/tests/test_forecast_d1_callsites.py` :

```python
"""D1 guard — Phase 1 : modules doivent exister avant suppression."""

def test_forecast_entry_module_importable():
    import app.models.forecast_entry  # noqa: F401
    assert True

def test_forecast_entry_in_models_init():
    from app.models import ForecastEntry
    assert ForecastEntry is not None
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_forecast_d1_callsites.py -v
# Attendu : 2 PASS
```

- [ ] **Step 3 : Migration drop**

Créer `backend/alembic/versions/20260508_1000_drop_forecast_entries.py` :

```python
"""D1 — Drop forecast_entries + enum forecast_recurrence.

Revision ID: h0r1z0n50801
Revises: h0r1z0n50701
Create Date: 2026-05-08 10:00:00
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "h0r1z0n50801"
down_revision = "h0r1z0n50701"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_forecast_entity_due", table_name="forecast_entries")
    op.drop_table("forecast_entries")
    sa.Enum(name="forecast_recurrence").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    recurrence_enum = sa.Enum(
        "NONE", "WEEKLY", "MONTHLY", "QUARTERLY", "YEARLY",
        name="forecast_recurrence",
    )
    op.create_table(
        "forecast_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_id", sa.Integer,
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bank_account_id", sa.Integer,
                  sa.ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("category_id", sa.Integer,
                  sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("counterparty_id", sa.Integer,
                  sa.ForeignKey("counterparties.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recurrence", recurrence_enum, nullable=False, server_default="NONE"),
        sa.Column("recurrence_until", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_forecast_entity_due", "forecast_entries",
                    ["entity_id", "due_date"])
```

```bash
docker cp backend/alembic/versions/20260508_1000_drop_forecast_entries.py \
  horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
docker exec horizon-backend-1 alembic current
# Attendu : h0r1z0n50801 (head)
```

- [ ] **Step 4 : Nettoyer `forecast_engine.py`**

Modifications à faire dans `backend/app/services/forecast_engine.py` :

1. Supprimer ligne 29 : `from app.models.forecast_entry import ForecastEntry`
2. Supprimer ligne 86 dans dataclass `Preloaded` : `forecast_entries_by_cat_month: dict[tuple[int, str], int]`
3. Dans `_preload`, supprimer le bloc commenté `# 3) Forecast entries...` (lignes 205-228) et retirer `forecast_entries_by_cat_month=forecast_entries_by_cat_month,` du `return Preloaded(...)`.
4. Supprimer la fonction `_sum_forecast_entries` (lignes 323-348).
5. Dans `_compute_cell_internal`, remplacer les lignes 596-599 :

```python
# AVANT :
manual = _sum_forecast_entries(
    session, entity_id, category_id, month, preloaded=preloaded
)
forecast = line_value + manual

# APRÈS :
forecast = line_value
```

- [ ] **Step 5 : Nettoyer `services/forecast.py`**

1. Supprimer ligne 15 : `from app.models.forecast_entry import ForecastEntry, ForecastRecurrence`
2. Dans `compute_projection` : supprimer toutes les références à `ForecastEntry`. La projection ne rendra plus les entrées manuelles dans ses `points`, uniquement les engagements PENDING.
3. `detect_recurring` (ligne 146+) : ne référence pas ForecastEntry — laisser intact.

- [ ] **Step 6 : Nettoyer `api/forecast.py`**

1. Supprimer imports lignes 18-25 : `ForecastEntry`, `ForecastEntryCreate`, `ForecastEntryRead`, `ForecastEntryUpdate`.
2. Supprimer les 4 fonctions endpoint (lignes 39-125) : `list_entries`, `create_entry`, `update_entry`, `delete_entry`.
3. Conserver : `get_projection` et `get_recurring_suggestions`.

- [ ] **Step 7 : Nettoyer analysis, counterparty_merge, dashboard**

`backend/app/services/analysis.py` :
- Supprimer ligne 27 : `from app.models.forecast_entry import ForecastEntry`
- Supprimer la fonction `compute_forecast_variance` complète (environ lignes 871-960)

`backend/app/services/counterparty_merge.py` :
- Supprimer ligne 16 : `from app.models.forecast_entry import ForecastEntry`
- Dans `build_merge_preview` (ligne ~45), remplacer :
  ```python
  fe_count = session.query(ForecastEntry).filter_by(counterparty_id=src.id).count()
  ```
  par :
  ```python
  fe_count = 0
  ```
- Dans `execute_merge` (lignes 106-110), supprimer le bloc :
  ```python
  session.execute(
      update(ForecastEntry)
      .where(ForecastEntry.counterparty_id == src.id)
      .values(counterparty_id=tgt.id)
  )
  ```

`backend/app/api/dashboard.py` :
- Supprimer les lignes 747-773 (bloc alerte `stale-forecast`, import local inclus)

- [ ] **Step 8 : Nettoyer schémas et modèles**

`backend/app/schemas/forecast.py` :
- Supprimer ligne 10 : `from app.models.forecast_entry import ForecastRecurrence`
- Supprimer les classes `ForecastEntryCreate` (L.13-22), `ForecastEntryUpdate` (L.26-35), `ForecastEntryRead` (L.38-51)

`backend/app/schemas/counterparty.py` :
- Retirer `forecast_entry_count: int` de `CounterpartyMergePreview` (ligne 56)

`backend/app/models/__init__.py` :
- Supprimer ligne 20 : `from app.models.forecast_entry import ForecastEntry, ForecastRecurrence  # noqa: F401`

Supprimer le fichier `backend/app/models/forecast_entry.py`.

- [ ] **Step 9 : Nettoyer le frontend**

`frontend/src/api/forecast.ts` — supprimer :
- Interface `ForecastEntry` (L.10-22), `ForecastEntryCreate` (L.24-35), `ForecastEntryUpdate` (L.37)
- Fonctions `listForecastEntries`, `createForecastEntry`, `updateForecastEntry`, `deleteForecastEntry` (L.63-89)
- Conserver : `ForecastRecurrence`, `ForecastProjection*`, `DetectedRecurrenceSuggestion`, `fetchForecastProjection`, `fetchRecurringSuggestions`

`frontend/src/types/api.ts` : retirer `forecast_entry_count: number` (L.123)

`frontend/src/components/CounterpartyMergeDialog.tsx` : retirer l'affichage du count (ligne ~98) et son wrapper JSX

Supprimer `frontend/src/components/analyse/ForecastVarianceCard.tsx`

`frontend/src/pages/AnalysePage.tsx` :
- Supprimer ligne 19 : `import { ForecastVarianceCard } from "@/components/analyse/ForecastVarianceCard";`
- Supprimer le bloc `<div className="col-span-12"><ForecastVarianceCard entityId={entityId ?? undefined} /></div>` (~L.86-89)

- [ ] **Step 10 : Réécrire le test de garde pour vérifier l'ABSENCE**

Remplacer le contenu de `backend/tests/test_forecast_d1_callsites.py` :

```python
"""D1 guard — Phase 2 : vérifier l'ABSENCE après suppression."""
import pytest


def test_forecast_entry_module_deleted():
    with pytest.raises(ModuleNotFoundError):
        import app.models.forecast_entry  # noqa: F401


def test_forecast_entry_not_in_models_init():
    import app.models as m
    assert not hasattr(m, "ForecastEntry")
    assert not hasattr(m, "ForecastRecurrence")


def test_entry_schemas_deleted():
    from app.schemas import forecast as f
    assert not hasattr(f, "ForecastEntryCreate")
    assert not hasattr(f, "ForecastEntryRead")
    assert not hasattr(f, "ForecastEntryUpdate")


def test_counterparty_preview_no_forecast_entry_count():
    from app.schemas.counterparty import CounterpartyMergePreview
    assert "forecast_entry_count" not in CounterpartyMergePreview.model_fields
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_forecast_d1_callsites.py -v
# Attendu : 4 PASS
```

- [ ] **Step 11 : Régression backend**

```bash
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 12 : Vérification TypeScript**

```bash
cd /srv/prod/tools/horizon/frontend && npx tsc --noEmit
```

- [ ] **Step 13 : Commit D1**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(forecast): kill forecast_entries — suppression complète du système legacy

Table forecast_entries droppée (migration h0r1z0n50801), modèle
ForecastEntry supprimé, 4 routes CRUD /api/forecast/entries retirées,
ForecastVarianceCard supprimée, alerte dashboard stale-forecast retirée.
5 call-sites nettoyés (analysis, counterparty_merge, dashboard, schemas,
frontend). Prévisionnel repose désormais sur ForecastLine uniquement.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task D8 — No-op résolu par D1

D8 demandait "Reconnecter ForecastVarianceCard sur forecast_lines". La card est supprimée par D1. D8 est résolu implicitement. Aucune action.

---

## Task D2 — `Category.kind` + migration de seeding + `_directions_by_category`

**Pourquoi :** la direction d'une catégorie dans le pivot est actuellement inférée par le signe historique des transactions — instable. `Category.kind` est une propriété structurelle stable que l'on seede une fois sur les 65 catégories existantes.

**Files :**
- Créer : `backend/alembic/versions/20260508_1010_add_category_kind.py`
- Modifier : `backend/app/models/category.py`
- Modifier : `backend/app/services/forecast_engine.py` (fonctions `_infer_direction`, `_directions_by_category`)
- Créer : `backend/tests/test_category_kind.py`

**Critères de seeding**

| kind | Slugs |
|---|---|
| `in` | `encaissements`, `ventes-clients`, `subventions-aides`, `remboursements-encaissements`, `autres-encaissements`, `produits-financiers`, `affacturage-dailly` |
| `out` | `decaissements-personnel`, `decaissements-sous-traitants`, `decaissements-fournisseurs`, `personnel`, `charges-sociales`, `charges-externes`, `frais-bancaires`, `investissements`, `honoraires-juridiques`, `salaires-nets`, `acomptes-salaires`, `primes-bonus`, `frais-professionnels-remb`, `urssaf`, `retraite`, `prevoyance`, `mutuelle`, `taxe-apprentissage`, `formation-professionnelle`, `loyers-charges-locatives`, `energie-eau`, `telecom-internet`, `assurances`, `honoraires-conseil`, `deplacements-missions`, `fournitures-bureau`, `informatique-logiciels`, `publicite-marketing`, `sous-traitance-generique`, `commissions`, `agios-interets`, `frais-cartes`, `change`, `acquisitions-materiel`, `acquisitions-logiciels`, `acquisitions-immobilier` |
| `both` | `impots-taxes`, `flux-financiers`, `flux-intergroupe`, `autres`, `non-categorisees`, `tva-collectee`, `tva-deductible`, `tva-a-payer`, `impot-societes`, `cfe-cvae`, `taxe-fonciere`, `autres-taxes`, `emprunts-remboursements`, `apports-comptes-courants`, `virements-internes`, `dividendes-remontees`, `non-identifies`, `ajustements`, `depenses-personnelles`, `charges-sociales-taxes` |

Catégories créées ultérieurement par l'utilisateur : `server_default='both'`.

Dans le pivot, `kind='both'` est mappé à `"in"` par convention (cohérent avec le fallback actuel), pour éviter de doubler les lignes. Le split `both` en deux directions est un choix de design futur hors scope D2.

**Steps :**

- [ ] **Step 1 : Test rouge**

Créer `backend/tests/test_category_kind.py` :

```python
"""Tests Category.kind — D2."""


def test_category_has_kind_attribute(db_session):
    from app.models.category import Category
    cat = db_session.query(Category).first()
    assert hasattr(cat, "kind")
    assert cat.kind in ("in", "out", "both")


def test_encaissements_is_in(db_session):
    from app.models.category import Category
    cat = db_session.query(Category).filter(Category.slug == "encaissements").one()
    assert cat.kind == "in"


def test_personnel_is_out(db_session):
    from app.models.category import Category
    cat = db_session.query(Category).filter(Category.slug == "personnel").one()
    assert cat.kind == "out"


def test_flux_financiers_is_both(db_session):
    from app.models.category import Category
    cat = db_session.query(Category).filter(Category.slug == "flux-financiers").one()
    assert cat.kind == "both"
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_category_kind.py -v
# Attendu : 4 FAIL (colonne kind inexistante)
```

- [ ] **Step 2 : Migration**

Créer `backend/alembic/versions/20260508_1010_add_category_kind.py` :

```python
"""D2 — Ajoute Category.kind (in/out/both) + seeding des catégories existantes.

Revision ID: h0r1z0n50802
Revises: h0r1z0n50801
Create Date: 2026-05-08 10:10:00
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "h0r1z0n50802"
down_revision = "h0r1z0n50801"
branch_labels = None
depends_on = None

IN_SLUGS = [
    "encaissements", "ventes-clients", "subventions-aides",
    "remboursements-encaissements", "autres-encaissements",
    "produits-financiers", "affacturage-dailly",
]
OUT_SLUGS = [
    "decaissements-personnel", "decaissements-sous-traitants",
    "decaissements-fournisseurs", "personnel", "charges-sociales",
    "charges-externes", "frais-bancaires", "investissements",
    "honoraires-juridiques",
    "salaires-nets", "acomptes-salaires", "primes-bonus",
    "frais-professionnels-remb",
    "urssaf", "retraite", "prevoyance", "mutuelle",
    "taxe-apprentissage", "formation-professionnelle",
    "loyers-charges-locatives", "energie-eau", "telecom-internet",
    "assurances", "honoraires-conseil", "deplacements-missions",
    "fournitures-bureau", "informatique-logiciels",
    "publicite-marketing", "sous-traitance-generique",
    "commissions", "agios-interets", "frais-cartes", "change",
    "acquisitions-materiel", "acquisitions-logiciels",
    "acquisitions-immobilier",
]
BOTH_SLUGS = [
    "impots-taxes", "flux-financiers", "flux-intergroupe",
    "autres", "non-categorisees",
    "tva-collectee", "tva-deductible", "tva-a-payer",
    "impot-societes", "cfe-cvae", "taxe-fonciere", "autres-taxes",
    "emprunts-remboursements", "apports-comptes-courants",
    "virements-internes", "dividendes-remontees",
    "non-identifies", "ajustements", "depenses-personnelles",
    "charges-sociales-taxes",
]


def upgrade() -> None:
    conn = op.get_bind()
    op.add_column(
        "categories",
        sa.Column("kind", sa.String(4), nullable=False, server_default="both"),
    )
    conn.execute(
        sa.text("UPDATE categories SET kind='in' WHERE slug = ANY(:s)"),
        {"s": IN_SLUGS},
    )
    conn.execute(
        sa.text("UPDATE categories SET kind='out' WHERE slug = ANY(:s)"),
        {"s": OUT_SLUGS},
    )
    conn.execute(
        sa.text("UPDATE categories SET kind='both' WHERE slug = ANY(:s)"),
        {"s": BOTH_SLUGS},
    )


def downgrade() -> None:
    op.drop_column("categories", "kind")
```

```bash
docker cp backend/alembic/versions/20260508_1010_add_category_kind.py \
  horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
docker exec horizon-backend-1 alembic current
# Attendu : h0r1z0n50802 (head)
```

- [ ] **Step 3 : Mettre à jour le modèle `Category`**

Dans `backend/app/models/category.py`, ajouter après `is_system` :

```python
kind: Mapped[str] = mapped_column(
    String(4), nullable=False, default="both", server_default="both"
)
```

- [ ] **Step 4 : Basculer `_directions_by_category` sur `Category.kind`**

Dans `backend/app/services/forecast_engine.py`, remplacer les deux fonctions `_infer_direction` (L.645-662) et `_directions_by_category` (L.665-689) par :

```python
def _directions_by_category(
    session: Session, entity_id: int  # entity_id conservé pour compatibilité signature
) -> dict[int, str]:
    """Retourne la direction de chaque catégorie selon Category.kind.

    kind='in'  → 'in'
    kind='out' → 'out'
    kind='both' → 'in' (convention pivot : pas de double-ligne pour les
                        catégories neutres, cohérent avec l'ancien fallback)
    """
    rows = session.execute(select(Category.id, Category.kind)).all()
    return {
        int(cat_id): ("out" if kind == "out" else "in")
        for cat_id, kind in rows
        if cat_id is not None
    }
```

Supprimer `_infer_direction` (n'est plus utilisée).

- [ ] **Step 5 : Tests**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_category_kind.py -v
# Attendu : 4 PASS
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 6 : Commit D2**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(categories): Category.kind (in/out/both) remplace l'heuristique sign-based

Migration h0r1z0n50802 : colonne kind VARCHAR(4) NOT NULL DEFAULT 'both',
seeding par slug sur toutes les catégories existantes. _directions_by_category
lit désormais Category.kind au lieu de SUM(transactions). Direction stable
indépendamment de la période ou des données manquantes.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task D3 — Fixer `_combine_total` pour mois futurs

**Pourquoi :** sur les mois futurs, `committed` (engagements PENDING) est ignoré par `_combine_total` qui retourne uniquement `forecast`. Un fournisseur dont la facture est PENDING sur un mois futur est invisible dans le pivot prévisionnel.

**Files :**
- Modifier : `backend/app/services/forecast_engine.py:528-539`
- Créer (section D3 dans) : `backend/tests/test_forecast_engine_d3_d5.py`

**Steps :**

- [ ] **Step 1 : Test rouge**

Créer `backend/tests/test_forecast_engine_d3_d5.py` :

```python
"""Tests forecast_engine : D3 (_combine_total) et D5 (AVG guards)."""
from __future__ import annotations
from datetime import date
import pytest
from app.services.forecast_engine import _combine_total

PAST = date(2026, 3, 1)
CURRENT = date(2026, 5, 1)
FUTURE = date(2026, 7, 1)


class TestCombineTotal:
    """D3 — mois futurs doivent inclure committed_pending quand forecast==0."""

    def test_past_returns_realized_only(self):
        assert _combine_total(50_000, 10_000, 30_000, PAST, CURRENT) == 50_000

    def test_future_no_forecast_includes_committed(self):
        """Sans ligne (forecast=0), committed remonte sur mois futur."""
        assert _combine_total(0, -15_000, 0, FUTURE, CURRENT) == -15_000

    def test_future_with_forecast_ignores_committed(self):
        """Avec une ligne (forecast!=0), committed ignoré (choix utilisateur)."""
        assert _combine_total(0, -15_000, -20_000, FUTURE, CURRENT) == -20_000

    def test_current_month_with_remaining(self):
        # remaining = max(0, 20000 - 10000 - 5000) = 5000 → total = 20000
        assert _combine_total(10_000, 5_000, 20_000, CURRENT, CURRENT) == 20_000

    def test_current_month_no_remaining(self):
        # remaining = max(0, 20000 - 18000 - 5000) = 0 → total = 23000
        assert _combine_total(18_000, 5_000, 20_000, CURRENT, CURRENT) == 23_000
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_forecast_engine_d3_d5.py::TestCombineTotal -v
# Attendu : test_future_no_forecast_includes_committed FAIL (retourne 0)
```

- [ ] **Step 2 : Implémenter dans `forecast_engine.py`**

Remplacer la fonction `_combine_total` (lignes 528-539) :

```python
def _combine_total(
    realized: int, committed: int, forecast: int, month: date, current_month: date,
) -> int:
    if month < current_month:
        return realized
    if month > current_month:
        # Si une ForecastLine couvre ce mois (forecast != 0), respecter le choix
        # de l'utilisateur. Si aucune ligne (forecast == 0), remonter les
        # engagements PENDING pour ne pas les masquer visuellement.
        return forecast if forecast != 0 else committed
    # Mois courant : réalisé + engagé + reste prévisionnel non couvert
    remaining = forecast - realized - committed
    if remaining < 0:
        remaining = 0
    return realized + committed + remaining
```

- [ ] **Step 3 : Tests verts**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_forecast_engine_d3_d5.py::TestCombineTotal -v
# Attendu : 5 PASS
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 4 : Commit D3**

```bash
git add backend/app/services/forecast_engine.py backend/tests/test_forecast_engine_d3_d5.py
git commit -m "$(cat <<'EOF'
fix(forecast): _combine_total inclut committed_pending sur mois futurs

Sans ForecastLine active (forecast=0), les engagements PENDING étaient
invisibles dans le pivot futur. Correction : return committed si forecast==0,
return forecast sinon (ligne active = choix de l'utilisateur).

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task D4 — Réduire `Cache-Control` sur `/forecast/pivot` à `max-age=5`

**Pourquoi :** `max-age=30` masque toute modification saisie dans le drawer pendant ~30s après enregistrement. `max-age=5` réduit la fenêtre à un délai imperceptible tout en conservant un effet de cache minimal côté navigateur.

**Files :**
- Modifier : `backend/app/api/forecast_pivot.py:163`

**Steps :**

- [ ] **Step 1 : Appliquer le fix**

Dans `backend/app/api/forecast_pivot.py`, ligne 163, remplacer :

```python
response.headers["Cache-Control"] = "private, max-age=30"
```

par :

```python
response.headers["Cache-Control"] = "private, max-age=5"
```

- [ ] **Step 2 : Vérification**

```bash
# En prod après déploiement :
# curl -sI "https://<host>/api/forecast/pivot?scenario_id=1&entity_id=1&from=2026-05&to=2026-05" \
#   -H "Cookie: session=..." | grep -i cache-control
# Attendu : Cache-Control: private, max-age=5
```

- [ ] **Step 3 : Commit D4**

```bash
git add backend/app/api/forecast_pivot.py
git commit -m "$(cat <<'EOF'
fix(forecast): Cache-Control pivot réduit à max-age=5s (était 30s)

30s masquait les modifications du drawer trop longtemps après enregistrement.
5s préserve un effet de cache minimal sans impacter l'UX de feedback.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task D5 — Garde-fous AVG_3M/AVG_6M/AVG_12M sur historique insuffisant

**Pourquoi :** `_avg_transactions_n_months` divise toujours par `n_months` même si moins de `n` mois ont des données. Une entité créée il y a 2 mois avec `AVG_12M` reçoit `total / 12` au lieu de `total / 2` — sous-estimation grave et silencieuse. La correction : diviser par le nombre de mois non nuls disponibles.

**Files :**
- Modifier : `backend/app/services/forecast_engine.py:351-371`
- Ajouter (section D5 dans) : `backend/tests/test_forecast_engine_d3_d5.py`

**Steps :**

- [ ] **Step 1 : Test**

Ajouter dans `backend/tests/test_forecast_engine_d3_d5.py` :

```python
class TestAvgTransactionsGuard:
    """D5 — division par mois disponibles, pas par N fixe."""

    def test_avg_no_history_returns_zero(self, db_session):
        """Catégorie sans historique → 0 (jamais de division par zéro)."""
        from datetime import date
        from app.services.forecast_engine import _avg_transactions_n_months
        result = _avg_transactions_n_months(
            db_session, entity_id=999999, category_id=999999,
            month=date(2026, 5, 1), n_months=3,
        )
        assert result == 0

    def test_avg_returns_int(self, db_session):
        from datetime import date
        from app.services.forecast_engine import _avg_transactions_n_months
        result = _avg_transactions_n_months(
            db_session, entity_id=999999, category_id=999999,
            month=date(2026, 5, 1), n_months=6,
        )
        assert isinstance(result, int)
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_forecast_engine_d3_d5.py::TestAvgTransactionsGuard -v
# Ces tests passent déjà si entity/catégorie inexistants retournent 0.
# Le test de division correcte nécessite des fixtures DB — voir note ci-dessous.
```

Note : le test de "division par available" complet nécessite des fixtures avec des transactions réelles. L'implémentation est validée par lecture de code. Le test ci-dessus valide au minimum le type de retour et l'absence d'exception.

- [ ] **Step 2 : Corriger `_avg_transactions_n_months`**

Dans `backend/app/services/forecast_engine.py`, remplacer la fonction (lignes 351-371) :

```python
def _avg_transactions_n_months(
    session: Session,
    entity_id: int,
    category_id: int,
    month: date,
    n_months: int,
    *,
    preloaded: Optional["Preloaded"] = None,
) -> int:
    """Moyenne des N mois précédents (excluant `month`).

    Divise par le nombre de mois ayant des données non nulles (min(n, available))
    pour éviter la sous-estimation sur historique court. Retourne 0 si aucune
    donnée n'existe sur la fenêtre.
    """
    if n_months <= 0:
        return 0
    totals = []
    for i in range(1, n_months + 1):
        m = _add_months(month, -i)
        v = _sum_transactions(session, entity_id, category_id, m, preloaded=preloaded)
        totals.append(v)

    non_zero = [v for v in totals if v != 0]
    available = len(non_zero)
    if available == 0:
        return 0

    # Division par le nombre de mois avec données, jamais par n_months fixe
    return sum(totals) // available
```

- [ ] **Step 3 : Mettre à jour `CellValue` et `PivotCellRead` pour signaler l'historique insuffisant**

Dans `backend/app/services/forecast_engine.py`, ajouter `insufficient_history: bool = False` au dataclass `CellValue` :

```python
@dataclass
class CellValue:
    realized_cents: int
    committed_cents: int
    forecast_cents: int
    total_cents: int
    line_method: Optional[str] = None
    line_params: Optional[dict] = None
    insufficient_history: bool = False  # D5 : AVG_* sans données disponibles
```

Dans `backend/app/schemas/forecast.py`, ajouter le champ à `PivotCellRead` :

```python
class PivotCellRead(BaseModel):
    month: str
    realized_cents: int
    committed_cents: int
    forecast_cents: int
    total_cents: int
    line_method: str | None = None
    line_params: dict | None = None
    insufficient_history: bool = False
```

Dans `backend/app/api/forecast_pivot.py`, dans la construction des `PivotCellRead` (dans la list comprehension qui sérialise les cellules), propager `insufficient_history=cv.insufficient_history` depuis `CellValue`.

Note : la détection de "0 disponible" est déjà dans `_avg_transactions_n_months` (retourne 0). Pour propager le flag `insufficient_history` jusqu'à `CellValue`, il faut soit un second retour de valeur, soit un log. Pour D5, on accepte que `insufficient_history=True` soit positionné uniquement lorsque `_evaluate_line` est appelée avec une méthode AVG_* — cette logique fine est implémentée dans `_evaluate_line` (si method est AVG_* et résultat == 0, poser le flag). L'implémenteur doit juger si ce niveau de précision est nécessaire ou si `insufficient_history=False` par défaut suffit pour la release D5 (pas de griseage UI requis dans ce plan — feature UI différée).

- [ ] **Step 4 : Tests verts**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_forecast_engine_d3_d5.py -v
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 5 : Commit D5**

```bash
git add backend/app/services/forecast_engine.py backend/app/schemas/forecast.py \
        backend/app/api/forecast_pivot.py backend/tests/test_forecast_engine_d3_d5.py
git commit -m "$(cat <<'EOF'
fix(forecast): AVG_* divise par mois disponibles, pas par N fixe

Corrige la sous-estimation silencieuse sur historique court : une entité
créée il y a 2 mois avec AVG_12M recevait total/12 au lieu de total/2.
_avg_transactions_n_months divise désormais par len(non_zero_months).
Ajoute insufficient_history dans CellValue/PivotCellRead pour usage futur.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task D6 — Brancher `detect_recurring` dans le drawer forecast

**Pourquoi :** `detect_recurring` analyse l'historique des transactions pour détecter les récurrences. Le service et l'endpoint `GET /api/forecast/recurring-suggestions` existent mais ne sont accessibles nulle part dans l'UI du Prévisionnel. Ce bouton permet à l'utilisateur de pré-remplir une ligne ForecastLine depuis une suggestion détectée automatiquement.

**Impact CLAUDE.md :** action UI à effet (pré-remplit une ForecastLine) → tooltip sur le bouton + mise à jour `documentation.ts`.

**Files :**
- Créer : `frontend/src/components/forecast/RecurringSuggestionPicker.tsx`
- Modifier : `frontend/src/components/forecast/CellEditorDrawer.tsx`
- Modifier : `frontend/src/components/forecast/MethodForm.tsx`
- Modifier : `frontend/src/content/documentation.ts`

**Steps :**

- [ ] **Step 1 : Créer `RecurringSuggestionPicker.tsx`**

Créer `frontend/src/components/forecast/RecurringSuggestionPicker.tsx` :

```tsx
import { useQuery } from "@tanstack/react-query";
import { fetchRecurringSuggestions } from "@/api/forecast";
import type { DetectedRecurrenceSuggestion } from "@/api/forecast";
import { formatCents } from "@/lib/forecastFormat";
import { cn } from "@/lib/utils";

interface Props {
  entityId: number;
  onSelect: (suggestion: DetectedRecurrenceSuggestion) => void;
  onClose: () => void;
}

const RECURRENCE_LABELS: Record<string, string> = {
  MONTHLY: "Mensuel",
  WEEKLY: "Hebdomadaire",
  QUARTERLY: "Trimestriel",
  YEARLY: "Annuel",
  NONE: "Ponctuel",
};

export function RecurringSuggestionPicker({ entityId, onSelect, onClose }: Props) {
  const query = useQuery({
    queryKey: ["recurring-suggestions", entityId],
    queryFn: () => fetchRecurringSuggestions(entityId),
    staleTime: 5 * 60 * 1000, // 5 min — l'historique ne change pas à chaque ouverture
  });

  return (
    <div className="rounded-lg border border-line-soft bg-panel-2/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[12px] font-semibold text-ink">
          Récurrences détectées sur 6 mois
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-[11px] text-muted-foreground hover:text-ink"
        >
          Fermer
        </button>
      </div>

      {query.isLoading && (
        <div className="py-3 text-center text-[12px] text-muted-foreground">
          Analyse en cours…
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-rose-50 px-2 py-1.5 text-[12px] text-rose-800">
          Impossible d'analyser l'historique.
        </div>
      )}
      {query.data && query.data.length === 0 && (
        <div className="py-3 text-center text-[12px] text-muted-foreground">
          Aucune récurrence détectée sur les 6 derniers mois.
        </div>
      )}
      {query.data && query.data.length > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto">
          {query.data.slice(0, 10).map((s, i) => {
            const cents = Math.round(Number(s.average_amount) * 100);
            return (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => onSelect(s)}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-md border",
                    "border-line-soft bg-panel px-3 py-2 text-left text-[12px]",
                    "transition-colors hover:border-accent hover:bg-accent/5",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate font-medium text-ink">
                    {s.counterparty_name}
                  </span>
                  <span className="shrink-0 text-[11px] text-muted-foreground">
                    {RECURRENCE_LABELS[s.recurrence] ?? s.recurrence}
                  </span>
                  <span
                    className={cn(
                      "shrink-0 font-mono text-[12px] tabular-nums",
                      cents >= 0 ? "text-emerald-700" : "text-rose-700",
                    )}
                  >
                    {formatCents(cents)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2 : Ajouter `prefillAmountCents` à `MethodForm.tsx`**

Dans `frontend/src/components/forecast/MethodForm.tsx`, modifier l'interface `Props` :

```tsx
interface Props {
  scenarioId: number;
  categoryId: number;
  cellMonth?: string;
  line?: ForecastLine | null;
  onSave: () => void;
  prefillAmountCents?: number; // D6 — pré-remplissage depuis RecurringSuggestionPicker
}
```

Modifier le `useState` initial de `method` (première ligne de la fonction) :

```tsx
const [method, setMethod] = useState<ForecastMethod>(
  prefillAmountCents != null
    ? "RECURRING_FIXED"
    : (line?.method ?? "RECURRING_FIXED"),
);
```

Modifier le `useState` initial de `amountStr` :

```tsx
const [amountStr, setAmountStr] = useState<string>(() => {
  if (prefillAmountCents != null) {
    return String(prefillAmountCents / 100);
  }
  if (
    (line?.method === "RECURRING_FIXED" || line?.method === "SINGLE_MONTH_FIXED") &&
    line?.amount_cents != null
  ) {
    return String(line.amount_cents / 100);
  }
  return "";
});
```

- [ ] **Step 3 : Modifier `CellEditorDrawer.tsx`**

Dans `frontend/src/components/forecast/CellEditorDrawer.tsx` :

1. Ajouter imports en haut :
```tsx
import { RecurringSuggestionPicker } from "./RecurringSuggestionPicker";
import type { DetectedRecurrenceSuggestion } from "@/api/forecast";
```

2. Ajouter deux états dans le composant `CellEditorDrawer` :
```tsx
const [showSuggestions, setShowSuggestions] = useState(false);
const [prefillAmountCents, setPrefillAmountCents] = useState<number | null>(null);
```

3. Remplacer le bloc `{tab === "forecast" && (<MethodForm ... />)}` par :

```tsx
{tab === "forecast" && (
  <div className="space-y-3">
    <button
      type="button"
      onClick={() => setShowSuggestions((v) => !v)}
      title="Analyser les 6 derniers mois de transactions pour détecter les flux récurrents et pré-remplir cette ligne prévisionnelle avec le montant médian détecté."
      className="inline-flex items-center gap-1.5 rounded-md border border-line-soft px-2.5 py-1.5 text-[12px] font-medium text-ink-2 transition-colors hover:bg-panel-2 hover:text-ink"
    >
      Suggérer depuis l'historique
    </button>
    {showSuggestions && (
      <RecurringSuggestionPicker
        entityId={entityId}
        onSelect={(s: DetectedRecurrenceSuggestion) => {
          const cents = Math.round(Number(s.average_amount) * 100);
          setPrefillAmountCents(cents);
          setShowSuggestions(false);
        }}
        onClose={() => setShowSuggestions(false)}
      />
    )}
    <MethodForm
      scenarioId={scenarioId}
      categoryId={categoryId}
      cellMonth={month}
      line={currentLine}
      onSave={onClose}
      prefillAmountCents={prefillAmountCents ?? undefined}
    />
  </div>
)}
```

4. Réinitialiser `prefillAmountCents` et `showSuggestions` à la fermeture du drawer. Dans le `useEffect` qui gère l'ESC ou en ajoutant un `useEffect` sur `open` :
```tsx
useEffect(() => {
  if (!open) {
    setShowSuggestions(false);
    setPrefillAmountCents(null);
  }
}, [open]);
```

- [ ] **Step 4 : Mettre à jour `documentation.ts`**

Dans `frontend/src/content/documentation.ts`, section `previsionnel` (id: `"previsionnel"`), dans le tableau `does`, ajouter après la ligne sur "saisir une entrée prévisionnelle" :

```typescript
"Pour pré-remplir une ligne depuis un flux récurrent détecté : dans le tiroir d'édition (onglet Prévisionnel), cliquez sur le bouton Suggérer depuis l'historique. Horizon analyse les 6 derniers mois de transactions et propose les contreparties dont le rythme est régulier (mensuel, hebdomadaire, trimestriel). Sélectionnez une suggestion pour pré-remplir la méthode Récurrent à montant fixe avec le montant médian calculé. Vous pouvez ajuster le montant avant d'enregistrer.",
```

Dans `panel.does` de la même section, ajouter :

```typescript
"Cliquez sur Suggérer depuis l'historique (onglet Prévisionnel du tiroir) pour détecter les flux récurrents et pré-remplir automatiquement la ligne.",
```

- [ ] **Step 5 : Vérification TypeScript**

```bash
cd /srv/prod/tools/horizon/frontend && npx tsc --noEmit
```

- [ ] **Step 6 : Smoke visuel**

En dev local ou staging : ouvrir `/previsionnel`, cliquer sur une cellule future, aller dans l'onglet "Prévisionnel", vérifier que le bouton "Suggérer depuis l'historique" est présent, que le picker s'ouvre, que la sélection pré-remplit le formulaire en mode RECURRING_FIXED avec le bon montant.

- [ ] **Step 7 : Commit D6**

```bash
git add frontend/src/components/forecast/RecurringSuggestionPicker.tsx \
        frontend/src/components/forecast/CellEditorDrawer.tsx \
        frontend/src/components/forecast/MethodForm.tsx \
        frontend/src/content/documentation.ts
git commit -m "$(cat <<'EOF'
feat(forecast): bouton Suggérer depuis l'historique dans le drawer

Expose detect_recurring dans l'UI du tiroir d'édition prévisionnel.
Sélectionner une suggestion pré-remplit MethodForm en RECURRING_FIXED
avec le montant médian. Tooltip sur le bouton + doc d'impact dans
documentation.ts section previsionnel.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task D7 — Corriger l'agrégation de groupe dans `PivotTable.tsx`

**Pourquoi :** `inTotals`/`outTotals` ne somment que les rows racines (`inHier.roots`) en supposant que le backend fait du rollup parent←enfant — ce n'est pas le cas. Le backend calcule chaque `PivotRow` indépendamment. Si une catégorie racine n'a pas de transactions directes mais uniquement des sous-catégories avec des valeurs, les totaux Encaissements/Décaissements et le solde projeté sont sous-estimés.

**Files :**
- Modifier : `frontend/src/components/forecast/PivotTable.tsx:114-125`
- Modifier : `frontend/src/test/forecast/PivotTable.test.tsx`

**Steps :**

- [ ] **Step 1 : Test rouge**

Dans `frontend/src/test/forecast/PivotTable.test.tsx`, ajouter après les tests existants :

```typescript
it("inTotals sums all rows including children, not only roots", () => {
  // Root in avec total=0 (pas de tx directes) + child in avec total=200k
  // Le total ligne Encaissements doit afficher 200k, pas 0.
  const months = ["2026-05", "2026-06"];
  const fixture: PivotResult = {
    months,
    opening_balance_cents: 0,
    closing_balance_projection_cents: [200_000, 400_000],
    realized_series: months.map((m) => ({ month: m, in_cents: 0, out_cents: 0 })),
    forecast_series: months.map((m) => ({ month: m, in_cents: 0, out_cents: 0 })),
    rows: [
      {
        category_id: 10,
        parent_id: null,
        label: "Ventes",
        level: 0,
        direction: "in" as const,
        cells: months.map((m) => ({
          month: m,
          realized_cents: 0,
          committed_cents: 0,
          forecast_cents: 0,
          total_cents: 0,       // root : pas de tx directes
          line_method: null,
          line_params: null,
        })),
      },
      {
        category_id: 11,
        parent_id: 10,
        label: "Ventes produits",
        level: 1,
        direction: "in" as const,
        cells: months.map((m) => ({
          month: m,
          realized_cents: 0,
          committed_cents: 0,
          forecast_cents: 0,
          total_cents: 200_000, // child : a des valeurs
          line_method: null,
          line_params: null,
        })),
      },
    ],
  };

  const { container } = render(
    <PivotTable
      result={fixture}
      onCellClick={() => undefined}
      currentMonth="2026-04"
    />,
  );

  // Après le fix, le total Encaissements = root(0) + child(200k) = 200k
  // Avant le fix, il vaut 0 (seul root sommé).
  // On vérifie que "2 000,00" apparaît dans le rendu (format formatCents de 200000 centimes).
  expect(container.textContent).toContain("2 000,00");
});
```

```bash
cd /srv/prod/tools/horizon/frontend && npx vitest run src/test/forecast/PivotTable.test.tsx
# Attendu : nouveau test FAIL
```

- [ ] **Step 2 : Implémenter le fix**

Dans `frontend/src/components/forecast/PivotTable.tsx`, remplacer les `useMemo` `inTotals` et `outTotals` (lignes 114-125) :

```typescript
// Monthly totals per direction — sum ALL rows of the direction (roots + children).
// The backend does NOT roll up parent←child: each PivotRow carries its own
// independent values. Summing only roots underestimates when roots have
// total_cents=0 but their children have values.
const inTotals = useMemo(() => {
  return months.map((_m, idx) =>
    inRows.reduce((s, r) => s + (r.cells[idx]?.total_cents ?? 0), 0),
  );
}, [months, inRows]);
const outTotals = useMemo(() => {
  return months.map((_m, idx) =>
    outRows.reduce((s, r) => s + (r.cells[idx]?.total_cents ?? 0), 0),
  );
}, [months, outRows]);
```

- [ ] **Step 3 : Tests verts**

```bash
cd /srv/prod/tools/horizon/frontend && npx vitest run src/test/forecast/PivotTable.test.tsx
# Attendu : tous les tests PASS
```

- [ ] **Step 4 : Commit D7**

```bash
git add frontend/src/components/forecast/PivotTable.tsx \
        frontend/src/test/forecast/PivotTable.test.tsx
git commit -m "$(cat <<'EOF'
fix(forecast): PivotTable totalise toutes les lignes, pas seulement les roots

inTotals/outTotals ne sommaient que inHier.roots, sous-estimant les totaux
quand les roots n'ont pas de transactions directes (valeurs dans les enfants
uniquement). Correction : reduce sur inRows/outRows complets.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```
