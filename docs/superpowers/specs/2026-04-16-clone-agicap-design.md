# Spécification de conception — Clone Agicap (outil local de gestion de trésorerie)

- **Date** : 2026-04-16
- **Statut** : Version 1.0 — validée par l'utilisateur à l'issue du brainstorming
- **Auteur** : design collaboratif (Tristan + assistant)

---

## 1. Contexte et objectifs

### 1.1. Contexte

Le dirigeant d'un groupe composé d'une **holding** et de **plusieurs filiales** (dont SAS ACREED CONSULTING RJ, banque Delubac) souhaite un outil de suivi et de gestion de trésorerie équivalent fonctionnellement à **Agicap** (leader du marché français), mais **auto-hébergé** sur son propre serveur et sans connexion à une API bancaire (trop coûteuse à l'échelle PME).

La source de données principale est **l'import manuel de relevés bancaires PDF** (ou export CSV), à une fréquence hebdomadaire ou mensuelle selon les besoins.

### 1.2. Objectifs

- Suivre en temps réel la trésorerie des différentes entités du groupe
- Produire un prévisionnel fiable à 30 / 90 / 180 / 365 jours
- Catégoriser automatiquement les opérations bancaires
- Alerter sur les situations critiques (seuils, échéances, anomalies)
- Garder **la totalité des données chez l'utilisateur** (aucune dépendance SaaS externe)
- Offrir une expérience d'utilisation fluide pour 4 utilisateurs (toi + 3 personnes de confiance)

### 1.3. Critères de succès

- Un import PDF Delubac fonctionnel, avec > 95 % de transactions correctement extraites sans intervention manuelle
- Après 2 mois d'usage, > 90 % des nouvelles transactions se catégorisent automatiquement (grâce à l'apprentissage des règles)
- Le prévisionnel à 30 jours doit avoir une erreur inférieure à 15 % sur des données historiques
- Déploiement Docker en moins de 15 minutes sur une VM Azure vierge
- Interface entièrement en français

---

## 2. Périmètre fonctionnel (MVP)

Le MVP couvre **5 modules** :

1. **Import & analyseurs (parsers) PDF/CSV** — avec un analyseur Delubac livré et une architecture extensible pour d'autres banques
2. **Catégorisation** — arborescence de catégories pré-configurée + règles automatiques + apprentissage
3. **Tableau de bord** — vue par entité ou consolidée, indicateurs clés, graphiques, tables analytiques
4. **Prévisionnel** — récurrences, opérations planifiées, scénarios (réaliste/optimiste/pessimiste + personnalisés)
5. **Alertes** — seuils de trésorerie, échéances, anomalies, avec canal in-app et email

### Hors-périmètre MVP (pour versions futures)

