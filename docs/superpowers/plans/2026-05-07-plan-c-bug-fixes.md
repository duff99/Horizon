# Plan C — Bug fixes cross-domaines (P0 consolidés) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Refermer les 13 bugs P0 listés dans
`docs/superpowers/audits/2026-05-06-app-review-master.md` + une tâche
préalable C14 (compte READER de test). Aucun ajout fonctionnel : on lève
la dette qui décrédibilise les widgets, sécurise les fuites multi-tenant,
et aligne la doc sécurité avec le code.

**Architecture :**
- Backend (Python/FastAPI/SQLAlchemy 2.x) : 1 nouvelle migration
  (`session_token_version` sur `users`), 1 nouveau service (`audit.py`
  enrichi avec helper batch), 1 nouveau middleware ASGI (`X-Request-ID`),
  fixes ponctuels dans `services/categorization.py`, `services/analysis.py`,
  `api/health.py`, `api/router.py`, `api/bank_accounts.py`,
  `api/admin_audit.py`, `api/auth.py`, `api/users.py`, `api/transactions.py`,
  `api/rules.py`.
- Frontend (React 18 / TS / react-query / Tailwind) : 1 nouveau composant
  `AdminRoute`, fixes dans `RuleForm.tsx` (setters manquants),
  routes admin protégées dans `router.tsx`.
- Tests : pytest dans le container backend (`docker exec horizon-backend-1
  pytest …`). Cookie session : `BACKEND_COOKIE_SECURE=false` en env de test
  (déjà appliqué via conftest, cf. commit 434f6af).
- Documentation d'impact (règle CLAUDE.md) : mise à jour de
  `frontend/src/content/documentation.ts` à la fin du plan, **section par
  section** au fur et à mesure des features touchées (analyse, règles,
  admin, sécurité).

**Tech Stack :** FastAPI, SQLAlchemy 2.x, Postgres, Alembic, React 18,
react-query 5, react-router-dom 6, TypeScript, Tailwind, pytest, itsdangerous
(TimestampSigner pour le token de session).

---

## File Structure

### Création
- `backend/alembic/versions/20260507_1000_user_session_token_version.py` —
  ajoute colonne `session_token_version: int default 1 not null` sur `users`.
- `backend/app/middleware/__init__.py` — package marker.
- `backend/app/middleware/request_id.py` — middleware ASGI X-Request-ID +
  contextvar.
- `backend/app/services/audit_batch.py` — helpers `record_batch_audit(...)`
  centralisant les 3 sites try/except dupliqués
  (transactions.py / rules.py × 2).
- `backend/tests/test_request_id_middleware.py`
- `backend/tests/test_session_token_version.py`
- `backend/tests/test_preview_rule_tenant.py`
- `backend/tests/test_categorization_parent_filter.py`
- `backend/tests/test_analysis_anchor.py`
- `backend/tests/test_admin_audit_merge_filter.py`
- `backend/tests/test_health_alias.py`
- `backend/tests/test_bank_accounts_reader.py`
- `frontend/src/components/AdminRoute.tsx`

