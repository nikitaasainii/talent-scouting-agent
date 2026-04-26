import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.3,
    max_tokens: int = 1000
) -> str:
    # Updated active Groq models. 
    # Ordered by token efficiency and rate-limit friendliness
    models = [
        "llama-3.1-8b-instant",       # Primary: Fast, high limit, great for JSON parsing
        "openai/gpt-oss-20b",         # Fallback 1: Extremely fast, stable
        "llama-3.3-70b-versatile"     # Fallback 2: Last resort due to 100k TPD limit
    ]
    
    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e).lower()
            if "rate_limit" in error_msg or "429" in error_msg:
                print(f"  ⚠ Rate limit hit on {model}, falling back to next...")
                time.sleep(2)
                continue
            # Catch other potential API errors (e.g., service down) so the loop continues
            print(f"  ⚠ Error with {model}: {e}")
            continue
            
    raise Exception("All models exhausted or rate limited. Wait a few minutes and retry.")
import json
import re

def parse_llm_json(raw_response: str) -> dict:
    """Extracts and parses the first JSON object from a messy LLM response."""
    try:
        # First, try a direct parse just in case it's already perfect
        return json.loads(raw_response)
    except json.JSONDecodeError:
        # If it fails, use regex to find the outermost curly braces
        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if match:
            clean_json_str = match.group(0)
            return json.loads(clean_json_str)
        else:
            raise ValueError(f"Could not extract JSON from LLM output: {raw_response}")