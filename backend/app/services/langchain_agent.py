import asyncio
from typing import Optional

try:
    from langchain.agents import initialize_agent, Tool, AgentType
    from langchain.llms.base import LLM
except Exception:
    initialize_agent = None
    Tool = None
    AgentType = None
    LLM = None

from .coforge_llm import invoke_llm, ainvoke_llm
from .langchain_tools import search_ddg, asearch_ddg, price_search, vin_lookup, get_tool_calls


class CoforgeLLM(LLM):
    """LangChain LLM wrapper that delegates to the existing coforge LLM functions."""

    @property
    def _llm_type(self) -> str:
        return "coforge"

    def _call(self, prompt: str, stop: Optional[list] = None) -> str:
        return invoke_llm(prompt)

    async def _acall(self, prompt: str, stop: Optional[list] = None) -> str:
        return await ainvoke_llm(prompt)


_AGENT = None


def _make_agent():
    if initialize_agent is None:
        raise RuntimeError("LangChain not available in environment")

    # create tools from the simple langchain_tools wrappers
    tools = [
        Tool(name="duckduckgo_search", func=search_ddg, description="Search DuckDuckGo and return a short summary."),
        Tool(name="price_search", func=price_search, description="Lookup market price information for an item."),
        Tool(name="vin_lookup", func=vin_lookup, description="Decode VIN and return make/model/year info."),
    ]

    llm = CoforgeLLM()
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=False)
    return agent


def run_agent_sync(prompt: str) -> str:
    global _AGENT
    if _AGENT is None:
        _AGENT = _make_agent()
    return _AGENT.run(prompt)


def get_recent_tool_calls():
    return get_tool_calls()


async def run_agent_async(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_agent_sync, prompt)
