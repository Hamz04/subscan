"""
Bank Statement Parser
Supports: RBC, TD, Scotiabank, BMO, CIBC
Formats: CSV, PDF
Output: Normalized pandas DataFrame
"""

import re
import io
import logging
from datetime import datetime
from typing import Optional
import pandas as pd
import pdfplumber
from dateutil import parser as dateparser

logger = logging.getLogger(__name__)

STANDARD_COLUMNS = ["date", "description", "amount", "type", "bank"]

BANK_SIGNATURES = {
    "rbc": ["rbc", "royal bank", "account statement", "chequing account"],
    "td": ["td bank", "toronto-dominion", "td canada trust"],
    "scotiabank": ["scotiabank", "scotia", "bank of nova scotia"],
    "bmo": ["bmo", "bank of montreal"],
    "cibc": ["cibc", "canadian imperial"],
}

RBC_CSV_COLUMNS = {
    "Account Type": "account_type",
    "Account Number": "account_number",
    "Transaction Date": "date",
    "Cheque Number": "cheque",
    "Description 1": "desc1",
    "Description 2": "desc2",
    "CAD$": "amount",
    "USD$": "usd_amount",
}

TD_CSV_COLUMNS = {
    "date": "date",
    "description": "description",
    "debit": "debit",
    "credit": "credit",
    "balance": "balance",
}

def detect_bank(content: str) -> str:
    content_lower = content.lower()
    for bank, signatures in BANK_SIGNATURES.items():
        if any(sig in content_lower for sig in signatures):
            return bank
    return "unknown"

def parse_amount(val) -> float:
    if pd.isna(val) or val == "":
        return 0.0
    val = str(val).replace(",", "").replace("$", "").strip()
    try:
        return float(val)
    except ValueError:
        return 0.0

def normalize_date(val) -> Optional[datetime]:
    try:
        return dateparser.parse(str(val))
    except Exception:
        return None

def parse_rbc_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=RBC_CSV_COLUMNS)
    df["description"] = df.get("desc1", "").fillna("") + " " + df.get("desc2", "").fillna("")
    df["description"] = df["description"].str.strip()
    df["amount"] = df["amount"].apply(parse_amount)
    df["date"] = df["date"].apply(normalize_date)
    df["type"] = df["amount"].apply(lambda x: "debit" if x < 0 else "credit")
    df["bank"] = "rbc"
    return df[STANDARD_COLUMNS]

def parse_td_csv(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c.lower().strip() for c in df.columns]
    df.columns = cols
    if "debit" in cols and "credit" in cols:
        df["amount"] = df["debit"].apply(parse_amount) * -1
        credits = df["credit"].apply(parse_amount)
        df["amount"] = df["amount"].where(df["amount"] != 0, credits)
    else:
        df["amount"] = df.iloc[:, 1].apply(parse_amount)
    df["date"] = df["date"].apply(normalize_date)
    df["description"] = df.get("description", df.iloc[:, 2]).fillna("").astype(str)
    df["type"] = df["amount"].apply(lambda x: "debit" if x < 0 else "credit")
    df["bank"] = "td"
    return df[STANDARD_COLUMNS]

def parse_generic_csv(df: pd.DataFrame, bank: str) -> pd.DataFrame:
    cols = [c.lower().strip() for c in df.columns]
    df.columns = cols
    date_col = next((c for c in cols if "date" in c), cols[0])
    desc_col = next((c for c in cols if any(k in c for k in ["desc", "narr", "memo", "detail", "name"])), cols[1] if len(cols) > 1 else cols[0])
    amount_col = next((c for c in cols if any(k in c for k in ["amount", "debit", "cad", "withdrawal"])), cols[-1])
    df["date"] = df[date_col].apply(normalize_date)
    df["description"] = df[desc_col].fillna("").astype(str)
    df["amount"] = df[amount_col].apply(parse_amount)
    df["type"] = df["amount"].apply(lambda x: "debit" if x < 0 else "credit")
    df["bank"] = bank
    return df[STANDARD_COLUMNS]

def parse_pdf_statement(content: bytes, bank: str) -> pd.DataFrame:
    rows = []
    date_pattern = re.compile(r"(\w{3}\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
    amount_pattern = re.compile(r"-?\$?[\d,]+\.\d{2}")
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if row and len(row) >= 3:
                            rows.append(row)
            else:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    dates = date_pattern.findall(line)
                    amounts = amount_pattern.findall(line)
                    if dates and amounts:
                        date_val = normalize_date(dates[0])
                        amount_val = parse_amount(amounts[-1])
                        desc = re.sub(r"(\w{3}\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|-?\$?[\d,]+\.\d{2})", "", line).strip()
                        rows.append({"date": date_val, "description": desc, "amount": amount_val, "type": "debit" if amount_val < 0 else "credit", "bank": bank})
    if not rows:
        return pd.DataFrame(columns=STANDARD_COLUMNS)
    df = pd.DataFrame(rows)
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "description", df.columns[-1]: "amount"})
        df["date"] = df["date"].apply(normalize_date)
        df["amount"] = df["amount"].apply(parse_amount)
        df["type"] = df["amount"].apply(lambda x: "debit" if x < 0 else "credit")
        df["bank"] = bank
    return df[STANDARD_COLUMNS]

def parse_statement(content: bytes, filename: str) -> pd.DataFrame:
    content_str = content.decode("utf-8", errors="ignore")
    bank = detect_bank(content_str)
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        df = parse_pdf_statement(content, bank)
    else:
        try:
            df_raw = pd.read_csv(io.BytesIO(content))
        except Exception:
            df_raw = pd.read_csv(io.BytesIO(content), encoding="latin-1")
        if bank == "rbc":
            df = parse_rbc_csv(df_raw)
        elif bank == "td":
            df = parse_td_csv(df_raw)
        else:
            df = parse_generic_csv(df_raw, bank)
    df = df[df["date"].notna()].copy()
    df["amount"] = df["amount"].abs()
    df = df[df["type"] == "debit"].copy()
    df = df.sort_values("date").reset_index(drop=True)
    return df
