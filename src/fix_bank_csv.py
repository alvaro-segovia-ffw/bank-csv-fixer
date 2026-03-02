#!/usr/bin/env python3
import argparse
import re
import pandas as pd


DEFAULT_DATE_COL = "Operation date (local)"
DEFAULT_COUNTERPART_COL = "Counterparty name"
DEFAULT_REFERENCE_COL = "Reference"
DEFAULT_NEW_COL = "qontodata"
DEFAULT_CREDIT_COL = "Credit"
DEFAULT_CURRENCY_COL = "Currency"
DEFAULT_PAYMENT_METHOD_COL = "Payment method"
DEFAULT_INITIATOR_COL = "Initiator"
FUTURE_FOR_PREFIX_RE = re.compile(r"^(Future\s+For-[^\s]+)\b", flags=re.IGNORECASE)


def to_ddmmyyyy(series: pd.Series) -> pd.Series:
    # Pandas >=2 supports "mixed" and avoids warnings with heterogeneous date formats.
    try:
        dt = pd.to_datetime(series, errors="coerce", dayfirst=True, format="mixed")
    except TypeError:
        dt = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return dt.dt.strftime("%d.%m.%Y")


def to_ddmmyy_hhmm(series: pd.Series) -> pd.Series:
    try:
        dt = pd.to_datetime(series, errors="coerce", dayfirst=True, format="mixed")
    except TypeError:
        dt = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return dt.dt.strftime("%d.%m.%y %H:%M")


def to_datetime_series(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", dayfirst=True, format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", dayfirst=True)


def to_dmy_no_zero(series: pd.Series) -> pd.Series:
    dt = to_datetime_series(series)
    out = pd.Series("", index=series.index, dtype=str)
    valid = dt.notna()
    out.loc[valid] = (
        dt.loc[valid].dt.day.astype(str)
        + "."
        + dt.loc[valid].dt.month.astype(str)
        + "."
        + dt.loc[valid].dt.year.astype(str)
    )
    return out


def build_fixed_dataframe(
    df: pd.DataFrame,
    date_col: str,
    counterparty_col: str,
    reference_col: str,
    new_col: str,
) -> pd.DataFrame:
    for col in [date_col, reference_col, counterparty_col]:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    out = df.copy()
    out[date_col] = to_ddmmyy_hhmm(out[date_col]).fillna("")
    out[new_col] = to_dmy_no_zero(out[date_col]).fillna("")

    reference_original = out[reference_col].fillna("").astype(str)
    counterparty = out[counterparty_col].fillna("").astype(str)
    initiator = out["Initiator"].fillna("").astype(str) if "Initiator" in out.columns else ""

    has_counterparty = counterparty.str.strip().ne("")
    reference_is_empty = reference_original.str.strip().eq("")
    initiator_has_value = initiator.str.strip().ne("") if isinstance(initiator, pd.Series) else False

    # Keep original reference by default.
    out[reference_col] = reference_original

    # If reference is empty and counterparty exists:
    # - Use "<counterparty> <Initiator>" when Initiator exists
    # - Otherwise use only counterparty.
    needs_counterparty_fill = reference_is_empty & has_counterparty
    if isinstance(initiator, pd.Series):
        initiator_pretty = initiator.str.strip().str.title()
        with_initiator = needs_counterparty_fill & initiator_has_value
        out.loc[with_initiator, reference_col] = (
            counterparty.loc[with_initiator].str.strip()
            + " "
            + initiator_pretty.loc[with_initiator]
        )

        without_initiator = needs_counterparty_fill & (~initiator_has_value)
        out.loc[without_initiator, reference_col] = counterparty.loc[without_initiator]
    else:
        out.loc[needs_counterparty_fill, reference_col] = counterparty.loc[needs_counterparty_fill]

    # If both counterparty and reference are empty, use formatted date.
    needs_date_fallback = (~has_counterparty) & reference_is_empty
    out.loc[needs_date_fallback, reference_col] = out.loc[needs_date_fallback, new_col]

    cols = list(out.columns)
    cols.remove(new_col)
    date_idx = cols.index(date_col)
    cols.insert(date_idx + 1, new_col)
    return out[cols]


