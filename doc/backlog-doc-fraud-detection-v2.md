# NexusIQ — Document Fraud Detection: Product Backlog v2

> **Product:** NexusIQ — Document Fraud Detection Module  
> **Platform:** Coforge Quasar + LangChain Agentic AI + MCP Architecture  
> **Timeline:** May–June 2026 (~2 months, 4 sprints × 2 weeks)  
> **Capacity:** 4 resources × ~10 hrs each = ~40 hrs  
> **Created:** April 28, 2026  
> **Revised:** April 29, 2026 — v2 (detailed implementation specs added)

---

## How to Read This Document

Each user story includes:
1. **Acceptance Criteria** — what the feature must do (testable conditions)
2. **Technical Specification** — exact files, functions, data models, API contracts, and configuration required
3. **Implementation Checklist** — step-by-step tasks a developer must complete
4. **API Contract** — request/response JSON schemas for every endpoint
5. **Data Model Reference** — Pydantic models with exact field definitions
6. **Error Handling Matrix** — every error condition and expected behavior
7. **Definition of Done** — what must be true before the story is marked complete

---

## Architecture Overview

### System Architecture Diagram (Textual)

```
┌─────────────────────────────────┐
│  Frontend (index.html)          │
│  Vanilla JS + Tailwind CSS      │
│  http://localhost:5500          │
│  ┌───────────┐ ┌──────────┐    │
│  │ Chat UI   │ │ File     │    │
│  │ Component │ │ Upload   │    │
│  └─────┬─────┘ └────┬─────┘    │
└────────┼─────────────┼──────────┘
         │  HTTP/NDJSON │
         ▼             ▼
┌─────────────────────────────────┐
│  FastAPI Backend (port 8000)    │
│  backend/app/main.py            │
│  ┌──────────────────────────┐   │
│  │  API Routes (routes.py)  │   │
│  │  /api/session  POST      │   │
│  │  /api/upload   POST      │   │
│  │  /api/extract  POST      │   │
│  │  /api/verify   POST      │   │
│  │  /api/report   GET       │   │
│  │  /api/report/pdf GET     │   │
│  │  /api/chat     GET       │   │
│  └──────────┬───────────────┘   │
│             ▼                   │
│  ┌──────────────────────────┐   │
│  │  Session Manager         │   │
│  │  (in-memory, 24h TTL)    │   │
│  └──────────────────────────┘   │
│             ▼                   │
│  ┌──────────────────────────┐   │
│  │  PDF Extraction Service  │   │
│  │  pdfplumber + LLM parse  │   │
│  └──────────────────────────┘   │
│             ▼                   │
│  ┌──────────────────────────┐   │
│  │  Fraud Agent Pipeline    │   │
│  │  5 sequential steps      │   │
│  │  NDJSON streaming output │   │
│  └──────────┬───────────────┘   │
│             ▼                   │
│  ┌──────────────────────────┐   │
│  │  Quasar LLM Gateway     │   │
│  │  CoforgeAIGardenLLM →    │   │
│  │  httpx fallback          │   │
│  └──────────┬───────────────┘   │
│             ▼                   │
│  ┌──────────────────────────┐   │
│  │  Report Generator        │   │
│  │  (ReportLab → PDF)       │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  External Services              │
│  • Quasar LLM Router API       │
│  • NHTSA vPIC API (VIN decode) │
│  • Tavily Search API (optional)│
└─────────────────────────────────┘
```

### File Structure Reference

```
backend/
├── requirements.txt              # Python dependencies
├── .env                          # ← MUST CREATE (see US-401)
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, CORS, router mount
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py             # All API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # All Pydantic models
│   ├── agents/
│   │   ├── __init__.py
│   │   └── fraud_agent.py        # 5-step verification pipeline
│   ├── services/
│   │   ├── __init__.py
│   │   ├── coforge_llm.py        # CoforgeAIGardenLLM (LangChain LLM wrapper)
│   │   ├── quasar_gateway.py     # Quasar gateway (routes LLM calls)
│   │   ├── pdf_extraction.py     # PDF text extraction + LLM parsing
│   │   ├── session_manager.py    # In-memory session store
│   │   └── report_generator.py   # ReportLab PDF generation
│   ├── tools/
│   │   ├── __init__.py
│   │   └── verification.py       # Steps 2-5 implementation + LLM prompts
│   └── utils/
│       ├── __init__.py
│       └── guardrails.py         # PII masking + compliance checks
├── tests/
│   ├── __init__.py
│   ├── generate_sample_invoice.py
│   ├── test_fraud_detection.py
│   └── playwright/
│       └── health.spec.js
└── sample_invoices/              # Test PDF files

frontend/
├── src/
│   └── app/
│       └── index.html            # Single-page chat UI (all JS inline)
├── public/
├── components/                   # Empty — future modular components
└── lib/                          # Empty — future shared utilities
```

### Key Dependencies (requirements.txt)

| Package | Version | Purpose |
|---------|---------|--------|
| `fastapi` | 0.115.0 | Web framework |
| `uvicorn[standard]` | 0.30.0 | ASGI server |
| `python-multipart` | 0.0.9 | File upload parsing |
| `pdfplumber` | 0.11.0 | PDF text extraction |
| `langchain` | 0.3.0 | LLM orchestration framework |
| `langchain-openai` | 0.2.0 | OpenAI-compatible LLM bindings |
| `langchain-community` | 0.3.0 | Community integrations |
| `pydantic` | 2.9.0 | Data validation & schemas |
| `httpx` | 0.27.0 | Async HTTP client |
| `python-dotenv` | 1.0.1 | .env file loading |
| `reportlab` | 4.2.0 | PDF report generation |
| `websockets` | 12.0 | WebSocket support |
| `pytest` | 8.3.0 | Testing framework |
| `pytest-asyncio` | 0.24.0 | Async test support |

### Environment Variables (.env)

| Variable | Required | Default | Example | Used By |
|----------|----------|---------|---------|--------|
| `API_URL` | **Yes** | `https://quasarmarket.coforge.com/qag/llmrouter-api/v3/chat/completions` | Same | `quasar_gateway.py`, `coforge_llm.py` |
| `MODEL_NAME` | **Yes** | `gpt-5-2` | `gpt-5-2` | `quasar_gateway.py`, `coforge_llm.py` |
| `API_KEY` | **Yes** | `""` | `sk-xxxx` | `quasar_gateway.py`, `coforge_llm.py` |
| `TAVILY_API_KEY` | No | `""` | `tvly-xxxx` | `verification.py` (vendor search) |
| `MAX_FILE_SIZE_MB` | No | `25` | `25` | `routes.py` |
| `FRAUD_PRICE_DEVIATION_THRESHOLD` | No | `50` | `50` | `verification.py` (price check) |

### How to Run

```bash
# 1. Create virtual environment
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file (see Environment Variables table above)
copy .env.example .env
# Edit .env with your API_URL, MODEL_NAME, API_KEY

# 4. Start backend
uvicorn app.main:app --reload --port 8000

# 5. Open frontend
# Open frontend/src/app/index.html in browser (or serve via Live Server on port 5500)
# Frontend connects to http://localhost:8000/api
```

---

## Data Models Reference

> All models defined in `backend/app/models/schemas.py`. Developers MUST use these exact types.

### Enums

