# NexusIQ — Document Fraud Detection 🔍

> AI-powered insurance document fraud detection system built with FastAPI, LangChain, and Quasar Marketplace LLM.

---

## 🎯 What It Does

NexusIQ analyzes uploaded PDF invoices (auto repair, medical bills, insurance claims) through a **5-step AI verification pipeline** to detect potential fraud:

| Step | Name | What It Checks |
|------|------|---------------|
| 1 | Data Extraction Summary | Extracts & validates all invoice fields using LLM |
| 2 | Arithmetic & Tax Validation | Re-calculates line items, tax, totals for manipulation |
| 3 | Vendor Legitimacy | Assesses if vendor is real or fictitious |
| 4 | Market Price Benchmarking | Compares prices against market rates |
| 5 | VIN Validation | Decodes vehicle VIN via NHTSA API |

The system produces a **fraud verdict**: ✅ Approve, ⚠️ Approve with Notation, or 🚨 Escalate to SIU.

---

## 🏗️ Architecture

```
┌────────────────────────────┐
│  Frontend (index.html)     │
│  Vanilla JS + Tailwind CSS │
│  Chat-based UI             │
└──────────┬─────────────────┘
           │ HTTP / NDJSON Streaming
           ▼
┌────────────────────────────┐
│  FastAPI Backend (:8000)   │
│  ├── Session Manager       │
│  ├── PDF Extraction (pdfplumber + LLM) │
│  ├── 5-Step Fraud Agent Pipeline       │
│  ├── Quasar LLM Gateway (x-api-key)   │
│  ├── PII Guardrails                    │
│  └── PDF Report Generator (ReportLab)  │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│  External Services         │
│  • Quasar Marketplace LLM  │
│  • NHTSA vPIC API (VIN)    │
└────────────────────────────┘
```

---

## 📁 Project Structure

```
C:\nexusiqapp\
├── backend/
│   ├── .env                          # API keys & configuration
│   ├── requirements.txt              # Python dependencies
│   └── app/
│       ├── main.py                   # FastAPI app entry point
│       ├── api/
│       │   └── routes.py             # All API endpoints
│       ├── models/
│       │   └── schemas.py            # Pydantic data models
│       ├── agents/
│       │   └── fraud_agent.py        # 5-step verification pipeline
│       ├── services/
│       │   ├── coforge_llm.py        # Quasar LLM client (x-api-key auth)
│       │   ├── quasar_gateway.py     # Gateway wrapper
│       │   ├── pdf_extraction.py     # PDF parsing + LLM extraction
│       │   ├── session_manager.py    # In-memory session store (24h TTL)
│       │   └── report_generator.py   # ReportLab PDF generation
│       ├── tools/
│       │   └── verification.py       # Steps 2–5 implementation
│       └── utils/
│           └── guardrails.py         # PII masking + compliance
├── frontend/
│   └── src/app/
│       └── index.html                # Chat UI (single-page)
├── doc/
│   └── backlog-doc-fraud-detection-v2.md  # Full product backlog
├── .github/
│   └── copilot-instructions.md       # Copilot coding context
├── venv/                             # Python virtual environment
├── .env                              # Root env (shared config)
├── .gitignore
└── README.md                         # ← You are here
```

---

## ⚙️ Prerequisites

