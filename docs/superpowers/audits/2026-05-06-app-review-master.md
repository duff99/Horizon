# Audit complet Horizon — Master Report (2026-05-06)

> **Pour reprise de session** : ce document capture l'audit produit + technique
> complet de l'app, mené en parallèle par 5 subagents spécialisés. Il contient
> les bugs identifiés (priorisés), les patterns systémiques, les features
> manquantes et une roadmap en 5 plans (C, D, E, F, G).
>
> **À lire en premier la prochaine session.** Voir aussi le prompt de relance
> en bas du doc.

---

## Contexte de l'audit

**Date :** 2026-05-06.
**App :** Horizon, clone Agicap (gestion de trésorerie). Stack : FastAPI +
SQLAlchemy 2.x + Postgres + React 18 + react-query + TypeScript + Tailwind.
Déployée en docker-compose (`docker-compose.prod.yml`).
**Données en prod au moment de l'audit :** 711 transactions, 4 mois (janv→avril
2026), 3 entités (Acronos, Acreed Consulting, Acreed IA Solutions),
5 utilisateurs (tous admin), 10 imports complétés, 48 règles, 65 catégories,
1 commitment pending.
**Refontes récentes :** Plan A — page Tiers (mergé sur main), Plan B — page
Engagements (sur branche `refonte/engagements`, 9 commits, **non mergée**).

**Méthode :** 5 subagents en parallèle, chacun read-only sur un domaine cohérent.
Rapports détaillés dans la transcription de session ; cette synthèse est la
référence opérationnelle pour les fixes à venir.

**Élément déclencheur de l'audit (utilisateur) :** la page Analyse semble vide
malgré 4 mois de data importés ; le widget "Dérive par catégorie" affiche
**-1272,6 %** sur la première ligne. L'audit a confirmé les deux et trouvé
beaucoup d'autres choses.

---

## État des lieux — synthèse exécutive

L'app a un socle solide :
- Architecture multi-tenant claire et centralisée (`accessible_entity_ids_subquery`).
- Parsers PDF Delubac + Crédit Agricole robustes, dedup SHA-256 des transactions
  (0 doublon en prod sur 711 tx / 10 imports).
- Audit log avec scrub des champs sensibles, garde "jamais sans admin actif".
- Pipeline backup propre (trigger via fichier `/data/triggers`, watcher hôte
  privilégié, restore-test auto le dimanche, verify SHA256, 18 backups en base).
- Forecast moteur formules avec resolver récursif et détection de cycle (peu de
  produits à ce niveau).
- Pivot batch-loaded (~4 requêtes au total au lieu de N×M).
- Refontes Tiers + Engagements (Plans A/B) à un niveau de qualité référence.

Mais elle traîne **3 pathologies systémiques** :

**A. Code mort qui pollue l'état réel.**
- `forecast_entries` : table à 0 ligne, lue par 3 endroits, API `/api/forecast/*`
  exposée publiquement, frontend `forecast.ts` orphelin (0 importeurs).
- `is_intercompany`, `counter_entity_id` jamais set ni consommés.
- Page admin `client_errors` n'existe pas alors que l'API est en place.
- 22/48 règles à 0 hit (dont règle 103 inerte car `**` disparaît à la
  normalisation).
- Styling pour `is_aggregation_parent` mort (parent masqué dans la requête).
- `RuleForm` : 5 setters manquants (filtres amount/counterparty/bank inertes
  côté UI alors que backend supporte).

