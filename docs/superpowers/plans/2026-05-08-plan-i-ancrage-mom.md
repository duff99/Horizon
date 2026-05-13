# Plan I — Ancrage anti-mois-vide + MoM 6 mois (remplace YoY)

> **For agentic workers:** Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal :** Réparer les widgets analytiques qui s'ancrent sur `date.today()` et finissent vides parce que l'utilisateur importe ses relevés en fin de mois (le mois courant n'a aucune transaction tant que l'import n'est pas fait). Et remplacer le widget YoY (Year-over-Year) par un widget **MoM 6 mois glissants finis** mieux adapté à ce workflow et à un historique court (4 mois en prod aujourd'hui).

**Décision utilisateur (2026-05-08) :**
- I1 : ancrage uniformisé via helper `_data_anchor()`.
- I2 : remplacer YoY par MoM 6 mois (pas de gating, suppression du widget YoY existant).

**Tech Stack :** FastAPI, SQLAlchemy 2.x, Postgres, React 18, Recharts, pytest, Vitest.

---

## Conventions de l'app à respecter

- Tests dans le container backend : `docker exec horizon-backend-1 pytest -x tests/test_xxx.py -v --no-cov`.
- Frontend : `cd frontend && npx tsc -b && npx vitest --run`.
- Migrations : pas de migration alembic dans ce plan.
- Commits français, ton sobre, sans emoji, format `feat/fix/refactor(scope): message (I{n})`. Co-author Claude.
- Pas de `cat .env`, pas de `sed -i` sur DB.
- Doc d'impact : I2 supprime un widget visible et le remplace → mise à jour `frontend/src/content/documentation.ts` section `analyse` + lexique sigles (retirer mention YoY si elle figure ; ajouter MoM si nécessaire).

---

## File Structure

### Création
- `backend/app/services/_anchor.py` (ou ajouter dans `services/analysis.py`) — helper `data_anchor(session, entity_id) -> date` qui renvoie `min(date.today(), MAX(operation_date_for_entity))`. Si aucune data, fallback sur `date.today()`.
- `backend/tests/test_data_anchor.py` — couvre les 3 cas (data récente, data ancienne, pas de data).
- `backend/tests/test_mom_endpoint.py` — couvre le nouveau endpoint MoM.
- `frontend/src/components/analyse/MoMChart.tsx` — nouveau composant Recharts.

### Modification
- `backend/app/services/analysis.py` :
  - Refactorer `_compute_runway_core` (ligne 547), `compute_client_concentration` (ligne 699), `compute_entities_comparison` (ligne 798), `compute_runway` si nécessaire — pour utiliser `data_anchor` au lieu de `date.today()`.
  - Supprimer `compute_yoy` (lignes ~614-691) et schémas `YoYPoint`, `YoYResponse` associés.
  - Ajouter `compute_mom_6m(session, entity_id) -> MoM6MResponse` qui calcule les 6 mois finis [M-6, M-5, M-4, M-3, M-2, M-1] basés sur l'ancre data, avec revenues/expenses par mois et delta % vs mois précédent.
