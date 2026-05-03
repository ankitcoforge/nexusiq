import asyncio
from typing import Dict, Any, List
from cachetools import TTLCache
import threading
import httpx
import logging

logger = logging.getLogger(__name__)

try:
    from duckduckgo_search import ddg
except Exception:
    ddg = None


# simple TTL cache to avoid rate limits; 1 hour TTL, 512 entries
_ddg_cache = TTLCache(maxsize=512, ttl=3600)
_cache_lock = threading.Lock()

# record recent tool calls for observability
_tool_calls: List[Dict[str, Any]] = []
_tool_calls_lock = threading.Lock()


def _record_tool_call(tool_name: str, query: str, result_summary: str):
    entry = {"tool": tool_name, "query": query, "summary": (result_summary or "")}
    with _tool_calls_lock:
        _tool_calls.append(entry)
        # keep last 50 calls
        if len(_tool_calls) > 50:
            _tool_calls.pop(0)


def get_tool_calls() -> List[Dict[str, Any]]:
    with _tool_calls_lock:
        return list(_tool_calls)


def clear_tool_calls():
    with _tool_calls_lock:
        _tool_calls.clear()


def _fetch_ddg(query: str, max_results: int = 5) -> str:
    """
    Use the duckduckgo_search.ddg() helper to perform a query and return
    a short textual summary suitable for LLM consumption.
    """
    if ddg is None:
        raise RuntimeError("duckduckgo_search not installed")
    try:
        hits = ddg(query, max_results=max_results)
        if not hits:
            return ""
        # Build a compact summary: first result abstract + titles of next results
        parts = []
        first = hits[0]
        title = first.get("title") or first.get("text") or ""
        body = first.get("body") or first.get("snippet") or ""
        href = first.get("href") or first.get("url") or ""
        if title:
            parts.append(f"{title}")
        if body:
            parts.append(body)
        if href:
            parts.append(href)
        # include up to two additional titles for context
        for h in hits[1:3]:
            t = h.get("title") or h.get("text") or ""
            if t:
                parts.append(t)
        return "\n".join(parts)
    except Exception as e:
        logger.warning(f"duckduckgo_search query failed: {e}")
        return ""


def search_ddg(query: str) -> Dict[str, str]:
    """Synchronous wrapper returning a text summary from DuckDuckGo via LangChain with TTL cache."""
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
    # use executor to call the sync cached function
    txt = await loop.run_in_executor(None, lambda: search_ddg(query)["summary"])
    return {"query": query, "summary": txt}


def price_search(item: str, vehicle: str = "") -> Dict[str, Any]:
    q = f"average price {item} {vehicle}".strip()
    res = search_ddg(q)
    _record_tool_call("price_search", q, res.get("summary", ""))
    return {"query": q, "summary": res.get("summary", "")}


async def aprice_search(item: str, vehicle: str = "") -> Dict[str, Any]:
    q = f"average price {item} {vehicle}".strip()
    res = await asearch_ddg(q)
    _record_tool_call("price_search", q, res.get("summary", ""))
    return {"query": q, "summary": res.get("summary", "")}


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
        summary = f"Make: {results.get('Make','')}, Model: {results.get('Model','')}, Year: {results.get('ModelYear','')}"
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
        summary = f"Make: {results.get('Make','')}, Model: {results.get('Model','')}, Year: {results.get('ModelYear','')}"
        _record_tool_call("vin_lookup", vin, summary)
        return {"vin": vin, "summary": summary, "raw": results}
    except Exception as e:
        logger.warning(f"VIN lookup failed: {e}")
        _record_tool_call("vin_lookup", vin, f"error: {e}")
        return {"vin": vin, "error": str(e)}