```python
class ConfidenceLevel(str, Enum):
    HIGH = "high"       # >= 0.8
    MEDIUM = "medium"   # 0.5–0.79
    LOW = "low"         # < 0.5

class FraudFlagSeverity(str, Enum):
    CRITICAL = "critical"   # Auto-escalates to SIU
    WARNING = "warning"     # Approve with notation
    INFO = "info"           # Informational only

class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    UNAVAILABLE = "unavailable"
    MANUAL_REVIEW = "manual_review"

class VerdictType(str, Enum):
    APPROVE = "Approve for Processing"
    APPROVE_WITH_NOTATION = "Approve with Notation"
    ESCALATE_SIU = "Escalate to SIU"
```

### Core Models

| Model | File | Purpose | Key Fields |
|-------|------|---------|------------|
| `ExtractedField` | schemas.py | Field + confidence score | `value: str`, `confidence: float (0.0–1.0)` |
| `VendorInfo` | schemas.py | Vendor details | `name`, `address`, `phone`, `website` (all `ExtractedField`) |
| `CustomerInfo` | schemas.py | Customer details | `name`, `address`, `phone` (all `ExtractedField`) |
| `VehicleInfo` | schemas.py | Vehicle details | `make`, `model`, `year`, `vin`, `mileage` (all `ExtractedField`) |
| `LineItem` | schemas.py | Invoice line item | `description`, `part_number?`, `quantity`, `unit_price`, `total`, `is_taxable`, `confidence` |
| `InvoiceData` | schemas.py | Full extracted invoice | All above + `line_items[]`, `subtotal`, `tax_rate`, `tax_amount`, `total`, `raw_text` |
| `FraudFlag` | schemas.py | Single fraud flag | `check_name`, `severity`, `message`, `details` |
| `VerificationStepResult` | schemas.py | One step's output | `step_number`, `step_name`, `status`, `summary`, `details`, `thought_process`, `flags[]`, `duration_seconds` |
| `ArithmeticCheckResult` | schemas.py | Step 2 result (extends VerificationStepResult) | `line_item_checks[]`, `computed_subtotal`, `computed_tax`, `computed_total`, `invoice_total` |
| `VendorCheckResult` | schemas.py | Step 3 result | `vendor_found`, `official_phone`, `official_address`, `search_sources[]` |
| `PriceCheckResult` | schemas.py | Step 4 result | `price_comparisons[]` |
| `VINCheckResult` | schemas.py | Step 5 result | `vin_valid`, `decoded_year`, `decoded_make`, `decoded_model` |
| `FraudReport` | schemas.py | Final aggregated report | `session_id`, `document_name`, `analysis_date`, `invoice_data`, `verification_results[]`, `total_flags`, `critical_flags`, `verdict`, `verdict_reasoning`, `recommendation` |
| `ChatMessage` | schemas.py | Chat history entry | `role`, `content`, `message_type`, `data?`, `timestamp` |
| `UploadResponse` | schemas.py | Upload API response | `session_id`, `file_name`, `message`, `status` |

---

## Epic 1: Document Ingestion & Data Extraction

**Epic ID:** NEXIQ-E1  
**Description:** Enable users to upload insurance-related documents (invoices, repair estimates, medical bills) and automatically extract structured data using AI-powered OCR and LLM parsing.  
**Business Value:** Eliminates manual data entry for claims adjusters, reduces processing time by ~70%.

### Feature 1.1: Document Upload Interface

**Feature ID:** NEXIQ-F1.1  
**Description:** Chat-based UI allowing users to upload PDF documents for fraud analysis with a conversational interface.

---

#### NEXIQ-US-101: Chat UI Landing Page

**Story:** As a claims adjuster, I want a chat interface that greets me and prompts me to upload an invoice PDF so that I can quickly start fraud analysis without navigating complex menus.

**Acceptance Criteria:**

| # | Given | When | Then | Testable? |
|---|-------|------|------|----------|
| AC1 | User opens the app | Page loads | Welcome message displays: "Upload an invoice PDF for fraud analysis" | Yes — check DOM |
| AC2 | Chat UI is loaded | User views the interface | Attachment button (📎) and text input field visible | Yes — check DOM |
| AC3 | Chat UI is loaded | User views the interface | A collapsible "Thought Process" section is available per verification step | Yes — UI test |
| AC4 | Page loads | Timer measured | Load < 2 seconds P95 | Yes — Lighthouse |
| AC5 | Session created | API called | Quasar RBAC role validated (adjuster, supervisor) | Yes — API test |

**Technical Specification:**

| Aspect | Detail |
|--------|--------|
| **File** | `frontend/src/app/index.html` |
| **Framework** | Vanilla JS + Tailwind CSS (CDN: `https://cdn.tailwindcss.com`) |
| **Session Init** | On page load, call `POST /api/session` → receive `session_id` + welcome message |
| **State Machine** | `currentState`: `init` → `uploaded` → `extracting` → `extracted` → `verifying` → `complete` |
| **Layout** | Header (logo + status badge + export button) → Chat container (scrollable) → Input area (upload button + hint text + analyze button) |
| **CSS** | `.chat-container { height: calc(100vh - 200px); }` — full viewport chat |
| **Status Badge** | `#status-badge` — changes color/text per state |
| **Thought Process** | `.thought-content` — CSS transition `max-height: 0 → 2000px` on `.open` class toggle |

**Implementation Checklist:**

- [ ] `index.html` — Create the page structure: `<header>`, `<div id="chat-messages">`, input area with file input
- [ ] `initSession()` — On page load, `POST /api/session`, store `sessionId`, render welcome message
- [ ] `addMessage(role, content, type)` — Render chat bubble (blue for user, gray for assistant, red border for error)
- [ ] `setStatus(text, classes)` — Update `#status-badge` text and Tailwind classes
- [ ] `toggleThought(id)` — Toggle `.open` on `#thought-{stepNumber}` div
- [ ] Status badge states: Ready (gray) → Uploading (yellow) → Extracting (blue) → Verifying (purple) → Complete (green) → Error (red)
- [ ] Responsive: `max-w-4xl mx-auto p-4` — works on desktop and tablet

**API Contract:**

```
POST /api/session
Request: (empty body)
Response 200:
{
  "session_id": "uuid-string",
  "message": "Upload an invoice PDF for fraud analysis",
  "chat_history": [
    {
      "role": "assistant",
      "content": "Welcome to NexusIQ Document Fraud Detection! 👋\n\nUpload an invoice PDF to begin fraud analysis.",
      "message_type": "text",
      "data": null,
      "timestamp": "2026-05-01T10:00:00"
    }
  ]
}
```

**Error Handling:**

| Condition | Expected Behavior |
|-----------|------------------|
| Backend not running | Display: "⚠️ Could not connect to backend. Make sure the server is running on port 8000." |
| Network timeout | Retry once, then show error message |

**Definition of Done:**
- [ ] Unit test: page loads and welcome message appears
- [ ] Playwright test: `health.spec.js` passes
- [ ] Responsive on desktop (1440px) and tablet (768px)
- [ ] Status badge shows "Ready" on load
- [ ] Session ID is stored in JS variable after init

**Story Points:** 3  
**Priority:** Must Have (H1) — Sprint 1

---

#### NEXIQ-US-102: PDF File Upload & Validation

