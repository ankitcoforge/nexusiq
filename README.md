# NexusIQ — Document Fraud Detection

NexusIQ is an AI-powered fraud detection application that analyzes insurance invoices and repair estimates for fraudulent patterns. It uses LLM-powered reasoning, real-time internet search, and multi-step verification to flag suspicious transactions with explainable results.

![NexusIQ Screenshot](test-angular-screenshot.png)

---

## Features

- **PDF Invoice Upload & Extraction** — Upload invoice PDFs and extract structured data (vendor, customer, vehicle, line items) using LLM-powered parsing
- **5-Step Fraud Verification Pipeline**
  1. **Data Extraction Summary** — Validates extracted fields with internet-based vendor lookup
  2. **Arithmetic & Tax Validation** — Cross-checks line item totals, tax calculations, and grand total
  3. **Vendor Legitimacy** — Searches the internet for vendor reviews, complaints, and legitimacy signals
  4. **Market Price Benchmarking** — Compares line item prices against real-time market data
  5. **VIN Validation** — Decodes Vehicle Identification Numbers via NHTSA API
- **AI-Powered Verdicts** — LLM generates final fraud verdict with reasoning (Approve / Approve with Notation / Escalate to SIU)
- **Real-Time Streaming** — Step-by-step verification results streamed to the frontend
- **Chat Assistant** — Interactive fraud investigation chat with session memory
- **PDF Report Generation** — Downloadable fraud analysis reports
- **PII Guardrails** — Automatic redaction of SSN, email, credit card, and DOB from outputs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Angular 14, Angular Material, Bootstrap 5 |
| **Backend** | Python 3.x, FastAPI, Uvicorn |
| **LLM Framework** | LangChain 1.2.x |
| **LLM Provider** | Quasar Marketplace (Coforge) — `gpt-4o-mini` |
| **Web Search** | Serper API (Google Search) |
| **PDF Parsing** | pdfplumber |
| **VIN Decoding** | NHTSA vPIC API |
| **Auth** | `x-api-key` header |

---

## Project Structure

```
nexusiqapp/
├── backend/
│   ├── .env                          # API keys & config (not committed)
│   ├── combined.pem                  # SSL certificate bundle
│   ├── requirements.txt              # Python dependencies
│   └── app/
│       ├── main.py                   # FastAPI app entry point
│       ├── api/
│       │   └── routes.py             # API endpoint definitions
│       ├── agents/
│       │   └── fraud_agent.py        # 5-step verification pipeline
│       ├── models/
│       │   └── schemas.py            # Pydantic data models
│       ├── services/
│       │   ├── coforge_llm.py        # Quasar LLM client (sync/async)
│       │   ├── langchain_agent.py    # LangChain agent with tools
│       │   ├── langchain_tools.py    # Serper search, price search, VIN lookup
│       │   ├── pdf_extraction.py     # PDF parsing & LLM extraction
│       │   ├── report_generator.py   # PDF report generation
│       │   └── session_manager.py    # Session state management
│       ├── tools/
│       │   └── verification.py       # Fraud verification logic
│       └── utils/
│           └── guardrails.py         # PII masking & content safety
├── frontend/
│   └── nexus-ui/                     # Angular 14 application
│       └── src/app/
│           ├── chat/                 # Chat interface component
│           ├── header/               # Navigation header
│           ├── input/                # User input component
│           └── api.service.ts        # Backend API service
├── test_playwright.py                # Playwright E2E tests
├── test_full_pipeline.py             # Full pipeline integration test
└── requirements.txt                  # Root-level dependencies
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | App health check |
| `GET` | `/api/health` | API health check |
| `POST` | `/api/session` | Create new analysis session |
| `POST` | `/api/upload/{session_id}` | Upload invoice PDF |
| `POST` | `/api/extract/{session_id}` | Extract data from uploaded PDF |
| `POST` | `/api/verify/{session_id}` | Run fraud verification pipeline (streaming) |
| `GET` | `/api/report/{session_id}` | Get fraud report (JSON) |
| `GET` | `/api/report/{session_id}/pdf` | Download fraud report (PDF) |
| `GET` | `/api/chat/{session_id}` | Get chat history |
| `POST` | `/api/chat/{session_id}/message` | Send message to AI assistant |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 16+ and npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/ankitcoforge/nexusiq.git
cd nexusiq
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Configure Environment

Create `backend/.env` with the following:

```env
# LLM Configuration
API_URL=https://quasarmarket.coforge.com/qag/llmrouter-api/v2/chat/completions
MODEL_NAME=gpt-4o-mini
API_KEY=<your-quasar-api-key>

# LangChain Configuration
LANGCHAIN_TRACING_V2=false
LANGCHAIN_PROJECT=nexusiqapp

# App Configuration
APP_ENV=development
APP_DEBUG=true
MAX_FILE_SIZE_MB=25
FRAUD_PRICE_DEVIATION_THRESHOLD=50
```

### 4. Frontend Setup

```bash
cd frontend/nexus-ui
npm install
```

### 5. Run the Application

**Start Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Start Frontend:**
```bash
cd frontend/nexus-ui
npm start
```

Open **http://localhost:4200** in your browser.

---

## Running Tests

### Playwright E2E Tests

```bash
python test_playwright.py
```

Runs 6 automated tests:
- Backend API health check
- FastAPI docs accessibility
- Angular frontend rendering
- API session creation
- UI element validation
- Screenshot capture

### Full Pipeline Test

```bash
python test_full_pipeline.py
```

Runs the complete 5-step fraud verification pipeline against a sample invoice with real internet searches.

---

## Fraud Verdict Types

| Verdict | Description |
|---------|-------------|
| **Approve for Processing** | No significant fraud indicators found |
| **Approve with Notation** | Minor warnings detected, supervisor review recommended |
| **Escalate to SIU** | Critical fraud flags found, requires Special Investigations Unit review |

---

## Key Data Models

- **InvoiceData** — Complete invoice with vendor, customer, vehicle, line items, and totals
- **FraudFlag** — Individual fraud check result with severity (CRITICAL / WARNING / INFO)
- **FraudReport** — Final analysis report with all verification results and verdict
- **VerificationStepResult** — Per-step outcome with status, flags, thought process, and duration

---

## License

Internal project — Coforge Limited.
