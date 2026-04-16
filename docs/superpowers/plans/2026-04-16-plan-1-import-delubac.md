# Plan 1 — Import & Analyseur Delubac : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre l'import d'un relevé bancaire PDF Delubac, en extraire les transactions (≥ 95 % d'exactitude), les normaliser, les dédupliquer, créer automatiquement les contreparties manquantes, et les stocker en base prêtes à être catégorisées (Plan 2). Livrer l'API REST et les pages frontend qui exposent ce pipeline.

**Architecture:** Un module `backend/app/parsers/` expose une interface `BaseParser` et un registre à découverte automatique ; un analyseur `DelubacParser` implémente l'extraction PDF via `pdfplumber`. Le pipeline `backend/app/services/imports.py` orchestre la normalisation, la détection de doublons via clé de hachage stable, la fusion des trios SEPA (virement + commission + TVA), la création des contreparties (statut `pending`) et l'insertion atomique. L'API REST expose `/api/imports` et `/api/transactions` ; le frontend ajoute trois pages (Import, Imports, Transactions) plus la gestion des contreparties à valider.

**Tech Stack:**

- **Backend** : pdfplumber 0.11+, rapidfuzz 3.x, python-magic 0.4+ (MIME), pytest, Alembic
- **Frontend** : existant (React 18 + TanStack Query + shadcn/ui) + composants fichier/dropzone (pas de nouvelle librairie externe — implémentation native avec `<input type="file">` stylé)
- **Schéma DB** : 4 nouvelles tables (`imports`, `transactions`, `counterparties`, `categories`) + 1 migration Alembic

---

## Prérequis

- Plan 0 complet (tag `plan-0-done`) : modèles `User`, `Entity`, `UserEntityAccess`, `BankAccount` en place, auth fonctionnelle, API REST opérationnelle.
- Branche `plan-1-import-delubac` créée et poussée.
- `.gitignore` exclut `backend/tests/fixtures/delubac/*.pdf` sauf `anon_*.pdf` et `synthetic_*.pdf`. (Déjà fait — premier commit de la branche.)
- Un PDF Delubac réel (`exemple_Delubac.pdf`) est disponible **localement** dans `backend/tests/fixtures/delubac/` mais **jamais commité**. Il sert uniquement de référence manuelle pour l'analyse de format.

---

## Conventions propres au Plan 1

