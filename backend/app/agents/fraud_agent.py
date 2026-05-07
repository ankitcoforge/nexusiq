import time
import json
import logging
from typing import AsyncGenerator
from datetime import datetime
from ..models.schemas import (
    InvoiceData, FraudReport, FraudFlag, FraudFlagSeverity,
    VerdictType, CheckStatus, VerificationStepResult
)
from ..tools.verification import verify_arithmetic, verify_vendor, verify_prices, verify_vin
from ..services.coforge_llm import invoke_llm
from ..services.langchain_tools import search_web
from ..utils.guardrails import apply_guardrails

logger = logging.getLogger(__name__)

def _step1_summary(invoice: InvoiceData) -> VerificationStepResult:
    start = time.time()
    thought = "=== Step 1: Data Extraction Summary ===\n\n"
    flags = []
    low_confidence = []

    for field_name in ["invoice_number", "invoice_date"]:
        field = getattr(invoice, field_name)
        thought += f"{field_name}: '{field.value}' (confidence: {field.confidence:.2f})\n"
        if field.confidence < 0.5:
            low_confidence.append(field_name)

    thought += f"\nVendor: {invoice.vendor.name.value} (conf: {invoice.vendor.name.confidence:.2f})\n"
    thought += f"Customer: {invoice.customer.name.value} (conf: {invoice.customer.name.confidence:.2f})\n"
    thought += f"Vehicle: {invoice.vehicle.year.value} {invoice.vehicle.make.value} {invoice.vehicle.model.value}\n"
    thought += f"VIN: {invoice.vehicle.vin.value} (conf: {invoice.vehicle.vin.confidence:.2f})\n"
    thought += f"Line items: {len(invoice.line_items)}\n"
    thought += f"Invoice total: ${invoice.total:.2f}\n"

    # --- Internet search to validate extracted data ---
    vendor_name = invoice.vendor.name.value or ""
    if vendor_name:
        thought += f"\n🔍 Searching internet for vendor: {vendor_name}\n"
        try:
            web_result = search_web(f"{vendor_name} business reviews location")
            web_summary = web_result.get("summary", "")
            if web_summary and "failed" not in web_summary.lower():
                thought += f"Web results: {web_summary[:300]}\n"

                web_lower = web_summary.lower()
                if any(w in web_lower for w in ["scam", "fraud", "fake", "complaint"]):
                    flags.append(FraudFlag(
                        check_name="Vendor Web Presence",
                        severity=FraudFlagSeverity.WARNING,
                        message=f"Negative signals found online for '{vendor_name}'",
                        details=web_summary[:200]
                    ))
                    thought += "⚠️ Negative signals detected in web results\n"
                elif any(w in web_lower for w in ["official", "verified", "established", "franchise"]):
                    thought += "✓ Vendor appears to have legitimate web presence\n"
                else:
                    thought += "ℹ️ Vendor found online, no strong signals either way\n"
            else:
                thought += "⚠️ No web results found for vendor\n"
        except Exception as e:
            thought += f"⚠️ Web search unavailable: {e}\n"

    if low_confidence:
        thought += f"\n⚠️ Low confidence fields: {', '.join(low_confidence)}\n"
        flags.append(FraudFlag(
            check_name="Low Confidence Fields",
            severity=FraudFlagSeverity.INFO,
            message=f"{len(low_confidence)} field(s) need manual review",
            details=f"Fields: {', '.join(low_confidence)}"
        ))
        status = CheckStatus.WARNING
        summary = f"Extraction complete with {len(low_confidence)} low-confidence field(s)"
    else:
        status = CheckStatus.PASSED
        summary = f"✓ Data extracted — {len(invoice.line_items)} line items, total ${invoice.total:.2f}"

    thought = apply_guardrails(thought)
    return VerificationStepResult(
        step_number=1, step_name="Data Extraction Summary",
        status=status, summary=summary, thought_process=thought,
        flags=flags, duration_seconds=round(time.time() - start, 2)
    )

