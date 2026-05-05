import asyncio
import json
from typing import Optional

from langchain.agents import create_structured_chat_agent, AgentExecutor
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.llms.base import LLM

from .coforge_llm import invoke_llm, ainvoke_llm
from .langchain_tools import (
    search_ddg,
    price_search,
    vin_lookup,
    get_tool_calls
)

# =========================
# LLM WRAPPER
# =========================

class CoforgeLLM(LLM):
    @property
    def _llm_type(self) -> str:
        return "coforge"

    def _call(self, prompt: str, stop: Optional[list] = None) -> str:
        return invoke_llm(prompt)

    async def _acall(self, prompt: str, stop: Optional[list] = None) -> str:
        return await ainvoke_llm(prompt)


_AGENT_EXECUTOR = None


# =========================
# SAFE HELPERS
# =========================

def _clean_json(text: str) -> str:
    """Strip markdown wrappers."""
    return text.replace("```json", "").replace("```", "").strip()


def _safe_parse(text: str):
    """Never break the pipeline — always return JSON."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {
            "assessment": "needs_verification",
            "confidence": 0.5,
            "reasoning": "Non-dict JSON returned",
            "red_flags": [],
            "recommendation": "Manual review"
        }
    except Exception:
        return {
            "assessment": "error",
            "confidence": 0,
            "reasoning": "Invalid JSON from LLM",
            "red_flags": [],
            "recommendation": "Retry"
        }


# =========================
# AGENT CREATION (FINAL FIX)
# =========================

def _make_agent():
    tools = [
        Tool.from_function(
            name="duckduckgo_search",
            func=search_ddg,
            description="Search vendor reviews, complaints, legitimacy"
        ),
        Tool.from_function(
            name="price_search",
            func=price_search,
            description="Get market price estimates"
        ),
        Tool.from_function(
            name="vin_lookup",
            func=vin_lookup,
            description="Decode VIN details"
        ),
    ]

    llm = CoforgeLLM()

    # ✅ SIMPLE STRING PROMPT (NO ChatPromptTemplate)
    prompt = """You are a fraud detection AI agent.

You can use tools if needed.

Your task:
- Analyze vendor legitimacy
- Return ONLY valid JSON

Output format:
{
 "assessment": "likely_legitimate|suspicious|needs_verification",
 "confidence": 0.0,
 "reasoning": "",
 "red_flags": [],
 "recommendation": ""
}
"""

    # ✅ Wrap into standard agent pipeline
    agent = create_structured_chat_agent(
        llm=llm,
        tools=tools,
        prompt=prompt   # ✅ just string now
    )

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        handle_parsing_errors=True,
        verbose=False,
        max_iterations=3
    )

    return executor
# =========================
# AGENT EXECUTION
# =========================

def run_agent_sync(prompt: str):
    global _AGENT_EXECUTOR

    if _AGENT_EXECUTOR is None:
        _AGENT_EXECUTOR = _make_agent()

    try:
        response = _AGENT_EXECUTOR.invoke({"input": prompt})
        raw_output = response.get("output", "")

        cleaned = _clean_json(raw_output)
        parsed = _safe_parse(cleaned)

        return parsed

    except Exception as e:
        return {
            "assessment": "error",
            "confidence": 0,
            "reasoning": f"Agent failure: {str(e)}",
            "red_flags": ["Agent crashed"],
            "recommendation": "Manual review"
        }


async def run_agent_async(prompt: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_agent_sync, prompt)


# =========================
# DEBUG / OBSERVABILITY
# =========================

def get_recent_tool_calls():
    return get_tool_calls()