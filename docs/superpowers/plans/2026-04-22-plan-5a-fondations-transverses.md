# Plan 5a — Fondations transverses : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre Horizon cohérent multi-entités (filtrage global persistant) et permettre la gestion des mots de passe (self-service + admin reset), avant d'entamer le gros chantier Forecast v2.

**Architecture:** (1) Store Zustand `useEntityFilter` persisté en `localStorage`, injecté dans un nouveau `TopBar` du `Layout`, consommé par toutes les pages via un hook unifié. (2) Param `entity_id` propagé sur les endpoints manquants (`/api/transactions`, `/api/imports`, `/api/counterparties`, `/api/categories`) avec validation via `require_entity_access`. (3) Deux endpoints mot de passe : `POST /api/me/password` (self) et `POST /api/users/{id}/password` (admin). UI dédiée : page `/profil` + bouton "Réinitialiser" sur `AdminUsersPage`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, pytest. React + TS, TanStack Query, Zustand (nouveau), react-router 6.

**Branche :** `plan-5a-fondations`
**Tag attendu :** `plan-5a-done`

---

## Arborescence des fichiers touchés

### Backend
- **Créer** : aucun (extensions d'endpoints existants)
- **Modifier** :
  - `backend/app/api/transactions.py` — param `entity_id`
  - `backend/app/api/imports.py` — param `entity_id` sur `/history`
  - `backend/app/api/counterparties.py` — param `entity_id`
  - `backend/app/api/categories.py` — param `entity_id`
  - `backend/app/api/users.py` — endpoint `POST /{id}/password`
  - `backend/app/api/me.py` — endpoint `POST /password`
  - `backend/app/schemas/user.py` — nouveaux schémas `PasswordChange`, `PasswordResetByAdmin`
- **Tests** :
  - `backend/tests/api/test_transactions_entity_filter.py` (nouveau)
  - `backend/tests/api/test_imports_entity_filter.py` (nouveau)
  - `backend/tests/api/test_counterparties_entity_filter.py` (nouveau)
  - `backend/tests/api/test_categories_entity_filter.py` (nouveau)
  - `backend/tests/api/test_password_change.py` (nouveau)

### Frontend
- **Créer** :
  - `frontend/src/stores/entityFilter.ts` — store Zustand
  - `frontend/src/components/TopBar.tsx` — barre haute avec sélecteur entité + menu user
  - `frontend/src/components/EntitySelector.tsx` — dropdown dédié
  - `frontend/src/pages/ProfilPage.tsx` — changement mdp self-service
  - `frontend/src/pages/AdminUsersResetPasswordDialog.tsx` — modale reset mdp (admin)
  - `frontend/src/api/password.ts` — hooks `useChangeOwnPassword`, `useAdminResetPassword`
- **Modifier** :
  - `frontend/src/components/Layout.tsx` — insérer `<TopBar />`
  - `frontend/src/App.tsx` (ou le fichier de routes) — route `/profil`
  - `frontend/src/pages/TransactionsPage.tsx` — consommer le store + colonne Société
  - `frontend/src/pages/ImportHistoryPage.tsx` — consommer le store
  - `frontend/src/pages/CounterpartiesPage.tsx` — consommer le store
  - `frontend/src/pages/DashboardPage.tsx` — remplacer le `useState` local par le store
  - `frontend/src/pages/ForecastPage.tsx` — idem
  - `frontend/src/pages/RulesPage.tsx` — idem
  - `frontend/src/pages/AdminUsersPage.tsx` — bouton "Réinitialiser mot de passe"
  - `frontend/src/api/transactions.ts`, `imports.ts`, `counterparties.ts` — propager `entityId`
  - `frontend/package.json` — dépendance `zustand`
- **Tests** :
  - `frontend/src/test/entityFilter.test.ts` (store)
  - `frontend/src/test/TopBar.test.tsx`
  - `frontend/src/test/ProfilPage.test.tsx`

---

## Phase A — Backend : `entity_id` sur endpoints manquants

### Task A1 : Filtre `entity_id` sur `/api/transactions`

**Files:**
- Modify: `backend/app/api/transactions.py:20-67`
- Test: `backend/tests/api/test_transactions_entity_filter.py`

- [ ] **A1.1 — Écrire le test d'acceptation**

Créer `backend/tests/api/test_transactions_entity_filter.py` :

```python
from datetime import date
from decimal import Decimal

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.transaction import Transaction, TransactionDirection
from app.models.user_entity_access import UserEntityAccess


def _seed_two_entities_with_tx(db, admin_user):
    e1 = Entity(name="Soc1", legal_form="SAS")
    e2 = Entity(name="Soc2", legal_form="SAS")
    db.add_all([e1, e2])
    db.flush()
    db.add_all([
        UserEntityAccess(user_id=admin_user.id, entity_id=e1.id),
        UserEntityAccess(user_id=admin_user.id, entity_id=e2.id),
    ])
    ba1 = BankAccount(entity_id=e1.id, iban="FR7611111111111111111111111", bank_code="DELUBAC", label="C1")
    ba2 = BankAccount(entity_id=e2.id, iban="FR7622222222222222222222222", bank_code="DELUBAC", label="C2")
    db.add_all([ba1, ba2])
    db.flush()
    db.add_all([
        Transaction(bank_account_id=ba1.id, operation_date=date(2026, 1, 10), label="TX1", amount=Decimal("-10"), direction=TransactionDirection.DEBIT),
        Transaction(bank_account_id=ba2.id, operation_date=date(2026, 1, 11), label="TX2", amount=Decimal("-20"), direction=TransactionDirection.DEBIT),
    ])
    db.commit()
    return e1, e2


def test_transactions_filter_by_entity_id(client, db, admin_user, admin_session):
    e1, e2 = _seed_two_entities_with_tx(db, admin_user)
    r = client.get(f"/api/transactions?entity_id={e1.id}", cookies=admin_session)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["label"] == "TX1"


def test_transactions_entity_id_without_access_is_forbidden(client, db, reader_user, reader_session):
    # reader_user n'a pas d'accès à e3
    e3 = Entity(name="Secret", legal_form="SAS")
    db.add(e3); db.commit()
    r = client.get(f"/api/transactions?entity_id={e3.id}", cookies=reader_session)
    assert r.status_code == 403
```

- [ ] **A1.2 — Lancer, observer l'échec**

```bash
cd backend && uv run pytest tests/api/test_transactions_entity_filter.py -v
```
Expected: FAIL (param `entity_id` n'existe pas encore).

- [ ] **A1.3 — Implémenter**

Dans `backend/app/api/transactions.py`, modifier la signature de `list_transactions` :

```python
@router.get("", response_model=TransactionListResponse)
def list_transactions(
    *,
    session: Session = Depends(get_db),
    user: User = Depends(require_authenticated),
    entity_id: int | None = Query(None),
    bank_account_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    counterparty_id: int | None = Query(None),
    search: str | None = Query(None),
    uncategorized: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
) -> TransactionListResponse:
    accessible_entity_ids = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )
    stmt = select(Transaction).join(BankAccount).where(
        BankAccount.entity_id.in_(accessible_entity_ids),
    )
    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        stmt = stmt.where(BankAccount.entity_id == entity_id)
    # … reste inchangé
```

- [ ] **A1.4 — Vérifier les tests**

```bash
cd backend && uv run pytest tests/api/test_transactions_entity_filter.py -v
```
Expected: PASS (2/2).

- [ ] **A1.5 — Commit**

```bash
git add backend/app/api/transactions.py backend/tests/api/test_transactions_entity_filter.py
git commit -m "feat(transactions): filter by entity_id + require access"
```

---

### Task A2 : Filtre `entity_id` sur `/api/imports/history`

**Files:**
- Modify: `backend/app/api/imports.py:70-95`
- Test: `backend/tests/api/test_imports_entity_filter.py`

- [ ] **A2.1 — Écrire le test**

Reproduire la structure de A1 mais avec 2 `ImportRecord` (un par entité), puis `GET /api/imports/history?entity_id={e1.id}` → 1 item. Ajouter un test 403 pour entité non accessible.

- [ ] **A2.2 — Lancer, vérifier l'échec**

```bash
cd backend && uv run pytest tests/api/test_imports_entity_filter.py -v
```

- [ ] **A2.3 — Implémenter**

Ajouter param `entity_id: int | None = Query(None)` à `list_imports` + appel à `require_entity_access` si fourni + ajouter `.where(BankAccount.entity_id == entity_id)` au stmt.

- [ ] **A2.4 — Vérifier PASS**

- [ ] **A2.5 — Commit**

```bash
git commit -m "feat(imports): filter /history by entity_id"
```

---

### Task A3 : Filtre `entity_id` sur `/api/counterparties`

**Files:**
- Modify: `backend/app/api/counterparties.py:20-35`
- Test: `backend/tests/api/test_counterparties_entity_filter.py`

- [ ] **A3.1 — Test** : seed 2 entités avec 1 tiers chacune, vérifier `?entity_id={e1.id}` → 1 tiers.
- [ ] **A3.2 — Fail run**
- [ ] **A3.3 — Implémenter** : param `entity_id` + `require_entity_access` + `.where(Counterparty.entity_id == entity_id)`
- [ ] **A3.4 — Pass run**
- [ ] **A3.5 — Commit** : `feat(counterparties): filter by entity_id`

---

### Task A4 : `entity_id` sur `/api/categories`

**Décision :** Les catégories restent **globales** pour l'instant (table `categories` sans `entity_id`). Le param accepté est no-op mais silent (200 retourne la liste complète). On évite ainsi un changement de schéma hors-scope. Documenter dans docstring.

- [ ] **A4.1 — Test** : `GET /api/categories?entity_id=1` → 200 + liste complète (même réponse que sans param).
- [ ] **A4.2 — Implémenter** : accepter `entity_id: int | None = Query(None)` sans l'utiliser, docstring `"""Accepte entity_id pour compat future ; les catégories sont globales."""`.
- [ ] **A4.3 — Pass run**
- [ ] **A4.4 — Commit** : `chore(categories): accept entity_id no-op for future compat`

---

## Phase B — Backend : endpoints mot de passe

### Task B1 : Schemas Pydantic

**Files:**
- Modify: `backend/app/schemas/user.py`

- [ ] **B1.1 — Ajouter** :

```python
from pydantic import BaseModel, Field, SecretStr


class PasswordChangePayload(BaseModel):
    current_password: SecretStr
    new_password: SecretStr = Field(min_length=12)


class AdminPasswordResetPayload(BaseModel):
    new_password: SecretStr = Field(min_length=12)
```

- [ ] **B1.2 — Commit** : `feat(schemas): password change payloads`

---

### Task B2 : `POST /api/me/password` (self-service)

**Files:**
- Modify: `backend/app/api/me.py`
- Test: `backend/tests/api/test_password_change.py`

- [ ] **B2.1 — Tests**

```python
def test_change_own_password_success(client, db, admin_user, admin_session):
    r = client.post(
        "/api/me/password",
        json={"current_password": "AdminPassword2026!", "new_password": "NewPassword2026!!"},
        cookies=admin_session,
    )
    assert r.status_code == 204
    # Re-login avec nouveau mdp
    r2 = client.post("/api/auth/login", json={"email": admin_user.email, "password": "NewPassword2026!!"})
    assert r2.status_code == 200


def test_change_own_password_wrong_current(client, admin_session):
    r = client.post(
        "/api/me/password",
        json={"current_password": "WrongPassword!", "new_password": "NewPassword2026!!"},
        cookies=admin_session,
    )
    assert r.status_code == 400


def test_change_own_password_weak_new(client, admin_session):
    r = client.post(
        "/api/me/password",
        json={"current_password": "AdminPassword2026!", "new_password": "short"},
        cookies=admin_session,
    )
    assert r.status_code == 422  # Pydantic min_length


def test_change_own_password_requires_auth(client):
    r = client.post(
        "/api/me/password",
        json={"current_password": "x", "new_password": "NewPassword2026!!"},
    )
    assert r.status_code == 401
```

- [ ] **B2.2 — Run, fail**

- [ ] **B2.3 — Implémenter** — dans `backend/app/api/me.py` :

```python
from fastapi import HTTPException, status
from app.schemas.user import PasswordChangePayload
from app.security import hash_password, validate_password_policy, verify_password


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_own_password(
    payload: PasswordChangePayload,
    *,
    session: Session = Depends(get_db),
    user: User = Depends(require_authenticated),
) -> None:
    if not verify_password(payload.current_password.get_secret_value(), user.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    new_pw = payload.new_password.get_secret_value()
    validate_password_policy(new_pw)
    user.password_hash = hash_password(new_pw)
    session.commit()
```

- [ ] **B2.4 — Pass run**

- [ ] **B2.5 — Commit** : `feat(me): POST /api/me/password — self-service change`

---

### Task B3 : `POST /api/users/{id}/password` (admin reset)

**Files:**
- Modify: `backend/app/api/users.py`
- Test: `backend/tests/api/test_password_change.py` (mêmes fichier, tests ajoutés)

- [ ] **B3.1 — Tests**

```python
def test_admin_reset_password(client, db, admin_session, reader_user):
    r = client.post(
        f"/api/users/{reader_user.id}/password",
        json={"new_password": "ResetPassword2026!!"},
        cookies=admin_session,
    )
    assert r.status_code == 204
    r2 = client.post("/api/auth/login", json={"email": reader_user.email, "password": "ResetPassword2026!!"})
    assert r2.status_code == 200


def test_non_admin_cannot_reset_password(client, reader_session, admin_user):
    r = client.post(
        f"/api/users/{admin_user.id}/password",
        json={"new_password": "ResetPassword2026!!"},
        cookies=reader_session,
    )
    assert r.status_code == 403


def test_admin_reset_password_404_on_missing_user(client, admin_session):
    r = client.post(
        "/api/users/99999/password",
        json={"new_password": "ResetPassword2026!!"},
        cookies=admin_session,
    )
    assert r.status_code == 404
```

- [ ] **B3.2 — Run, fail**

- [ ] **B3.3 — Implémenter**

```python
@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def admin_reset_password(
    user_id: int,
    payload: AdminPasswordResetPayload,
    db: Session = Depends(get_db),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    new_pw = payload.new_password.get_secret_value()
    validate_password_policy(new_pw)
    user.password_hash = hash_password(new_pw)
    db.commit()
```

- [ ] **B3.4 — Pass run**

- [ ] **B3.5 — Commit** : `feat(users): POST /{id}/password — admin reset`

---

## Phase C — Frontend : store entité global

### Task C1 : Installer Zustand

- [ ] **C1.1** — `cd frontend && npm install zustand`
- [ ] **C1.2 — Commit** : `chore(frontend): add zustand dependency`

---

### Task C2 : Créer le store `entityFilter`

**Files:**
- Create: `frontend/src/stores/entityFilter.ts`
- Test: `frontend/src/test/entityFilter.test.ts`

- [ ] **C2.1 — Test**

```ts
import { describe, expect, it, beforeEach } from "vitest";
import { useEntityFilter } from "@/stores/entityFilter";

describe("useEntityFilter", () => {
  beforeEach(() => {
    localStorage.clear();
    useEntityFilter.setState({ entityId: null });
  });

  it("defaults to null (all entities)", () => {
    expect(useEntityFilter.getState().entityId).toBeNull();
  });

  it("setEntityId updates the store", () => {
    useEntityFilter.getState().setEntityId(42);
    expect(useEntityFilter.getState().entityId).toBe(42);
  });

  it("persists entityId to localStorage", () => {
    useEntityFilter.getState().setEntityId(7);
    const raw = localStorage.getItem("horizon:entityFilter");
    expect(raw).toContain("\"entityId\":7");
  });
});
```

- [ ] **C2.2 — Run, fail**

```bash
cd frontend && npm run test -- entityFilter
```

- [ ] **C2.3 — Implémenter**

```ts
// frontend/src/stores/entityFilter.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface EntityFilterState {
  entityId: number | null;
  setEntityId: (id: number | null) => void;
}

export const useEntityFilter = create<EntityFilterState>()(
  persist(
    (set) => ({
      entityId: null,
      setEntityId: (id) => set({ entityId: id }),
    }),
    { name: "horizon:entityFilter" }
  )
);
```

- [ ] **C2.4 — Pass run**

- [ ] **C2.5 — Commit** : `feat(stores): global entity filter store (zustand + persist)`

---

### Task C3 : Composant `EntitySelector`

**Files:**
- Create: `frontend/src/components/EntitySelector.tsx`

- [ ] **C3.1 — Implémenter** (pas de test unitaire dédié, couvert par TopBar) :

```tsx
import { useEntities } from "@/api/entities";
import { useEntityFilter } from "@/stores/entityFilter";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function EntitySelector() {
  const entitiesQuery = useEntities();
  const { entityId, setEntityId } = useEntityFilter();
  const entities = entitiesQuery.data ?? [];

  const value = entityId === null ? "all" : String(entityId);

  return (
    <Select
      value={value}
      onValueChange={(v) => setEntityId(v === "all" ? null : Number(v))}
    >
      <SelectTrigger className="w-[220px]">
        <SelectValue placeholder="Toutes les sociétés" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">Toutes les sociétés</SelectItem>
        {entities.map((e) => (
          <SelectItem key={e.id} value={String(e.id)}>{e.name}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

- [ ] **C3.2 — Commit** : `feat(components): EntitySelector reading from global store`

---

### Task C4 : `TopBar` + intégration dans `Layout`

**Files:**
- Create: `frontend/src/components/TopBar.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Test: `frontend/src/test/TopBar.test.tsx`

- [ ] **C4.1 — Test**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TopBar } from "@/components/TopBar";

// Mock useEntities + useMe
vi.mock("@/api/entities", () => ({
  useEntities: () => ({ data: [{ id: 1, name: "ACREED" }], isLoading: false }),
}));
vi.mock("@/hooks/useAuth", () => ({
  useMe: () => ({ data: { email: "admin@acreed.fr", full_name: "Admin" } }),
}));

it("renders EntitySelector and user menu", () => {
  const qc = new QueryClient();
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <TopBar />
      </MemoryRouter>
    </QueryClientProvider>
  );
  expect(screen.getByText(/Toutes les sociétés/i)).toBeInTheDocument();
  expect(screen.getByText(/Admin/i)).toBeInTheDocument();
});
```

- [ ] **C4.2 — Implémenter** `TopBar.tsx` : contient l'`EntitySelector` à gauche + un dropdown user à droite avec items "Mon profil" (lien `/profil`) et "Se déconnecter".

- [ ] **C4.3 — Modifier `Layout.tsx`** pour ajouter la TopBar :

```tsx
import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';

