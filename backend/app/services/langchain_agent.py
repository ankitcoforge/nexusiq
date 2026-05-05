import asyncio
import json
from typing import Optional

from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.llms.base import LLM

from .coforge_llm import invoke_llm, ainvoke_llm
from .langchain_tools import search_ddg, price_search, vin_lookup, get_tool_calls


# =========================
# LLM WRAPPER
# =========================
class CoforgeLLM(LLM):
    @property
    def _llm_type(self) -> str:
        return "coforge"

    def _call(self, prompt: str, stop: Optional[list] = None,**kwargs) -> str:
        return invoke_llm(prompt)

    async def _acall(self, prompt: str, stop: Optional[list] = None,**kwargs) -> str:
        return await ainvoke_llm(prompt)


_AGENT_EXECUTOR = None


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
# AGENT CREATION ✅ FINAL
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

    # ✅ FIXED PROMPT (ESCAPED JSON ✅)
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a fraud detection AI.

Use tools when needed.

Return ONLY valid JSON.

Format:
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

    agent = create_openai_tools_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )

    return AgentExecutor(
        agent=agent,
        tools=tools,
        handle_parsing_errors=True,
        verbose=False,
        max_iterations=3
    )


# =========================
# EXECUTION ✅ FORCE RELOAD
# =========================
def run_agent_sync(prompt: str):
    global _AGENT_EXECUTOR

    # ✅ IMPORTANT: prevent cached broken agent
    _AGENT_EXECUTOR = _make_agent()

    try:
        response = _AGENT_EXECUTOR.invoke({"input": prompt})
        raw_output = response.get("output", "")

        cleaned = _clean_json(raw_output)
        return _safe_parse(cleaned)

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
# DEBUG
# =========================
def get_recent_tool_calls():
    return get_tool_calls()
