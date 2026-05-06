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
from ..services.langchain_tools import asearch_web
# from ..services.langchain_agent import run_agent_async, get_recent_tool_calls
from ..utils.guardrails import apply_guardrails
import html  # ✅ add this

import time
import logging
import httpx
import json
import html

from ..models.schemas import (
    InvoiceData, FraudFlag, FraudFlagSeverity, CheckStatus,
    ArithmeticCheckResult, VendorCheckResult, PriceCheckResult, VINCheckResult
)

from ..services.coforge_llm import invoke_llm, ainvoke_llm
from ..services.langchain_tools import asearch_web
from ..utils.guardrails import apply_guardrails

logger = logging.getLogger(__name__)
PRICE_THRESHOLD = float(os.getenv("FRAUD_PRICE_DEVIATION_THRESHOLD", "50"))

# =========================================================
# ✅ STEP 3: VENDOR VERIFICATION (FIXED ✅)
# =========================================================

async def verify_vendor(invoice: InvoiceData) -> VendorCheckResult:
    start = time.time()
    flags = []
    thought = "=== Step 3: Vendor Legitimacy Verification ===\n\n"

    vendor_name = html.unescape(invoice.vendor.name.value or "")
    vendor_address = invoice.vendor.address.value
    vendor_phone = invoice.vendor.phone.value

    if not vendor_name:
        return VendorCheckResult(
            step_number=3,
            step_name="Vendor Legitimacy",
            status=CheckStatus.MANUAL_REVIEW,
            summary="No vendor name",
            thought_process=thought,
            flags=[],
            duration_seconds=0
        )

    thought += f"Vendor: {vendor_name}\nAddress: {vendor_address}\nPhone: {vendor_phone}\n\n"

    # =========================
    # ✅ SEARCH
    # =========================
    web = await asearch_web(f"{vendor_name} address phone official location")
    web_context = web.get("summary", "")
    print("web-context--->"+web_context)

    if not web_context or "failed" in web_context.lower():
        web_context = "Search unavailable"

    thought += f"Web:\n{web_context}\n\n"

    # =========================
    # ✅ VALIDATION
    # =========================

    # Phone
    phone_valid = False
    if vendor_phone:
        digits = re.sub(r"\D", "", vendor_phone)
        if 10 <= len(digits) <= 12:
            phone_valid = True

    # Address
    address_valid = False
    if vendor_address and len(vendor_address.split()) >= 4:
        address_valid = True

    # Web signals
    web_lower = web_context.lower()

    negatives = ["complaint", "fraud", "scam", "worst"]
    positives = ["official", "franchise", "verified", "company", "locations"]

    neg_hits = sum(1 for w in negatives if w in web_lower)
    pos_hits = sum(1 for w in positives if w in web_lower)

    # =========================
    # ✅ SCORING
    # =========================
    score = 0

    if vendor_name:
        score += 1

    if phone_valid:
        score += 2
    else:
        thought += "⚠️ Phone weak\n"

    if address_valid:
        score += 2
    else:
        thought += "⚠️ Address weak\n"

    if "AAMCO" in vendor_name.upper():
        score += 3

    score += pos_hits
    score -= neg_hits

    thought += f"Signals: +{pos_hits} / -{neg_hits}\n"

    if score >= 5:
        rule = "likely_legitimate"
    elif score >= 2:
        rule = "needs_verification"
    else:
        rule = "suspicious"

    thought += f"Score: {score} → {rule}\n\n"

    # =========================
    # ✅ LLM FINAL
    # =========================
    prompt = f"""
Check vendor legitimacy.

Vendor: {vendor_name}
Context: {web_context}
Rule: {rule}

Return JSON:
{{
 "assessment":"",
 "confidence":0.0,
 "reasoning":"",
 "red_flags":[]
}}
"""

    try:
        response = await ainvoke_llm(prompt)
        cleaned = re.sub(r"```|```json", "", (response or "")).strip()

        if not cleaned:
            raise ValueError("Empty LLM response")

        result = json.loads(cleaned)

    except Exception:
        result = {
            "assessment": rule,
            "confidence": 0.5,
            "reasoning": "Fallback to rules",
            "red_flags": []
        }

    assessment = result.get("assessment", rule)

    thought += f"LLM: {assessment}\n"

    # =========================
    # ✅ FLAGS
    # =========================
    if assessment == "suspicious":
        flags.append(FraudFlag(
            check_name="Vendor Legitimacy",
            severity=FraudFlagSeverity.CRITICAL,
            message=f"Vendor suspicious: {vendor_name}",
            details=result.get("reasoning", "")
        ))

    # =========================
    # ✅ FINAL STATUS
    # =========================
    if assessment == "suspicious":
        status = CheckStatus.FAILED
        summary = f"⚠️ Suspicious vendor: {vendor_name}"
    elif assessment == "likely_legitimate":
        status = CheckStatus.PASSED
        summary = f"✓ Vendor appears legitimate: {vendor_name}"
    else:
        status = CheckStatus.MANUAL_REVIEW
        summary = "Vendor needs verification"

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
async def verify_prices(invoice: InvoiceData) -> PriceCheckResult:
    start = time.time()
    flags = []
    thought = "=== Step 4: Market Price Benchmarking ===\n\n"

    if not invoice.line_items:
        return PriceCheckResult(
            step_number=4,
            step_name="Market Price Benchmarking",
            status=CheckStatus.UNAVAILABLE,
            summary="No line items",
            thought_process=thought,
            flags=[],
            duration_seconds=0,
            price_comparisons=[]
        )

    price_comparisons = []

    try:
        for item in invoice.line_items[:10]:
            item_name = item.description
            listed_price = item.unit_price

            thought += f"\n--- Checking: {item_name} ---\n"

            # =========================
            # ✅ SEARCH (SERPER)
            # =========================
            query = f"{item_name} price cost {invoice.vehicle.make.value} {invoice.vehicle.model.value}"
            web = await asearch_web(query)
            web_context = web.get("summary", "")

            if not web_context:
                thought += "⚠️ No market data\n"
                continue

            thought += f"Market data:\n{web_context[:300]}\n"

            # =========================
            # ✅ REGEX PRICE EXTRACTION (FIX ✅)
            # =========================
            prices = re.findall(r"\$?\d{2,5}", web_context)

            numeric_prices = []
            for p in prices:
                try:
                    val = int(re.sub(r"\D", "", p))
                    if 20 <= val <= 10000:  # realistic bounds
                        numeric_prices.append(val)
                except:
                    pass

            if not numeric_prices:
                thought += "⚠️ No usable price found\n"
                continue

            # =========================
            # ✅ OUTLIER FILTER (IMPORTANT ✅)
            # =========================
            avg = sum(numeric_prices) / len(numeric_prices)

            filtered = [
                p for p in numeric_prices
                if 0.5 * avg <= p <= 2 * avg
            ]

            if filtered:
                market_low = min(filtered)
                market_high = max(filtered)
            else:
                market_low = min(numeric_prices)
                market_high = max(numeric_prices)

            # =========================
            # ✅ DEVIATION
            # =========================
            avg_market = (market_low + market_high) / 2
            deviation_pct = ((listed_price - avg_market) / avg_market) * 100 if avg_market else 0

            thought += f"Listed: ${listed_price:.2f} | Market: ${market_low}-{market_high}\n"
            thought += f"Deviation: {deviation_pct:.0f}%\n"

            assessment = "normal"

            if deviation_pct > PRICE_THRESHOLD:
                assessment = "overpriced"

                flags.append(FraudFlag(
                    check_name="Price Inflation",
                    severity=FraudFlagSeverity.CRITICAL if deviation_pct > 100 else FraudFlagSeverity.WARNING,
                    message=f"{item_name} overpriced by {deviation_pct:.0f}%",
                    details=f"Market range {market_low}-{market_high}, Listed {listed_price}"
                ))

                thought += "⚠️ OVERPRICED\n"
            else:
                thought += "✓ OK\n"

            price_comparisons.append({
                "item": item_name,
                "listed_price": listed_price,
                "market_low": market_low,
                "market_high": market_high,
                "deviation_pct": round(deviation_pct, 2),
                "assessment": assessment
            })

        # =========================
        # ✅ FINAL STATUS
        # =========================
        if not price_comparisons:
            status = CheckStatus.UNAVAILABLE
            summary = "No price data available"
        else:
            status = (
                CheckStatus.FAILED if any(f.severity == FraudFlagSeverity.CRITICAL for f in flags)
                else CheckStatus.WARNING if flags
                else CheckStatus.PASSED
            )

            summary = f"{len(flags)} pricing issue(s)" if flags else "✓ Prices reasonable"

    except Exception as e:
        logger.warning(f"Price check failed: {e}")
        thought += f"ERROR: {e}\n"
        status = CheckStatus.UNAVAILABLE
        summary = "Price check failed"

    thought = apply_guardrails(thought)

    return PriceCheckResult(
        step_number=4,
        step_name="Market Price Benchmarking",
        status=status,
        summary=summary,
        thought_process=thought,
        flags=flags,
        duration_seconds=round(time.time() - start, 2),
        price_comparisons=price_comparisons
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