export function Layout() {
  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-x-hidden">
          <div className="mx-auto w-full max-w-[1320px] px-8 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
```

- [ ] **C4.4 — Pass run**

- [ ] **C4.5 — Commit** : `feat(layout): TopBar with global EntitySelector + user menu`

---

## Phase D — Frontend : propager `entityId` dans les hooks API

### Task D1 : Ajouter `entityId` aux signatures

**Files:**
- Modify: `frontend/src/api/transactions.ts`, `imports.ts`, `counterparties.ts`

- [ ] **D1.1** — Dans chaque fichier, ajouter `entityId?: number | null` au payload du hook et propager en query param si défini.

Exemple pour `transactions.ts` :
```ts
export function useTransactions(filters: { entityId?: number | null; /* … */ }) {
  const params = new URLSearchParams();
  if (filters.entityId != null) params.set("entity_id", String(filters.entityId));
  // … autres params
  return useQuery({ queryKey: ["transactions", filters], queryFn: () => apiFetch(`/api/transactions?${params}`) });
}
```

- [ ] **D1.2 — Commit** : `feat(api): plumb entityId on transactions/imports/counterparties hooks`

---

### Task D2 : Consommer le store sur chaque page

**Files (modify):**
- `frontend/src/pages/TransactionsPage.tsx`
- `frontend/src/pages/ImportHistoryPage.tsx`
- `frontend/src/pages/CounterpartiesPage.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/ForecastPage.tsx`
- `frontend/src/pages/RulesPage.tsx`

- [ ] **D2.1** — Dans chaque page :
  - Supprimer le `useState("all")` local d'entité
  - Remplacer par `const entityId = useEntityFilter((s) => s.entityId);`
  - Passer `entityId` dans la query
  - Supprimer le sélecteur d'entité local sur la page (il est désormais global dans la TopBar)

- [ ] **D2.2** — Lancer `npm run test` et `npm run build`, tout doit passer.

- [ ] **D2.3 — Commit** : `refactor(pages): wire all pages to global entity filter store`

---

### Task D3 : Colonne Société dans Transactions

**Files:**
- Modify: `frontend/src/pages/TransactionsPage.tsx`
- Modify: `backend/app/api/transactions.py` (si non déjà exposé : inclure `bank_account.entity_name` dans la réponse)

- [ ] **D3.1 — Vérifier la réponse** — Si `TransactionRead` n'expose pas `entity_name`, l'ajouter (join `BankAccount.entity.name`). Sinon passer.

- [ ] **D3.2 — Frontend** — Ajouter une colonne "Société" entre Date et Tiers, visible **uniquement quand `entityId === null`** (filtre global = toutes les sociétés). Sinon elle reste masquée pour éviter la redondance.

- [ ] **D3.3 — Test manuel** : builder frontend, ouvrir `/transactions`, vérifier.

- [ ] **D3.4 — Commit** : `feat(transactions): Société column when no entity filter`

---

## Phase E — Frontend : pages mot de passe

### Task E1 : API hooks password

**Files:**
- Create: `frontend/src/api/password.ts`

- [ ] **E1.1 — Implémenter** :

```ts
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export function useChangeOwnPassword() {
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      apiFetch("/api/me/password", { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } }),
  });
}

