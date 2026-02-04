
import os
from collections import Counter
from extract_factors import extract_factors_llm


def load_cases_from_folder(folder_path):
    cases = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            with open(os.path.join(folder_path, filename), "r") as f:
                cases.append((filename, f.read()))
    return cases


def extract_metadata(text):
    metadata = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().upper()
            value = value.strip()
            if key in {"JURISDICTION", "COURT", "YEAR", "JUDGE"}:
                metadata[key] = value
        else:
            break
    return metadata


if __name__ == "__main__":
    cases = load_cases_from_folder("data/raw/ny_real_snippets")

    all_results = []
    case_metadata = []

    for filename, text in cases:
        metadata = extract_metadata(text)
        case_metadata.append(metadata)

        factors = extract_factors_llm(text)
        all_results.append(factors)

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

    # ===== Lawyer-facing context summary =====
    jurisdictions = {m.get("JURISDICTION") for m in case_metadata if "JURISDICTION" in m}
    courts = {m.get("COURT") for m in case_metadata if "COURT" in m}
    years = sorted(int(m["YEAR"]) for m in case_metadata if "YEAR" in m)

    print("\n=== Analysis Context ===\n")
    print(f"Jurisdiction: {', '.join(jurisdictions)}")
    print(f"Courts: {', '.join(courts)}")

    if years:
        print(f"Years Covered: {years[0]}–{years[-1]}")

    print(f"Number of Cases Analyzed: {len(case_metadata)}\n")

    # ===== Factor emphasis summary =====
    print("=== New York Equitable Distribution Factor Emphasis ===\n")

    for factor, freq in sorted(factor_frequencies.items(), key=lambda x: -x[1]):
        if freq >= 0.6:
            label = "Frequently emphasized"
        elif freq >= 0.3:
            label = "Sometimes emphasized"
        else:
            label = "Rarely emphasized"

        print(f"{label}: {factor} ({freq:.0%} of cases)")


