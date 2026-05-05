import os
import re
import time
import logging
import httpx
from ..models.schemas import (
    InvoiceData, FraudFlag, FraudFlagSeverity, CheckStatus,
    ArithmeticCheckResult, VendorCheckResult, PriceCheckResult, VINCheckResult
)
from ..services.coforge_llm import invoke_llm, ainvoke_llm
from ..services.langchain_tools import asearch_ddg
from ..services.langchain_agent import run_agent_async, get_recent_tool_calls
from ..utils.guardrails import apply_guardrails

logger = logging.getLogger(__name__)
PRICE_THRESHOLD = float(os.getenv("FRAUD_PRICE_DEVIATION_THRESHOLD", "50"))

def verify_arithmetic(invoice: InvoiceData) -> ArithmeticCheckResult:
    start = time.time()
    flags = []
    thought = "=== Step 2: Arithmetic & Tax Validation ===\n\n"
    line_item_checks = []
    computed_subtotal = 0.0

    thought += f"Checking {len(invoice.line_items)} line items...\n"
    for item in invoice.line_items:
        expected = round(item.quantity * item.unit_price, 2)
        diff = abs(expected - item.total)
        check = {
            "description": item.description,
            "qty": item.quantity,
            "unit_price": item.unit_price,
            "listed_total": item.total,
            "computed_total": expected,
            "diff": diff,
            "status": "OK" if diff <= 0.01 else "MISMATCH"
        }
        line_item_checks.append(check)
        computed_subtotal += expected
        thought += f"  • {item.description}: {item.quantity} × ${item.unit_price:.2f} = ${expected:.2f} (listed: ${item.total:.2f})"
        if diff > 0.01:
            thought += f" ⚠️ MISMATCH: ${diff:.2f}\n"
            flags.append(FraudFlag(
                check_name="Line Item Arithmetic",
                severity=FraudFlagSeverity.CRITICAL,
                message=f"Line item mismatch: '{item.description}'",
                details=f"Expected ${expected:.2f}, listed ${item.total:.2f}, diff ${diff:.2f}"
            ))
        else:
            thought += " ✓\n"

    computed_subtotal = round(computed_subtotal, 2)
    computed_tax = round(computed_subtotal * (invoice.tax_rate / 100), 2) if invoice.tax_rate else invoice.tax_amount
    computed_total = round(computed_subtotal + computed_tax, 2)
    total_diff = abs(computed_total - invoice.total)

    thought += f"\nComputed subtotal: ${computed_subtotal:.2f} (invoice: ${invoice.subtotal:.2f})\n"
    thought += f"Computed tax ({invoice.tax_rate}%): ${computed_tax:.2f} (invoice: ${invoice.tax_amount:.2f})\n"
    thought += f"Computed total: ${computed_total:.2f} (invoice: ${invoice.total:.2f})\n"
    thought += f"Total difference: ${total_diff:.2f}\n"

    if total_diff > 1.00:
        flags.append(FraudFlag(
            check_name="Grand Total Mismatch",
            severity=FraudFlagSeverity.CRITICAL,
            message=f"Grand total mismatch: ${total_diff:.2f} difference",
            details=f"Computed ${computed_total:.2f} vs invoice ${invoice.total:.2f}"
        ))
        status = CheckStatus.FAILED
        summary = f"⚠️ CRITICAL: Grand total mismatch of ${total_diff:.2f}"
    elif total_diff > 0.05:
        flags.append(FraudFlag(
            check_name="Total Variance",
            severity=FraudFlagSeverity.WARNING,
            message=f"Total variance: ${total_diff:.2f}",
            details="Minor discrepancy may indicate rounding manipulation"
        ))
        status = CheckStatus.WARNING
        summary = f"Minor variance of ${total_diff:.2f} detected"
    elif flags:
        status = CheckStatus.FAILED
        summary = f"{len(flags)} arithmetic flag(s) found"
    else:
        status = CheckStatus.PASSED
        summary = "✓ Arithmetic Verified — All calculations correct"

    try:
        llm_prompt = f"""Analyze this invoice arithmetic check for fraud indicators:
Computed subtotal: ${computed_subtotal}, Tax: ${computed_tax}, Total: ${computed_total}
Invoice total: ${invoice.total}, Difference: ${total_diff}
Line items: {len(invoice.line_items)}
Flags found: {len(flags)}

Return JSON: {{"analysis": "", "anomalies_found": false, "risk_level": "low", "recommendation": ""}}"""
        llm_response = invoke_llm(llm_prompt)
        thought += f"\nLLM Analysis: {llm_response[:300]}\n"
    except Exception as e:
        thought += f"\nLLM analysis skipped: {e}\n"

    thought = apply_guardrails(thought)
    return ArithmeticCheckResult(
        step_number=2, step_name="Arithmetic & Tax Validation",
        status=status, summary=summary, thought_process=thought,
        flags=flags, duration_seconds=round(time.time() - start, 2),
        line_item_checks=line_item_checks,
        computed_subtotal=computed_subtotal, computed_tax=computed_tax,
        computed_total=computed_total, invoice_total=invoice.total
    )