def build_ontool_dataframe(
    df: pd.DataFrame,
    iban_kontoinhaber: str,
    date_col: str = DEFAULT_DATE_COL,
    reference_col: str = DEFAULT_REFERENCE_COL,
    counterparty_col: str = DEFAULT_COUNTERPART_COL,
    credit_col: str = DEFAULT_CREDIT_COL,
    currency_col: str = DEFAULT_CURRENCY_COL,
    payment_method_col: str = DEFAULT_PAYMENT_METHOD_COL,
) -> pd.DataFrame:
    for col in [date_col, reference_col, counterparty_col, credit_col, currency_col]:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    out = df.copy()
    credit_num = pd.to_numeric(out[credit_col].replace("", "0"), errors="coerce").fillna(0.0)
    out = out.loc[credit_num > 0].copy()
    credit_num = credit_num.loc[out.index]

    buchungstag = to_dmy_no_zero(out[date_col].fillna("").astype(str))

    if payment_method_col in out.columns:
        payment_method = out[payment_method_col].fillna("").astype(str).str.strip()
        umsatzart = payment_method.where(payment_method.ne("Transfer"), "Überweisung (Echtzeit)")
    else:
        umsatzart = pd.Series("Überweisung (Echtzeit)", index=out.index)

    buchungstext = out[reference_col].fillna("").astype(str)
    counterparty = out[counterparty_col].fillna("").astype(str)
    buchungstext = buchungstext.where(buchungstext.str.strip().ne(""), counterparty)

    # Special case from expected ontool format:
    # "Future For-<id> ..." becomes "Future For-<id> <Counterparty name>".
    future_prefix = buchungstext.str.extract(FUTURE_FOR_PREFIX_RE, expand=False).fillna("")
    special_mask = (future_prefix.str.strip() != "") & (counterparty.str.strip() != "")
    buchungstext = buchungstext.mask(
        special_mask,
        future_prefix.str.strip() + " " + counterparty.str.strip(),
    )

    ontool_df = pd.DataFrame(
        {
            "Buchungstag": buchungstag,
            "Wertstellung": buchungstag,
            "Umsatzart": umsatzart,
            "Buchungstext": buchungstext,
            "Betrag": credit_num.map(lambda x: f"{x:.2f}"),
            "Währung": out[currency_col].fillna("").astype(str),
            "IBAN_Kontoinhaber": iban_kontoinhaber,
            "Kategorie": "",
        }
    )
    return ontool_df.reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(
        description="Generate sumup and optional ontool exports from a bank CSV."
    )
    ap.add_argument("input_csv", help="Input CSV path")
    ap.add_argument("output_csv", help="Sumup output CSV path")
    ap.add_argument("--ontool-output-csv", help="Optional ontool output CSV path")

    ap.add_argument("--date-col", default=DEFAULT_DATE_COL, help="Date column name")
    ap.add_argument("--reference-col", default=DEFAULT_REFERENCE_COL, help="Reference column name")
    ap.add_argument("--counterparty-col", default=DEFAULT_COUNTERPART_COL, help="Counterparty name column")
    ap.add_argument("--new-col", default=DEFAULT_NEW_COL, help="New date column name (d.m.yyyy)")
    ap.add_argument(
        "--ontool-iban",
        default="",
        help="Value for IBAN_Kontoinhaber in ontool export",
    )

    ap.add_argument("--sep", default=",", help="CSV separator")
    ap.add_argument("--encoding", default="utf-8", help="CSV encoding")

    args = ap.parse_args()

    df = pd.read_csv(
        args.input_csv,
        dtype=str,
        keep_default_na=False,
        sep=args.sep,
        encoding=args.encoding,
    )

    try:
        sumup_df = build_fixed_dataframe(
            df=df,
            date_col=args.date_col,
            counterparty_col=args.counterparty_col,
            reference_col=args.reference_col,
            new_col=args.new_col,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    sumup_df.to_csv(args.output_csv, index=False, sep=args.sep, encoding=args.encoding)

    if args.ontool_output_csv:
        try:
            ontool_df = build_ontool_dataframe(
                df=sumup_df,
                iban_kontoinhaber=args.ontool_iban,
                date_col=args.date_col,
                reference_col=args.reference_col,
                counterparty_col=args.counterparty_col,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        ontool_df.to_csv(args.ontool_output_csv, index=False, sep=args.sep, encoding=args.encoding)


if __name__ == "__main__":
    main()
