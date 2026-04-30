import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "https://quasarmarket.coforge.com/qag/llmrouter-api/v2")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
CHAT_ENDPOINT = f"{API_URL}/chat/completions"

def invoke_llm(prompt: str, system: str = "You are a fraud detection expert.", temperature: float = 0.1) -> str:
    """Synchronous LLM call to Quasar marketplace using x-api-key auth."""
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(CHAT_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def ainvoke_llm(prompt: str, system: str = "You are a fraud detection expert.", temperature: float = 0.1) -> str:
    """Async LLM call to Quasar marketplace."""
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(CHAT_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
