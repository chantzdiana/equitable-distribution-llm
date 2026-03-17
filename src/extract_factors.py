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
from src.cache import get_cached_result, store_cached_result

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



FACTOR_SCHEMA = [
    "income_and_property_at_marriage_and_divorce",          # (1)
    "duration_of_marriage_age_and_health",                   # (2)
    "custodial_parent_residence_needs",                      # (3)
    "loss_of_inheritance_and_pension_rights",                # (4)
    "loss_of_health_insurance",                              # (5)
    "maintenance_award",                                     # (6)
    "contributions_to_marital_property_and_career",          # (7)
    "liquidity_of_assets",                                   # (8)
    "future_financial_circumstances",                        # (9)
    "difficulty_of_asset_valuation_or_business_interests",   # (10)
    "tax_consequences",                                      # (11)
    "wasteful_dissipation_of_assets",                        # (12)
    "improper_transfer_or_encumbrance",                      # (13)
    "domestic_violence",                                     # (14)
    "companion_animal_best_interests",                       # (15)
    "other_just_and_proper_factor"                           # (16)
]


def extract_factors(text: str) -> dict:
    """
    Simple rule-based baseline for detecting equitable-distribution factors.
    Uses keyword heuristics mapped to the same schema as the LLM model.
    """
    text = text.lower()

    return {

        "income_and_property_at_marriage_and_divorce":
            "income" in text or "salary" in text or "property" in text,

        "duration_of_marriage_age_and_health":
            "duration" in text or "length of the marriage" in text
            or "age" in text or "health" in text or "medical" in text,

        "custodial_parent_residence_needs":
            "custodial parent" in text or "marital residence" in text or "household effects" in text,

        "loss_of_inheritance_and_pension_rights":
            "pension" in text or "inheritance" in text or "retirement" in text,

        "loss_of_health_insurance":
            "health insurance" in text or "insurance coverage" in text,

        "maintenance_award":
            "maintenance" in text or "spousal support" in text or "alimony" in text,

        "contributions_to_marital_property_and_career":
            "contribution" in text or "career" in text or "education" in text,

        "liquidity_of_assets":
            "liquid" in text or "non-liquid" in text or "liquidity" in text,

        "future_financial_circumstances":
            "future financial" in text or "earning capacity" in text or "future income" in text,

        "difficulty_of_asset_valuation_or_business_interests":
            "valuation" in text or "business interest" in text or "professional practice" in text,

        "tax_consequences":
            "tax" in text,

        "wasteful_dissipation_of_assets":
            "dissipation" in text or "waste" in text,

        "improper_transfer_or_encumbrance":
            "transfer" in text or "encumbrance" in text or "conceal" in text,

        "domestic_violence":
            "domestic violence" in text or "abuse" in text,

        "companion_animal_best_interests":
            "dog" in text or "cat" in text or "companion animal" in text or "pet" in text,

        "other_just_and_proper_factor":
            False
    }

def chunk_text(text, chunk_size=2500):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i + chunk_size])


def extract_factors_llm(text: str, use_cache=True) -> dict:
    """
    Uses an LLM to extract equitable-distribution factors from text.
    Returns the same schema as extract_factors().
    """
    schema_json = json.dumps(FACTOR_SCHEMA, indent=2)
    
    
    if use_cache:
        cached = get_cached_result(text.strip())
        if cached:
            return cached
    
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
    3. The FIRST factor must be the most decisive driver of the court's reasoning.
    4. Do NOT guess.
    5. Do NOT infer from background facts alone.
    6. Focus ONLY on judicial reasoning language.

    Rules:
    - Always return at least ONE factor
    - Return AT MOST three
    - Order matters: first = most decisive
    - Do NOT guess

    Confidence Guidelines:

    Assign confidence based on how clearly the opinion identifies the decisive factor.

    High confidence:
    The opinion explicitly states that the court relied primarily or heavily on a factor,
    using reasoning language such as "primary consideration", "determinative",
    "critical to the outcome", or "the court relies heavily on".

    Medium confidence:
    The factor appears central to the reasoning but the court does not explicitly state
    that it is decisive. Multiple factors may appear important.

    Low confidence:
    The opinion discusses several factors but it is unclear which factor drives the
    decision, or the reasoning language is weak or ambiguous.

    Use the lowest confidence level that accurately reflects the certainty of the reasoning.

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

    {schema_json}
    """

    chunks = list(chunk_text(text))

    chunk_results = []

    for chunk in chunks:
        chunk_prompt = f"""
        {prompt}

        Case text:
        {chunk}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": chunk_prompt}],
            temperature=0,
            top_p=1,

        )

        content = response.choices[0].message.content.strip()

        try:
            # Strip markdown code fences if present
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
            parsed = json.loads(cleaned)
            chunk_results.append(parsed)
        except json.JSONDecodeError as e:
            print(f"  [Warning] Failed to parse JSON from chunk: {e}")
            print(f"  [Raw response]: {content[:200]}")
            continue

    
   
   # ---- Aggregate chunk outputs ----
    if not chunk_results:
        result = {
            "mentioned": {factor: False for factor in FACTOR_SCHEMA},
            "most_weighted": [],
            "confidence": "low",
            "explanation": "Model could not confidently extract reasoning from the provided text."
        }
        store_cached_result(text.strip(), result)
        return result

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

    # Deduplicate factors (preserve order)
    seen = set()
    ordered = []
    for f in most_weighted:
        if f not in seen:
            ordered.append(f)
            seen.add(f)
    most_weighted = ordered[:3]

    confidence = max(
        confidence_scores,
        key=lambda x: ["low", "medium", "high"].index(x)
    ) if confidence_scores else "medium"

    # ---- Final normalization ----
    for factor in FACTOR_SCHEMA:
        mentioned.setdefault(factor, False)

    result = {
        "mentioned": mentioned,
        "most_weighted": most_weighted,
        "confidence": confidence,
        "explanation": explanation_text
    }

    if use_cache:
        store_cached_result(text.strip(), result)
    return result


   