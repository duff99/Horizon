# Plan 2 — Module Catégorisation (règles automatiques)

**Date :** 2026-04-17
**Projet :** Horizon (clone Agicap — ACREED Consulting)
**Branche :** `plan-2-categorization`
**Dépend de :** Plan 1 (import & transactions Delubac) — livré, tag `plan-1-done`

## 1. Objectif

Permettre la catégorisation automatique et manuelle des transactions bancaires importées, via un moteur de règles déterministe, avec trente règles pré-installées pour les libellés Delubac standards et une interface de gestion complète.

Ce plan implémente le **Mécanisme 1** (règles automatiques) décrit dans la spec racine `2026-04-16-clone-agicap-design.md`. Les mécanismes d'apprentissage statistique et de suggestion IA sont hors scope.

## 2. Décisions de conception (issues du brainstorming)

| # | Décision | Choix |
|---|---|---|
| 1 | Scope | Mécanisme 1 seul : règles + UI CRUD + inbox + 30 règles Delubac + intégration pipeline |
| 2 | Application des règles | Preview avant persist ; l'utilisateur décide ; les transactions `MANUAL` ne sont jamais écrasées |
| 3 | Taxonomie | Seed complet des ~50 sous-catégories de la spec §6.1, en plus des 9 racines de Plan 1 |
| 4 | Portée des règles | Hybride : globales (entity_id NULL) + par entité ; règle entité > globale à priorité égale |
| 5 | Opérateurs libellé | `CONTAINS`, `STARTS_WITH`, `ENDS_WITH`, `EQUALS` (+ filtres structurels sens/montant/contrepartie/compte) |
| 6 | UX inbox | Multi-sélection + bouton "Assigner catégorie X" + "Créer une règle depuis la sélection" |
| 7 | Import/export JSON | Rien dans Plan 2 ; les 30 règles vivent dans une migration Alembic |
| 8 | Conflit multi-règles | First-match-wins par `priority` ASC ; scope entité prime sur globale à priorité égale |

## 3. Architecture

### 3.1 Modèle de données

**Nouvelle table `categorization_rule`**

| Colonne | Type | Contrainte |
|---|---|---|
| `id` | integer | PK autoincrement |
| `name` | text | non-null, longueur 1..120 |
| `entity_id` | int | FK `entity.id`, nullable (NULL = globale) |
| `priority` | int | non-null, unique par `(COALESCE(entity_id,'00000000-0000-0000-0000-000000000000'), priority)` via index partiel |
| `is_system` | bool | défaut False ; True pour les 30 pré-installées |
| `label_operator` | enum `rule_label_operator` | nullable (`CONTAINS / STARTS_WITH / ENDS_WITH / EQUALS`) |
| `label_value` | text | nullable ; requis si `label_operator` non-null ; normalisé à la même moulinette que `Transaction.normalized_label` |
| `direction` | enum `rule_direction` | non-null, défaut `ANY` (`CREDIT / DEBIT / ANY`) |
| `amount_operator` | enum `rule_amount_operator` | nullable (`EQ / NE / GT / LT / BETWEEN`) |
| `amount_value` | numeric(14,2) | nullable ; requis si `amount_operator` non-null |
| `amount_value2` | numeric(14,2) | nullable ; requis si `amount_operator = BETWEEN` |
| `counterparty_id` | int FK `counterparty.id` | nullable |
| `bank_account_id` | int FK `bank_account.id` | nullable |
| `category_id` | int FK `category.id` | non-null |
| `created_at / updated_at` | timestamptz | |
| `created_by_id` | int FK `user.id` | nullable pour les règles `is_system` seed |

**Contraintes applicatives** (CHECK ou validation pydantic) :

- Au moins un filtre non-trivial : `label_operator NOT NULL OR counterparty_id NOT NULL OR bank_account_id NOT NULL OR amount_operator NOT NULL OR direction <> 'ANY'`
- `amount_operator = BETWEEN ⇒ amount_value2 NOT NULL AND amount_value < amount_value2`

