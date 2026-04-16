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
