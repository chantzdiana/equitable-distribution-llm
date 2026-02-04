from load_cases import load_cases
from extract_factors import extract_factors

if __name__ == "__main__":
    cases = load_cases()
    for text in cases:
        factors = extract_factors(text)
        print(factors)