export function useAdminResetPassword(userId: number) {
  return useMutation({
    mutationFn: (body: { new_password: string }) =>
      apiFetch(`/api/users/${userId}/password`, { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } }),
  });
}
```

- [ ] **E1.2 — Commit** : `feat(api): password mutation hooks`

---

### Task E2 : Page `/profil`

**Files:**
- Create: `frontend/src/pages/ProfilPage.tsx`
- Modify: `frontend/src/App.tsx` (ou `routes.tsx`) — ajouter `<Route path="profil" element={<ProfilPage />} />`
- Test: `frontend/src/test/ProfilPage.test.tsx`

- [ ] **E2.1 — Test**

```tsx
// happy path
it("submits new password and shows success toast", async () => {
  // mock useChangeOwnPassword → success
  render(<ProfilPage />);
  await userEvent.type(screen.getByLabelText(/actuel/i), "OldPass2026!!");
  await userEvent.type(screen.getByLabelText(/nouveau/i), "NewPass2026!!");
  await userEvent.type(screen.getByLabelText(/confirmation/i), "NewPass2026!!");
  await userEvent.click(screen.getByRole("button", { name: /enregistrer/i }));
  await waitFor(() => expect(screen.getByText(/mis à jour/i)).toBeInTheDocument());
});

// mismatch
it("shows error if new != confirmation", async () => { /* … */ });