- **Python 3.11+** installed
- **Quasar Marketplace API Key** (from https://quasarmarket.coforge.com)
- A modern web browser (Chrome, Edge, Firefox)

---

## 🚀 How to Start / Restart the Application

### First-Time Setup (one-time only)

```powershell
# 1. Navigate to the project
cd C:\nexusiqapp

# 2. Activate virtual environment
.\venv\Scripts\activate

# 3. Install dependencies
cd backend
pip install -r requirements.txt

# 4. Configure .env (edit with your API key)
notepad .env
```

### Start the Backend Server

```powershell
cd C:\nexusiqapp\backend
C:\nexusiqapp\venv\Scripts\uvicorn app.main:app --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Open the Frontend

Open this file in your browser:
```
C:\nexusiqapp\frontend\src\app\index.html
```

Or use VS Code Live Server on port 5500.

### Verify It's Working

```powershell
curl http://localhost:8000/health
```
Expected: `{"status":"ok","service":"NexusIQ Fraud Detection"}`

---

## 🔄 How to Restart the Application

### Option 1: If the server is still running in terminal

Press `Ctrl+C` to stop, then restart:
```powershell
cd C:\nexusiqapp\backend
C:\nexusiqapp\venv\Scripts\uvicorn app.main:app --port 8000 --reload
```

### Option 2: If you closed the terminal / new session

```powershell
# Open PowerShell and run:
cd C:\nexusiqapp\backend
C:\nexusiqapp\venv\Scripts\uvicorn app.main:app --port 8000 --reload
```

### Option 3: Run as background process

```powershell
cd C:\nexusiqapp\backend
Start-Process -FilePath "C:\nexusiqapp\venv\Scripts\uvicorn.exe" -ArgumentList "app.main:app", "--port", "8000", "--reload" -WindowStyle Normal
```

To stop the background process:
```powershell
Get-Process -Name uvicorn | Stop-Process
```

### Option 4: Quick one-liner restart

```powershell
Get-Process -Name uvicorn -ErrorAction SilentlyContinue | Stop-Process; cd C:\nexusiqapp\backend; Start-Process "C:\nexusiqapp\venv\Scripts\uvicorn.exe" -ArgumentList "app.main:app","--port","8000","--reload"
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/session` | Create new analysis session |
| `POST` | `/api/upload/{session_id}` | Upload PDF invoice |
| `POST` | `/api/extract/{session_id}` | Extract invoice data with AI |
| `POST` | `/api/verify/{session_id}` | Run fraud verification (streaming NDJSON) |
| `GET` | `/api/report/{session_id}` | Get fraud report JSON |
| `GET` | `/api/report/{session_id}/pdf` | Download PDF report |
| `GET` | `/api/chat/{session_id}` | Get chat history |
| `POST` | `/api/chat/{session_id}/message` | Ask follow-up questions |

---

## 🛡️ Security & Guardrails

- **PII Masking**: SSN, email, credit card, DOB, phone numbers automatically redacted from all AI outputs
- **Blocked Phrases**: "claim denied" and similar phrases trigger disclaimers
- **No disk storage**: Uploaded files stored in-memory only, auto-purged after 24h
- **No PII in logs**: Only metadata (filename, size) is logged

---

## 🔧 Environment Variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_URL` | Yes | — | Quasar LLM endpoint base URL |
| `MODEL_NAME` | Yes | `gpt-4o-mini` | LLM model to use |
| `API_KEY` | Yes | — | Quasar Marketplace API key |
| `TAVILY_API_KEY` | No | — | Web search for vendor verification |
| `MAX_FILE_SIZE_MB` | No | `25` | Max upload size in MB |
| `FRAUD_PRICE_DEVIATION_THRESHOLD` | No | `50` | Price flag threshold (%) |

---

## 🧪 Testing

```powershell
# Run from backend directory
cd C:\nexusiqapp\backend
C:\nexusiqapp\venv\Scripts\python -m pytest tests/ -v
```

---

## 📦 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Uvicorn |
| LLM | LangChain + Quasar Marketplace (gpt-4o-mini) |
| PDF Parsing | pdfplumber |
| PDF Reports | ReportLab |
| Data Models | Pydantic v2 |
| HTTP Client | httpx (async) |
| Frontend | Vanilla JS + Tailwind CSS |
| VIN Decode | NHTSA vPIC API |

---

## 👥 Team

Built by Coforge NexusIQ team using GitHub Copilot.

---

## 📝 License

Internal use only — Coforge Limited.
