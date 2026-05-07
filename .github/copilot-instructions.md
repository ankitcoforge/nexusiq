# Copilot Instructions – Fraud Detection Application

## Project Overview
This is a **Fraud Detection Application** built with Python, LangChain, and OpenAI (via Quasar Marketplace).
The goal is to detect fraudulent transactions, activities, or patterns using AI/ML techniques and LLM-powered reasoning.

---

## Core Objectives
- Detect fraudulent transactions in real-time or batch mode
- Use LangChain chains and agents to analyze suspicious patterns
- Integrate with SQL Server for transaction data
- Provide explainable fraud alerts with reasoning
- Minimize false positives while maximizing fraud detection accuracy

---

## Tech Stack
- **Language**: Python 3.x
- **LLM Framework**: LangChain + LangChain-OpenAI
- **LLM Provider**: Quasar Marketplace (Coforge) — model: `gpt-4o-mini`
- **Auth**: `x-api-key` header (NOT Bearer token)
- **Database**: Microsoft SQL Server (via `pyodbc` / `mssql`)
- **Config**: `.env` file with `python-dotenv`

---

## Coding Guidelines

### General
- Always load config from `.env` using `python-dotenv`
- Never hardcode API keys, credentials, or connection strings
- Use structured logging (`logging` module) — not plain `print()`
- All functions must have docstrings explaining inputs, outputs, and purpose
- Handle exceptions gracefully with meaningful error messages

### LangChain Patterns
- Use `ChatOpenAI` with `default_headers={"x-api-key": api_key}` for Quasar Marketplace
- Prefer `langchain_core.messages` over deprecated `langchain.schema`
- Use LangChain **chains** for multi-step fraud analysis pipelines
- Use LangChain **agents** for dynamic tool-calling fraud investigations
- Use LangChain **memory** for conversational fraud investigation sessions

### Fraud Detection Specifics
- Flag transactions based on: amount thresholds, location anomalies, velocity checks, unusual patterns
- Always return a **fraud score (0-100)** and **reasoning explanation** with every analysis
- Use **few-shot prompting** to guide the LLM with known fraud patterns
- Batch suspicious transactions and analyze in groups where possible
- Store fraud decisions with timestamps and audit trail in the database

---

## Fraud Analysis Prompt Style
When writing prompts for fraud detection:
- Provide clear context: transaction amount, merchant, location, time, user history
- Ask for: fraud likelihood score, key risk factors, recommended action
- Example structure:
  ```
  Analyze this transaction for fraud:
  - Amount: $X
  - Merchant: Y
  - Location: Z
  - User history: ...
  Return: fraud_score (0-100), risk_factors (list), recommendation (allow/review/block)
  ```

---

## Project Structure
```
C:\nexusiqapp\
├── .github\
│   └── copilot-instructions.md   ← You are here
├── .env                          ← API keys & config
├── main.py                       ← Entry point
├── fraud_detector.py             ← Core fraud detection logic
├── data_loader.py                ← SQL Server data fetching
├── prompts.py                    ← LangChain prompt templates
├── models.py                     ← Data models / schemas
├── utils\
│   ├── logger.py                 ← Logging setup
│   └── helpers.py                ← Utility functions
├── tests\
│   └── test_fraud_detector.py    ← Unit tests
└── requirements.txt
```

---

## Do's and Don'ts
| ✅ Do | ❌ Don't |
|-------|--------|
| Use environment variables for secrets | Hardcode API keys |
| Return fraud score + explanation | Return just True/False |
| Log all fraud decisions | Use bare `print()` statements |
| Write unit tests for detection logic | Skip error handling |
| Use LangChain chains for pipelines | Write monolithic scripts |