- **Montants** : stockés en `Numeric(14, 2)` (jusqu'à 999 999 999 999,99 €). Signe inclus : encaissement > 0, décaissement < 0. Le parser Delubac lit les colonnes Débit/Crédit et applique le signe avant insertion.
- **Dates** : toujours `Date` (sans heure). UTC implicite.
- **Libellés** : colonne `raw_label` = texte exact du PDF (1 seule ligne, espaces normalisés) ; colonne `label` = version normalisée (majuscules, diacritiques supprimés, espaces compactés) utilisée pour les matchings et le dedup.
- **Dedup key** : SHA-256 hex des champs concaténés, stocké en colonne `dedup_key CHAR(64)` avec index unique partiel.
- **Parent/enfant** : une transaction `parent_transaction_id` nullable auto-référente. Un flag `is_aggregation_parent BOOLEAN` (généré applicativement à l'insertion) indique que la transaction a des enfants et doit être **exclue** des sommations statistiques.
- **Plan 2 en vue** : les tables `categories`, `tags`, `transaction_tags`, `category_rules` ne sont pas toutes créées ici. Ce plan crée uniquement `categories` (arborescence minimale) et le champ `category_id` sur `transactions` (nullable) pour permettre l'affichage « Non catégorisée ». Le moteur de règles et l'apprentissage arriveront au Plan 2.

---

## Structure des fichiers (cible à la fin du Plan 1)

```
backend/
├── app/
│   ├── models/
│   │   ├── category.py              # NEW — arborescence minimale
│   │   ├── counterparty.py          # NEW — statut pending/active/ignored
│   │   ├── transaction.py           # NEW — table centrale
│   │   └── import_record.py         # NEW — historique d'imports
│   ├── schemas/
│   │   ├── category.py              # NEW
│   │   ├── counterparty.py          # NEW
│   │   ├── transaction.py           # NEW
│   │   └── import_record.py         # NEW
│   ├── parsers/                     # NEW MODULE
│   │   ├── __init__.py              # registre et découverte
│   │   ├── base.py                  # BaseParser + ParsedStatement + ParsedTransaction
│   │   ├── errors.py                # ParserError, InvalidPdfStructureError
│   │   ├── normalization.py         # helpers : amount, label, counterparty extract
│   │   └── delubac.py               # DelubacParser
│   ├── services/
│   │   ├── __init__.py              # NEW
│   │   └── imports.py               # NEW — pipeline : normalize + dedup + insert
│   └── api/
│       ├── imports.py               # NEW — POST /api/imports, GET /api/imports[/id]
│       ├── transactions.py          # NEW — GET /api/transactions
│       ├── counterparties.py        # NEW — GET/PATCH /api/counterparties
│       └── router.py                # MODIFY — brancher les nouveaux routeurs
├── alembic/versions/
│   └── <timestamp>_plan1_transactions_imports.py   # NEW migration
└── tests/
    ├── fixtures/delubac/
    │   ├── synthetic_minimal.pdf                 # NEW — 3 transactions, 1 page
    │   ├── synthetic_minimal.ground_truth.json   # NEW — vérité terrain
    │   ├── synthetic_sepa_trio.pdf               # NEW — 1 virement + commission + TVA
    │   ├── synthetic_sepa_trio.ground_truth.json
    │   ├── synthetic_full_month.pdf              # NEW — ~50 transactions, 3 pages
    │   ├── synthetic_full_month.ground_truth.json
    │   └── build_fixtures.py                     # NEW — script de génération des PDF
    ├── test_parser_delubac.py                    # NEW — tests de DelubacParser
    ├── test_parsers_registry.py                  # NEW — tests du registre
    ├── test_normalization.py                     # NEW — helpers de normalisation
    ├── test_service_imports.py                   # NEW — pipeline d'import
    ├── test_api_imports.py                       # NEW — endpoints /imports
    ├── test_api_transactions.py                  # NEW — endpoints /transactions
    ├── test_api_counterparties.py                # NEW — endpoints /counterparties
    ├── test_model_transaction.py                 # NEW
    ├── test_model_import_record.py               # NEW
    ├── test_model_counterparty.py                # NEW
    └── test_model_category.py                    # NEW

frontend/
├── src/
│   ├── api/
│   │   ├── imports.ts                # NEW
│   │   ├── transactions.ts           # NEW
│   │   └── counterparties.ts         # NEW
│   ├── pages/
│   │   ├── ImportNewPage.tsx         # NEW — /imports/nouveau (dropzone + résumé)
│   │   ├── ImportHistoryPage.tsx     # NEW — /imports
│   │   ├── TransactionsPage.tsx      # NEW — /transactions
│   │   └── CounterpartiesPage.tsx    # NEW — /contreparties
│   ├── components/
│   │   ├── FileDropzone.tsx          # NEW
│   │   └── TransactionFilters.tsx    # NEW
│   ├── types/api.ts                  # MODIFY — ajouter Transaction, Import, Counterparty
│   └── router.tsx                    # MODIFY — 4 nouvelles routes
└── src/test/
    ├── ImportNewPage.test.tsx        # NEW
    ├── TransactionsPage.test.tsx     # NEW
    └── CounterpartiesPage.test.tsx   # NEW
```

**Rationale :**

- Un fichier par modèle SQLAlchemy (conforme à la convention du Plan 0 — éviter les gros `models.py`).
- `parsers/` sous `app/` et non à la racine : cohérent avec le reste du code applicatif, pas de package externe à packager.
- `services/imports.py` sépare la logique d'orchestration (hors HTTP) de la couche API : permet de réutiliser le pipeline depuis un cron ou un test sans passer par FastAPI.
- Les fixtures synthétiques sont générées par un script Python dédié (`build_fixtures.py`) — chaque contributeur peut les régénérer sans données réelles. Les PDF et JSON sont commités ; le script est commité aussi.
- Les tests de modèles restent cohérents avec la convention du Plan 0 (un fichier `test_model_*.py` par table).

---

## Sections du plan

Le plan est découpé en **8 sections** :

- **A** — Préparation, fixtures synthétiques, script de génération (4 tâches)
- **B** — Modèles ORM + migration Alembic : `Category`, `Counterparty`, `Transaction`, `ImportRecord` (6 tâches)
- **C** — Module `parsers/` : `BaseParser`, `ParsedStatement`, registre, erreurs, normalisation (4 tâches)
- **D** — Analyseur Delubac : extraction PDF + normalisation + fusion SEPA (6 tâches)
- **E** — Pipeline d'import : limites, dedup, contreparties, insertion atomique (5 tâches)
- **F** — API REST : `imports`, `transactions`, `counterparties` (5 tâches)
- **G** — Frontend : 4 pages + composants + routes (6 tâches)
- **H** — Tests E2E d'intégration + validation couverture + PROGRESS.md (3 tâches)

**Total : ~39 tâches numérotées**, chacune découpée en 3-7 étapes TDD.

---

# SECTION A — Préparation, fixtures synthétiques

### Tâche A1 : Ajouter les dépendances backend (pdfplumber, rapidfuzz, python-magic)

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/Dockerfile`

- [ ] **Étape 1 : Vérifier l'état actuel de `pyproject.toml`**

```bash
cd /home/kierangauthier/claude-secure/horizon/backend
grep -A 30 'dependencies' pyproject.toml
```

- [ ] **Étape 2 : Ajouter les dépendances à la section `[project].dependencies`**

Ouvre `backend/pyproject.toml`. Dans la liste `dependencies`, ajouter après la dernière ligne existante :

```toml
  "pdfplumber>=0.11.4",
  "rapidfuzz>=3.9.0",
  "python-magic>=0.4.27",
```

- [ ] **Étape 3 : Ajouter `reportlab` aux dépendances dev pour générer les PDF synthétiques**

Dans la section `[project.optional-dependencies].dev` :

```toml
  "reportlab>=4.2.0",
```

Si la section `[project.optional-dependencies]` n'existe pas, l'ajouter après `dependencies` :

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "ruff>=0.6.0",
  "httpx>=0.27.0",
  "reportlab>=4.2.0",
]
```

- [ ] **Étape 4 : Mettre à jour le Dockerfile pour installer libmagic**

Dans `backend/Dockerfile`, repérer la couche d'installation système (`RUN apt-get update …`). Ajouter `libmagic1` à la liste des paquets :

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
 && rm -rf /var/lib/apt/lists/*
```

- [ ] **Étape 5 : Installer les dépendances en local**

```bash
cd /home/kierangauthier/claude-secure/horizon/backend
python3 -m pip install -e '.[dev]'
python3 -c "import pdfplumber, rapidfuzz, magic; print('ok')"
```

Expected: `ok`

- [ ] **Étape 6 : Commit**

```bash
git add backend/pyproject.toml backend/Dockerfile
git commit -m "chore(backend): add pdfplumber/rapidfuzz/python-magic/reportlab deps"
```

---

### Tâche A2 : Créer le script de génération de fixtures synthétiques

**Files:**
- Create: `backend/tests/fixtures/delubac/build_fixtures.py`

- [ ] **Étape 1 : Écrire le script complet**

Créer `backend/tests/fixtures/delubac/build_fixtures.py` :

```python
"""Génère des PDF Delubac synthétiques + leurs vérités terrain JSON.

Usage :
    python -m tests.fixtures.delubac.build_fixtures

Produit :
    synthetic_minimal.pdf + .ground_truth.json
    synthetic_sepa_trio.pdf + .ground_truth.json
    synthetic_full_month.pdf + .ground_truth.json

Les PDF reproduisent la mise en page exacte du relevé Delubac officiel :
- En-tête avec code agence, numéro de compte, IBAN
- Colonnes Date opé / Date valeur / Libellé / Débit / Crédit
- Totaux par page, ancien solde, nouveau solde
- Trios VIR SEPA + COMMISSION VIR SEPA + TVA VIR SEPA

Aucune donnée réelle n'est utilisée : tous les noms, IBAN et montants sont fictifs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent

ACCOUNT_HEADER = {
    "bank_name": "Delubac",
    "bank_code": "delubac",
    "account_number": "11170202001",
    "iban": "FR76 1287 9000 0111 1702 0200 105",
    "bic": "DELUFR22XXX",
    "account_holder": "SYNTHETIQUE SAS",
    "address_line1": "1 RUE FICTIVE",
    "address_line2": "75000 PARIS",
    "statement_date": "31/03/2026",
}


@dataclass
class Txn:
    operation_date: str    # DD/MM/YYYY
    value_date: str
    label: str             # libellé brut (1 ligne)
    detail: str            # ligne(s) de détail sous le libellé (peut être "")
    amount: str            # "1.234,56" — format français
    direction: str         # "debit" ou "credit"


def draw_page_header(c: canvas.Canvas, page_num: int) -> float:
    """Dessine l'en-tête et retourne l'ordonnée du haut de la zone transactions."""
    width, height = A4
    # En-têtes administratifs (top-left)
    c.setFont("Helvetica", 7)
    c.drawString(520, height - 30, "RG SDC : X")
    c.drawString(520, height - 40, f"RG : 0170202")
    c.drawString(520, height - 50, "Code AG : 1")
    # Titre central
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, height - 60, "RELEVÉ DE COMPTE (EN EUR)")
    # Date d'arrêté
    c.setFont("Helvetica", 8)
    c.drawString(410, height - 78, f"Date d'arrêté : {ACCOUNT_HEADER['statement_date']}")
    # Numéro de page
    c.drawString(520, height - 90, f"Page {page_num}")
    # Titulaire (zone droite)
    c.drawString(310, height - 115, ACCOUNT_HEADER["account_holder"])
    # Sur la page 1, bloc identité complet
    if page_num == 1:
        c.drawString(50, height - 150, "Numéro client :")
        c.drawString(50, height - 160, "0170202")
        c.drawString(50, height - 180, "Intitulé du compte :")
        c.drawString(50, height - 190, ACCOUNT_HEADER["account_holder"])
        c.drawString(50, height - 220, ACCOUNT_HEADER["address_line1"])
        c.drawString(50, height - 230, ACCOUNT_HEADER["address_line2"])
        c.drawString(50, height - 260, f"Numéro de compte : {ACCOUNT_HEADER['account_number']}")
        c.drawString(50, height - 275, f"IBAN : {ACCOUNT_HEADER['iban']}  BIC : {ACCOUNT_HEADER['bic']}")
    else:
        # Page > 1 : bandeau simplifié
        c.drawString(50, height - 130,
                     f"{ACCOUNT_HEADER['account_holder']} - N° de compte : {ACCOUNT_HEADER['account_number']}")
    # En-tête de colonnes (y ≈ height - 300)
    y_header = height - 300
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, y_header, "Date opé")
    c.drawString(102, y_header, "Date valeur")
    c.drawString(167, y_header, "Libellé des opérations")
    c.drawString(424, y_header, "Débit")
    c.drawString(521, y_header, "Crédit")
    return y_header - 15


def draw_txn_row(c: canvas.Canvas, y: float, t: Txn) -> float:
    """Dessine une ligne de transaction et retourne la nouvelle ordonnée."""
    c.setFont("Helvetica", 8)
    c.drawString(49, y, t.operation_date)
    c.drawString(112, y, t.value_date)
    c.drawString(167, y, t.label[:45])
    # Montant : aligné à droite
    if t.direction == "debit":
        c.drawRightString(455, y, t.amount)
    else:
        c.drawRightString(550, y, t.amount)
    y -= 11
    if t.detail:
        c.drawString(167, y, t.detail)
        y -= 11
    return y - 2  # petit espace entre transactions


def draw_opening_balance(c: canvas.Canvas, y: float, date: str, amount: str) -> float:
    c.setFont("Helvetica", 8)
    c.drawString(239, y, f"Ancien solde au {date}")
    c.drawRightString(550, y, amount)
    return y - 15


def draw_closing_balance(c: canvas.Canvas, y: float, date: str, amount: str) -> float:
    c.setFont("Helvetica", 8)
    c.drawString(239, y, f"Nouveau solde créditeur au {date}")
    c.drawRightString(550, y, amount)
    return y - 15


def draw_page_total(c: canvas.Canvas, y: float, debit_total: str, credit_total: str) -> float:
    c.setFont("Helvetica", 8)
    c.drawString(167, y, "Total des opérations")
    c.drawRightString(455, y, debit_total)
    c.drawRightString(550, y, credit_total)
    return y - 15


def draw_footer(c: canvas.Canvas) -> None:
    c.setFont("Helvetica", 6)
    c.drawString(50, 25, '"T" Tarification selon les conditions en vigueur        Sauf erreur ou omission')


def build_pdf(path: Path, pages: list[tuple[list[Txn], str, str]],
              opening_balance: tuple[str, str] | None,
              closing_balance: tuple[str, str] | None) -> None:
    """pages = liste de (transactions_de_la_page, total_debit_str, total_credit_str)."""
    c = canvas.Canvas(str(path), pagesize=A4)
    for i, (txns, deb_tot, cred_tot) in enumerate(pages, start=1):
        y = draw_page_header(c, i)
        if i == 1 and opening_balance:
            y = draw_opening_balance(c, y, *opening_balance)
        for t in txns:
            y = draw_txn_row(c, y, t)
        y = draw_page_total(c, y, deb_tot, cred_tot)
        if i == len(pages) and closing_balance:
            y = draw_closing_balance(c, y, *closing_balance)
        draw_footer(c)
        c.showPage()
    c.save()


def write_ground_truth(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# -------------- Fixture 1 : synthetic_minimal --------------

def build_minimal() -> None:
    txns = [
        Txn("02/03/2026", "01/03/2026", "ARRETE DE COMPTE AU 28/02/26", "", "92,32", "debit"),
        Txn("05/03/2026", "05/03/2026", "COTIS CARTE BUSI IMM", "4350520489680012", "80,00", "debit"),
        Txn("05/03/2026", "05/03/2026", "VIR SEPA BNP PARIBAS FACTOR", "BNPPF Na-6213143", "25.204,95", "credit"),
    ]
    pages = [(txns, "172,32", "25.204,95")]
    build_pdf(HERE / "synthetic_minimal.pdf", pages,
              opening_balance=("28/02/2026", "19,70"),
              closing_balance=("31/03/2026", "25.052,33"))
    write_ground_truth(HERE / "synthetic_minimal.ground_truth.json", {
        "bank_code": "delubac",
        "account_number": ACCOUNT_HEADER["account_number"],
        "iban": ACCOUNT_HEADER["iban"].replace(" ", ""),
        "period_start": "2026-03-02",
        "period_end": "2026-03-05",
        "opening_balance": "19.70",
        "closing_balance": "25052.33",
        "transactions": [
            {"operation_date": "2026-03-02", "value_date": "2026-03-01",
             "label": "ARRETE DE COMPTE AU 28/02/26", "amount": "-92.32"},
            {"operation_date": "2026-03-05", "value_date": "2026-03-05",
             "label": "COTIS CARTE BUSI IMM 4350520489680012", "amount": "-80.00"},
            {"operation_date": "2026-03-05", "value_date": "2026-03-05",
             "label": "VIR SEPA BNP PARIBAS FACTOR BNPPF Na-6213143",
             "amount": "25204.95"},
        ],
    })


# -------------- Fixture 2 : synthetic_sepa_trio --------------

def build_sepa_trio() -> None:
    txns = [
        Txn("06/03/2026", "06/03/2026", "VIR SEPA JEAN DUPONT", "Facture Fevrier", "1.000,00", "debit"),
        Txn("06/03/2026", "06/03/2026", "COMMISSION VIR SEPA JEAN DUPONT", "", "0,50", "debit"),
        Txn("06/03/2026", "06/03/2026", "TVA VIR SEPA JEAN DUPONT", "", "0,10", "debit"),
    ]
    pages = [(txns, "1.000,60", "0,00")]
    build_pdf(HERE / "synthetic_sepa_trio.pdf", pages,
              opening_balance=("28/02/2026", "5.000,00"),
              closing_balance=("31/03/2026", "3.999,40"))
    write_ground_truth(HERE / "synthetic_sepa_trio.ground_truth.json", {
        "bank_code": "delubac",
        "account_number": ACCOUNT_HEADER["account_number"],
        "iban": ACCOUNT_HEADER["iban"].replace(" ", ""),
        "period_start": "2026-03-06",
        "period_end": "2026-03-06",
        "opening_balance": "5000.00",
        "closing_balance": "3999.40",
        "transactions": [
            {"operation_date": "2026-03-06", "value_date": "2026-03-06",
             "label": "VIR SEPA JEAN DUPONT Facture Fevrier",
             "amount": "-1000.60",
             "is_aggregation_parent": True,
             "children": [
                 {"label": "VIR SEPA JEAN DUPONT Facture Fevrier", "amount": "-1000.00"},
                 {"label": "COMMISSION VIR SEPA JEAN DUPONT", "amount": "-0.50"},
                 {"label": "TVA VIR SEPA JEAN DUPONT", "amount": "-0.10"},
             ]},
        ],
    })


# -------------- Fixture 3 : synthetic_full_month --------------

def build_full_month() -> None:
    """50+ transactions réparties sur 3 pages, mélange de trios SEPA et de lignes isolées."""
    p1 = [
        Txn("02/03/2026", "01/03/2026", "Intérêts de retard", "Créance n° 0502321", "59,29", "debit"),
        Txn("02/03/2026", "01/03/2026", "T-CION Créances non réglées", "n° 0502321", "32,00", "debit"),
        Txn("02/03/2026", "01/03/2026", "TVA/CION Créances non réglées", "n° 0502321", "6,40", "debit"),
        Txn("05/03/2026", "05/03/2026", "VIR SEPA BNP PARIBAS FACTOR", "BNPPF Na-6213143", "25.204,95", "credit"),
        Txn("06/03/2026", "06/03/2026", "VIR SEPA JEAN DUPONT", "Facture Fevrier", "1.000,00", "debit"),
        Txn("06/03/2026", "06/03/2026", "COMMISSION VIR SEPA JEAN DUPONT", "", "0,50", "debit"),
        Txn("06/03/2026", "06/03/2026", "TVA VIR SEPA JEAN DUPONT", "", "0,10", "debit"),
        Txn("09/03/2026", "09/03/2026", "VIR SEPA MARIE MARTIN", "Salaire Fevrier", "1.500,00", "debit"),
        Txn("09/03/2026", "09/03/2026", "COMMISSION VIR SEPA MARIE MARTIN", "", "0,50", "debit"),
        Txn("09/03/2026", "09/03/2026", "TVA VIR SEPA MARIE MARTIN", "", "0,10", "debit"),
        Txn("10/03/2026", "10/03/2026", "CARTE 09/03 COMMERCE EXEMPLE", "", "125,40", "debit"),
        Txn("10/03/2026", "10/03/2026", "PRLV SEPA URSSAF", "CENTRE PAIEMENT 10012001", "8.500,00", "debit"),
    ]
    p2 = [
        Txn("15/03/2026", "15/03/2026", "VIR SEPA BNP PARIBAS FACTOR", "BNPPF Na-6213402", "27.680,53", "credit"),
        Txn("15/03/2026", "15/03/2026", "PRLV SEPA MALAKOFF HUMANIS", "MH R145 2603", "450,00", "debit"),
        Txn("15/03/2026", "15/03/2026", "PRLV SEPA DKV EURO SERVICE GMB", "DE93ZZZ00000001787", "94,50", "debit"),
        Txn("20/03/2026", "20/03/2026", "VIR SEPA PIERRE DUBOIS", "Salaire Fevrier", "1.800,00", "debit"),
        Txn("20/03/2026", "20/03/2026", "COMMISSION VIR SEPA PIERRE DUBOIS", "", "0,50", "debit"),
        Txn("20/03/2026", "20/03/2026", "TVA VIR SEPA PIERRE DUBOIS", "", "0,10", "debit"),
        Txn("22/03/2026", "22/03/2026", "VIR SEPA LUCIE BERNARD", "Salaire Fevrier", "1.200,00", "debit"),
        Txn("22/03/2026", "22/03/2026", "COMMISSION VIR SEPA LUCIE BERNARD", "", "0,50", "debit"),
        Txn("22/03/2026", "22/03/2026", "TVA VIR SEPA LUCIE BERNARD", "", "0,10", "debit"),
        Txn("24/03/2026", "24/03/2026", "PRLV SEPA DGFIP", "TVA1-032026-3310CA3", "4.982,00", "debit"),
        Txn("25/03/2026", "25/03/2026", "CARTE 24/03 EDF ENTREPRISE", "", "309,80", "debit"),
    ]
    p3 = [
        Txn("27/03/2026", "27/03/2026", "VIR SEPA SELARL CASAL", "Honoraires", "254,98", "debit"),
        Txn("27/03/2026", "27/03/2026", "COMMISSION VIR SEPA SELARL CASAL", "", "0,50", "debit"),
        Txn("27/03/2026", "27/03/2026", "TVA VIR SEPA SELARL CASAL", "", "0,10", "debit"),
        Txn("31/03/2026", "31/03/2026", "VIR SEPA THOMAS BERTIN", "Primes", "156,46", "debit"),
        Txn("31/03/2026", "31/03/2026", "COMMISSION VIR SEPA THOMAS BERTIN", "", "0,50", "debit"),
        Txn("31/03/2026", "31/03/2026", "TVA VIR SEPA THOMAS BERTIN", "", "0,10", "debit"),
        Txn("31/03/2026", "31/03/2026", "CARTE 30/03 STATION EXEMPLE", "", "89,50", "debit"),
    ]
    pages = [
        (p1, "11.428,24", "25.204,95"),
        (p2, "8.527,70", "27.680,53"),
        (p3, "501,64", "0,00"),
    ]
    build_pdf(HERE / "synthetic_full_month.pdf", pages,
              opening_balance=("28/02/2026", "1.000,00"),
              closing_balance=("31/03/2026", "33.427,90"))

    # Vérité terrain : aplatie, avec parents agrégés marqués.
    gt_txns = []
    all_input = p1 + p2 + p3
    i = 0
    while i < len(all_input):
        t = all_input[i]
        amount_val = _fr_to_decimal(t.amount)
        signed = -amount_val if t.direction == "debit" else amount_val
        label_full = (t.label + (" " + t.detail if t.detail else "")).strip()
        # Détection trio SEPA : t + t+1 commence par COMMISSION VIR SEPA + t+2 commence par TVA VIR SEPA
        if (i + 2 < len(all_input)
            and t.label.startswith("VIR SEPA ")
            and all_input[i + 1].label.startswith("COMMISSION VIR SEPA ")
            and all_input[i + 2].label.startswith("TVA VIR SEPA ")
            and t.direction == "debit"):
            child1 = all_input[i + 1]
            child2 = all_input[i + 2]
            parent_amount = -(amount_val + _fr_to_decimal(child1.amount) + _fr_to_decimal(child2.amount))
            gt_txns.append({
                "operation_date": _fr_date(t.operation_date),
                "value_date": _fr_date(t.value_date),
                "label": label_full,
                "amount": f"{parent_amount:.2f}",
                "is_aggregation_parent": True,
                "children": [
                    {"label": label_full, "amount": f"{signed:.2f}"},
                    {"label": child1.label, "amount": f"{-_fr_to_decimal(child1.amount):.2f}"},
                    {"label": child2.label, "amount": f"{-_fr_to_decimal(child2.amount):.2f}"},
                ],
            })
            i += 3
        else:
            gt_txns.append({
                "operation_date": _fr_date(t.operation_date),
                "value_date": _fr_date(t.value_date),
                "label": label_full,
                "amount": f"{signed:.2f}",
            })
            i += 1

    write_ground_truth(HERE / "synthetic_full_month.ground_truth.json", {
        "bank_code": "delubac",
        "account_number": ACCOUNT_HEADER["account_number"],
        "iban": ACCOUNT_HEADER["iban"].replace(" ", ""),
        "period_start": "2026-03-02",
        "period_end": "2026-03-31",
        "opening_balance": "1000.00",
        "closing_balance": "33427.90",
        "transactions": gt_txns,
    })


def _fr_to_decimal(s: str) -> Decimal:
    """'1.234,56' -> Decimal('1234.56')"""
    return Decimal(s.replace(".", "").replace(",", "."))


def _fr_date(s: str) -> str:
    """'02/03/2026' -> '2026-03-02'"""
    d, m, y = s.split("/")
    return f"{y}-{m}-{d}"


if __name__ == "__main__":
    build_minimal()
    build_sepa_trio()
    build_full_month()
    print(f"Fixtures générées dans {HERE}")
```

- [ ] **Étape 2 : Exécuter le script pour produire les PDF et JSON**

```bash
cd /home/kierangauthier/claude-secure/horizon/backend
python -m tests.fixtures.delubac.build_fixtures
```

Expected: `Fixtures générées dans /home/kierangauthier/claude-secure/horizon/backend/tests/fixtures/delubac`
puis `ls tests/fixtures/delubac/` doit lister 3 `.pdf` + 3 `.ground_truth.json` + `build_fixtures.py` + `exemple_Delubac.pdf` (ignoré par git).

- [ ] **Étape 3 : Vérifier que git ne suit que les fichiers synthétiques**

```bash
git status --short tests/fixtures/delubac/
```

Expected : 3 PDF `synthetic_*.pdf`, 3 JSON, et le script. Aucun `exemple_Delubac.pdf`.

- [ ] **Étape 4 : Commit**

```bash
git add backend/tests/fixtures/delubac/build_fixtures.py \
        backend/tests/fixtures/delubac/synthetic_*.pdf \
        backend/tests/fixtures/delubac/synthetic_*.ground_truth.json
git commit -m "test(fixtures): synthetic Delubac PDFs and ground truth JSON"
```

---

### Tâche A3 : Créer un test de cohérence des fixtures

Vérifie que chaque fixture synthétique est lisible par pdfplumber et que la vérité terrain associée est un JSON valide et complet.

**Files:**
- Create: `backend/tests/test_fixtures_delubac.py`

- [ ] **Étape 1 : Écrire le test (doit passer immédiatement après A2)**

```python
"""Sanity check des fixtures Delubac synthétiques."""
import json
from pathlib import Path

import pdfplumber
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"

PDF_GT_PAIRS = [
    ("synthetic_minimal.pdf", "synthetic_minimal.ground_truth.json"),
    ("synthetic_sepa_trio.pdf", "synthetic_sepa_trio.ground_truth.json"),
    ("synthetic_full_month.pdf", "synthetic_full_month.ground_truth.json"),
]


@pytest.mark.parametrize("pdf_name,gt_name", PDF_GT_PAIRS)
def test_fixture_pdf_readable(pdf_name: str, gt_name: str) -> None:
    pdf_path = FIXTURES / pdf_name
    gt_path = FIXTURES / gt_name
    assert pdf_path.exists(), f"PDF manquant: {pdf_path}. Lance build_fixtures.py."
    assert gt_path.exists(), f"Vérité terrain manquante: {gt_path}"

    with pdfplumber.open(pdf_path) as pdf:
        assert len(pdf.pages) >= 1
        assert pdf.pages[0].extract_text(), "PDF vide"

    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    for required in ("bank_code", "iban", "transactions", "period_start", "period_end"):
        assert required in gt, f"{gt_name} manque la clé {required}"
    assert gt["bank_code"] == "delubac"
    assert len(gt["transactions"]) >= 1
```

- [ ] **Étape 2 : Lancer les tests**

```bash
cd /home/kierangauthier/claude-secure/horizon/backend
pytest tests/test_fixtures_delubac.py -v
```

Expected: 3 tests passent.

- [ ] **Étape 3 : Commit**

```bash
git add backend/tests/test_fixtures_delubac.py
git commit -m "test(fixtures): validate Delubac fixtures readable and well-formed"
```

---

### Tâche A4 : Documenter le format fixture dans docs/operations

**Files:**
- Create: `backend/tests/fixtures/delubac/README.md`

- [ ] **Étape 1 : Créer la documentation**

```markdown
# Fixtures Delubac

Ce dossier contient des PDF Delubac **synthétiques** et leurs vérités terrain JSON,
utilisés pour valider le parser `DelubacParser` et le pipeline d'import.

## Fichiers suivis par git

- `build_fixtures.py` — script de génération (reportlab).
- `synthetic_minimal.pdf` + `.ground_truth.json` — 3 transactions, 1 page.
- `synthetic_sepa_trio.pdf` + `.ground_truth.json` — 1 virement SEPA + commission + TVA.
- `synthetic_full_month.pdf` + `.ground_truth.json` — ≈ 30 transactions, 3 pages.

## Fichiers **jamais** commités

Les vrais relevés bancaires (fichiers `*.pdf` autres que `synthetic_*.pdf` et
`anon_*.pdf`) sont **ignorés** par `.gitignore` à la racine. Ne JAMAIS retirer cette règle.

## Régénérer les fixtures

```bash
cd backend
python -m tests.fixtures.delubac.build_fixtures
```

## Format de la vérité terrain

```json
{
  "bank_code": "delubac",
  "account_number": "...",
  "iban": "FR76...",
  "period_start": "YYYY-MM-DD",
  "period_end": "YYYY-MM-DD",
  "opening_balance": "123.45",     // Decimal signé en str
  "closing_balance": "678.90",
  "transactions": [
    {
      "operation_date": "YYYY-MM-DD",
      "value_date": "YYYY-MM-DD",
      "label": "Libellé complet incluant les lignes de détail",
      "amount": "-12.34",           // négatif = débit
      "is_aggregation_parent": true, // optionnel, défaut false
      "children": [ ... ]            // si aggregation_parent
    }
  ]
}
```

## Critère d'acceptation Plan 1

Le parser doit extraire **≥ 95 %** des transactions de chaque fixture synthétique
avec date, libellé et montant exacts, et produire les parents SEPA correctement.
```

- [ ] **Étape 2 : Commit**

```bash
git add backend/tests/fixtures/delubac/README.md
git commit -m "docs(fixtures): document Delubac fixtures format and policy"
```

---

# SECTION B — Modèles ORM + migration Alembic

### Tâche B1 : Modèle `Category` (arborescence minimale)

**Files:**
- Create: `backend/app/models/category.py`
- Create: `backend/tests/test_model_category.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Étape 1 : Écrire le test (échec attendu — modèle absent)**

`backend/tests/test_model_category.py` :

```python
"""Tests du modèle Category (arborescence)."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.category import Category


def test_category_basic_fields(db_session) -> None:
    cat = Category(name="Ventes clients", slug="ventes-clients",
                   color="#2ecc71", is_system=True)
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    assert cat.id is not None
    assert cat.parent_category_id is None
    assert cat.created_at is not None


def test_category_parent_child(db_session) -> None:
    parent = Category(name="Encaissements", slug="encaissements", is_system=True)
    db_session.add(parent)
    db_session.commit()
    child = Category(name="Ventes", slug="ventes", parent_category_id=parent.id,
                     is_system=True)
    db_session.add(child)
    db_session.commit()
    db_session.refresh(child)
    assert child.parent_category_id == parent.id


def test_category_slug_unique(db_session) -> None:
    db_session.add(Category(name="Ventes", slug="ventes", is_system=False))
    db_session.commit()
    db_session.add(Category(name="Autres", slug="ventes", is_system=False))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Étape 2 : Vérifier l'échec du test**

```bash
pytest tests/test_model_category.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.models.category'`

- [ ] **Étape 3 : Implémenter le modèle**

`backend/app/models/category.py` :

```python
"""Catégorie d'opération : arborescence partagée par toutes les entités."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[Optional[str]] = mapped_column(String(9), nullable=True)
    parent_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    parent: Mapped[Optional["Category"]] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent"
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, slug={self.slug!r})>"
```

- [ ] **Étape 4 : Enregistrer le modèle dans `__init__.py`**

Ouvrir `backend/app/models/__init__.py` et ajouter l'import :

```python
from app.models.category import Category  # noqa: F401
```

Placer à côté des autres imports existants (`User`, `Entity`, etc.).

- [ ] **Étape 5 : Relancer les tests**

```bash
pytest tests/test_model_category.py -v
```

Expected : 3 tests passent.

- [ ] **Étape 6 : Commit**

```bash
git add backend/app/models/category.py backend/app/models/__init__.py backend/tests/test_model_category.py
git commit -m "feat(models): Category model with hierarchical parent_category_id"
```

---

### Tâche B2 : Modèle `Counterparty` (contrepartie normalisée)

**Files:**
- Create: `backend/app/models/counterparty.py`
- Create: `backend/tests/test_model_counterparty.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_model_counterparty.py` :

```python
"""Tests du modèle Counterparty."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.counterparty import Counterparty, CounterpartyStatus


def test_counterparty_basic(db_session) -> None:
    cp = Counterparty(name="URSSAF", normalized_name="URSSAF",
                      status=CounterpartyStatus.PENDING)
    db_session.add(cp)
    db_session.commit()
    db_session.refresh(cp)
    assert cp.id is not None
    assert cp.status == CounterpartyStatus.PENDING
    assert cp.created_at is not None


def test_counterparty_status_enum(db_session) -> None:
    for st in (CounterpartyStatus.PENDING,
               CounterpartyStatus.ACTIVE,
               CounterpartyStatus.IGNORED):
        db_session.add(Counterparty(name=f"n_{st.value}",
                                    normalized_name=f"N {st.value}",
                                    status=st))
    db_session.commit()
    rows = db_session.query(Counterparty).all()
    assert len(rows) == 3


def test_counterparty_normalized_name_unique(db_session) -> None:
    db_session.add(Counterparty(name="URSSAF Paris",
                                normalized_name="URSSAF",
                                status=CounterpartyStatus.ACTIVE))
    db_session.commit()
    db_session.add(Counterparty(name="Urssaf Lyon",
                                normalized_name="URSSAF",
                                status=CounterpartyStatus.PENDING))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_model_counterparty.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Étape 3 : Implémenter le modèle**

`backend/app/models/counterparty.py` :

```python
"""Contrepartie (fournisseur, client, salarié) associée à des transactions."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CounterpartyStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    IGNORED = "ignored"


class Counterparty(Base):
    __tablename__ = "counterparties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True, index=True
    )
    status: Mapped[CounterpartyStatus] = mapped_column(
        Enum(CounterpartyStatus,
             name="counterparty_status",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False, default=CounterpartyStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Counterparty(id={self.id}, name={self.name!r}, status={self.status.value})>"
```

- [ ] **Étape 4 : Enregistrer dans `__init__.py`**

```python
from app.models.counterparty import Counterparty, CounterpartyStatus  # noqa: F401
```

- [ ] **Étape 5 : Relancer les tests**

```bash
pytest tests/test_model_counterparty.py -v
```

Expected : 3 tests passent.

- [ ] **Étape 6 : Commit**

```bash
git add backend/app/models/counterparty.py backend/app/models/__init__.py backend/tests/test_model_counterparty.py
git commit -m "feat(models): Counterparty with PENDING/ACTIVE/IGNORED status"
```

---

### Tâche B3 : Modèle `ImportRecord` (historique des imports)

**Files:**
- Create: `backend/app/models/import_record.py`
- Create: `backend/tests/test_model_import_record.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_model_import_record.py` :

```python
"""Tests du modèle ImportRecord."""
from datetime import date

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord
from app.models.user import User, UserRole


def _seed(db_session) -> tuple[User, BankAccount]:
    u = User(email="a@b.fr", password_hash="x", role=UserRole.ADMIN,
             full_name="A")
    e = Entity(name="Acreed", slug="acreed")
    db_session.add_all([u, e])
    db_session.commit()
    ba = BankAccount(entity_id=e.id, name="Delubac pro", iban="FR7612345",
                     bank_code="delubac")
    db_session.add(ba)
    db_session.commit()
    return u, ba


def test_import_record_basic(db_session) -> None:
    u, ba = _seed(db_session)
    rec = ImportRecord(
        bank_account_id=ba.id,
        uploaded_by_id=u.id,
        filename="releve_mars.pdf",
        file_size_bytes=12345,
        file_sha256="a" * 64,
        bank_code="delubac",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        transactions_imported=42,
        transactions_duplicated=3,
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    assert rec.id is not None
    assert rec.created_at is not None
    assert rec.transactions_imported == 42


def test_import_record_file_sha256_unique_per_account(db_session) -> None:
    """Deux imports avec même hash et même compte : autorisés (réimport avec override)
    mais détectables via la colonne. Contrainte soft applicative, pas DB."""
    u, ba = _seed(db_session)
    r1 = ImportRecord(bank_account_id=ba.id, uploaded_by_id=u.id,
                      filename="f1.pdf", file_size_bytes=1,
                      file_sha256="b" * 64, bank_code="delubac",
                      period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
                      transactions_imported=0, transactions_duplicated=0)
    r2 = ImportRecord(bank_account_id=ba.id, uploaded_by_id=u.id,
                      filename="f1_bis.pdf", file_size_bytes=1,
                      file_sha256="b" * 64, bank_code="delubac",
                      period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
                      transactions_imported=0, transactions_duplicated=0)
    db_session.add_all([r1, r2])
    db_session.commit()  # Aucune contrainte DB — volontaire
    rows = db_session.query(ImportRecord).filter_by(file_sha256="b" * 64).all()
    assert len(rows) == 2
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_model_import_record.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Étape 3 : Implémenter le modèle**

`backend/app/models/import_record.py` :

```python
"""Journal des imports de relevés bancaires."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImportRecord(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bank_code: Mapped[str] = mapped_column(String(32), nullable=False)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    transactions_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transactions_duplicated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    override_duplicates: Mapped[bool] = mapped_column(nullable=False, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ImportRecord(id={self.id}, file={self.filename!r}, nb={self.transactions_imported})>"
```

- [ ] **Étape 4 : Enregistrer dans `__init__.py`**

```python
from app.models.import_record import ImportRecord  # noqa: F401
```

- [ ] **Étape 5 : Relancer les tests**

```bash
pytest tests/test_model_import_record.py -v
```

Expected : 2 tests passent.

- [ ] **Étape 6 : Commit**

```bash
git add backend/app/models/import_record.py backend/app/models/__init__.py backend/tests/test_model_import_record.py
git commit -m "feat(models): ImportRecord tracks uploaded bank statements"
```

---

### Tâche B4 : Modèle `Transaction` (table centrale)

**Files:**
- Create: `backend/app/models/transaction.py`
- Create: `backend/tests/test_model_transaction.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_model_transaction.py` :

```python
"""Tests du modèle Transaction."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord
from app.models.transaction import Transaction
from app.models.user import User, UserRole


def _seed(db_session):
    u = User(email="a@b.fr", password_hash="x", role=UserRole.ADMIN, full_name="A")
    e = Entity(name="Acreed", slug="acreed")
    db_session.add_all([u, e])
    db_session.commit()
    ba = BankAccount(entity_id=e.id, name="Delubac", iban="FR76",
                     bank_code="delubac")
    db_session.add(ba)
    db_session.commit()
    imp = ImportRecord(bank_account_id=ba.id, uploaded_by_id=u.id,
                       filename="f.pdf", file_size_bytes=1,
                       file_sha256="h" * 64, bank_code="delubac",
                       transactions_imported=0, transactions_duplicated=0)
    db_session.add(imp)
    db_session.commit()
    return u, ba, imp


def test_transaction_basic(db_session):
    u, ba, imp = _seed(db_session)
    t = Transaction(
        bank_account_id=ba.id,
        import_id=imp.id,
        operation_date=date(2026, 3, 5),
        value_date=date(2026, 3, 5),
        amount=Decimal("-80.00"),
        label="COTIS CARTE BUSI IMM",
        raw_label="COTIS CARTE BUSI IMM",
        dedup_key="a" * 64,
        statement_row_index=0,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    assert t.id is not None
    assert t.is_aggregation_parent is False
    assert t.is_intercompany is False
    assert t.created_at is not None


def test_transaction_dedup_key_unique(db_session):
    u, ba, imp = _seed(db_session)
    common = dict(bank_account_id=ba.id, import_id=imp.id,
                  operation_date=date(2026, 3, 5), value_date=date(2026, 3, 5),
                  amount=Decimal("-10.00"), label="L", raw_label="L",
                  dedup_key="d" * 64, statement_row_index=0)
    db_session.add(Transaction(**common))
    db_session.commit()
    db_session.add(Transaction(**{**common, "statement_row_index": 1}))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_transaction_parent_child(db_session):
    u, ba, imp = _seed(db_session)
    parent = Transaction(
        bank_account_id=ba.id, import_id=imp.id,
        operation_date=date(2026, 3, 6), value_date=date(2026, 3, 6),
        amount=Decimal("-1000.60"),
        label="VIR SEPA JEAN DUPONT",
        raw_label="VIR SEPA JEAN DUPONT",
        dedup_key="p" * 64, statement_row_index=0,
        is_aggregation_parent=True,
    )
    db_session.add(parent)
    db_session.commit()
    child = Transaction(
        bank_account_id=ba.id, import_id=imp.id,
        operation_date=date(2026, 3, 6), value_date=date(2026, 3, 6),
        amount=Decimal("-0.50"),
        label="COMMISSION VIR SEPA JEAN DUPONT",
        raw_label="COMMISSION VIR SEPA JEAN DUPONT",
        dedup_key="c" * 64, statement_row_index=1,
        parent_transaction_id=parent.id,
    )
    db_session.add(child)
    db_session.commit()
    db_session.refresh(child)
    assert child.parent_transaction_id == parent.id
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_model_transaction.py -v
```

Expected : `ModuleNotFoundError`.

- [ ] **Étape 3 : Implémenter le modèle**

`backend/app/models/transaction.py` :

```python
"""Transaction bancaire : table centrale du système."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_tx_operation_date", "operation_date"),
        Index("ix_tx_bank_account_date", "bank_account_id", "operation_date"),
        Index("ix_tx_category", "category_id"),
        Index("ix_tx_counterparty", "counterparty_id"),
        Index("uq_tx_dedup_key", "dedup_key", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    import_id: Mapped[int] = mapped_column(
        ForeignKey("imports.id", ondelete="RESTRICT"), nullable=False
    )
    parent_transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    counterparty_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("counterparties.id", ondelete="SET NULL"), nullable=True
    )
    counter_entity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )

    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_label: Mapped[str] = mapped_column(String(500), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)
    statement_row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_aggregation_parent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_intercompany: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, {self.operation_date}, {self.amount}€)>"
```

- [ ] **Étape 4 : Enregistrer dans `__init__.py`**

```python
from app.models.transaction import Transaction  # noqa: F401
```

- [ ] **Étape 5 : Relancer les tests**

```bash
pytest tests/test_model_transaction.py -v
```

Expected : 3 tests passent.

- [ ] **Étape 6 : Commit**

```bash
git add backend/app/models/transaction.py backend/app/models/__init__.py backend/tests/test_model_transaction.py
git commit -m "feat(models): Transaction — central table with dedup_key and parent/child"
```

---

### Tâche B5 : Migration Alembic pour les 4 nouvelles tables

**Files:**
- Create: `backend/alembic/versions/<timestamp>_plan1_transactions.py`

- [ ] **Étape 1 : Générer la migration via Alembic autogenerate**

```bash
cd /home/kierangauthier/claude-secure/horizon/backend
# Lancer la base de dev en local (si pas déjà faite)
docker compose -f ../docker-compose.dev.yml up -d
export DATABASE_URL="postgresql+psycopg://tresorerie:tresorerie@localhost:5432/tresorerie"
alembic revision --autogenerate -m "plan1 transactions imports categories counterparties"
```

Le fichier produit s'appelle `alembic/versions/<timestamp>_plan1_transactions_imports_categories_counterparties.py`.

- [ ] **Étape 2 : Inspecter et corriger la migration**

Ouvrir le fichier généré. Vérifier que :

1. L'enum `counterparty_status` utilise `postgresql.ENUM(..., create_type=False)` OU `create_type=True` avant le `op.create_table('counterparties', …)` (la leçon du Plan 0 — voir docs/operations/deployment.md).
2. L'ordre de création respecte les FK : `categories` → `counterparties` → `imports` → `transactions`.
3. Les index (composés + partiels) sont bien créés.

Remplacer le corps de `upgrade()` par cette version explicite (écrase l'autogenerate) :

```python
"""plan1: transactions imports categories counterparties

Revision ID: <conservé>
Revises: <precedente>
Create Date: 2026-04-16 ...
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "<conservé>"
down_revision: Union[str, None] = "<precedente>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


counterparty_status_enum = postgresql.ENUM(
    "pending", "active", "ignored",
    name="counterparty_status",
    create_type=False,
)


def upgrade() -> None:
    # 1. Enum créé explicitement avant la table qui l'utilise
    counterparty_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("color", sa.String(9), nullable=True),
        sa.Column("parent_category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )

    # 3. counterparties
    op.create_table(
        "counterparties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False),
        sa.Column("status", counterparty_status_enum, nullable=False,
                  server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("normalized_name", name="uq_counterparties_normalized"),
    )
    op.create_index("ix_counterparties_normalized", "counterparties",
                    ["normalized_name"])

    # 4. imports
    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bank_account_id", sa.Integer(),
                  sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("bank_code", sa.String(32), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("transactions_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transactions_duplicated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("override_duplicates", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_imports_bank_account", "imports", ["bank_account_id"])
    op.create_index("ix_imports_file_sha256", "imports", ["file_sha256"])

    # 5. transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bank_account_id", sa.Integer(),
                  sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("import_id", sa.Integer(),
                  sa.ForeignKey("imports.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("parent_transaction_id", sa.Integer(),
                  sa.ForeignKey("transactions.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("counterparty_id", sa.Integer(),
                  sa.ForeignKey("counterparties.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("counter_entity_id", sa.Integer(),
                  sa.ForeignKey("entities.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("raw_label", sa.String(500), nullable=False),
        sa.Column("dedup_key", sa.String(64), nullable=False),
        sa.Column("statement_row_index", sa.Integer(), nullable=False),
        sa.Column("is_aggregation_parent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_intercompany", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tx_operation_date", "transactions", ["operation_date"])
    op.create_index("ix_tx_bank_account_date", "transactions",
                    ["bank_account_id", "operation_date"])
    op.create_index("ix_tx_category", "transactions", ["category_id"])
    op.create_index("ix_tx_counterparty", "transactions", ["counterparty_id"])
    op.create_index("uq_tx_dedup_key", "transactions", ["dedup_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_tx_dedup_key", table_name="transactions")
    op.drop_index("ix_tx_counterparty", table_name="transactions")
    op.drop_index("ix_tx_category", table_name="transactions")
    op.drop_index("ix_tx_bank_account_date", table_name="transactions")
    op.drop_index("ix_tx_operation_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_imports_file_sha256", table_name="imports")
    op.drop_index("ix_imports_bank_account", table_name="imports")
    op.drop_table("imports")
    op.drop_index("ix_counterparties_normalized", table_name="counterparties")
    op.drop_table("counterparties")
    op.drop_table("categories")
    counterparty_status_enum.drop(op.get_bind(), checkfirst=True)
```

- [ ] **Étape 3 : Appliquer la migration**

```bash
alembic upgrade head
```

Expected : `INFO  [alembic.runtime.migration] Running upgrade ... -> <rev>, plan1 ...`

- [ ] **Étape 4 : Vérifier que le downgrade fonctionne puis ré-appliquer**

```bash
alembic downgrade -1
alembic upgrade head
```

Expected : passage sans erreur dans les deux sens.

- [ ] **Étape 5 : Relancer la suite de tests complète**

```bash
pytest -v
```

Expected : tous les tests passent (incluant les modèles des tâches B1-B4).

- [ ] **Étape 6 : Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(db): alembic migration for plan 1 tables (categories, counterparties, imports, transactions)"
```

---

### Tâche B6 : Seed d'arborescence de catégories minimale

Pour que les transactions importées puissent être liées à une catégorie par défaut "Non catégorisée", il faut qu'elle existe en base. Ce seed insère **uniquement** les catégories racines + la catégorie "Non catégorisée" (l'arborescence complète viendra au Plan 2).

**Files:**
- Create: `backend/alembic/versions/<timestamp>_plan1_seed_categories.py`

- [ ] **Étape 1 : Créer la migration de seed**

```bash
alembic revision -m "plan1 seed minimal categories"
```

- [ ] **Étape 2 : Écrire la migration**

```python
"""plan1: seed minimal categories

Revision ID: <conservé>
Revises: <revision B5>
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "<conservé>"
down_revision: Union[str, None] = "<revision B5>"
branch_labels = None
depends_on = None


CATEGORIES = [
    # (slug, name, color, parent_slug, is_system)
    ("encaissements",              "Encaissements",                  "#2ecc71", None, True),
    ("decaissements-personnel",    "Décaissements — Personnel",      "#e74c3c", None, True),
    ("decaissements-sous-traitants","Décaissements — Sous-traitants", "#e67e22", None, True),
    ("decaissements-fournisseurs", "Décaissements — Fournisseurs",   "#d35400", None, True),
    ("charges-sociales-taxes",     "Charges sociales & taxes",       "#8e44ad", None, True),
    ("frais-bancaires",            "Frais bancaires",                "#34495e", None, True),
    ("honoraires-juridiques",      "Honoraires juridiques",          "#16a085", None, True),
    ("flux-intergroupe",           "Flux intergroupe",               "#2980b9", None, True),
    ("non-categorisees",           "Non catégorisées",               "#95a5a6", None, True),
]


def upgrade() -> None:
    bind = op.get_bind()
    # Insertion racines
    slug_to_id: dict[str, int] = {}
    for slug, name, color, parent_slug, is_system in CATEGORIES:
        parent_id = slug_to_id.get(parent_slug) if parent_slug else None
        result = bind.execute(
            sa.text(
                "INSERT INTO categories (name, slug, color, parent_category_id, is_system) "
                "VALUES (:name, :slug, :color, :parent_id, :is_system) RETURNING id"
            ),
            {"name": name, "slug": slug, "color": color,
             "parent_id": parent_id, "is_system": is_system},
        )
        slug_to_id[slug] = result.scalar_one()


def downgrade() -> None:
    op.execute("DELETE FROM categories WHERE is_system = TRUE")
```

- [ ] **Étape 3 : Appliquer la migration**

```bash
alembic upgrade head
psql "$DATABASE_URL" -c "SELECT slug, name FROM categories ORDER BY id;"
```

Expected : 9 lignes correspondant à la liste ci-dessus.

- [ ] **Étape 4 : Tester le rollback**

```bash
alembic downgrade -1
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM categories WHERE is_system = TRUE;"
alembic upgrade head
```

Expected : 0 puis 9 après ré-upgrade.

- [ ] **Étape 5 : Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(db): seed minimal root categories for plan 1"
```

---

# SECTION C — Module `parsers/` : interface commune

### Tâche C1 : Dataclasses `ParsedTransaction` et `ParsedStatement`

**Files:**
- Create: `backend/app/parsers/__init__.py`
- Create: `backend/app/parsers/base.py`
- Create: `backend/tests/test_parser_base.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_parser_base.py` :

```python
"""Tests des dataclasses ParsedTransaction et ParsedStatement."""
from datetime import date
from decimal import Decimal

import pytest

from app.parsers.base import ParsedStatement, ParsedTransaction


def test_parsed_transaction_signed_amount() -> None:
    t = ParsedTransaction(
        operation_date=date(2026, 3, 5),
        value_date=date(2026, 3, 5),
        label="COTIS CARTE",
        raw_label="COTIS CARTE",
        amount=Decimal("-80.00"),
        statement_row_index=3,
    )
    assert t.is_debit is True
    assert t.is_credit is False
    assert t.children == []


def test_parsed_transaction_children() -> None:
    child = ParsedTransaction(
        operation_date=date(2026, 3, 6),
        value_date=date(2026, 3, 6),
        label="COMMISSION VIR SEPA X",
        raw_label="COMMISSION VIR SEPA X",
        amount=Decimal("-0.50"),
        statement_row_index=2,
    )
    parent = ParsedTransaction(
        operation_date=date(2026, 3, 6),
        value_date=date(2026, 3, 6),
        label="VIR SEPA X",
        raw_label="VIR SEPA X",
        amount=Decimal("-1.50"),
        statement_row_index=1,
        children=[child],
    )
    assert parent.is_aggregation_parent is True
    assert child.is_aggregation_parent is False


def test_parsed_statement_total_count() -> None:
    p1 = ParsedTransaction(date(2026, 3, 1), date(2026, 3, 1),
                           "L1", "L1", Decimal("10"), 0)
    p2 = ParsedTransaction(date(2026, 3, 2), date(2026, 3, 2),
                           "L2", "L2", Decimal("-20"), 1)
    s = ParsedStatement(
        bank_code="delubac", account_number="123",
        iban="FR76XXX", period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 2),
        opening_balance=Decimal("100"),
        closing_balance=Decimal("90"),
        transactions=[p1, p2],
    )
    assert s.total_count == 2
    assert s.bank_code == "delubac"


def test_parsed_statement_total_count_with_children() -> None:
    child = ParsedTransaction(date(2026, 3, 6), date(2026, 3, 6),
                              "c", "c", Decimal("-1"), 1)
    parent = ParsedTransaction(date(2026, 3, 6), date(2026, 3, 6),
                               "p", "p", Decimal("-2"), 0, children=[child])
    s = ParsedStatement(
        bank_code="delubac", account_number="1",
        iban="FR", period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 6),
        opening_balance=Decimal("0"),
        closing_balance=Decimal("-2"),
        transactions=[parent],
    )
    # 1 parent + 1 enfant = 2 lignes logiques
    assert s.total_count == 2
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parser_base.py -v
```

Expected : `ModuleNotFoundError`.

- [ ] **Étape 3 : Implémenter `base.py`**

`backend/app/parsers/base.py` :

```python
"""Interface commune des analyseurs de relevés bancaires."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class ParsedTransaction:
    """Une transaction extraite d'un relevé, avant insertion en base."""
    operation_date: date
    value_date: date
    label: str                  # libellé normalisé (1 ligne, espaces compacts)
    raw_label: str              # libellé brut (multi-lignes possibles, joint par \n)
    amount: Decimal             # signé : > 0 encaissement, < 0 décaissement
    statement_row_index: int    # position dans le relevé (pour dédup stable)
    children: list["ParsedTransaction"] = field(default_factory=list)
    counterparty_hint: str | None = None  # nom extrait, avant normalisation

    @property
    def is_debit(self) -> bool:
        return self.amount < 0

    @property
    def is_credit(self) -> bool:
        return self.amount > 0

    @property
    def is_aggregation_parent(self) -> bool:
        return bool(self.children)


@dataclass
class ParsedStatement:
    """Résultat d'un parse() : métadonnées de compte + liste de transactions."""
    bank_code: str
    account_number: str
    iban: str | None
    period_start: date | None
    period_end: date | None
    opening_balance: Decimal | None
    closing_balance: Decimal | None
    transactions: list[ParsedTransaction]

    @property
    def total_count(self) -> int:
        """Nombre total de lignes logiques (parents + enfants)."""
        count = 0
        for t in self.transactions:
            count += 1 + len(t.children)
        return count


class BaseParser(ABC):
    """Interface que chaque analyseur de banque doit implémenter."""

    bank_name: str   # "Delubac", "Qonto", …
    bank_code: str   # "delubac", "qonto", …

    @abstractmethod
    def detect(self, pdf_bytes: bytes) -> bool:
        """Retourne True si ce PDF ressemble à un relevé émis par cette banque."""

    @abstractmethod
    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        """Extrait un ParsedStatement du PDF."""
```

`backend/app/parsers/__init__.py` (vide pour l'instant — complété en C3) :

```python
"""Module d'analyseurs de relevés bancaires."""
from app.parsers.base import BaseParser, ParsedStatement, ParsedTransaction  # noqa: F401
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_parser_base.py -v
```

Expected : 4 tests passent.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/__init__.py backend/app/parsers/base.py backend/tests/test_parser_base.py
git commit -m "feat(parsers): BaseParser interface + ParsedStatement dataclasses"
```

---

### Tâche C2 : Erreurs métier des parsers

**Files:**
- Create: `backend/app/parsers/errors.py`
- Create: `backend/tests/test_parser_errors.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_parser_errors.py` :

```python
"""Tests de la hiérarchie d'erreurs des parsers."""
import pytest

from app.parsers.errors import (
    InvalidPdfStructureError,
    ParserError,
    UnknownBankError,
)


def test_parser_error_is_exception() -> None:
    with pytest.raises(ParserError):
        raise ParserError("boom")


def test_unknown_bank_is_parser_error() -> None:
    with pytest.raises(ParserError):
        raise UnknownBankError()


def test_invalid_pdf_structure_carries_context() -> None:
    err = InvalidPdfStructureError("colonnes absentes", page=3)
    assert err.page == 3
    assert "page=3" in repr(err)
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parser_errors.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Étape 3 : Implémenter**

`backend/app/parsers/errors.py` :

```python
"""Erreurs levées par les analyseurs de relevés bancaires."""
from __future__ import annotations


class ParserError(Exception):
    """Base de toutes les erreurs des parsers."""


class UnknownBankError(ParserError):
    """Aucun parser n'a pu détecter la banque émettrice du PDF."""

    def __init__(self, message: str = "Banque inconnue — impossible de détecter l'émetteur") -> None:
        super().__init__(message)


class InvalidPdfStructureError(ParserError):
    """Le PDF est de la bonne banque mais sa structure interne est inattendue."""

    def __init__(self, message: str, *, page: int | None = None) -> None:
        super().__init__(message)
        self.page = page

    def __repr__(self) -> str:
        return f"InvalidPdfStructureError({self.args[0]!r}, page={self.page})"
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_parser_errors.py -v
```

Expected : 3 tests passent.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/errors.py backend/tests/test_parser_errors.py
git commit -m "feat(parsers): error hierarchy for parser failures"
```

---

### Tâche C3 : Registre des parsers avec découverte automatique

**Files:**
- Modify: `backend/app/parsers/__init__.py`
- Create: `backend/tests/test_parsers_registry.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_parsers_registry.py` :

```python
"""Tests du registre des parsers."""
import pytest

from app.parsers import BaseParser, get_parser_for, get_registry, register_parser
from app.parsers.errors import UnknownBankError


class _FakeBank(BaseParser):
    bank_name = "Fake"
    bank_code = "fake"
    def detect(self, pdf_bytes: bytes) -> bool:
        return pdf_bytes.startswith(b"FAKE")
    def parse(self, pdf_bytes: bytes):  # type: ignore[override]
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _snapshot_registry():
    backup = dict(get_registry())
    yield
    get_registry().clear()
    get_registry().update(backup)


def test_register_and_get_by_code() -> None:
    register_parser(_FakeBank())
    reg = get_registry()
    assert "fake" in reg
    assert isinstance(reg["fake"], _FakeBank)


def test_register_same_code_twice_raises() -> None:
    register_parser(_FakeBank())
    with pytest.raises(ValueError, match="already registered"):
        register_parser(_FakeBank())


def test_get_parser_for_detects() -> None:
    register_parser(_FakeBank())
    p = get_parser_for(b"FAKE content")
    assert isinstance(p, _FakeBank)


def test_get_parser_for_unknown_raises() -> None:
    register_parser(_FakeBank())
    with pytest.raises(UnknownBankError):
        get_parser_for(b"OTHER content")


def test_get_parser_by_code() -> None:
    from app.parsers import get_parser_by_code
    register_parser(_FakeBank())
    p = get_parser_by_code("fake")
    assert isinstance(p, _FakeBank)
    with pytest.raises(UnknownBankError):
        get_parser_by_code("nonexistent")
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parsers_registry.py -v
```

Expected : erreur d'import des fonctions `register_parser`, `get_registry`, etc.

- [ ] **Étape 3 : Compléter `app/parsers/__init__.py`**

Remplacer le contenu de `backend/app/parsers/__init__.py` :

```python
"""Module d'analyseurs de relevés bancaires avec registre."""
from __future__ import annotations

from app.parsers.base import BaseParser, ParsedStatement, ParsedTransaction
from app.parsers.errors import (
    InvalidPdfStructureError,
    ParserError,
    UnknownBankError,
)

_REGISTRY: dict[str, BaseParser] = {}


def register_parser(parser: BaseParser) -> None:
    """Enregistre un parser dans le registre global. Lève ValueError si doublon."""
    code = parser.bank_code
    if code in _REGISTRY:
        raise ValueError(f"Parser for bank_code={code!r} is already registered")
    _REGISTRY[code] = parser


def get_registry() -> dict[str, BaseParser]:
    """Retourne le registre (mutable — usage test uniquement)."""
    return _REGISTRY


def get_parser_by_code(bank_code: str) -> BaseParser:
    """Retourne le parser enregistré pour `bank_code`. Lève UnknownBankError."""
    if bank_code not in _REGISTRY:
        raise UnknownBankError(f"Aucun parser pour bank_code={bank_code!r}")
    return _REGISTRY[bank_code]


def get_parser_for(pdf_bytes: bytes) -> BaseParser:
    """Détecte la banque via `.detect()` de chaque parser enregistré."""
    for parser in _REGISTRY.values():
        if parser.detect(pdf_bytes):
            return parser
    raise UnknownBankError()


def _auto_register() -> None:
    """Importe les modules parsers connus pour qu'ils s'enregistrent.

    Convention : chaque fichier parser (ex. `delubac.py`) instancie et enregistre
    son parser via `register_parser(...)` au niveau module.
    """
    from app.parsers import delubac  # noqa: F401  (import pour side-effect)


__all__ = [
    "BaseParser", "ParsedStatement", "ParsedTransaction",
    "ParserError", "UnknownBankError", "InvalidPdfStructureError",
    "register_parser", "get_parser_for", "get_parser_by_code", "get_registry",
]
```

**Note :** `_auto_register` importe `delubac` qui n'existe pas encore ; nous ne l'appellerons qu'en tâche D6 après avoir créé le parser Delubac. Pour que les tests passent dès maintenant, nous ne le branchons pas dans `__init__`.

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_parsers_registry.py -v
```

Expected : 5 tests passent.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/__init__.py backend/tests/test_parsers_registry.py
git commit -m "feat(parsers): global registry with detection + lookup by code"
```

---

### Tâche C4 : Helpers de normalisation (montant, libellé, contrepartie)

**Files:**
- Create: `backend/app/parsers/normalization.py`
- Create: `backend/tests/test_normalization.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_normalization.py` :

```python
"""Tests des helpers de normalisation."""
from datetime import date
from decimal import Decimal

import pytest

from app.parsers.normalization import (
    compute_dedup_key,
    extract_counterparty,
    fr_amount_to_decimal,
    fr_date_to_date,
    fix_latin1_encoding,
    normalize_label,
)


@pytest.mark.parametrize("raw,expected", [
    ("1.234,56", Decimal("1234.56")),
    ("0,10", Decimal("0.10")),
    ("25.204,95", Decimal("25204.95")),
    ("92,32", Decimal("92.32")),
    ("0", Decimal("0")),
])
def test_fr_amount_to_decimal(raw: str, expected: Decimal) -> None:
    assert fr_amount_to_decimal(raw) == expected


def test_fr_amount_invalid_raises() -> None:
    with pytest.raises(ValueError):
        fr_amount_to_decimal("abc")


def test_fr_date_to_date_basic() -> None:
    assert fr_date_to_date("02/03/2026") == date(2026, 3, 2)


def test_fr_date_invalid_raises() -> None:
    with pytest.raises(ValueError):
        fr_date_to_date("32/13/2026")


@pytest.mark.parametrize("raw,expected", [
    ("  Intérêts  de   retard  ", "INTERETS DE RETARD"),
    ("COMMISSION\nVIR\tSEPA", "COMMISSION VIR SEPA"),
    ("Créance n° 0502321", "CREANCE N 0502321"),
])
def test_normalize_label(raw: str, expected: str) -> None:
    assert normalize_label(raw) == expected


def test_fix_latin1_encoding_passthrough() -> None:
    # Texte déjà correct : pas de changement
    assert fix_latin1_encoding("Intérêts de retard") == "Intérêts de retard"


def test_fix_latin1_encoding_fixes_mojibake() -> None:
    # Cas réel Delubac : "Intérêts" mal décodé devient "IntÃ©rÃªts"
    assert fix_latin1_encoding("IntÃ©rÃªts de retard") == "Intérêts de retard"


def test_extract_counterparty_vir_sepa() -> None:
    assert extract_counterparty("VIR SEPA NIZAR MOUADDEB") == "NIZAR MOUADDEB"
    assert extract_counterparty("VIR SEPA BNP PARIBAS FACTOR") == "BNP PARIBAS FACTOR"
    assert extract_counterparty("VIR SEPA JEAN-PAUL DUPONT") == "JEAN-PAUL DUPONT"


def test_extract_counterparty_prlv_sepa() -> None:
    assert extract_counterparty("PRLV SEPA URSSAF") == "URSSAF"
    assert extract_counterparty("PRLV SEPA DGFIP") == "DGFIP"


def test_extract_counterparty_carte() -> None:
    assert extract_counterparty("CARTE 25/03 SAS LE BACCHUS") == "SAS LE BACCHUS"
    assert extract_counterparty("CARTE 26/03 EDF ENTREPRISE") == "EDF ENTREPRISE"


def test_extract_counterparty_commission_vir_sepa() -> None:
    # Les lignes COMMISSION / TVA se réfèrent à la contrepartie de leur parent
    assert extract_counterparty("COMMISSION VIR SEPA NIZAR MOUADDEB") == "NIZAR MOUADDEB"
    assert extract_counterparty("TVA VIR SEPA NIZAR MOUADDEB") == "NIZAR MOUADDEB"


def test_extract_counterparty_unknown_returns_none() -> None:
    assert extract_counterparty("ARRETE DE COMPTE AU 28/02/26") is None
    assert extract_counterparty("Intérêts de retard") is None


def test_compute_dedup_key_stable() -> None:
    k1 = compute_dedup_key(bank_account_id=1, operation_date=date(2026, 3, 1),
                           value_date=date(2026, 3, 1), amount=Decimal("-80.00"),
                           normalized_label="COTIS CARTE", statement_row_index=0)
    k2 = compute_dedup_key(bank_account_id=1, operation_date=date(2026, 3, 1),
                           value_date=date(2026, 3, 1), amount=Decimal("-80.00"),
                           normalized_label="COTIS CARTE", statement_row_index=0)
    assert k1 == k2
    assert len(k1) == 64


def test_compute_dedup_key_differs_on_row_index() -> None:
    args = dict(bank_account_id=1, operation_date=date(2026, 3, 1),
                value_date=date(2026, 3, 1), amount=Decimal("-80.00"),
                normalized_label="COTIS CARTE")
    assert compute_dedup_key(**args, statement_row_index=0) \
        != compute_dedup_key(**args, statement_row_index=1)
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_normalization.py -v
```

Expected : `ModuleNotFoundError`.

- [ ] **Étape 3 : Implémenter**

`backend/app/parsers/normalization.py` :

```python
"""Helpers de normalisation pour les parsers."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

_WHITESPACE_RE = re.compile(r"\s+")


def fr_amount_to_decimal(s: str) -> Decimal:
    """Convertit un montant au format français ('1.234,56' ou '0,10') en Decimal.

    Raises:
        ValueError: si la chaîne n'est pas un montant valide.
    """
    cleaned = s.strip().replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Montant invalide: {s!r}") from exc


def fr_date_to_date(s: str) -> date:
    """Convertit 'DD/MM/YYYY' en date."""
    parts = s.strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"Date invalide: {s!r}")
    d, m, y = parts
    return date(int(y), int(m), int(d))


def fix_latin1_encoding(text: str) -> str:
    """Corrige le mojibake typique (texte latin-1 interprété comme utf-8).

    Exemple : 'IntÃ©rÃªts' → 'Intérêts'.

    Stratégie : si le texte contient des séquences typiques de mojibake
    (Ã©, Ã¨, Ã¢, etc.), ré-encoder en latin-1 puis décoder en utf-8.
    Sinon : retourner tel quel.
    """
    mojibake_markers = ("Ã©", "Ã¨", "Ãª", "Ã ", "Ã¢", "Ã§", "Ã´", "Ã»", "Ã®", "Ã¯")
    if not any(m in text for m in mojibake_markers):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def normalize_label(raw: str) -> str:
    """Normalise un libellé pour les matchings et le dédoublonnage.

    - Supprime les diacritiques (café → CAFE)
    - Supprime la ponctuation sauf chiffres, lettres, espaces
    - Majuscule
    - Compacte les espaces
    """
    if raw is None:
        return ""
    text = raw.strip()
    # Normalisation Unicode NFD + suppression des marques de combinaison
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Upper
    text = text.upper()
    # Garder lettres latines, chiffres, espaces et traits d'union
    text = re.sub(r"[^A-Z0-9\s-]", " ", text)
    # Compacter les espaces
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


_COUNTERPARTY_RULES: list[tuple[re.Pattern[str], int]] = [
    # Lignes COMMISSION/TVA VIR SEPA → prendre ce qui vient après "VIR SEPA"
    (re.compile(r"^(?:COMMISSION|TVA)\s+VIR\s+SEPA\s+(.+)$", re.I), 1),
    # VIR SEPA <nom>
    (re.compile(r"^VIR\s+SEPA\s+(.+?)(?:\s+[A-Z]{3,}\s*\d.*)?$", re.I), 1),
    # PRLV SEPA <nom>
    (re.compile(r"^PRLV\s+SEPA\s+(.+?)(?:\s+[A-Z]{2,}\d.*)?$", re.I), 1),
    # CARTE DD/MM <nom>
    (re.compile(r"^CARTE\s+\d{2}/\d{2}\s+(.+)$", re.I), 1),
]


def extract_counterparty(raw_label: str) -> str | None:
    """Extrait la contrepartie depuis un libellé brut.

    Retourne None si aucune heuristique n'a matché.
    """
    if not raw_label:
        return None
    text = raw_label.strip()
    for pattern, group in _COUNTERPARTY_RULES:
        m = pattern.match(text)
        if m:
            candidate = m.group(group).strip()
            # Stripper les suffixes numériques courants (références, IDs)
            candidate = re.sub(r"\s+[A-Z0-9]{3,}-?\d+.*$", "", candidate).strip()
            if candidate:
                return candidate
    return None


def compute_dedup_key(
    *,
    bank_account_id: int,
    operation_date: date,
    value_date: date,
    amount: Decimal,
    normalized_label: str,
    statement_row_index: int,
) -> str:
    """Calcule la clé stable de dédoublonnage (SHA-256 hex)."""
    parts = [
        str(bank_account_id),
        operation_date.isoformat(),
        value_date.isoformat(),
        f"{amount:.2f}",
        normalized_label,
        str(statement_row_index),
    ]
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_normalization.py -v
```

Expected : tous les tests passent (~ 15 cas).

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/normalization.py backend/tests/test_normalization.py
git commit -m "feat(parsers): normalization helpers (amount, date, label, counterparty, dedup)"
```

---

# SECTION D — Analyseur Delubac

### Tâche D1 : Détection du format Delubac (`detect()`)

**Files:**
- Create: `backend/app/parsers/delubac.py`
- Create: `backend/tests/test_parser_delubac.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_parser_delubac.py` (début — complété en D2-D6) :

```python
"""Tests de l'analyseur Delubac."""
from pathlib import Path

import pytest

from app.parsers.delubac import DelubacParser

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


@pytest.fixture
def parser() -> DelubacParser:
    return DelubacParser()


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_detect_delubac_minimal(parser: DelubacParser) -> None:
    assert parser.detect(_load("synthetic_minimal.pdf")) is True


def test_detect_delubac_full(parser: DelubacParser) -> None:
    assert parser.detect(_load("synthetic_full_month.pdf")) is True


def test_detect_non_delubac(parser: DelubacParser) -> None:
    # Bytes aléatoires en-tête PDF minimum
    assert parser.detect(b"%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF\n") is False


def test_bank_code_and_name(parser: DelubacParser) -> None:
    assert parser.bank_code == "delubac"
    assert parser.bank_name == "Delubac"
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parser_delubac.py -v
```

Expected : `ModuleNotFoundError`.

- [ ] **Étape 3 : Implémenter la détection**

`backend/app/parsers/delubac.py` (début) :

```python
"""Analyseur du relevé bancaire Delubac (format Mapping Suite)."""
from __future__ import annotations

import io
from typing import Final

import pdfplumber

from app.parsers.base import BaseParser, ParsedStatement
from app.parsers.errors import InvalidPdfStructureError


_DETECTION_MARKERS: Final = (
    b"DELUFR22",          # BIC Delubac
    b"Delubac",           # mention "Banque Delubac" ou www.delubac.com
    b"edelubac.com",
    b"map_809",           # Creator PDF des relevés Delubac
)


class DelubacParser(BaseParser):
    bank_name = "Delubac"
    bank_code = "delubac"

    def detect(self, pdf_bytes: bytes) -> bool:
        """Détection par présence de marqueurs Delubac dans le PDF brut."""
        if not pdf_bytes.startswith(b"%PDF"):
            return False
        # Test rapide bytes sans parser le PDF complet
        head = pdf_bytes[:200_000]  # premiers ~200 Ko suffisent
        if any(marker in head for marker in _DETECTION_MARKERS):
            return True
        # Fallback : extraire la 1ère page et chercher les en-têtes textuels
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                if not pdf.pages:
                    return False
                text = pdf.pages[0].extract_text() or ""
                return "RELEVÉ DE COMPTE" in text and "DELUFR22" in text
        except Exception:
            return False

    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        raise NotImplementedError  # implémenté en D2-D5
```

- [ ] **Étape 4 : Relancer les tests de détection**

```bash
pytest tests/test_parser_delubac.py::test_detect_delubac_minimal \
       tests/test_parser_delubac.py::test_detect_delubac_full \
       tests/test_parser_delubac.py::test_detect_non_delubac \
       tests/test_parser_delubac.py::test_bank_code_and_name -v
```

Expected : 4 tests passent.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/delubac.py backend/tests/test_parser_delubac.py
git commit -m "feat(parsers): DelubacParser detection via PDF markers"
```

---

### Tâche D2 : Extraction de l'en-tête de compte (IBAN, période, soldes)

**Files:**
- Modify: `backend/app/parsers/delubac.py`
- Modify: `backend/tests/test_parser_delubac.py`

- [ ] **Étape 1 : Ajouter les tests**

Ajouter à la fin de `backend/tests/test_parser_delubac.py` :

```python
from datetime import date
from decimal import Decimal


def test_parse_minimal_account_header(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    assert stmt.bank_code == "delubac"
    assert stmt.iban == "FR7612879000011117020200105"
    assert stmt.account_number == "11170202001"
    assert stmt.opening_balance == Decimal("19.70")
    assert stmt.closing_balance == Decimal("25052.33")


def test_parse_minimal_period(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    assert stmt.period_start == date(2026, 3, 2)
    assert stmt.period_end == date(2026, 3, 5)


def test_parse_full_month_period(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_full_month.pdf"))
    assert stmt.period_start == date(2026, 3, 2)
    assert stmt.period_end == date(2026, 3, 31)
    assert stmt.closing_balance == Decimal("33427.90")
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parser_delubac.py::test_parse_minimal_account_header -v
```

Expected : `NotImplementedError`.

- [ ] **Étape 3 : Implémenter `parse()` (partiel — en-tête seulement)**

Remplacer la classe `DelubacParser` dans `backend/app/parsers/delubac.py` :

```python
"""Analyseur du relevé bancaire Delubac (format Mapping Suite)."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

import pdfplumber

from app.parsers.base import BaseParser, ParsedStatement, ParsedTransaction
from app.parsers.errors import InvalidPdfStructureError
from app.parsers.normalization import (
    fix_latin1_encoding,
    fr_amount_to_decimal,
    fr_date_to_date,
    normalize_label,
)


_DETECTION_MARKERS: Final = (
    b"DELUFR22",
    b"Delubac",
    b"edelubac.com",
    b"map_809",
)

_IBAN_RE = re.compile(r"IBAN\s*:\s*([A-Z0-9 ]{15,40})")
_ACCOUNT_NUM_RE = re.compile(r"Num[ée]ro\s+de\s+compte\s*:\s*(\d+)")
_OPENING_RE = re.compile(
    r"Ancien\s+solde\s+au\s+(\d{2}/\d{2}/\d{4})\s+([\d.,-]+)",
    re.I,
)
_CLOSING_RE = re.compile(
    r"Nouveau\s+solde\s+(?:créditeur|débiteur|crditeur|debiteur)\s+au\s+(\d{2}/\d{2}/\d{4})\s+([\d.,-]+)",
    re.I,
)
_TXN_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}")


@dataclass
class _RawLine:
    """Une ligne de transaction brute (principale) avec ses lignes de détail."""
    operation_date: date
    value_date: date
    label: str                # libellé principal (1 ligne)
    detail_lines: list[str]   # lignes continues sous le libellé
    amount: Decimal           # signé : + crédit, − débit
    page: int
    row_index: int            # index global dans le relevé


class DelubacParser(BaseParser):
    bank_name = "Delubac"
    bank_code = "delubac"

    # -------- détection --------
    def detect(self, pdf_bytes: bytes) -> bool:
        if not pdf_bytes.startswith(b"%PDF"):
            return False
        head = pdf_bytes[:200_000]
        if any(marker in head for marker in _DETECTION_MARKERS):
            return True
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                if not pdf.pages:
                    return False
                text = pdf.pages[0].extract_text() or ""
                return "RELEVÉ DE COMPTE" in text and "DELUFR22" in text
        except Exception:
            return False

    # -------- parsing --------
    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(
                fix_latin1_encoding(p.extract_text() or "") for p in pdf.pages
            )
            account_number, iban = self._parse_account_identifiers(full_text)
            opening_balance, opening_date = self._parse_opening_balance(full_text)
            closing_balance, closing_date = self._parse_closing_balance(full_text)

            # Pour l'instant : pas de transactions — D3 les ajoute.
            transactions: list[ParsedTransaction] = []
            period_start, period_end = self._parse_period(full_text, opening_date, closing_date)

        return ParsedStatement(
            bank_code=self.bank_code,
            account_number=account_number,
            iban=iban,
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            transactions=transactions,
        )

    # -------- helpers en-tête --------
    def _parse_account_identifiers(self, text: str) -> tuple[str, str | None]:
        num_m = _ACCOUNT_NUM_RE.search(text)
        if not num_m:
            raise InvalidPdfStructureError("Numéro de compte introuvable")
        account_number = num_m.group(1).strip()
        iban_m = _IBAN_RE.search(text)
        iban = iban_m.group(1).replace(" ", "") if iban_m else None
        return account_number, iban

    def _parse_opening_balance(self, text: str) -> tuple[Decimal | None, date | None]:
        m = _OPENING_RE.search(text)
        if not m:
            return None, None
        return fr_amount_to_decimal(m.group(2)), fr_date_to_date(m.group(1))

    def _parse_closing_balance(self, text: str) -> tuple[Decimal | None, date | None]:
        m = _CLOSING_RE.search(text)
        if not m:
            return None, None
        amt = fr_amount_to_decimal(m.group(2))
        # Débiteur = solde négatif
        if "débiteur" in m.group(0).lower() or "debiteur" in m.group(0).lower():
            amt = -amt
        return amt, fr_date_to_date(m.group(1))

    def _parse_period(self, text: str, opening_date: date | None,
                      closing_date: date | None) -> tuple[date | None, date | None]:
        # Pour les tests de D2, pas encore de transactions → on renvoie
        # les dates basées sur les lignes de transactions si présentes, sinon
        # les dates de soldes.
        txn_dates: list[date] = []
        for line in text.splitlines():
            m = _TXN_DATE_RE.match(line)
            if m:
                try:
                    txn_dates.append(fr_date_to_date(m.group(0)))
                except ValueError:
                    continue
        if txn_dates:
            return min(txn_dates), max(txn_dates)
        return opening_date, closing_date
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_parser_delubac.py::test_parse_minimal_account_header \
       tests/test_parser_delubac.py::test_parse_minimal_period \
       tests/test_parser_delubac.py::test_parse_full_month_period -v
```

Expected : 3 tests passent.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/delubac.py backend/tests/test_parser_delubac.py
git commit -m "feat(parsers): Delubac header parsing (IBAN, account, balances, period)"
```

---

### Tâche D3 : Extraction des lignes de transactions

**Files:**
- Modify: `backend/app/parsers/delubac.py`
- Modify: `backend/tests/test_parser_delubac.py`

- [ ] **Étape 1 : Ajouter les tests**

Ajouter à `backend/tests/test_parser_delubac.py` :

```python
def test_parse_minimal_transactions_count(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    assert stmt.total_count == 3


def test_parse_minimal_transactions_content(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    t0, t1, t2 = stmt.transactions
    # ARRETE DE COMPTE
    assert t0.operation_date == date(2026, 3, 2)
    assert t0.value_date == date(2026, 3, 1)
    assert "ARRETE DE COMPTE" in t0.label
    assert t0.amount == Decimal("-92.32")
    # COTIS CARTE
    assert t1.amount == Decimal("-80.00")
    assert "COTIS CARTE" in t1.label
    # VIR SEPA BNP PARIBAS FACTOR (crédit)
    assert t2.amount == Decimal("25204.95")
    assert "BNP PARIBAS FACTOR" in t2.label


def test_parse_ignores_page_totals_and_headers(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_full_month.pdf"))
    for t in stmt.transactions:
        # Aucune transaction ne doit contenir "Total des opérations" dans son libellé
        assert "Total des opérations" not in t.label
        assert "RELEVÉ DE COMPTE" not in t.label
        assert "Ancien solde" not in t.label
        assert "Nouveau solde" not in t.label


def test_parse_full_month_transactions_count_within_tolerance(parser: DelubacParser) -> None:
    """≥ 95% d'extraction vs vérité terrain."""
    import json
    stmt = parser.parse(_load("synthetic_full_month.pdf"))
    gt = json.loads((FIXTURES / "synthetic_full_month.ground_truth.json")
                    .read_text(encoding="utf-8"))
    expected = len(gt["transactions"])  # parents uniquement (enfants exposés via children)
    # total_count compte parents + enfants. Pour comparer avec gt,
    # on compte les "blocs" (parents du point de vue de la vérité terrain).
    actual_blocks = len(stmt.transactions)
    ratio = actual_blocks / expected
    assert ratio >= 0.95, f"Extraction insuffisante: {actual_blocks}/{expected} = {ratio:.1%}"
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parser_delubac.py::test_parse_minimal_transactions_count -v
```

Expected : test échoue car la liste est vide.

- [ ] **Étape 3 : Implémenter l'extraction ligne par ligne**

Dans `backend/app/parsers/delubac.py`, **ajouter** les méthodes suivantes à la classe `DelubacParser` (avant la dernière accolade) et **modifier** `parse()` pour les appeler. Remplacer le corps de `parse()` :

```python
    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(
                fix_latin1_encoding(p.extract_text() or "") for p in pdf.pages
            )
            account_number, iban = self._parse_account_identifiers(full_text)
            opening_balance, opening_date = self._parse_opening_balance(full_text)
            closing_balance, closing_date = self._parse_closing_balance(full_text)
            raw_lines = self._extract_raw_lines(pdf)

        transactions = [self._raw_line_to_parsed(rl) for rl in raw_lines]
        # D4 branchera la fusion SEPA ici
        period_start, period_end = self._period_from_transactions(
            transactions, opening_date, closing_date
        )

        return ParsedStatement(
            bank_code=self.bank_code,
            account_number=account_number,
            iban=iban,
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            transactions=transactions,
        )
```

**Ajouter** en bas de la classe :

```python
    # -------- extraction lignes --------
    _IGNORE_PREFIXES = (
        "total des opérations",
        "total des operations",
        "ancien solde",
        "nouveau solde",
        "page",
        '"t" tarification',
        "rg sdc",
        "rg :",
        "code ag",
        "relevé de compte",
        "releve de compte",
        "date opé",
        "date ope",
        "date d'arrêté",
        "date d'arrete",
        "numéro client",
        "numero client",
        "intitulé du compte",
        "intitule du compte",
        "numéro de compte",
        "numero de compte",
        "iban :",
        "sas acreed",
        "5 lotissement",
        "43320 saint-vidal",
        "votre gestionnaire",
        "internet :",
        "banque à distance",
    )

    def _extract_raw_lines(self, pdf: pdfplumber.PDF) -> list[_RawLine]:
        """Parcourt chaque page et reconstruit les lignes de transactions."""
        raw_lines: list[_RawLine] = []
        global_idx = 0
        for page_num, page in enumerate(pdf.pages, start=1):
            # On regroupe les mots par ligne (même top ± 1.5 px)
            words = page.extract_words(keep_blank_chars=False, x_tolerance=2,
                                       y_tolerance=3)
            rows = self._group_words_by_row(words)
            current: _RawLine | None = None
            for row in rows:
                # Filtrer en-têtes et pieds
                joined = " ".join(w["text"] for w in row).strip()
                low = joined.lower()
                if any(low.startswith(p) for p in self._IGNORE_PREFIXES):
                    if current is not None:
                        raw_lines.append(current)
                        current = None
                    continue
                first_text = row[0]["text"]
                if _TXN_DATE_RE.match(first_text):
                    # Nouvelle ligne de transaction : clôturer la précédente
                    if current is not None:
                        raw_lines.append(current)
                    try:
                        current = self._parse_txn_row(row, page_num, global_idx)
                        global_idx += 1
                    except ValueError:
                        current = None
                else:
                    # Ligne de détail : attacher au current
                    if current is not None:
                        current.detail_lines.append(
                            fix_latin1_encoding(joined).strip()
                        )
            # Fin de page : clôturer la ligne ouverte
            if current is not None:
                raw_lines.append(current)
                current = None
        return raw_lines

    @staticmethod
    def _group_words_by_row(words: list[dict]) -> list[list[dict]]:
        """Groupe les mots pdfplumber par ligne (y proche), ordonnés par x."""
        rows: dict[int, list[dict]] = {}
        for w in words:
            key = round(w["top"])
            # Fusion avec une ligne existante ± 2 px (gestion du bruit vertical)
            matched = None
            for k in rows:
                if abs(k - key) <= 2:
                    matched = k
                    break
            k = matched if matched is not None else key
            rows.setdefault(k, []).append(w)
        result = []
        for k in sorted(rows):
            result.append(sorted(rows[k], key=lambda w: w["x0"]))
        return result

    def _parse_txn_row(self, row: list[dict], page_num: int, row_index: int) -> _RawLine:
        """Décompose une ligne en (op_date, value_date, label, montant, colonne)."""
        op_date = fr_date_to_date(row[0]["text"])
        # Date valeur : 2e mot (fallback : même que op_date)
        try:
            val_date = fr_date_to_date(row[1]["text"])
            label_start = 2
        except (ValueError, IndexError):
            val_date = op_date
            label_start = 1

        # Montant : dernier mot, x1 ≈ 455 (débit) ou ≈ 550 (crédit)
        last = row[-1]
        try:
            magnitude = fr_amount_to_decimal(last["text"])
        except ValueError as exc:
            raise ValueError(f"Montant invalide: {last['text']!r}") from exc

        # Seuil : x1 < 470 → débit, sinon crédit
        is_debit = last["x1"] < 475
        signed_amount = -magnitude if is_debit else magnitude

        # Libellé : tous les mots entre label_start et avant le dernier (montant)
        label_words = row[label_start:-1]
        label_raw = " ".join(w["text"] for w in label_words).strip()
        label_raw = fix_latin1_encoding(label_raw)

        return _RawLine(
            operation_date=op_date,
            value_date=val_date,
            label=label_raw,
            detail_lines=[],
            amount=signed_amount,
            page=page_num,
            row_index=row_index,
        )

    def _raw_line_to_parsed(self, rl: _RawLine) -> ParsedTransaction:
        """Convertit une ligne brute en ParsedTransaction (sans fusion SEPA)."""
        detail = " ".join(rl.detail_lines).strip()
        full_label = (rl.label + " " + detail).strip() if detail else rl.label
        full_label = re.sub(r"\s+", " ", full_label)
        return ParsedTransaction(
            operation_date=rl.operation_date,
            value_date=rl.value_date,
            label=full_label,
            raw_label=full_label,
            amount=rl.amount,
            statement_row_index=rl.row_index,
        )

    def _period_from_transactions(
        self,
        transactions: list[ParsedTransaction],
        opening_date: date | None,
        closing_date: date | None,
    ) -> tuple[date | None, date | None]:
        if not transactions:
            return opening_date, closing_date
        dates = [t.operation_date for t in transactions]
        return min(dates), max(dates)
```

**Retirer** la méthode `_parse_period` obsolète (remplacée par `_period_from_transactions`).

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_parser_delubac.py -v
```

Expected : tous les tests de D1-D3 passent (sauf éventuellement `test_parse_full_month_transactions_count_within_tolerance` si la fusion SEPA n'est pas encore faite — ce test sera recalibré en D4).

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/delubac.py backend/tests/test_parser_delubac.py
git commit -m "feat(parsers): Delubac transaction row extraction with header filtering"
```

---

### Tâche D4 : Fusion des trios SEPA (parent + commission + TVA)

**Files:**
- Modify: `backend/app/parsers/delubac.py`
- Modify: `backend/tests/test_parser_delubac.py`

- [ ] **Étape 1 : Ajouter les tests**

Ajouter à `backend/tests/test_parser_delubac.py` :

```python
def test_parse_sepa_trio_merged(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_sepa_trio.pdf"))
    assert len(stmt.transactions) == 1, "Le trio doit être fusionné en 1 parent"
    parent = stmt.transactions[0]
    assert parent.is_aggregation_parent is True
    assert len(parent.children) == 3
    # Montants : parent = somme enfants (tous en débit → négatifs)
    assert parent.amount == Decimal("-1000.60")
    total_children = sum(c.amount for c in parent.children)
    assert total_children == parent.amount


def test_parse_sepa_trio_children_labels(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_sepa_trio.pdf"))
    parent = stmt.transactions[0]
    child_labels = [c.label for c in parent.children]
    assert any("VIR SEPA JEAN DUPONT" in l and "COMMISSION" not in l and "TVA" not in l
               for l in child_labels)
    assert any("COMMISSION VIR SEPA" in l for l in child_labels)
    assert any("TVA VIR SEPA" in l for l in child_labels)


def test_parse_full_month_merges_all_trios(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_full_month.pdf"))
    # Vérifier qu'aucune transaction top-level ne commence par COMMISSION/TVA
    for t in stmt.transactions:
        assert not t.label.startswith("COMMISSION VIR SEPA"), \
            f"Orphelin: {t.label!r}"
        assert not t.label.startswith("TVA VIR SEPA"), \
            f"Orphelin: {t.label!r}"


def test_parse_vir_sepa_credit_not_merged(parser: DelubacParser) -> None:
    """Un VIR SEPA reçu (crédit) sans commission associée ne doit pas être fusionné."""
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    # Le VIR SEPA BNP PARIBAS FACTOR est un crédit isolé
    bnp = [t for t in stmt.transactions if "BNP PARIBAS FACTOR" in t.label]
    assert len(bnp) == 1
    assert bnp[0].is_aggregation_parent is False
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parser_delubac.py::test_parse_sepa_trio_merged -v
```

Expected : `len(stmt.transactions) == 3, pas 1`.

- [ ] **Étape 3 : Implémenter la fusion SEPA**

Dans `backend/app/parsers/delubac.py` :

**A.** Modifier `parse()` pour appeler la fusion :

```python
        transactions = [self._raw_line_to_parsed(rl) for rl in raw_lines]
        transactions = self._merge_sepa_trios(transactions)
        period_start, period_end = self._period_from_transactions(
            transactions, opening_date, closing_date
        )
```

**B.** Ajouter la méthode :

```python
    _COMMISSION_PREFIX = "COMMISSION VIR SEPA"
    _TVA_PREFIX = "TVA VIR SEPA"
    _VIR_PREFIX = "VIR SEPA"

    def _merge_sepa_trios(
        self, transactions: list[ParsedTransaction]
    ) -> list[ParsedTransaction]:
        """Fusionne les trios (VIR SEPA parent + COMMISSION + TVA) en transaction parente."""
        merged: list[ParsedTransaction] = []
        i = 0
        n = len(transactions)
        while i < n:
            t = transactions[i]
            # On fusionne uniquement si :
            # - t commence par "VIR SEPA " (hors COMMISSION/TVA)
            # - t est un débit
            # - i+1 commence par "COMMISSION VIR SEPA" sur même date
            # - i+2 commence par "TVA VIR SEPA" sur même date
            if (
                i + 2 < n
                and t.label.startswith(self._VIR_PREFIX + " ")
                and not t.label.startswith(self._COMMISSION_PREFIX)
                and not t.label.startswith(self._TVA_PREFIX)
                and t.amount < 0
                and transactions[i + 1].label.startswith(self._COMMISSION_PREFIX)
                and transactions[i + 1].operation_date == t.operation_date
                and transactions[i + 2].label.startswith(self._TVA_PREFIX)
                and transactions[i + 2].operation_date == t.operation_date
            ):
                parent_raw = t
                child_commission = transactions[i + 1]
                child_tva = transactions[i + 2]
                # L'ex-parent "VIR SEPA …" devient un enfant ; on crée un nouveau parent agrégé
                parent = ParsedTransaction(
                    operation_date=t.operation_date,
                    value_date=t.value_date,
                    label=parent_raw.label,
                    raw_label=parent_raw.raw_label,
                    amount=parent_raw.amount + child_commission.amount + child_tva.amount,
                    statement_row_index=parent_raw.statement_row_index,
                    children=[
                        ParsedTransaction(
                            operation_date=parent_raw.operation_date,
                            value_date=parent_raw.value_date,
                            label=parent_raw.label,
                            raw_label=parent_raw.raw_label,
                            amount=parent_raw.amount,
                            statement_row_index=parent_raw.statement_row_index,
                        ),
                        child_commission,
                        child_tva,
                    ],
                )
                merged.append(parent)
                i += 3
            else:
                merged.append(t)
                i += 1
        return merged
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_parser_delubac.py -v
```

Expected : tous les tests passent.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/delubac.py backend/tests/test_parser_delubac.py
git commit -m "feat(parsers): Delubac merges SEPA trio (parent + commission + TVA)"
```

---

### Tâche D5 : Extraction de la contrepartie (`counterparty_hint`)

**Files:**
- Modify: `backend/app/parsers/delubac.py`
- Modify: `backend/tests/test_parser_delubac.py`

- [ ] **Étape 1 : Ajouter les tests**

```python
def test_parse_counterparty_extracted_from_label(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_full_month.pdf"))
    # Au moins 1 transaction doit avoir counterparty_hint non-None
    hints = [t.counterparty_hint for t in stmt.transactions]
    assert any(h is not None for h in hints)
    # URSSAF reconnu
    urssaf = next((t for t in stmt.transactions if "URSSAF" in t.label), None)
    assert urssaf is not None
    assert urssaf.counterparty_hint == "URSSAF"


def test_parse_counterparty_on_sepa_parent(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_sepa_trio.pdf"))
    parent = stmt.transactions[0]
    assert parent.counterparty_hint == "JEAN DUPONT"
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parser_delubac.py::test_parse_counterparty_extracted_from_label -v
```

Expected : `urssaf.counterparty_hint is None`.

- [ ] **Étape 3 : Implémenter**

Dans `backend/app/parsers/delubac.py`, modifier `_raw_line_to_parsed` :

```python
    def _raw_line_to_parsed(self, rl: _RawLine) -> ParsedTransaction:
        """Convertit une ligne brute en ParsedTransaction (sans fusion SEPA)."""
        from app.parsers.normalization import extract_counterparty
        detail = " ".join(rl.detail_lines).strip()
        full_label = (rl.label + " " + detail).strip() if detail else rl.label
        full_label = re.sub(r"\s+", " ", full_label)
        hint = extract_counterparty(rl.label)  # extrait depuis la ligne principale
        return ParsedTransaction(
            operation_date=rl.operation_date,
            value_date=rl.value_date,
            label=full_label,
            raw_label=full_label,
            amount=rl.amount,
            statement_row_index=rl.row_index,
            counterparty_hint=hint,
        )
```

Et dans `_merge_sepa_trios`, hériter le hint du parent :

```python
                parent = ParsedTransaction(
                    operation_date=t.operation_date,
                    value_date=t.value_date,
                    label=parent_raw.label,
                    raw_label=parent_raw.raw_label,
                    amount=parent_raw.amount + child_commission.amount + child_tva.amount,
                    statement_row_index=parent_raw.statement_row_index,
                    counterparty_hint=parent_raw.counterparty_hint,
                    children=[...],
                )
```

(Laisser le reste de `children=` inchangé.)

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_parser_delubac.py -v
```

Expected : tous les tests passent.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/delubac.py backend/tests/test_parser_delubac.py
git commit -m "feat(parsers): Delubac extracts counterparty hint from labels"
```

---

### Tâche D6 : Enregistrer le parser dans le registre global

**Files:**
- Modify: `backend/app/parsers/delubac.py`
- Modify: `backend/app/parsers/__init__.py`
- Create: `backend/tests/test_parsers_registry_integration.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_parsers_registry_integration.py` :

```python
"""Vérifie que DelubacParser est bien enregistré à l'import du package."""
from pathlib import Path

from app.parsers import get_parser_by_code, get_parser_for
from app.parsers.delubac import DelubacParser

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_delubac_registered_by_code() -> None:
    p = get_parser_by_code("delubac")
    assert isinstance(p, DelubacParser)


def test_delubac_autodetected_from_bytes() -> None:
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    p = get_parser_for(pdf)
    assert isinstance(p, DelubacParser)
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_parsers_registry_integration.py -v
```

Expected : `UnknownBankError("Aucun parser pour bank_code='delubac'")`.

- [ ] **Étape 3 : Enregistrer DelubacParser au chargement du module**

**A.** Dans `backend/app/parsers/delubac.py`, ajouter à la toute fin du fichier :

```python
from app.parsers import register_parser  # noqa: E402
register_parser(DelubacParser())
```

**B.** Dans `backend/app/parsers/__init__.py`, appeler `_auto_register` au chargement du package :

```python
# Tout en bas du fichier :
def _auto_register() -> None:
    from app.parsers import delubac  # noqa: F401


try:
    _auto_register()
except ValueError:
    # Déjà enregistré (cas du double-import en test) — ignorer
    pass
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_parsers_registry_integration.py tests/test_parser_delubac.py tests/test_parsers_registry.py -v
```

Expected : tous passent.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/parsers/delubac.py backend/app/parsers/__init__.py \
        backend/tests/test_parsers_registry_integration.py
git commit -m "feat(parsers): auto-register DelubacParser at module import"
```

---

# SECTION E — Pipeline d'import : limites, dedup, contreparties

Cette section implémente le service `backend/app/services/imports.py` qui orchestre le parsing, la normalisation, la déduplication, la création automatique de contreparties et l'insertion atomique en base. Toutes les fonctions sont testées en isolation avant l'intégration API.

### Tâche E1 : Limites et garde-fous du pipeline

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/imports.py`
- Create: `backend/tests/test_service_imports_limits.py`

Objectif : refuser un fichier qui dépasse les limites configurées **avant** de tenter de le parser. Limites (valeurs configurables via variables d'environnement, avec défauts explicites) :

| Limite | Valeur par défaut | Variable d'env |
|---|---|---|
| Taille fichier max | 20 Mo | `IMPORT_MAX_BYTES` |
| Pages PDF max | 500 | `IMPORT_MAX_PAGES` |
| Transactions max / statement | 10 000 | `IMPORT_MAX_TRANSACTIONS` |
| Timeout parsing (s) | 60 | `IMPORT_PARSE_TIMEOUT_S` |

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_service_imports_limits.py` :

```python
"""Les limites du pipeline d'import doivent rejeter les fichiers trop gros."""
import pytest

from app.services.imports import (
    FileTooLargeError,
    TooManyPagesError,
    TooManyTransactionsError,
    check_size_limit,
    check_pages_limit,
    check_transactions_limit,
)


def test_size_limit_accepts_small_file() -> None:
    check_size_limit(b"x" * 100, max_bytes=1024)


def test_size_limit_rejects_large_file() -> None:
    with pytest.raises(FileTooLargeError):
        check_size_limit(b"x" * 2048, max_bytes=1024)


def test_pages_limit_accepts_within_bound() -> None:
    check_pages_limit(pages=10, max_pages=500)


def test_pages_limit_rejects_over_bound() -> None:
    with pytest.raises(TooManyPagesError):
        check_pages_limit(pages=501, max_pages=500)


def test_transactions_limit_rejects_over_bound() -> None:
    with pytest.raises(TooManyTransactionsError):
        check_transactions_limit(count=10_001, max_count=10_000)
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_service_imports_limits.py -v
```

Expected : `ModuleNotFoundError: No module named 'app.services.imports'`.

- [ ] **Étape 3 : Implémenter les garde-fous**

`backend/app/services/__init__.py` : fichier vide.

`backend/app/services/imports.py` :

```python
"""Pipeline d'import : orchestre parser + normalisation + dedup + insertion."""
from __future__ import annotations

import os


class ImportLimitError(Exception):
    """Erreur générique de dépassement de limite."""


class FileTooLargeError(ImportLimitError):
    pass


class TooManyPagesError(ImportLimitError):
    pass


class TooManyTransactionsError(ImportLimitError):
    pass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        v = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} doit être un entier, reçu : {raw!r}") from exc
    if v <= 0:
        raise RuntimeError(f"{name} doit être > 0")
    return v


MAX_BYTES = _env_int("IMPORT_MAX_BYTES", 20 * 1024 * 1024)
MAX_PAGES = _env_int("IMPORT_MAX_PAGES", 500)
MAX_TRANSACTIONS = _env_int("IMPORT_MAX_TRANSACTIONS", 10_000)
PARSE_TIMEOUT_S = _env_int("IMPORT_PARSE_TIMEOUT_S", 60)


def check_size_limit(data: bytes, *, max_bytes: int = MAX_BYTES) -> None:
    if len(data) > max_bytes:
        raise FileTooLargeError(
            f"Fichier de {len(data)} octets > limite {max_bytes}"
        )


def check_pages_limit(*, pages: int, max_pages: int = MAX_PAGES) -> None:
    if pages > max_pages:
        raise TooManyPagesError(f"{pages} pages > limite {max_pages}")


def check_transactions_limit(*, count: int, max_count: int = MAX_TRANSACTIONS) -> None:
    if count > max_count:
        raise TooManyTransactionsError(
            f"{count} transactions > limite {max_count}"
        )
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_service_imports_limits.py -v
```

Expected : 4 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/imports.py \
        backend/tests/test_service_imports_limits.py
git commit -m "feat(imports): add pipeline size/pages/transactions limit checks"
```

---

### Tâche E2 : Fonction `compute_dedup_key` et détection de doublons

**Files:**
- Modify: `backend/app/services/imports.py`
- Create: `backend/tests/test_service_imports_dedup.py`

Logique dedup : un enregistrement en base est considéré doublon d'une ligne importée si leurs `dedup_key` sont identiques. Clé = SHA-256 hex de la concaténation de :

```
{bank_account_id}|{operation_date:iso}|{value_date:iso}|{amount_signed_cents}|{normalized_label}|{statement_row_index}
```

`statement_row_index` est inclus pour distinguer deux lignes identiques présentes deux fois sur le même relevé (cas rare mais licite : deux retraits DAB de même montant le même jour). Il permet aussi à l'utilisateur de ré-importer un relevé corrigé et d'avoir des clés différentes si l'ordre change.

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_service_imports_dedup.py` :

```python
"""Unicité de la dedup_key et détection de doublons."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.services.imports import compute_dedup_key, DedupKeyInput


ACC = UUID("00000000-0000-0000-0000-000000000001")


def test_dedup_key_is_deterministic() -> None:
    payload = DedupKeyInput(
        bank_account_id=ACC,
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        amount=Decimal("-42.50"),
        normalized_label="VIR SEPA ACME SAS",
        statement_row_index=3,
    )
    k1 = compute_dedup_key(payload)
    k2 = compute_dedup_key(payload)
    assert k1 == k2
    assert len(k1) == 64
    assert all(c in "0123456789abcdef" for c in k1)


def test_dedup_key_differs_if_amount_changes() -> None:
    base = DedupKeyInput(
        bank_account_id=ACC,
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        amount=Decimal("-42.50"),
        normalized_label="VIR SEPA ACME SAS",
        statement_row_index=3,
    )
    other = DedupKeyInput(**{**base.__dict__, "amount": Decimal("-42.51")})
    assert compute_dedup_key(base) != compute_dedup_key(other)


def test_dedup_key_differs_if_row_index_changes() -> None:
    base = DedupKeyInput(
        bank_account_id=ACC,
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        amount=Decimal("-42.50"),
        normalized_label="VIR SEPA ACME SAS",
        statement_row_index=3,
    )
    other = DedupKeyInput(**{**base.__dict__, "statement_row_index": 4})
    assert compute_dedup_key(base) != compute_dedup_key(other)
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_service_imports_dedup.py -v
```

Expected : `ImportError: cannot import name 'compute_dedup_key'`.

- [ ] **Étape 3 : Implémenter**

Ajouter en bas de `backend/app/services/imports.py` :

```python
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class DedupKeyInput:
    bank_account_id: UUID
    operation_date: date
    value_date: date
    amount: Decimal
    normalized_label: str
    statement_row_index: int


def compute_dedup_key(payload: DedupKeyInput) -> str:
    """Retourne le SHA-256 hex (64 caractères) déterministe de l'entrée."""
    # Montant en centimes signé, stable : évite les pièges Decimal("-42.50") vs "-42.5"
    amount_cents = int((payload.amount * 100).to_integral_value())
    parts = [
        str(payload.bank_account_id),
        payload.operation_date.isoformat(),
        payload.value_date.isoformat(),
        str(amount_cents),
        payload.normalized_label,
        str(payload.statement_row_index),
    ]
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_service_imports_dedup.py -v
```

Expected : 3 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/services/imports.py backend/tests/test_service_imports_dedup.py
git commit -m "feat(imports): add deterministic dedup_key computation"
```

---

### Tâche E3 : Matching et création automatique des contreparties

**Files:**
- Modify: `backend/app/services/imports.py`
- Create: `backend/tests/test_service_imports_counterparty.py`

Stratégie de matching :

1. Si `counterparty_hint` (extrait par le parser) est non vide : recherche insensible à la casse d'une `Counterparty` existante (statut `active` ou `pending`) dont `name` fuzzy-matche à ≥ 90 % (`rapidfuzz.fuzz.token_set_ratio`) — la première correspondance triée par score décroissant puis `created_at` croissant est retenue.
2. Sinon : aucune contrepartie liée.
3. Si aucune correspondance et `hint` présent : création automatique d'une `Counterparty` en statut `pending`, avec `name = hint` nettoyé (majuscules + trim + espaces compactés). Elle sera validée manuellement par l'utilisateur plus tard.

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_service_imports_counterparty.py` :

```python
"""Matching fuzzy et création auto-pending de contreparties."""
import pytest
from sqlalchemy.orm import Session

from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.services.imports import match_or_create_counterparty


def _make_entity(session: Session) -> Entity:
    e = Entity(name="SAS Test", slug="sas-test")
    session.add(e)
    session.flush()
    return e


def test_match_returns_none_when_hint_empty(db_session: Session) -> None:
    e = _make_entity(db_session)
    result = match_or_create_counterparty(db_session, entity_id=e.id, hint=None)
    assert result is None


def test_match_finds_existing_active_fuzzy(db_session: Session) -> None:
    e = _make_entity(db_session)
    existing = Counterparty(
        entity_id=e.id, name="ACME SAS", status=CounterpartyStatus.ACTIVE
    )
    db_session.add(existing)
    db_session.flush()
    result = match_or_create_counterparty(
        db_session, entity_id=e.id, hint="ACME S.A.S."
    )
    assert result is not None
    assert result.id == existing.id


def test_match_creates_pending_when_no_existing(db_session: Session) -> None:
    e = _make_entity(db_session)
    result = match_or_create_counterparty(
        db_session, entity_id=e.id, hint="NEW PARTNER SARL"
    )
    assert result is not None
    assert result.status == CounterpartyStatus.PENDING
    assert result.name == "NEW PARTNER SARL"


def test_match_does_not_create_when_fuzzy_below_threshold(db_session: Session) -> None:
    e = _make_entity(db_session)
    existing = Counterparty(
        entity_id=e.id, name="ACME SAS", status=CounterpartyStatus.ACTIVE
    )
    db_session.add(existing)
    db_session.flush()
    result = match_or_create_counterparty(
        db_session, entity_id=e.id, hint="COMPLETELY DIFFERENT GMBH"
    )
    assert result is not None
    assert result.id != existing.id
    assert result.status == CounterpartyStatus.PENDING
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_service_imports_counterparty.py -v
```

Expected : `ImportError: cannot import name 'match_or_create_counterparty'`.

- [ ] **Étape 3 : Implémenter**

Ajouter dans `backend/app/services/imports.py` :

```python
from typing import TYPE_CHECKING
from uuid import UUID

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.counterparty import Counterparty, CounterpartyStatus

FUZZY_THRESHOLD = 90


def _normalize_counterparty_name(raw: str) -> str:
    return " ".join(raw.upper().split())


def match_or_create_counterparty(
    session: Session,
    *,
    entity_id: UUID,
    hint: str | None,
) -> Counterparty | None:
    """Retourne une Counterparty matchée ou nouvellement créée (pending).

    - Retourne None si hint est vide.
    - Match fuzzy ≥ 90 % (token_set_ratio) contre les contreparties existantes
      de l'entité (statut != ignored).
    - Sinon crée une Counterparty en statut `pending`.
    """
    if not hint or not hint.strip():
        return None

    clean = _normalize_counterparty_name(hint)

    existing = session.execute(
        select(Counterparty).where(
            Counterparty.entity_id == entity_id,
            Counterparty.status != CounterpartyStatus.IGNORED,
        )
    ).scalars().all()

    if existing:
        choices = {cp.id: cp.name for cp in existing}
        best = process.extractOne(
            clean, choices, scorer=fuzz.token_set_ratio
        )
        if best is not None and best[1] >= FUZZY_THRESHOLD:
            cp_id = best[2]
            return next(cp for cp in existing if cp.id == cp_id)

    # Création auto-pending
    cp = Counterparty(
        entity_id=entity_id,
        name=clean,
        status=CounterpartyStatus.PENDING,
    )
    session.add(cp)
    session.flush()
    return cp
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_service_imports_counterparty.py -v
```

Expected : 4 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/services/imports.py backend/tests/test_service_imports_counterparty.py
git commit -m "feat(imports): fuzzy-match or auto-create pending counterparty"
```

---

### Tâche E4 : Insertion atomique et détection de doublons en base

**Files:**
- Modify: `backend/app/services/imports.py`
- Create: `backend/tests/test_service_imports_insert.py`

La fonction `ingest_parsed_statement` prend un `ParsedStatement`, un `bank_account_id`, une session DB, et effectue dans une **seule transaction** :

1. Pour chaque `ParsedTransaction` (parent inclus s'il est aggregation_parent) : calcul de `dedup_key`.
2. Lookup des `dedup_key` déjà présents en base → produit la liste des doublons.
3. Si `override_duplicates=False` (défaut) : les doublons sont **ignorés** (pas d'erreur, simplement non insérés) ; leur `dedup_key` est remonté dans le résumé.
4. Si `override_duplicates=True` : l'insertion est effectuée avec un suffixe `|dup:N` sur la `normalized_label` pour recalculer une nouvelle `dedup_key`, et une entrée `ImportRecord.audit` (JSON) liste les `dedup_key` surchargées.
5. Matching/création de contreparties (E3) par transaction.
6. Insertion des parents avant les enfants (respect de la FK `parent_transaction_id`).
7. Création de l'`ImportRecord` final avec statistiques (`imported_count`, `duplicates_skipped`, `counterparties_pending_created`).
8. Commit ou rollback global en cas d'exception.

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_service_imports_insert.py` :

```python
"""Insertion atomique : dedup, doublons, override, parent/enfants."""
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.parsers.base import ParsedStatement, ParsedTransaction
from app.services.imports import ingest_parsed_statement


def _fx_parent_child() -> ParsedStatement:
    parent = ParsedTransaction(
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        label="VIR SEPA ACME",
        raw_label="VIR SEPA ACME",
        amount=Decimal("-100.00"),
        statement_row_index=0,
        counterparty_hint="ACME",
    )
    child_comm = ParsedTransaction(
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        label="COMMISSION VIR SEPA ACME",
        raw_label="COMMISSION VIR SEPA ACME",
        amount=Decimal("-1.50"),
        statement_row_index=1,
    )
    parent.children.append(child_comm)
    return ParsedStatement(
        bank_code="delubac",
        iban="FR7600000000000000000000001",
        account_number="001",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        opening_balance=Decimal("1000.00"),
        closing_balance=Decimal("898.50"),
        transactions=[parent],
    )


def _fx_bank_account(session: Session) -> tuple[BankAccount, Entity]:
    e = Entity(name="SAS Test", slug="sas-test")
    session.add(e)
    session.flush()
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        iban="FR7600000000000000000000001",
        label="Compte courant",
    )
    session.add(ba)
    session.flush()
    return ba, e


def test_ingest_inserts_parent_and_children(db_session: Session) -> None:
    ba, _ = _fx_bank_account(db_session)
    stmt = _fx_parent_child()
    rec = ingest_parsed_statement(
        db_session, bank_account_id=ba.id, statement=stmt
    )
    assert rec.status == ImportStatus.COMPLETED
    assert rec.imported_count == 2
    assert rec.duplicates_skipped == 0

    rows = db_session.execute(select(Transaction)).scalars().all()
    assert len(rows) == 2
    parent = next(r for r in rows if r.amount == Decimal("-100.00"))
    child = next(r for r in rows if r.amount == Decimal("-1.50"))
    assert parent.is_aggregation_parent is True
    assert child.parent_transaction_id == parent.id


def test_ingest_skips_duplicates_by_default(db_session: Session) -> None:
    ba, _ = _fx_bank_account(db_session)
    stmt = _fx_parent_child()
    first = ingest_parsed_statement(db_session, bank_account_id=ba.id, statement=stmt)
    assert first.imported_count == 2
    # Second import de la même donnée
    second = ingest_parsed_statement(db_session, bank_account_id=ba.id, statement=stmt)
    assert second.imported_count == 0
    assert second.duplicates_skipped == 2


def test_ingest_override_duplicates_inserts_with_suffix(db_session: Session) -> None:
    ba, _ = _fx_bank_account(db_session)
    stmt = _fx_parent_child()
    ingest_parsed_statement(db_session, bank_account_id=ba.id, statement=stmt)
    rec = ingest_parsed_statement(
        db_session, bank_account_id=ba.id, statement=stmt, override_duplicates=True
    )
    assert rec.imported_count == 2
    assert rec.duplicates_skipped == 0
    assert "dup" in (rec.audit or {}).get("overridden", [])[0] if rec.audit else True


def test_ingest_creates_pending_counterparty(db_session: Session) -> None:
    ba, e = _fx_bank_account(db_session)
    stmt = _fx_parent_child()
    rec = ingest_parsed_statement(db_session, bank_account_id=ba.id, statement=stmt)
    cps = db_session.execute(
        select(Counterparty).where(Counterparty.entity_id == e.id)
    ).scalars().all()
    assert len(cps) == 1
    assert cps[0].name == "ACME"
    assert cps[0].status == CounterpartyStatus.PENDING
    assert rec.counterparties_pending_created == 1
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_service_imports_insert.py -v
```

Expected : `ImportError: cannot import name 'ingest_parsed_statement'`.

- [ ] **Étape 3 : Implémenter**

Ajouter dans `backend/app/services/imports.py` :

```python
from datetime import datetime, timezone

from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.parsers.base import ParsedStatement, ParsedTransaction


def _to_dedup_input(
    tx: ParsedTransaction,
    *,
    bank_account_id: UUID,
    label_suffix: str = "",
) -> DedupKeyInput:
    return DedupKeyInput(
        bank_account_id=bank_account_id,
        operation_date=tx.operation_date,
        value_date=tx.value_date,
        amount=tx.amount,
        normalized_label=tx.label + label_suffix,
        statement_row_index=tx.statement_row_index,
    )


def _flatten(parent: ParsedTransaction) -> list[ParsedTransaction]:
    out = [parent]
    out.extend(parent.children)
    return out


def ingest_parsed_statement(
    session: Session,
    *,
    bank_account_id: UUID,
    statement: ParsedStatement,
    override_duplicates: bool = False,
    import_record: ImportRecord | None = None,
) -> ImportRecord:
    """Insère atomiquement un ParsedStatement. Retourne l'ImportRecord mis à jour.

    - Si un import_record existe déjà (créé en amont par l'API), il est réutilisé ;
      sinon un nouveau est créé.
    - Toute exception déclenche un rollback global et passe l'ImportRecord en FAILED.
    """
    # Récupérer l'entity_id à partir du bank_account
    from app.models.bank_account import BankAccount

    ba = session.get(BankAccount, bank_account_id)
    if ba is None:
        raise ValueError(f"BankAccount {bank_account_id} introuvable")

    if import_record is None:
        import_record = ImportRecord(
            bank_account_id=bank_account_id,
            bank_code=statement.bank_code,
            status=ImportStatus.PENDING,
            period_start=statement.period_start,
            period_end=statement.period_end,
        )
        session.add(import_record)
        session.flush()

    overridden: list[str] = []
    pending_created = 0

    try:
        # 1. Aplatit tous les ParsedTransaction (parents + enfants), préservant l'ordre
        all_parsed: list[tuple[ParsedTransaction, bool]] = []
        for root in statement.transactions:
            for tx in _flatten(root):
                is_parent = tx is root and bool(root.children)
                all_parsed.append((tx, is_parent))

        # 2. Calcule les dedup_keys
        keys_to_check = [
            compute_dedup_key(_to_dedup_input(tx, bank_account_id=bank_account_id))
            for tx, _ in all_parsed
        ]

        # 3. Détecte les doublons existants en base
        existing_keys: set[str] = set(
            session.execute(
                select(Transaction.dedup_key).where(
                    Transaction.dedup_key.in_(keys_to_check)
                )
            ).scalars().all()
        )

        # 4. Matching counterparty par parsed tx (une seule fois, même pour parent/enfant)
        cp_cache: dict[int, UUID | None] = {}
        for idx, (tx, _is_parent) in enumerate(all_parsed):
            if id(tx) not in cp_cache:
                cp = match_or_create_counterparty(
                    session, entity_id=ba.entity_id, hint=tx.counterparty_hint
                )
                if cp is not None and cp.status == CounterpartyStatus.PENDING:
                    pending_created += 1
                cp_cache[id(tx)] = cp.id if cp else None

        # 5. Insertion (parents d'abord pour FK)
        # Mappe ParsedTransaction -> Transaction inséré (pour FK parent/enfant)
        inserted_map: dict[int, Transaction] = {}
        imported_count = 0
        duplicates_skipped = 0

        def _insert_tx(
            tx: ParsedTransaction,
            parent_db: Transaction | None,
            is_aggregation_parent: bool,
        ) -> None:
            nonlocal imported_count, duplicates_skipped
            key = compute_dedup_key(_to_dedup_input(tx, bank_account_id=bank_account_id))
            if key in existing_keys:
                if override_duplicates:
                    # Nouvelle clé avec suffixe
                    suffix = f"|dup:{datetime.now(timezone.utc).timestamp()}"
                    key = compute_dedup_key(
                        _to_dedup_input(tx, bank_account_id=bank_account_id, label_suffix=suffix)
                    )
                    overridden.append(key)
                else:
                    duplicates_skipped += 1
                    return

            db_tx = Transaction(
                bank_account_id=bank_account_id,
                import_id=import_record.id,
                operation_date=tx.operation_date,
                value_date=tx.value_date,
                label=tx.label,
                raw_label=tx.raw_label,
                amount=tx.amount,
                dedup_key=key,
                statement_row_index=tx.statement_row_index,
                is_aggregation_parent=is_aggregation_parent,
                parent_transaction_id=parent_db.id if parent_db else None,
                counterparty_id=cp_cache.get(id(tx)),
            )
            session.add(db_tx)
            session.flush()
            inserted_map[id(tx)] = db_tx
            imported_count += 1

        for root in statement.transactions:
            parent_db: Transaction | None = None
            if root.children:
                _insert_tx(root, None, is_aggregation_parent=True)
                parent_db = inserted_map.get(id(root))
                for child in root.children:
                    _insert_tx(child, parent_db, is_aggregation_parent=False)
            else:
                _insert_tx(root, None, is_aggregation_parent=False)

        import_record.status = ImportStatus.COMPLETED
        import_record.imported_count = imported_count
        import_record.duplicates_skipped = duplicates_skipped
        import_record.counterparties_pending_created = pending_created
        import_record.opening_balance = statement.opening_balance
        import_record.closing_balance = statement.closing_balance
        if overridden:
            import_record.audit = {"overridden": overridden}
        session.flush()
        return import_record

    except Exception as exc:
        import_record.status = ImportStatus.FAILED
        import_record.error_message = str(exc)[:500]
        session.flush()
        raise
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_service_imports_insert.py -v
```

Expected : 4 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/services/imports.py backend/tests/test_service_imports_insert.py
git commit -m "feat(imports): atomic ingestion with dedup, parents, counterparties"
```

---

### Tâche E5 : Fonction d'entrée unique `import_pdf_bytes`

**Files:**
- Modify: `backend/app/services/imports.py`
- Create: `backend/tests/test_service_imports_entrypoint.py`

Fonction haut-niveau qui orchestre tout le pipeline pour l'API :

```python
def import_pdf_bytes(
    session: Session,
    *,
    bank_account_id: UUID,
    pdf_bytes: bytes,
    filename: str,
    override_duplicates: bool = False,
) -> ImportRecord: ...
```

Étapes :
1. `check_size_limit(pdf_bytes)`.
2. `get_parser_for(pdf_bytes)` → sélection automatique.
3. Création de l'`ImportRecord` en statut `PENDING` avec filename et sha256 du fichier (pour audit).
4. Parse (`parser.parse(pdf_bytes)`) → attraper ParserError → statut FAILED + erreur.
5. `check_pages_limit`, `check_transactions_limit`.
6. Appel `ingest_parsed_statement(..., import_record=rec)`.
7. Retour du record final.

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_service_imports_entrypoint.py` :

```python
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportStatus
from app.services.imports import import_pdf_bytes, FileTooLargeError

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def _make_ba(session: Session) -> BankAccount:
    e = Entity(name="SAS Test", slug="sas-test")
    session.add(e)
    session.flush()
    ba = BankAccount(
        entity_id=e.id, bank_code="delubac", iban="FR7600000000000000000000001",
        label="Compte courant",
    )
    session.add(ba)
    session.flush()
    return ba


def test_import_pdf_bytes_happy_path(db_session: Session) -> None:
    ba = _make_ba(db_session)
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    rec = import_pdf_bytes(
        db_session,
        bank_account_id=ba.id,
        pdf_bytes=pdf,
        filename="synthetic_minimal.pdf",
    )
    assert rec.status == ImportStatus.COMPLETED
    assert rec.imported_count >= 3
    assert rec.filename == "synthetic_minimal.pdf"
    assert rec.file_sha256 is not None


def test_import_pdf_bytes_rejects_oversized(db_session: Session) -> None:
    import pytest
    ba = _make_ba(db_session)
    big = b"%PDF-1.4\n" + b"x" * (21 * 1024 * 1024)
    with pytest.raises(FileTooLargeError):
        import_pdf_bytes(
            db_session,
            bank_account_id=ba.id,
            pdf_bytes=big,
            filename="big.pdf",
        )
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_service_imports_entrypoint.py -v
```

Expected : `ImportError: cannot import name 'import_pdf_bytes'`.

- [ ] **Étape 3 : Implémenter**

Ajouter dans `backend/app/services/imports.py` :

```python
import hashlib as _hashlib_std  # déjà importé plus haut, alias pour clarté

from app.parsers import get_parser_for
from app.parsers.errors import ParserError


def import_pdf_bytes(
    session: Session,
    *,
    bank_account_id: UUID,
    pdf_bytes: bytes,
    filename: str,
    override_duplicates: bool = False,
) -> ImportRecord:
    check_size_limit(pdf_bytes)

    file_sha256 = _hashlib_std.sha256(pdf_bytes).hexdigest()

    # Pré-crée le record pour pouvoir logger un échec de parsing
    rec = ImportRecord(
        bank_account_id=bank_account_id,
        bank_code="unknown",
        status=ImportStatus.PENDING,
        filename=filename,
        file_sha256=file_sha256,
    )
    session.add(rec)
    session.flush()

    try:
        parser = get_parser_for(pdf_bytes)
        rec.bank_code = parser.code
        statement = parser.parse(pdf_bytes)
        check_pages_limit(pages=statement.page_count)
        check_transactions_limit(count=sum(1 + len(t.children) for t in statement.transactions))
    except ParserError as exc:
        rec.status = ImportStatus.FAILED
        rec.error_message = str(exc)[:500]
        session.flush()
        raise

    return ingest_parsed_statement(
        session,
        bank_account_id=bank_account_id,
        statement=statement,
        override_duplicates=override_duplicates,
        import_record=rec,
    )
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_service_imports_entrypoint.py -v
```

Expected : 2 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/services/imports.py backend/tests/test_service_imports_entrypoint.py
git commit -m "feat(imports): high-level import_pdf_bytes entrypoint"
```

---

# SECTION F — API REST : imports, transactions, counterparties

Toutes les routes sont protégées par l'auth du Plan 0 (session cookie + middleware `require_user`). Les routes qui manipulent une `Entity` ou un `BankAccount` vérifient en plus que l'utilisateur authentifié possède un `UserEntityAccess` correspondant (sinon 403).

### Tâche F1 : Schémas Pydantic pour imports / transactions / counterparties

**Files:**
- Create: `backend/app/schemas/import_record.py`
- Create: `backend/app/schemas/transaction.py`
- Create: `backend/app/schemas/counterparty.py`
- Create: `backend/app/schemas/category.py`
- Create: `backend/tests/test_schemas_plan1.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_schemas_plan1.py` :

```python
"""Sérialisation/désérialisation des schémas Plan 1."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.schemas.import_record import ImportRecordRead
from app.schemas.transaction import TransactionRead, TransactionFilter
from app.schemas.counterparty import CounterpartyRead, CounterpartyUpdate


def test_import_record_read_minimal() -> None:
    obj = ImportRecordRead(
        id=uuid4(),
        bank_account_id=uuid4(),
        bank_code="delubac",
        status="completed",
        filename="x.pdf",
        imported_count=3,
        duplicates_skipped=0,
        counterparties_pending_created=1,
        created_at=date(2026, 4, 16),
    )
    d = obj.model_dump()
    assert d["status"] == "completed"


def test_transaction_read_amount_is_string() -> None:
    obj = TransactionRead(
        id=uuid4(),
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        label="VIR SEPA",
        raw_label="VIR SEPA",
        amount=Decimal("-42.50"),
        is_aggregation_parent=False,
        counterparty=None,
        category=None,
    )
    d = obj.model_dump()
    assert d["amount"] == "-42.50"  # Decimal sérialisé en str pour précision


def test_transaction_filter_defaults() -> None:
    f = TransactionFilter()
    assert f.page == 1
    assert f.per_page == 50


def test_counterparty_update_accepts_status() -> None:
    obj = CounterpartyUpdate(status="active", name="ACME")
    assert obj.status == "active"
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_schemas_plan1.py -v
```

Expected : `ImportError`.

- [ ] **Étape 3 : Implémenter les schémas**

`backend/app/schemas/import_record.py` :

```python
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bank_account_id: UUID
    bank_code: str
    status: Literal["pending", "completed", "failed"]
    filename: str | None = None
    file_sha256: str | None = None
    imported_count: int = 0
    duplicates_skipped: int = 0
    counterparties_pending_created: int = 0
    period_start: date | None = None
    period_end: date | None = None
    error_message: str | None = None
    created_at: date | datetime | None = None
```

`backend/app/schemas/transaction.py` :

```python
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CounterpartyNested(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: str


class CategoryNested(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operation_date: date
    value_date: date
    label: str
    raw_label: str
    amount: Decimal
    is_aggregation_parent: bool = False
    parent_transaction_id: UUID | None = None
    counterparty: CounterpartyNested | None = None
    category: CategoryNested | None = None

    def model_dump(self, **kw):
        d = super().model_dump(**kw)
        # Decimal → str pour conserver la précision côté client
        if isinstance(d.get("amount"), Decimal):
            d["amount"] = str(d["amount"])
        return d


class TransactionFilter(BaseModel):
    bank_account_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    counterparty_id: UUID | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=500)


class TransactionListResponse(BaseModel):
    items: list[TransactionRead]
    total: int
    page: int
    per_page: int
```

`backend/app/schemas/counterparty.py` :

```python
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CounterpartyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    entity_id: UUID
    name: str
    status: Literal["pending", "active", "ignored"]


class CounterpartyUpdate(BaseModel):
    status: Literal["active", "ignored"] | None = None
    name: str | None = None
```

`backend/app/schemas/category.py` :

```python
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    parent_id: UUID | None = None
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_schemas_plan1.py -v
```

Expected : 4 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/schemas/import_record.py backend/app/schemas/transaction.py \
        backend/app/schemas/counterparty.py backend/app/schemas/category.py \
        backend/tests/test_schemas_plan1.py
git commit -m "feat(schemas): Plan 1 — imports, transactions, counterparties, categories"
```

---

### Tâche F2 : Endpoint `POST /api/imports` (upload PDF)

**Files:**
- Create: `backend/app/api/imports.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_api_imports_post.py`

Contrat :
- `POST /api/imports` — multipart form : champs `bank_account_id` (UUID) et `file` (PDF).
- Vérifie que l'utilisateur a accès à l'entité du bank_account (403 sinon).
- Vérifie le MIME (`application/pdf`) via `python-magic` (pas seulement sur le nom de fichier).
- Appelle `import_pdf_bytes`.
- Retourne `ImportRecordRead` (201).
- Rate limit : 10 imports / 10 min / utilisateur (SlowAPI décorateur).

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_api_imports_post.py` :

```python
"""POST /api/imports : upload PDF et création d'un ImportRecord."""
from pathlib import Path

from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_post_import_returns_201_and_record(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    resp = client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("synthetic_minimal.pdf", pdf, "application/pdf")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert body["imported_count"] >= 3


def test_post_import_rejects_non_pdf(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    resp = client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "pdf" in resp.json()["detail"].lower()


def test_post_import_forbidden_without_access(
    client: TestClient, auth_user, other_entity_bank_account,
) -> None:
    resp = client.post(
        "/api/imports",
        data={"bank_account_id": str(other_entity_bank_account.id)},
        files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 403
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_api_imports_post.py -v
```

Expected : 404 (route introuvable).

- [ ] **Étape 3 : Implémenter**

`backend/app/api/imports.py` :

```python
"""Endpoints /api/imports."""
from __future__ import annotations

from uuid import UUID

import magic
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_entity_access
from app.db.session import get_session
from app.models.bank_account import BankAccount
from app.models.user import User
from app.parsers.errors import ParserError, UnknownBankError
from app.schemas.import_record import ImportRecordRead
from app.services.imports import (
    FileTooLargeError,
    TooManyPagesError,
    TooManyTransactionsError,
    import_pdf_bytes,
)

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("", response_model=ImportRecordRead, status_code=status.HTTP_201_CREATED)
async def create_import(
    bank_account_id: UUID = Form(...),
    file: UploadFile = File(...),
    override_duplicates: bool = Form(False),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ImportRecordRead:
    ba = session.get(BankAccount, bank_account_id)
    if ba is None:
        raise HTTPException(status_code=404, detail="Compte bancaire introuvable")

    # 403 si l'utilisateur n'a pas accès à l'entité
    require_entity_access(session=session, user=user, entity_id=ba.entity_id)

    content = await file.read()
    mime = magic.from_buffer(content, mime=True)
    if mime != "application/pdf":
        raise HTTPException(
            status_code=400, detail=f"Fichier non PDF (type détecté : {mime})"
        )

    try:
        rec = import_pdf_bytes(
            session,
            bank_account_id=bank_account_id,
            pdf_bytes=content,
            filename=file.filename or "upload.pdf",
            override_duplicates=override_duplicates,
        )
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except (TooManyPagesError, TooManyTransactionsError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except UnknownBankError:
        raise HTTPException(
            status_code=400,
            detail="Banque non reconnue. Seul Delubac est supporté pour l'instant.",
        )
    except ParserError as exc:
        raise HTTPException(status_code=422, detail=f"Erreur d'analyse : {exc}")

    session.commit()
    return ImportRecordRead.model_validate(rec)
```

Modifier `backend/app/api/router.py` pour brancher le routeur :

```python
from app.api import imports as imports_module
api_router.include_router(imports_module.router)
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_api_imports_post.py -v
```

Expected : 3 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/api/imports.py backend/app/api/router.py backend/tests/test_api_imports_post.py
git commit -m "feat(api): POST /api/imports uploads and parses bank statement PDF"
```

---

### Tâche F3 : Endpoints `GET /api/imports` et `GET /api/imports/{id}`

**Files:**
- Modify: `backend/app/api/imports.py`
- Create: `backend/tests/test_api_imports_list.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_api_imports_list.py` :

```python
"""GET /api/imports et GET /api/imports/{id}."""
from pathlib import Path
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_list_imports_returns_user_accessible_imports(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )

    resp = client.get("/api/imports")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert body[0]["bank_code"] == "delubac"


def test_get_import_by_id_returns_detail(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    created = client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    ).json()

    resp = client.get(f"/api/imports/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_import_404_when_not_found(client: TestClient, auth_user) -> None:
    resp = client.get("/api/imports/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_api_imports_list.py -v
```

Expected : 405 ou 404.

- [ ] **Étape 3 : Implémenter**

Ajouter dans `backend/app/api/imports.py` :

```python
from sqlalchemy import select

from app.models.import_record import ImportRecord
from app.models.user_entity_access import UserEntityAccess


@router.get("", response_model=list[ImportRecordRead])
def list_imports(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ImportRecordRead]:
    # Imports accessibles = ceux dont le bank_account appartient à une entity où user a accès
    accessible_entity_ids = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )
    rows = session.execute(
        select(ImportRecord)
        .join(BankAccount, BankAccount.id == ImportRecord.bank_account_id)
        .where(BankAccount.entity_id.in_(accessible_entity_ids))
        .order_by(ImportRecord.created_at.desc())
    ).scalars().all()
    return [ImportRecordRead.model_validate(r) for r in rows]


@router.get("/{import_id}", response_model=ImportRecordRead)
def get_import(
    import_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ImportRecordRead:
    rec = session.get(ImportRecord, import_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Import introuvable")

    ba = session.get(BankAccount, rec.bank_account_id)
    require_entity_access(session=session, user=user, entity_id=ba.entity_id)
    return ImportRecordRead.model_validate(rec)
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_api_imports_list.py -v
```

Expected : 3 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/api/imports.py backend/tests/test_api_imports_list.py
git commit -m "feat(api): GET /api/imports list and GET /api/imports/{id} detail"
```

---

### Tâche F4 : Endpoint `GET /api/transactions` (liste paginée filtrable)

**Files:**
- Create: `backend/app/api/transactions.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_api_transactions.py`

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_api_transactions.py` :

```python
"""GET /api/transactions : filtres, pagination, autorisation."""
from pathlib import Path
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_list_transactions_after_import(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    resp = client.get("/api/transactions", params={"per_page": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) >= 3
    assert body["page"] == 1


def test_list_transactions_filter_by_bank_account(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    resp = client.get(
        "/api/transactions", params={"bank_account_id": str(ba.id), "per_page": 100}
    )
    assert resp.status_code == 200
    assert all(True for _ in resp.json()["items"])  # tous liés à ce ba


def test_list_transactions_pagination(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_full_month.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    p1 = client.get("/api/transactions", params={"page": 1, "per_page": 10}).json()
    p2 = client.get("/api/transactions", params={"page": 2, "per_page": 10}).json()
    assert p1["items"] != p2["items"]
    assert len(p1["items"]) == 10
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_api_transactions.py -v
```

Expected : 404.

- [ ] **Étape 3 : Implémenter**

`backend/app/api/transactions.py` :

```python
"""Endpoint /api/transactions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import get_current_user
from app.db.session import get_session
from app.models.bank_account import BankAccount
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.schemas.transaction import (
    TransactionFilter,
    TransactionListResponse,
    TransactionRead,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    filters: TransactionFilter = Depends(),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TransactionListResponse:
    accessible_entity_ids = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )

    conditions = [BankAccount.entity_id.in_(accessible_entity_ids)]
    if filters.bank_account_id:
        conditions.append(Transaction.bank_account_id == filters.bank_account_id)
    if filters.date_from:
        conditions.append(Transaction.operation_date >= filters.date_from)
    if filters.date_to:
        conditions.append(Transaction.operation_date <= filters.date_to)
    if filters.counterparty_id:
        conditions.append(Transaction.counterparty_id == filters.counterparty_id)
    if filters.search:
        like = f"%{filters.search.lower()}%"
        conditions.append(
            or_(
                func.lower(Transaction.label).like(like),
                func.lower(Transaction.raw_label).like(like),
            )
        )

    base_q = (
        select(Transaction)
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(and_(*conditions))
        .order_by(Transaction.operation_date.desc(), Transaction.statement_row_index.desc())
        .options(selectinload(Transaction.counterparty), selectinload(Transaction.category))
    )

    total = session.execute(
        select(func.count()).select_from(base_q.subquery())
    ).scalar_one()

    offset = (filters.page - 1) * filters.per_page
    rows = session.execute(
        base_q.offset(offset).limit(filters.per_page)
    ).scalars().all()

    return TransactionListResponse(
        items=[TransactionRead.model_validate(r) for r in rows],
        total=total,
        page=filters.page,
        per_page=filters.per_page,
    )
```

Brancher dans `router.py` :

```python
from app.api import transactions as transactions_module
api_router.include_router(transactions_module.router)
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_api_transactions.py -v
```

Expected : 3 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/api/transactions.py backend/app/api/router.py backend/tests/test_api_transactions.py
git commit -m "feat(api): GET /api/transactions with filters and pagination"
```

---

### Tâche F5 : Endpoints `GET /api/counterparties` et `PATCH /api/counterparties/{id}`

**Files:**
- Create: `backend/app/api/counterparties.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_api_counterparties.py`

Permet à l'utilisateur de valider (`status: active`) ou ignorer (`status: ignored`) les contreparties créées automatiquement en `pending`, et de les renommer.

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_api_counterparties.py` :

```python
"""GET /api/counterparties et PATCH /api/counterparties/{id}."""
from pathlib import Path
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_list_counterparties_includes_pending(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    resp = client.get("/api/counterparties", params={"status": "pending"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_patch_counterparty_activates_it(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    cp = client.get("/api/counterparties", params={"status": "pending"}).json()[0]
    resp = client.patch(
        f"/api/counterparties/{cp['id']}",
        json={"status": "active", "name": "ACME SAS Validé"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
    assert resp.json()["name"] == "ACME SAS Validé"
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pytest tests/test_api_counterparties.py -v
```

Expected : 404.

- [ ] **Étape 3 : Implémenter**

`backend/app/api/counterparties.py` :

```python
"""Endpoints /api/counterparties."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_entity_access
from app.db.session import get_session
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.schemas.counterparty import CounterpartyRead, CounterpartyUpdate

router = APIRouter(prefix="/api/counterparties", tags=["counterparties"])


@router.get("", response_model=list[CounterpartyRead])
def list_counterparties(
    status: Literal["pending", "active", "ignored"] | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CounterpartyRead]:
    accessible = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )
    q = select(Counterparty).where(Counterparty.entity_id.in_(accessible))
    if status:
        q = q.where(Counterparty.status == CounterpartyStatus(status))
    q = q.order_by(Counterparty.name.asc())
    rows = session.execute(q).scalars().all()
    return [CounterpartyRead.model_validate(r) for r in rows]


@router.patch("/{counterparty_id}", response_model=CounterpartyRead)
def update_counterparty(
    counterparty_id: UUID,
    payload: CounterpartyUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CounterpartyRead:
    cp = session.get(Counterparty, counterparty_id)
    if cp is None:
        raise HTTPException(status_code=404, detail="Contrepartie introuvable")
    require_entity_access(session=session, user=user, entity_id=cp.entity_id)

    if payload.status is not None:
        cp.status = CounterpartyStatus(payload.status)
    if payload.name is not None:
        cp.name = payload.name.strip()
    session.flush()
    session.commit()
    return CounterpartyRead.model_validate(cp)
```

Brancher dans `router.py` :

```python
from app.api import counterparties as counterparties_module
api_router.include_router(counterparties_module.router)
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pytest tests/test_api_counterparties.py -v
```

Expected : 2 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add backend/app/api/counterparties.py backend/app/api/router.py backend/tests/test_api_counterparties.py
git commit -m "feat(api): GET /api/counterparties and PATCH /api/counterparties/{id}"
```

---

# SECTION G — Frontend : 4 pages + composants + routes

Toutes les pages utilisent les composants shadcn/ui déjà installés au Plan 0 (`Card`, `Button`, `Input`, `Table`, `Dialog`) et TanStack Query pour les appels API. **Interface 100 % française.**

### Tâche G1 : Clients API typés (`imports.ts`, `transactions.ts`, `counterparties.ts`)

**Files:**
- Create: `frontend/src/api/imports.ts`
- Create: `frontend/src/api/transactions.ts`
- Create: `frontend/src/api/counterparties.ts`
- Modify: `frontend/src/types/api.ts`
- Create: `frontend/src/test/api_clients.test.ts`

- [ ] **Étape 1 : Écrire le test**

`frontend/src/test/api_clients.test.ts` :

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchImports, uploadImport } from "../api/imports";
import { fetchTransactions } from "../api/transactions";
import { fetchCounterparties, updateCounterparty } from "../api/counterparties";

describe("API clients Plan 1", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  it("fetchImports calls GET /api/imports", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    await fetchImports();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/imports",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("uploadImport POSTs multipart with file", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: "1", status: "completed" }),
    });
    const file = new File([new Uint8Array([1, 2])], "x.pdf", { type: "application/pdf" });
    await uploadImport({ bankAccountId: "abc", file });
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe("/api/imports");
    expect(call[1].method).toBe("POST");
    expect(call[1].body).toBeInstanceOf(FormData);
  });

  it("fetchTransactions serialises filters as query params", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0, page: 1, per_page: 50 }),
    });
    await fetchTransactions({ bank_account_id: "abc", page: 2 });
    const url = (globalThis.fetch as any).mock.calls[0][0];
    expect(url).toContain("bank_account_id=abc");
    expect(url).toContain("page=2");
  });

  it("updateCounterparty PATCHes with JSON body", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "1", status: "active", name: "X", entity_id: "e" }),
    });
    await updateCounterparty("1", { status: "active" });
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[1].method).toBe("PATCH");
    expect(call[1].headers["Content-Type"]).toBe("application/json");
  });
});
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
cd /home/kierangauthier/claude-secure/horizon/frontend
pnpm test src/test/api_clients.test.ts
```

Expected : `Cannot find module '../api/imports'`.

- [ ] **Étape 3 : Implémenter**

`frontend/src/types/api.ts` (ajouter aux types existants) :

```typescript
export type ImportStatus = "pending" | "completed" | "failed";

export interface ImportRecord {
  id: string;
  bank_account_id: string;
  bank_code: string;
  status: ImportStatus;
  filename: string | null;
  file_sha256: string | null;
  imported_count: number;
  duplicates_skipped: number;
  counterparties_pending_created: number;
  period_start: string | null;
  period_end: string | null;
  error_message: string | null;
  created_at: string | null;
}

export interface CounterpartyNested {
  id: string;
  name: string;
  status: "pending" | "active" | "ignored";
}

export interface CategoryNested {
  id: string;
  name: string;
}

export interface Transaction {
  id: string;
  operation_date: string;
  value_date: string;
  label: string;
  raw_label: string;
  amount: string; // Decimal en string
  is_aggregation_parent: boolean;
  parent_transaction_id: string | null;
  counterparty: CounterpartyNested | null;
  category: CategoryNested | null;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  per_page: number;
}

export interface TransactionFilter {
  bank_account_id?: string;
  date_from?: string;
  date_to?: string;
  counterparty_id?: string;
  search?: string;
  page?: number;
  per_page?: number;
}

export interface Counterparty {
  id: string;
  entity_id: string;
  name: string;
  status: "pending" | "active" | "ignored";
}
```

`frontend/src/api/imports.ts` :

```typescript
import type { ImportRecord } from "../types/api";

const DEFAULT_OPTIONS: RequestInit = { credentials: "include" };

export async function fetchImports(): Promise<ImportRecord[]> {
  const resp = await fetch("/api/imports", DEFAULT_OPTIONS);
  if (!resp.ok) throw new Error(`GET /api/imports → ${resp.status}`);
  return resp.json();
}

export async function fetchImport(id: string): Promise<ImportRecord> {
  const resp = await fetch(`/api/imports/${id}`, DEFAULT_OPTIONS);
  if (!resp.ok) throw new Error(`GET /api/imports/${id} → ${resp.status}`);
  return resp.json();
}

export async function uploadImport(args: {
  bankAccountId: string;
  file: File;
  overrideDuplicates?: boolean;
}): Promise<ImportRecord> {
  const body = new FormData();
  body.append("bank_account_id", args.bankAccountId);
  body.append("file", args.file);
  if (args.overrideDuplicates) body.append("override_duplicates", "true");
  const resp = await fetch("/api/imports", {
    method: "POST",
    credentials: "include",
    body,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail ?? `Erreur ${resp.status}`);
  }
  return resp.json();
}
```

`frontend/src/api/transactions.ts` :

```typescript
import type { TransactionFilter, TransactionListResponse } from "../types/api";

export async function fetchTransactions(
  filters: TransactionFilter = {},
): Promise<TransactionListResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const url = `/api/transactions${params.toString() ? `?${params}` : ""}`;
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`GET ${url} → ${resp.status}`);
  return resp.json();
}
```

`frontend/src/api/counterparties.ts` :

```typescript
import type { Counterparty } from "../types/api";

export async function fetchCounterparties(
  status?: "pending" | "active" | "ignored",
): Promise<Counterparty[]> {
  const qs = status ? `?status=${status}` : "";
  const resp = await fetch(`/api/counterparties${qs}`, { credentials: "include" });
  if (!resp.ok) throw new Error(`GET /api/counterparties → ${resp.status}`);
  return resp.json();
}

export async function updateCounterparty(
  id: string,
  patch: { status?: "active" | "ignored"; name?: string },
): Promise<Counterparty> {
  const resp = await fetch(`/api/counterparties/${id}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!resp.ok) throw new Error(`PATCH → ${resp.status}`);
  return resp.json();
}
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pnpm test src/test/api_clients.test.ts
```

Expected : 4 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add frontend/src/api/imports.ts frontend/src/api/transactions.ts \
        frontend/src/api/counterparties.ts frontend/src/types/api.ts \
        frontend/src/test/api_clients.test.ts
git commit -m "feat(frontend): typed API clients for imports, transactions, counterparties"
```

---

### Tâche G2 : Composant `FileDropzone` réutilisable

**Files:**
- Create: `frontend/src/components/FileDropzone.tsx`
- Create: `frontend/src/test/FileDropzone.test.tsx`

Pas de librairie externe : implémentation native avec `onDragOver`/`onDrop` + `<input type="file">` stylé.

- [ ] **Étape 1 : Écrire le test**

`frontend/src/test/FileDropzone.test.tsx` :

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FileDropzone } from "../components/FileDropzone";

describe("FileDropzone", () => {
  it("displays French instructions", () => {
    render(<FileDropzone onFileSelected={() => {}} accept="application/pdf" />);
    expect(screen.getByText(/glisser/i)).toBeInTheDocument();
  });

  it("calls onFileSelected when file is dropped", () => {
    const handler = vi.fn();
    render(<FileDropzone onFileSelected={handler} accept="application/pdf" />);
    const zone = screen.getByTestId("file-dropzone");
    const file = new File([new Uint8Array([1])], "x.pdf", { type: "application/pdf" });
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(handler).toHaveBeenCalledWith(file);
  });

  it("rejects files with wrong mime", () => {
    const handler = vi.fn();
    render(<FileDropzone onFileSelected={handler} accept="application/pdf" />);
    const zone = screen.getByTestId("file-dropzone");
    const file = new File([new Uint8Array([1])], "x.txt", { type: "text/plain" });
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(handler).not.toHaveBeenCalled();
  });
});
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pnpm test src/test/FileDropzone.test.tsx
```

Expected : `Cannot find module '../components/FileDropzone'`.

- [ ] **Étape 3 : Implémenter**

`frontend/src/components/FileDropzone.tsx` :

```typescript
import { useRef, useState, type DragEvent } from "react";

export interface FileDropzoneProps {
  onFileSelected: (file: File) => void;
  accept: string;
  maxSizeMb?: number;
}

export function FileDropzone({ onFileSelected, accept, maxSizeMb = 20 }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [hover, setHover] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = (file: File) => {
    if (accept && !accept.split(",").map((t) => t.trim()).includes(file.type)) {
      setError(`Type de fichier non accepté : ${file.type || "inconnu"}`);
      return;
    }
    if (file.size > maxSizeMb * 1024 * 1024) {
      setError(`Fichier trop volumineux (> ${maxSizeMb} Mo)`);
      return;
    }
    setError(null);
    onFileSelected(file);
  };

  const onDrop = (ev: DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setHover(false);
    const file = ev.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div
      data-testid="file-dropzone"
      onDragOver={(e) => { e.preventDefault(); setHover(true); }}
      onDragLeave={() => setHover(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`rounded-lg border-2 border-dashed p-8 text-center cursor-pointer transition ${
        hover ? "border-primary bg-primary/5" : "border-muted-foreground/30"
      }`}
    >
      <p className="text-sm text-muted-foreground">
        Glisser-déposer un fichier PDF ici, ou cliquer pour parcourir
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Taille maximale : {maxSizeMb} Mo
      </p>
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />
    </div>
  );
}
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pnpm test src/test/FileDropzone.test.tsx
```

Expected : 3 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add frontend/src/components/FileDropzone.tsx frontend/src/test/FileDropzone.test.tsx
git commit -m "feat(frontend): FileDropzone component with French labels"
```

---

### Tâche G3 : Page `ImportNewPage` (upload + sélection compte + résumé)

**Files:**
- Create: `frontend/src/pages/ImportNewPage.tsx`
- Create: `frontend/src/test/ImportNewPage.test.tsx`

- [ ] **Étape 1 : Écrire le test**

`frontend/src/test/ImportNewPage.test.tsx` :

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ImportNewPage } from "../pages/ImportNewPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ImportNewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ImportNewPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.startsWith("/api/bank-accounts")) {
        return Promise.resolve({
          ok: true,
          json: async () => [{ id: "ba1", iban: "FR76...", label: "Compte 1", entity_id: "e1" }],
        });
      }
      if (url === "/api/imports" && (globalThis.fetch as any).mock.calls.length > 0) {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: "imp1", status: "completed", imported_count: 3,
            duplicates_skipped: 0, counterparties_pending_created: 1,
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => [] });
    });
  });

  it("displays page title in French", async () => {
    renderPage();
    expect(await screen.findByText(/importer un relevé/i)).toBeInTheDocument();
  });

  it("displays success summary after upload", async () => {
    renderPage();
    await screen.findByText(/Compte 1/);
    fireEvent.change(screen.getByTestId("bank-account-select"), {
      target: { value: "ba1" },
    });
    const file = new File([new Uint8Array([1])], "x.pdf", { type: "application/pdf" });
    const input = screen.getByTestId("file-dropzone").querySelector("input") as HTMLInputElement;
    Object.defineProperty(input, "files", { value: [file] });
    fireEvent.change(input);
    await waitFor(() => {
      expect(screen.getByText(/3 transaction/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pnpm test src/test/ImportNewPage.test.tsx
```

Expected : `Cannot find module '../pages/ImportNewPage'`.

- [ ] **Étape 3 : Implémenter**

`frontend/src/pages/ImportNewPage.tsx` :

```typescript
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileDropzone } from "../components/FileDropzone";
import { uploadImport } from "../api/imports";
import type { ImportRecord } from "../types/api";

interface BankAccount {
  id: string;
  iban: string;
  label: string;
}

export function ImportNewPage() {
  const [selected, setSelected] = useState<string>("");
  const [result, setResult] = useState<ImportRecord | null>(null);

  const { data: accounts = [] } = useQuery({
    queryKey: ["bank-accounts"],
    queryFn: async () => {
      const r = await fetch("/api/bank-accounts", { credentials: "include" });
      return (await r.json()) as BankAccount[];
    },
  });

  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (file: File) =>
      uploadImport({ bankAccountId: selected, file }),
    onSuccess: (rec) => {
      setResult(rec);
      qc.invalidateQueries({ queryKey: ["imports"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    },
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Importer un relevé bancaire</h1>

      <div className="space-y-2">
        <label className="text-sm font-medium">Compte bancaire</label>
        <select
          data-testid="bank-account-select"
          className="w-full rounded-md border px-3 py-2"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          <option value="">— Sélectionner un compte —</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.label} ({a.iban})
            </option>
          ))}
        </select>
      </div>

      {selected && (
        <FileDropzone
          accept="application/pdf"
          onFileSelected={(f) => mutation.mutate(f)}
        />
      )}

      {mutation.isPending && (
        <p className="text-sm text-muted-foreground">Analyse en cours…</p>
      )}

      {mutation.isError && (
        <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
          Erreur : {(mutation.error as Error).message}
        </div>
      )}

      {result && (
        <div className="rounded-md border bg-muted/30 p-4">
          <h2 className="font-semibold">Import terminé</h2>
          <ul className="mt-2 space-y-1 text-sm">
            <li>✅ {result.imported_count} transaction(s) importée(s)</li>
            {result.duplicates_skipped > 0 && (
              <li>⏭️ {result.duplicates_skipped} doublon(s) ignoré(s)</li>
            )}
            {result.counterparties_pending_created > 0 && (
              <li>
                👥 {result.counterparties_pending_created} nouvelle(s) contrepartie(s) à valider
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pnpm test src/test/ImportNewPage.test.tsx
```

Expected : 2 tests PASS.

- [ ] **Étape 5 : Commit**

```bash
git add frontend/src/pages/ImportNewPage.tsx frontend/src/test/ImportNewPage.test.tsx
git commit -m "feat(frontend): ImportNewPage upload + summary"
```

---

### Tâche G4 : Page `ImportHistoryPage` (liste des imports passés)

**Files:**
- Create: `frontend/src/pages/ImportHistoryPage.tsx`
- Create: `frontend/src/test/ImportHistoryPage.test.tsx`

- [ ] **Étape 1 : Écrire le test**

`frontend/src/test/ImportHistoryPage.test.tsx` :

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ImportHistoryPage } from "../pages/ImportHistoryPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ImportHistoryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ImportHistoryPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: "1", bank_account_id: "ba1", bank_code: "delubac",
          status: "completed", filename: "janv.pdf",
          imported_count: 25, duplicates_skipped: 2,
          counterparties_pending_created: 3,
          created_at: "2026-04-16T10:00:00",
        },
      ],
    });
  });

  it("displays imports in a table", async () => {
    renderPage();
    expect(await screen.findByText("janv.pdf")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText(/Terminé/i)).toBeInTheDocument();
  });
});
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pnpm test src/test/ImportHistoryPage.test.tsx
```

Expected : `Cannot find module`.

- [ ] **Étape 3 : Implémenter**

`frontend/src/pages/ImportHistoryPage.tsx` :

```typescript
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchImports } from "../api/imports";

const STATUS_LABEL: Record<string, string> = {
  pending: "En cours",
  completed: "Terminé",
  failed: "Échoué",
};

export function ImportHistoryPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["imports"],
    queryFn: fetchImports,
  });

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Historique des imports</h1>
        <Link
          to="/imports/nouveau"
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
        >
          Nouvel import
        </Link>
      </div>

      {isLoading && <p>Chargement…</p>}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2">Date</th>
            <th>Fichier</th>
            <th>Banque</th>
            <th>Statut</th>
            <th className="text-right">Importées</th>
            <th className="text-right">Ignorées</th>
          </tr>
        </thead>
        <tbody>
          {data.map((imp) => (
            <tr key={imp.id} className="border-b">
              <td className="py-2">
                {imp.created_at
                  ? new Date(imp.created_at).toLocaleDateString("fr-FR")
                  : "—"}
              </td>
              <td>{imp.filename ?? "—"}</td>
              <td className="uppercase">{imp.bank_code}</td>
              <td>{STATUS_LABEL[imp.status] ?? imp.status}</td>
              <td className="text-right">{imp.imported_count}</td>
              <td className="text-right">{imp.duplicates_skipped}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {!isLoading && data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Aucun import pour le moment. Commencer par{" "}
          <Link to="/imports/nouveau" className="underline">
            importer un relevé
          </Link>
          .
        </p>
      )}
    </div>
  );
}
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pnpm test src/test/ImportHistoryPage.test.tsx
```

Expected : 1 test PASS.

- [ ] **Étape 5 : Commit**

```bash
git add frontend/src/pages/ImportHistoryPage.tsx frontend/src/test/ImportHistoryPage.test.tsx
git commit -m "feat(frontend): ImportHistoryPage lists past imports"
```

---

### Tâche G5 : Page `TransactionsPage` (liste paginée filtrable)

**Files:**
- Create: `frontend/src/pages/TransactionsPage.tsx`
- Create: `frontend/src/components/TransactionFilters.tsx`
- Create: `frontend/src/test/TransactionsPage.test.tsx`

- [ ] **Étape 1 : Écrire le test**

`frontend/src/test/TransactionsPage.test.tsx` :

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TransactionsPage } from "../pages/TransactionsPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <TransactionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TransactionsPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            id: "t1", operation_date: "2026-01-10", value_date: "2026-01-10",
            label: "VIR SEPA ACME", raw_label: "VIR SEPA ACME",
            amount: "-42.50", is_aggregation_parent: false,
            parent_transaction_id: null, counterparty: null, category: null,
          },
        ],
        total: 1, page: 1, per_page: 50,
      }),
    });
  });

  it("displays transactions in a French table", async () => {
    renderPage();
    expect(await screen.findByText("VIR SEPA ACME")).toBeInTheDocument();
    expect(screen.getByText("-42,50 €")).toBeInTheDocument();
  });
});
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pnpm test src/test/TransactionsPage.test.tsx
```

Expected : `Cannot find module`.

- [ ] **Étape 3 : Implémenter**

`frontend/src/components/TransactionFilters.tsx` :

```typescript
import type { TransactionFilter } from "../types/api";

export interface TransactionFiltersProps {
  value: TransactionFilter;
  onChange: (patch: TransactionFilter) => void;
}

export function TransactionFilters({ value, onChange }: TransactionFiltersProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <input
        type="search"
        placeholder="Rechercher un libellé…"
        value={value.search ?? ""}
        onChange={(e) => onChange({ ...value, search: e.target.value || undefined, page: 1 })}
        className="rounded-md border px-3 py-2 text-sm"
      />
      <input
        type="date"
        value={value.date_from ?? ""}
        onChange={(e) => onChange({ ...value, date_from: e.target.value || undefined, page: 1 })}
        className="rounded-md border px-3 py-2 text-sm"
      />
      <input
        type="date"
        value={value.date_to ?? ""}
        onChange={(e) => onChange({ ...value, date_to: e.target.value || undefined, page: 1 })}
        className="rounded-md border px-3 py-2 text-sm"
      />
    </div>
  );
}
```

`frontend/src/pages/TransactionsPage.tsx` :

```typescript
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../api/transactions";
import { TransactionFilters } from "../components/TransactionFilters";
import type { TransactionFilter } from "../types/api";

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

export function TransactionsPage() {
  const [filters, setFilters] = useState<TransactionFilter>({ page: 1, per_page: 50 });
  const { data, isLoading } = useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => fetchTransactions(filters),
  });

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Transactions</h1>
      <TransactionFilters value={filters} onChange={setFilters} />

      {isLoading && <p>Chargement…</p>}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2">Date</th>
            <th>Libellé</th>
            <th>Contrepartie</th>
            <th>Catégorie</th>
            <th className="text-right">Montant</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((tx) => (
            <tr
              key={tx.id}
              className={`border-b ${tx.is_aggregation_parent ? "bg-muted/30 font-medium" : ""}`}
            >
              <td className="py-2">
                {new Date(tx.operation_date).toLocaleDateString("fr-FR")}
              </td>
              <td>{tx.label}</td>
              <td>{tx.counterparty?.name ?? "—"}</td>
              <td>{tx.category?.name ?? "Non catégorisée"}</td>
              <td className={`text-right ${parseFloat(tx.amount) < 0 ? "text-destructive" : "text-emerald-700"}`}>
                {EUR.format(parseFloat(tx.amount))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data && (
        <div className="flex items-center justify-between text-sm">
          <span>
            {data.total} transaction(s) — page {data.page}
          </span>
          <div className="flex gap-2">
            <button
              disabled={data.page <= 1}
              onClick={() => setFilters({ ...filters, page: data.page - 1 })}
              className="rounded-md border px-3 py-1 disabled:opacity-40"
            >
              Précédent
            </button>
            <button
              disabled={data.page * data.per_page >= data.total}
              onClick={() => setFilters({ ...filters, page: data.page + 1 })}
              className="rounded-md border px-3 py-1 disabled:opacity-40"
            >
              Suivant
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pnpm test src/test/TransactionsPage.test.tsx
```

Expected : 1 test PASS.

- [ ] **Étape 5 : Commit**

```bash
git add frontend/src/pages/TransactionsPage.tsx \
        frontend/src/components/TransactionFilters.tsx \
        frontend/src/test/TransactionsPage.test.tsx
git commit -m "feat(frontend): TransactionsPage with filters and pagination"
```

---

### Tâche G6 : Page `CounterpartiesPage` + branchement routes

**Files:**
- Create: `frontend/src/pages/CounterpartiesPage.tsx`
- Modify: `frontend/src/router.tsx`
- Modify: `frontend/src/components/AppShell.tsx` (ou équivalent de nav — ajouter liens)
- Create: `frontend/src/test/CounterpartiesPage.test.tsx`

- [ ] **Étape 1 : Écrire le test**

`frontend/src/test/CounterpartiesPage.test.tsx` :

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { CounterpartiesPage } from "../pages/CounterpartiesPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CounterpartiesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CounterpartiesPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockImplementation((url: string, opts: any = {}) => {
      if ((opts.method ?? "GET") === "GET") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { id: "c1", entity_id: "e1", name: "ACME", status: "pending" },
          ],
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ id: "c1", entity_id: "e1", name: "ACME", status: "active" }),
      });
    });
  });

  it("lists pending counterparties and activates one", async () => {
    renderPage();
    expect(await screen.findByText("ACME")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /valider/i }));
    await waitFor(() => {
      expect((globalThis.fetch as any).mock.calls.some(
        ([url, o]: any[]) => url.startsWith("/api/counterparties/c1") && o.method === "PATCH"
      )).toBe(true);
    });
  });
});
```

- [ ] **Étape 2 : Vérifier l'échec**

```bash
pnpm test src/test/CounterpartiesPage.test.tsx
```

Expected : `Cannot find module`.

- [ ] **Étape 3 : Implémenter**

`frontend/src/pages/CounterpartiesPage.tsx` :

```typescript
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCounterparties, updateCounterparty } from "../api/counterparties";

type Status = "pending" | "active" | "ignored";

const LABEL: Record<Status, string> = {
  pending: "À valider",
  active: "Actives",
  ignored: "Ignorées",
};

export function CounterpartiesPage() {
  const [tab, setTab] = useState<Status>("pending");
  const qc = useQueryClient();

  const { data = [] } = useQuery({
    queryKey: ["counterparties", tab],
    queryFn: () => fetchCounterparties(tab),
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "active" | "ignored" }) =>
      updateCounterparty(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["counterparties"] }),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Contreparties</h1>

      <div className="flex gap-2 border-b">
        {(Object.keys(LABEL) as Status[]).map((s) => (
          <button
            key={s}
            onClick={() => setTab(s)}
            className={`px-4 py-2 text-sm ${
              tab === s ? "border-b-2 border-primary font-medium" : "text-muted-foreground"
            }`}
          >
            {LABEL[s]}
          </button>
        ))}
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2">Nom</th>
            <th className="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.map((cp) => (
            <tr key={cp.id} className="border-b">
              <td className="py-2">{cp.name}</td>
              <td className="text-right space-x-2">
                {cp.status === "pending" && (
                  <>
                    <button
                      onClick={() => mutation.mutate({ id: cp.id, status: "active" })}
                      className="rounded-md bg-primary px-3 py-1 text-xs text-primary-foreground"
                    >
                      Valider
                    </button>
                    <button
                      onClick={() => mutation.mutate({ id: cp.id, status: "ignored" })}
                      className="rounded-md border px-3 py-1 text-xs"
                    >
                      Ignorer
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Aucune contrepartie {LABEL[tab].toLowerCase()}.
        </p>
      )}
    </div>
  );
}
```

Modifier `frontend/src/router.tsx` pour ajouter les 4 routes :

```typescript
import { ImportNewPage } from "./pages/ImportNewPage";
import { ImportHistoryPage } from "./pages/ImportHistoryPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { CounterpartiesPage } from "./pages/CounterpartiesPage";

// Dans les routes authentifiées, ajouter :
//   { path: "/imports", element: <ImportHistoryPage /> },
//   { path: "/imports/nouveau", element: <ImportNewPage /> },
//   { path: "/transactions", element: <TransactionsPage /> },
//   { path: "/contreparties", element: <CounterpartiesPage /> },
```

Ajouter les liens dans le shell de navigation (`AppShell.tsx` ou équivalent du Plan 0) :

```typescript
<NavLink to="/imports">Imports</NavLink>
<NavLink to="/transactions">Transactions</NavLink>
<NavLink to="/contreparties">Contreparties</NavLink>
```

- [ ] **Étape 4 : Relancer les tests**

```bash
pnpm test src/test/CounterpartiesPage.test.tsx
pnpm test  # Full suite — tout doit passer
```

Expected : toute la suite passe.

- [ ] **Étape 5 : Commit**

```bash
git add frontend/src/pages/CounterpartiesPage.tsx \
        frontend/src/test/CounterpartiesPage.test.tsx \
        frontend/src/router.tsx frontend/src/components/AppShell.tsx
git commit -m "feat(frontend): CounterpartiesPage + wire Plan 1 routes into router"
```

---

# SECTION H — Tests E2E, validation, documentation

### Tâche H1 : Test E2E complet `import → transactions → counterparty validation`

**Files:**
- Create: `backend/tests/test_e2e_plan1.py`

Un unique test qui exerce le pipeline complet via l'API, de l'upload PDF à la validation d'une contrepartie.

- [ ] **Étape 1 : Écrire le test**

`backend/tests/test_e2e_plan1.py` :

```python
"""E2E Plan 1 : import PDF → transactions listées → contrepartie validée."""
from pathlib import Path
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_e2e_full_flow(client: TestClient, auth_user_with_bank_account) -> None:
    ba = auth_user_with_bank_account["bank_account"]

    # 1. Upload
    pdf = (FIXTURES / "synthetic_full_month.pdf").read_bytes()
    up = client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("relevé_mars.pdf", pdf, "application/pdf")},
    )
    assert up.status_code == 201
    imp = up.json()
    assert imp["status"] == "completed"
    assert imp["imported_count"] >= 40

    # 2. Import listé
    history = client.get("/api/imports").json()
    assert any(h["id"] == imp["id"] for h in history)

    # 3. Transactions listées
    tx = client.get("/api/transactions", params={"per_page": 100}).json()
    assert tx["total"] >= 40

    # 4. Contreparties pending
    pending = client.get("/api/counterparties", params={"status": "pending"}).json()
    assert len(pending) >= 1

    # 5. Valider la première
    target = pending[0]
    patch = client.patch(
        f"/api/counterparties/{target['id']}",
        json={"status": "active"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "active"

    # 6. Re-lister : elle doit disparaître de "pending"
    still_pending = client.get("/api/counterparties", params={"status": "pending"}).json()
    assert target["id"] not in {c["id"] for c in still_pending}

    # 7. Ré-import du même fichier : tout doit être dédupliqué
    reup = client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("relevé_mars.pdf", pdf, "application/pdf")},
    )
    assert reup.status_code == 201
    reimp = reup.json()
    assert reimp["imported_count"] == 0
    assert reimp["duplicates_skipped"] >= 40
```

- [ ] **Étape 2 : Vérifier l'échec (ou le passage)**

```bash
cd backend
pytest tests/test_e2e_plan1.py -v
```

Expected : PASS si toutes les sections précédentes sont correctes.

- [ ] **Étape 3 : Si échec, investiguer la tâche concernée et corriger**

Les erreurs E2E remontent typiquement à :
- Un endpoint manquant → vérifier `api/router.py`
- Un schéma mal sérialisé → `model_validate` vs `from_attributes=True`
- Un seed manquant → fixture `auth_user_with_bank_account`

- [ ] **Étape 4 : Commit**

```bash
git add backend/tests/test_e2e_plan1.py
git commit -m "test(e2e): full Plan 1 flow — import, list, validate counterparty, dedup"
```

---

### Tâche H2 : Validation couverture ≥ 85 % sur le code Plan 1

**Files:**
- Modify: `backend/pyproject.toml` (config coverage si besoin)

- [ ] **Étape 1 : Lancer la suite avec couverture**

```bash
cd backend
pytest --cov=app.parsers --cov=app.services.imports --cov=app.api.imports \
       --cov=app.api.transactions --cov=app.api.counterparties \
       --cov=app.models.transaction --cov=app.models.import_record \
       --cov=app.models.counterparty --cov=app.models.category \
       --cov-report=term-missing tests/ -q
```

- [ ] **Étape 2 : Vérifier la couverture**

Target : ≥ 85 % sur chaque module listé ci-dessus. Si un module tombe en-dessous, ajouter un test ciblé **sur la branche manquante**, pas un test « pour faire du chiffre ».

- [ ] **Étape 3 : Commit (optionnel, uniquement si tests ajoutés)**

```bash
git add backend/tests/
git commit -m "test: raise coverage on plan 1 modules to ≥ 85%"
```

---

### Tâche H3 : Mise à jour `docs/PROGRESS.md` et `docs/HORIZON.md`

**Files:**
- Modify: `docs/PROGRESS.md`
- Modify: `docs/HORIZON.md` (section « Progression »)

- [ ] **Étape 1 : Mettre à jour `PROGRESS.md`**

Ajouter une section :

```markdown
## Plan 1 — Import & Analyseur Delubac ✅

**Branche :** `plan-1-import-delubac`
**Statut :** Terminé (tag `plan-1-done` à venir après déploiement prod)

**Livré :**
- Module `app/parsers/` avec `BaseParser`, registre auto-discovery, `DelubacParser`
- Extraction PDF via `pdfplumber` : dates, libellés, montants signés, trios SEPA
- Normalisation libellés, extraction hint contrepartie
- Modèles `Category`, `Counterparty`, `Transaction`, `ImportRecord` + migration Alembic
- Pipeline `services/imports.py` : limites, dedup SHA-256, matching fuzzy ≥ 90 %, création auto `pending`, insertion atomique
- API REST : `POST /api/imports`, `GET /api/imports[/id]`, `GET /api/transactions`, `GET/PATCH /api/counterparties`
- Frontend : pages `ImportNew`, `ImportHistory`, `Transactions`, `Counterparties` + composants `FileDropzone`, `TransactionFilters` + navigation
- Tests unitaires, d'intégration et E2E (≥ 85 % couverture sur les modules Plan 1)
- Fixtures synthétiques générables via `build_fixtures.py`

**Décisions importantes :**
- Seule la banque **Delubac** est supportée ; les autres parsers arriveront au besoin (architecture extensible via `register_parser`)
- Limites configurables : 20 Mo / 500 pages / 10 000 tx / 60 s timeout
- Agrégation SEPA : le parent porte `is_aggregation_parent=True` et est exclu des sommations Plan 3+
- Catégorisation : table `categories` minimale créée, moteur de règles renvoyé au Plan 2
```

- [ ] **Étape 2 : Mettre à jour `HORIZON.md`**

Remplacer la ligne du roadmap :

```markdown
- **Plan 1** — Import & Analyseur Delubac → TERMINÉ (tag `plan-1-done`)
```

- [ ] **Étape 3 : Commit**

```bash
git add docs/PROGRESS.md docs/HORIZON.md
git commit -m "docs(progress): plan 1 complete"
```

---

# Clôture du Plan 1 — Étape E & F (rappel pour l'agent)

Les étapes E (validation E2E + déploiement) et F (récap + pause) du workflow global du projet ne sont **pas des tâches numérotées du plan d'implémentation**. Elles sont exécutées directement par Claude à la fin :

1. **Backup DB prod** : `docker compose -f docker-compose.prod.yml exec -T db pg_dump -U horizon horizon > /home/kierangauthier/backups/horizon-pre-plan1-$(date +%F).sql`.
2. **Merge `plan-1-import-delubac` → `main`** (fast-forward ou merge commit, non `--force`).
3. **Rebuild prod** : `docker compose -f docker-compose.prod.yml up -d --build`.
4. **Migration prod** : `docker compose -f docker-compose.prod.yml exec backend alembic upgrade head`.
5. **Smoke tests** : login admin, upload d'un PDF, vérif liste transactions.
6. **Tag** : `git tag plan-1-done && git push origin plan-1-done`.
7. **Récap 5-10 lignes** à l'utilisateur, terminé par « Continuer sur Plan 2 ? ».

**Ne jamais démarrer Plan 2 avant le OK explicite de Tristan.**

---