async def verify_vendor(invoice: InvoiceData) -> VendorCheckResult:
    start = time.time()
    flags = []
    thought = "=== Step 3: Vendor Legitimacy Verification ===\n\n"

    vendor_name = invoice.vendor.name.value
    vendor_address = invoice.vendor.address.value
    vendor_phone = invoice.vendor.phone.value

    if not vendor_name:
        thought += "No vendor name extracted — cannot verify.\n"
        thought = apply_guardrails(thought)
        return VendorCheckResult(
            step_number=3,
            step_name="Vendor Legitimacy",
            status=CheckStatus.MANUAL_REVIEW,
            summary="No vendor name — manual review required",
            thought_process=thought,
            flags=flags,
            duration_seconds=round(time.time() - start, 2)
        )

    thought += f"Vendor: {vendor_name}\nAddress: {vendor_address}\nPhone: {vendor_phone}\n\n"

    try:
        # ✅ IMPROVED SEARCH
        try:
            ddg = await asearch_ddg(
                f"{vendor_name} reviews complaints business legitimacy"
            )
            web_context = ddg.get("summary", "")

            if web_context:
                thought += f"Web search summary:\n{web_context}\n\n"
        except Exception as e:
            thought += f"Web search failed: {e}\n\n"

        prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a fraud detection assistant.

You must:
- Use tools when required
- Return ONLY valid JSON

Available tools:
{tools}

Tool names:
{tool_names}