def _determine_verdict(all_flags: list, invoice: InvoiceData) -> tuple[VerdictType, str, str]:
    critical = [f for f in all_flags if f.severity == FraudFlagSeverity.CRITICAL]
    warnings = [f for f in all_flags if f.severity == FraudFlagSeverity.WARNING]

    try:
        flag_summary = "\n".join([f"- [{f.severity.value.upper()}] {f.message}" for f in all_flags])
        prompt = f"""As a fraud detection system, determine the verdict for this insurance invoice analysis.

Invoice total: ${invoice.total:.2f}
Vendor: {invoice.vendor.name.value}

Fraud flags found ({len(all_flags)} total):
{flag_summary if flag_summary else "No flags found"}

Critical flags: {len(critical)}
Warning flags: {len(warnings)}

Return JSON:
{{"verdict": "Approve for Processing|Approve with Notation|Escalate to SIU", "reasoning": "", "recommendation": ""}}"""
        response = invoke_llm(prompt)
        import re, json
        cleaned = re.sub(r"```(?:json)?", "", response).strip()
        result = json.loads(cleaned)
        verdict_str = result.get("verdict", "Approve for Processing")
        verdict = VerdictType(verdict_str) if verdict_str in [v.value for v in VerdictType] else VerdictType.APPROVE
        return verdict, result.get("reasoning", ""), result.get("recommendation", "")
    except Exception as e:
        logger.warning(f"LLM verdict failed: {e}")
        if critical:
            return VerdictType.ESCALATE_SIU, f"{len(critical)} critical flag(s) found", "Escalate to SIU for manual review"
        elif warnings:
            return VerdictType.APPROVE_WITH_NOTATION, f"{len(warnings)} warning(s)", "Approve with supervisor notation"
        return VerdictType.APPROVE, "No significant flags found", "Approve for processing"

async def run_verification_pipeline(invoice: InvoiceData, session_id: str, document_name: str) -> AsyncGenerator[dict, None]:
    all_flags = []
    results = []

    # Step 1
    yield {"type": "step_start", "step": 1, "total": 5, "name": "Data Extraction Summary"}
    step1 = _step1_summary(invoice)
    all_flags.extend(step1.flags)
    results.append(step1)
    yield {"type": "step_complete", "step": 1, "result": step1.model_dump()}

    # Step 2
    yield {"type": "step_start", "step": 2, "total": 5, "name": "Arithmetic & Tax Validation"}
    try:
        step2 = verify_arithmetic(invoice)
    except Exception as e:
        step2 = VerificationStepResult(step_number=2, step_name="Arithmetic & Tax Validation", status=CheckStatus.UNAVAILABLE, summary=str(e))
    all_flags.extend(step2.flags)
    results.append(step2)
    yield {"type": "step_complete", "step": 2, "result": step2.model_dump()}

    # Step 3
    yield {"type": "step_start", "step": 3, "total": 5, "name": "Vendor Legitimacy"}
    try:
        step3 = await verify_vendor(invoice)
    except Exception as e:
        step3 = VerificationStepResult(step_number=3, step_name="Vendor Legitimacy", status=CheckStatus.UNAVAILABLE, summary=str(e))
    all_flags.extend(step3.flags)
    results.append(step3)
    yield {"type": "step_complete", "step": 3, "result": step3.model_dump()}

    # Step 4
    yield {"type": "step_start", "step": 4, "total": 5, "name": "Market Price Benchmarking"}
    try:
        step4 = await verify_prices(invoice)
    except Exception as e:
        step4 = VerificationStepResult(step_number=4, step_name="Market Price Benchmarking", status=CheckStatus.UNAVAILABLE, summary=str(e))
    all_flags.extend(step4.flags)
    results.append(step4)
    yield {"type": "step_complete", "step": 4, "result": step4.model_dump()}

    # Step 5
    yield {"type": "step_start", "step": 5, "total": 5, "name": "VIN Validation"}
    try:
        step5 = await verify_vin(invoice)
    except Exception as e:
        step5 = VerificationStepResult(step_number=5, step_name="VIN Validation", status=CheckStatus.UNAVAILABLE, summary=str(e))
    all_flags.extend(step5.flags)
    results.append(step5)
    yield {"type": "step_complete", "step": 5, "result": step5.model_dump()}

    # Final verdict
    verdict, reasoning, recommendation = _determine_verdict(all_flags, invoice)
    critical_count = len([f for f in all_flags if f.severity == FraudFlagSeverity.CRITICAL])

    report = FraudReport(
        session_id=session_id,
        document_name=document_name,
        analysis_date=datetime.now().isoformat(),
        invoice_data=invoice,
        verification_results=results,
        total_flags=len(all_flags),
        critical_flags=critical_count,
        verdict=verdict,
        verdict_reasoning=reasoning,
        recommendation=recommendation
    )
    yield {"type": "report", "report": report.model_dump()}
