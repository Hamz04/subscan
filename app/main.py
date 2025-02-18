from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import pdfplumber
import io
import re
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SubScan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUBSCRIPTION_PATTERNS = {
    "Netflix": {"pattern": r"netflix", "category": "Entertainment", "avg_price": 17.99},
    "Spotify": {"pattern": r"spotify", "category": "Music", "avg_price": 11.99},
    "Apple": {"pattern": r"apple\.com/bill|apple services", "category": "Tech", "avg_price": 9.99},
    "Amazon Prime": {"pattern": r"amazon prime|amzn prime", "category": "Shopping", "avg_price": 9.99},
    "Disney+": {"pattern": r"disney\+|disney plus", "category": "Entertainment", "avg_price": 11.99},
    "YouTube Premium": {"pattern": r"youtube premium|google.*youtube", "category": "Entertainment", "avg_price": 13.99},
    "Adobe": {"pattern": r"adobe", "category": "Software", "avg_price": 54.99},
    "Microsoft 365": {"pattern": r"microsoft 365|office 365|msft", "category": "Software", "avg_price": 9.99},
    "GitHub": {"pattern": r"github", "category": "Dev Tools", "avg_price": 4.00},
    "Dropbox": {"pattern": r"dropbox", "category": "Storage", "avg_price": 11.99},
    "Google One": {"pattern": r"google one|google storage", "category": "Storage", "avg_price": 2.79},
    "iCloud": {"pattern": r"icloud", "category": "Storage", "avg_price": 3.99},
    "Hulu": {"pattern": r"hulu", "category": "Entertainment", "avg_price": 17.99},
    "Paramount+": {"pattern": r"paramount", "category": "Entertainment", "avg_price": 9.99},
    "Crave": {"pattern": r"crave", "category": "Entertainment", "avg_price": 19.99},
    "Xbox Game Pass": {"pattern": r"xbox|game pass", "category": "Gaming", "avg_price": 16.99},
    "PlayStation": {"pattern": r"playstation|psn", "category": "Gaming", "avg_price": 11.99},
    "Audible": {"pattern": r"audible", "category": "Books", "avg_price": 14.95},
    "LinkedIn Premium": {"pattern": r"linkedin", "category": "Professional", "avg_price": 39.99},
    "Notion": {"pattern": r"notion", "category": "Productivity", "avg_price": 10.00},
    "Figma": {"pattern": r"figma", "category": "Design", "avg_price": 15.00},
    "Gym": {"pattern": r"goodlife|anytime fitness|planet fitness|equinox|ymca|crunch", "category": "Health", "avg_price": 40.00},
    "DoorDash": {"pattern": r"dashpass|doordash", "category": "Food", "avg_price": 9.99},
    "Uber One": {"pattern": r"uber one|uber pass", "category": "Transport", "avg_price": 9.99},
}

def parse_rbc_csv(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    col_map = {}
    for col in df.columns:
        if "date" in col: col_map[col] = "date"
        elif "description" in col or "memo" in col: col_map[col] = "description"
        elif "amount" in col or "debit" in col or "credit" in col: col_map[col] = "amount"
    df = df.rename(columns=col_map)
    if "amount" not in df.columns and "debit" in df.columns:
        df["amount"] = df["debit"].fillna(0) - df.get("credit", pd.Series(0)).fillna(0)
    return df[["date", "description", "amount"]].dropna(subset=["date", "description"])

def parse_generic_csv(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    date_col = next((c for c in df.columns if "date" in c), None)
    desc_col = next((c for c in df.columns if any(x in c for x in ["desc", "memo", "narr", "detail", "merchant"])), None)
    amt_col = next((c for c in df.columns if any(x in c for x in ["amount", "debit", "withdrawal", "charge"])), None)
    if not all([date_col, desc_col, amt_col]):
        raise ValueError("Could not identify date, description, and amount columns")
    df = df.rename(columns={date_col: "date", desc_col: "description", amt_col: "amount"})
    df["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce").abs()
    return df[["date", "description", "amount"]].dropna()

def parse_pdf_statement(content: bytes) -> pd.DataFrame:
    transactions = []
    date_pattern = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3}\s+\d{1,2})\b")
    amount_pattern = re.compile(r"\$?\s*(\d{1,6}[.,]\d{2})")
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                date_match = date_pattern.search(line)
                amount_match = amount_pattern.search(line)
                if date_match and amount_match:
                    desc = re.sub(r"[\d$.,/-]", " ", line).strip()
                    desc = " ".join(desc.split())
                    if len(desc) > 3:
                        transactions.append({
                            "date": date_match.group(1),
                            "description": desc,
                            "amount": float(amount_match.group(1).replace(",", ""))
                        })
    return pd.DataFrame(transactions)

def detect_subscriptions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    df["description_lower"] = df["description"].str.lower().fillna("")
    detected = []
    for name, info in SUBSCRIPTION_PATTERNS.items():
        mask = df["description_lower"].str.contains(info["pattern"], regex=True, na=False)
        matches = df[mask].copy()
        if matches.empty:
            continue
        matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
        matches = matches.dropna(subset=["date"]).sort_values("date")
        avg_amount = matches["amount"].median()
        frequency = detect_frequency(matches)
        monthly_cost = avg_amount if frequency == "monthly" else (avg_amount / 12 if frequency == "annual" else avg_amount * 4.33)
        detected.append({
            "name": name,
            "category": info["category"],
            "avg_charge": round(float(avg_amount), 2),
            "monthly_cost": round(float(monthly_cost), 2),
            "annual_cost": round(float(monthly_cost * 12), 2),
            "frequency": frequency,
            "occurrences": len(matches),
            "last_charge": matches["date"].max().strftime("%Y-%m-%d") if not matches.empty else "N/A",
            "transactions": matches[["date", "description", "amount"]].tail(6).to_dict("records"),
        })
    return sorted(detected, key=lambda x: x["monthly_cost"], reverse=True)

def detect_frequency(df: pd.DataFrame) -> str:
    if len(df) < 2:
        return "monthly"
    df = df.sort_values("date")
    gaps = df["date"].diff().dt.days.dropna()
    avg_gap = gaps.mean()
    if avg_gap < 10: return "weekly"
    elif avg_gap < 45: return "monthly"
    elif avg_gap < 100: return "quarterly"
    else: return "annual"

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.post("/analyze")
async def analyze_statement(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename.lower()
    try:
        if filename.endswith(".pdf"):
            df = parse_pdf_statement(content)
        elif filename.endswith(".csv"):
            raw = pd.read_csv(io.BytesIO(content), encoding="utf-8", on_bad_lines="skip")
            try:
                df = parse_rbc_csv(raw.copy())
            except Exception:
                df = parse_generic_csv(raw.copy())
        else:
            raise HTTPException(status_code=400, detail="Only CSV and PDF files supported")
        if df.empty:
            raise HTTPException(status_code=422, detail="No transactions found in file")
        subscriptions = detect_subscriptions(df)
        total_monthly = sum(s["monthly_cost"] for s in subscriptions)
        total_annual = total_monthly * 12
        categories = defaultdict(float)
        for s in subscriptions:
            categories[s["category"]] += s["monthly_cost"]
        return {
            "total_transactions": len(df),
            "subscriptions_found": len(subscriptions),
            "total_monthly_burn": round(total_monthly, 2),
            "total_annual_burn": round(total_annual, 2),
            "potential_savings_if_cancel_all": round(total_annual, 2),
            "category_breakdown": dict(categories),
            "subscriptions": subscriptions,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