Output format:
{{
 "assessment": "likely_legitimate|suspicious|needs_verification",
 "confidence": 0.0,
 "reasoning": "",
 "red_flags": [],
 "recommendation": ""
}}
"""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

        # ✅ IMPORTANT: agent already returns dict
        response = await run_agent_async(prompt)

        # ✅ SAFE HANDLING
        if isinstance(response, dict):
            result = response
        else:
            logger.warning(f"Invalid agent response: {response}")
            result = {
                "assessment": "needs_verification",
                "confidence": 0.3,
                "reasoning": "Invalid agent response",
                "red_flags": ["Agent failure"],
                "recommendation": "Manual review"
            }

        thought += f"LLM Assessment: {result.get('assessment')}\n"
        thought += f"Reasoning: {result.get('reasoning')}\n"

        if result.get("red_flags"):
            thought += f"Red flags: {', '.join(result['red_flags'])}\n"

        assessment = result.get("assessment", "needs_verification")

        if assessment == "suspicious":
            flags.append(FraudFlag(
                check_name="Vendor Legitimacy",
                severity=FraudFlagSeverity.CRITICAL,
                message=f"Vendor suspicious: {vendor_name}",
                details=result.get("reasoning", "")
            ))
            status = CheckStatus.FAILED
            summary = f"⚠️ SUSPICIOUS VENDOR: {vendor_name}"

        elif assessment == "needs_verification":
            status = CheckStatus.MANUAL_REVIEW
            summary = f"Vendor needs verification"

        else:
            status = CheckStatus.PASSED
            summary = f"✓ Vendor appears legitimate: {vendor_name}"

        # ✅ TOOL LOGS (safe)
        try:
            for tc in get_recent_tool_calls():
                thought += f"- {tc['tool']} → {tc['query']}\n"
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"Vendor verification failed: {e}")
        thought += f"Verification unavailable: {e}\n"
        status = CheckStatus.MANUAL_REVIEW
        summary = "Vendor verification unavailable"

    thought = apply_guardrails(thought)

    return VendorCheckResult(
        step_number=3,
        step_name="Vendor Legitimacy",
        status=status,
        summary=summary,
        thought_process=thought,
        flags=flags,
        duration_seconds=round(time.time() - start, 2),
        vendor_found=(status == CheckStatus.PASSED)
    )
async def verify_prices(invoice: InvoiceData) -> PriceCheckResult:
    start = time.time()
    flags = []
    thought = "=== Step 4: Market Price Benchmarking ===\n\n"

    if not invoice.line_items:
        thought += "No line items to check.\n"
        thought = apply_guardrails(thought)
        return PriceCheckResult(
            step_number=4,
            step_name="Market Price Benchmarking",
            status=CheckStatus.UNAVAILABLE,
            summary="No line items to analyze",
            thought_process=thought,
            flags=flags,
            duration_seconds=round(time.time() - start, 2)
        )

    items_text = "\n".join([
        f"- {item.description}: ${item.unit_price:.2f} x {item.quantity}"
        for item in invoice.line_items[:10]
    ])

    thought += f"Checking {len(invoice.line_items)} line items against market rates:\n{items_text}\n\n"

    price_comparisons = []

    try:
        prompt = f"""
You are an auto repair pricing expert.

Return ONLY valid JSON (no explanation, no markdown).

Format:
[
  {{
    "item": "string",
    "listed_price": 0.0,
    "market_low": 0.0,
    "market_high": 0.0,
    "assessment": "normal|overpriced|underpriced",
    "deviation_pct": 0.0
  }}
]

Line items:
{items_text}