**Story:** As a claims adjuster, I want to upload a PDF document via the chat interface so that the system can process it for fraud analysis.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | User clicks attachment button | Selects a PDF file | File name displayed in chat as user message: "📎 Uploaded: filename.pdf" |
| AC2 | User uploads a file | File is not PDF | Error: "Only PDF files are supported" (HTTP 400) |
| AC3 | User uploads a PDF | File > 25MB | Error: "File size must be under 25MB" (HTTP 400) |
| AC4 | User uploads a PDF | File is 0 bytes | Error: "File is empty" (HTTP 400) |
| AC5 | User uploads a valid PDF | Upload completes | Assistant message: "✅ Received **filename.pdf** (X.X KB). Click Analyze to start fraud detection." |
| AC6 | Upload completes | State changes | `currentState = 'uploaded'`, Analyze button becomes visible |
| AC7 | File uploaded | Audit checked | Quasar audit trail logs metadata (filename, size, timestamp — NOT file content) |

**Technical Specification:**

**Frontend (index.html):**

| Function | Behavior |
|----------|----------|
| `handleFileUpload(event)` | 1. Validate `.pdf` extension client-side. 2. Validate size < 25MB client-side. 3. Create `FormData`, append file. 4. `POST /api/upload/{sessionId}`. 5. On success: show message, reveal Analyze button, set state. 6. On error: show error message from `response.detail`. 7. Reset file input: `event.target.value = ''` |
| Client-side validation | Extension check: `file.name.toLowerCase().endsWith('.pdf')`. Size check: `file.size > 25 * 1024 * 1024` |

**Backend (routes.py → `upload_document`):**

| Aspect | Detail |
|--------|--------|
| **Endpoint** | `POST /api/upload/{session_id}` |
| **Input** | `UploadFile` (multipart form data, field name: `file`) |
| **Validations** | 1. Session exists (404 if not). 2. File extension is `.pdf` (400 if not). 3. File size ≤ `MAX_FILE_SIZE` env var (default 25MB) (400 if over). 4. File not empty (400 if empty). |
| **Storage** | `session.file_bytes = file_bytes` (in-memory, NOT written to disk) |
| **Session Update** | `session.file_name = filename`, `session.status = "uploaded"` |
| **Chat Messages Added** | User: "📎 Uploaded: filename.pdf", Assistant: "✅ Received..." |
| **Response Model** | `UploadResponse(session_id, file_name, message, status="uploaded")` |

**API Contract:**

```
POST /api/upload/{session_id}
Content-Type: multipart/form-data
Body: file=<binary PDF>

Response 200:
{
  "session_id": "uuid",
  "file_name": "invoice.pdf",
  "message": "File uploaded successfully. Size: 125.3 KB",
  "status": "uploaded"
}

Response 400 (not PDF):
{ "detail": "Only PDF files are supported" }

Response 400 (too large):
{ "detail": "File size must be under 25MB" }

Response 400 (empty):
{ "detail": "File is empty" }

Response 404 (bad session):
{ "detail": "Session not found" }
```

**Error Handling Matrix:**

| Error | HTTP Code | Client Message | Server Log |
|-------|-----------|----------------|------------|
| Not PDF | 400 | "Only PDF files are supported" | None (client-side first) |
| > 25MB | 400 | "File size must be under 25MB" | None (client-side first) |
| Empty file | 400 | "File is empty" | None |
| Invalid session | 404 | "Session not found" | Warning log |
| Network error | N/A | "Upload failed: {error}" | N/A |

**Implementation Checklist:**

- [ ] Frontend: `handleFileUpload()` — client-side validation + FormData POST
- [ ] Frontend: Reset file input after upload (`event.target.value = ''`)
- [ ] Frontend: Show/hide Analyze button based on state
- [ ] Backend: `upload_document()` in `routes.py` — validate and store in session
- [ ] Backend: Session stores `file_bytes` in memory (no disk write)
- [ ] Backend: Add chat messages to session history
- [ ] Test: Upload valid PDF → success response
- [ ] Test: Upload .txt file → 400 error
- [ ] Test: Upload 30MB PDF → 400 error
- [ ] Test: Upload to non-existent session → 404 error

**Security Notes:**
- File bytes stored in-memory only, auto-purged with session (24h TTL)
- No PII stored beyond session retention window
- File content is NOT logged — only metadata (filename, size)

**Definition of Done:**
- [ ] All 4 validation cases tested
- [ ] File stored in session memory only (verify no disk writes)
- [ ] Analyze button appears only after successful upload
- [ ] Chat history shows upload messages

**Story Points:** 3  
**Priority:** Must Have (H1) — Sprint 1

---

### Feature 1.2: AI-Powered Document Parsing

**Feature ID:** NEXIQ-F1.2  
**Description:** Extract structured data fields from uploaded documents using LLM-based parsing — vendor info, customer info, vehicle details, line items, amounts, tax, totals.

---

#### NEXIQ-US-103: Invoice Data Extraction

**Story:** As a claims adjuster, I want the system to automatically extract structured invoice fields (vendor, customer, vehicle, line items, amounts) from an uploaded PDF so that I don't have to manually key in data.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Valid PDF uploaded | Extraction completes | Vendor Name, Phone, Invoice Number, Invoice Date, Customer Name, Address, Phone displayed |
| AC2 | Vehicle repair invoice | Extraction completes | Vehicle Make/Model/Year, VIN, Mileage extracted |
| AC3 | Invoice with line items | Extraction completes | Each line shows: Description, Part Number (if present), Quantity, Unit Price, Total |
| AC4 | Extraction completes | Results displayed | Structured card/table in chat with all extracted data |
| AC5 | Single-page invoice | Timer measured | Extraction < 10 seconds P95 |
| AC6 | LLM unavailable | Extraction attempted | Falls back to text-only parsing (no LLM), still returns partial data |
| AC7 | LLM available | Extraction runs | Call routed through Quasar model gateway with prompt versioning |

**Technical Specification:**

**Backend Pipeline (pdf_extraction.py):**

```
PDF bytes → pdfplumber.open() → extract_text() + extract_tables()
         → concatenate all text
         → (if LLM available) send to Quasar LLM with EXTRACTION_PROMPT
         → parse JSON response → InvoiceData model
         → (if LLM unavailable) parse_text_fallback() → InvoiceData with low confidence
```

