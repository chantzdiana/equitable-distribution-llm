from src.extract_factors import extract_factors_llm
from src.vectorize import build_factor_vector
from src.similarity import find_most_similar_cases

def analyze_user_case(text, top_k=5):
    # Run LLM on user input
    result = extract_factors_llm(text)

    # Build factor vector
    vector = build_factor_vector(
        result["mentioned"],
        result["most_weighted"]
    )

    # Retrieve similar cases
    similar_cases = find_most_similar_cases(vector, top_k=top_k)

    return {
        "analysis": result,
        "similar_cases": similar_cases
    }