- Catégorisation par IA (modèle de langage) — on reste sur des règles explicites, auditables
- Rapprochement bancaire fin (pointage coche par coche vs factures comptables)
- OCR sur relevés scannés (images)
- Élimination automatique des flux intercompagnies (on se limite au tag manuel)
- Budgets prévisionnels vs réalisés par catégorie
- Modèles prédictifs d'apprentissage automatique
- Intégration CRM / pipeline commercial en amont
- Gestion multi-devises (toutes les entités sont en EUR pour l'instant)
- Interface mobile native (l'interface web sera simplement responsive)
- Permissions granulaires par fonction (on se limite aux rôles Administrateur / Lecture avec restriction d'accès par entité)

---

## 3. Architecture globale

### 3.1. Vue d'ensemble des composants

L'application tourne en Docker sur une VM Azure Linux (Ubuntu recommandée). 4 services orchestrés par `docker-compose` :

| Service | Rôle | Image de base |
|---|---|---|
| `reverse-proxy` | Routage HTTPS, certificat Let's Encrypt automatique | `caddy:latest` |
| `frontend` | Application React servie en statique via nginx | `nginx:alpine` (build multi-stage) |
| `backend` | API REST FastAPI + analyseurs PDF + logique métier | Image Python 3.12 personnalisée |
| `db` | Base PostgreSQL 16 avec volume persistant | `postgres:16-alpine` |

### 3.2. Flux principaux

**Import d'un relevé PDF** :

1. L'utilisateur téléverse un PDF depuis le frontend
2. Le frontend l'envoie à l'API (`POST /api/imports`)
3. Le backend identifie la banque (détection automatique ou sélection manuelle), appelle l'analyseur correspondant
4. L'analyseur retourne une liste structurée de transactions
5. Le backend détecte les doublons, applique les règles de catégorisation automatique, crée les contreparties inconnues, insère en base dans une transaction SQL atomique
6. Le frontend affiche le résumé (nouvelles transactions, doublons ignorés, transactions à catégoriser manuellement)

**Consultation du tableau de bord** :

1. L'utilisateur choisit une entité (ou "Groupe consolidé") et une période
2. Le frontend requête l'API (`GET /api/dashboard?entity_id=X&from=...&to=...`)
3. Le backend agrège les données, applique les filtres, calcule les indicateurs clés et les séries temporelles
4. Le frontend affiche les graphiques avec **Recharts**

### 3.3. Choix d'architecture clés

- **Monolithe modulaire** (pas de microservices) : simple à déployer, largement suffisant pour 4 utilisateurs et quelques milliers de transactions par mois
- **Analyseurs sous forme de plugins** : chaque banque = un fichier Python indépendant implémentant l'interface `BaseParser`. Ajout d'une nouvelle banque = ajout d'un fichier, aucun impact sur le reste
- **Pas de broker de messages** pour le MVP : un import PDF s'exécute en synchrone en quelques secondes. Si le volume grandit, on pourra passer à Celery + Redis
- **Caddy plutôt que Traefik** : configuration plus simple (un seul fichier `Caddyfile`), HTTPS Let's Encrypt automatique sans paramétrage
- **Migrations de base avec Alembic** : évolution du schéma sans perte de données

### 3.4. Diagramme simplifié

```
                        ┌───────────────────────────────┐
                        │     VM Azure (Docker host)     │
                        │                                │
  🧑 4 utilisateurs     │  ┌──────────┐    ┌──────────┐  │
  (holding + filiales)──┼─▶│  Caddy   │───▶│ Frontend │  │
  via HTTPS             │  │(reverse) │    │  React   │  │
                        │  └────┬─────┘    └──────────┘  │
                        │       │                        │
                        │       ▼                        │
                        │  ┌──────────┐    ┌──────────┐  │
                        │  │ Backend  │───▶│   DB     │  │
                        │  │ FastAPI  │    │ Postgres │  │
                        │  └────┬─────┘    └──────────┘  │
                        │       │                        │
                        │       ▼                        │
                        │  ┌──────────────────────────┐  │
                        │  │     Analyseurs PDF       │  │
                        │  │ - Delubac (MVP)          │  │
                        │  │ - (autres à venir)       │  │
                        │  └──────────────────────────┘  │
                        └───────────────────────────────┘
```

---

## 4. Modèle de données

### 4.1. Entités principales

| Table | Rôle |
|---|---|
| `users` | Les utilisateurs (email, mot de passe hashé Argon2, rôle global Administrateur/Lecture) |
| `entities` | Les sociétés du groupe (holding, filiales). Arborescence parent/enfant via `parent_entity_id` |
| `user_entity_access` | Liaison N-N : quel utilisateur a accès à quelle entité (pour les restrictions fines) |
| `bank_accounts` | Comptes bancaires (rattachés à une entité), IBAN, établissement, devise |
| `transactions` | Table centrale : toutes les opérations bancaires importées |
| `categories` | Arborescence hiérarchique (catégorie > sous-catégorie), partagée par toutes les entités |
| `category_rules` | Règles de catégorisation automatique |
| `counterparties` | Contreparties (fournisseurs, salariés, clients) normalisées |
| `tags` + `transaction_tags` | Tags libres attachés aux transactions (liaison N-N) |
| `imports` | Historique des imports (fichier, date, nombre de transactions, utilisateur) |
| `recurring_templates` | Modèles d'opérations récurrentes pour le prévisionnel |
| `scheduled_transactions` | Opérations prévisionnelles ponctuelles |
| `scenarios` | Scénarios de prévisionnel |
| `alerts` | Configurations d'alertes |
| `alert_events` | Historique des déclenchements d'alertes |

### 4.2. Relations clés

```
User ──< user_entity_access >── Entity (holding/filiale)
                                    │
                                    ├── BankAccount ── Transaction ──< Tag
                                    │                       │
                                    │                       ├── Category
                                    │                       ├── Counterparty
                                    │                       └── Import
                                    │
                                    ├── RecurringTemplate
                                    ├── ScheduledTransaction
                                    ├── Scenario
                                    └── Alert
```

### 4.3. Décisions structurantes

**Arborescence des entités** : la holding est la racine, les filiales ont la holding comme `parent_entity_id`. Cela permet la vue consolidée : "toutes les transactions des descendants de la Holding".

**Transactions fidèles au relevé** : chaque ligne du PDF est un record, y compris les commissions et TVA bancaires. Une colonne `parent_transaction_id` (auto-référence) permet de grouper visuellement les commissions SEPA sous leur virement principal. En base, les 3 lignes coexistent → le solde reste mathématiquement juste, le rapprochement bancaire reste possible. En interface, on affiche groupé par défaut avec un toggle "voir les lignes détaillées".

**Règle d'agrégation statistique (anti double-comptage)** : tous les calculs statistiques (totaux du tableau de bord, graphiques donuts par catégorie, top contreparties, prévisionnel) se font **sur les lignes de niveau le plus bas** (feuilles) : toutes les lignes sans `parent_transaction_id` + toutes les lignes enfants. Autrement dit, on somme les enfants mais jamais le parent avec ses enfants. La transaction parent n'est qu'un groupement visuel dans l'interface ; sa valeur `amount` est la somme des enfants pour les virements avec commission. La distinction est garantie par une colonne `is_aggregation_parent` calculée : `TRUE` si la transaction a des enfants, auquel cas elle est exclue des sommations.

**Flux intercompagnies simples** : deux colonnes sur `transactions` :
- `is_intercompany` (booléen)
- `counter_entity_id` (FK optionnelle vers `entities`)

Quand un virement entre deux entités du groupe est repéré, l'utilisateur peut le tagguer manuellement. En vue consolidée, une case à cocher "Exclure les flux intergroupe" filtrera ces transactions.

**Catégories globales au groupe** : partagées entre toutes les entités pour garantir la cohérence de reporting. Un jeu de catégories pré-configuré adapté au business (société de conseil/prestation en RJ) est créé à l'installation. Tout est modifiable.

**Contreparties normalisées** : le parseur extrait le nom de la contrepartie depuis les libellés (ex. "VIR SEPA NIZAR MOUADDEB" → contrepartie "NIZAR MOUADDEB"). Si une contrepartie existe déjà (match exact, ou match **token-set ratio ≥ 90 %** via la bibliothèque `rapidfuzz`), elle est liée. Sinon elle est créée avec un statut `pending`.

**Statut `pending` des contreparties auto-créées** : pour éviter de polluer les stats avec des milliers de contreparties éphémères issues de libellés à usage unique, toute contrepartie créée automatiquement passe d'abord par un statut `pending`. Une page "Contreparties à valider" permet à l'administrateur de :
- Valider (statut `active`) une contrepartie pour l'utiliser dans les règles et stats
- Fusionner avec une contrepartie existante (toutes les transactions sont rebranchées)
- Ignorer (statut `ignored`, la contrepartie reste associée aux transactions mais n'apparaît plus dans les listes de sélection)

Les statistiques du tableau de bord incluent les contreparties `active` par défaut ; un toggle permet d'inclure les `pending`.

**Audit léger** : colonnes `created_at` / `updated_at` / `created_by` / `updated_by` sur les tables sensibles (transactions, catégories, règles). Pas de versioning complet pour le MVP.

---

## 5. Module Import & Analyseurs

### 5.1. Interface commune

Tous les analyseurs implémentent la même interface :

```python
class BaseParser(ABC):
    bank_name: str          # "Delubac", "Qonto", etc.
    bank_code: str          # "delubac", "qonto", etc.

    @abstractmethod
    def detect(self, pdf_bytes: bytes) -> bool:
        """Retourne True si ce PDF vient de cette banque."""

    @abstractmethod
    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        """Extrait les transactions."""
        # Retourne : account_number, iban, period_start, period_end,
        #            opening_balance, closing_balance, transactions[]
```

Un registre `parser_registry` scanne automatiquement le dossier `backend/parsers/` au démarrage. Ajout d'une nouvelle banque = déposer un fichier Python conforme dans ce dossier.

### 5.2. Flux d'import détaillé

1. Téléversement du PDF via le frontend
2. Sauvegarde du fichier dans un volume Docker dédié (pour conservation d'audit)
3. Détection automatique de la banque en appelant `.detect()` sur chaque analyseur enregistré
   - Si aucun ne matche → l'interface propose à l'utilisateur de choisir manuellement
4. Appel de `.parse()` → liste brute des transactions
5. **Normalisation** :
   - Dates en ISO 8601
   - Montants : "25.204,95" → `25204.95`
   - Libellés : correction de l'encoding (cas Delubac : `�` → `é`)
   - Extraction de la contrepartie depuis le libellé (heuristiques par analyseur)
6. **Fusion des commissions SEPA** : détection des trios (virement + `COMMISSION VIR SEPA` + `TVA VIR SEPA`) et rattachement via `parent_transaction_id`
7. **Détection des doublons** : clé de déduplication = `bank_account_id + operation_date + amount + normalized_label`. Les doublons sont ignorés
8. **Catégorisation automatique** : application des `CategoryRule` actives dans l'ordre de priorité. Les transactions non matchées restent "Non catégorisées"
9. **Détection des contreparties** : match exact ou fuzzy ≥ 90 %, sinon création
10. **Insertion atomique** en base (transaction SQL)
11. **Résumé d'import** affiché à l'utilisateur :
    - Nombre de transactions importées
    - Nombre de doublons ignorés
    - Nombre catégorisées automatiquement
    - Nombre à catégoriser manuellement

### 5.3. Analyseur Delubac (MVP)

Particularités identifiées :
- Colonnes : Date opération / Date valeur / Libellé / Débit / Crédit
- Encodage latin-1 mal converti en UTF-8 → caractères accentués corrompus (fix dédié)
- Lignes multi-banques : commissions et TVA en lignes séparées, à fusionner
- Totaux intermédiaires sur chaque page à ignorer
- En-têtes de page techniques à filtrer (`RG SDC : X`, etc.)

### 5.4. Import Excel / CSV

En complément du PDF, un format CSV standard est supporté :
- Colonnes attendues : `date_operation, date_valeur, libelle, debit, credit, solde` (solde optionnel)
- Mapping des colonnes à la volée via l'interface si les noms diffèrent
- Même pipeline de normalisation / doublons / catégorisation

### 5.5. Gestion des erreurs

- Si le parsing échoue sur une ligne, on passe à la suivante et on liste les lignes problématiques dans le résumé
- Si le parsing échoue complètement, transaction SQL annulée, rien inséré
- Aperçu de l'import avant validation finale (l'utilisateur peut annuler avant insertion)

### 5.6. Limites de taille et protections

Pour éviter toute surcharge du serveur par un fichier mal formé ou volumineux, les limites suivantes sont appliquées à l'upload :

| Limite | Valeur par défaut | Comportement si dépassée |
|---|---|---|
| Taille du fichier | 20 Mo | Réponse HTTP 413, message utilisateur explicite |
| Nombre de pages PDF | 500 | Même traitement que ci-dessus |
| Nombre de transactions par import | 10 000 | Import refusé, invitation à découper le fichier |
| Durée maximale du parsing | 60 secondes | Timeout, rollback SQL, message d'erreur |
| Taux d'upload par utilisateur | 10 imports / 10 minutes | Rate limiter (HTTP 429) |

Toutes ces valeurs sont configurables dans le fichier `.env`.

### 5.7. Amélioration de la clé de déduplication

La clé de déduplication simple `bank_account_id + operation_date + amount + normalized_label` n'est pas suffisante : deux prélèvements URSSAF identiques le même jour sont légitimes. La clé effective est donc :

```
dedup_key = hash(
    bank_account_id,
    operation_date,
    value_date,
    amount,
    normalized_label,
    statement_row_index    # position de la ligne dans le relevé source
)
```

Le `statement_row_index` garantit que deux lignes identiques dans le même relevé ne s'écrasent pas. Si la banque fournit une référence unique (ex. numéro de créance, référence SEPA), elle est ajoutée au hash pour fiabiliser encore.

Pour gérer les **chevauchements inter-relevés** (réimport d'une période couverte par un relevé précédent), la détection se base sur `(bank_account_id, operation_date, value_date, amount, normalized_label)` sans l'index de ligne. Compromis : les éventuelles lignes identiques répétées sont considérées comme des doublons ; l'utilisateur peut forcer l'insertion via un bouton "importer malgré tout" avec confirmation.

---

## 6. Module Catégorisation

### 6.1. Arborescence pré-configurée

Créée automatiquement à l'installation :

- **💰 Encaissements** : Ventes clients / Affacturage BNP Paribas Factor / Remboursements créances (Dailly) / Restitutions retenue de garantie / Autres
- **💸 Décaissements — Personnel** : Salaires / Avances sur salaire / Indemnités kilométriques / Notes de frais / Autres
- **💸 Décaissements — Sous-traitants** (sous-catégories créées dynamiquement)
- **💸 Décaissements — Fournisseurs** (sous-catégories créées dynamiquement)
- **🏛️ Charges sociales & taxes** : URSSAF / Retraite / Mutuelle / TVA / IS / PAS-DSN / Autres
- **🏦 Frais bancaires** : Commissions virements SEPA / TVA sur commissions / Intérêts de retard / Commissions créances non réglées / Cotisations cartes / Arrêtés de compte / Retraits DAB
- **⚖️ Honoraires juridiques** : Mandataire judiciaire / Avocats / Autres conseils
- **🔁 Flux intergroupe** : Remontée de trésorerie / Prêts intragroupe / Management fees / Autres
- **❓ Non catégorisées** (défaut)

Tout est modifiable par l'utilisateur.

### 6.2. Les trois mécanismes

**Mécanisme 1 — Règles automatiques (`CategoryRule`)**

Condition sur le libellé + catégorie cible. Opérateurs supportés :
- `contient` (insensible à la casse)
- `commence par`
- `finit par`
- `correspond au regex`
- combiné avec condition optionnelle sur le montant (`> X`, `< X`, `entre X et Y`)

Environ 30 règles pré-installées couvrant les patterns identifiés dans le relevé Delubac exemple (URSSAF, Malakoff, DGFIP, BNP Factor, commissions SEPA, etc.).

**Mécanisme 2 — Suggestion basée sur l'historique**

Quand une transaction reste non catégorisée, on cherche dans l'historique une transaction très similaire (même contrepartie, même fourchette de montant ±20 %, libellé Levenshtein-proche). Si trouvée, sa catégorie est suggérée à l'utilisateur (validation en 1 clic).

**Mécanisme 3 — Conversion en règle (apprentissage)**

Après une catégorisation manuelle, l'interface propose : *"Créer une règle : tout libellé contenant `DKV EURO SERVICE` → Fournisseurs > DKV ?"*. L'utilisateur peut accepter, refuser, ou ajuster la condition.

### 6.3. Priorités des règles

Les règles ont un champ `priority` (entier). La 1ère règle qui matche gagne. L'interface permet de réordonner par glisser-déposer.

### 6.4. Import / export des règles

Les règles sont exportables et importables en JSON : utile pour sauvegarder une configuration, la répliquer, ou partager entre instances.

---

## 7. Module Prévisionnel

### 7.1. Principe

La projection du solde dans le futur = solde actuel + somme des 3 sources de flux prévus :

1. **Transactions récurrentes** (templates)
2. **Transactions planifiées ponctuelles** (opérations one-shot)
3. **Estimation basée sur l'historique** (moyenne des 6 derniers mois, par catégorie, activable par catégorie)

### 7.2. Modèles récurrents (`recurring_templates`)

Champs :
- Libellé
- Catégorie, contrepartie
- Entité, compte bancaire
- Montant : fixe OU moyenne glissante sur 3 / 6 / 12 derniers mois
- Fréquence : mensuelle / trimestrielle / annuelle / personnalisée (tous les N jours)
- Jour du mois ou date précise
- Date de début, date de fin (optionnelle)
- Actif / inactif

**Détection automatique (fonctionnalité bonus, pousée en fin de MVP ou reportée en v2)** : au premier lancement, l'outil analyse l'historique et propose des templates pour les patterns récurrents détectés (URSSAF mensuel, salaires, etc.). Validation en 1 clic. Cette fonctionnalité est non-bloquante pour la sortie du MVP ; si le planning se tend, elle bascule en v2. La création manuelle de modèles récurrents reste pleinement disponible.

### 7.3. Opérations planifiées (`scheduled_transactions`)

Pour les événements ponctuels :
- Description, catégorie, contrepartie, entité, compte
- Montant (en encaissement ou décaissement)
- Date prévue, avec marge optionnelle ± N jours
- Niveau de certitude : `Confirmé` / `Probable` / `Hypothétique`

### 7.4. Scénarios

3 scénarios par défaut + scénarios personnalisés :

| Scénario | Ajustements |
|---|---|
| 🟢 Réaliste | Aucun. Templates et planifiées aux dates prévues |
| 🔵 Optimiste | Encaissements +10 % et 7 jours plus tôt. Décaissements normaux |
| 🔴 Pessimiste | Encaissements probables/hypothétiques −20 %, +15 jours de retard. Événement exceptionnel ajoutable |

**Algorithme d'application d'un scénario** (pseudocode) :

```
projection = []
pour chaque jour J de aujourd'hui à (aujourd'hui + horizon) :
    flux_jour = 0

    # 1. Templates récurrents
    pour chaque template actif T :
        si T doit se déclencher à J (selon fréquence/jour) :
            montant = T.montant_effectif()   # fixe ou moyenne glissante
            si scenario a un ajustement sur la catégorie de T :
                appliquer le % et/ou le décalage de date
            flux_jour += montant * T.signe

    # 2. Planifiées ponctuelles
    pour chaque planifiée P :
        date_effective = P.date_prevue
        si scenario.decalage_encaissements et P est un encaissement :
            date_effective += scenario.decalage_encaissements  # en jours
        si scenario exclut les planifiées "Hypothétiques" et P.certitude == Hypothétique :
            continuer
        montant = P.montant
        si scenario a un ajustement sur encaissements/décaissements :
            appliquer le %
        si date_effective == J :
            flux_jour += montant * P.signe

    # 3. Estimation historique (pour catégories sans template)
    pour chaque catégorie C sans template et activée pour l'estimation :
        moyenne_mensuelle = moyenne(derniers_6_mois, C)
        part_journaliere = moyenne_mensuelle / 30
        si scenario a un ajustement sur C :
            appliquer le %
        flux_jour += part_journaliere * C.signe

    # 4. Événements exceptionnels du scénario
    pour chaque événement E du scénario :
        si E.date == J :
            flux_jour += E.montant

    solde_J = solde_J_moins_1 + flux_jour
    projection.append({date: J, solde: solde_J, flux: flux_jour})
```

**Règles de compounding (non cumul des effets)** :

- Les ajustements de scénario s'appliquent **une seule fois** sur un flux donné : si un flux provient d'une planifiée, le scénario n'applique pas en plus l'ajustement de sa catégorie (sinon double effet).
- Les ajustements de date (ex. +15 jours) ne repoussent **pas au-delà de l'horizon** : si un encaissement prévu au jour H−10 devient jour H+5 (hors horizon), il est exclu de cette projection.
- Les événements exceptionnels du scénario sont **additifs** : ils ne déplacent ni ne remplacent rien.

**Exemple chiffré (scénario Pessimiste, horizon 30 jours)** :

- Encaissement planifié Probable : 30 000 € au 15 mai → devient −20 % × 30 000 € = **24 000 € au 30 mai** (+15 jours)
- Template "URSSAF" mensuel (catégorie Charges sociales) : 10 012 € au 17 mai → inchangé (aucun ajustement pessimiste sur décaissements)
- Estimation historique "Frais bancaires" : 400 €/mois ≈ 13 €/jour → inchangé
- Événement exceptionnel ajouté : "Coup dur" 5 000 € au 20 mai → −5 000 € au 20 mai

Paramètres ajustables par l'utilisateur :
- % de variation encaissements / décaissements
- Délai de retard moyen (jours)
- Inclusion/exclusion des planifiées "Hypothétiques"
- Ajout d'événements exceptionnels ponctuels

### 7.5. Visualisation

**Courbe de projection** sur l'horizon choisi (30 / 90 / 180 / 365 jours) :
- Ligne pleine sur le passé, pointillée sur le futur
- 3 courbes superposées : réaliste / optimiste / pessimiste
- Jalons importants marqués (grosses échéances)

**Indicateurs clés** :
- **Autonomie de trésorerie** (runway) : date estimée d'atteinte du 0 € dans le scénario pessimiste
- **Solde minimum prévisionnel** : valeur et date
- **Solde maximum prévisionnel** : valeur et date
- **Flux de trésorerie net prévu** sur l'horizon

**Table mensuelle** : pour chaque mois à venir, encaissements / décaissements prévus, solde fin de mois, variation.

### 7.6. Vue consolidée et par entité

Le prévisionnel fonctionne à tous les niveaux : compte, entité, groupe (avec option d'exclusion des intercos tagués).

---

## 8. Module Tableau de bord & Alertes

### 8.1. Tableau de bord principal

**Sélecteur contextuel en haut de page** : Entité / Période / Scénario prévisionnel. Tout le reste de la page se recalcule en temps réel.

**Rangée 1 — Indicateurs clés (cartes)** :
- Solde actuel (+ variation vs mois dernier)
- Flux de trésorerie sur la période (encaissements − décaissements)
- Dépenses mensuelles moyennes (burn rate)
- Autonomie de trésorerie (runway)

**Rangée 2 — Graphiques temporels** :
- Évolution du solde : réel (trait plein) + prévisionnel (pointillé, couleur par scénario), avec bande optimiste/pessimiste
- Encaissements vs décaissements par mois (barres), avec courbe du solde fin de mois superposée

**Rangée 3 — Répartitions** :
- Décaissements par catégorie (donut)
- Encaissements par catégorie / contrepartie (donut)
- Clic sur segment → détail (drill-down) des transactions

**Rangée 4 — Tables analytiques** :
- Top 10 contreparties sur la période
- Prochaines échéances à 7 / 30 jours
- Transactions à catégoriser (badge compteur + raccourci vers la boîte de réception de catégorisation)

### 8.2. Page "Transactions"

Liste détaillée façon tableur :
- Filtres avancés : période, catégorie, contrepartie, montant min/max, statut, entité, compte, tags
- Recherche plein texte dans les libellés
- Actions en masse : recatégoriser, ajouter tag, marquer interco
- Tri sur toutes les colonnes
- Export CSV / Excel de la vue filtrée

### 8.3. Vue consolidée vs par entité

**Groupe consolidé** : indicateurs agrégés sur toutes les entités, ligne "Répartition par entité" en plus, case à cocher "Exclure flux intergroupe".

**Entité unique** : tout filtré, flux intercos visibles avec leur tag.

### 8.4. Alertes

**Types d'alertes configurables** :
1. Seuil de trésorerie : solde prévisionnel sous X € dans les N jours
2. Échéance importante à venir (> X € dans N jours)
3. Transaction inhabituelle : montant > X € détecté à l'import
4. Nouvelle contrepartie inconnue
5. Import manquant : aucun import depuis N jours
6. Découvert prévisionnel : le scénario pessimiste passe en négatif
7. Accumulation de transactions non catégorisées (> N)

Chaque utilisateur configure ses propres alertes.

**Canaux** :
- In-app : cloche en haut à droite avec badge
- Email : notification immédiate (sévère) ou digest quotidien

**Centre d'alertes** : page listant actives / résolues / historique. Configuration de chaque alerte (seuil, canal, fréquence).

---

## 9. Authentification, droits & déploiement

### 9.1. Authentification

- Email + mot de passe, hashage **Argon2id**
- Cookie de session HttpOnly, SameSite=Lax, expiration glissante **8 heures par défaut** (configurable dans `.env`, le paramétrage par défaut visait initialement 30 minutes mais c'est trop agressif pour un usage professionnel quotidien)
- Politique de mot de passe : 12 caractères minimum, vérification contre la base HIBP (locale, fichier de hashes)
- Verrouillage temporaire après 5 tentatives échouées en 10 minutes
- Protections : CSRF (token double submit), XSS (React), injection SQL (SQLAlchemy paramétré)

**Flux de réinitialisation de mot de passe** :

1. L'utilisateur saisit son email sur la page "Mot de passe oublié"
2. Si l'email existe, un token aléatoire cryptographiquement fort (32 octets) est généré, son hash est stocké en base avec une durée de vie de **60 minutes**
3. Un email est envoyé à l'utilisateur contenant le lien `https://<domaine>/reinit-mot-de-passe?token=<token>`
4. Le clic ouvre une page de saisie du nouveau mot de passe (contrôles identiques à l'inscription)
5. À la soumission, le token est invalidé immédiatement, tous les autres tokens actifs de l'utilisateur aussi
6. Toutes les sessions actives de l'utilisateur sont invalidées pour forcer la reconnexion
7. Un email de confirmation "Votre mot de passe a été modifié" est envoyé

Pour prévenir l'énumération d'emails, la réponse à la soumission du formulaire est toujours la même (message générique), qu'un compte existe ou non.

**Réinitialisation par un administrateur** : l'admin peut déclencher un reset sans email ; un mot de passe temporaire à usage unique est affiché (copier-coller manuel à l'utilisateur), avec obligation de changement à la première connexion.

Préparé pour la suite (hors MVP) : 2FA TOTP, SSO Microsoft (pertinent sur Azure).

### 9.1.bis Configuration SMTP (requise par l'auth et les alertes)

Les emails (réinitialisation mot de passe + alertes, cf. §8.4) nécessitent une configuration SMTP. Variables dans `.env` :

```
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=tresorerie@acreed-consulting.fr
SMTP_FROM_NAME=Outil de trésorerie
SMTP_USE_TLS=true
```

Recommandations : utiliser un service transactionnel (Azure Communication Services Email, SendGrid, Mailjet) ou le SMTP interne de l'organisation. Un test d'envoi est disponible dans la page Administration (bouton "Envoyer un email de test").

Si la configuration SMTP est absente ou invalide, les alertes in-app continuent de fonctionner ; seule la réinitialisation de mot de passe en self-service est indisponible (l'admin reste capable de réinitialiser via l'interface).

### 9.2. Rôles et droits

**Rôles globaux** :

| Rôle | Permissions |
|---|---|
| Administrateur | Tout : import, catégorisation, règles, gestion utilisateurs, entités, alertes globales, sauvegardes |
| Lecture | Consulter, exporter, configurer ses propres alertes. Ne peut pas modifier |

**Restriction par entité** (table `user_entity_access`) : un utilisateur peut être limité à certaines entités. Si accès à une seule, le sélecteur d'entité est verrouillé.

### 9.3. Page "Administration"

Accessible aux administrateurs :
- Gestion des utilisateurs (créer, désactiver, réinitialiser mot de passe, journal connexions)
- Gestion des entités (arborescence)
- Gestion des comptes bancaires
- Gestion des catégories (arborescence, import/export JSON)
- Gestion des règles de catégorisation
- Journal d'activité (qui, quoi, quand)
- Sauvegardes (manuelles et automatiques)

### 9.4. Sauvegardes

- Dump PostgreSQL quotidien automatique à 3h, chiffré en **AES-256-GCM**, stocké dans un volume dédié
- Rétention : 30 jours glissants + 1 par mois sur 12 mois
- Export manuel à la demande (fichier SQL chiffré téléchargeable)
- Restauration documentée (procédure CLI, pas d'interface graphique au MVP)
- Complémentaire : snapshot du disque VM via outils natifs Azure

**Gestion de la clé de chiffrement des sauvegardes** :

La clé de chiffrement ne doit **pas** vivre sur la même VM que les sauvegardes (sinon le chiffrement est cosmétique). Deux modes supportés :

- **Mode recommandé (Azure Key Vault)** : la clé est stockée dans Azure Key Vault de l'organisation. Le conteneur backend y accède via Managed Identity de la VM. La clé n'est jamais persistée sur disque ; elle est chargée en mémoire à chaque opération de chiffrement/déchiffrement.
- **Mode autonome (passphrase opérateur)** : la passphrase est fournie à chaque restauration par l'opérateur humain (variable d'environnement temporaire au moment de la commande). Les sauvegardes automatiques utilisent une passphrase stockée **hors** de la VM (ex. gestionnaire de mots de passe de l'administrateur) et injectée au boot initial.

La procédure de restauration documentée (dans `docs/operations/restauration.md`, à écrire pendant l'implémentation) inclut : récupération de la clé, déchiffrement, import SQL, vérification d'intégrité, tests de cohérence. Une restauration complète doit être testée lors du déploiement initial et consignée au journal.

### 9.5. Déploiement

Sur VM Azure Ubuntu :

```
1. Installer Docker + Docker Compose
2. Cloner le repo Git
3. Configurer le fichier .env (mot de passe DB, domaine, email Let's Encrypt)
4. docker compose up -d
   → Caddy obtient automatiquement le certificat HTTPS
5. Première connexion : page d'initialisation → création du compte admin
6. Création des entités et comptes bancaires
7. Premier import de relevé
```

**Mise à jour** :
```
git pull
docker compose pull
docker compose up -d --build
```

### 9.6. Sécurité complémentaire

- HTTPS obligatoire (Let's Encrypt)
- En-têtes : HSTS, CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy
- Rate limiting sur `/login` et `/imports`
- Logs applicatifs structurés (JSON) avec rotation
- Secrets dans `.env` (non commité)
- Base de données accessible uniquement sur le réseau Docker interne

### 9.7. Observabilité

Pour qu'un administrateur puisse diagnostiquer un dysfonctionnement à distance sans accès direct à la machine :

**Endpoints de santé** (non authentifiés, exposés uniquement sur le réseau Docker interne sauf `/healthz`) :

| Endpoint | Objectif | Codes HTTP |
|---|---|---|
| `GET /healthz` | Preuve de vie basique (l'API répond) | 200 OK |
| `GET /readyz` | Prêt à servir du trafic (DB accessible, migrations appliquées) | 200 ou 503 |
| `GET /metrics` | Métriques au format Prometheus (durée requêtes, erreurs, imports) | 200 OK |

**Schéma structuré des logs d'erreur** (JSON, 1 ligne par événement) :

```json
{
  "timestamp": "2026-04-16T14:23:01.234Z",
  "level": "ERROR",
  "logger": "import.delubac",
  "trace_id": "c1a2...",
  "user_id": 42,
  "entity_id": 3,
  "event": "parser_failed",
  "error_type": "InvalidPdfStructureError",
  "message": "Colonnes attendues introuvables page 2",
  "context": {...}
}
```

Les logs passent par un volume Docker monté, avec rotation quotidienne et rétention 30 jours.

**Suivi des erreurs (optionnel)** : intégration Sentry (ou équivalent auto-hébergé type GlitchTip) désactivée par défaut, activable via `SENTRY_DSN` dans `.env`. Recommandé pour détecter les erreurs non remontées.

**Dashboard de supervision (optionnel)** : le port Prometheus peut être scrapé par un Grafana existant pour visualiser les métriques. Pas de stack monitoring dédiée livrée avec le MVP.

---

## 10. Stack technique retenue

| Couche | Technologie |
|---|---|
| Langage backend | Python 3.12 |
| Framework backend | FastAPI |
| ORM | SQLAlchemy 2.x |
| Migrations DB | Alembic |
| Base de données | PostgreSQL 16 |
| Analyse (parsing) PDF | pdfplumber |
| Hashage mots de passe | Argon2-cffi |
| Tests backend | pytest + pytest-asyncio |
| Langage frontend | TypeScript |
| Framework frontend | React 18 + Vite |
| Graphiques | Recharts |
| Tables | TanStack Table |
| Composants UI | shadcn/ui (Radix + Tailwind) |
| Formulaires | React Hook Form + Zod |
| Gestion d'état | TanStack Query (serveur) + Zustand (client léger) |
| Tests frontend | Vitest + Testing Library |
| Reverse proxy | Caddy |
| Orchestration | Docker Compose |
| CI (optionnel) | GitHub Actions |

---

## 11. Terminologie française (glossaire normatif)

L'interface et la documentation sont **entièrement en français**. L'anglais est autorisé uniquement sans équivalent français consacré.

| Terme anglais | Traduction retenue |
|---|---|
| Dashboard | Tableau de bord |
| KPI | Indicateur clé |
| Cash flow | Flux de trésorerie |
| Burn rate | Dépenses mensuelles moyennes |
| Runway | Autonomie de trésorerie |
| Scheduled | Planifiée |
| Recurring | Récurrente |
| Template | Modèle |
| Inbox | Boîte de réception |
| Drill-down | Détail |
| Drag & drop | Glisser-déposer |
| Hover | Survol |
| Upload | Téléverser |
| Login | Connexion |
| Logout | Déconnexion |
| Workflow | Flux de travail |
| Backup | Sauvegarde |
| Parser | Analyseur |

---

## 12. Hors-périmètre MVP (liste complète pour rappel)

À prévoir pour les versions ultérieures, par ordre de pertinence estimée :

1. Catégorisation par IA / LLM (auto-catégorisation plus fine des libellés ambigus)
2. 2FA TOTP + SSO Microsoft
3. Budgets prévisionnels par catégorie (vs réalisés)
4. Rapprochement bancaire fin (pointage par facture)
5. Élimination automatique des flux intercompagnies en vue consolidée
6. Interface mobile native (iOS / Android)
7. Import OFX / QIF
8. OCR sur relevés scannés (images)
9. Gestion multi-devises
10. Permissions granulaires par fonction
11. Webhooks / intégrations Slack / Teams
12. Ventilation analytique multi-axes (projets, chantiers)
13. Intégration CRM / pipeline commercial

---

## 13. Critères d'acceptation MVP

Le MVP est considéré comme terminé quand :

- Un utilisateur peut créer un compte admin et se connecter en HTTPS sur la VM Azure
- L'analyseur Delubac extrait correctement **≥ 95 % des lignes d'opération** sur le **jeu de référence** (3 relevés Delubac de test anonymisés fournis, cf. §13.2 ci-dessous). Méthode de comptage : (nombre de transactions correctement extraites avec date, libellé, montant exacts) / (nombre total de lignes d'opérations dans le PDF source, hors en-têtes/totaux intermédiaires/pieds de page)
- Les 3 mécanismes de catégorisation fonctionnent (règles, suggestions, apprentissage)
- Le tableau de bord affiche les 4 indicateurs clés + 2 graphiques + répartitions
- Le prévisionnel projette correctement sur 30 jours avec les 3 scénarios par défaut (vérifiable via jeu de test)
- Au moins 3 types d'alertes (seuil, échéance, découvert prévisionnel) sont opérationnels
- La vue consolidée agrège les données de plusieurs entités
- 4 utilisateurs peuvent se connecter avec des rôles et des restrictions d'entités distinctes
- La sauvegarde automatique quotidienne fonctionne **et une restauration complète a été testée avec succès** (procédure consignée)
- Le déploiement via `docker compose up -d` réussit sur une VM Azure vierge
- Les endpoints `/healthz` et `/readyz` répondent correctement
- Les flux email (réinitialisation de mot de passe + alerte seuil) ont été testés de bout en bout

### 13.1. Stratégie de tests

| Niveau | Outils | Exigence MVP |
|---|---|---|
| Tests unitaires backend | pytest + pytest-asyncio | Couverture **≥ 70 %** des modules critiques (analyseurs, catégorisation, prévisionnel) |
| Tests d'intégration backend | pytest + base PostgreSQL de test isolée | Scénarios : import complet Delubac, catégorisation appliquée, calcul tableau de bord, projection 30 jours |
| Tests frontend | Vitest + Testing Library | Couverture **≥ 60 %** des composants critiques (formulaires d'import, tableau de bord, page catégorisation) |
| Test de bout en bout | Playwright (1 scénario) | Parcours complet : connexion → import PDF → catégorisation → consultation tableau de bord |
| Tests de charge (informatif) | k6 | Un import de 10 000 transactions, affichage d'un tableau de bord avec 100 000 transactions en base |

### 13.2. Jeu de référence pour la validation Delubac

- 3 relevés Delubac anonymisés (mars 2026 + 2 autres mois fournis par l'utilisateur pendant l'implémentation)
- Une version "vérité terrain" de chaque relevé au format JSON, annotée manuellement, sert de référence pour le taux d'extraction
- Stocké dans `backend/tests/fixtures/delubac/`

---

_Fin de la spécification de conception._
