import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# ✅ Base LLM Router URL (IMPORTANT: no /chat/completions)
API_URL = os.getenv(
    "API_URL",
    "https://quasarmarket.coforge.com/qag/llmrouter-api/v2"
)

API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

if not API_KEY:
    raise ValueError("API_KEY is not set")

CHAT_ENDPOINT = API_URL


# ---------------------------------------------------
# ✅ SYNC LLM CALL
# ---------------------------------------------------
def invoke_llm(
    prompt: str,
    system: str = "You are a fraud detection expert.",
    temperature: float = 0.1
) -> str:

    headers = {
        "X-API-KEY": API_KEY,   # ✅ correct header
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "max_tokens": 800,   # ✅ prevents empty outputs
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt[:4000]}  # ✅ limit input size
        ]
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(CHAT_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        if not content or not content.strip():
            raise ValueError("Empty response from LLM")

        return content


# ---------------------------------------------------
# ✅ ASYNC LLM CALL (used in your pipeline)
# ---------------------------------------------------
async def ainvoke_llm(
    prompt: str,
    system: str = "You are a fraud detection expert.",
    temperature: float = 0.1
) -> str:

    headers = {
        "X-API-KEY": API_KEY,   # ✅ FIXED (case-sensitive)
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "max_tokens": 800,   # ✅ avoids silent empty outputs
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt[:4000]}  # ✅ trim large input
        ]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(CHAT_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        if not content or not content.strip():
            raise ValueError("Empty response from LLM")

        return content