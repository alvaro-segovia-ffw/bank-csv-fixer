# Hope Apartments CSV Exporter

Simple tool to convert bank CSV files into:
- SumUp export
- Retool export

## Run locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create `.env`:

```dotenv
IBAN_Kontoinhaber=YOUR_IBAN_OR_ACCOUNT_VALUE
```

3. Start the web app:

```bash
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

## CLI usage

```bash
python src/fix_bank_csv.py "input.csv" "sumup_export.csv" \
  --ontool-output-csv "retool_export.csv" \
  --ontool-iban "YOUR_IBAN_OR_ACCOUNT_VALUE"
```

## Vercel deploy

This project is ready for Vercel (`vercel.json` + `api/index.py` already included).

1. Push to GitHub.
2. Import the repo in Vercel.
3. Add env var in Vercel:
- `IBAN_Kontoinhaber=YOUR_IBAN_OR_ACCOUNT_VALUE`
4. Deploy.

Anyone with the deployed URL can use the app.

