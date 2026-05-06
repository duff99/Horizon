# Plan B — Refonte page Engagements (À encaisser / À payer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Refondre la page Engagements en "À encaisser / À payer" : trois onglets (in / out / Tout), KPI cards (30j, retards, nb retards), badge "En retard", bandeau d'alerte fantômes (>7j retard sans match) avec action en masse "Clôturer", score de matching exposé dans le dialog d'appariement, bandeau d'introduction permanent, section documentation au format FeatureDoc, tooltips d'impact.

**Architecture :** Backend FastAPI + SQLAlchemy : endpoints d'agrégats (KPI 30j/retards/fantômes) calculés en SQL agrégat, endpoint POST bulk-cancel pour clôturer en masse, extension du schema CommitmentSuggestion avec score + breakdown. Frontend React + react-query : refonte CommitmentsPage (split direction onglets, cards KPI, badge En retard, bandeau alerte fantômes), MatchDialog enrichi avec score visible et bordure verte si ≥80, tooltips d'impact sur Matcher/Clôturer.

**Tech Stack :** FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest, React 18, react-query, TypeScript, Tailwind, composants UI maison.

**Spec source :** `docs/superpowers/specs/2026-05-06-tiers-engagements-refonte-design.md` (section "Page 2 — À encaisser / À payer").

**Précondition :** Plan A (refonte Tiers) mergé sur main. La règle d'équipe doc d'impact est déjà posée dans CLAUDE.md, le type FeatureDoc existe dans documentation.ts.

---

## Phase 1 — Backend Engagements

### Task 1 : Endpoint agrégats KPI

**Files:**
- Modify: `backend/app/api/commitments.py` (nouvelle route GET `/aggregates`)
- Modify: `backend/app/schemas/commitment.py` (schémas `CommitmentKpis`, `CommitmentDirectionKpis`)
- Create: `backend/tests/test_api_commitments_aggregates.py`

**Spec :**

GET `/api/commitments/aggregates?entity_id=X&direction=in|out|null` retourne :

```json
{
  "in": {
    "total_30d_cents": 123456,    // somme amount_cents pending, expected_date dans [today, today+30j]
    "overdue_total_cents": 78900, // somme amount_cents pending, expected_date < today
    "overdue_count": 4,           // count des pending overdue
    "phantom_count": 2            // count pending sans match dont expected_date < today - 7j
  },
  "out": { ... même structure ... }
}
```

Si `direction` est précisé, ne retourne qu'un côté (clé unique). Sinon retourne les deux. Toujours filtré par les entités accessibles à l'utilisateur (subquery `accessible_entity_ids_subquery`).

**Steps :**

- [ ] **Step 1: Ajouter les schémas Pydantic**

Dans `backend/app/schemas/commitment.py` ajouter :

```python
class CommitmentDirectionKpis(BaseModel):
    total_30d_cents: int
    overdue_total_cents: int
    overdue_count: int
    phantom_count: int


class CommitmentKpis(BaseModel):
    in_: CommitmentDirectionKpis | None = Field(default=None, alias="in")
    out: CommitmentDirectionKpis | None = None

    model_config = ConfigDict(populate_by_name=True)
```

