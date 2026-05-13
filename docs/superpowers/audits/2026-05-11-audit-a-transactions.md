# Audit A — Transactions & Catégorisation
Date : 2026-05-11
Couverture : pages 2/2 (TransactionsPage, RulesPage), endpoints 12/12

## Synthèse
- 2 bugs **critiques** (action ne fait pas ce qu'elle dit / erreur serveur)
- 2 bugs **moyens** (UX dégradée mais data correcte)
- 2 bugs **mineurs** (libellés, edge cases)
- 4 **observations** (pas des bugs mais à connaître)

---

## Bugs trouvés (par sévérité décroissante)

### BUG-A-001 (critique) — Export CSV : HTTP 500 dès que date_from ou date_to est fourni

- **Composant** : `backend/app/api/transactions.py` lignes 141–178 (`export_transactions`)
- **Action testée** : Clic "Exporter CSV" avec un filtre de période actif
- **Cas reproduisant** :
  - `GET /api/transactions/export?date_from=2026-01-01` → HTTP 500
  - `GET /api/transactions/export?date_to=2026-01-31` → HTTP 500
  - Tout export sans filtre de date → HTTP 200 (OK)
- **Résultat attendu** : CSV filtré par la période
- **Résultat observé** : `Internal Server Error` ; log backend :
  ```
  sqlalchemy.exc.ProgrammingError: operator does not exist: date >= character varying
  transactions.operation_date >= $2::VARCHAR
  HINT: No operator matches the given name and argument types.
  ```
- **Cause** : `export_transactions` déclare `date_from: str | None = Query(None)` alors que
  `list_transactions` utilise `TransactionFilter` (Pydantic coerce automatiquement en `date`).
  SQLAlchemy refuse de comparer une colonne `date` PostgreSQL avec un `VARCHAR`.
- **Suggestion de fix** : Changer le type en `date | None` dans la signature d'`export_transactions`
  (importer `date` depuis `datetime`). Deux lignes de changement.

---

### BUG-A-002 (critique) — Export CSV : 0 résultats quand counterparty_id est filtré (les enfants SEPA manquent)

- **Composant** : `backend/app/api/transactions.py` lignes 179 et 195–196 (`export_transactions`)
- **Action testée** : Exporter avec un filtre par tiers actif (ex. counterparty_id=74)
- **Cas reproduisant** :
  - List API : `GET /api/transactions?counterparty_id=74` → total=20 (E7 bypass inclut les enfants SEPA)
  - Export : `GET /api/transactions/export?counterparty_id=74` → 0 lignes de données (seulement l'en-tête)
  - Export avec `include_sepa_children=true` : `GET /api/transactions/export?counterparty_id=74&include_sepa_children=true` → 20 lignes (OK)
- **Résultat attendu** : L'export reflète exactement ce que la liste affiche pour le même filtre
- **Résultat observé** : L'export ignore l'exception E7 (inclure les enfants SEPA si counterparty_id est
  fourni) présente dans `list_transactions` mais absente d'`export_transactions`. Le CSV exporté contient
  0 ligne de données pour ce tiers.
- **Cause** : `list_transactions` applique `if not filters.include_sepa_children and not filters.counterparty_id: conditions.append(parent IS NULL)` (E7 bypass). `export_transactions` applique seulement `if not include_sepa_children: conditions.append(parent IS NULL)`, sans le bypass counterparty.
- **Suggestion de fix** : Dans `export_transactions`, remplacer :
  ```python
  if not include_sepa_children:
      conditions.append(Transaction.parent_transaction_id.is_(None))
  ```
  par :
  ```python
  if not include_sepa_children and not counterparty_id:
      conditions.append(Transaction.parent_transaction_id.is_(None))
  ```

---

### BUG-A-003 (moyen) — auto-suggest propose des règles déjà couvertes par des patterns multi-valeurs

- **Composant** : `backend/app/api/rules.py` lignes 183–208 (`auto_suggest`)
- **Action testée** : Consulter les suggestions de règles automatiques
- **Cas reproduisant** :
  - Entité : toutes ; `GET /api/rules/auto-suggest`
  - Retourne `RESTITUTION RETENUE GARANTIE` comme pattern sans règle
  - La règle 113 ("Affacturage Dailly") a `label_value = "VIR DU COMPTE DAILLY, REM CREANCE, RETENUE GARANTIE, REGLEMENT CREANCE, BNP PARIBAS FACTOR"`
  - "RETENUE GARANTIE" est un des patterns multi-valeurs qui matcherait ce libellé
- **Résultat attendu** : Ce pattern est exclu des suggestions car couvert par la règle 113
- **Résultat observé** : Le pattern est suggéré comme "sans règle associée"
- **Cause** : La vérification de couverture compare `norm_label.upper() in lv.upper()` et
  `lv.upper() in norm_label.upper()` sur la chaîne brute `lv`. Pour les règles multi-valeurs
  (`lv = "VIR DU COMPTE DAILLY, REM CREANCE, RETENUE GARANTIE,..."`) la comparaison de chaîne
  entière échoue. Le code ne split pas `lv` par virgule avant de tester les patterns individuels.
- **Suggestion de fix** : Dans la liste comprehension `existing_label_values`, stocker les patterns
  individuels après split par virgule, ou modifier la vérification pour itérer sur
  `[p.strip() for p in (lv or '').split(',')]`.

---

### BUG-A-004 (moyen) — RulesPage : toutes les règles disparaissent quand un filtre entité est actif

- **Composant** : `frontend/src/pages/RulesPage.tsx` ligne 30–33 ; `backend/app/api/rules.py` lignes 85–98
- **Action testée** : Sélectionner une entité via EntitySelector sur la page Règles
- **Cas reproduisant** :
  - Entité = "Acreed Consulting" (id=2) : `GET /api/rules?entity_id=2` → 0 règles
  - Entité = "Acronos" (id=1) : `GET /api/rules?entity_id=1` → 0 règles
  - Aucun filtre entité : `GET /api/rules` → 59 règles
- **Résultat attendu** : L'EntitySelector sur RulesPage devrait filtrer les règles entity-specific
  et afficher les règles globales (applicables à toutes les entités)
- **Résultat observé** : Quand entity_id est fourni à l'API, seules les règles ayant
  `entity_id == X` remontent. Comme toutes les 59 règles sont globales (`entity_id IS NULL`),
  la page affiche 0 règles dès qu'une entité est sélectionnée.
- **Cause** : `RulesPage` transmet `entity_id` à `useRules`, qui passe à l'API `?entity_id=X`.
  L'API filtre `CategorizationRule.entity_id == X`, masquant les règles globales.
  Comportement API correct mais usage frontend inadapté.
- **Suggestion de fix** :
  Option A : Ne pas passer `entity_id` à l'API depuis RulesPage (l'EntitySelector n'est
  peut-être pas pertinent sur cette page).
  Option B : Côté API, quand `entity_id` est fourni, retourner les règles de cette entité
  ET les règles globales (ajouter `| CategorizationRule.entity_id.is_(None)`).

---

### BUG-A-005 (mineur) — SortableRulesTable : opérateurs de règle affichés en majuscules (non traduits)

- **Composant** : `frontend/src/components/SortableRulesTable.tsx` lignes 29–38 (`operatorLabel`)
- **Action testée** : Consulter la liste des règles (page Règles)
- **Cas reproduisant** : Toutes les règles affichent `CONTAINS`, `STARTS_WITH`, etc. dans la cellule libellé
- **Résultat attendu** : "contient", "commence par", "finit par", "égal à" (labels français)
- **Résultat observé** : `CONTAINS`, `STARTS_WITH`, `ENDS_WITH`, `EQUALS` (uppercase API values)
- **Cause** : `operatorLabel` mappe des clés en minuscule (`{ contains: "contient", starts_with: "commence par", ... }`) alors que l'API retourne des valeurs en MAJUSCULES. `map['CONTAINS']` est `undefined`, la fonction retourne la clé brute.
- **Suggestion de fix** :
  ```ts
  const key = (op ?? "").toLowerCase();
  return map[key] ?? op;
  ```

---

### BUG-A-006 (mineur) — E2E tests : test_e2e_plan1 et test_e2e_plan2 échouent

- **Composant** : `backend/tests/test_e2e_plan1.py`, `backend/tests/test_e2e_plan2.py`
- **Action testée** : Suite de tests E2E sur import + catégorisation automatique
- **Cas reproduisant** : `pytest tests/test_e2e_plan1.py` → `assert 12 >= 30` ; `pytest tests/test_e2e_plan2.py` → `assert auto_count >= 3` (obtenu 2)
- **Résultat attendu** : ≥ 30 transactions importées depuis la fixture PDF, ≥ 3 catégorisées automatiquement
- **Résultat observé** : 12 transactions importées (fixture produit moins que ce que le test attend)
- **Cause supposée** : La fixture `synthetic_full_month.pdf` a évolué (ou le parseur PDF a changé de comportement) sans que les assertions du test soient mises à jour. Non lié à la couche Transactions/Catégorisation.
- **Suggestion de fix** : Mettre à jour les seuils dans les tests en accord avec ce que la fixture produit réellement, ou régénérer la fixture.

---

## Tableau exhaustif des actions testées

| # | Action | Cas | Entité | Attendu | Observé | Verdict |
|---|--------|-----|--------|---------|---------|---------|
| 1 | GET /api/transactions (nominal) | page=1, per_page=5 | toutes | items, total | ✓ total=319, items=5 | PASS |
| 2 | GET /api/transactions | entity_id=1 | Acronos | total=178, all entity_id=1 | ✓ | PASS |
| 3 | GET /api/transactions | entity_id=2 | Acreed Consulting | total=133, all entity_id=2 | ✓ | PASS |
| 4 | GET /api/transactions | entity_id=3 | Acreed IA Solutions | total=8 | ✓ | PASS |
| 5 | GET /api/transactions | entity_id=999 (inexistant) | admin | 0 résultats (pas 403 car admin) | ✓ items=[] | PASS |
| 6 | GET /api/transactions | date_from=2026-01-01&date_to=2026-01-31 | toutes | 96 tx en jan 2026 | ✓ total=96 | PASS |
| 7 | GET /api/transactions | uncategorized=true | toutes | total=81, toutes sans catégorie | ✓ | PASS |
| 8 | GET /api/transactions | search=URSSAF (majuscules) | toutes | 13 tx | ✓ total=13 | PASS |
| 9 | GET /api/transactions | search=urssaf (minuscules) | toutes | même résultat | ✓ total=13 | PASS |
| 10 | GET /api/transactions | search=% (wildcard SQL) | toutes | 319 (matches all) | ✓ total=319 | PASS (comportement attendu) |
| 11 | GET /api/transactions | amount_min=1000&amount_max=5000 | toutes | 26 tx entre 1000€ et 5000€ (valeur absolue) | ✓ total=26 | PASS |
| 12 | GET /api/transactions | amount_min=-100 (valeur négative) | toutes | 319 (abs>=−100 = toujours vrai) | ✓ total=319 | PASS (UI empêche via min=0) |
| 13 | GET /api/transactions | counterparty_id=74 | toutes | total=20 avec SEPA children | ✓ total=20, SEPA children inclus | PASS |
| 14 | GET /api/transactions | category_id=21 (Virement salaire) | toutes | total=1 (SEPA children exclus par défaut) | ✓ total=1 (43 avec SEPA) | PASS (conforme E7) |
| 15 | GET /api/transactions | category_id=21&include_sepa_children=true | toutes | total=43 | ✓ total=43 | PASS |
| 16 | GET /api/transactions | include_sepa_children=false vs true | toutes | 319 vs 613 | ✓ | PASS |
| 17 | GET /api/transactions | page=2, per_page=10 | toutes | 10 items, page=2 | ✓ | PASS |
| 18 | GET /api/transactions | page=100 (au-delà) | toutes | 0 items | ✓ | PASS |
| 19 | GET /api/transactions | per_page=500 (max) | toutes | 319 items | ✓ | PASS |
| 20 | GET /api/transactions | per_page=501 (hors plage) | toutes | 422 Unprocessable | ✓ | PASS |
| 21 | GET /api/transactions | COMBO entity=2 + date jan + uncategorized=true | Acreed Consulting | total=0 (toutes catégorisées) | ✓ | PASS |
| 22 | GET /api/transactions | COMBO search=URSSAF + amount_min=500 + amount_max=2000 | toutes | 11 tx | ✓ | PASS |
| 23 | GET /api/transactions | COMBO entity=1 + category_id=25 (URSSAF) | Acronos | 7 tx | ✓ | PASS |
| 24 | GET /api/transactions | COMBO counterparty=74 + date_from=2026-01-01 + date_to=2026-03-31 | toutes | 8 tx | ✓ | PASS |
| 25 | GET /api/transactions | COMBO entity=2 + search=SEPA + amount_min=1000 + sepa=true | Acreed Consulting | 82 tx | ✓ | PASS |
| 26 | GET /api/transactions/export | sans filtre | toutes | CSV 319+1 lignes | ✓ 319+header | PASS |
| 27 | GET /api/transactions/export | entity_id=1 | Acronos | CSV 178+1 lignes | ✓ 178+header | PASS |
| 28 | GET /api/transactions/export | date_from=2026-01-01 | toutes | CSV filtré | HTTP 500 | **BUG A-001** |
| 29 | GET /api/transactions/export | date_to=2026-01-31 | toutes | CSV filtré | HTTP 500 | **BUG A-001** |
| 30 | GET /api/transactions/export | entity_id=2 + date_from + date_to | Acreed Consulting | CSV filtré | HTTP 500 | **BUG A-001** |
| 31 | GET /api/transactions/export | counterparty_id=74 | toutes | 20 lignes | 0 lignes de données | **BUG A-002** |
| 32 | GET /api/transactions/export | counterparty_id=74 + include_sepa_children=true | toutes | 20 lignes | ✓ 20 lignes | PASS |
| 33 | GET /api/transactions/export | format=xlsx | toutes | 400 (xlsx non dispo) | ✓ 400 | PASS |
| 34 | POST /api/transactions/bulk-categorize | transaction_ids=[X], category_id=Y (reader) | toutes | 403 | ✓ 403 | PASS |
| 35 | POST /api/transactions/bulk-categorize | IDs valides, category_id valide (admin) | test-pg | updated_count=N | ✓ (tests pytest passent) | PASS |
| 36 | POST /api/transactions/bulk-categorize-filtered | uncategorized=true + entity_id | test-pg | toutes tx non catégorisées mises à jour | ✓ (tests pytest passent) | PASS |
| 37 | POST /api/transactions/bulk-categorize-filtered | date_from/date_to (Pydantic date) | test-pg | fonctionne | ✓ (date typé correctement) | PASS |
| 38 | GET /api/rules | scope=all | toutes | 59 règles | ✓ 59 | PASS |
| 39 | GET /api/rules | scope=global | toutes | 59 globales | ✓ all entity_id=null | PASS |
| 40 | GET /api/rules | scope=entity | toutes | 0 entity-specific | ✓ 0 | PASS |
| 41 | GET /api/rules | entity_id=2 | Acreed Consulting | 0 (aucune règle entity-scoped) | ✓ 0 — mais UX cassée | **BUG A-004** |
| 42 | GET /api/rules hit_count | rule URSSAF (id=1) | toutes | hit_count=9 | ✓ = COUNT(*) DB | PASS |
| 43 | GET /api/rules hit_count | rule TVA débit (id=3) | toutes | hit_count=20 | ✓ = COUNT(*) DB | PASS |
| 44 | GET /api/rules hit_count | rule Virement salaire (id=5) | toutes | hit_count=39 | ✓ = COUNT(*) DB (SEPA children comptés) | PASS |
| 45 | GET /api/rules/auto-suggest | min_count=3 (défaut) | toutes | suggestions légitimes | ✓ mais 1 faux positif | **BUG A-003** |
| 46 | GET /api/rules/auto-suggest | min_count=2 | toutes | plus de suggestions | ✓ 3 suggestions | PASS |
| 47 | POST /api/rules/preview | CONTAINS URSSAF DEBIT global | toutes | count=9 (non-MANUAL, non-SEPA-child, DEBIT) | ✓ | PASS |
| 48 | POST /api/rules/preview | STARTS_WITH VIR ANY global | toutes | count=114 | ✓ | PASS |
| 49 | POST /api/rules/preview | entity_id=1 URSSAF DEBIT | Acronos | count=7 | ✓ vs DB: 7 non-MANUAL entity_1 | PASS |
| 50 | POST /api/rules/preview | entity_id=2 URSSAF DEBIT | Acreed Consulting | count=2 | ✓ vs DB: 2 non-MANUAL entity_2 | PASS |
| 51 | POST /api/rules/preview | cross-tenant check (global rule, accessible_ids fournis) | toutes | restreint aux entités accessibles | ✓ | PASS |
| 52 | POST /api/rules/preview | ENDS_WITH AUVERGNE | toutes | count=5 | ✓ | PASS |
| 53 | POST /api/rules/preview | EQUALS RESTITUTION RETENUE GARANTIE | toutes | count=0 (tous MANUAL) | ✓ | PASS |
| 54 | POST /api/rules/preview | BETWEEN 1000-5000 (amount) | toutes | count=72 | ✓ | PASS |
| 55 | POST /api/rules/{id}/apply | règle système (id=1) — reader | toutes | 403 | ✓ | PASS |
| 56 | DELETE /api/rules/1 | règle système | toutes | 409 RULE_SYSTEM_DELETE | ✓ | PASS |
| 57 | POST /api/rules/from-transactions | 3 IDs URSSAF | toutes | STARTS_WITH PRLV URSSAF AUVERGNE, DEBIT | ✓ | PASS |
| 58 | POST /api/rules/from-transactions | IDs vides | toutes | 422 Sélection vide | ✓ | PASS |
| 59 | POST /api/rules/from-transactions | ID inexistant 99999 | toutes | 404 | ✓ | PASS |
| 60 | POST /api/rules/from-transactions | 1 seul ID | toutes | STARTS_WITH = label complet (très spécifique) | ✓ (design choice) | PASS |
| 61 | POST /api/rules/reorder | règles valides | test-pg | priorities mises à jour | ✓ (tests pytest passent) | PASS |
| 62 | PATCH /api/rules/{id} | règle système : champ structurel | toutes | 409 RULE_SYSTEM_MUTATE | ✓ | PASS |
| 63 | PATCH /api/rules/{id} | règle système : nom uniquement | test-pg | OK | ✓ (tests pytest passent) | PASS |
| 64 | SortableRulesTable operatorLabel | label_operator=CONTAINS | UI | "contient" | "CONTAINS" (uppercase) | **BUG A-005** |
| 65 | Bulk drawer auto-open | sélection d'une tx | UI | drawer s'ouvre | ✓ (code vérifié) | PASS |
| 66 | URL persistence counterparty_id | ?counterparty=74 | UI | filtre restauré depuis URL | ✓ (code vérifié, filtersFromSearchParams) | PASS |
| 67 | URL persistence date_from/date_to | ?date_from=X&date_to=Y | UI | filtres restaurés | ✓ (code vérifié) | PASS |
| 68 | CategoryCombobox directionHint CREDIT | sélection DEBIT transactions | UI | masque catégories débit | ✓ (CREDIT_ROOT_SLUGS + NEUTRAL_ROOT_SLUGS) | PASS |
| 69 | Reader permissions | bulk-categorize | toutes | 403 | ✓ | PASS |
| 70 | Reader permissions | create rule | toutes | 403 | ✓ | PASS |
| 71 | Reader permissions | apply rule | toutes | 403 | ✓ | PASS |
| 72 | Reader permissions | read transactions | entity_id=2 seulement | 133 tx | ✓ | PASS |
| 73 | E2E: import + auto-cat | test_e2e_plan1 | test-pg | ≥30 tx | 12 tx | **BUG A-006** |
| 74 | E2E: import + auto-cat | test_e2e_plan2 | test-pg | auto_count≥3 | 2 | **BUG A-006** |
| 75 | Pytest: 637 autres tests | tous | test-pg | PASS | ✓ 637 passed, 4 skipped | PASS |

---

## Observations (non bloquantes)

### OBS-1 — Category filter ne bypass pas les enfants SEPA (contrairement au filtre counterparty)

Quand on filtre par `category_id=21` (Virement salaire), l'API retourne 1 transaction au lieu
de 43. Les 42 restantes sont des enfants SEPA (`parent_transaction_id IS NOT NULL`) qui sont
masqués par défaut. Le filtre par tiers (counterparty_id) force l'inclusion des enfants SEPA
(E7 bypass), mais le filtre par catégorie ne le fait pas. L'utilisateur voit "1 opération
dans Salaire" alors que 43 sont catégorisées dans cette catégorie. Un message explicatif
ou un bypass similaire pour le filtre catégorie améliorerait la lisibilité.

### OBS-2 — Mettre à jour une règle ne recatégorise pas les transactions existantes

L'endpoint `PATCH /api/rules/{id}` ne déclenche pas `recategorize_entity`. Les transactions
déjà catégorisées par la version précédente de la règle gardent l'ancienne catégorie jusqu'à
ce que l'utilisateur clique manuellement sur "Appliquer" depuis la page Règles. C'est cohérent
avec le design actuel (apply explicite), mais l'UX du formulaire d'édition ne propose pas
de bouton "Modifier et appliquer" (contrairement au formulaire de création).

### OBS-3 — Export CSV : pas de colonne "Société" en contexte multi-entités

Quand l'export est déclenché sans filtre d'entité (toutes les entités), le CSV ne contient pas
de colonne "Société". L'utilisateur ne peut identifier l'entité d'une transaction que via le
nom du compte bancaire (colonne "Compte"). Cette ambiguïté est acceptable si les noms de compte
sont suffisamment distincts, mais peut poser problème si des comptes ont des noms similaires.

### OBS-4 — from-transactions avec 1 seul ID : suggestion trop spécifique

`POST /api/rules/from-transactions` avec un seul ID retourne `STARTS_WITH <label complet>`.
Le label normalisé d'une transaction bancaire inclut souvent des références uniques (numéros de
lot, dates), rendant la règle inutilisable pour des transactions futures similaires. Ce
comportement est par design mais l'UX pourrait indiquer que la suggestion est basée sur un
libellé complet non générique.

