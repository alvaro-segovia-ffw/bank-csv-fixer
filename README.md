# Bank CSV Fixer

Tool to automate modifications on a bank export CSV.

## What It Does
- Reads an input CSV.
- Generates a **sumup export**:
  - Inserts a new column right after `Operation date (local)` with format `dd.mm.yyyy`.
  - Updates `Reference` using these rules:
  - Keep original `Reference` when it already has a value.
  - If `Reference` is empty and `Counterparty name` has a value:
    - If `Initiator` exists: `Reference = "<Counterparty name> <Initiator>"`.
    - Otherwise: `Reference = Counterparty name`.
  - If both `Counterparty name` and `Reference` are empty: `Reference = formatted date`.
- Generates an **ontool export**:
  - Includes only rows with positive `Credit`.
  - Columns: `Buchungstag,Wertstellung,Umsatzart,Buchungstext,Betrag,Währung,IBAN_Kontoinhaber,Kategorie`.
  - `Umsatzart` maps `Transfer` -> `Überweisung (Echtzeit)`.
- Keeps all other sumup columns intact and preserves column order.

## Setup
1. Create or activate your virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## CLI Usage

```bash
python src/fix_bank_csv.py "data/original bank export.csv" "data/modified bank export.csv"
```

Optional arguments:
- `--date-col`
- `--reference-col`
- `--counterparty-col`
- `--new-col`
- `--sep`
- `--encoding`
- `--ontool-output-csv` (generate second file)
- `--ontool-iban` (value used for `IBAN_Kontoinhaber`)

Example (generate both files):

```bash
python src/fix_bank_csv.py "data/original bank export.csv" "data/sumup_export.csv" \
  --ontool-output-csv "data/ontool.csv" \
  --ontool-iban "DE33120400000073046500"
```

## Web App (FastAPI)
The web app supports login, CSV upload, processing, and download.

### Environment Variables
Environment is loaded automatically from `.env`.

- `APP_SECRET_KEY`:
  - Secret for session cookies.
  - Set this in production.
- `APP_USERS`:
  - Comma-separated credentials: `user1:pass1,user2:pass2`
  - Example: `APP_USERS="ops:strong-pass,finance:another-pass"`
- `ONTOOL_IBAN_KONTOINHABER`:
  - Value used in the generated ontool file.

If `APP_USERS` is not set, fallback is:
- `APP_USERNAME` (default: `admin`)
- `APP_PASSWORD` (default: `change-me`)

Example `.env`:

```dotenv
APP_SECRET_KEY=replace-with-a-strong-random-secret
APP_USERS=admin:change-me
ONTOOL_IBAN_KONTOINHABER=DE33120400000073046500
```

### Run Locally

```bash
uvicorn app:app --reload
```

Then open `http://127.0.0.1:8000`.
The web app has two separate processes:
- **SumUp Export**: downloads `*_sumup_export.csv`
- **Retool Export**: downloads `*_ontool.csv`

## Notes
- Expected input encoding is UTF-8.
- Non-parseable dates do not break processing; formatted date will be empty for those rows.
