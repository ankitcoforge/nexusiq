from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os

# Load environment variables from .env
load_dotenv()

def main():
    api_key = os.getenv("API_KEY")
    api_url = os.getenv("API_URL")
    model   = os.getenv("MODEL_NAME", "gpt-5-mini")

    # Quasar Marketplace uses x-api-key header (not Bearer token)
    llm = ChatOpenAI(
        model=model,
        temperature=0.7,
        openai_api_key="placeholder",   # required by SDK but overridden by default_headers
        openai_api_base=api_url,
        default_headers={"x-api-key": api_key}
    )

    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello! What can LangChain help me build?")
    ]

    print(f"🚀 Connecting to Quasar Marketplace...")
    print(f"   Model : {model}")
    print(f"   URL   : {api_url}\n")

    response = llm.invoke(messages)
    print("✅ Response:", response.content)

if __name__ == "__main__":
    main()
