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
    "income_and_property_at_marriage_and_divorce",   # §236(B)(5)(d)(1)
    "duration_of_marriage_age_and_health",           # §236(B)(5)(d)(2)
    "custodial_parent_housing_needs",                 # §236(B)(5)(d)(3)
    "loss_of_inheritance_or_pension",                 # §236(B)(5)(d)(4)
    "loss_of_health_insurance",                       # §236(B)(5)(d)(5)
    "maintenance_award",                              # §236(B)(5)(d)(6)
    "contributions_to_marital_property_and_career",  # §236(B)(5)(d)(7)
    "liquidity_of_assets",                            # §236(B)(5)(d)(8)
    "future_financial_circumstances",                 # §236(B)(5)(d)(9)
    "valuation_difficulty_and_business_assets",      # §236(B)(5)(d)(10)
    "tax_consequences",                               # §236(B)(5)(d)(11)
    "wasteful_dissipation_of_assets",                 # §236(B)(5)(d)(12)
    "improper_transfers_or_encumbrances",             # §236(B)(5)(d)(13)
    "domestic_violence",                              # §236(B)(5)(d)(14)
    "companion_animal_best_interests",                # §236(B)(5)(d)(15)
    "other_just_and_proper_factors",                  # §236(B)(5)(d)(16)
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
    "income_and_property_at_marriage_and_divorce",   # §236(B)(5)(d)(1)
    "duration_of_marriage_age_and_health",           # §236(B)(5)(d)(2)
    "custodial_parent_housing_needs",                 # §236(B)(5)(d)(3)
    "loss_of_inheritance_or_pension",                 # §236(B)(5)(d)(4)
    "loss_of_health_insurance",                       # §236(B)(5)(d)(5)
    "maintenance_award",                              # §236(B)(5)(d)(6)
    "contributions_to_marital_property_and_career",  # §236(B)(5)(d)(7)
    "liquidity_of_assets",                            # §236(B)(5)(d)(8)
    "future_financial_circumstances",                 # §236(B)(5)(d)(9)
    "valuation_difficulty_and_business_assets",      # §236(B)(5)(d)(10)
    "tax_consequences",                               # §236(B)(5)(d)(11)
    "wasteful_dissipation_of_assets",                 # §236(B)(5)(d)(12)
    "improper_transfers_or_encumbrances",             # §236(B)(5)(d)(13)
    "domestic_violence",                              # §236(B)(5)(d)(14)
    "companion_animal_best_interests",                # §236(B)(5)(d)(15)
    "other_just_and_proper_factors",                  # §236(B)(5)(d)(16)

]

    # prompt = f"""
    # You are a system that extracts structured data.

    # Return ONLY valid JSON.
    # Do not include explanations, comments, or markdown.

    # The JSON must have exactly these keys:
    # {schema}

    # Each value must be true or false.

    # Text:
    # {text}

    # JSON:
    # """
    prompt = f"""
    You are analyzing a divorce opinion applying New York equitable distribution law.

    TASK:

    1. Identify which statutory factors are meaningfully discussed in the court's reasoning.
    2. Then identify which factor or factors the court appears to rely on MOST HEAVILY in reaching its decision.
    - These are the factors that seem decisive, emphasized, or outcome-driving.
    - There may be one or multiple such factors.
    - Do NOT guess — only include factors clearly emphasized.

    Return ONLY valid JSON in the following format:

    {{
    "mentioned": {{
        "FACTOR_1": true/false,
        "FACTOR_2": true/false,
        ...
    }},
    "most_weighted": ["FACTOR_NAME", ...]
    }}

    Use ONLY the following factors:

    {schema}

    Case text:
    {text}
    """


    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0,
)

    content = response.choices[0].message.content
    print("RAW LLM OUTPUT:", content)

    # try:
    #     return json.loads(content)
    # except json.JSONDecodeError:
    #     return {key: False for key in schema}

    # try:
    #     parsed = json.loads(content)
    # except json.JSONDecodeError:
    #     return {
    #         "mentioned": {factor: False for factor in FACTOR_SCHEMA},
    #         "most_weighted": []
    #     }
    clean = content.strip()

    # Remove markdown code fences if present
    # if clean.startswith("```"):
    #     clean = clean.split("```", 1)[1]
    #     clean = clean.rsplit("```", 1)[0].strip()

    # clean = content.strip()

# Remove markdown code fences (``` or ```json)
    if clean.startswith("```"):
        clean = clean.split("```", 1)[1]        # remove first ```
        clean = clean.lstrip("json").strip()    # remove optional 'json'
        if "```" in clean:
            clean = clean.rsplit("```", 1)[0]   # remove closing ```
        clean = clean.strip()


    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        return {
            "mentioned": {factor: False for factor in FACTOR_SCHEMA},
            "most_weighted": []
        }


    # Safety normalization
    mentioned = parsed.get("mentioned", {})
    most_weighted = parsed.get("most_weighted", [])

    # Ensure all schema keys exist
    for factor in FACTOR_SCHEMA:
        mentioned.setdefault(factor, False)

    # ---- Confidence scoring ----
    num_weighted = len(most_weighted)

    if num_weighted == 1:
        confidence = "high"
    elif num_weighted == 2:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "mentioned": mentioned,
        "most_weighted": most_weighted,
        "confidence": confidence
    }



  




