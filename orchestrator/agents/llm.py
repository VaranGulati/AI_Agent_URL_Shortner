import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

def get_llm():
    # If the user has an API key set, use the real LLM. 
    # Otherwise, we will use a mock mode for testing the DAG.
    api_key = os.environ.get("QROQ_API_KEY")
    base_url = os.environ.get("QROQ_BASE_URL") # Adjust if different
    
    if api_key:
        return ChatOpenAI(
            model="openai/gpt-oss-120b",
            api_key=api_key,
            base_url=base_url,
            max_retries=2
        )
    return None

import time

def invoke_agent(system_prompt: str, user_prompt: str, mock_response: str) -> str:
    """
    Invokes the LLM. If no API key is provided, returns the mock_response 
    to preserve the 30 requests/day limit during development.
    Includes rate-limit retry logic with exponential backoff.
    """
    llm = get_llm()
    if llm:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        max_rate_limit_retries = 4
        backoff_seconds = 10.0
        
        for attempt in range(max_rate_limit_retries):
            try:
                response = llm.invoke(messages)
                return response.content
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "rate_limit" in err_str or "429" in err_str
                
                if is_rate_limit and attempt < max_rate_limit_retries - 1:
                    print(f"\n[Rate Limit] 429 hit. Sleeping for {backoff_seconds}s before retry... (Attempt {attempt + 1}/{max_rate_limit_retries})")
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2
                else:
                    raise e
    else:
        print("[MOCK LLM] Returning mock response to save API quota.")
        return mock_response