### Modification
- `backend/app/services/analysis.py` — ancrage temporel + guard drift (C1, C2, C3).
- `backend/app/services/categorization.py` — filtre `parent_transaction_id IS NULL` (C4) + signature `preview_rule(..., user)` pour scope global (C6).
- `backend/app/api/rules.py` — passe `user` à `preview_rule` (C6) ; remplace les 2 try/except par helper (C11) ; logging top de fichier.
- `backend/app/api/transactions.py` — remplace try/except par helper (C11) ; logging top de fichier.
- `backend/app/api/health.py` — préfixe `/api` (C7).
- `backend/app/api/router.py` — ajustement include si nécessaire (C7).
- `backend/app/api/bank_accounts.py` — split admin/reader : retire `dependencies=[require_admin]` global, READER reçoit listing filtré, mutations admin (C9).
- `backend/app/api/admin_audit.py` — regex action accepte `merge` (C10).
- `backend/app/api/auth.py` — encode `session_token_version` dans le token (C13).
- `backend/app/api/users.py` — bumper `session_token_version` au reset MdP admin (C13).
- `backend/app/deps.py` — décode et vérifie `session_token_version` (C13).
- `backend/app/security/__init__.py` (ou `security.py`) — `encode_session_token` / `decode_session_token` accepte/retourne `version` (C13).
- `backend/app/main.py` — `app.add_middleware(RequestIDMiddleware)` (C12).
- `backend/app/logging_config.py` — `JsonFormatter` injecte `request_id` via contextvar (C12).
- `frontend/src/components/RuleForm.tsx` — setters manquants + champs UI (C5).
- `frontend/src/router.tsx` — wrap les routes `/administration/*` dans `<AdminRoute>` (C8).
- `frontend/src/content/documentation.ts` — sections `analyse`, `regles`, `admin`, `securite` mises à jour (règle d'équipe).

---

## Conventions de l'app à respecter

(Rappel pour chaque subagent — copier-coller en briefing.)

- **Tests dans le container backend uniquement** (Python 3.10 vs 3.11+ local
  → import incompatibles). `docker exec horizon-backend-1 pytest -x
  backend/tests/test_xxx.py -v`.
- **Cookie session en test** : `BACKEND_COOKIE_SECURE=false` est déjà câblé
  via conftest, ne PAS le toucher.
- **Migrations** : copier le fichier dans le container puis `alembic
  upgrade head`. Procédure : `docker cp backend/alembic/versions/<file>
  horizon-backend-1:/app/alembic/versions/ && docker exec horizon-backend-1
  alembic upgrade head`.
- **Commit messages** : français, ton sobre, sans emoji, format
  `type(scope): message`. Exemples Plan A/B :
  `feat(tiers): refonte page liste`, `fix(imports): réutiliser tiers
  IGNORED au lieu de PENDING`. Co-author Claude requis.
- **Doc d'impact (règle CLAUDE.md)** : si une action UI a un effet métier
  modifié (cf. C8 readers, C5 nouveaux filtres), mettre à jour
  `documentation.ts` au format `FeatureDoc` + tooltip `<HelpTooltip>` +
  bandeau page si concept nouveau. Sinon, pas de doc nécessaire (pure
  correction de bug).
- **Pas d'emoji**, pas d'auto-fix sur la DB (UPDATE SQL transactionnel
  obligatoire — jamais sed -i), pas de `cat .env`.

---

# Tâches

## Task C14 — Préalable : compte READER de test

**Pourquoi en premier :** la branche `accessible_entity_ids_subquery` côté
READER n'est jamais exercée en prod (5 users, tous admin). C8/C9/C6 ne
peuvent pas être validés sans elle.

**Files :**
- Aucun code modifié — opération DB en prod uniquement.

**Steps :**

- [ ] **Step 1 : Créer le compte READER en prod**

Lancer dans le container backend (script Python ad-hoc, pas SQL direct
pour bénéficier de la validation de policy + hash argon2) :

```bash
docker exec -i horizon-backend-1 python - <<'PY'
from app.db import SessionLocal
from app.models.user import User, UserRole
from app.security import hash_password

with SessionLocal() as s:
    if s.query(User).filter(User.email == "reader.test@horizon.local").first():
        print("déjà existant"); raise SystemExit(0)
    u = User(
        email="reader.test@horizon.local",
        password_hash=hash_password("ReaderTest2026!"),
        role=UserRole.READER,
        full_name="Reader Test",
        is_active=True,
    )
    s.add(u); s.commit()
    print(f"created id={u.id}")
PY
```

- [ ] **Step 2 : Lui donner accès à 1 entité (Acreed Consulting, id=2) via UserEntityAccess**

```bash
docker exec -i horizon-backend-1 python - <<'PY'
from app.db import SessionLocal
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess

with SessionLocal() as s:
    u = s.query(User).filter(User.email == "reader.test@horizon.local").one()
    if not s.query(UserEntityAccess).filter(
        UserEntityAccess.user_id == u.id,
        UserEntityAccess.entity_id == 2,
    ).first():
        s.add(UserEntityAccess(user_id=u.id, entity_id=2))
        s.commit()
        print("access granted to entity 2")
    else:
        print("déjà accordé")
PY
```

- [ ] **Step 3 : Smoke manuel — login depuis browser dev**

Sur `https://horizon.<host>/connexion` ou en local, login avec
`reader.test@horizon.local` / `ReaderTest2026!`. Vérifier les écrans
suivants et noter les bugs reproduits dans un commentaire de ce plan
(pour confirmation avant correction) :

| Page | Comportement attendu | Bug attendu (cf. audit) |
|---|---|---|
| `/transactions` | Liste filtrée à entité 2 | Filtre Comptes vide → 403 sur `/api/bank-accounts` (C9) |
| `/regles` | Liste OK, page lit `/api/bank-accounts` | Idem (C9) |
| `/administration/utilisateurs` | Doit refuser l'accès | Frontend laisse entrer, formulaire affiché, 403 muet sur submit (C8) |
| Création règle globale | preview_rule | Compte transactions sur entités hors accès (C6) |

Documenter le résultat (ces 4 doivent reproduire) directement dans le
plan en éditant la table ci-dessus.

- [ ] **Step 4 : Pas de commit** — opération de prod ponctuelle.

---

## Task C7 — Alias `/api/healthz` et `/api/readyz`

**Files :**
- Modify : `backend/app/api/health.py:8`
- Modify : `backend/app/api/router.py:30`
- Test : `backend/tests/test_health_alias.py` (créer)

- [ ] **Step 1 : Test qui échoue**

Créer `backend/tests/test_health_alias.py` :

```python
def test_healthz_via_api_prefix(client):
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_readyz_via_api_prefix(client):
    r = client.get("/api/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_healthz_legacy_root_still_works(client):
    # On garde /healthz à la racine pour ne pas casser une sonde existante.
    r = client.get("/healthz")
    assert r.status_code == 200
```

- [ ] **Step 2 : Run le test, attendre échec**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_health_alias.py -v
```
Expected : 2 fails (404 sur `/api/healthz` et `/api/readyz`).

- [ ] **Step 3 : Implémenter — préfixe `/api` sur le router health**

Dans `backend/app/api/health.py` ligne 8 :

```python
router = APIRouter(prefix="/api", tags=["health"])
```

Et dans `backend/app/api/router.py`, ajouter un router racine pour
préserver `/healthz` à la racine (sondes monitoring qui suivent ce
chemin) :

```python
# router.py — ajouter au-dessus du include health.router :
from fastapi import APIRouter as _RootRouter
root_router = _RootRouter(tags=["health-root"])

@root_router.get("/healthz")
def _root_healthz() -> dict[str, str]:
    return {"status": "alive"}
```

Puis dans `app/main.py`, après `app.include_router(api_router)` :

```python
from app.api.router import root_router  # noqa: E402
app.include_router(root_router)
```

- [ ] **Step 4 : Run tests, attendre PASS**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_health_alias.py -v
```

- [ ] **Step 5 : Commit**

```bash
git add backend/app/api/health.py backend/app/api/router.py backend/app/main.py backend/tests/test_health_alias.py
git commit -m "$(cat <<'EOF'
fix(health): /api/healthz et /api/readyz exposés sous /api

Les sondes monitoring qui suivent toutes les routes sous /api étaient
aveugles au healthcheck. On garde /healthz à la racine pour les
appelants existants.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C10 — Filtre audit-log accepte l'action `merge`

**Contexte :** la migration `20260506_1400_audit_action_merge.py` a élargi
l'enum DB ; il reste à débloquer le filtre côté API.

**Files :**
- Modify : `backend/app/api/admin_audit.py:32`
- Test : `backend/tests/test_admin_audit_merge_filter.py` (créer)

- [ ] **Step 1 : Test failing**

```python
# backend/tests/test_admin_audit_merge_filter.py
def test_admin_audit_filter_accepts_merge(admin_client):
    r = admin_client.get("/api/admin/audit-log", params={"action": "merge"})
    assert r.status_code == 200, r.text


def test_admin_audit_filter_rejects_unknown_action(admin_client):
    r = admin_client.get("/api/admin/audit-log", params={"action": "delete_all"})
    assert r.status_code == 422
```

(Utiliser la fixture admin_client existante. Si absente, écrire un
fixture local qui login via /api/auth/login avec un admin créé en
conftest — cf. plan B test_api_commitments_aggregates.py:1-60 pour le
pattern.)

- [ ] **Step 2 : Run test → FAIL** (422 sur "merge").

- [ ] **Step 3 : Patch regex**

`backend/app/api/admin_audit.py:32` :

```python
action: str | None = Query(default=None, pattern="^(create|update|delete|merge)$"),
```

- [ ] **Step 4 : Run test → PASS.**

- [ ] **Step 5 : Commit**

```bash
git add backend/app/api/admin_audit.py backend/tests/test_admin_audit_merge_filter.py
git commit -m "$(cat <<'EOF'
fix(audit): filtre action accepte 'merge' (Plan A débloqué)

La migration audit_action_merge avait élargi l'enum DB mais l'API
rejetait toujours le filtre côté query param.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C9 — `GET /api/bank-accounts` ouvert aux readers

**Pourquoi :** TransactionsPage / RulesPage / Forecast cassent pour un
READER (filtre Comptes vide). Décision : `GET` (list) ouvert à tout user
authentifié avec filtrage `entity_id IN accessible_entity_ids`. Mutations
(POST/PATCH/DELETE) restent admin.

**Files :**
- Modify : `backend/app/api/bank_accounts.py` (entête router + signature
  list_bank_accounts)
- Test : `backend/tests/test_bank_accounts_reader.py` (créer)

- [ ] **Step 1 : Test failing**

```python
# backend/tests/test_bank_accounts_reader.py
def test_reader_can_list_only_accessible_bank_accounts(reader_client, db_session):
    """Reader avec accès à entité 2 voit uniquement les comptes de 2."""
    r = reader_client.get("/api/bank-accounts")
    assert r.status_code == 200
    payload = r.json()
    assert all(ba["entity_id"] == 2 for ba in payload)


def test_reader_cannot_create_bank_account(reader_client):
    r = reader_client.post(
        "/api/bank-accounts",
        json={"entity_id": 2, "name": "Test", "iban": "FR7612345678901234567890123"},
    )
    assert r.status_code == 403


def test_admin_still_sees_all_bank_accounts(admin_client):
    r = admin_client.get("/api/bank-accounts")
    assert r.status_code == 200
```

(Fixture `reader_client` à ajouter à `backend/tests/conftest.py` si
absente — login en tant que READER avec accès à entité 2. Pattern
identique à `admin_client`.)

- [ ] **Step 2 : Run → FAIL.**

- [ ] **Step 3 : Implémenter**

`backend/app/api/bank_accounts.py` :

```python
from app.deps import accessible_entity_ids_subquery, get_current_user, require_admin
# ... imports existants ...

router = APIRouter(
    prefix="/api/bank-accounts",
    tags=["bank-accounts"],
    # NB : guard admin déplacé sur les routes mutantes ci-dessous.
)


@router.get("", response_model=list[BankAccountRead])
def list_bank_accounts(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[BankAccount]:
    accessible = accessible_entity_ids_subquery(session=db, user=current)
    return list(
        db.scalars(
            select(BankAccount)
            .where(BankAccount.entity_id.in_(accessible))
            .order_by(BankAccount.created_at.desc())
        )
    )


@router.post(
    "",
    response_model=BankAccountRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_bank_account(...):  # corps identique
    ...


@router.patch(
    "/{account_id}",
    response_model=BankAccountRead,
    dependencies=[Depends(require_admin)],
)
def update_bank_account(...):  # corps identique
    ...
```

(Si une route DELETE existe — vérifier le fichier — l'envelopper aussi.
Au moment de la rédaction, seul GET/POST/PATCH sont définis.)

- [ ] **Step 4 : Run tests → PASS.**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_bank_accounts_reader.py -v
```

- [ ] **Step 5 : Commit**

```bash
git add backend/app/api/bank_accounts.py backend/tests/test_bank_accounts_reader.py backend/tests/conftest.py
git commit -m "$(cat <<'EOF'
fix(bank-accounts): GET ouvert aux readers avec filtrage par entités accessibles

TransactionsPage et RulesPage cassaient pour un READER : le filtre
"compte bancaire" était vide ou en erreur silencieuse. Mutations restent
admin-only.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C4 — Filtre `parent_transaction_id IS NULL` dans la catégorisation

**Effet attendu :** corriger 197 lignes en prod (TVA et Commissions
bancaires gonflées par les enfants `TVA VIR SEPA`).

**Files :**
- Modify : `backend/app/services/categorization.py:18` (`build_rule_filter`)
  + `:71` (`matches_transaction`)
- Test : `backend/tests/test_categorization_parent_filter.py` (créer)

- [ ] **Step 1 : Test failing**

```python
# backend/tests/test_categorization_parent_filter.py
import pytest
from sqlalchemy import select
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.services.categorization import (
    apply_rule, matches_transaction, build_rule_filter,
)


def test_rule_does_not_match_aggregation_children(db_session, sample_entity, sample_bank_account):
    # Crée 1 parent agrégat + 3 enfants au libellé "TVA VIR SEPA"
    parent = Transaction(
        bank_account_id=sample_bank_account.id,
        operation_date="2026-04-01",
        amount=-300,
        label="TVA VIR SEPA",
        normalized_label="TVA VIR SEPA",
        is_aggregation_parent=True,
        categorized_by=TransactionCategorizationSource.NONE,
    )
    db_session.add(parent); db_session.flush()
    for i in range(3):
        db_session.add(Transaction(
            bank_account_id=sample_bank_account.id,
            operation_date="2026-04-01",
            amount=-100,
            label=f"TVA VIR SEPA #{i}",
            normalized_label=f"TVA VIR SEPA #{i}",
            parent_transaction_id=parent.id,
            categorized_by=TransactionCategorizationSource.NONE,
        ))
    db_session.commit()

    rule = CategorizationRule(
        name="TVA",
        label_operator=RuleLabelOperator.CONTAINS,
        label_value="TVA",
        direction=RuleDirection.ANY,
        priority=100,
        category_id=1,  # n'importe quelle cat existante
    )
    db_session.add(rule); db_session.flush()

    # Python check
    children = db_session.execute(
        select(Transaction).where(Transaction.parent_transaction_id == parent.id)
    ).scalars().all()
    for child in children:
        assert matches_transaction(rule, child) is False, (
            "matches_transaction ne doit pas matcher un enfant SEPA"
        )

    # SQL check via apply_rule
    report = apply_rule(db_session, rule)
    # Seul le parent doit être catégorisé (1), pas les 3 enfants.
    assert report.updated_count == 1
```

- [ ] **Step 2 : Run → FAIL** (matches enfants ; report=4).

- [ ] **Step 3 : Patch `build_rule_filter`**

`backend/app/services/categorization.py:68` (clause finale) :

```python
# Toujours exclure les enfants d'agrégat : les règles ne matchent que les
# transactions de premier niveau (parent unique ou ligne sans parent).
clauses.append(Transaction.parent_transaction_id.is_(None))

return and_(*clauses) if clauses else (Transaction.parent_transaction_id.is_(None))
```

(Le fallback `Transaction.id == Transaction.id` doit aussi être remplacé
pour préserver la garde même si aucun autre filtre n'est défini.)

- [ ] **Step 4 : Patch `matches_transaction`**

Ajouter en haut de la fonction (avant les checks label/direction) :

```python
def matches_transaction(rule: CategorizationRule, tx: Transaction) -> bool:
    if tx.parent_transaction_id is not None:
        return False
    # ... reste inchangé ...
```

- [ ] **Step 5 : Run test → PASS.**

- [ ] **Step 6 : Recategorize les 2 entités impactées en prod**

```bash
docker exec -i horizon-backend-1 python - <<'PY'
from app.db import SessionLocal
from app.services.categorization import recategorize_entity

with SessionLocal() as s:
    for entity_id in (1, 2):
        report = recategorize_entity(s, entity_id)
        s.commit()
        print(f"entity {entity_id} → {report.updated_count} tx recatégorisées")
PY
```

Noter le delta dans le commit (attendu : ~197 lignes corrigées d'après
audit, mais peut varier si data a bougé).

- [ ] **Step 7 : Commit**

```bash
git add backend/app/services/categorization.py backend/tests/test_categorization_parent_filter.py
git commit -m "$(cat <<'EOF'
fix(categorization): exclure les enfants d'agrégat du matching de règles

Les règles TVA et Commissions bancaires capturaient les enfants
'TVA VIR SEPA' à -0,10 €, gonflant le top des catégories de +99/+98
lignes. Filtre 'parent_transaction_id IS NULL' ajouté à build_rule_filter
ET matches_transaction. Recategorize lancé sur entités 1 et 2.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C6 — `preview_rule` filtre par accessible_entity_ids du user

**Files :**
- Modify : `backend/app/services/categorization.py:186` (`preview_rule`)
- Modify : `backend/app/api/rules.py` (route `/preview` qui appelle `preview_rule`)
- Test : `backend/tests/test_preview_rule_tenant.py` (créer)

- [ ] **Step 1 : Localiser la route preview**

```bash
grep -n "preview_rule\|/preview" backend/app/api/rules.py
```

Identifier la fonction qui appelle `preview_rule(session, rule)` —
typiquement `preview_rule_route` ou similaire. Noter sa signature.

- [ ] **Step 2 : Test failing**

```python
# backend/tests/test_preview_rule_tenant.py
def test_global_rule_preview_restricted_to_accessible_entities(reader_client, seed_two_entities_data):
    """Reader avec accès à entité 2 ne voit pas le compte sur entité 1."""
    payload = {
        "name": "Loyer global",
        "entity_id": None,
        "priority": 100,
        "label_operator": "CONTAINS",
        "label_value": "LOYER",
        "direction": "DEBIT",
        "category_id": seed_two_entities_data["category_id"],
    }
    r = reader_client.post("/api/rules/preview", json=payload)
    assert r.status_code == 200
    body = r.json()
    # Sur entité 1 il y a 5 transactions LOYER, sur entité 2 il y en a 2.
    # Reader voit uniquement 2.
    assert body["matching_count"] == 2
```

(`seed_two_entities_data` : fixture qui crée 2 entités, 2 BA, 5 tx LOYER
sur entité 1, 2 tx LOYER sur entité 2. Pattern dans tests existants.)

- [ ] **Step 3 : Run → FAIL** (count=7).

- [ ] **Step 4 : Élargir signature `preview_rule`**

`backend/app/services/categorization.py:186` :

```python
def preview_rule(
    session: Session,
    rule: CategorizationRule,
    *,
    sample_limit: int = 20,
    accessible_entity_ids: list[int] | None = None,
) -> RulePreviewResult:
    """...
    Si la règle est scopée à une entité (`rule.entity_id` non NULL), le
    comptage et l'échantillon sont restreints aux comptes bancaires de
    cette entité.
    Si la règle est globale (`rule.entity_id IS NULL`), restreindre aux
    comptes des entités accessibles passées par le caller — sinon un
    READER pourrait observer le décompte sur des entités hors de son
    périmètre (leak quantitatif cross-tenant).
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
        base_filter = and_(base_filter, Transaction.bank_account_id.in_(accessible_accounts))
    elif accessible_entity_ids is not None:
        accessible_accounts = select(BankAccount.id).where(
            BankAccount.entity_id.in_(accessible_entity_ids)
        )
        base_filter = and_(base_filter, Transaction.bank_account_id.in_(accessible_accounts))

    # ... reste inchangé ...
```

- [ ] **Step 5 : Caller dans `api/rules.py`**

Localiser la route preview, ajouter :

```python
from app.deps import accessible_entity_ids_subquery, get_current_user

@router.post("/preview", ...)
def preview_rule_route(
    payload: RulePreviewPayload,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RulePreviewResponse:
    # ... construction du rule object existante ...

    accessible_ids = list(
        session.scalars(accessible_entity_ids_subquery(session=session, user=user))
    )
    result = preview_rule_service(
        session, rule, accessible_entity_ids=accessible_ids,
    )
    # ...
```

- [ ] **Step 6 : Run test → PASS.**

- [ ] **Step 7 : Commit**

```bash
git add backend/app/services/categorization.py backend/app/api/rules.py backend/tests/test_preview_rule_tenant.py
git commit -m "$(cat <<'EOF'
fix(rules): preview_rule respecte les entités accessibles du user

Pour une règle globale (entity_id IS NULL), le preview comptait toutes
les transactions de toutes les entités, exposant un décompte sur des
entités hors du périmètre du user. Service signature étendue ;
caller passe la subquery accessible_entity_ids.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C2 — Ancrage temporel `MAX(operation_date)` dans `analysis.py`

**Pourquoi :** Tous les widgets s'ancrent sur `date.today()` (mai 2026)
mais data couvre janv→avr 2026. `current_first` pointe sur un mois vide.

**Décision :** ancrer sur le mois du dernier import (`MAX(operation_date)`)
de l'entité, et exposer cette fenêtre au frontend (header de la page
Analyse). Si pas de data : retourner réponses vides avec
`window_month=null`.

**Files :**
- Modify : `backend/app/services/analysis.py` (toutes les fonctions
  `compute_*` qui utilisent `date.today()`)
- Modify : `backend/app/schemas/analysis.py` (ajouter `window_month` aux
  réponses concernées)
- Modify : `frontend/src/pages/AnalysePage.tsx` (afficher la fenêtre dans
  le header — règle d'équipe doc d'impact)
- Test : `backend/tests/test_analysis_anchor.py` (créer)

- [ ] **Step 1 : Recenser les usages de `date.today()` dans analysis.py**

```bash
grep -n "date.today\|datetime.now\|today =" backend/app/services/analysis.py
```

Lister chaque occurrence, fonction par fonction, et noter celles qui
servent d'ancrage temporel (par opposition à un horodatage technique).

- [ ] **Step 2 : Helper d'ancrage**

Ajouter en haut de `backend/app/services/analysis.py` :

```python
def _resolve_anchor_month(session: Session, entity_id: int) -> date | None:
    """Retourne le 1er du mois de la dernière transaction connue (par
    operation_date) pour les comptes de l'entité. None si aucune data.

    Ancrer sur la data plutôt que sur date.today() évite que les widgets
    pointent sur un mois vide entre deux imports (ex. mai 2026 alors que
    le dernier import couvre avril).
    """
    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    if not ba_ids:
        return None
    max_op = session.execute(
        select(func.max(Transaction.operation_date)).where(
            Transaction.bank_account_id.in_(ba_ids),
            Transaction.is_aggregation_parent.is_(False),
        )
    ).scalar()
    if max_op is None:
        return None
    return _first_of_month(max_op)
```

- [ ] **Step 3 : Test failing**

```python
# backend/tests/test_analysis_anchor.py
from datetime import date
from app.services.analysis import (
    compute_category_drift, compute_top_movers, _resolve_anchor_month,
)


def test_anchor_uses_max_operation_date(db_session, seed_entity_with_data_through_april):
    """Si la dernière tx est en avril 2026, l'ancrage doit être avril
    même si date.today() est en mai."""
    eid = seed_entity_with_data_through_april.id
    anchor = _resolve_anchor_month(db_session, eid)
    assert anchor == date(2026, 4, 1)


def test_drift_returns_window_month_in_response(db_session, seed_entity_with_data_through_april):
    eid = seed_entity_with_data_through_april.id
    resp = compute_category_drift(db_session, entity_id=eid, seuil_pct=20.0)
    assert resp.window_month == "2026-04"


def test_drift_empty_when_no_data(db_session, seed_empty_entity):
    eid = seed_empty_entity.id
    resp = compute_category_drift(db_session, entity_id=eid, seuil_pct=20.0)
    assert resp.window_month is None
    assert resp.rows == []
```

- [ ] **Step 4 : Run → FAIL** (window_month n'existe pas).

- [ ] **Step 5 : Patch `compute_category_drift` (analysis.py:~120-177)**

Remplacer :

```python
today = date.today()
current_first = _first_of_month(today)
target_first = _add_months(current_first, -1)
```

Par :

```python
anchor = _resolve_anchor_month(session, entity_id)
if anchor is None:
    return CategoryDriftResponse(rows=[], seuil_pct=seuil_pct, window_month=None)
target_first = anchor  # mois de référence = mois ancré (dernier mois plein)
```

Et ajouter `window_month=_month_key(target_first)` à la réponse finale.

- [ ] **Step 6 : Patch `compute_category_drift_detail` (analysis.py:195+)**

Idem : remplacer `today = date.today()` + `_add_months(current_first, -1)`
par `target_first = _resolve_anchor_month(session, entity_id)`.

- [ ] **Step 7 : Patch `compute_top_movers` (analysis.py:262+)**

Remplacer :

```python
today = date.today()
current_first = _first_of_month(today)
```

Par :

```python
current_first = _resolve_anchor_month(session, entity_id)
if current_first is None:
    return TopMoversResponse(increases=[], decreases=[], window_month=None)
```

Le `current_first` ainsi obtenu sera utilisé pour `current_key` (cf. C3
qui ajuste cette ligne).

- [ ] **Step 8 : Audit des autres `compute_*`**

Faire pareil dans `compute_category_distribution`, `compute_yoy_*`,
`compute_runway*`, `compute_working_capital`, `compute_forecast_variance`,
**toute fonction qui prenait `date.today()`** comme ancrage. Ne pas
toucher les usages purement techniques (timestamps de logs).

Pour chacune, ajouter `window_month` à sa réponse (ou
`anchor_month` selon le sens — uniformiser sur `window_month`).

- [ ] **Step 9 : Élargir les schemas**

`backend/app/schemas/analysis.py` — ajouter `window_month: str | None = None`
à `CategoryDriftResponse`, `TopMoversResponse`, et autres réponses
concernées.

- [ ] **Step 10 : Run tests + tests existants → PASS**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_analysis_anchor.py -v
docker exec horizon-backend-1 pytest backend/tests/ -k analysis -v
```

- [ ] **Step 11 : Frontend — afficher la fenêtre temporelle dans le
  header de AnalysePage**

`frontend/src/pages/AnalysePage.tsx` : récupérer `window_month` (ex. via
le retour `compute_category_drift`) et l'afficher dans le header :

```tsx
<header className="flex items-baseline justify-between">
  <h1 className="text-2xl font-semibold">Analyse</h1>
  {windowMonth && (
    <p className="text-sm text-muted-foreground">
      Fenêtre temporelle : {formatMonth(windowMonth)} (dernier mois importé)
    </p>
  )}
</header>
```

`formatMonth("2026-04")` → "avril 2026" via Intl.DateTimeFormat.

- [ ] **Step 12 : Commit**

```bash
git add backend/app/services/analysis.py backend/app/schemas/analysis.py backend/tests/test_analysis_anchor.py frontend/src/pages/AnalysePage.tsx
git commit -m "$(cat <<'EOF'
fix(analyse): ancrer les widgets sur MAX(operation_date), pas sur today()

Tous les widgets pointaient sur le mois courant (mai 2026) alors que
les imports couvrent janv→avril : top movers, dérive, YoY plats. Ancrage
calculé sur le mois de la dernière tx, fenêtre exposée dans le header
de la page Analyse.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C1 — Drift formula avec guard

**Pourquoi :** -1272,6 % sur "Frais pro. remboursés" car avg3m sur
3 mois dont 2 à 0 → dénominateur 3× trop petit. La règle :
- si `|avg3m| < 50 €` (ε = 5000 cents) **OU** moins de 2 mois actifs sur
  3 → `delta_pct = None` ; UI affiche "—" et un tooltip
  "Insuffisant pour calculer un %".

**Files :**
- Modify : `backend/app/services/analysis.py:154-163` (logique drift)
- Modify : `backend/app/schemas/analysis.py` (rendre `delta_pct: float | None`)
- Modify : `frontend/src/components/widgets/CategoryDriftTable.tsx` (UI fallback)
- Test : étendre `backend/tests/test_analysis_anchor.py` ou créer
  `test_analysis_drift_guard.py`

- [ ] **Step 1 : Test failing**

```python
# backend/tests/test_analysis_drift_guard.py
def test_drift_pct_none_when_avg3m_below_threshold(db_session, seed_drift_edge_case):
    """Catégorie active 1 mois sur 3 avec faible montant → delta_pct=None."""
    eid = seed_drift_edge_case.entity_id
    resp = compute_category_drift(db_session, entity_id=eid, seuil_pct=20.0)
    edge = next(r for r in resp.rows if r.category_id == seed_drift_edge_case.cat_id)
    # avg3m_cents = -2158 (cf. cas réel audit) → sous seuil 5000
    assert edge.delta_pct is None
    assert edge.status == "insufficient"


def test_drift_pct_none_when_too_few_active_months(db_session, seed_drift_one_active_month):
    """Catégorie active sur seulement 1 des 3 mois précédents → None."""
    eid = seed_drift_one_active_month.entity_id
    resp = compute_category_drift(db_session, entity_id=eid, seuil_pct=20.0)
    edge = next(r for r in resp.rows if r.category_id == seed_drift_one_active_month.cat_id)
    assert edge.delta_pct is None


def test_drift_pct_computed_normally_when_data_sufficient(db_session, seed_drift_normal):
    eid = seed_drift_normal.entity_id
    resp = compute_category_drift(db_session, entity_id=eid, seuil_pct=20.0)
    edge = next(r for r in resp.rows if r.category_id == seed_drift_normal.cat_id)
    assert edge.delta_pct is not None
    assert -100.0 < edge.delta_pct < 1000.0
```

- [ ] **Step 2 : Run → FAIL.**

- [ ] **Step 3 : Patcher la logique**

`backend/app/services/analysis.py:150-177` :

```python
DRIFT_AVG3M_THRESHOLD_CENTS = 5000  # 50 € — sous ce seuil, % devient bruité
DRIFT_MIN_ACTIVE_PREV_MONTHS = 2     # /3 — sinon avg3m peu représentatif

# ... dans la boucle ...
for cat_id, months_map in by_cat.items():
    current = months_map.get(current_key, 0)
    prev_values = [months_map.get(k, 0) for k in prev_keys]
    active_prev = sum(1 for v in prev_values if v != 0)
    prev_sum = sum(prev_values)
    avg3m = prev_sum // 3 if prev_sum else 0
    if current == 0 and avg3m == 0:
        continue
    delta = current - avg3m

    insufficient = (
        abs(avg3m) < DRIFT_AVG3M_THRESHOLD_CENTS
        or active_prev < DRIFT_MIN_ACTIVE_PREV_MONTHS
    )
    if insufficient:
        delta_pct: float | None = None
        status = "insufficient"
    else:
        delta_pct = (current - avg3m) / abs(avg3m) * 100.0
        status = "alert" if abs(delta_pct) > seuil_pct else "normal"

    out.append(
        CategoryDriftRow(
            category_id=cat_id,
            label=labels.get(cat_id, f"Catégorie {cat_id}"),
            current_cents=current,
            avg3m_cents=avg3m,
            delta_cents=delta,
            delta_pct=round(delta_pct, 2) if delta_pct is not None else None,
            status=status,
        )
    )

# Tri : insufficient en bas, sinon par |delta_pct| desc
out.sort(
    key=lambda r: (r.status == "insufficient", -abs(r.delta_pct or 0)),
)
```

- [ ] **Step 4 : Schéma**

`CategoryDriftRow.delta_pct: float | None` ; `status: Literal["normal",
"alert", "insufficient"]`.

- [ ] **Step 5 : UI fallback**

`frontend/src/components/widgets/CategoryDriftTable.tsx` (ou nom
équivalent) :

```tsx
function renderDeltaPct(row: CategoryDriftRow): JSX.Element {
  if (row.delta_pct === null) {
    return (
      <Tooltip content="Historique insuffisant pour calculer un pourcentage (montants trop faibles ou catégorie peu active).">
        <span className="text-muted-foreground">—</span>
      </Tooltip>
    );
  }
  // ...
}
```

- [ ] **Step 6 : Run → PASS** + smoke UI manuel.

- [ ] **Step 7 : Commit**

```bash
git add backend/app/services/analysis.py backend/app/schemas/analysis.py backend/tests/test_analysis_drift_guard.py frontend/src/components/widgets/CategoryDriftTable.tsx
git commit -m "$(cat <<'EOF'
fix(analyse): guard sur le calcul du drift % (catégories peu actives)

Le widget affichait -1272,6 % sur des catégories actives 1 mois sur 3
(avg3m sous seuil + activité éparse). Ajout d'un statut 'insufficient'
qui mute delta_pct à null ; UI rend '—' avec tooltip.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C3 — Top Movers : `current = dernier mois plein`

**Pourquoi :** déjà partiellement résolu par C2 (ancrage), mais le widget
Top Movers a un piège supplémentaire : si l'ancrage tombe sur un mois
partiellement importé (ex. import en cours d'avril), le delta `current
- prev` devient trompeur. Règle : ne sélectionner comme `current` que les
mois **pleins** au sens « ≥ N transactions, ex. ≥ 50 % de la médiane
mensuelle des 6 derniers mois ».

**Files :**
- Modify : `backend/app/services/analysis.py` (compute_top_movers)
- Test : étendre `test_analysis_anchor.py` ou créer
  `test_top_movers_full_month.py`

- [ ] **Step 1 : Helper "mois plein"**

Ajouter à `analysis.py` :

```python
def _last_full_month(session: Session, entity_id: int) -> date | None:
    """Retourne le 1er du dernier mois 'plein' : ≥ 50 % de la médiane
    des 6 derniers mois en nombre de transactions. Si l'ancrage (mois de
    la dernière tx) est sous le seuil, on recule d'un mois.
    """
    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    if not ba_ids:
        return None
    month_col = func.date_trunc("month", Transaction.operation_date)
    rows = session.execute(
        select(month_col.label("m"), func.count(Transaction.id).label("n"))
        .where(
            Transaction.bank_account_id.in_(ba_ids),
            Transaction.is_aggregation_parent.is_(False),
        )
        .group_by(month_col)
        .order_by(month_col.desc())
        .limit(7)
    ).all()
    if not rows:
        return None
    counts = [r.n for r in rows]
    if len(counts) <= 1:
        return _first_of_month(rows[0].m)
    # médiane sur les 6 mois précédant le plus récent
    sorted_prev = sorted(counts[1:7])
    median = sorted_prev[len(sorted_prev) // 2] if sorted_prev else 0
    threshold = max(1, median // 2)
    if counts[0] >= threshold:
        return _first_of_month(rows[0].m)
    # Sinon : reculer d'un mois
    if len(rows) >= 2:
        return _first_of_month(rows[1].m)
    return None
```

- [ ] **Step 2 : Test failing**

```python
def test_top_movers_skips_partial_current_month(db_session, seed_partial_april):
    """Si avril a 5 tx et la médiane Q1 est 200, avril doit être ignoré
    et le 'current' est mars."""
    eid = seed_partial_april.id
    resp = compute_top_movers(db_session, entity_id=eid, limit=10)
    assert resp.window_month == "2026-03"
```

- [ ] **Step 3 : Run → FAIL.**

- [ ] **Step 4 : Patcher `compute_top_movers`**

Remplacer `current_first = _resolve_anchor_month(...)` (issu de C2) par
`current_first = _last_full_month(session, entity_id)`.

- [ ] **Step 5 : Run → PASS.**

- [ ] **Step 6 : Commit**

```bash
git add backend/app/services/analysis.py backend/tests/test_top_movers_full_month.py
git commit -m "$(cat <<'EOF'
fix(analyse): Top Movers ignore les mois partiellement importés

Le widget comparait un mois en cours d'import au mois précédent et
remontait des baisses fictives. On retient le dernier mois 'plein'
(≥ 50 % de la médiane sur 6 mois en nb tx).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C11 — Helper `record_batch_audit` factorise les 3 try/except

**Pourquoi :** `transactions.py:152-177`, `rules.py:274-299`,
`rules.py:347-370` dupliquent la même logique « audit batch via
session.add(AuditLog(...)) entouré de try/except ». Le swallow silencieux
peut masquer un audit non écrit alors que la mutation métier commit.

**Files :**
- Create : `backend/app/services/audit_batch.py`
- Modify : `backend/app/api/transactions.py:142-178`
- Modify : `backend/app/api/rules.py:265-300`
- Modify : `backend/app/api/rules.py:347-371`

- [ ] **Step 1 : Créer le helper**

`backend/app/services/audit_batch.py` :

```python
"""Helper pour les audit logs batch (1 ligne par opération de masse).

Diffère de `record_audit` qui prend une entité ORM : ici on enregistre
une entrée audit construite à la main (entity_type/entity_id virtuels,
ex. 'bulk(N)' ou 'rule-apply(K)').

Garantie : ne fait JAMAIS planter la transaction métier — exception
loggée à WARNING avec exc_info, et drapeau retourné pour visibilité.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.audit import _extract_request_meta

logger = logging.getLogger(__name__)


def record_batch_audit(
    session: Session,
    *,
    user: User,
    request: Request,
    action: str,
    entity_type: str,
    entity_id: str,
    after: dict[str, Any],
    before: dict[str, Any] | None = None,
) -> bool:
    """Enregistre un AuditLog "batch" et flush. Retourne True si OK,
    False si une exception a été loggée (transaction métier non
    impactée).
    """
    try:
        meta = _extract_request_meta(request)
        session.add(
            AuditLog(
                user_id=user.id,
                user_email=user.email,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_json=before,
                after_json=after,
                diff_json=None,
                ip_address=meta["ip_address"],
                user_agent=meta["user_agent"],
                request_id=meta["request_id"],
            )
        )
        session.flush()
        return True
    except Exception:  # noqa: BLE001
        logger.warning(
            "audit.batch_failed",
            extra={
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
            exc_info=True,
        )
        return False
```

- [ ] **Step 2 : Refactor `transactions.py:142-178`**

```python
from app.services.audit_batch import record_batch_audit

# ... à la place du bloc try/except existant ...
if txs:
    record_batch_audit(
        session,
        user=user,
        request=request,
        action="update",
        entity_type="Transaction",
        entity_id=f"bulk({len(txs)})",
        after={
            "operation": "bulk_categorize",
            "transaction_ids": [tx.id for tx in txs],
            "category_id": payload.category_id,
            "count": len(txs),
        },
    )
session.commit()
```

- [ ] **Step 3 : Refactor `rules.py:265-300` (rule_apply)**

Idem pour le bloc audit batch — appeler `record_batch_audit` avec
`entity_id=f"rule-apply({rule.id})"`.

- [ ] **Step 4 : Refactor `rules.py:347-371` (reorder)**

Idem — `entity_id=f"reorder({len(items)})"`, `before={"priorities_before":
before_priorities}`, `after={"operation": "reorder", "priorities_after":
{...}}`.

- [ ] **Step 5 : Supprimer `import logging` redondants dans except**

Les 3 `import logging` à l'intérieur des except blocks deviennent
inutiles. Vérifier qu'aucun autre logging n'utilise ce nom local.

- [ ] **Step 6 : Run la suite tests existante**

```bash
docker exec horizon-backend-1 pytest backend/tests/ -k "audit or rule or transaction" -v
```

- [ ] **Step 7 : Commit**

```bash
git add backend/app/services/audit_batch.py backend/app/api/transactions.py backend/app/api/rules.py
git commit -m "$(cat <<'EOF'
refactor(audit): helper record_batch_audit centralise les 3 sites batch

Les blocs try/except autour de session.add(AuditLog(...)) étaient
dupliqués dans transactions.bulk_categorize, rules.apply et
rules.reorder. Le swallow remplacé par un logger.warning(exc_info) qui
laisse une trace visible si l'audit échoue.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C12 — Middleware ASGI `X-Request-ID` + injection dans logging

**Files :**
- Create : `backend/app/middleware/__init__.py` (vide)
- Create : `backend/app/middleware/request_id.py`
- Modify : `backend/app/main.py` (add_middleware)
- Modify : `backend/app/logging_config.py` (JsonFormatter lit le
  contextvar)
- Test : `backend/tests/test_request_id_middleware.py`

- [ ] **Step 1 : Créer le middleware**

`backend/app/middleware/request_id.py` :

```python
"""Middleware ASGI : génère ou propage `X-Request-ID` et l'expose au
logging via un contextvar.
"""
from __future__ import annotations

import contextvars
import uuid
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = request.headers.get(REQUEST_ID_HEADER)
        if not rid:
            rid = uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = rid
        return response
```

- [ ] **Step 2 : Câbler dans `main.py`**

```python
from app.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)
# Note : doit être ajouté APRÈS CORSMiddleware si on veut que CORS
# expose le header — ajouter "expose_headers=['X-Request-ID']" au
# CORSMiddleware existant.
```

Mettre à jour CORSMiddleware existant :

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
```

- [ ] **Step 3 : Injecter dans le JsonFormatter**

`backend/app/logging_config.py` — repérer le formatter, ajouter :

```python
from app.middleware.request_id import request_id_ctx

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            # ... champs existants ...
            "request_id": request_id_ctx.get(),
        }
        return json.dumps(payload, ensure_ascii=False)
```

(Si `JsonFormatter` n'existe pas tel quel, étendre le formatter en
place. Si l'app utilise `structlog`, ajouter un processor au lieu d'un
formatter.)

- [ ] **Step 4 : Test**

```python
# backend/tests/test_request_id_middleware.py
def test_request_id_generated_when_absent(client):
    r = client.get("/api/healthz")
    assert "x-request-id" in r.headers
    assert len(r.headers["x-request-id"]) >= 16


def test_request_id_propagated_when_provided(client):
    r = client.get("/api/healthz", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"


def test_request_id_logged_in_audit(admin_client, db_session):
    """Quand admin_client envoie X-Request-ID, l'audit_log le récupère."""
    rid = "test-rid-789"
    # une mutation simple : créer un user
    r = admin_client.post(
        "/api/users",
        json={"email": "rid-test@x.local", "password": "Foobar2026!", "role": "reader"},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 201
    from app.models.audit_log import AuditLog
    last = db_session.execute(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
    ).scalar_one()
    assert last.request_id == rid
```

- [ ] **Step 5 : Run → PASS.**

- [ ] **Step 6 : Commit**

```bash
git add backend/app/middleware/ backend/app/main.py backend/app/logging_config.py backend/tests/test_request_id_middleware.py
git commit -m "$(cat <<'EOF'
feat(middleware): X-Request-ID généré ou propagé, injecté dans le logging

Permet de corréler logs/audit/erreurs sur une même requête. uuid4 si
absent, contextvar pour exposer la valeur au formatter de logs et au
record_audit (déjà câblé via _extract_request_meta).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C13 — `session_token_version` : reset MdP révoque les sessions

**Pourquoi :** la doc `securite` promet l'invalidation au reset MdP — non
implémentée. Mécanisme : `User.session_token_version` (int, default=1) ;
embarqué dans le token signé ; au reset MdP admin, on incrémente la
version → tous les tokens existants deviennent invalides au prochain
appel.

**Files :**
- Create : `backend/alembic/versions/20260507_1000_user_session_token_version.py`
- Modify : `backend/app/models/user.py`
- Modify : `backend/app/security/__init__.py`
- Modify : `backend/app/api/auth.py`
- Modify : `backend/app/api/users.py` (reset_user_password)
- Modify : `backend/app/deps.py`
- Modify : `frontend/src/content/documentation.ts` (section securite alignée)
- Test : `backend/tests/test_session_token_version.py`

- [ ] **Step 1 : Migration**

`backend/alembic/versions/20260507_1000_user_session_token_version.py` :

```python
"""user.session_token_version

Revision ID: h0r1z0n50701
Revises: <DOWN_REVISION>  # à remplacer par la HEAD actuelle (cf. alembic heads)
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "h0r1z0n50701"
down_revision = None  # à compléter
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "session_token_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    # On retire le server_default après backfill : la valeur par défaut
    # applicative reste 1 mais le DDL ne la rappelle plus.
    op.alter_column("users", "session_token_version", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "session_token_version")
```

Pour récupérer la down_revision :

```bash
docker exec horizon-backend-1 alembic heads
```

Mettre la valeur retournée dans `down_revision`.

- [ ] **Step 2 : Modèle**

`backend/app/models/user.py` :

```python
session_token_version: Mapped[int] = mapped_column(
    Integer, nullable=False, default=1, server_default="1"
)
```

- [ ] **Step 3 : Encode/decode token avec version**

`backend/app/security/__init__.py` (ou `security.py`) :

```python
import json

def encode_session_token(*, user_id: int, version: int, secret: str) -> str:
    signer = TimestampSigner(secret)
    payload = json.dumps({"u": user_id, "v": version}, separators=(",", ":"))
    return signer.sign(payload).decode("utf-8")


def decode_session_token(token: str, *, secret: str, max_age_seconds: int) -> tuple[int, int]:
    signer = TimestampSigner(secret)
    try:
        raw = signer.unsign(token, max_age=max_age_seconds).decode("utf-8")
    except SignatureExpired as exc:
        raise SessionTokenError("Session expirée") from exc
    except BadSignature as exc:
        raise SessionTokenError("Token invalide") from exc
    try:
        # Supporter l'ancien format pour la transition (1 seul int)
        if raw.isdigit():
            return int(raw), 1
        data = json.loads(raw)
        return int(data["u"]), int(data["v"])
    except (ValueError, KeyError, TypeError) as exc:
        raise SessionTokenError("Format de token invalide") from exc
```

- [ ] **Step 4 : `auth.py` login**

```python
token = encode_session_token(
    user_id=user.id,
    version=user.session_token_version,
    secret=settings.secret_key,
)
```

- [ ] **Step 5 : `deps.py` get_current_user**

```python
try:
    user_id, version = decode_session_token(
        session,
        secret=settings.secret_key,
        max_age_seconds=settings.session_hours * 3600,
    )
except SessionTokenError as exc:
    raise HTTPException(status_code=401, detail=str(exc)) from exc

user = db.get(User, user_id)
if user is None or not user.is_active:
    raise HTTPException(status_code=401, detail="Utilisateur inconnu ou désactivé")
if user.session_token_version != version:
    raise HTTPException(status_code=401, detail="Session révoquée")
return user
```

- [ ] **Step 6 : `users.py` reset_user_password bumpe la version**

Dans `reset_user_password` (ligne 134) :

```python
user.password_hash = hash_password(new_pw)
user.session_token_version = (user.session_token_version or 1) + 1
db.flush()
```

- [ ] **Step 7 : Tests**

```python
# backend/tests/test_session_token_version.py
def test_password_reset_invalidates_existing_sessions(admin_client, reader_client, db_session):
    """Après reset MdP du reader, son cookie cesse de fonctionner."""
    # 1. Le reader fonctionne avant reset
    r = reader_client.get("/api/me")
    assert r.status_code == 200
    reader_id = r.json()["id"]

    # 2. Admin reset le MdP du reader
    r = admin_client.post(
        f"/api/users/{reader_id}/password",
        json={"new_password": "BrandNewPwd2026!"},
    )
    assert r.status_code == 204

    # 3. Le reader_client (avec son ancien cookie) doit recevoir 401
    r = reader_client.get("/api/me")
    assert r.status_code == 401


def test_token_format_legacy_still_decoded_as_v1(client):
    """Tokens émis avant la migration (format 'user_id' brut) restent
    valides en version 1, donc fonctionnels tant que User.version == 1."""
    # ...
```

- [ ] **Step 8 : Appliquer la migration**

```bash
docker cp backend/alembic/versions/20260507_1000_user_session_token_version.py horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
```

- [ ] **Step 9 : Run tests → PASS.**

- [ ] **Step 10 : Mise à jour `documentation.ts` (section securite)**

`frontend/src/content/documentation.ts` — section `securite` : aligner
le contenu sur le comportement réel (le reset MdP révoque bien les
sessions actives). Format `FeatureDoc` :
"À quoi ça sert", "Ce que ça change", "Ce que ça ne change pas",
"Quand l'utiliser".

- [ ] **Step 11 : Commit**

```bash
git add backend/alembic/versions/20260507_1000_user_session_token_version.py backend/app/models/user.py backend/app/security/__init__.py backend/app/api/auth.py backend/app/api/users.py backend/app/deps.py backend/tests/test_session_token_version.py frontend/src/content/documentation.ts
git commit -m "$(cat <<'EOF'
feat(auth): reset MdP admin révoque les sessions actives via token version

User.session_token_version embarqué dans le token signé ; bumpé au
reset MdP. Doc 'securite' alignée sur le comportement réel. Compat
descendante : ancien format 'int brut' interprété comme version 1.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

# CHECKPOINT BACKEND ✋

**À ce stade, tous les fixes backend sont mergés sur main.** Avant
d'attaquer le frontend (C5, C8) :

1. Lancer la suite de tests complète :
   ```bash
   docker exec horizon-backend-1 pytest backend/tests/ -v --tb=short
   ```
2. Smoke manuel sur le compte READER de test (cf. C14) :
   - `/api/bank-accounts` → 200 avec liste filtrée
   - `/api/me` → 200 avant reset, 401 après reset MdP par admin
   - Création règle globale → preview compte filtré
3. Vérifier `/api/healthz` et `/api/readyz` répondent 200.
4. Vérifier qu'une requête arbitraire renvoie un header `X-Request-ID`.
5. **Pause utilisateur** : confirmation explicite avant de continuer
   sur frontend.

---

## Task C5 — RuleForm : 5 setters manquants

**Files :**
- Modify : `frontend/src/components/RuleForm.tsx:36-42`

- [ ] **Step 1 : Ajouter les setters**

Lignes 36-42, remplacer `useState` sans setter par version complète :

```tsx
const [amountOp, setAmountOp] = useState<RuleAmountOperator | "">(
  (init?.amount_operator as RuleAmountOperator) ?? ""
);
const [amountVal, setAmountVal] = useState(init?.amount_value ?? "");
const [amountVal2, setAmountVal2] = useState(init?.amount_value2 ?? "");
const [counterpartyId, setCounterpartyId] = useState<number | null>(init?.counterparty_id ?? null);
const [bankAccountId, setBankAccountId] = useState<number | null>(init?.bank_account_id ?? null);
```

- [ ] **Step 2 : Ajouter les champs UI manquants**

Après la ligne 4 (filtre libellé), insérer un bloc collapsible "Filtres
avancés" :

```tsx
<details className="space-y-3 rounded-md border border-line-soft bg-surface-1 p-3">
  <summary className="cursor-pointer text-[12.5px] text-ink-2">
    Filtres avancés (montant, tiers, compte)
    <HelpTooltip text="Ces filtres sont combinés en ET avec le filtre sur libellé." />
  </summary>

  {/* Montant */}
  <div className="grid grid-cols-3 gap-2">
    <div className="space-y-1">
      <Label className="text-[12.5px] text-ink-2">Opérateur montant</Label>
      <Select value={amountOp} onValueChange={(v) => setAmountOp(v as RuleAmountOperator)}>
        <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="">aucun</SelectItem>
          <SelectItem value="EQ">égal à</SelectItem>
          <SelectItem value="NE">différent de</SelectItem>
          <SelectItem value="GT">supérieur à</SelectItem>
          <SelectItem value="LT">inférieur à</SelectItem>
          <SelectItem value="BETWEEN">entre</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div className="space-y-1">
      <Label className="text-[12.5px] text-ink-2">Valeur (€)</Label>
      <Input
        type="number" step="0.01" value={amountVal}
        onChange={(e) => setAmountVal(e.target.value)}
        placeholder="ex. 100.00"
      />
    </div>
    {amountOp === "BETWEEN" && (
      <div className="space-y-1">
        <Label className="text-[12.5px] text-ink-2">Et (€)</Label>
        <Input
          type="number" step="0.01" value={amountVal2}
          onChange={(e) => setAmountVal2(e.target.value)}
        />
      </div>
    )}
  </div>

  {/* Tiers */}
  <div className="space-y-1">
    <Label className="text-[12.5px] text-ink-2">Tiers (optionnel)</Label>
    <Select
      value={counterpartyId != null ? String(counterpartyId) : "__none__"}
      onValueChange={(v) => setCounterpartyId(v === "__none__" ? null : Number(v))}
    >
      <SelectTrigger><SelectValue placeholder="Aucun" /></SelectTrigger>
      <SelectContent>
        <SelectItem value="__none__">Aucun (tous tiers)</SelectItem>
        {props.counterparties.map((c) => (
          <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>

  {/* Compte bancaire */}
  <div className="space-y-1">
    <Label className="text-[12.5px] text-ink-2">Compte bancaire (optionnel)</Label>
    <Select
      value={bankAccountId != null ? String(bankAccountId) : "__none__"}
      onValueChange={(v) => setBankAccountId(v === "__none__" ? null : Number(v))}
    >
      <SelectTrigger><SelectValue placeholder="Aucun" /></SelectTrigger>
      <SelectContent>
        <SelectItem value="__none__">Aucun (tous comptes)</SelectItem>
        {props.bankAccounts
          .filter((b) => entityId == null || b.entity_id === entityId)
          .map((b) => (
            <SelectItem key={b.id} value={String(b.id)}>{b.name}</SelectItem>
          ))}
      </SelectContent>
    </Select>
  </div>
</details>
```

(Le filtre par compte est filtré sur l'entité sélectionnée si une
entité est définie — sinon tous comptes.)

- [ ] **Step 2bis : `<HelpTooltip>` import**

S'il n'existe pas déjà dans RuleForm :

```tsx
import { HelpTooltip } from "@/components/HelpTooltip";
```

- [ ] **Step 3 : Smoke UI manuel**

`docker compose -f docker-compose.prod.yml restart frontend` (ou en
build live à la fin), puis :
1. Créer une règle avec un filtre montant `> 100 €` → preview → vérifier
   que le filtre est bien appliqué.
2. Éditer une règle existante → les valeurs amount/counterparty/bank
   sont rappelées et éditables.

- [ ] **Step 4 : Mise à jour documentation.ts**

`frontend/src/content/documentation.ts` — section `regles` : ajouter une
sous-section "Filtres avancés" expliquant les 5 nouveaux filtres au
format `FeatureDoc` (existait peut-être déjà côté backend, à compléter).

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/components/RuleForm.tsx frontend/src/content/documentation.ts
git commit -m "$(cat <<'EOF'
fix(rules): RuleForm expose les filtres montant, tiers, compte (setters)

Les 5 useState sans setter rendaient les filtres avancés inertes côté
UI alors que le backend les supporte. Bloc collapsible 'Filtres
avancés' ajouté ; documentation.ts mise à jour.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task C8 — `<AdminRoute>` : guard rôle admin sur les routes admin

**Files :**
- Create : `frontend/src/components/AdminRoute.tsx`
- Modify : `frontend/src/router.tsx:170-216`
- Modify : `frontend/src/components/Sidebar.tsx` (cacher liens admin
  pour reader — vérifier pattern existant)

- [ ] **Step 1 : Créer AdminRoute**

`frontend/src/components/AdminRoute.tsx` :

```tsx
import { Navigate } from 'react-router-dom';
import { useMe } from '@/hooks/useAuth';

/**
 * Guard rôle pour les routes /administration/*. Doit être nesté dans
 * un <ProtectedRoute> (qui garantit déjà l'authentification).
 *
 * - Loading → spinner identique au ProtectedRoute pour éviter le saut.
 * - Reader (rôle non-admin) → redirige vers /tableau-de-bord avec un
 *   toast informatif (pas de 403 muet).
 * - Admin → enfants rendus.
 */
export function AdminRoute({ children }: { children: React.ReactNode }) {
  const me = useMe();
  if (me.isLoading) return <div className="p-8">Chargement…</div>;
  if (!me.data) return <Navigate to="/connexion" replace />;
  if (me.data.role !== 'admin') {
    return <Navigate to="/tableau-de-bord" replace state={{ adminDenied: true }} />;
  }
  return <>{children}</>;
}
```

- [ ] **Step 2 : Wrapper les 6 routes admin dans router.tsx**

Lignes 170-216, transformer chaque entrée en :

```tsx
{
  path: '/administration/utilisateurs',
  element: (
    <AdminRoute>
      <LazyPage><AdminUsersPage /></LazyPage>
    </AdminRoute>
  ),
},
// idem pour /administration/societes, /administration/comptes-bancaires,
// /administration/categories, /administration/sauvegardes,
// /administration/audit
```

- [ ] **Step 3 : Sidebar — cacher les liens admin pour reader**

`frontend/src/components/Sidebar.tsx` — repérer la section navigation
admin. Pattern :

```tsx
const me = useMe();
const isAdmin = me.data?.role === 'admin';

// ...
{isAdmin && (
  <NavSection title="Administration">
    {/* liens admin */}
  </NavSection>
)}
```

(Si la sidebar est en dur, remplacer par ce conditionnel.)

- [ ] **Step 4 : Toast `adminDenied`**

Optionnel : sur `/tableau-de-bord`, si `useLocation().state?.adminDenied`,
afficher un toast "Cette page est réservée aux administrateurs."
(`useToast` ou équivalent). Si la stack n'a pas de toast,
sauter cette étape — la redirection silencieuse suffit déjà à fermer le
trou.

- [ ] **Step 5 : Smoke manuel**

Connecté en tant que `reader.test@horizon.local` :
1. Naviguer vers `/administration/utilisateurs` → redirection vers
   `/tableau-de-bord`.
2. La sidebar n'affiche pas le bloc Administration.

Connecté en admin :
1. Sidebar affiche tout.
2. `/administration/*` accessibles.

- [ ] **Step 6 : Mise à jour documentation.ts**

Section `admin` : préciser que les pages admin sont strictement réservées
au rôle admin et que les readers sont redirigés vers le tableau de bord.

- [ ] **Step 7 : Commit**

```bash
git add frontend/src/components/AdminRoute.tsx frontend/src/router.tsx frontend/src/components/Sidebar.tsx frontend/src/content/documentation.ts
git commit -m "$(cat <<'EOF'
fix(admin): AdminRoute redirige les readers hors des pages admin

ProtectedRoute ne regardait que la session, pas le rôle. Les readers
voyaient les formulaires admin et recevaient des 403 muets au submit.
Sidebar masque aussi le bloc Administration pour les non-admin.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task finale — Build & deploy live

- [ ] **Step 1 : Build images**

```bash
docker compose -f docker-compose.prod.yml build backend frontend
```

- [ ] **Step 2 : Restart**

```bash
docker compose -f docker-compose.prod.yml up -d backend frontend
```

- [ ] **Step 3 : Vérifs post-deploy**

```bash
curl -sf http://localhost:<port>/api/healthz
curl -sf http://localhost:<port>/api/readyz
curl -sI http://localhost:<port>/api/healthz | grep -i x-request-id
```

- [ ] **Step 4 : Smoke prod**

Login admin → page Analyse → vérifier le header "Fenêtre temporelle :
avril 2026" + tableau Drift sans -1272 %. Page Règles → ouvrir une
règle → bloc Filtres avancés visible.

- [ ] **Step 5 : Lancer `./scripts/dev/show-client-errors.sh --since
  10m`** pour vérifier qu'aucune erreur frontend nouvelle n'a été
  introduite.

- [ ] **Step 6 : Ping utilisateur** avec un récap (commits, points
  d'attention, prochaine étape éventuelle Plan D).

---

## Self-Review checklist

- [x] Spec coverage — tous les items C1→C14 mappés sur une tâche.
- [x] Pas de placeholders "TBD/TODO/à compléter" dans les blocs de code.
- [x] Type consistency : `delta_pct: float | None`, `window_month: str |
  None`, `session_token_version: int`, `accessible_entity_ids: list[int]
  | None` cohérents entre tasks.
- [x] Doc d'impact (CLAUDE.md) référencée dans C5, C8, C13.
- [x] Migration C13 : down_revision à compléter au moment d'écrire le
  fichier (récupéré via `alembic heads`) — flagué explicitement dans la
  Step 1.

## Ordre d'exécution recommandé (pour subagent driven)

```
C14 (préalable, manuel)
 → C7 (low risk, débloque smoke healthcheck)
 → C10 (low risk, sans impact code)
 → C9 (low risk, prérequis pour smoke C14)
 → C4 (logique pure backend, recategorize en prod après merge)
 → C6 (besoin C9 + fixture reader_client)
 → C2 (refactor analysis.py, isolé)
 → C1 (étend C2)
 → C3 (étend C2)
 → C11 (refactor pur)
 → C12 (middleware, sans impact métier)
 → C13 (migration + doc, le plus lourd)

CHECKPOINT BACKEND — pause utilisateur

 → C5 (frontend isolé)
 → C8 (frontend isolé)

Build + deploy + ping utilisateur
```