**B. Doc qui promet ce que le code ne fait pas.**
- Section `securite` documente l'invalidation de session au reset MdP — non
  implémentée (cookies actifs jusqu'à expiration `session_hours=8`).
- Doc référence des règles `Frais **` qui ne peuvent jamais matcher.
- Sidebar/router montrent les pages admin aux READERs → 403 muets.
- ⚠️ Memo "Doc à jour après chaque déploiement" tient pour les ajouts mais pas
  pour les promesses non tenues.

**C. Multi-tenant non testé live.**
- 5 users en prod, **tous ADMIN**. La branche READER de
  `accessible_entity_ids_subquery` n'est jamais exercée.
- Si un bug d'isolation tenant existe, il passe inaperçu.
- Le bug P0 `preview_rule` (cf. plus bas) est précisément ce genre de fuite
  invisible.

---

## P0 — Bugs critiques consolidés (13 items)

| # | Bug | Domaine | Fichier:ligne | Cause | Effet |
|---|---|---|---|---|---|
| 1 | Drift -1272,6 % | Pilotage | `backend/app/services/analysis.py:152-162` | `(current - avg3m) / abs(avg3m)` sans guard ; sur catégorie active 1 mois sur 3, dénominateur 3× trop petit | Mur de % faux qui décrédibilise tout le widget |
| 2 | Page Analyse "vide" | Pilotage | `analysis.py` (tous les `compute_*`) | Tous les widgets s'ancrent sur `date.today()` (mai 2026) mais data couvre janv→avr 2026 → mois courant vide | YoY plat, top movers que des baisses, dérives à -100 % |
| 3 | Top Movers compare un mois vide | Pilotage | `analysis.py:325-326` | `current_first` = 1er du mois courant (inexistant) | 0 hausse, "baisses" = flux normaux d'avril faussement présentés |
| 4 | KPI déformés par enfants SEPA | Flux | `backend/app/services/categorization.py:18,71` | `build_rule_filter` ne filtre pas `parent_transaction_id IS NULL` → règle TVA capture 99 enfants `TVA VIR SEPA` à -0,10 €, règle Commissions capture 98 idem | Top catégories Commissions bancaires gonflées de +98, TVA gonflée de +99 — tout l'analytique biaisé |
| 5 | RuleForm 5 filtres morts | Flux | `frontend/src/components/RuleForm.tsx:36-42` | `useState` sans setter sur `amountOp`, `amountVal`, `amountVal2`, `counterpartyId`, `bankAccountId` | UI prétend supporter ces filtres, en pratique impossible de les éditer |
| 6 | preview_rule cross-tenant | Flux (sécurité) | `backend/app/services/categorization.py:186` | Pour règles globales (`entity_id IS NULL`), preview compte sur **toute la base** sans filtrer par entités accessibles | Leak quantitatif : un user voit "X tx matchent" sur des entités auxquelles il n'a pas accès |
| 7 | API forecast legacy orpheline | Forecast | `backend/app/api/forecast.py` (215 LOC) ; `frontend/src/api/forecast.ts` (0 importeurs) | Code mort exposé publiquement. `forecast_entries` à 0 ligne mais lue par `forecast_engine.py:224` | Un user curieux peut écrire dedans → pivot v2 additionne silencieusement aux ForecastLine sans UI pour les voir |
| 8 | TVA collectée mal classée | Forecast | `backend/app/services/forecast_engine.py:645-689` | Direction `in/out` inférée par signe (`SUM(amount) >= 0`) faute de `Category.kind` | TVA collectée -17 952 € → rangée en **Décaissements** au lieu d'Encaissements |
| 9 | `/api/healthz` → 404 | Admin | `backend/app/api/health.py:11`, `backend/app/api/router.py:30` | `health.router` monté sans préfixe `/api` | Toute sonde monitoring qui suit `/api` est aveugle |
| 10 | Routes admin sans guard rôle frontend | Admin | `frontend/src/router.tsx:170-216` | `ProtectedRoute` ne regarde que la session, pas le rôle | READER navigue vers les pages admin, formulaires affichés, 403 muets sur submit |
| 11 | `GET /api/bank-accounts` admin-only | Admin | `backend/app/api/bank_accounts.py:22` | `dependencies=[Depends(require_admin)]` | TransactionsPage / RulesPage / Forecast cassent pour un READER (filtre BA vide ou erreur silencieuse) |
| 12 | Reset MdP ne révoque pas les sessions | Admin (sécurité) | `backend/app/api/users.py:113-140` ; pas de `session_token_version` | Pas de mécanisme de rotation de token | La doc promet l'invalidation → mensonge fonctionnel ; cookie reste valide 8h |
| 13 | Audit `try/except` swallow silencieux | Hygiène (sécurité) | `transactions.py:175-177`, `rules.py:297-299`, `rules.py:368-370` | 3 sites avalent `Exception` autour de `record_audit` puis `session.commit()` poursuit | Audit log peut **ne pas être écrit** sans qu'on le sache, transaction métier commit quand même |

**Bonus P0 sécurité (Hygiène) :** pas de middleware `X-Request-ID` →
investigation prod à l'aveugle (logs/audit/erreurs non corrélables).

---

## P1 — Bugs notables (résumé par domaine)

### Pilotage analytique
- Drift `status="alert"` sur catégories à 1 mois actif (analysis.py:163).
- Working capital DSO/DPO basé sur `Commitment.matched_transaction_id` → muet
  tant qu'aucun matching, sans signal UI explicite.
- Runway prend `closing_balance` du dernier import au lieu de fallback
  `Σ amounts` jusqu'à `MAX(operation_date)` (Acronos balance figée fin mars).
- HHI calculé sur `amount > 0` brut, sans exclusion des "Ajustements" et "Flux
  intergroupe" → faux clients qui polluent (Acronos +34 k€ janv en
  Ajustements).
