import os
import requests
from typing import Optional, List
from dotenv import load_dotenv
from langchain_core.language_models import LLM

# Load env once when module is imported
load_dotenv(override=True)


class CoforgeAIGardenLLM(LLM):
    temperature: float = 0.2
    max_tokens: int = 1024

    @property
    def _llm_type(self) -> str:
        return "coforge-ai-garden"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None
    ) -> str:

        payload = {
            "model": os.getenv("MODEL_NAME"),
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        if stop:
            payload["stop"] = stop

        response = requests.post(
            os.getenv("API_URL"),
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": os.getenv("API_KEY")
            },
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
