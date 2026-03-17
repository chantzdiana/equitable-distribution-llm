from src.extract_factors import extract_factors_llm
from src.vectorize import build_factor_vector
from src.similarity import find_most_similar_cases


def analyze_user_case(text, top_k=8):

    # Run LLM factor analysis
    analysis = extract_factors_llm(text)

    # Build factor vector
    vector = build_factor_vector(
        analysis["mentioned"],
        analysis["most_weighted"]
    )

    # Retrieve similar cases
    similar_cases = find_most_similar_cases(
        vector,
        text,
        top_k=top_k
    )

    return {
        "analysis": analysis,
        "similar_cases": similar_cases
    }