(Le `model_config` permet de sérialiser sous la clé `"in"` même si l'attribut Python est `in_` — `in` est un mot-clé réservé.)

- [ ] **Step 2: Écrire le test**

Créer `backend/tests/test_api_commitments_aggregates.py` avec :

```python
"""GET /api/commitments/aggregates retourne les KPI consolidés par direction."""
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus


def _commit(entity_id, direction, amount_cents, expected_offset_days, status=CommitmentStatus.PENDING):
    today = date.today()
    return Commitment(
        entity_id=entity_id, direction=direction, amount_cents=amount_cents,
        issue_date=today - timedelta(days=30),
        expected_date=today + timedelta(days=expected_offset_days),
        status=status,
    )


def test_aggregates_kpi_per_direction(
    client: TestClient, db_session: Session, auth_user_with_bank_account,
) -> None:
    e_id = auth_user_with_bank_account["bank_account"].entity_id
    db_session.add_all([
        # in : 1 dans 15j (10€), 1 retard 3j (20€), 1 fantôme retard 14j (50€)
        _commit(e_id, CommitmentDirection.IN, 1000, 15),
        _commit(e_id, CommitmentDirection.IN, 2000, -3),
        _commit(e_id, CommitmentDirection.IN, 5000, -14),
        # out : 1 dans 7j (40€)
        _commit(e_id, CommitmentDirection.OUT, 4000, 7),
        # cancelled : ignoré
        _commit(e_id, CommitmentDirection.IN, 9999, -10, status=CommitmentStatus.CANCELLED),
    ])
    db_session.commit()

    resp = client.get("/api/commitments/aggregates", params={"entity_id": e_id})
    assert resp.status_code == 200
    body = resp.json()

    assert body["in"]["total_30d_cents"] == 1000
    assert body["in"]["overdue_total_cents"] == 2000 + 5000  # 70€
    assert body["in"]["overdue_count"] == 2
    assert body["in"]["phantom_count"] == 1                  # le -14j sans match

    assert body["out"]["total_30d_cents"] == 4000
    assert body["out"]["overdue_count"] == 0
    assert body["out"]["phantom_count"] == 0


def test_aggregates_filtered_by_direction(
    client: TestClient, db_session: Session, auth_user_with_bank_account,
) -> None:
    e_id = auth_user_with_bank_account["bank_account"].entity_id
    db_session.add(_commit(e_id, CommitmentDirection.IN, 1000, 5))
    db_session.add(_commit(e_id, CommitmentDirection.OUT, 2000, 5))
    db_session.commit()

    resp = client.get(
        "/api/commitments/aggregates",
        params={"entity_id": e_id, "direction": "in"},
    )
    body = resp.json()
    assert body["in"]["total_30d_cents"] == 1000
    assert body.get("out") is None
```

- [ ] **Step 3: Lancer le test, vérifier qu'il échoue**

```bash
docker exec horizon-backend-1 sh -c 'cd /app && python -m pytest tests/test_api_commitments_aggregates.py -xvs --no-cov'
```

Attendu : 404 sur la route.

- [ ] **Step 4: Implémenter l'endpoint**

Dans `backend/app/api/commitments.py`, ajouter avant la route `list_commitments` :

```python
@router.get("/aggregates", response_model=CommitmentKpis)
def aggregates(
    entity_id: int | None = Query(default=None),
    direction: Literal["in", "out"] | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CommitmentKpis:
    accessible = _accessible_entity_ids(session, user)
    if entity_id is not None:
        if entity_id not in accessible:
            raise HTTPException(status_code=403, detail="Entité non accessible")
        scope = [Commitment.entity_id == entity_id]
    else:
        scope = [Commitment.entity_id.in_(accessible)]

    today = date.today()
    h30 = today + timedelta(days=30)
    phantom_cutoff = today - timedelta(days=7)

    def _kpi_for(d: CommitmentDirection) -> CommitmentDirectionKpis:
        base = and_(
            *scope,
            Commitment.direction == d,
            Commitment.status == CommitmentStatus.PENDING,
        )
        total_30d = session.scalar(
            select(func.coalesce(func.sum(Commitment.amount_cents), 0)).where(
                and_(base,
                     Commitment.expected_date >= today,
                     Commitment.expected_date <= h30)
            )
        ) or 0
        overdue_total = session.scalar(
            select(func.coalesce(func.sum(Commitment.amount_cents), 0)).where(
                and_(base, Commitment.expected_date < today)
            )
        ) or 0
        overdue_count = session.scalar(
            select(func.count(Commitment.id)).where(
                and_(base, Commitment.expected_date < today)
            )
        ) or 0
        phantom_count = session.scalar(
            select(func.count(Commitment.id)).where(
                and_(base,
                     Commitment.matched_transaction_id.is_(None),
                     Commitment.expected_date < phantom_cutoff)
            )
        ) or 0
        return CommitmentDirectionKpis(
            total_30d_cents=int(total_30d),
            overdue_total_cents=int(overdue_total),
            overdue_count=int(overdue_count),
            phantom_count=int(phantom_count),
        )

    if direction == "in":
        return CommitmentKpis(in_=_kpi_for(CommitmentDirection.IN))
    if direction == "out":
        return CommitmentKpis(out=_kpi_for(CommitmentDirection.OUT))
    return CommitmentKpis(
        in_=_kpi_for(CommitmentDirection.IN),
        out=_kpi_for(CommitmentDirection.OUT),
    )
```

Imports manquants en haut du fichier :

```python
from datetime import date, timedelta
from app.schemas.commitment import CommitmentKpis, CommitmentDirectionKpis
```

(`date` est déjà importé en l10. Vérifier que `timedelta` ne l'est pas et l'ajouter.)

- [ ] **Step 5: Vérifier le passage**

```bash
docker exec horizon-backend-1 sh -c 'cd /app && python -m pytest tests/test_api_commitments_aggregates.py -xvs --no-cov'
```

Attendu : 2/2 PASS.

**IMPORTANT — workflow docker pour les tests :**
- Copier les fichiers modifiés/créés vers le container : `docker cp <local> horizon-backend-1:/app/<path>`
- Cibles à copier : tout fichier de `backend/app/` ou `backend/tests/` ou `backend/alembic/versions/` modifié
- Le tests dir n'est pas monté en volume, copies obligatoires à chaque itération

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/commitments.py backend/app/schemas/commitment.py backend/tests/test_api_commitments_aggregates.py
git commit -m "feat(api): GET /api/commitments/aggregates — KPI 30j, retards, fantômes par direction"
```

---

### Task 2 : Score exposé dans suggest-matches

**Files:**
- Modify: `backend/app/schemas/commitment.py` (`TransactionBrief` → ajouter score + breakdown)
- Modify: `backend/app/api/commitments.py` (route `suggest_matches_endpoint`)
- Modify: `backend/tests/` (compléter test existant)

**Spec :** chaque candidat retourné par `GET /api/commitments/{id}/suggest-matches` doit porter `score` (int 0-100) et `score_breakdown` (objet avec `amount_diff_eur`, `date_diff_days`, `counterparty_match` bool).

- [ ] **Step 1: Étendre le schema**

```python
class CommitmentScoreBreakdown(BaseModel):
    amount_diff_eur: float
    date_diff_days: int
    counterparty_match: bool


class TransactionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_date: date
    label: str
    amount: Decimal
    bank_account_label: str | None = None
    score: int | None = None
    score_breakdown: CommitmentScoreBreakdown | None = None
```

- [ ] **Step 2: Étendre l'endpoint pour transmettre le score**

Dans `suggest_matches_endpoint`, le service `suggest_matches` retourne déjà `(tx, score)`. Il faut juste calculer la breakdown et passer le tout. Helper local :

```python
from app.services.commitment_matching import _direction_of_tx  # déjà privé, OK pour usage interne


def _breakdown(commitment: Commitment, tx: Transaction) -> CommitmentScoreBreakdown:
    cp_match = (
        commitment.counterparty_id is not None
        and tx.counterparty_id is not None
        and tx.counterparty_id == commitment.counterparty_id
    )
    commitment_eur = commitment.amount_cents / 100.0
    return CommitmentScoreBreakdown(
        amount_diff_eur=float(commitment_eur - float(abs(tx.amount))),
        date_diff_days=(tx.operation_date - commitment.expected_date).days,
        counterparty_match=bool(cp_match),
    )
```

Puis dans la boucle :

```python
items = [
    TransactionBrief(
        id=tx.id, operation_date=tx.operation_date, label=tx.label,
        amount=tx.amount, bank_account_label=ba_map.get(tx.bank_account_id),
        score=score,
        score_breakdown=_breakdown(c, tx),
    )
    for tx, score in candidates
]
```

- [ ] **Step 3: Test**

Compléter ou ajouter un test dans `backend/tests/test_api_commitments_suggest.py` (s'il n'existe pas, créer) :

```python
"""GET /api/commitments/{id}/suggest-matches expose score + breakdown."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction


def test_suggest_matches_exposes_score_and_breakdown(
    client: TestClient, db_session: Session, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    today = date.today()

    imp = ImportRecord(
        bank_account_id=ba.id, filename="x.pdf",
        file_sha256="d"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.flush()

    c = Commitment(
        entity_id=e_id, direction=CommitmentDirection.OUT,
        amount_cents=10000, issue_date=today - timedelta(days=10),
        expected_date=today, status=CommitmentStatus.PENDING,
    )
    db_session.add(c); db_session.flush()

    db_session.add(Transaction(
        bank_account_id=ba.id, import_id=imp.id,
        operation_date=today, value_date=today,
        label="ACME 100", raw_label="ACME 100", amount=Decimal("-100"),
        dedup_key="dks1", statement_row_index=1,
    ))
    db_session.commit()

    resp = client.get(f"/api/commitments/{c.id}/suggest-matches")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["candidates"]) == 1
    cand = body["candidates"][0]
    assert cand["score"] is not None
    assert cand["score_breakdown"]["date_diff_days"] == 0
    assert cand["score_breakdown"]["amount_diff_eur"] == 0.0
    assert cand["score_breakdown"]["counterparty_match"] is False
```

- [ ] **Step 4: Lancer**

```bash
docker exec horizon-backend-1 sh -c 'cd /app && python -m pytest tests/test_api_commitments_suggest.py -xvs --no-cov'
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/commitment.py backend/app/api/commitments.py backend/tests/test_api_commitments_suggest.py
git commit -m "feat(commitments): expose score + breakdown sur /suggest-matches"
```

---

### Task 3 : Endpoint bulk-cancel (clôturer fantômes en masse)

**Files:**
- Modify: `backend/app/api/commitments.py` (route POST `/bulk-cancel`)
- Modify: `backend/app/schemas/commitment.py` (schema `BulkCancelRequest` + `BulkCancelResponse`)
- Create: `backend/tests/test_api_commitments_bulk_cancel.py`

**Spec :** POST `/api/commitments/bulk-cancel` body `{"ids": [1,2,3]}` → bascule tous les commitments listés en `cancelled` après vérif d'accès entity. Retourne `{cancelled: int}` (nombre effectivement modifié, ignore les déjà-cancelled). Loggue UNE entrée audit par commitment (action="update", before/after).

- [ ] **Step 1: Schémas**

```python
class BulkCancelRequest(BaseModel):
    ids: list[int]


class BulkCancelResponse(BaseModel):
    cancelled: int
```

- [ ] **Step 2: Test**

`backend/tests/test_api_commitments_bulk_cancel.py` :

```python
"""POST /api/commitments/bulk-cancel basculer plusieurs engagements en cancelled."""
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus


def _c(e_id, status=CommitmentStatus.PENDING):
    today = date.today()
    return Commitment(
        entity_id=e_id, direction=CommitmentDirection.IN, amount_cents=100,
        issue_date=today - timedelta(days=30), expected_date=today,
        status=status,
    )


def test_bulk_cancel_pending_commitments(
    client: TestClient, db_session: Session, auth_user_with_bank_account,
) -> None:
    e_id = auth_user_with_bank_account["bank_account"].entity_id
    a, b, already = _c(e_id), _c(e_id), _c(e_id, status=CommitmentStatus.CANCELLED)
    db_session.add_all([a, b, already]); db_session.commit()

    resp = client.post("/api/commitments/bulk-cancel", json={"ids": [a.id, b.id, already.id]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["cancelled"] == 2
    db_session.expire_all()
    assert db_session.get(Commitment, a.id).status == CommitmentStatus.CANCELLED
    assert db_session.get(Commitment, b.id).status == CommitmentStatus.CANCELLED


def test_bulk_cancel_rejects_cross_entity(
    client: TestClient, db_session: Session, auth_user_with_bank_account,
) -> None:
    """Si un id n'appartient pas à une entité accessible, refuser globalement."""
    from app.models.entity import Entity
    e_id = auth_user_with_bank_account["bank_account"].entity_id
    other = Entity(name="Autre", legal_name="Autre SARL")
    db_session.add(other); db_session.flush()
    a = _c(e_id)
    forbidden = _c(other.id)
    db_session.add_all([a, forbidden]); db_session.commit()

    resp = client.post(
        "/api/commitments/bulk-cancel",
        json={"ids": [a.id, forbidden.id]},
    )
    assert resp.status_code == 403
```

- [ ] **Step 3: Implémentation**

```python
@router.post("/bulk-cancel", response_model=BulkCancelResponse)
def bulk_cancel(
    payload: BulkCancelRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> BulkCancelResponse:
    if not payload.ids:
        return BulkCancelResponse(cancelled=0)
    accessible = set(_accessible_entity_ids(session, user))
    rows = session.execute(
        select(Commitment).where(Commitment.id.in_(payload.ids))
    ).scalars().all()
    if any(c.entity_id not in accessible for c in rows):
        raise HTTPException(status_code=403, detail="Engagement hors périmètre")
    cancelled = 0
    for c in rows:
        if c.status == CommitmentStatus.CANCELLED:
            continue
        before = to_dict_for_audit(c)
        c.status = CommitmentStatus.CANCELLED
        session.flush()
        record_audit(
            session, user=user, action="update", entity=c,
            before=before, after=to_dict_for_audit(c), request=request,
        )
        cancelled += 1
    session.commit()
    return BulkCancelResponse(cancelled=cancelled)
```

- [ ] **Step 4: Tests + commit**

```bash
docker exec horizon-backend-1 sh -c 'cd /app && python -m pytest tests/test_api_commitments_bulk_cancel.py -xvs --no-cov'
git add backend/app/api/commitments.py backend/app/schemas/commitment.py backend/tests/test_api_commitments_bulk_cancel.py
git commit -m "feat(api): POST /api/commitments/bulk-cancel — clôturer plusieurs engagements en une opération"
```

---

## Phase 2 — Frontend Engagements

### Task 4 : API client (KPI, score, bulk-cancel)

**Files:**
- Modify: `frontend/src/api/commitments.ts`

- [ ] **Step 1: Étendre le module**

Ajouter en haut du fichier les types :

```ts
export interface CommitmentDirectionKpis {
  total_30d_cents: number;
  overdue_total_cents: number;
  overdue_count: number;
  phantom_count: number;
}

export interface CommitmentKpis {
  in?: CommitmentDirectionKpis;
  out?: CommitmentDirectionKpis;
}

export interface CommitmentScoreBreakdown {
  amount_diff_eur: number;
  date_diff_days: number;
  counterparty_match: boolean;
}
```

Étendre `CommitmentTransactionBrief` (déjà exporté) :

```ts
export interface CommitmentTransactionBrief {
  id: number;
  operation_date: string;
  label: string;
  amount: string;
  bank_account_label: string | null;
  score: number | null;
  score_breakdown: CommitmentScoreBreakdown | null;
}
```

Ajouter les fonctions API :

```ts
export async function fetchCommitmentKpis(
  args: { entityId?: number | null; direction?: "in" | "out" } = {},
): Promise<CommitmentKpis> {
  const p = new URLSearchParams();
  if (args.entityId != null) p.set("entity_id", String(args.entityId));
  if (args.direction) p.set("direction", args.direction);
  const qs = p.toString() ? `?${p}` : "";
  return apiFetch<CommitmentKpis>(`/api/commitments/aggregates${qs}`);
}

export function useCommitmentKpis(
  args: { entityId?: number | null; direction?: "in" | "out" },
) {
  return useQuery({
    queryKey: ["commitment-kpis", args],
    queryFn: () => fetchCommitmentKpis(args),
  });
}

export async function bulkCancelCommitments(ids: number[]): Promise<{ cancelled: number }> {
  return apiFetch<{ cancelled: number }>("/api/commitments/bulk-cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
}

export function useBulkCancelCommitments() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: bulkCancelCommitments,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["commitments"] });
      qc.invalidateQueries({ queryKey: ["commitment-kpis"] });
    },
  });
}
```

(Vérifier l'usage existant de `apiFetch` ou `fetch` dans le fichier et rester cohérent avec le style local.)

- [ ] **Step 2: Typecheck**

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit
```

