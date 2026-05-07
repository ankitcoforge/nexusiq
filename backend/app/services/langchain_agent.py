import asyncio
import json
import logging
import os
from typing import Optional, List, Any, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain.agents import create_agent
from langchain.tools import tool

from .coforge_llm import invoke_llm, ainvoke_llm
from .langchain_tools import search_web, price_search, vin_lookup, get_tool_calls

logger = logging.getLogger(__name__)


# =========================
# CHAT MODEL WRAPPER
# =========================
class CoforgeChatModel(BaseChatModel):
    """Custom ChatModel wrapper for Coforge Quasar Marketplace."""

    model_name: str = os.getenv("MODEL_NAME", "gpt-4o-mini")

    @property
    def _llm_type(self) -> str:
        return "coforge-chat"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Call Coforge LLM with formatted messages."""
        import httpx
        from dotenv import load_dotenv

        load_dotenv()

        api_url = os.getenv("API_URL", "https://quasarmarket.coforge.com/qag/llmrouter-api/v2")
        api_key = os.getenv("API_KEY")

        formatted = []
        for m in messages:
            if isinstance(m, SystemMessage):
                formatted.append({"role": "system", "content": m.content})
            elif isinstance(m, HumanMessage):
                formatted.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage):
                formatted.append({"role": "assistant", "content": m.content})
            else:
                formatted.append({"role": "user", "content": m.content})

        payload = {
            "model": self.model_name,
            "temperature": 0.1,
            "max_tokens": 800,
            "messages": formatted,
        }
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


# =========================
# TOOLS (using @tool decorator)
# =========================
@tool
def web_search(query: str) -> str:
    """Search the internet for vendor reviews, complaints, legitimacy, or general info."""
    result = search_web(query)
    return result.get("summary", "No results found")


@tool
def market_price_search(item: str) -> str:
    """Get market price estimates for an item or service."""
    result = price_search(item)
    if result.get("status") == "ok":
        return result.get("estimated_info", "No price data")
    return "No reliable market data found"


@tool
def vin_decode(vin: str) -> str:
    """Decode a Vehicle Identification Number (VIN) to get make, model, year."""
    result = vin_lookup(vin)
    if "error" in result:
        return f"VIN lookup failed: {result['error']}"
    return result.get("summary", "No VIN data")


# =========================
# HELPERS
# =========================
def _clean_json(text: str) -> str:
    return text.replace("```json", "").replace("```", "").strip()


def _safe_parse(text: str):
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {
        "assessment": "needs_verification",
        "confidence": 0.3,
        "reasoning": "Invalid or unparsable LLM output",
        "red_flags": ["Parsing failure"],
        "recommendation": "Manual review"
    }


# =========================
# AGENT CREATION (langchain 1.2.x)
# =========================
_AGENT = None

SYSTEM_PROMPT = """You are a fraud detection AI.

Use the available tools to search for vendor information, market prices, and VIN details when needed.

After gathering information, return ONLY valid JSON in this format:
{
 "assessment": "likely_legitimate|suspicious|needs_verification",
 "confidence": 0.0,
 "reasoning": "",
 "red_flags": [],
 "recommendation": ""
}
"""


def _make_agent():
    """Create the fraud detection agent using langchain create_agent."""
    llm = CoforgeChatModel()
    tools = [web_search, market_price_search, vin_decode]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        name="fraud_detection_agent",
    )
    return agent


# =========================
# EXECUTION
# =========================
def run_agent_sync(prompt: str):
    """Run the fraud detection agent synchronously."""
    global _AGENT
    _AGENT = _make_agent()

    try:
        result = _AGENT.invoke({"messages": [{"role": "user", "content": prompt}]})

        # Extract final AI message content
        messages = result.get("messages", [])
        raw_output = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                raw_output = msg.content
                break

        cleaned = _clean_json(raw_output)
        return _safe_parse(cleaned)

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return {
            "assessment": "error",
            "confidence": 0,
            "reasoning": f"Agent failure: {str(e)}",
            "red_flags": ["Agent crashed"],
            "recommendation": "Manual review"
        }


async def run_agent_async(prompt: str):
    """Run the fraud detection agent asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_agent_sync, prompt)


# =========================
# DEBUG
# =========================
def get_recent_tool_calls():
    return get_tool_calls()