// wrong current → 400 → toast erreur
it("shows backend error on wrong current password", async () => { /* … */ });
```

- [ ] **E2.2 — Implémenter**

```tsx
export function ProfilPage() {
  const { data: me } = useMe();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const mutation = useChangeOwnPassword();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null); setSuccess(false);
    if (next !== confirm) { setError("Les deux mots de passe ne correspondent pas"); return; }
    if (next.length < 12) { setError("Minimum 12 caractères"); return; }
    try {
      await mutation.mutateAsync({ current_password: current, new_password: next });
      setSuccess(true);
      setCurrent(""); setNext(""); setConfirm("");
    } catch (err: any) {
      setError(err?.message ?? "Erreur");
    }
  };

  return (
    <div className="max-w-md">
      <h1 className="text-2xl font-semibold mb-6">Mon profil</h1>
      <section className="mb-8">
        <p className="text-sm text-muted-foreground">{me?.email}</p>
        <p>{me?.full_name}</p>
      </section>
      <section>
        <h2 className="text-lg font-medium mb-4">Changer mon mot de passe</h2>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Mot de passe actuel" type="password" value={current} onChange={setCurrent} required />
          <Field label="Nouveau mot de passe" type="password" value={next} onChange={setNext} required />
          <Field label="Confirmation" type="password" value={confirm} onChange={setConfirm} required />
          {error && <p className="text-destructive text-sm">{error}</p>}
          {success && <p className="text-success text-sm">Mot de passe mis à jour</p>}
          <Button type="submit" disabled={mutation.isPending}>Enregistrer</Button>
        </form>
      </section>
    </div>
  );
}
```

(Le composant `Field` est un wrapper simple `<Label/><Input/>`.)

- [ ] **E2.3 — Ajouter la route** dans le router principal.

- [ ] **E2.4 — Pass run**

- [ ] **E2.5 — Commit** : `feat(profil): /profil page with self-service password change`

---

### Task E3 : Admin reset password dans `AdminUsersPage`

**Files:**
- Create: `frontend/src/pages/AdminUsersResetPasswordDialog.tsx`
- Modify: `frontend/src/pages/AdminUsersPage.tsx`

- [ ] **E3.1 — Implémenter la modale** : Dialog shadcn/ui avec 1 champ "nouveau mot de passe", submit → `useAdminResetPassword(userId)`. Affiche une confirmation au succès.

- [ ] **E3.2 — Ajouter le bouton** dans la liste des utilisateurs (à côté des boutons Éditer/Désactiver) : icône clé + label "Réinitialiser mot de passe" → ouvre la modale pour ce `user.id`.

- [ ] **E3.3 — Commit** : `feat(admin/users): reset password dialog`

---

## Phase F — E2E + déploiement

### Task F1 : Test E2E manuel

- [ ] **F1.1** — Rebuild prod : `docker compose -f docker-compose.prod.yml up -d --build`
- [ ] **F1.2** — Ouvrir `https://horizon.acreedconsulting.com`. Checklist :
  - [ ] TopBar visible avec sélecteur "Toutes les sociétés"
  - [ ] Changer d'entité persiste après reload (localStorage)
  - [ ] Filtre actif sur Dashboard, Transactions, Forecast, Rules, Imports, Tiers
  - [ ] Colonne "Société" visible sur Transactions quand filtre = "Toutes"
  - [ ] Page `/profil` accessible, changement mdp fonctionne (tester login après)
  - [ ] Admin peut réinitialiser le mdp d'un autre user (tester login après)

