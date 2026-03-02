#!/usr/bin/env python3
import base64
import io
import os
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Tuple, Union

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from src.fix_bank_csv import (
    DEFAULT_COUNTERPART_COL,
    DEFAULT_DATE_COL,
    DEFAULT_NEW_COL,
    DEFAULT_REFERENCE_COL,
    build_fixed_dataframe,
    build_ontool_dataframe,
)

load_dotenv()


def resolve_logo_src() -> str:
    base = Path(__file__).resolve().parent
    candidates = [
        base / "src" / "public" / "images" / "image.png",
        base.parent / "src" / "public" / "images" / "image.png",
        Path.cwd() / "src" / "public" / "images" / "image.png",
        Path("/var/task/src/public/images/image.png"),
        Path("/var/task/user/src/public/images/image.png"),
    ]
    for candidate in candidates:
        if candidate.exists():
            encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
    return "/public/images/image.png"


LOGO_SRC = resolve_logo_src()


def page_html(body: str, title: str = "Bank CSV Fixer", logo_src: str = "/public/images/image.png") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
    :root {{
      --bg: #f6f3ee;
      --surface: #ffffff;
      --ink: #182126;
      --muted: #67737c;
      --accent: #1f4a43;
      --accent-strong: #163831;
      --ring: #b8924f;
      --danger: #8f2d2d;
      --border: #e4e1da;
      --line: #ece8df;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "DM Sans", "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.86)),
        repeating-linear-gradient(
          0deg,
          transparent 0,
          transparent 26px,
          rgba(236, 232, 223, 0.55) 26px,
          rgba(236, 232, 223, 0.55) 27px
        ),
        var(--bg);
      min-height: 100vh;
      padding: 1.25rem 1rem 2rem;
    }}
    .shell {{
      width: 100%;
      max-width: 980px;
      margin: 0 auto;
    }}
    .navbar {{
      width: 100%;
      background: rgba(255, 255, 255, 0.78);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 0.8rem 1rem;
      box-shadow: 0 8px 24px rgba(24, 33, 38, 0.06);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.9rem;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 0.7rem;
    }}
    .navbar-logo {{
      width: 40px;
      height: 40px;
      border-radius: 10px;
      object-fit: cover;
      border: 1px solid var(--border);
    }}
    .navbar-title {{
      margin: 0;
      font-size: 1.18rem;
      font-family: "Source Serif 4", Georgia, serif;
      font-weight: 700;
      letter-spacing: 0.04em;
      color: #1e2f35;
    }}
    .navbar-note {{
      margin: 0;
      font-size: 0.79rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    main {{
      margin-top: 1rem;
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 1.5rem;
      box-shadow: 0 20px 48px rgba(24, 33, 38, 0.08);
    }}
    .hero {{
      margin-bottom: 1.2rem;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(1.65rem, 2.6vw, 2.15rem);
      line-height: 1.15;
      font-family: "Source Serif 4", Georgia, serif;
      font-weight: 700;
      letter-spacing: 0.012em;
      color: #172a30;
    }}
    .subtle {{
      margin: 0.4rem 0 0;
      color: var(--muted);
      max-width: 70ch;
      font-size: 0.98rem;
    }}
    .divider {{
      height: 1px;
      width: 100%;
      margin: 1rem 0 1.15rem;
      background: linear-gradient(90deg, #cbb38a 0%, var(--line) 34%, var(--line) 100%);
    }}
    .session {{
      margin: 0 0 1rem;
      color: #4f5d67;
      font-size: 0.93rem;
    }}
    .cards {{
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .card {{
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1rem;
      background: #fff;
    }}
    .card h2 {{
      margin: 0;
      font-size: 1.2rem;
      font-family: "Source Serif 4", Georgia, serif;
      color: #20353a;
      letter-spacing: 0.01em;
    }}
    .card p {{
      margin: 0.32rem 0 0.9rem;
      color: var(--muted);
      font-size: 0.93rem;
    }}
    p {{
      margin: 0.5rem 0;
      color: var(--muted);
    }}
    .stack > * + * {{ margin-top: 0.9rem; }}
    label {{
      font-size: 0.89rem;
      font-weight: 600;
      display: block;
      margin-bottom: 0.35rem;
      color: #2a3c40;
    }}
    input[type="text"], input[type="password"], input[type="file"] {{
      width: 100%;
      padding: 0.72rem 0.8rem;
      border: 1px solid #d8d3c8;
      border-radius: 10px;
      font-size: 0.96rem;
      color: var(--ink);
      background: #fffdfa;
    }}
    button {{
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: #fff;
      padding: 0.72rem 1rem;
      font-size: 0.93rem;
      font-weight: 600;
      letter-spacing: 0.01em;
      cursor: pointer;
      transition: background 160ms ease, transform 160ms ease;
    }}
    button:hover {{
      background: var(--accent-strong);
      transform: translateY(-1px);
    }}
    .ghost-btn {{
      background: transparent;
      color: #2f464b;
      border: 1px solid #d4d8db;
    }}
    .ghost-btn:hover {{
      background: #f6f8f8;
      transform: translateY(-1px);
    }}
    button:focus-visible, input:focus-visible {{
      outline: 3px solid var(--ring);
      outline-offset: 2px;
    }}
    .danger {{
      color: var(--danger);
      font-weight: 600;
      background: #fff4f4;
      border: 1px solid #efcdcd;
      border-radius: 10px;
      padding: 0.7rem 0.8rem;
      margin-bottom: 1rem;
    }}
    .auth-card {{
      width: min(470px, 100%);
      margin: 0 auto;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1rem;
      background: #fff;
    }}
    .auth-card button {{
      width: 100%;
    }}
    .row {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
    }}
    main form {{
      margin: 0;
    }}
    .small {{ font-size: 0.93rem; }}
    @media (max-width: 820px) {{
      .cards {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      body {{ padding: 0.8rem 0.65rem 1.2rem; }}
      main {{ padding: 1rem; border-radius: 16px; }}
      .navbar {{ border-radius: 14px; }}
      .navbar-note {{ display: none; }}
      .row form {{ width: 100%; }}
      .row form button {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <nav class="navbar" aria-label="Main navigation">
      <div class="brand">
        <img class="navbar-logo" src="{escape(logo_src, quote=True)}" alt="Hope Apartments logo">
        <p class="navbar-title">Hope Apartments</p>
      </div>
      <p class="navbar-note">Property Operations</p>
    </nav>
    <main>{body}</main>
  </div>
</body>
</html>"""


def app_page(error: str = "") -> HTMLResponse:
    error_html = (
        f'<p class="danger" role="alert" aria-live="polite">{escape(error)}</p>' if error else ""
    )
    body = f"""
    <div class="row">
      <h1>Accounting Exports</h1>
    </div>
    <p class="subtle">Upload your raw banking file and export it in the exact structure required by each destination.</p>
    <div class="divider"></div>
    {error_html}
    <section class="cards" aria-label="Export processes">
      <article class="card stack" aria-label="SumUp process">
        <h2>SumUp Export</h2>
        <p>Prepare and download the file used for SumUp imports.</p>
        <form method="post" action="/process/sumup" enctype="multipart/form-data" class="stack" aria-label="Upload CSV for SumUp">
          <div>
            <label for="sumup-file">CSV file (.csv)</label>
            <input id="sumup-file" name="file" type="file" accept=".csv,text/csv" required>
          </div>
          <button type="submit">Generate SumUp CSV</button>
        </form>
      </article>
      <article class="card stack" aria-label="Retool process">
        <h2>Retool Export</h2>
        <p>Prepare and download the file used for Retool imports.</p>
        <form method="post" action="/process/retool" enctype="multipart/form-data" class="stack" aria-label="Upload CSV for Retool">
          <div>
            <label for="retool-file">CSV file (.csv)</label>
            <input id="retool-file" name="file" type="file" accept=".csv,text/csv" required>
          </div>
          <button type="submit">Generate Retool CSV</button>
        </form>
      </article>
    </section>
    """
    return HTMLResponse(content=page_html(body, title="Bank CSV Fixer", logo_src=LOGO_SRC))


async def parse_uploaded_csv(request: Request, file: UploadFile) -> Union[Tuple[pd.DataFrame, str], HTMLResponse]:
    filename = file.filename or "bank_export.csv"
    if not filename.lower().endswith(".csv"):
        return app_page(error="Please upload a .csv file.")

    raw = await file.read()
    if not raw:
        return app_page(error="Uploaded file is empty.")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return app_page(error="File is not valid UTF-8.")

    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except Exception as exc:
        return app_page(error=f"Cannot read CSV file: {exc}")

    return df, filename


def build_output_filename(filename: str, export_type: str) -> str:
    stem = Path(filename).stem.strip().replace(" ", "_")
    stem = "".join(ch for ch in stem if ch.isalnum() or ch in {"_", "-"}).strip("_-")
    if not stem:
        stem = "bank_export"
    date_stamp = datetime.now().strftime("%Y%m%d")
    return f"hope_apartments_{stem}_{export_type}_{date_stamp}.csv"


app = FastAPI(title="Bank CSV Fixer")


def find_static_dir() -> Path:
    base = Path(__file__).resolve().parent
    candidates = [
        base / "src" / "public",
        base.parent / "src" / "public",
        Path.cwd() / "src" / "public",
        Path("/var/task/src/public"),
        Path("/var/task/user/src/public"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return base / "src" / "public"


static_dir = find_static_dir()
if static_dir.exists():
    app.mount("/public", StaticFiles(directory=static_dir), name="public")


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return app_page()


@app.post("/process/sumup")
async def process_sumup_file(request: Request, file: UploadFile = File(...)) -> Response:
    parsed = await parse_uploaded_csv(request, file)
    if isinstance(parsed, HTMLResponse):
        return parsed
    df, filename = parsed

    try:
        sumup_df = build_fixed_dataframe(
            df=df,
            date_col=DEFAULT_DATE_COL,
            counterparty_col=DEFAULT_COUNTERPART_COL,
            reference_col=DEFAULT_REFERENCE_COL,
            new_col=DEFAULT_NEW_COL,
        )
    except Exception as exc:
        return app_page(error=f"Cannot process file: {exc}")

    sumup_output = io.StringIO()
    sumup_df.to_csv(sumup_output, index=False, encoding="utf-8")
    output_name = build_output_filename(filename, "sumup_export")

    return Response(
        content=sumup_output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{output_name}"'},
    )


@app.post("/process/retool")
async def process_retool_file(request: Request, file: UploadFile = File(...)) -> Response:
    parsed = await parse_uploaded_csv(request, file)
    if isinstance(parsed, HTMLResponse):
        return parsed
    df, filename = parsed

    try:
        sumup_df = build_fixed_dataframe(
            df=df,
            date_col=DEFAULT_DATE_COL,
            counterparty_col=DEFAULT_COUNTERPART_COL,
            reference_col=DEFAULT_REFERENCE_COL,
            new_col=DEFAULT_NEW_COL,
        )
        ontool_df = build_ontool_dataframe(
            df=sumup_df,
            iban_kontoinhaber=os.getenv("IBAN_Kontoinhaber", "").strip(),
            date_col=DEFAULT_DATE_COL,
            reference_col=DEFAULT_REFERENCE_COL,
            counterparty_col=DEFAULT_COUNTERPART_COL,
        )
    except Exception as exc:
        return app_page(error=f"Cannot process file: {exc}")

    ontool_output = io.StringIO()
    ontool_df.to_csv(ontool_output, index=False, encoding="utf-8")
    output_name = build_output_filename(filename, "retool_export")

    return Response(
        content=ontool_output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{output_name}"'},
    )
