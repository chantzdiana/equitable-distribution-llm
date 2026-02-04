"""
Extract equitable-distribution factors from divorce opinions.

Class-project scope:
- Single jurisdiction
- Small number of cases
- Exploratory, not predictive
"""
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



FACTOR_SCHEMA = [
    "duration_of_marriage",
    "earning_capacity",
    "contributions_to_marriage",
    "age_and_health",
    "misconduct"
]

def extract_factors(text: str) -> dict:
    """
    Returns a dictionary mapping factor names to booleans.
    """
    text = text.lower()

    return {
        "duration_of_marriage": "duration" in text or "length of the marriage" in text,
        "earning_capacity": "earning" in text or "income" in text,
        "contributions_to_marriage": "contribution" in text,
        "age_and_health": any( phrase in text for phrase in [" age ", " health ", " medical"]),

        "misconduct": "misconduct" in text or "fault" in text
    }

def extract_factors_llm(text: str) -> dict:
    """
    Uses an LLM to extract equitable-distribution factors from text.
    Returns the same schema as extract_factors().
    """
    schema = [
    "duration_of_marriage",
    "earning_capacity",
    "contributions_to_marriage",
    "age_and_health",
    "misconduct",
]

    prompt = f"""
    You are a system that extracts structured data.

    Return ONLY valid JSON.
    Do not include explanations, comments, or markdown.

    The JSON must have exactly these keys:
    {schema}

    Each value must be true or false.

    Text:
    {text}

    JSON:
    """

    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0,
)

    content = response.choices[0].message.content
    print("RAW LLM OUTPUT:", content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {key: False for key in schema}




  