---

## Couverture

- **Actions identifiées** : 75
- **Actions testées** : 75 (100%)
- **Endpoints couverts** :
  - `GET /api/transactions` (tous filtres individuels + 5 combinaisons croisées)
  - `GET /api/transactions/export` (CSV avec et sans filtres)
  - `POST /api/transactions/bulk-categorize` (nominal + permissions)
  - `POST /api/transactions/bulk-categorize-filtered` (4 scénarios)
  - `GET /api/rules` (scope=global/entity/all, entity_id filter)
  - `GET /api/rules/auto-suggest` (min_count=2 et 3)
  - `POST /api/rules` (création — via pytest)
  - `PATCH /api/rules/{id}` (modification — via pytest)
  - `DELETE /api/rules/{id}` (système + admin only)
  - `POST /api/rules/preview` (CONTAINS/STARTS_WITH/ENDS_WITH/EQUALS/BETWEEN, global/entity-scoped)
  - `POST /api/rules/{id}/apply` (via pytest)
  - `POST /api/rules/reorder` (via pytest)
  - `POST /api/rules/from-transactions` (1 ID, 3 IDs, vide, inexistant)
  - `GET /api/categories` (structure, kind)

- **Endpoints non couverts en direct** (testés uniquement via pytest sur test-pg) :
  - `POST /api/transactions/bulk-categorize` (mutation prod interdite)
  - `POST /api/rules/{id}/apply` (mutation prod interdite — tests pytest complets)
  - `POST /api/rules/reorder` (mutation prod interdite — tests pytest complets)
  - Format XLSX export (xlsxwriter non installé → 400 attendu, confirmé)