**Modifications à la table `transaction`** (Plan 1)

- Ajout `categorized_by` enum `transaction_categorization_source` non-null, défaut `NONE` (`NONE / RULE / MANUAL`)
- Ajout `categorization_rule_id` int FK `categorization_rule.id` nullable ON DELETE SET NULL (audit : quelle règle a matché)
- Ajout `normalized_label` text non-null, indexé (index B-tree sur `normalized_label` pour accélérer les LIKE ancrés ; pas de trigram en Plan 2). Plan 1 normalise déjà le libellé en vol pour calculer `dedup_key` via `app.parsers.normalization.normalize_label` ; on matérialise simplement cette valeur sur la ligne pour que le moteur de règles matche en SQL sans recalcul. Le pipeline d'import de Plan 1 sera modifié pour populer cette colonne à l'insert (une ligne de code).
- Backfill : la migration qui ajoute `normalized_label` renseigne la colonne pour les transactions existantes via un UPDATE qui réplique la logique de `normalize_label` en SQL pur (`UPPER(TRANSLATE(unaccent(label), '...', '...'))`), ou en Python via une migration data si l'UPDATE SQL pur est trop délicat — à trancher en phase de plan.

Invariant : `categorized_by = MANUAL` ⇒ aucune règle ne l'écrase. `categorized_by = NONE OR RULE` ⇒ un re-run du moteur peut réécrire `category_id` et `categorization_rule_id`.

### 3.2 Moteur de catégorisation

Service `app/services/categorization.py` :

```python
def evaluate_rules(tx: Transaction, rules: Iterable[CategorizationRule]) -> CategorizationRule | None:
    """Retourne la 1re règle qui matche (AND des filtres), dans l'ordre reçu."""

def fetch_rules_for_entity(session, entity_id: int) -> list[CategorizationRule]:
    """Retourne les règles de l'entité + globales, triées par (is_entity_scoped DESC, priority ASC).
    Le tri garantit qu'une règle entité gagne sur une globale de même priorité."""

def categorize_transaction(session, tx: Transaction) -> CategorizationResult:
    """Appelle fetch_rules_for_entity + evaluate_rules. Si match et tx.categorized_by != MANUAL,
    assigne category_id, categorization_rule_id, categorized_by=RULE. Ne commit pas."""

def preview_rule(session, rule_payload: RuleCreate) -> RulePreview:
    """Compte et échantillonne les transactions qui matcheraient cette règle (non persistée),
    en excluant celles categorized_by=MANUAL. Retourne total + 20 samples."""

def apply_rule(session, rule: CategorizationRule) -> ApplyReport:
    """Applique la règle aux transactions de son scope (entité ou global) non-MANUAL.
    Utilisé après création/édition d'une règle quand l'utilisateur confirme le preview."""

def recategorize_entity(session, entity_id: int) -> RecategorizationReport:
    """Réinitialise toutes les tx non-MANUAL de l'entité (categorized_by=NONE, category_id=NULL)
    puis relance categorize_transaction sur chacune. Utilisé après réordonnancement massif."""
```

### 3.3 Matching — sémantique précise

Un rule matche une transaction ssi **tous** les filtres non-null passent (ET logique) :

- **Libellé** (`label_operator`/`label_value`) : comparaison sur `tx.normalized_label` (colonne ajoutée en Plan 2, cf. §3.1). La valeur `label_value` est normalisée à l'écriture de la règle (pydantic validator) via le même `app.parsers.normalization.normalize_label`, donc la comparaison côté SQL est une égalité stricte ou un LIKE direct sans transformation runtime. `CONTAINS` = `normalized_label LIKE '%' || label_value || '%'`. `STARTS_WITH` = `LIKE label_value || '%'`. `ENDS_WITH` = `LIKE '%' || label_value`. `EQUALS` = `=`.
- **Sens** (`direction`) : `CREDIT` ⇒ `tx.amount > 0` ; `DEBIT` ⇒ `tx.amount < 0` ; `ANY` ⇒ toujours vrai.
- **Montant** : comparaison sur `ABS(tx.amount)`. `BETWEEN amount_value AND amount_value2` inclusif.
- **Contrepartie** : `tx.counterparty_id = rule.counterparty_id` strict (NULL ≠ NULL).
- **Compte bancaire** : `tx.bank_account_id = rule.bank_account_id`.

