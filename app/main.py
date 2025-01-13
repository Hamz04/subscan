"""
SubScan FastAPI Backend
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import logging

from app.parsers.statement_parser import parse_statement
from app.detectors.subscription_detector import detect_subscriptions
from app.calculators.savings_calculator import rank_cancellation_candidates, calculate_savings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SubScan API",
    description="Upload bank statements and detect subscriptions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "service": "SubScan API v1.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/analyze")
async def analyze_statement(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    ext = file.filename.lower().split(".")[-1]
    if ext not in ["csv", "pdf", "xlsx"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV, PDF, or XLSX.")
    try:
        content = await file.read()
        df = parse_statement(content, file.filename)
        if df.empty:
            raise HTTPException(status_code=422, detail="No transactions found in file. Check the format.")
        subscriptions = detect_subscriptions(df)
        if subscriptions.empty:
            return JSONResponse(content={"subscriptions": [], "savings": {}, "total_transactions": len(df)})
        ranked = rank_cancellation_candidates(subscriptions)
        savings = calculate_savings(ranked)
        return JSONResponse(content={
            "subscriptions": ranked.to_dict(orient="records"),
            "savings": savings,
            "total_transactions": len(df),
            "bank_detected": df["bank"].iloc[0] if not df.empty else "unknown"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/savings-projection")
async def savings_projection(file: UploadFile = File(...)):
    content = await file.read()
    df = parse_statement(content, file.filename)
    subscriptions = detect_subscriptions(df)
    ranked = rank_cancellation_candidates(subscriptions)
    all_savings = []
    for i in range(1, len(ranked) + 1):
        top_n = ranked.head(i)["service"].tolist()
        s = calculate_savings(ranked, top_n)
        all_savings.append({"cancel_count": i, "monthly_savings": s.get("potential_monthly_savings", 0), "annual_savings": s.get("potential_annual_savings", 0)})
    return JSONResponse(content={"projection": all_savings})