Attendu : pas d'erreur sur `commitments.ts`. Erreur tolérée sur `CommitmentsPage.tsx` (réécrit en Task 5).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/commitments.ts
git commit -m "feat(frontend/api): client commitments enrichi (KPI, score, bulk-cancel)"
```

---

### Task 5 : Refonte CommitmentsPage (3 onglets, KPI cards, badge "En retard")

**Files:**
- Modify: `frontend/src/pages/CommitmentsPage.tsx` (réécriture complète)
- Modify: `frontend/src/components/Sidebar.tsx` (renommer "Engagements" → "À encaisser / À payer")

**Spec :**
- Onglets `Tab` : "À encaisser" (in), "À payer" (out), "Tout" (mixte)
- Cards KPI en haut (3 si onglet single, 6 si onglet "Tout")
- Bandeau d'introduction permanent (texte fixe spec section "Bandeau d'introduction permanent")
- Badge "En retard" rouge si `pending && expected_date < aujourd'hui`
- Tri par défaut : retards en haut, puis expected_date asc
- Bouton "Tout clôturer" en haut quand le bandeau d'alerte fantômes est actif (Task 6)

- [ ] **Step 1: Renommer dans Sidebar**

`frontend/src/components/Sidebar.tsx` : remplacer le label de l'item Engagements par `'À encaisser / À payer'`. Conserver la route.

