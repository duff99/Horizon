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
