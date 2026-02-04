from load_cases import load_cases
from extract_factors import extract_factors, extract_factors_llm

if __name__ == "__main__":
    cases = load_cases()
    for text in cases:
        print("RULE-BASED:", extract_factors(text))
        print("LLM-BASED:", extract_factors_llm(text))