- Burn rate à 0 → `runway_months=None` → status "none" (cache l'info utile).
- N+1 potentiel sur `compute_runway_core` quand le nombre d'entités grossit.

### Forecast
- **Double-comptage Engagements ↔ ForecastLine sur mois futurs** :
  `forecast_engine.py:528-539` → pour `month > current_month`, `_combine_total`
  retourne `forecast` seul, `committed` n'est PAS ajouté → les commitments
  futurs ne s'affichent pas dans le total mensuel sauf au mois courant.
  Drawer affiche pourtant l'onglet "Engagées" → UX schizophrène.
- PivotTable suppose une agrégation parent qui n'existe pas backend
  (`PivotTable.tsx:115-117`) — fonctionne par accident (filtre rows vides +
  promotion enfants orphelins en roots).
- AVG_3M / AVG_6M / AVG_12M sans guard si données insuffisantes → divisent par
  n même quand 3 mois disponibles seulement.
- Cache `Cache-Control: max-age=30` sur `/forecast/pivot` → cellule reste vide
  quelques secondes après création.
- `parseAmount` accepte `0` pour RECURRING_FIXED (ligne fantôme à 0 € en DB).
- `entity_id` redondant sur ForecastLine (déductible via scenario).

### Flux d'entrée
- Re-upload même PDF non idempotent : `/api/imports` ne check pas `file_sha256`
  existant avant créer ImportRecord → historique pollué.
- Imports tout-ou-rien : 1 erreur de parsing → 0 ligne insérée pour 207. Pas
  de feedback fin (pas de skiplist).
- Filtres transactions : pas d'amount_min/max, pas de persistance URL.
- Bulk-categorize perd la sélection au changement de page → bulk > 50 lignes
  impossible.
- Suggestion de règle (`/from-transactions`) : préfixe le plus long fragile.
- Reorder règles : risque IntegrityError sur swap (UNIQUE
  `(entity_id, priority)`) — try/except 409 mais UX cassante.
- 25 % des transactions réelles non catégorisées après 4 mois (taux 74,6 %
  sous seuil pro 80 %). Manque règles cartes par défaut, Agicap, salariés
  Primes/IK/STC.
- Règle 103 "STARTS_WITH `FRAIS **`" : 0 hit, les `**` disparaissent à la
  normalisation (`parsers/normalization.py`).

### Admin & cross-cutting
- Filtre audit-log exclut `merge` (`admin_audit.py:32` regex
  `^(create|update|delete)$`) alors que la migration a été faite pour
  l'accepter (Plan A).
- Pas d'audit auth events (login/logout/failed_login).
- Pas de lockout user après N échecs login (slowapi IP-only, contournable).
- Page admin pour `client_errors` n'existe pas (API en place).
- `AdminCategoriesPage` n'expose pas la couleur (schema accepte `color`).
- Section `securite` doc → désynchro avec le code (cf. P0 #12).
- Pas d'export CSV sur audit-log et client-errors.
- Pas de `X-Request-ID` middleware (corrélation logs/audit impossible).

### Hygiène backend
- **23 FK sans index** : `entities.parent_entity_id`,
  `categories.parent_category_id`, `imports.uploaded_by_id`,
  `transactions.{categorization_rule_id, counter_entity_id, import_id, parent_transaction_id}`,
  `categorization_rules.{bank_account_id, category_id, counterparty_id, created_by_id}`,
  `forecast_entries.{bank_account_id, category_id, counterparty_id, created_by_id}`,
  `commitments.{bank_account_id, category_id, counterparty_id, created_by_id, pdf_attachment_id}`,
  `forecast_scenarios.created_by_id`,
  `forecast_lines.{base_category_id, updated_by_id}`.
  Priorité haute : `transactions.import_id`, `transactions.categorization_rule_id`,
  `commitments.{category_id, counterparty_id, bank_account_id}`.
- **6 routers critiques sans test API** : auth, bootstrap, me, users, entities,
  bank_accounts. + `admin_audit`, `admin_client_errors`, `admin_backups`,
  `client_errors` également absents.
- Code dupliqué : try/except autour de l'audit log (3 sites quasi-identiques).
- `import logging` répété DANS des except blocs (devrait être en haut de
  fichier).
- Mass-assignment partiel via `setattr` boucle sur
  `model_dump(exclude_unset=True)` : risque latent si un champ sensible est
  ajouté à un schéma (users, commitments, forecast, forecast_scenarios,
  bank_accounts, entities).
- Listings non bornés : counterparties (139 lignes auj), forecast_lines,
  forecast_scenarios, rules. À paginer même si tables petites aujourd'hui.
- `selectinload`/`joinedload` quasi-inexistant (3 occurrences) → N+1 latents
  sur listings rules/commitments avec relations.
- `9b47b41a827e_initial_schema_placeholder.py` à documenter ou squash.

---

## Features pertinentes qui marchent (à protéger)

- Garde "jamais sans admin actif", multi-tenant centralisé, audit avec scrub.
- Backup pipeline robuste avec restore-test automatique.
- Dedup SHA-256 transactions (0 doublon en prod).
- Multi-valeurs `label_value` ("DGFIP, TVA"), 25/48 règles l'utilisent.
- Forecast moteur formules avec resolver récursif + détection de cycle.
- Pivot batch-loaded (~4 requêtes vs N×M).
- 9 méthodes de prévision propres et utiles.
- `reassign_to_parent` sur DELETE category (excellente UX).
- Refontes Plan A (Tiers) + Plan B (Engagements) — pattern qualité référence.
- Health/readyz fonctionnent (juste mauvais préfixe).
- Documentation exhaustive (sauf désynchros listées).

---

## Features sans valeur / à supprimer ou repenser

| Item | Domaine | Verdict |
|---|---|---|
| API legacy `/api/forecast/{entries,projection,recurring-suggestions}` | Forecast | À supprimer OU rebrancher |
| `forecast_entries` table + modèle | Forecast | Cf. ci-dessus |
| `frontend/src/api/forecast.ts` | Forecast | Orphelin → à supprimer |
| `is_intercompany`, `counter_entity_id` (Transaction) | Flux | À supprimer ou implémenter |
| Styling `is_aggregation_parent` | Flux | Mort (parent masqué) |
| TopMoversCard | Pilotage | Doublonne CategoryDriftTable, à fusionner |
| YoYChart sur 12 mois fixes | Pilotage | À gater (afficher si ≥ 13 mois sinon MoM 6 mois) |
| ForecastVarianceCard | Pilotage | Mesure une table morte (`forecast_entries`) — à reconnecter sur `forecast_lines` ou supprimer |
| `POST /admin/audit-log/prune` | Admin | À cron-iser ou retirer de l'API |
| Endpoint `bootstrap` exposé à vie | Admin | À fermer via flag une fois bootstrap fait |
| Scénario démo "Scénario redressement" Acreed | Forecast | À nettoyer si test |
| 22 règles à 0 hit (dont règle 103 inerte) | Flux | Audit + suppression ciblée |
| `PivotBars` ("hachures = prévisionnel") | Forecast | À évaluer en usage réel, peut-être bruit visuel |

---

## Top features manquantes (12 items priorisés)

Anchored à l'usage trésorerie réelle (Agicap-like) :

1. **Solde de trésorerie quotidien sur 90 jours** — graphe central absent.
2. **Export CSV/XLSX** — sur Audit, Analyse (chaque widget), Pivot prévisionnel,
   Transactions filtrées. Demandé par les 5 audits indépendamment.
3. **Rolling 13-week** côté Forecast (vue hebdo court terme).
4. **DSO/DPO/BFR en bandeau** sur Forecast (déjà calculé via
   `compute_working_capital`, juste à brancher).
5. **`Category.kind`** (`in`/`out`/`both`) — prérequis structurel qui débloque
   plusieurs corrections.
6. **Filtres URL-persistés** sur Transactions, Règles, Engagements, Audit
   (refresh perd l'état).
7. **Détection auto de récurrents** branchée à l'UI (`detect_recurring` existe
   en backend, 0 importeur frontend).
8. **Auto-suggestion de règle** quand un user catégorise manuellement N fois la
   même chose ("vous avez catégorisé 3 PRLV AGICAP en X, créer une règle ?").
9. **Anomalies p95** par catégorie (montant > p95 historique).
10. **Login auth events dans audit log** + lockout après N échecs.
11. **2FA TOTP** (le scrub `totp_secret` est déjà en place, plus qu'à ajouter
    la colonne).
12. **Forgot-password** — aujourd'hui dépend d'un admin qui reset.

Autres (P3) : invite user par email, comparaison overlay multi-scénarios,
what-if sur ligne unique sans dupliquer scénario, saisonnalité par catégorie,
position de trésorerie nette par compte bancaire, vue PDF↔tx parsées
côte-à-côte, hit count par règle exposé, snooze de dérive.

---

## Roadmap proposée (5 plans)

Ordre suggéré, du plus rentable au plus lourd. Estimations indicatives
(approximations basées sur la complexité et la taille relative à Plan A/B
qui ont pris ~1 jour chacun).

### Plan C — Bug fixes cross-domaines (P0 consolidés)
**Scope :** 13 bugs P0 de la table consolidée + bonus middleware request_id.
**Pas d'ajout fonctionnel.** Effet immédiat sur la perception qualité.
**Estimation :** 2-3 jours en subagent driven.

Items :
- C1. Drift formula avec guard (`|avg3m| ≥ 50 €` ET ≥ 2 mois actifs sur 3 ;
  sinon `delta_pct=None` → UI affiche "—")
- C2. Ancrage `MAX(operation_date)` au lieu de `date.today()` partout dans
  `analysis.py` ; afficher la fenêtre temporelle dans le header de la page
  Analyse
- C3. Top Movers : `current = dernier mois plein` (≥ N transactions, ex. ≥
  50 % médiane mensuelle)
- C4. Filtre `parent_transaction_id IS NULL` dans `build_rule_filter` ET
  `matches_transaction` ; lancer `recategorize_entity` sur les 2 entités →
  197 lignes corrigées
- C5. Setters dans `RuleForm.tsx:36-42` + UI pour éditer
  amount/counterparty/bank_account ; mettre à jour la validation ligne 75
- C6. `preview_rule` filtre par `accessible_entity_ids` du user (passer `user`
  au service)
- C7. Alias `/api/healthz` (monter `health.router` avec préfixe ou ajouter
  alias) + `/api/readyz`
- C8. Composant `AdminRoute` wrapper qui vérifie `me.role==='admin'` ;
  appliquer aux routes `/administration/*` dans `router.tsx`
- C9. Ouvrir `GET /api/bank-accounts` aux readers avec filtrage
  `accessible_entity_ids`
- C10. Étendre filtre audit-log pour accepter `merge` (regex
  `^(create|update|delete|merge)$`)
- C11. Helper `audit_safely(...)` dans `services/audit.py` ; remplacer les 3
  try/except de `transactions.py:142-178`, `rules.py:265-300/347-371` ;
  loguer `WARNING` avec `exc_info` au lieu de swallow
- C12. Middleware ASGI `X-Request-ID` (uuid4 si absent) + injection dans
  logging via `contextvars` ; embarquer `request_id` + `user_id` dans
  `JsonFormatter`
- C13. `session_token_version` sur User ; rotation au reset MdP → invalide
  les sessions actives ; aligner doc `securite`
- C14. **Préalable :** créer un compte READER de test pour exercer la branche
  tenant (révèle bugs latents)

### Plan D — Forecast cleanup
**Scope :** lever la dette qui pourrit aussi Pilotage analytique.
**Estimation :** 1-2 jours.

Items :
- D1. Trancher `forecast_entries` : kill complet (API `forecast.py`, modèle
  `ForecastEntry`, service `forecast.py`, `frontend/src/api/forecast.ts`,
  `ForecastVarianceCard`) OU rebrancher comme "entrées manuelles" avec UI
  dédiée. Statu quo = dette qui grossit.
- D2. Ajouter `Category.kind` (`in`/`out`/`both`) + migration de seeding
  sur les 65 catégories existantes ; basculer
  `_directions_by_category` dessus
- D3. Fixer `_combine_total` pour mois futurs : ajouter `committed_pending` au
  `forecast` (en évitant double-compte si une ligne couvre déjà l'engagement)
- D4. Supprimer `Cache-Control: max-age=30` sur `/forecast/pivot` (ou
  descendre à 5s)
- D5. Garde-fous AVG_* : `null`/grisé si historique insuffisant, division par
  `min(n, available)`
- D6. Brancher `detect_recurring` dans le drawer/page forecast ("Suggérer
  depuis l'historique")
- D7. Corriger l'agrégation de groupe dans `PivotTable.tsx:115-117` (sommer
  toutes les lignes d'une direction, pas seulement les roots)
- D8. Reconnecter `ForecastVarianceCard` sur `forecast_lines` (si on garde la
  carte) — sinon supprimer

### Plan F — Hygiène & sécurité
**Scope :** avant d'ajouter du fonctionnel sur une base avec des trous.
**Estimation :** 3 jours.

Items :
- F1. Migration unique "add_missing_fk_indexes" : 23 FK manquantes (priorité
  `transactions.import_id`, `transactions.categorization_rule_id`,
  `commitments.category_id/counterparty_id/bank_account_id`)
- F2. Tests API minimaux pour les 6 routers critiques sans coverage : auth,
  bootstrap, me, users, entities, bank_accounts. ≥ happy path + 1 cas 403/404
  par endpoint
- F3. Audit auth events (login OK / fail / logout) — table dédiée `auth_log`
  ou élargir audit_log
- F4. Lockout user après N échecs login (incrémenter
  `failed_login_attempts`, gel 15 min)
- F5. Pagination forcée sur listings non bornés : counterparties,
  forecast_lines, forecast_scenarios, rules (`Query(default=200, le=1000)`)
- F6. Fix règle 103 et autres regex cassées par `normalize_label` (audit
  des 22 règles à 0 hit)
- F7. Remplacer la boucle `setattr` générique par whitelist explicite dans
  users.py, commitments.py, bank_accounts.py, forecast.py,
  forecast_scenarios.py, entities.py
- F8. `selectinload` sur listings rules + commitments (relations category,
  counterparty, bank_account)
- F9. Cron pour `audit-log/prune` ou retirer l'endpoint
- F10. Synchroniser doc `securite` avec la réalité

### Plan E — Catégorisation upgrade
**Scope :** cible taux **≥ 90 %** (vs 74,6 % actuel).
**Estimation :** 2 jours.

Items :
- E1. Règles génériques manquantes :
  - Cartes par défaut ("Carte X%" → "Achats par carte" + sous-règles)
  - Agicap (PRLV AGICAP)
  - Salariés Primes/IK/Solde de tout compte (étendre règle Salaires)
  - Frais bancaires (corriger règle 103 ou nouvelle)
- E2. Idempotence upload : SHA-256 check sur `imports` → renvoyer
  ImportRecord existant en 200 si déjà importé
- E3. Aperçu live debounced dans RuleForm (pas un bouton "Aperçu")
- E4. Auto-suggestion de règle après N catégorisations manuelles identiques
- E5. Page admin pour `client_errors` (utiliser `admin_client_errors.py`)
- E6. Bulk "select all results" sur transactions filtrées
- E7. Filtre `parent_transaction_id IS NULL` exposé en UI (toggle "afficher
  détails SEPA")
- E8. Filtre amount_min/amount_max + persistance URL des filtres
  Transactions
- E9. Hit count par règle exposé dans la liste

### Plan G — Features pro (la cerise)
**Scope :** features qui distinguent un outil pro d'une démo.
**Estimation :** 5-7 jours.

Items :
- G1. Solde de trésorerie quotidien sur 90 jours (graphe central type Agicap)
- G2. Rolling 13-week côté Forecast
- G3. DSO/DPO/BFR en bandeau Forecast (data déjà calculée)
- G4. Anomalies p95 par catégorie
- G5. 2FA TOTP
- G6. Forgot-password + reset par email
- G7. Comparaison overlay multi-scénarios (PivotBars overlay)
- G8. What-if sur une ligne unique sans dupliquer le scénario
- G9. Saisonnalité par catégorie (M de l'an N vs M de l'an N-1)
- G10. Position de trésorerie nette par compte bancaire
- G11. Export CSV/XLSX généralisé (audit, analyse, pivot, transactions)
- G12. Snooze/acquittement de dérive

---

## Annexe : données observées en DB au moment de l'audit

| Item | Valeur |
|---|---|
| Transactions | 711 (107 NONE / 402 RULE / 202 MANUAL ; 98 parents agrégat ; 294 enfants) |
| Transactions réelles (hors agrégats) | 319 (238 catégorisées, 81 NONE → **74,6 %**) |
| Imports | 10/10 completed, 0 failed, 0 réimportés |
| Période data | janv→avril 2026 |
| Entités | 3 (Acronos id=1 : 178 tx 0 en avril ; Acreed Consulting id=2 : 525 tx ; Acreed IA Solutions id=3 : 8 tx) |
| Users | 5, **tous admin** (0 reader) |
| Catégories | 65 (16 racines, 49 enfants, 0 avec `kind`) |
| Règles | 48 (47 système, 1 user) ; 22 à 0 hit |
| Counterparties | 139 |
| Commitments | 1 pending (entity 2, OUT), 0 matché |
| Forecast scenarios | 4 (3 entités, 1 a 2 scénarios dont 1 démo "Scénario redressement") |
| Forecast lines | 2 (toutes RECURRING_FIXED, dont 1 à 0 € en pollution) |
| Forecast entries | **0** — table orpheline |
| Audit log | 110 lignes (du 27/04/2026 au 06/05/2026) |
| Backup history | 18 (16 scheduled, 1 manual, 1 restore-test ; 5 verified) |
| Client errors | 21 (20 errors, 1 info, 0 acquittés/exposés UI) |
| LOC backend (`app/`) | 11 905 lignes Python |
| Migrations | 19 + 1 placeholder |
| Indexes existants | 58 ; 23 FK sans index |

**Cas reproduit du drift -1272,6 %** : entity_id=2, category_id=24
"Frais pro. remboursés", current_cents=-29 621, avg3m_cents=-2158
(jan=0, fev=0, mars=-6474, avg3m = -6474//3 = -2158),
delta_pct = (-29621 - (-2158)) / 2158 * 100 = -1272,61 %.

---

## État du repo au moment de l'audit

- Branche courante : `refonte/engagements`, 9 commits, **non mergée sur main**.
- Plan A (Refonte Tiers) : mergé sur main.
- Plan B (Refonte Engagements) : sur la branche `refonte/engagements`,
  build prod déployé, validé par l'utilisateur (test "ok pour l'instant").
- Pas de push sur origin (toujours en local).
- `CLAUDE.md` : règle d'équipe doc d'impact en place + type FeatureDoc.
- DB head : `h0r1z0n50601` (migration audit "merge" appliquée Plan A).
- Containers : `horizon-backend-1`, `horizon-frontend-1`, `horizon-db-1`.

**Décisions ouvertes (à arbitrer demain) :**
- Merger `refonte/engagements` sur main avant Plan C ? Ma reco : **oui**, avant
  d'attaquer Plan C, pour avoir un point de départ propre.
- Pousser sur origin ? Pas demandé jusqu'ici.
- Démarrer par Plan C tel quel, ou C+D combinés (plus de cohérence forecast/
  pilotage), ou réordonner ?

---

## Prompt de relance pour la prochaine session

Demain, ouvre une nouvelle conversation et dis-moi ceci (copier-coller direct,
ou résumer en tes mots) :

> **Reprends le doc d'audit
> `docs/superpowers/audits/2026-05-06-app-review-master.md`. Avant tout :
> merge la branche `refonte/engagements` sur main (Plan B validé hier soir).
> Ensuite, rédige Plan C (bug fixes cross-domaines, 14 items C1→C14) sur le
> modèle des Plans A/B précédents et exécute-le en subagent driven. Checkpoint
> après les fixes backend (avant le frontend) puis ping moi à la fin avec
> build & deploy live.**

Optionnel selon ton arbitrage :
- Si tu veux **ajouter Plan D** dans la foulée (forecast cleanup) : ajoute
  "Enchaîne Plan D directement après Plan C, même mode subagent driven."
- Si tu veux **revoir la roadmap d'abord** : dis "Avant Plan C, on revoit
  ensemble la priorisation des plans D/E/F/G."
- Si tu veux **un compte READER de test d'abord** (recommandé) : dis "Avant
  Plan C, crée un compte de test READER et lance un smoke pour vérifier que
  les bugs P0 #10, #11 sont bien reproductibles, puis fixe-les en priorité."

---

## Mémo pour l'agent qui reprend

- Lis CE document **en premier**, pas la peine de re-investiguer ce qui est
  déjà documenté ici.
- Les rapports détaillés des 5 subagents ne sont plus accessibles dans la
  prochaine session (ils étaient dans la transcription) — ce résumé est la
  source de vérité.
- Les fichiers et lignes cités ont été vérifiés au moment de l'audit
  (2026-05-06) ; vérifie quand même qu'ils n'ont pas bougé avant de coder.
- Conventions de l'app à respecter (rappel) : tests dans le container, pas
  localement (Python 3.10 vs 3.11+) ; `BACKEND_COOKIE_SECURE=false` dans
  conftest pour que TestClient garde le cookie ; pour migrations, `docker cp`
  dans `/app/alembic/versions/` puis appliquer côté DB ; commit messages en
  français, ton sobre, sans emoji.
- Workflow subagent driven : briefer chaque agent avec le scope précis du
  Plan + les conventions ci-dessus + lien vers ce master report pour contexte.
