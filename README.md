# SubScan 💳
> Upload your bank statement. Instantly see every subscription draining your account.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)

## What it does
- Parses RBC, TD, Scotiabank, BMO, CIBC bank statements (CSV + PDF)
- Detects recurring charges using pattern matching + frequency analysis
- Calculates your monthly subscription burn rate
- Shows exactly how much you'd save cancelling each subscription
- Flags free trials that are about to charge you

## Stack
- FastAPI backend with PDF/CSV parsing (pdfplumber + pandas)
- Streamlit dashboard
- Docker + docker-compose
- No data stored — everything processed in memory

## Run locally
```bash
docker-compose up
```
Then open http://localhost:8501