Vehicle: {invoice.vehicle.make.value} {invoice.vehicle.model.value} {invoice.vehicle.year.value}
"""

        response = await ainvoke_llm(prompt)

        import json, re as re2
        cleaned = re2.sub(r"```(?:json)?", "", (response or "")).strip()

        # ✅ SAFE JSON PARSE
        try:
            parsed = json.loads(cleaned)

            if isinstance(parsed, list):
                price_comparisons = parsed
            else:
                raise ValueError("Invalid structure (not list)")

        except Exception:
            logger.warning(f"Invalid price JSON: {cleaned[:200]}")
            price_comparisons = []

        # ✅ PROCESS RESULTS
        for comp in price_comparisons:
            deviation = abs(comp.get("deviation_pct", 0))

            thought += f"  • {comp.get('item', '')}: ${comp.get('listed_price', 0):.2f} "
            thought += f"(market: ${comp.get('market_low', 0):.2f}-${comp.get('market_high', 0):.2f})"

            if comp.get("assessment") == "overpriced" and deviation > PRICE_THRESHOLD:
                thought += f" ⚠️ OVERPRICED by {deviation:.0f}%\n"

                flags.append(FraudFlag(
                    check_name="Price Inflation",
                    severity=FraudFlagSeverity.WARNING if deviation < 100 else FraudFlagSeverity.CRITICAL,
                    message=f"Overpriced item: {comp.get('item', '')} ({deviation:.0f}% above market)",
                    details=f"Listed ${comp.get('listed_price', 0):.2f}, market range ${comp.get('market_low', 0):.2f}-${comp.get('market_high', 0):.2f}"
                ))
            else:
                thought += " ✓\n"

        # ✅ FINAL STATUS
        if not price_comparisons:
            status = CheckStatus.UNAVAILABLE
            summary = "Price benchmarking unavailable (invalid LLM output)"
        else:
            status = (
                CheckStatus.FAILED if any(f.severity == FraudFlagSeverity.CRITICAL for f in flags)
                else CheckStatus.WARNING if flags
                else CheckStatus.PASSED
            )

            summary = f"{len(flags)} pricing flag(s) found" if flags else "✓ Prices within market range"

    except Exception as e:
        logger.warning(f"Price check failed: {e}")
        thought += f"Price check unavailable: {e}\n"
        status = CheckStatus.UNAVAILABLE
        summary = "Price benchmarking unavailable"

    thought = apply_guardrails(thought)

    return PriceCheckResult(
        step_number=4,
        step_name="Market Price Benchmarking",
        status=status,
        summary=summary,
        thought_process=thought,
        flags=flags,
        duration_seconds=round(time.time() - start, 2),
        price_comparisons=price_comparisons if isinstance(price_comparisons, list) else []
    )

async def verify_vin(invoice: InvoiceData) -> VINCheckResult:
    start = time.time()
    flags = []
    thought = "=== Step 5: VIN Validation ===\n\n"
    vin = invoice.vehicle.vin.value.strip().upper()

    if not vin:
        thought += "No VIN found in invoice.\n"
        thought = apply_guardrails(thought)
        return VINCheckResult(
            step_number=5, step_name="VIN Validation",
            status=CheckStatus.MANUAL_REVIEW,
            summary="No VIN found — manual verification required",
            thought_process=thought, flags=flags,
            duration_seconds=round(time.time() - start, 2)
        )

    thought += f"VIN to validate: {vin}\n"
    decoded_year = decoded_make = decoded_model = ""
    vin_valid = False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json")
            data = resp.json()
            results = data.get("Results", [{}])[0]
            decoded_make = results.get("Make", "")
            decoded_model = results.get("Model", "")
            decoded_year = results.get("ModelYear", "")
            error_code = results.get("ErrorCode", "0")
            vin_valid = error_code == "0"

            thought += f"NHTSA Decode: {decoded_year} {decoded_make} {decoded_model}\n"
            thought += f"Invoice vehicle: {invoice.vehicle.year.value} {invoice.vehicle.make.value} {invoice.vehicle.model.value}\n"

            if not vin_valid:
                flags.append(FraudFlag(
                    check_name="VIN Invalid",
                    severity=FraudFlagSeverity.CRITICAL,
                    message=f"VIN {vin} is invalid per NHTSA",
                    details=f"Error code: {error_code}"
                ))
                status = CheckStatus.FAILED
                summary = f"⚠️ INVALID VIN: {vin}"
            else:
                # Check make/model match
                inv_make = invoice.vehicle.make.value.upper()
                if decoded_make and inv_make and decoded_make not in inv_make and inv_make not in decoded_make:
                    flags.append(FraudFlag(
                        check_name="VIN Make Mismatch",
                        severity=FraudFlagSeverity.WARNING,
                        message=f"VIN decodes to {decoded_make}, invoice says {invoice.vehicle.make.value}",
                        details="Vehicle make on invoice does not match VIN"
                    ))
                    status = CheckStatus.WARNING
                    summary = f"⚠️ VIN make mismatch: {decoded_make} vs {invoice.vehicle.make.value}"
                else:
                    status = CheckStatus.PASSED
                    summary = f"✓ VIN Valid: {decoded_year} {decoded_make} {decoded_model}"

    except Exception as e:
        logger.warning(f"VIN check failed: {e}")
        thought += f"VIN validation unavailable: {e}\n"
        status = CheckStatus.UNAVAILABLE
        summary = "VIN validation unavailable"

    thought = apply_guardrails(thought)
    return VINCheckResult(
        step_number=5, step_name="VIN Validation",
        status=status, summary=summary, thought_process=thought,
        flags=flags, duration_seconds=round(time.time() - start, 2),
        vin_valid=vin_valid, decoded_year=decoded_year,
        decoded_make=decoded_make, decoded_model=decoded_model
    )
