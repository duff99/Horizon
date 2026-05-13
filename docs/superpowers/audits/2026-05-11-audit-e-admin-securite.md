# Audit Admin & Sécurité — Horizon — 2026-05-11

**Périmètre** : Auth, AdminRoute, /api/admin/*, /api/entities, cross-tenant, audit log, rate limiter, cookies, session token version.

**Méthode** : lecture exhaustive du code + exécution des pytest ciblés sur test-pg.

---

## Synthèse

| Sévérité | Bugs | Dont sécu-critique |
|---|---|---|
| CRITIQUE | 2 | 2 |
| HAUTE | 2 | 1 |
| MOYENNE | 3 | 0 |
| FAIBLE / INFO | 4 | 0 |

**Pas de fuite cross-tenant détectée sur les endpoints de données.** Le filtre `accessible_entity_ids_subquery` est correctement appliqué sur tous les endpoints sensibles (transactions, imports, counterparties, rules, commitments, forecast, dashboard, treasury, analysis, anomalies, drift_acks). Le correctif bd60b8e (preview_rule) tient toujours.

---

## Bugs par sévérité

### CRITIQUE — Sécurité

#### BUG-SEC-01 : `POST /api/me/password` ne bumpe pas `session_token_version` [OWASP A07 — Identification and Authentication Failures]

**Fichier** : `backend/app/api/me.py` — fonction `change_password`

**Description** : Quand un utilisateur change son propre mot de passe via `POST /api/me/password`, le champ `session_token_version` n'est pas incrémenté. Or, le design de sécurité de l'app (commit 80bdf94) impose que tout changement de mot de passe invalide immédiatement les sessions actives en bumping ce champ. Un attaquant ayant volé un cookie de session actif (XSS, réseau, compromission poste) peut donc continuer à utiliser ce cookie même après que la victime ait changé son mot de passe, sans être révoqué.

**Comportement attendu** : identique au reset admin (`/api/users/{id}/password`) — bumper `user.session_token_version` puis committer.

**Scénario d'attaque** : cookie volé → victime change son mot de passe (croit mettre fin aux sessions actives) → attaquant continue à accéder à l'app avec l'ancien cookie.

**Contraste** : `POST /api/users/{id}/password` (reset admin) bumpe correctement (ligne 138 de users.py). La parité est manquante dans me.py.

**Fix** : ajouter `current.session_token_version = (current.session_token_version or 1) + 1` avant le `db.commit()` dans `change_password`.

---

#### BUG-SEC-02 : `GET /api/entities` accessible uniquement aux admins, mais les pages frontend non-admin (`EntitySelector`, `TransactionsPage`, `AnalysePage`, `ForecastV2Page`, `RulesPage`, `CommitmentFormDialog`) l'appellent pour tous les rôles [OWASP A01 — Broken Access Control]

**Fichier** : `backend/app/api/entities.py` (router-level `require_admin`) + `frontend/src/api/entities.ts` + `frontend/src/components/EntitySelector.tsx`

**Description** : Le routeur `/api/entities` est protégé par `dependencies=[Depends(require_admin)]` au niveau router, ce qui signifie que **tous** les endpoints de ce routeur (GET, POST, PATCH, DELETE) exigent le rôle admin. Or, `EntitySelector` (composant partagé utilisé sur le Layout/Sidebar et sur de nombreuses pages) appelle `GET /api/entities` pour peupler la liste déroulante de sélection de société — pour **tous** les utilisateurs connectés, y compris les readers. Résultat : les readers reçoivent une erreur 403 lors du chargement de l'`EntitySelector`, ce qui casse le sélecteur d'entité et potentiellement toutes les pages qui en dépendent (`TransactionsPage`, `AnalysePage`, `ForecastV2Page`, `RulesPage`, `CommitmentFormDialog`).

**Impact opérationnel** : l'app est fonctionnellement cassée pour les readers si l'`EntitySelector` est monté (toutes les pages de données).

**Distinction avec une vraie fuite cross-tenant** : le backend protège correctement les *données* par `accessible_entity_ids_subquery`. Le problème est que les readers ne peuvent même pas obtenir la liste des entités auxquelles ils ont accès pour peupler leur propre sélecteur.

**Fix attendu** : créer un endpoint dédié `GET /api/me/entities` (ou modifier `GET /api/entities` pour retourner les entités accessibles filtrées selon le rôle courant) accessible à tout utilisateur authentifié. Pour les readers, ne retourner que les entités présentes dans `user_entity_access`. Pour les admins, retourner toutes les entités (comportement actuel).

---

### HAUTE

#### BUG-HIGH-01 : Absence d'endpoint CRUD pour `UserEntityAccess` (grant/revoke) [OWASP A01 — Broken Access Control — missing feature]

**Fichier** : aucun endpoint existant dans `backend/app/api/` pour gérer la table `user_entity_access`

**Description** : La page `AdminUsersPage.tsx` permet de créer/modifier/désactiver des utilisateurs, mais il n'existe aucun endpoint API pour accorder ou révoquer l'accès d'un reader à une entité donnée (`UserEntityAccess`). La gestion des droits d'entité ne peut se faire que par intervention directe en base de données. Cela signifie que l'admin ne peut pas, via l'interface, attribuer les accès que le backend s'attend à trouver pour les readers. La sécurité multitenante des readers est donc incomplète du point de vue opérationnel : les readers auront accès à 0 entité tant qu'un admin n'intervient pas en DB.

**Sévérité** : HAUTE (manque fonctionnel bloquant pour le multitenancy reader, pas une fuite).

---

#### BUG-HIGH-02 : `PATCH /api/admin/client-errors/{id}/acknowledge` sans audit et sans injection du user courant [OWASP A09 — Security Logging and Monitoring Failures]

**Fichier** : `backend/app/api/admin_client_errors.py` — fonction `acknowledge_client_error`

**Description** : L'endpoint `PATCH /{error_id}/acknowledge` ne prend pas le `current: User` en dépendance (seul `db` est injecté) et n'appelle pas `record_audit`. Toute action d'acquittement est donc invisible dans le journal d'audit : il est impossible de savoir quel admin a acquitté quelle erreur client, ni quand. Pour des raisons de traçabilité dans une app financière, c'est un manquement notable. De plus, l'utilisation de `datetime.utcnow()` (deprecated) génère des warnings en production.

---

### MOYENNE

#### BUG-MED-01 : `AuditAction` frontend limité à `create|update|delete` — les actions `login`, `login_failed`, `logout`, `merge` non filtrables dans l'UI

**Fichier** : `frontend/src/types/auditLog.ts` (ligne 7) + `frontend/src/pages/AdminAuditLogPage.tsx` (ligne 42)

**Description** : Le type TypeScript `AuditAction` et le tableau `ACTIONS` dans la page AdminAuditLogPage ne contiennent que `['create', 'update', 'delete']`. Le backend accepte pourtant `login`, `login_failed`, `logout` et `merge` comme valeurs du filtre `action`. L'admin ne peut donc pas filtrer le journal d'audit par ces actions depuis l'interface ; il doit faire appel à l'API directement. Le journal les affiche bien en réception (le backend les renvoie), mais le filtre UI ne les propose pas.

---

#### BUG-MED-02 : Rate limiter sur `/api/auth/login` basé sur IP uniquement — bypassable derrière un proxy partagé (CGNAT / VPN)

**Fichier** : `backend/app/rate_limiter.py` (key_func = `get_remote_address`) + `backend/app/api/auth.py` (décorateur `@limiter.limit("10/minute")`)

**Description** : Le rate limiter utilise `get_remote_address` comme clé de comptage. Derrière un proxy partagé (ou si `X-Forwarded-For` est spoofé — `_extract_request_meta` dans `audit.py` fait confiance au premier XFF sans validation), plusieurs utilisateurs derrière la même IP partagent le même compteur. Inversement, un attaquant avec accès à des IPs multiples (VPN rotatif) peut contourner le lockout de 5 tentatives car il changera d'IP avant d'atteindre la limite de 10/minute. Le lockout par compte (5 tentatives → 15 min) est une bonne mitigation, mais la limite par IP seule n'est pas suffisante.

**Niveau de risque** : moyen (atténué par le lockout par compte).

---

#### BUG-MED-03 : Cookie `SameSite=lax` — exposition aux CSRF sur navigateurs anciens

**Fichier** : `backend/app/api/auth.py` ligne 82 (`samesite="lax"`)

**Description** : Le cookie de session est configuré `SameSite=lax`, `HttpOnly=True`, `Secure=True` (en prod). `SameSite=lax` protège contre les CSRF initiés par liens tiers, mais pas contre les requêtes POST cross-origin avec user-agent ancien. Pour une app financière, `SameSite=strict` serait plus robuste. En pratique, avec l'app en auto-hébergement, le risque est faible, mais ce n'est pas le réglage le plus sûr possible.

**Note** : CORS est configuré avec `allow_origins` strict et `allow_credentials=True`, ce qui limite déjà le vecteur. C'est donc surtout un point de durcissement.

---

### FAIBLE / INFO

#### BUG-LOW-01 : `datetime.utcnow()` déprécié dans `admin_client_errors.py`

**Fichier** : `backend/app/api/admin_client_errors.py` ligne 116

**Description** : `dt_datetime.utcnow()` est déprécié depuis Python 3.12. Utiliser `datetime.now(UTC)` pour cohérence avec le reste de la codebase.

---

#### BUG-LOW-02 : Pas de 2FA (G5 Plan H) — item déféré connu

**Statut** : confirmé non implémenté, consigné dans les items déférés Plan H. Hors périmètre de cet audit.

---

#### BUG-LOW-03 : Pas de forgot-password / reset par email (Plan H G6) — item déféré connu

**Statut** : confirmé non implémenté. Hors périmètre de cet audit.

---

#### BUG-LOW-04 : `accessible_entity_ids_subquery` supprime le paramètre `session` sans utilisation (`del session`) — dette technique

**Fichier** : `backend/app/deps.py` ligne 100

**Description** : Commentaire dans le code reconnaît l'inutilité de ce paramètre pour l'instant mais le conserve pour "extensibilité future". Pas de risque sécurité, mais dette technique mineure.

---

## Tableau actions × scénarios

| Endpoint | Légitime (admin) | Non autorisé (reader → 403) | Cross-tenant |
|---|---|---|---|
| `POST /api/auth/login` | OK — audit + cookie | N/A | N/A |
| `POST /api/auth/logout` | OK — audit | OK (sans cookie = silencieux) | N/A |
| `GET /api/auth/me` (via /api/me) | OK | 401 si pas de cookie | N/A |
| `POST /api/me/password` | OK (fonctionne) mais **session_token_version non bumpé** | 401 si pas de cookie | N/A |
| `GET /api/users` | OK (200) | **403** (testé) | N/A |
| `POST /api/users` | OK (201) | **403** (testé) | N/A |
| `PATCH /api/users/{id}` | OK (200) | **403** | N/A |
| `POST /api/users/{id}/password` | OK (204 + bump session_token_version) | **403** (testé) | N/A |
| `DELETE /api/users/{id}` | OK (204, ou 409 si dernier admin) | **403** (testé) | N/A |
| `GET /api/entities` | OK (200) | **403** (testé) — **mais casse l'EntitySelector pour les readers** | N/A |
| `GET /api/admin/audit-log` | OK | **403** | N/A |
| `GET /api/admin/audit-log/export` | OK | **403** | N/A |
| `GET /api/admin/client-errors` | OK | **403** | N/A |
| `PATCH /api/admin/client-errors/{id}/acknowledge` | OK (fonctionnel) mais **sans audit, sans user courant** | **403** (router-level) | N/A |
| `GET /api/transactions` | OK — filtre `accessible_entity_ids` | 401 si pas de cookie | **OK (filtre appliqué, testé)** |
| `GET /api/transactions?entity_id=X` | OK si accès | **403 si entity inconnue** | **OK — require_entity_access** |
| `POST /api/transactions/bulk-categorize` | OK | **403 reader** | **OK — filtre accessible_accounts** |
| `GET /api/rules` | OK | OK (reader peut lire) | **OK — filtre scope** |
| `POST /api/rules/preview` | OK | OK (reader peut prévisualiser) | **OK — require_entity_access si entity_id** |
| `GET /api/counterparties` | OK | OK (reader peut lire) | **OK — accessible subquery** |
| `GET /api/imports` | OK | OK (reader peut lire) | **OK — accessible subquery** |
| `POST /api/imports` | OK | OK si accès entity | **OK — require_entity_access** |
| `GET /api/dashboard/summary` | OK | OK (reader) | **OK — accessible_entity_ids** |
| `GET /api/analysis/*` | OK | OK (reader) | **OK — require_entity_access sur tous** |
| `GET /api/analysis/anomalies` | OK | OK (reader) | **OK — require_entity_access** |
| `GET /api/analysis/drift-acks/` | OK | OK (reader) | **OK — require_entity_access** |
| `GET /api/healthz` | OK — no auth | N/A | N/A |
| `GET /api/readyz` | OK — no auth, retourne 503 si DB down | N/A | N/A |
| `GET /` (root) | OK — no auth | N/A | N/A |
| `GET /healthz` (legacy alias) | OK — no auth | N/A | N/A |
| `POST /api/client-errors` | OK (anonyme ou avec session) | N/A | N/A |
| `AdminRoute` frontend | Redirige vers /tableau-de-bord si non-admin | OK | N/A |
| `/admin/users` forcé en browser non-admin | **Redirigé vers /tableau-de-bord par AdminRoute** | OK | N/A |

---

## Couverture des tests existants

| Test | Résultat |
|---|---|
| `test_session_token_version.py` | 4 passed |
| `test_user_lockout_f4.py` | 5 passed |
| `test_audit_auth_f3.py` | 3 passed |
| `test_api_users_f2.py` | 10 passed |
| `test_preview_rule_tenant.py` | 2 passed |
| `api/test_admin_audit.py` | 7 passed |
| `test_admin_audit_merge_filter.py` | 2 passed |
| `test_e5_client_errors_admin.py` | 5 passed |
| `api/test_client_errors.py` | 10 passed |
| `api/test_transactions_entity_filter.py` | 3 passed |
| `api/test_imports_entity_filter.py` | 3 passed |
| `api/test_categories_entity_filter.py` | 1 passed |
| `api/test_counterparties_entity_filter.py` | 2 passed |
| `test_api_rules_permissions.py` | 3 passed |
| `test_bank_accounts_reader.py` | 3 passed |
| `test_api_entities_f2.py` | 7 passed |
| `test_api_auth_f2.py` | 4 passed |
| `test_security.py` | 11 passed |
| `test_request_id_middleware.py` | 3 passed |
| `test_health_basic.py` | 1 passed |
| `test_health_alias.py` | 3 passed |
| **TOTAL** | **91 passed, 0 failed** |

### Tests non couverts (trous de couverture)

- Pas de test pour `POST /api/me/password` vérifiant que `session_token_version` est bumpé après un self-service password change.
- Pas de test confirmant que l'`EntitySelector` obtient les entités accessibles pour un reader (BUG-SEC-02).
- Pas de test sur l'acquittement d'erreur client avec vérification de l'auteur (BUG-HIGH-02).
- Pas de test sur le filtre audit `action=login` depuis l'interface (BUG-MED-01).

---

## Points confirmés comme OK (régressions antérieures vérifiées)

- **Cross-tenant preview_rule** (bd60b8e) : `POST /api/rules/preview` filtre bien par `accessible_entity_ids` — 2 tests passent.
- **session_token_version bump sur reset admin** (80bdf94) : `POST /api/users/{id}/password` bumpe correctement — 4 tests passent.
- **Filtre audit-log action=merge** (f1551c5) : pattern regex du backend inclut `merge` — 2 tests passent.
- **X-Request-ID middleware** (9a97761) : injecté dans les logs et header de réponse — 3 tests passent.
- **`/api/healthz` et `/api/readyz`** (5d55c40) : accessibles sans auth, readyz retourne 503 si DB unreachable — 4 tests passent.
- **Lockout 5 tentatives** : fonctionne correctement, message 423 sans révélation du compteur — 5 tests passent.
- **Password hash argon2** : utilisé correctement, champs sensibles masqués `<redacted>` dans l'audit log — vérifié code + 11 tests security passent.
- **Cookie HttpOnly + Secure en prod** : configuré correctement (`cookie_secure=True` en prod via `BACKEND_COOKIE_SECURE`).

---

## Doutes / impossibilités d'investigation

- **Timing attack sur le login** : le backend exécute `verify_password` (argon2, ~80 ms) uniquement si l'utilisateur existe, mais renvoie immédiatement 401 si l'email est inconnu (sans argon2). Cela crée un différentiel de temps mesurable qui permet l'énumération d'emails (malgré le message identique). Non exploitable facilement en pratique (réseau + jitter), mais techniquement présent. Classé comme point d'amélioration plutôt que bug critique.
- **`X-Forwarded-For` trusted sans validation** : `_extract_request_meta` prend le premier XFF sans vérifier que le proxy est de confiance. Si l'app est exposée directement sans proxy, un attaquant peut spoofer son IP dans les logs d'audit et contourner le rate limiter. Non testé en prod (dépend de la configuration réseau).
- **Pas de test de charge** sur le rate limiter slowapi — le comportement sous burst n'a pas été vérifié.