- [ ] **Step 2: Réécrire CommitmentsPage**

Structure recommandée (s'inspirer du style minimal et propre de la nouvelle CounterpartiesPage déjà mergée) :

```tsx
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { EntitySelector } from "@/components/EntitySelector";
import { useEntityFilter } from "../stores/entityFilter";
import {
  useCommitments, useCancelCommitment, useUpdateCommitment, useCommitmentKpis,
  type Commitment, type CommitmentDirection,
} from "../api/commitments";
import { CommitmentFormDialog } from "./CommitmentFormDialog";
import { CommitmentMatchDialog } from "./CommitmentMatchDialog";
import { GhostCommitmentsBanner } from "@/components/GhostCommitmentsBanner";

type Tab = "in" | "out" | "all";

const fmtEur = (cents: number) => new Intl.NumberFormat("fr-FR", {
  style: "currency", currency: "EUR", maximumFractionDigits: 0,
}).format(cents / 100);
const fmtDate = (iso: string) => new Date(iso).toLocaleDateString("fr-FR");

function isOverdue(c: Commitment): boolean {
  return c.status === "pending" && new Date(c.expected_date) < new Date(new Date().toDateString());
}
```

L'idée :
- État local `tab: "in" | "out" | "all"` (par défaut `"in"`).
- `useCommitmentKpis` filtré par `entityId` + `direction` (omis si `tab==="all"`, on a alors les deux).
- `useCommitments` avec `direction: tab === "all" ? undefined : tab`, `status="pending"` par défaut, `perPage: 100`.
- Trois Tabs cliquables. Sous chaque, les cards KPI.
- Tableau réutilisé (proche de l'existant) avec colonnes : Statut (Badge En retard ROUGE si overdue), Tiers, Catégorie, Date prévue, Montant, Référence (issue_date passe dans une tooltip ou cachée), Tx matchée, Actions (Modifier / Matcher / Clôturer).
- Tri front : `(c) => isOverdue(c) ? 0 : 1` puis `expected_date asc`.
- Bandeau d'introduction permanent (section "Bandeau d'introduction permanent" de la spec, copié verbatim).
- `<GhostCommitmentsBanner entityId={entityId} direction={tab === "all" ? undefined : tab} />` au-dessus du tableau (composant créé Task 6).

**Bouton "Annuler" → "Clôturer"** : changer le libellé partout (copy plus orthogonal au métier — la spec utilise "Clôturer"). Garder l'icône / l'emplacement.

- [ ] **Step 3: Cards KPI**

Composant local ou inline :

```tsx
function KpiCard({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "warn" }) {
  return (
    <div className={cn(
      "rounded-xl border p-4 shadow-card",
      tone === "warn" ? "border-amber-200 bg-amber-50" : "border-line-soft bg-panel",
    )}>
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn(
        "mt-1 text-[18px] font-semibold tabular-nums",
        tone === "warn" ? "text-amber-900" : "text-ink",
      )}>{value}</div>
    </div>
  );
}
```

Sur onglet single (in OU out), 3 cards : "Sous 30 jours", "En retard (montant)", "En retard (nombre)".
Sur onglet "Tout", 6 cards regroupées en 2 lignes (à encaisser / à payer).

- [ ] **Step 4: Vérifications**

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit 2>&1 | grep -v "GhostCommitmentsBanner"
```

Attendu : pas d'erreur (sauf imports en attente du composant Task 6).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Sidebar.tsx frontend/src/pages/CommitmentsPage.tsx
git commit -m "feat(engagements): refonte page — 3 onglets in/out/all, KPI cards, badge En retard"
```

---

### Task 6 : Bandeau d'alerte fantômes + dialog "Tout clôturer"

**Files:**
- Create: `frontend/src/components/GhostCommitmentsBanner.tsx`

**Spec :** Le bandeau s'affiche en haut de la liste si `phantom_count > 0` (donné par les KPI). Texte verbatim spec ligne 138. Deux actions :
- "Voir la liste" → applique un filtre rapide pour ne montrer que les fantômes (passe l'état parent à un mode `filterPhantomsOnly` que la page consomme dans son tri/filtre, ex. ?phantoms=1 dans l'URL ou un état React).
- "Tout clôturer" → ouvre une `ConfirmDialog`, après confirmation appelle `bulkCancelCommitments(ids)` avec la liste des ids fantômes (à récupérer via une query dédiée ou en filtrant les commitments déjà chargés).

Pragmatique pour V1 : l'action "Tout clôturer" peut faire un GET supplémentaire pour récupérer les ids fantômes (ou les calculer côté front à partir des commitments déjà listés si tous sont chargés). On simplifie : on charge tous les `pending` du périmètre courant, on filtre côté front les fantômes (`expected_date < today - 7j && matched_transaction_id == null`), on liste les ids, on appelle `bulkCancelCommitments`.

```tsx
import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  useCommitments,
  useBulkCancelCommitments,
  useCommitmentKpis,
} from "../api/commitments";

type Props = {
  entityId: number | null;
  direction?: "in" | "out";
  onShowPhantomsOnly: () => void;
};

export function GhostCommitmentsBanner({ entityId, direction, onShowPhantomsOnly }: Props) {
  const kpis = useCommitmentKpis({ entityId, direction });
  const phantomCount =
    (kpis.data?.in?.phantom_count ?? 0) + (kpis.data?.out?.phantom_count ?? 0);

  const all = useCommitments({ entityId, status: "pending", direction, perPage: 500 });
  const phantomIds = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);
    return (all.data?.items ?? [])
      .filter(c => !c.matched_transaction_id && new Date(c.expected_date) < cutoff)
      .map(c => c.id);
  }, [all.data]);

  const cancelMut = useBulkCancelCommitments();
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!phantomCount || phantomCount === 0) return null;

  return (
    <>
      <div className="flex items-start justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-[13px] text-amber-900">
        <div>
          <strong>{phantomCount} engagement(s) probablement fantômes.</strong>{" "}
          Ces lignes en retard de plus de 7 jours sans transaction associée
          gonflent peut-être ton prévisionnel à tort.
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="ghost" size="sm" onClick={onShowPhantomsOnly}>
            Voir la liste
          </Button>
          <Button size="sm" onClick={() => setConfirmOpen(true)}>
            Tout clôturer
          </Button>
        </div>
      </div>

      {confirmOpen && (
        <ConfirmDialog
          open
          tone="danger"
          title={`Clôturer ${phantomIds.length} engagement(s) fantôme(s) ?`}
          description={
            "Ils seront marqués comme annulés et sortiront du prévisionnel " +
            "et des indicateurs DSO/DPO. Action irréversible (mais réversible " +
            "ligne par ligne via Réactiver)."
          }
          confirmLabel="Clôturer"
          busy={cancelMut.isPending}
          onCancel={() => setConfirmOpen(false)}
          onConfirm={() => {
            cancelMut.mutate(phantomIds, {
              onSuccess: () => setConfirmOpen(false),
            });
          }}
        />
      )}
    </>
  );
}
```

CommitmentsPage doit gérer un état local `phantomsOnly: boolean` — quand activé, filtre la liste affichée aux ids fantômes uniquement, et affiche un bouton "Voir tout" pour annuler le filtre.

- [ ] **Step 1: Créer le composant**
- [ ] **Step 2: Brancher dans CommitmentsPage** (ajouter l'état `phantomsOnly`)
- [ ] **Step 3: Typecheck + commit**

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit
git add frontend/src/components/GhostCommitmentsBanner.tsx frontend/src/pages/CommitmentsPage.tsx
git commit -m "feat(engagements): bandeau alerte fantômes + action Tout clôturer en masse"
```

---

### Task 7 : MatchDialog enrichi (score visible)

**Files:**
- Modify: `frontend/src/pages/CommitmentMatchDialog.tsx`

**Spec :** chaque suggestion affiche maintenant le score (0-100) et la décomposition courte. Bordure verte sur les candidats de score ≥ 80.

- [ ] **Step 1: Adapter le rendu**

Sur chaque `<li>` candidat (autour de la ligne 110 de l'existant) :

```tsx
const isStrong = (tx.score ?? 0) >= 80;
return (
  <li
    key={tx.id}
    className={cn(
      "flex items-center gap-3 px-3 py-2.5 transition-colors",
      isStrong && "border-l-2 border-emerald-500 bg-emerald-50/40",
    )}
  >
    {/* ... existing date/label/amount ... */}
    {tx.score != null && tx.score_breakdown && (
      <div className="w-[180px] shrink-0 text-right">
        <div className={cn(
          "text-[13px] font-semibold tabular-nums",
          isStrong ? "text-emerald-700" : "text-ink-2",
        )}>
          Score {tx.score}
        </div>
        <div className="text-[11px] text-muted-foreground">
          Montant ±{tx.score_breakdown.amount_diff_eur.toFixed(0)} €,
          date ±{Math.abs(tx.score_breakdown.date_diff_days)} j
          {tx.score_breakdown.counterparty_match && " · tiers identique +20"}
        </div>
      </div>
    )}
    {/* button Lier */}
  </li>
);
```

(Adapter les widths du flex pour conserver un rendu propre ; au besoin retirer `w-[110px]` du montant et compresser.)

- [ ] **Step 2: Typecheck + commit**

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit
git add frontend/src/pages/CommitmentMatchDialog.tsx
git commit -m "feat(engagements): score + breakdown dans le dialog de matching, bordure verte si ≥80"
```

---

### Task 8 : Tooltips + section documentation FeatureDoc

**Files:**
- Modify: `frontend/src/pages/CommitmentsPage.tsx` (tooltips title= sur Matcher / Clôturer)
- Modify: `frontend/src/content/documentation.ts` (renommer + réécrire la section Engagements)

- [ ] **Step 1: Tooltips d'impact**

Sur le bouton Matcher (CommitmentsPage et CommitmentMatchDialog si pertinent) ajouter `title=` :

```
title="Lie cet engagement à la transaction réelle correspondante. L'engagement passe en 'Payé' et sort du prévisionnel."
```

Sur Clôturer (anciennement Annuler) :

```
title="Marque l'engagement comme annulé. Il sort du prévisionnel et des indicateurs DSO/DPO. Utilise pour les fantômes ou les factures finalement non émises."
```

- [ ] **Step 2: Section documentation.ts**

Repérer l'actuelle section `id: "engagements"` (ou équivalent — chercher "Engagements" dans le fichier). La remplacer par une section au format FeatureDoc, en s'inspirant de la section "tiers" récemment refondue (id="tiers"). Couvrir :

- title : "À encaisser / À payer"
- subtitle : "Saisis ici les factures que tu attends ou que tu dois payer. Elles alimentent ton prévisionnel et tes indicateurs DSO/DPO."
- sees : trois onglets, KPI cards 30j / retards / fantômes, badge En retard rouge, bandeau alerte fantômes, tableau, dialog matching avec score.
- does : créer / modifier / matcher / clôturer / clôturer en masse via bandeau, voir transaction matchée.
- tips :
  - Matcher est automatique au moment de l'import quand un seul candidat dépasse score 80 (et qu'il est unique en tête).
  - Le score est calculé à partir de l'écart de montant, de date et d'un bonus si le tiers est identique.
  - Un engagement non matché vieux de plus de 7 jours est considéré "fantôme" — bandeau d'alerte.
  - Clôturer est réversible via Réactiver.
- panel : version condensée 4-5 puces.

Ne PAS créer une entrée FeatureDoc séparée — pour cette V1, on étend la `DocSectionData` existante. Le type `FeatureDoc` créé Plan A reste réservé aux futures actions à effet documentées séparément.

- [ ] **Step 3: Typecheck + commit**

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit
git add frontend/src/pages/CommitmentsPage.tsx frontend/src/pages/CommitmentMatchDialog.tsx frontend/src/content/documentation.ts
git commit -m "docs(engagements): documentation refondue + tooltips d'impact sur Matcher/Clôturer"
```

---

### Task 9 : Build live + smoke

**Files:** —

- [ ] **Step 1: Build & redeploy**

```bash
cd /srv/prod/tools/horizon
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d backend frontend
```

- [ ] **Step 2: Smoke**

```bash
sleep 5
docker exec horizon-backend-1 sh -c 'python -c "import urllib.request; r=urllib.request.urlopen(\"http://localhost:8000/api/commitments/aggregates\")"'
```

Attendu : 401 sans auth (= endpoint en place).

- [ ] **Step 3: Final summary**

Tous les tests passent localement :

```bash
docker exec horizon-backend-1 sh -c 'cd /app && python -m pytest tests/test_api_commitments_aggregates.py tests/test_api_commitments_suggest.py tests/test_api_commitments_bulk_cancel.py --no-cov'
```

Frontend typecheck propre :

```bash
cd /srv/prod/tools/horizon/frontend && pnpm tsc --noEmit
```

---

## Self-review (à effectuer avant exécution)

1. Tous les commits sont sur la branche `refonte/engagements` (créée depuis main, après merge Plan A).
2. Aucun nouveau type non aligné sur le modèle DB (Commitment.amount_cents, Commitment.issue_date, statuts pending/paid/cancelled).
3. Les tests utilisent `auth_user_with_bank_account` quand HTTP, `db_session` direct quand pur DB.
4. Le calcul `phantom_count` (>7j retard sans match) est cohérent avec la définition utilisée côté front pour `bulkCancel`.
5. Le bandeau d'introduction permanent est strictement présent en V1 sur la page (pas optionnel).

## Hors scope (rappel)

- Import CSV / PDF d'engagements
- Engagements récurrents auto-générés
- Notifications retard (email/push)
- Filtre catégorie/tiers fin (déjà couvert par les filtres existants `from`/`to` ; pas d'ajout V1)