| Function | File | Behavior |
|----------|------|----------|
| `extract_text_from_pdf(file_bytes)` | `pdf_extraction.py` | Uses `pdfplumber.open(BytesIO(file_bytes))` → extracts text per page + tables → joins with newlines |
| `extract_invoice_data(file_bytes, use_llm)` | `pdf_extraction.py` | 1. Extract text. 2. If `use_llm=True`: send `EXTRACTION_PROMPT` with text to `gateway.invoke()`. 3. Parse response JSON into `InvoiceData`. 4. If LLM fails: fall back to `use_llm=False`. 5. If `use_llm=False`: use regex-based text parsing with low confidence scores. |
| `parse_extraction_response(response_text)` | `pdf_extraction.py` | Strip markdown code fences (` ```json ` wrapper). Parse JSON. Map to `InvoiceData` Pydantic model. |

**LLM Prompt (EXTRACTION_PROMPT):**
- Located in `pdf_extraction.py`
- Asks LLM to return a strict JSON schema matching `InvoiceData`
- Confidence scoring rules embedded in prompt:
  - `1.0` = field clearly present and readable
  - `0.5–0.8` = partially visible or inferred
  - `0.0–0.5` = guessed or not found
  - Missing fields = `""` with `confidence: 0.0`

**API Contract:**

```
POST /api/extract/{session_id}
Request: (empty body — uses session's stored file_bytes)

Response 200:
{
  "session_id": "uuid",
  "invoice_data": {
    "invoice_number": {"value": "INV-2026-001", "confidence": 0.95},
    "invoice_date": {"value": "2026-04-15", "confidence": 0.90},
    "vendor": {
      "name": {"value": "Mike's Auto Repair", "confidence": 0.95},
      "address": {"value": "123 Main St, Dallas TX", "confidence": 0.85},
      "phone": {"value": "555-123-4567", "confidence": 0.80},
      "website": {"value": "", "confidence": 0.0}
    },
    "customer": {
      "name": {"value": "John Smith", "confidence": 0.90},
      "address": {"value": "456 Oak Ave", "confidence": 0.70},
      "phone": {"value": "555-987-6543", "confidence": 0.75}
    },
    "vehicle": {
      "make": {"value": "Toyota", "confidence": 0.95},
      "model": {"value": "Camry", "confidence": 0.95},
      "year": {"value": "2023", "confidence": 0.95},
      "vin": {"value": "1HGCM82633A123456", "confidence": 0.90},
      "mileage": {"value": "45000", "confidence": 0.80}
    },
    "line_items": [
      {
        "description": "Front Bumper Replacement",
        "part_number": "TB-4421",
        "quantity": 1.0,
        "unit_price": 450.00,
        "total": 450.00,
        "is_taxable": true,
        "confidence": 0.90
      }
    ],
    "subtotal": 1250.00,
    "tax_rate": 8.25,
    "tax_amount": 103.13,
    "total": 1353.13,
    "raw_text": "..."
  },
  "message": "Extraction complete",
  "llm_used": true
}

Response 400 (no file): { "detail": "No file uploaded" }
Response 404 (bad session): { "detail": "Session not found" }
Response 500 (extraction failed): { "detail": "Extraction failed: {error}" }
```

**Frontend Rendering (index.html → `renderExtraction()`):**
- Renders a blue card (`bg-blue-50 border border-blue-200 rounded-lg`)
- Grid of extracted fields with confidence badges:
  - `confidence < 0.5` → Red badge: "Needs Review"
  - `confidence < 0.8` → Amber badge: "Low Confidence"
  - `confidence >= 0.8` → No badge (high confidence)
- Line items table: Item | Qty | Price | Total
- Total displayed at bottom

**Error Handling Matrix:**

| Error | HTTP Code | Behavior |
|-------|-----------|----------|
| No file uploaded | 400 | "No file uploaded" |
| Invalid session | 404 | "Session not found" |
| LLM extraction fails | N/A | Fall back to text-only extraction (logged as warning) |
| Text-only extraction fails | 500 | "Extraction failed: {error}" |
| PDF has no readable text | 200 | Returns InvoiceData with all empty fields, low confidence |

**Implementation Checklist:**

- [ ] `extract_text_from_pdf()` — pdfplumber text + table extraction
- [ ] `EXTRACTION_PROMPT` — JSON schema prompt with confidence scoring rules
- [ ] `extract_invoice_data()` — LLM path + text-only fallback path
- [ ] `parse_extraction_response()` — JSON cleaning + Pydantic parsing
- [ ] Backend route: `POST /api/extract/{session_id}` with error handling
- [ ] Frontend: `renderExtraction(data, llmUsed)` — card with confidence badges
- [ ] Frontend: `field(label, obj)` helper — renders field + confidence badge
- [ ] Test: Extract from sample auto repair invoice → all fields populated
- [ ] Test: Extract from medical bill → handles different layout
- [ ] Test: LLM unavailable → text-only fallback works

**Definition of Done:**
- [ ] Tested with 5+ sample invoices (auto repair, medical, general)
- [ ] ≥90% field extraction accuracy on test set when LLM is available
- [ ] Text-only fallback produces partial results (not crash)
- [ ] Confidence badges render correctly for all three levels
- [ ] Extraction time < 10 seconds P95 for single-page invoice

**Story Points:** 8  
**Priority:** Must Have (H1) — Sprint 1

---

#### NEXIQ-US-104: Extraction Confidence Scoring

**Story:** As a claims adjuster, I want each extracted field to show a confidence indicator so that I can quickly identify fields that may need manual review.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Extraction completes | Field confidence >= 80% | No badge (high confidence, clean display) |
| AC2 | Extraction completes | Field confidence < 80% | Highlighted amber with "Low Confidence" tag |
| AC3 | Extraction completes | Field confidence < 50% | Highlighted red with "Needs Review" tag |
| AC4 | Low-confidence field | User clicks it | They can manually correct the value |

**Technical Specification:**

| Aspect | Detail |
|--------|--------|
| **Model** | `ExtractedField.confidence_level` property: `>= 0.8 → HIGH`, `>= 0.5 → MEDIUM`, `< 0.5 → LOW` |
| **Frontend function** | `field(label, obj)` in `index.html` — generates HTML with badge |
| **Badge HTML** | `conf < 0.5`: `<span class="bg-red-100 text-red-700">Needs Review</span>` |
| | `conf < 0.8`: `<span class="bg-amber-100 text-amber-700">Low Confidence</span>` |
| **Editable fields** | NOT YET IMPLEMENTED — AC4 requires adding `contenteditable` or input fields in extraction card |

**Implementation Checklist:**

- [ ] Confidence badges already render (in `field()` helper) — verify correct thresholds
- [ ] Add editable field support: on click, convert field value to `<input>` with save button
- [ ] Save edited values back to `session.invoice_data` via new API endpoint or local state
- [ ] Step 1 of pipeline flags low-confidence fields in thought process

**Definition of Done:**
- [ ] Confidence badges display correctly for HIGH/MEDIUM/LOW
- [ ] Manual field editing works (click → edit → save)
- [ ] Edited values persist through verification pipeline

**Story Points:** 3  
**Priority:** Should Have (H1) — Sprint 2

---

## Epic 2: Multi-Step Agentic Fraud Verification

**Epic ID:** NEXIQ-E2  
**Description:** Implement an agentic AI pipeline that performs automated verification checks on extracted data — arithmetic validation, vendor legitimacy, price benchmarking, VIN verification. Each step executes autonomously with tool use, reasoning transparency, and fraud flag generation.  
**Business Value:** Automates 80% of manual SIU initial screening, reducing fraud investigation time from hours to minutes.

### Feature 2.1: Agentic Execution Engine

**Feature ID:** NEXIQ-F2.1  
**Description:** Multi-step LangChain Agent that orchestrates fraud verification steps sequentially, with progress tracking and reasoning transparency.

---

#### NEXIQ-US-201: Agentic Step Orchestration

**Story:** As a claims adjuster, I want the system to automatically execute a multi-step fraud verification pipeline after data extraction so that I receive a comprehensive fraud assessment without manual intervention.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Data extraction complete | Verification begins | System executes all 5 steps sequentially |
| AC2 | Pipeline executing | Step completes | Progress: "Step N of 5" with step name shown in UI |
| AC3 | Pipeline executing | Step in progress | "Executing..." indicator shown |
| AC4 | Any step fails/times out | Failure occurs | Pipeline **continues** to remaining steps; failed step flagged `UNAVAILABLE` |
| AC5 | Full pipeline | Timer measured | Completes < 60 seconds P95 |
| AC6 | Each LLM call | Invoked | Routes through Quasar gateway; all steps logged |

**Technical Specification:**

**Pipeline Architecture (fraud_agent.py → `run_verification_pipeline()`):**

```python
async def run_verification_pipeline(invoice, session_id, document_name) -> AsyncGenerator[dict, None]:
    """Yields NDJSON progress updates as the pipeline executes."""
```

| Step | Name | Function | File | Sync/Async | Uses LLM? |
|------|------|----------|------|------------|----------|
| 1 | Data Extraction Summary | Inline in `fraud_agent.py` | `fraud_agent.py` | Sync | No |
| 2 | Arithmetic & Tax Validation | `verify_arithmetic(invoice)` | `verification.py` | Sync | Yes (optional) |
| 3 | Vendor Legitimacy | `verify_vendor(invoice)` | `verification.py` | **Async** | Yes |
| 4 | Market Price Benchmarking | `verify_prices(invoice)` | `verification.py` | **Async** | Yes |
| 5 | VIN Validation | `verify_vin(invoice)` | `verification.py` | **Async** | Yes |
| Final | LLM Verdict | Inline in `fraud_agent.py` | `fraud_agent.py` | Sync | Yes |

**Streaming Protocol (NDJSON):**

Each line is a JSON object followed by `\n`:
```json
{"type": "step_start", "step": 1, "total": 5, "name": "Data Extraction Summary"}
{"type": "step_complete", "step": 1, "result": {VerificationStepResult as JSON}}
{"type": "step_start", "step": 2, "total": 5, "name": "Arithmetic & Tax Validation"}
{"type": "step_complete", "step": 2, "result": {ArithmeticCheckResult as JSON}}
...
{"type": "report", "report": {FraudReport as JSON}}
```

**Error Recovery Pattern (per step):**
```python
try:
    stepN = verify_step(invoice)
    stepN.thought_process = apply_guardrails(stepN.thought_process)
    all_flags.extend(stepN.flags)
except Exception as e:
    logger.error(f"Step N failed: {e}")
    stepN = VerificationStepResult(
        step_number=N, step_name="...",
        status=CheckStatus.UNAVAILABLE,
        summary=f"Step failed: {e}", thought_process=f"Error: {e}",
    )
```

**Frontend Streaming (index.html → `runAnalysis()`):**
```javascript
const verifyResp = await fetch(`${API_BASE}/verify/${sessionId}`, { method: 'POST' });
const reader = verifyResp.body.getReader();
const decoder = new TextDecoder();
// Read NDJSON stream line-by-line
// Parse each line as JSON → handleVerificationUpdate(update)
```

**API Contract:**

```
POST /api/verify/{session_id}
Request: (empty body — uses session's extracted invoice_data)
Content-Type: application/x-ndjson (streaming response)

Stream lines:
  {"type": "step_start", "step": 1, "total": 5, "name": "Data Extraction Summary"}
  {"type": "step_complete", "step": 1, "result": {...}}
  ... (10 lines total: 5 starts + 5 completes)
  {"type": "report", "report": {...}}

Response 400 (no data): { "detail": "No extracted data — run extraction first" }
Response 404 (bad session): { "detail": "Session not found" }
```

**Implementation Checklist:**

- [ ] `run_verification_pipeline()` — async generator yielding NDJSON dicts
- [ ] Step 1–5 execute sequentially with try/except per step
- [ ] `apply_guardrails()` called on every thought_process before yielding
- [ ] Flags accumulated across all steps for verdict generation
- [ ] StreamingResponse with `media_type="application/x-ndjson"`
- [ ] Frontend: `ReadableStream` reader with line-by-line JSON parsing
- [ ] Frontend: `handleVerificationUpdate()` dispatches to correct renderer
- [ ] Test: Pipeline completes end-to-end on test invoice
- [ ] Test: Simulate step failure → pipeline continues, failed step shows UNAVAILABLE
- [ ] Test: Pipeline time < 60 seconds

**Definition of Done:**
- [ ] All 5 steps execute end-to-end
- [ ] Streaming progress renders in real-time in UI
- [ ] Failed step doesn't crash pipeline
- [ ] Complete pipeline takes < 60 seconds on test invoices

**Story Points:** 13  
**Priority:** Must Have (H1) — Sprint 1–2

---

#### NEXIQ-US-202: Thought Process Transparency

**Story:** As a claims adjuster, I want to see the AI's reasoning (thought process) at each step so that I can understand why the system flagged or cleared each check.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Agent executes a step | Reasoning generated | Collapsible "Thought Process" section shows chain-of-thought |
| AC2 | Step uses external tool | Tool returns data | Source and raw response shown in thought process |
| AC3 | All steps complete | User reviews | Each step's reasoning individually expandable/collapsible |
| AC4 | Thought process displayed | PII check | NO raw PII from external lookups — PII masked via guardrails |

**Technical Specification:**

| Aspect | Detail |
|--------|--------|
| **Backend** | Each `VerificationStepResult.thought_process` is a multi-line string built incrementally during the step |
| **Guardrails** | `apply_guardrails(thought_process)` called before returning — masks SSN, email, credit card, DOB |
| **PII masking function** | `mask_pii(text)` in `guardrails.py` — regex patterns for SSN, email, credit card, DOB, optionally phone |
| **Blocked phrases** | "claim denied", "claim is denied", "we are denying", etc. — if detected, disclaimer appended |
| **Frontend rendering** | Each step card has: `<button onclick="toggleThought('thought-N')">💭 Show Thought Process</button>` |
| **CSS transition** | `.thought-content { max-height: 0; transition: max-height 0.3s; }` → `.thought-content.open { max-height: 2000px; }` |
| **Font** | Thought process shown in `font-mono whitespace-pre-wrap` for readability |

**Implementation Checklist:**

- [ ] Each verification function builds `thought` string incrementally
- [ ] `apply_guardrails()` applied to all thought_process strings before yielding
- [ ] Frontend: collapsible thought section per step card
- [ ] Test: Thought process text does NOT contain raw SSN/email/CC
- [ ] Test: Thought process is readable (not overwhelming)

**Definition of Done:**
- [ ] Thought process renders for all 5 steps
- [ ] PII masking verified (SSN, email, CC, DOB)
- [ ] Blocked phrases trigger disclaimer
- [ ] Collapse/expand works smoothly

**Story Points:** 5  
**Priority:** Must Have (H1) — Sprint 2

---

### Feature 2.2: Arithmetic & Tax Validation (Step 2)

---

#### NEXIQ-US-203: Tax & Total Re-Calculation

**Story:** As a claims adjuster, I want the system to independently re-calculate all invoice arithmetic (line item totals, tax amounts, subtotal, grand total) so that I can detect padding or arithmetic manipulation.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Extracted line items | Verification runs | Each line item's (qty × unit_price) is re-calculated |
| AC2 | Tax rate present | Verification runs | Taxable vs non-taxable items classified, tax re-computed |
| AC3 | Re-calculation matches | Totals match (diff ≤ $0.01) | Status = "Arithmetic Verified ✓" |
| AC4 | Re-calculation differs | Diff > $0.01 | **FRAUD FLAG**: "Arithmetic Mismatch: Computed $X vs Invoice $Y" |
| AC5 | Minor rounding | Diff $0.02–$0.05 | Flagged as "Minor Rounding Variance" (WARNING, not CRITICAL) |
| AC6 | Major mismatch | Diff > $1.00 | CRITICAL severity flag |
| AC7 | Verification complete | Results display | Summary table: Line Items, Tax Rate, Tax Amount, Computed Total vs Invoice Total |

**Technical Specification:**

**Function:** `verify_arithmetic(invoice: InvoiceData) → ArithmeticCheckResult`  
**File:** `backend/app/tools/verification.py`  
**Sync/Async:** Synchronous (math is deterministic, LLM optional)

**Algorithm:**
```
1. For each line_item:
   expected = round(qty × unit_price, 2)
   actual = item.total
   diff = |expected - actual|
   if diff > 0.01 → CRITICAL flag: "Line item mismatch"
   computed_subtotal += expected

2. computed_tax = computed_subtotal × (tax_rate / 100)
   (if no tax_rate, use invoice.tax_amount as-is)

3. computed_total = computed_subtotal + computed_tax

4. total_diff = |computed_total - invoice.total|
   if total_diff > 1.00 → CRITICAL flag
   if total_diff > 0.05 → WARNING flag
   if total_diff > 0.01 → "Minor Rounding Variance" (no flag)
   else → "Arithmetic Verified ✓"

5. (Optional) LLM analysis via ARITHMETIC_ANALYSIS_PROMPT:
   - Tax classification (taxable vs non-taxable)
   - Pattern detection (padding, inflated quantities)
   - Risk level assessment
```

**LLM Prompt (ARITHMETIC_ANALYSIS_PROMPT):**
- Input: invoice summary, line item calculations, computed vs invoice totals
- Output JSON: `analysis`, `tax_classification`, `anomalies_found`, `anomaly_details[]`, `risk_level`, `recommendation`
- If LLM response has `anomalies_found: true` AND `risk_level: "high"` → add WARNING flags per anomaly

**Return Model:** `ArithmeticCheckResult` (extends `VerificationStepResult`)
- `line_item_checks: list[dict]` — per-item check results
- `computed_subtotal`, `computed_tax`, `computed_total`, `invoice_total`

**Implementation Checklist:**

- [ ] `verify_arithmetic()` — deterministic math re-calculation
- [ ] Line item check: qty × unit_price vs listed total (tolerance: $0.01)
- [ ] Subtotal, tax, grand total re-computation
- [ ] Flag severity: > $1.00 = CRITICAL, $0.05–$1.00 = WARNING
- [ ] LLM analysis for tax classification (optional, fails gracefully)
- [ ] Thought process built incrementally with all calculations
- [ ] Test: Invoice with correct arithmetic → PASSED
- [ ] Test: Invoice with one wrong line item → CRITICAL flag
- [ ] Test: Invoice with $0.03 rounding diff → no flag (minor variance)
- [ ] Test: Multi-tax-rate invoice handled

**Definition of Done:**
- [ ] Tested with correct and incorrect arithmetic invoices
- [ ] Handles multi-tax-rate invoices
- [ ] Rounding differences < $0.05 NOT flagged as fraud
- [ ] LLM failure doesn't crash step (rule-based math still works)

**Story Points:** 5  
**Priority:** Must Have (H1) — Sprint 2

---

### Feature 2.3: Vendor Legitimacy Verification (Step 3)

---

#### NEXIQ-US-204: Vendor Identity Cross-Reference

**Story:** As a claims adjuster, I want the system to verify the vendor's name, address, and phone number against public sources so that I can detect invoices from fictitious or spoofed vendors.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Vendor name + address | Verification runs | System analyzes vendor legitimacy (LLM + optional web search) |
| AC2 | Vendor appears legitimate | LLM assessment: `likely_legitimate` | Status = "Vendor Name/Address Verified ✓" |
| AC3 | Vendor appears suspicious | LLM assessment: `suspicious` | **FRAUD FLAG** (CRITICAL): "Vendor assessed as suspicious" |
| AC4 | Vendor needs verification | LLM assessment: `needs_verification` | Status = "Vendor Not Verified — Manual Review Required" |
| AC5 | No vendor name extracted | Verification runs | Status = MANUAL_REVIEW, no further processing |
| AC6 | Tavily API key available | Web search runs | Searches for vendor name + address + phone, results shown in thought |
| AC7 | Compliance | All searches | Only vendor info in queries — NO policyholder PII |

**Technical Specification:**

**Function:** `async verify_vendor(invoice: InvoiceData) → VendorCheckResult`  
**File:** `backend/app/tools/verification.py`  
**Async:** Yes (Tavily web search is async HTTP)

**Algorithm:**
```
1. Extract vendor_name, phone, address, website from invoice
2. If no vendor_name → return MANUAL_REVIEW immediately
3. Build service type summary from first 5 line items
4. Send VENDOR_ANALYSIS_PROMPT to LLM via gateway
5. Parse LLM JSON response:
   - business_name_assessment: legitimate|suspicious|unknown
   - address_assessment: valid_commercial|valid_residential|suspicious|unknown
   - phone_assessment: valid|suspicious|missing
   - red_flags: [list]
   - overall_legitimacy: likely_legitimate|needs_verification|suspicious
   - confidence: 0.0–1.0
6. Map overall_legitimacy to CheckStatus:
   - "suspicious" → FAILED + CRITICAL flag
   - "needs_verification" → MANUAL_REVIEW
   - "likely_legitimate" → PASSED
7. Each red_flag → WARNING flag
8. (Optional) If TAVILY_API_KEY set: search web for vendor, add results to thought
```

**LLM Prompt (VENDOR_ANALYSIS_PROMPT):**
- Input: vendor name, address, phone, website, invoice number, total, service types
- Output JSON: `analysis`, `business_name_assessment`, `address_assessment`, `phone_assessment`, `red_flags[]`, `overall_legitimacy`, `confidence`, `recommendation`

**Tavily Integration (optional):**
```python
if tavily_key:
    POST https://api.tavily.com/search
    body: {"api_key": key, "query": "{vendor_name} {address} phone number", "max_results": 3}
    # Results added to thought process only — NOT used for verdict override
```

**Implementation Checklist:**

- [ ] `verify_vendor()` — async function with LLM analysis
- [ ] Guard: return early if no vendor name
- [ ] `VENDOR_ANALYSIS_PROMPT` — vendor legitimacy assessment
- [ ] Parse LLM response → map to status + flags
- [ ] Tavily web search (gated on `TAVILY_API_KEY` env var)
- [ ] No PII in outbound web search queries
- [ ] Test: Known legitimate vendor → PASSED
- [ ] Test: Fictitious vendor name → CRITICAL flag or MANUAL_REVIEW
- [ ] Test: Missing vendor name → MANUAL_REVIEW
- [ ] Test: LLM unavailable → MANUAL_REVIEW (not crash)

**Definition of Done:**
- [ ] Tested with legitimate and fictitious vendors
- [ ] Handles franchise businesses (multiple locations)
- [ ] No PII in outbound search queries
- [ ] LLM failure → graceful fallback to MANUAL_REVIEW

**Story Points:** 8  
**Priority:** Must Have (H1) — Sprint 2

---

### Feature 2.4: Market Price Benchmarking (Step 4)

---

#### NEXIQ-US-205: Price Deviation Analysis

**Story:** As a claims adjuster, I want the system to compare each line item price against market benchmarks so that I can detect price inflation or phantom charges.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Line items with prices | Benchmarking runs | Each item compared against market price range |
| AC2 | Price within range | Assessment: `reasonable` | Status = "Within Market Range ✓" |
| AC3 | Price > 50% above range | Assessment: `overpriced`/`suspicious` | **FRAUD FLAG**: "Price Anomaly: [Item] at $X vs market $Y–$Z" |
| AC4 | Price > 100% above range | Deviation > 100% | **CRITICAL** severity flag |
| AC5 | No market data | Assessment unknown | Status = "No Benchmark Available — Manual Review" |
| AC6 | Benchmarking complete | Results display | Comparison table: Item, Invoice Price, Market Low, Market High, Deviation %, Status |

**Technical Specification:**

**Function:** `async verify_prices(invoice: InvoiceData) → PriceCheckResult`  
**File:** `backend/app/tools/verification.py`  
**Async:** Yes (for potential web search fallback)

**Algorithm:**
```
1. Build line_items_text from invoice line items
2. Get vehicle info and vendor address for context
3. Send PRICE_ANALYSIS_PROMPT to LLM
4. Parse LLM JSON response:
   - item_assessments[]: item, invoice_price, estimated_market_low/high, assessment, deviation_pct, notes
   - overall_pricing: reasonable|slightly_elevated|significantly_inflated|suspicious
   - total_estimated_overcharge
5. For each item assessment:
   - "overpriced" or "suspicious" → WARNING flag (or CRITICAL if deviation > 100%)
6. If LLM fails → call _fallback_price_check() for keyword-based matching
```

**LLM Prompt (PRICE_ANALYSIS_PROMPT):**
- Input: line items text, vendor name, vendor address, vehicle info
- Output JSON: `analysis`, `item_assessments[]`, `overall_pricing`, `total_estimated_overcharge`, `red_flags[]`, `recommendation`

**Fallback (`_fallback_price_check`):**
- Keyword-based price matching using hardcoded market ranges for common auto parts
- Returns basic comparisons with lower confidence

**Configurable Threshold:**
- Env var: `FRAUD_PRICE_DEVIATION_THRESHOLD` (default: `50` = 50%)
- Deviation > threshold → flag raised

**Implementation Checklist:**

- [ ] `verify_prices()` — async function with LLM price analysis
- [ ] `PRICE_ANALYSIS_PROMPT` — market price benchmarking
- [ ] Parse item assessments → flags by severity
- [ ] `_fallback_price_check()` — keyword-based fallback when LLM unavailable
- [ ] Configurable threshold via env var
- [ ] Test: Invoice with reasonable prices → PASSED
- [ ] Test: Invoice with 200% inflated price → CRITICAL flag
- [ ] Test: LLM unavailable → fallback works
- [ ] Test: Mixed labor + parts pricing

**Definition of Done:**
- [ ] Tested with auto repair, medical, general invoices
- [ ] Labor vs parts pricing handled separately by LLM
- [ ] Deviation threshold configurable
- [ ] LLM failure → keyword fallback

**Story Points:** 8  
**Priority:** Must Have (H1) — Sprint 3

---

### Feature 2.5: VIN Validation (Step 5)

---

#### NEXIQ-US-206: VIN Lookup & Cross-Validation

**Story:** As a claims adjuster, I want the system to validate the VIN from an auto repair invoice against a VIN database so that I can detect mismatched vehicle information indicating fraud.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Extracted VIN | Lookup runs | System queries NHTSA vPIC API |
| AC2 | VIN decode succeeds | Year/make/model match invoice | Status = "VIN Verified ✓" |
| AC3 | VIN decode succeeds | Year/make/model DON'T match | **FRAUD FLAG**: "VIN Mismatch: VIN decodes to [X] but invoice claims [Y]" |
| AC4 | VIN format invalid | Not 17 chars or fails check digit | **FRAUD FLAG**: "Invalid VIN Format" |
| AC5 | No VIN on invoice | VIN field empty | Status = MANUAL_REVIEW: "No VIN available for validation" |
| AC6 | NHTSA API unavailable | Timeout or error | Status = UNAVAILABLE: "VIN Check Unavailable — Manual Review" |

**Technical Specification:**

**Function:** `async verify_vin(invoice: InvoiceData) → VINCheckResult`  
**File:** `backend/app/tools/verification.py`  
**Async:** Yes (NHTSA API call is async HTTP)

**Algorithm:**
```
1. Get VIN from invoice.vehicle.vin.value
2. If empty/None → return MANUAL_REVIEW
3. Validate VIN format:
   - Must be 17 characters
   - Must not contain I, O, Q
   - Use regex: ^[A-HJ-NPR-Z0-9]{17}$
4. Call NHTSA vPIC API:
   GET https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json
   Timeout: 5 seconds
5. Parse response → extract Make, Model, ModelYear
6. Compare decoded values against invoice:
   - Year match (exact)
   - Make match (case-insensitive, partial match for abbreviations)
   - Model match (case-insensitive, partial match)
7. Send VIN_ANALYSIS_PROMPT to LLM for cross-validation + mileage assessment
8. Combine results:
   - All match → PASSED: "VIN Verified ✓"
   - Any mismatch → FAILED + CRITICAL flag
   - Format invalid → FAILED + CRITICAL flag
   - API unavailable → UNAVAILABLE
```

**NHTSA API Response Parsing:**
```python
# Response contains Results[] array with Variable/Value pairs
# Key variables:
# - "Make" → decoded make
# - "Model" → decoded model
# - "Model Year" → decoded year
# - "Error Code" → "0" means success
```

**LLM Prompt (VIN_ANALYSIS_PROMPT):**
- Input: invoice make/model/year, VIN, mileage, decoded make/model/year
- Output JSON: `analysis`, `make_match`, `model_match`, `year_match`, `vin_format_valid`, `mileage_assessment`, `mismatches[]`, `risk_level`, `recommendation`

**Implementation Checklist:**

- [ ] `verify_vin()` — async function with NHTSA API + LLM
- [ ] VIN format validation (17 chars, no I/O/Q)
- [ ] NHTSA API call with 5-second timeout
- [ ] Parse NHTSA response → extract Make, Model, Year
- [ ] Case-insensitive comparison with partial match support
- [ ] `VIN_ANALYSIS_PROMPT` for deeper cross-validation
- [ ] Return `VINCheckResult` with decoded values
- [ ] Test: Valid VIN matching invoice → PASSED
- [ ] Test: Valid VIN mismatching invoice → CRITICAL flag
- [ ] Test: Invalid VIN format (< 17 chars) → CRITICAL flag
- [ ] Test: VIN with I/O/Q characters → CRITICAL flag
- [ ] Test: NHTSA API timeout → UNAVAILABLE
- [ ] Test: No VIN on invoice → MANUAL_REVIEW

**Definition of Done:**
- [ ] All 6 test cases pass
- [ ] API timeout handling (5s timeout, graceful fallback)
- [ ] Works for US VIN formats
- [ ] LLM failure → still validates using NHTSA data alone

**Story Points:** 5  
**Priority:** Must Have (H1) — Sprint 3

---

## Epic 3: Fraud Assessment & Reporting

**Epic ID:** NEXIQ-E3  
**Description:** Aggregate verification results into a consolidated fraud assessment with verdict, flagged anomalies, and recommendations.  
**Business Value:** Single auditable fraud report per document — reduces SIU referral decision time from 2 hours to 5 minutes.

### Feature 3.1: Consolidated Fraud Report

---

#### NEXIQ-US-301: Verification Summary Dashboard

**Story:** As a claims adjuster, I want a summary table showing pass/fail for each verification check so that I can see the overall fraud risk at a glance.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | All steps complete | Summary renders | Table: Check Name, Status (✓/⚠/✗), Details |
| AC2 | All checks pass | Summary renders | Overall: "Low Risk — No Fraud Indicators Detected" |
| AC3 | 1+ checks flag anomalies | Summary renders | Overall: "Requires Review — [N] Anomalies Detected" |
| AC4 | Summary displayed | User clicks row | Expands to show thought process for that step |

**Technical Specification:**

| Aspect | Detail |
|--------|--------|
| **Data Source** | `FraudReport.verification_results[]` — array of `VerificationStepResult` |
| **Streamed as** | Last NDJSON line: `{"type": "report", "report": {FraudReport JSON}}` |
| **Frontend function** | `renderReport(report)` in `index.html` |
| **Verdict color** | `Approve for Processing` → green, `Approve with Notation` → amber, `Escalate to SIU` → red |
| **Flag rendering** | Each flag card: `[CRITICAL]` in red, `[WARNING]` in amber |
| **Advisory disclaimer** | Always shown: "⚠️ Advisory — This is not an automated claim decision." |

**Frontend HTML Structure:**
```html
<div class="border-2 border-{color}-400 rounded-xl p-4 bg-{color}-50">
  <h3>📊 Fraud Analysis Complete</h3>
  <div class="text-2xl font-bold">{verdict}</div>
  <p>Flags: {total} total ({critical} critical)</p>
  <p>Reasoning: {reasoning}</p>
  <p>Recommendation: {recommendation}</p>
  <div class="advisory">⚠️ Advisory Notice...</div>
</div>
```

**Implementation Checklist:**

- [ ] `renderReport()` — renders verdict card with color coding
- [ ] Flag summary with severity badges
- [ ] Thought process expandable per step (already in step_complete handler)
- [ ] Advisory disclaimer always present
- [ ] Test: Clean invoice → green card, "Approve for Processing"
- [ ] Test: Invoice with warnings → amber card, "Approve with Notation"
- [ ] Test: Invoice with critical flags → red card, "Escalate to SIU"

**Definition of Done:**
- [ ] Summary renders for all test invoices
- [ ] Visual layout matches: status table + expandable details
- [ ] Advisory disclaimer always visible

**Story Points:** 5  
**Priority:** Must Have (H1) — Sprint 3

---

#### NEXIQ-US-302: Overall Fraud Verdict & Recommendation

**Story:** As a claims adjuster, I want an AI-generated overall verdict with a recommendation (Approve / Escalate to SIU / Reject) so that I can take action quickly.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | All checks pass | Verdict generated | Recommendation = "Approve for Processing" |
| AC2 | 1+ non-critical flags | Verdict generated | Recommendation = "Approve with Notation" |
| AC3 | Critical flags (arithmetic mismatch, invalid VIN, price > 100%) | Verdict generated | Recommendation = "Escalate to SIU" |
| AC4 | Any verdict | Display | **No automated claim denial** — verdict is advisory only |
| AC5 | Any verdict | Quasar check | Verdict + reasoning logged to audit trail |

**Technical Specification:**

**Verdict Generation (fraud_agent.py, lines ~150–230):**

```
1. Collect all flags from all steps
2. Count critical_flags and warning_flags
3. Build verification_summary text from all results
4. Send VERDICT_PROMPT to LLM via gateway
5. Parse LLM response: verdict, confidence, reasoning, key_findings, risk_score, recommendation
6. Map LLM verdict string to VerdictType enum
7. RULE-BASED OVERRIDE: If critical_flags > 0 AND LLM didn't say "Escalate"
   → Force verdict = ESCALATE_SIU
   → Prepend "[OVERRIDE]" to reasoning
8. Fallback (LLM unavailable):
   - critical_flags > 0 → ESCALATE_SIU
   - warning_flags > 0 → APPROVE_WITH_NOTATION
   - no flags → APPROVE
```

**CRITICAL COMPLIANCE RULE:**
- LLM VERDICT_PROMPT explicitly states: "This is ADVISORY ONLY — never state that a claim is denied"
- `guardrails.py` blocks phrases: "claim denied", "claim is denied", "automatically denied"
- Rule-based override ALWAYS escalates on critical flags (LLM cannot override safety rules)

**Implementation Checklist:**

- [ ] VERDICT_PROMPT with compliance rules embedded
- [ ] LLM verdict parsing with enum mapping
- [ ] Rule-based override for critical flags
- [ ] Fallback verdict logic (no LLM)
- [ ] Advisory disclaimer in report
- [ ] Test: All checks pass → APPROVE
- [ ] Test: Non-critical flags → APPROVE_WITH_NOTATION
- [ ] Test: Critical flags → ESCALATE_SIU (even if LLM says approve)
- [ ] Test: LLM unavailable → rule-based verdict works

**Definition of Done:**
- [ ] Verdict logic tested with clean, suspicious, fraudulent invoices
- [ ] "Advisory only" disclaimer in UI and PDF
- [ ] Rule-based override tested: critical flag always = SIU escalation

**Story Points:** 5  
**Priority:** Must Have (H1) — Sprint 3

---

#### NEXIQ-US-303: Fraud Report Export

**Story:** As a claims supervisor, I want to export the fraud analysis report as a PDF so that I can attach it to the claim file.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Analysis complete | User clicks "Export Report" | PDF generated and downloaded |
| AC2 | PDF generated | Opened | Contains: Invoice summary, each check result, verdict, disclaimer |
| AC3 | PDF content | Compliance check | Includes: "Advisory — Not an Automated Decision" disclaimer |

**Technical Specification:**

**Function:** `generate_fraud_report_pdf(report: FraudReport) → bytes`  
**File:** `backend/app/services/report_generator.py`  
**Library:** ReportLab

**PDF Sections:**
1. **Header:** "NexusIQ — Fraud Analysis Report" + document name + date + session ID
2. **Invoice Summary Table:** Invoice #, Date, Vendor, Customer, Vehicle, VIN, Total
3. **Verification Results Table:** Step, Check, Status (✓/✗/⚠/—/?), Details
4. **Fraud Flags Section:** (if any) Severity-colored flags with messages
5. **Overall Verdict:** Colored verdict text + reasoning + recommendation
6. **Disclaimer:** "DISCLAIMER: ...advisory only...not an automated claim decision..."

**API Contract:**

```
GET /api/report/{session_id}/pdf
Response 200:
  Content-Type: application/pdf
  Content-Disposition: attachment; filename=nexusiq-fraud-report-{session_id[:8]}.pdf
  Body: <binary PDF>

Response 400: { "detail": "No report available — run verification first" }
Response 404: { "detail": "Session not found" }
```

**Frontend:**
```javascript
function exportPDF() {
    window.open(`${API_BASE}/report/${sessionId}/pdf`, '_blank');
}
// Export button visible only when currentState === 'complete'
```

**Implementation Checklist:**

- [ ] `generate_fraud_report_pdf()` — ReportLab PDF generation
- [ ] Invoice summary table with styled cells
- [ ] Verification results table with status symbols
- [ ] Fraud flags with severity colors
- [ ] Verdict section with colored text
- [ ] Disclaimer section (always present)
- [ ] API endpoint returns PDF as download
- [ ] Frontend: Export button visible only after analysis complete
- [ ] Test: PDF renders correctly with all sections
- [ ] Test: PDF includes disclaimer

**Definition of Done:**
- [ ] PDF renders correctly with all sections
- [ ] Disclaimer always present
- [ ] Export button only visible after complete analysis
- [ ] Downloaded filename: `nexusiq-fraud-report-{session_id[:8]}.pdf`

**Story Points:** 5  
**Priority:** Must Have (H1) — Sprint 3