### Task F2 : Merge + tag

- [ ] **F2.1** — Merger `plan-5a-fondations` dans `main` :
```bash
git checkout main
git merge --no-ff plan-5a-fondations -m "merge: plan-5a — fondations transverses"
git tag plan-5a-done
git push origin main --tags
```
- [ ] **F2.2** — Rebuild prod final + vérification `/readyz` = 200.

---

## Self-Review

**Spec coverage :**
- A. Sélecteur entité global → Phases C + D ✅
- B. `entity_id` partout → Phase A ✅
- C. URL-sync → **retiré** (localStorage suffit pour v1, URL-sync = scope creep pour Plan 5a ; à replanifier si besoin dans Plan 5c).
- D. Self-service password → Task B2 + E2 ✅
- E. Admin reset password → Task B3 + E3 ✅
- F. Regroupement/colonne Société Transactions → Task D3 ✅

**Placeholder scan :** les tests E2 sont esquissés (2e/3e cas) — remplacer par code complet à l'exécution. À l'exception de ces deux cas minor, le plan est concret.

**Type consistency :** `PasswordChangePayload.current_password`, `PasswordChangePayload.new_password`, `AdminPasswordResetPayload.new_password` cohérents entre backend et frontend. Champ store `entityId` (number | null) cohérent partout.

**Note :** URL-sync volontairement descopé (cf. point C). Ajouter au backlog pour Plan 5c si Tristan en fait la demande.
