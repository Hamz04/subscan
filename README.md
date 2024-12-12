# SubScan 💳

> Upload your bank statement. Instantly see every subscription bleeding your account dry.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## What it does

SubScan parses RBC, TD, Scotiabank, BMO, and CIBC bank statements (CSV or PDF) and automatically detects recurring subscriptions. It shows you exactly how much you're spending, flags ones you likely forgot about, and calculates your potential monthly savings if you cancel them.

## Features

- **Multi-bank support** — RBC, TD, Scotiabank, BMO, CIBC (CSV + PDF)
- **Smart subscription detection** — fuzzy matching + pattern recognition across 200+ known services
- **Savings calculator** — monthly, quarterly, annual projections
- **Cancellation priority** — ranks subscriptions by "most likely forgotten"
- **Category breakdown** — streaming, fitness, software, food, gaming
- **Privacy first** — all processing is local, nothing stored

## Stack

- FastAPI backend with file upload endpoint
- Streamlit dashboard with interactive charts
- pdfplumber for PDF parsing
- scikit-learn + fuzzy matching for subscription detection
- Plotly for visualizations
- Docker for deployment

## Quick Start

```bash
git clone https://github.com/Hamz04/subscan
cd subscan
pip install -r requirements.txt

# Start backend
uvicorn app.main:app --reload --port 8000

# Start dashboard (new terminal)
streamlit run dashboard/app.py
```

## Supported Banks

| Bank | CSV | PDF |
|------|-----|-----|
| RBC | ✅ | ✅ |
| TD | ✅ | ✅ |
| Scotiabank | ✅ | ✅ |
| BMO | ✅ | ✅ |
| CIBC | ✅ | ✅ |

## How It Works

1. Upload your bank statement (CSV or PDF)
2. SubScan detects the bank format automatically
3. Transactions are parsed and normalized
4. 200+ subscription patterns are matched using fuzzy logic
5. Results show spending breakdown + savings opportunities

## Privacy

Your statement never leaves your machine. All processing happens locally in memory — no database, no cloud storage, no logging of transaction data.

---

Built with ❤️ by Hamz04
