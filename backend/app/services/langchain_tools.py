import asyncio
from typing import Dict, Any, List
from cachetools import TTLCache
import threading
import httpx
import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# =========================
# CACHE + OBSERVABILITY
# =========================

_ddg_cache = TTLCache(maxsize=512, ttl=3600)
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
# DUCKDUCKGO SEARCH
# =========================

def _fetch_ddg(query: str, max_results: int = 5) -> str:
    try:
        with DDGS(headers={"User-Agent": "Mozilla/5.0"}) as ddgs:
            hits = list(ddgs.text(query, max_results=max_results))

        if not hits:
            return "No useful search results found"

        parts = []

        first = hits[0]
        if first.get("title"):
            parts.append(first["title"])
        if first.get("body"):
            parts.append(first["body"])
        if first.get("href"):
            parts.append(first["href"])

        for h in hits[1:3]:
            if h.get("title"):
                parts.append(h["title"])

        return " | ".join(parts)

    except Exception as e:
        logger.warning(f"duckduckgo_search failed: {e}")
        return "Search failed"


def search_ddg(query: str) -> Dict[str, str]:
    with _cache_lock:
        cached = _ddg_cache.get(query)

    if cached is not None:
        _record_tool_call("duckduckgo_search", query, cached[:400])
        return {"query": query, "summary": cached}

    txt = _fetch_ddg(query)

    with _cache_lock:
        _ddg_cache[query] = txt

    _record_tool_call("duckduckgo_search", query, txt[:400])
    return {"query": query, "summary": txt}


async def asearch_ddg(query: str) -> Dict[str, str]:
    loop = asyncio.get_event_loop()
    txt = await loop.run_in_executor(None, lambda: search_ddg(query)["summary"])
    return {"query": query, "summary": txt}


# =========================
# PRICE SEARCH (FIXED ✅)
# =========================

def price_search(item: str, vehicle: str = "") -> Dict[str, Any]:
    query = f"{item} cost estimate price {vehicle}".strip()
    res = search_ddg(query)

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
        "confidence": 0.6
    }


async def aprice_search(item: str, vehicle: str = "") -> Dict[str, Any]:
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: price_search(item, vehicle)
    )


# =========================
# OPTIONAL: BATCH PRICE BENCHMARK
# =========================

def price_benchmark(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []

    for item in items:
        name = item.get("name", "")
        vehicle = item.get("vehicle", "")

        res = price_search(name, vehicle)

        results.append({
            "item": name,
            "input_price": item.get("price"),
            "market_data": res
        })

    return results


# =========================
# VIN LOOKUP
# =========================

def vin_lookup(vin: str) -> Dict[str, Any]:
    vin = vin.strip()

    if not vin:
        return {"vin": vin, "error": "empty"}

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"

    try:
        with httpx.Client(timeout=10.0) as client:
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

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
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