Les filtres NULL sont **ignorés** (pas de contrainte).

### 3.4 Intégration dans le pipeline d'import (Plan 1)

Dans `app/services/imports.py`, après l'insertion d'une transaction et avant commit de l'import :

```python
for tx in inserted_transactions:
    categorize_transaction(session, tx)  # mute tx en place si match
categorized_count = sum(1 for tx in inserted_transactions if tx.categorized_by == 'RULE')
```

Le `ImportRecord.audit` JSONB gagne un champ `categorized_count`. La réponse API de l'upload expose ce nouveau compteur.

### 3.5 Seed Alembic

Deux migrations :

1. **`plan2_seed_subcategories`** — insère les ~50 sous-catégories documentées dans la spec §6.1 (ex. *Encaissements → Ventes clients, Subventions, Remboursements* ; *Personnel → Salaires nets, Acomptes* ; *Charges sociales → URSSAF, Retraite, Prévoyance, Mutuelle, Taxe apprentissage* ; *Impôts & taxes → TVA collectée, TVA déductible, IS, CFE* ; *Charges externes → Loyers, Énergie, Télécom, Assurances, Honoraires, Déplacements* ; etc.). Chaque sous-catégorie : `is_system=True`, `parent_category_id` pointe vers la racine de Plan 1, `slug` unique.
2. **`plan2_seed_delubac_rules`** — insère ~30 règles `is_system=True`, `entity_id=NULL` (globales), priorités 1000 à 1290 (pas de 10). Exemples cibles :

| Priorité | Name | Opérateur / Pattern | Catégorie cible |
|---|---|---|---|
| 1000 | URSSAF | `CONTAINS` "URSSAF" | `charges-sociales/urssaf` |
| 1010 | TVA déductible | `CONTAINS` "TVA" + direction `DEBIT` | `impots-taxes/tva-deductible` |
| 1020 | TVA collectée | `CONTAINS` "TVA" + direction `CREDIT` | `impots-taxes/tva-collectee` |
| 1030 | DGFIP | `CONTAINS` "DGFIP" | `impots-taxes/is` |
| 1040 | Salaires (virement SEPA) | `STARTS_WITH` "VIR SEPA SALAIRE" | `personnel/salaires-nets` |
| 1050 | Commission bancaire Delubac | `CONTAINS` "COMM" + `bank_account = Delubac` | `frais-bancaires/commissions` |
| … | … | … | … |

La liste définitive des 30 règles sera construite en phase de plan à partir (a) des transactions réelles déjà importées en Plan 1 via la fixture Delubac et (b) des libellés bancaires français standards.

## 4. API

Toutes les routes sont sous `/api`, protégées par le cookie de session (cf. `app/deps.py`).

