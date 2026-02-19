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

def chunk_text(text, chunk_size=2500):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i + chunk_size])


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

    
    prompt = f"""
    You are analyzing a judicial divorce opinion applying New York equitable distribution law.

    Your task is NOT to count mentions. Your task is to detect LEGAL REASONING.

    A factor is "most_weighted" ONLY if the court clearly treats it as:
    - decisive
    - outcome-driving
    - primary
    - central to the decision
    - heavily relied upon
    - explicitly emphasized in reasoning

    Signals of decisive weighting include language like:
    "primary consideration"
    "the court relies heavily on"
    "the key factor"
    "most significant"
    "determinative"
    "critical to the outcome"
    "the court gives substantial weight to"
    "the decision turns on"
    "the court bases its conclusion on"

    Steps:

    1. Identify which statutory factors are meaningfully discussed. 
    2. Rank the TOP THREE most important factors in order of importance.
    3. The FIRST factor must be the most decisive driver of the court’s reasoning.
    4. Do NOT guess.
    5. Do NOT infer from background facts alone.
    6. Focus ONLY on judicial reasoning language.

    Rules:
    - Always return at least ONE factor
    - Return AT MOST three
    - Order matters: first = most decisive
    - Do NOT guess

    Return ONLY valid JSON in this format:

    {{
    "mentioned": {{
        "FACTOR_1": true/false,
        "FACTOR_2": true/false,
        ...
    }},
    "most_weighted": ["FACTOR_NAME", ...],
    "confidence": "low/medium/high",
    "explanation": "2-3 sentence plain-English explanation of why the court relied most heavily on these factors"
    }}

    Use ONLY these factors:

    {schema}

    Case text:
    {text}
    """




    chunks = list(chunk_text(text))

    chunk_results = []

    for chunk in chunks:
        chunk_prompt = prompt.replace(text, chunk)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": chunk_prompt}],
            temperature=0,
            top_p=1,

        )

        content = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(content)
            chunk_results.append(parsed)
        except:
            continue

    # ---- Aggregate chunk outputs ----
    mentioned = {factor: False for factor in FACTOR_SCHEMA}
    most_weighted = []
    confidence_scores = []
    explanation_text = ""

    for r in chunk_results:
        for f, v in r.get("mentioned", {}).items():
            if v:
                mentioned[f] = True

        most_weighted.extend(r.get("most_weighted", []))
        confidence_scores.append(r.get("confidence", "medium"))

        if not explanation_text and r.get("explanation"):
            explanation_text = r["explanation"]

    seen = set()
    ordered = []
    for f in most_weighted:
        if f not in seen:
            ordered.append(f)
            seen.add(f)
    most_weighted = ordered


    confidence = max(
        confidence_scores,
        key=lambda x: ["low", "medium", "high"].index(x)
    ) if confidence_scores else "medium"






    # Safety normalization
    mentioned = parsed.get("mentioned", {})
    most_weighted = parsed.get("most_weighted", [])

    # Ensure all schema keys exist
    for factor in FACTOR_SCHEMA:
        mentioned.setdefault(factor, False)

   

    return {
    "mentioned": mentioned,
    "most_weighted": most_weighted,
    "confidence": confidence,
    "explanation": explanation_text
    }




  




