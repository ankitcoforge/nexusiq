import asyncio
from typing import Dict, Any, List
from cachetools import TTLCache
import threading
import httpx
import logging
import os

logger = logging.getLogger(__name__)

# =========================
# CACHE + OBSERVABILITY
# =========================

_cache = TTLCache(maxsize=512, ttl=3600)
_cache_lock = threading.Lock()

_tool_calls: List[Dict[str, Any]] = []
_tool_calls_lock = threading.Lock()


def _record_tool_call(tool_name: str, query: str, result_summary: str):
    entry = {"tool": tool_name, "query": query, "summary": result_summary or ""}
    with _tool_calls_lock:
        _tool_calls.append(entry)
        if len(_tool_calls) > 50:
            _tool_calls.pop(0)


def get_tool_calls() -> List[Dict[str, Any]]:
    with _tool_calls_lock:
        return list(_tool_calls)


def clear_tool_calls():
    with _tool_calls_lock:
        _tool_calls.clear()


# =========================
# ✅ SERPER SEARCH (REPLACES DDG)
# =========================

SERPER_URL = "https://google.serper.dev/search"
SERPER_API_KEY = "bbdcc94207f5d21170fc81a8a1b94ab432d592b7"


def _fetch_serper(query: str) -> str:
    try:
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {"q": query}

        with httpx.Client(timeout=10.0) as client:
            res = client.post(SERPER_URL, headers=headers, json=payload)
            data = res.json()

        results = data.get("organic", [])

        if not results:
            return "No reliable search results found"

        parts = []

        for r in results[:5]:
            if r.get("title"):
                parts.append(r["title"])
            if r.get("snippet"):
                parts.append(r["snippet"])

        return " | ".join(parts)

    except Exception as e:
        logger.warning(f"serper search failed: {e}")
        return "Search failed"


def search_web(query: str) -> Dict[str, str]:
    with _cache_lock:
        cached = _cache.get(query)

    if cached is not None:
        _record_tool_call("serper_search", query, cached[:400])
        return {"query": query, "summary": cached}

    txt = _fetch_serper(query)

    with _cache_lock:
        _cache[query] = txt

    _record_tool_call("serper_search", query, txt[:400])
    return {"query": query, "summary": txt}


async def asearch_web(query: str) -> Dict[str, str]:
    loop = asyncio.get_event_loop()
    txt = await loop.run_in_executor(None, lambda: search_web(query)["summary"])
    return {"query": query, "summary": txt}


# =========================
# ✅ PRICE SEARCH (USES SERPER NOW)
# =========================

def price_search(item: str, vehicle: str = "") -> Dict[str, Any]:
    query = f"{item} cost estimate price {vehicle}".strip()
    res = search_web(query)

    summary = res.get("summary", "")

    if not summary or "failed" in summary.lower():
        return {
            "item": item,
            "status": "unavailable",
            "message": "No reliable market data found"
        }

    return {
        "item": item,
        "status": "ok",
        "estimated_info": summary[:500],
        "confidence": 0.7
    }


async def aprice_search(item: str, vehicle: str = "") -> Dict[str, Any]:
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: price_search(item, vehicle)
    )


# =========================
# VIN LOOKUP (UNCHANGED ✅)
# =========================

def vin_lookup(vin: str) -> Dict[str, Any]:
    vin = vin.strip()

    if not vin:
        return {"vin": vin, "error": "empty"}

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
    cert_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "combined.pem")
    ssl_verify = cert_path if os.path.exists(cert_path) else False

    try:
        with httpx.Client(timeout=10.0, verify=ssl_verify) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("Results", [{}])[0]

        summary = (
            f"Make: {results.get('Make','')}, "
            f"Model: {results.get('Model','')}, "
            f"Year: {results.get('ModelYear','')}"
        )

        _record_tool_call("vin_lookup", vin, summary)

        return {"vin": vin, "summary": summary, "raw": results}

    except Exception as e:
        logger.warning(f"VIN lookup failed: {e}")
        _record_tool_call("vin_lookup", vin, f"error: {e}")
        return {"vin": vin, "error": str(e)}


async def avin_lookup(vin: str) -> Dict[str, Any]:
    vin = vin.strip()

    if not vin:
        return {"vin": vin, "error": "empty"}

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
    cert_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "combined.pem")
    ssl_verify = cert_path if os.path.exists(cert_path) else False

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=ssl_verify) as client:
            resp = await client.get(url)
            data = resp.json()

        results = data.get("Results", [{}])[0]

        summary = (
            f"Make: {results.get('Make','')}, "
            f"Model: {results.get('Model','')}, "
            f"Year: {results.get('ModelYear','')}"
        )

        _record_tool_call("vin_lookup", vin, summary)

        return {"vin": vin, "summary": summary, "raw": results}

    except Exception as e:
        logger.warning(f"VIN lookup failed: {e}")
        _record_tool_call("vin_lookup", vin, f"error: {e}")
        return {"vin": vin, "error": str(e)}
