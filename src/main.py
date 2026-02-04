from load_cases import load_cases
from extract_factors import extract_factors, extract_factors_llm
import os
from collections import Counter

def load_cases_from_folder(folder_path):
    cases = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            with open(os.path.join(folder_path, filename), "r") as f:
                cases.append((filename, f.read()))
    return cases

if __name__ == "__main__":
    cases = load_cases_from_folder("data/raw/ny_sample_cases")
    all_results = []

    for filename, text in cases:
        factors = extract_factors_llm(text)
        all_results.append(factors)

    #from collections import Counter

    counter = Counter()

    for result in all_results:
        for factor, present in result.items():
            if present:
                counter[factor] += 1

    total_cases = len(all_results)

    factor_frequencies = {
        factor: counter[factor] / total_cases
        for factor in counter
    }

    print("\n=== New York Equitable Distribution Factor Emphasis ===\n")

    for factor, freq in sorted(factor_frequencies.items(), key=lambda x: -x[1]):
        if freq >= 0.6:
            label = "Frequently emphasized"
        elif freq >= 0.3:
            label = "Sometimes emphasized"
        else:
            label = "Rarely emphasized"

        print(f"{label}: {factor} ({freq:.0%} of cases)")

