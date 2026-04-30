import io
import json
import re
import logging
from typing import Optional
import pdfplumber
from ..models.schemas import (
    InvoiceData, ExtractedField, VendorInfo,
    CustomerInfo, VehicleInfo, LineItem
)
from .coforge_llm import invoke_llm

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an expert at extracting structured data from insurance-related invoices and repair estimates.

Extract all information from the following invoice text and return a JSON object with this exact structure:

{{
  "invoice_number": {{"value": "", "confidence": 0.0}},
  "invoice_date": {{"value": "", "confidence": 0.0}},
  "vendor": {{
    "name": {{"value": "", "confidence": 0.0}},
    "address": {{"value": "", "confidence": 0.0}},
    "phone": {{"value": "", "confidence": 0.0}},
    "website": {{"value": "", "confidence": 0.0}}
  }},
  "customer": {{
    "name": {{"value": "", "confidence": 0.0}},
    "address": {{"value": "", "confidence": 0.0}},
    "phone": {{"value": "", "confidence": 0.0}}
  }},
  "vehicle": {{
    "make": {{"value": "", "confidence": 0.0}},
    "model": {{"value": "", "confidence": 0.0}},
    "year": {{"value": "", "confidence": 0.0}},
    "vin": {{"value": "", "confidence": 0.0}},
    "mileage": {{"value": "", "confidence": 0.0}}
  }},
  "line_items": [
    {{
      "description": "",
      "part_number": null,
      "quantity": 1.0,
      "unit_price": 0.0,
      "total": 0.0,
      "is_taxable": true,
      "confidence": 0.0
    }}
  ],
  "subtotal": 0.0,
  "tax_rate": 0.0,
  "tax_amount": 0.0,
  "total": 0.0
}}

Confidence scoring rules:
- 1.0 = field clearly present and readable
- 0.5-0.8 = partially visible or inferred
- 0.0-0.5 = guessed or not found
- Missing fields = "" with confidence 0.0

Return ONLY the JSON, no explanation.

Invoice text:
{text}"""

def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        text_parts.append(" | ".join([str(c) if c else "" for c in row]))
    return "\n".join(text_parts)

def parse_extraction_response(response_text: str) -> InvoiceData:
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", response_text).strip()
    data = json.loads(cleaned)
    
    def ef(obj) -> ExtractedField:
        if isinstance(obj, dict):
            return ExtractedField(value=str(obj.get("value", "")), confidence=float(obj.get("confidence", 0.0)))
        return ExtractedField()

    line_items = []
    for item in data.get("line_items", []):
        line_items.append(LineItem(
            description=item.get("description", ""),
            part_number=item.get("part_number"),
            quantity=float(item.get("quantity", 0)),
            unit_price=float(item.get("unit_price", 0)),
            total=float(item.get("total", 0)),
            is_taxable=bool(item.get("is_taxable", True)),
            confidence=float(item.get("confidence", 0))
        ))

    v = data.get("vendor", {})
    c = data.get("customer", {})
    vh = data.get("vehicle", {})

    return InvoiceData(
        invoice_number=ef(data.get("invoice_number", {})),
        invoice_date=ef(data.get("invoice_date", {})),
        vendor=VendorInfo(
            name=ef(v.get("name", {})), address=ef(v.get("address", {})),
            phone=ef(v.get("phone", {})), website=ef(v.get("website", {}))
        ),
        customer=CustomerInfo(
            name=ef(c.get("name", {})), address=ef(c.get("address", {})),
            phone=ef(c.get("phone", {}))
        ),
        vehicle=VehicleInfo(
            make=ef(vh.get("make", {})), model=ef(vh.get("model", {})),
            year=ef(vh.get("year", {})), vin=ef(vh.get("vin", {})),
            mileage=ef(vh.get("mileage", {}))
        ),
        line_items=line_items,
        subtotal=float(data.get("subtotal", 0)),
        tax_rate=float(data.get("tax_rate", 0)),
        tax_amount=float(data.get("tax_amount", 0)),
        total=float(data.get("total", 0))
    )

def extract_invoice_data(file_bytes: bytes, use_llm: bool = True) -> InvoiceData:
    raw_text = extract_text_from_pdf(file_bytes)
    
    if use_llm:
        try:
            prompt = EXTRACTION_PROMPT.format(text=raw_text[:6000])
            response = invoke_llm(prompt, system="You are a document extraction expert. Return only valid JSON.")
            invoice = parse_extraction_response(response)
            invoice.raw_text = raw_text
            return invoice
        except Exception as e:
            logger.warning(f"LLM extraction failed, falling back to text-only: {e}")

    # Text-only fallback with low confidence
    return InvoiceData(raw_text=raw_text)