| Méthode | Chemin | Rôle | Description |
|---|---|---|---|
| GET | `/rules` | READER | Liste paginée. Query : `entity_id`, `scope=global|entity|all`, `page`, `page_size`. |
| POST | `/rules` | EDITOR | Création. Body : schéma `RuleCreate`. |
| POST | `/rules/preview` | EDITOR | Dry-run. Body : `RuleCreate` (non persisté). Même scope que `/apply`. Réponse : `{matching_count, sample: [...20 tx]}`. |
| PATCH | `/rules/{id}` | EDITOR | Édition. Refus 409 si `is_system` et champs structurants modifiés (peut renommer, pas changer la cible). |
| DELETE | `/rules/{id}` | ADMIN | Refus 409 si `is_system`. |
| POST | `/rules/{id}/apply` | EDITOR | Applique la règle aux tx non-MANUAL de son scope. Pour une règle globale, "scope" = toutes les transactions de toutes les entités auxquelles l'utilisateur a accès (via `UserEntityAccess`). Pour une règle entité, "scope" = transactions des comptes bancaires de cette entité. Réponse : `{updated_count}`. |
| POST | `/rules/reorder` | EDITOR | Body : `[{id, priority}, …]`. Validation : même scope (toutes globales ou toutes d'une même entité). |
| POST | `/rules/from-transactions` | EDITOR | Body : `{transaction_ids: [...]}`. Retourne un `RuleSuggestion` (libellé commun le plus long + direction + compte si unique). Ne persiste rien. |
| GET | `/transactions` | READER | Plan 1 existant + filtre `uncategorized=true` qui ajoute `categorized_by IN (NONE)`. |
| POST | `/transactions/bulk-categorize` | EDITOR | Body : `{transaction_ids: [...], category_id}`. Positionne `categorized_by=MANUAL`. |

**Erreurs structurées** (réutilise `app/errors.py` de Plan 1) :

- `RULE_VALIDATION` (422) — règle vide ou incohérente (ex. `BETWEEN` sans borne sup).
- `RULE_DUPLICATE_PRIORITY` (409) — index unique violé.
- `RULE_SYSTEM_DELETE` / `RULE_SYSTEM_MUTATE` (409) — tentative sur `is_system`.
- `CATEGORY_NOT_FOUND` (404).
- `ENTITY_ACCESS_DENIED` (403) — user sans `UserEntityAccess` sur l'entité de la règle.

## 5. Frontend

### 5.1 Pages

- **`/rules`** — Table des règles, drag-and-drop (`@dnd-kit/sortable`). Filtres : scope (Toutes / Globales / ACREED Consulting / ACREED IA / ACRONOS) + recherche texte. Badge "système" non-cliquable sur les 30 règles seed. Boutons : "Nouvelle règle" (drawer), "Ré-appliquer tout" (ADMIN, lance `recategorize_entity`).
- **`/rules/new`** et **`/rules/{id}/edit`** — Drawer formulaire :
  - Nom
  - Scope (sélecteur entité, ou "Globale")
  - Priorité (auto par défaut = max+10 du scope)
  - Filtre libellé : opérateur + valeur (placeholder montre la normalisation appliquée)
  - Sens : radio `Tous / Crédits / Débits`
  - Montant : opérateur + valeur(s)
  - Contrepartie : autocomplete sur les counterparties de l'entité
  - Compte bancaire : sélecteur filtré par entité
  - Catégorie cible : `CategoryCombobox` (hiérarchique)
  - Boutons : "Aperçu" (appelle `/rules/preview`, affiche les N matches dans un panneau), "Créer" (persist + apply si preview validé), "Annuler"
- **`/transactions`** (existante) — ajout :
  - Filtre "non catégorisées" dans la barre
  - Toolbar multi-sélection : sélecteur `CategoryCombobox` + bouton "Catégoriser N transactions" (bulk manual) + bouton "Créer une règle depuis la sélection" (appelle `/rules/from-transactions` puis ouvre le drawer de `/rules/new` pré-rempli)

### 5.2 Composants nouveaux

- `CategoryCombobox` — autocomplete hiérarchique "Catégorie racine → sous-catégorie". Réutilisable partout. Gère l'affichage du chemin complet dans le résultat sélectionné.
- `RuleForm` — le formulaire du drawer, testé isolément.
- `RulePreviewPanel` — affiche `{matching_count, sample}` avec lien vers chaque tx.
- `SortableRulesTable` — wrapper `@dnd-kit` autour de la table existante.

### 5.3 Clients API (React Query)

- `src/api/rules.ts` — `listRules`, `createRule`, `updateRule`, `deleteRule`, `previewRule`, `applyRule`, `reorderRules`, `suggestRuleFromTransactions`.
- Extension de `src/api/transactions.ts` : `bulkCategorize`, flag `uncategorized` sur `listTransactions`.

## 6. Sécurité & permissions

| Action | READER | EDITOR | ADMIN |
|---|---|---|---|
| Lire règles | OUI | OUI | OUI |
| Créer/éditer/appliquer règle | non | OUI | OUI |
| Supprimer règle non-système | non | non | OUI |
| Supprimer règle système | non | non | NON (refusé par le service) |
| Catégoriser manuellement | non | OUI | OUI |
| Ré-appliquer toutes les règles | non | non | OUI |

Toutes les routes `/rules*` vérifient en plus que l'utilisateur a un `UserEntityAccess` sur `rule.entity_id` quand celle-ci est non-null. Les règles globales sont accessibles à tout utilisateur authentifié.

## 7. Tests (ordre TDD)

1. **`test_model_categorization_rule.py`** — fields, enums, CHECK constraints (au moins un filtre, BETWEEN cohérent), contrainte `is_system` avec `created_by_id=NULL` autorisé.
2. **`test_categorization_engine.py`** — pour chaque opérateur de libellé, chaque combinaison de filtres, normalisation identique, tie-break entité > globale, first-match-wins, exclusion MANUAL.
3. **`test_seed_categories.py`** — les 50 sous-catégories existent, parent correct, slug unique.
4. **`test_seed_rules.py`** — les 30 règles système existent, priorités uniques, pointent vers des catégories valides.
5. **`test_api_rules.py`** — CRUD, preview, apply, reorder, permissions par rôle, refus sur is_system.
6. **`test_api_transactions_bulk.py`** — bulk-categorize, filtre uncategorized, transitions `categorized_by`.
7. **`test_e2e_plan2.py`** — scénario bout-en-bout : import fixture Delubac → auto-catégorisation via règles système → vérif inbox vide pour libellés connus → création d'une règle custom → preview → apply → recompte.

Frontend : tests Vitest ciblés sur `RuleForm` (validation), `CategoryCombobox` (navigation clavier), `SortableRulesTable` (drag-and-drop émis → appel API).

## 8. Migrations Alembic

| Révision | Description |
|---|---|
| `plan2_rule_and_tx_columns` | Crée `categorization_rule` + enums + ajoute `transaction.categorized_by`, `transaction.categorization_rule_id`, `transaction.normalized_label` (avec backfill) |
| `plan2_seed_subcategories` | Insère les ~50 sous-catégories |
| `plan2_seed_delubac_rules` | Insère les ~30 règles système globales |

Chaque migration contient sa `downgrade()` symétrique.

## 9. Hors scope (reportés)

- Mécanismes d'apprentissage statistique et de suggestion IA.
- Import/export JSON des règles.
- Règles sur regex.
- Règles déclenchées par autre chose que l'import (ex. edit d'une tx).
- UI de backfill global avec barre de progression asynchrone (le `recategorize_entity` est synchrone en Plan 2).
- Distinction inter-entité automatique des virements (ACREED Consulting ↔ ACRONOS) — Plan 3+.

## 10. Critères de fin

- Les 3 migrations appliquent et rollback proprement sur DB de test.
- Les 30 règles seed matchent ≥ 70 % des transactions de la fixture Delubac après import.
- Toute la suite backend passe (existant Plan 0/1 + nouveaux tests Plan 2).
- Tests frontend Vitest passent.
- Déploiement dev validé à la main : créer une règle, voir le preview, apply, vérifier que la page Transactions reflète la catégorisation, manuel override ne re-catégorise pas.
- Revue de plan non obligatoire pour Plan 2 (obligatoire pour 1, 4, 6).
- Branche `plan-2-categorization` prête à merger sur `main`, tag `plan-2-done`.