- `backend/app/services/anomaly.py` ligne 62 — utiliser `data_anchor`.
- `backend/app/api/treasury.py` ligne 253 — utiliser `data_anchor`. Note : par compte, l'ancre devrait être par compte (`MAX(period_end)` pour les comptes du tenant) — utiliser un ancrage cohérent par tenant.
- `backend/app/api/forecast.py` ligne 146 — `get_rolling_13w` : utiliser l'ancre data pour la "semaine courante" de référence au lieu de today.
- `backend/app/api/analysis.py` :
  - Supprimer route `/yoy` et `/yoy/export`.
  - Ajouter route `/mom` et éventuellement `/mom/export` (si on conserve l'export — recommandé).
- `backend/app/schemas/analysis.py` — supprimer `YoYPoint`/`YoYResponse`, ajouter `MoMPoint`/`MoMResponse`.
- `frontend/src/types/analysis.ts` — idem.
- `frontend/src/api/analysis.ts` — supprimer `useYoY`/`fetchYoY`, ajouter `useMoM`/`fetchMoM`.
- `frontend/src/components/analyse/YoYChart.tsx` — **supprimer le fichier** (remplacé par `MoMChart`).
- `frontend/src/pages/AnalysePage.tsx` — remplacer `<YoYChart>` par `<MoMChart>`.
- `frontend/src/content/documentation.ts` section `analyse` — actualiser : retirer YoY, décrire MoM 6 mois, retirer l'entrée de lexique YoY si présente.

---

## Task I1 — Helper `data_anchor` et refactor des 6 call-sites

**Pourquoi :** uniformiser l'ancrage temporel. Si l'utilisateur n'a pas encore importé le mois courant, l'ancre vaut le 1er du mois suivant la dernière transaction au lieu d'aujourd'hui. Les widgets ne pointent plus dans le vide.

**Files :**
- Create : `backend/app/services/_anchor.py` (ou ajouter dans analysis.py)
- Create : `backend/tests/test_data_anchor.py`
- Modify : `backend/app/services/analysis.py` (compute_runway_core, compute_client_concentration, compute_entities_comparison)
- Modify : `backend/app/services/anomaly.py`
- Modify : `backend/app/api/treasury.py`
- Modify : `backend/app/api/forecast.py` (get_rolling_13w)

**Steps :**

- [ ] **Step 1 : Créer le helper `data_anchor`**

```python
# backend/app/services/_anchor.py (nouveau fichier)
"""Helper d'ancrage temporel pour les widgets analytiques.

Quand l'utilisateur importe ses relevés en fin de mois, le mois courant est
vide jusqu'à l'import. Les widgets ancrés sur `date.today()` calculent alors
sur des fenêtres qui incluent un mois sans data. `data_anchor` borne `today`
au-dessous par MAX(operation_date) de l'entité.

Sémantique : `data_anchor` est un proxy de "aujourd'hui" qui ne dépasse jamais
la date de la dernière transaction connue. C'est un repère lisible et stable
entre 2 imports.
"""
from __future__ import annotations
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.transaction import Transaction


def data_anchor(session: Session, entity_id: int | None = None) -> date:
    """Retourne min(today, MAX(operation_date)).

    Si entity_id donné : MAX limité aux comptes de l'entité.
    Si pas de transaction : fallback sur today.
    """
    today = date.today()
    q = select(func.max(Transaction.operation_date)).where(
        Transaction.is_aggregation_parent.is_(False)
    )
    if entity_id is not None:
        q = q.join(BankAccount, BankAccount.id == Transaction.bank_account_id).where(
            BankAccount.entity_id == entity_id
        )
    max_op = session.execute(q).scalar()
    if max_op is None:
        return today
    return min(today, max_op)
```

- [ ] **Step 2 : Tests `test_data_anchor.py`**

```python
def test_data_anchor_no_data_returns_today(db_session):
    assert data_anchor(db_session, entity_id=999) == date.today()

def test_data_anchor_recent_data_returns_today(db_session, entity, ...):
    # créer tx avec operation_date = today
    assert data_anchor(db_session, entity.id) == date.today()

def test_data_anchor_old_data_returns_max_operation_date(db_session, entity, ...):
    # créer tx avec operation_date = today - 60 jours
    sixty_ago = date.today() - timedelta(days=60)
    # ... insert
    assert data_anchor(db_session, entity.id) == sixty_ago
```

- [ ] **Step 3 : Refactorer les 6 call-sites**

Dans `analysis.py` (3 fonctions) :
```python
# Avant : today = date.today()
# Après : today = data_anchor(session, entity_id=entity_id)
```
Faire la même chose dans :
- `anomaly.py:62` (`detect_anomalies`)
- `treasury.py:253` (`get_per_account` — passer `entity_id` si dispo, sinon None pour ancre globale du tenant)
- `forecast.py:146` (`get_rolling_13w`)

- [ ] **Step 4 : Run tests**

```bash
docker exec horizon-backend-1 pytest tests/test_data_anchor.py tests/test_g1_daily_balance.py tests/test_g4_anomalies.py tests/test_g10_per_account.py tests/test_g2_rolling13w.py -v --no-cov
```

- [ ] **Step 5 : Commit**

```bash
git add -A && git commit -m "feat(analyse): ancrage data_anchor() au lieu de today() partout (I1)"
```

---

## Task I2 — Remplacer YoY par MoM 6 mois glissants

**Pourquoi :** YoY (12 mois N vs N-1) inutile dans le workflow utilisateur (4 mois de data, mois courant toujours vide). MoM 6 mois finis [M-6 à M-1] est exploitable dès 2 mois de data, lisible, et aligne le widget sur la réalité du workflow.

**Files :**
- Delete : `frontend/src/components/analyse/YoYChart.tsx`
- Create : `frontend/src/components/analyse/MoMChart.tsx`, `backend/tests/test_mom_endpoint.py`
- Modify : `backend/app/services/analysis.py` (supprimer compute_yoy, ajouter compute_mom_6m), `backend/app/api/analysis.py` (supprimer routes /yoy + /yoy/export, ajouter /mom), `backend/app/schemas/analysis.py`, `frontend/src/types/analysis.ts`, `frontend/src/api/analysis.ts`, `frontend/src/pages/AnalysePage.tsx`, `frontend/src/content/documentation.ts`.

**Spécification MoM 6 mois :**
- Fenêtre : 6 mois finis = [M-6, M-5, M-4, M-3, M-2, M-1] où M est le mois de `data_anchor`. Le mois M (= mois ancre) est exclu (peut être partiel).
- Pour chaque mois : `revenues_cents` (sum(amount > 0)), `expenses_cents` (abs(sum(amount < 0))), `net_cents`, `delta_revenues_pct` (vs mois précédent), `delta_expenses_pct` (vs mois précédent).
- Si moins de 6 mois de data, retourner les mois disponibles + flag `available_months: int`.

**Steps :**

- [ ] **Step 1 : Test rouge — créer `tests/test_mom_endpoint.py`**

Cas à couvrir :
- Endpoint répond 200 avec entity_id valide.
- Avec 6+ mois de data : retourne 6 points dans l'ordre chronologique.
- Avec 3 mois de data : retourne 3 points + `available_months=3`.
- Aucune data : retourne tableau vide + `available_months=0`.
- Reader sur entity hors accès : 403.

- [ ] **Step 2 : Implémenter `compute_mom_6m` dans `services/analysis.py`**

```python
def compute_mom_6m(session: Session, *, entity_id: int) -> MoMResponse:
    anchor = data_anchor(session, entity_id=entity_id)
    anchor_first = _first_of_month(anchor)
    # 6 mois finis avant anchor_first
    months = [_add_months(anchor_first, -i) for i in range(6, 0, -1)]
    # earliest = M-6, latest = M-1 inclus → exclusive = anchor_first
    earliest = months[0]
    latest = anchor_first
    
    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    if not ba_ids:
        return MoMResponse(months=[], series=[], available_months=0)
    
    # ... requête group_by month_col, calcul revenues/expenses
    
    # construire la série en gardant l'ordre chronologique, calculer delta_pct vs mois précédent
    # available_months = nombre de mois avec au moins une tx parmi les 6
```

- [ ] **Step 3 : Schemas et endpoint**

```python
# backend/app/schemas/analysis.py
class MoMPoint(BaseModel):
    month: str  # "2026-04"
    revenues_cents: int
    expenses_cents: int
    net_cents: int
    delta_revenues_pct: float | None  # None pour le 1er mois
    delta_expenses_pct: float | None

class MoMResponse(BaseModel):
    months: list[str]
    series: list[MoMPoint]
    available_months: int

# backend/app/api/analysis.py
@router.get("/mom", response_model=MoMResponse)
def get_mom(...): return compute_mom_6m(session, entity_id=entity_id)

@router.get("/mom/export") def export_mom(...) -> StreamingResponse: ...  # CSV
```

- [ ] **Step 4 : Supprimer YoY**

- Retirer `compute_yoy` de `services/analysis.py`.
- Retirer routes `/yoy` et `/yoy/export` de `api/analysis.py`.
- Retirer schemas `YoYPoint`/`YoYResponse` de `schemas/analysis.py`.
- Retirer/adapter test `tests/test_g11_exports.py` (s'il teste YoY export → renommer pour MoM).
- Adapter tout test `compute_yoy` existant pour cibler MoM.

- [ ] **Step 5 : Frontend — remplacer YoYChart par MoMChart**

- Supprimer `frontend/src/components/analyse/YoYChart.tsx`.
- Créer `MoMChart.tsx` (Recharts ComposedChart : barres revenues/expenses + ligne net, tooltip, légende française "Encaissements / Décaissements / Net").
- Adapter `AnalysePage.tsx` (remplacer import + JSX).
- `api/analysis.ts` : retirer `useYoY/fetchYoY`, ajouter `useMoM/fetchMoM`.
- `types/analysis.ts` : retirer YoYResponse/YoYPoint, ajouter MoM*.
- `documentation.ts` : section `analyse` — retirer mention YoY, ajouter description MoM 6 mois. Lexique sigles : retirer YoY si présent.

- [ ] **Step 6 : Tests frontend**

```bash
cd frontend && npx tsc -b && npx vitest --run
```

- [ ] **Step 7 : Commit**

```bash
git add -A && git commit -m "feat(analyse): remplace YoY par MoM 6 mois glissants finis (I2)"
```

---

## Build & deploy en fin de plan

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
sleep 6
curl -sS https://horizon.acreedconsulting.com/api/readyz
```

Smoke check : login admin, page Analyse, vérifier que MoMChart s'affiche avec les 4 mois disponibles (4 mois de data prod jan-avr 2026 → série courte mais lisible).
