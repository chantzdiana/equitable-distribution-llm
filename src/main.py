
import os
import json
from collections import Counter, defaultdict
#from extract_factors import extract_factors, extract_factors_llm
from src.extract_factors import extract_factors_llm, extract_factors
import csv


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

    os.makedirs("data/eval", exist_ok=True)
    with open("data/eval/eval_log.jsonl", "w") as f:

        for filename, text in cases:
            # --- Rule-based baseline ---
            rule_based = extract_factors(text)
            print("RULE-BASED:", rule_based)

            metadata = extract_metadata(text)
            metadata["FILE"] = filename
            case_metadata.append(metadata)

            factors = extract_factors_llm(text)
            all_results.append(factors)

            # ---- Evaluation logging ----
            eval_record = {
                "file": filename,
                "metadata": metadata,
                "most_weighted": factors["most_weighted"],
                "confidence": factors["confidence"],
                "mentioned": factors["mentioned"]
            }

            f.write(json.dumps(eval_record) + "\n")

    # for filename, text in cases:
    #     #if filename != "ny_obrien_excerpt.txt":
    #      #   continue
    #     # --- Rule-based baseline ---
    #     rule_based = extract_factors(text)
    #     print("RULE-BASED:", rule_based)
        
    #     metadata = extract_metadata(text)
    #     metadata["FILE"] = filename
    #     case_metadata.append(metadata)

    #     factors = extract_factors_llm(text)
    #     # print("DEBUG MOST WEIGHTED:", factors["most_weighted"])
    #     # new
    #     all_results.append(factors)
    #     # ---- Evaluation logging ----
    #     eval_record = {
    #     "file": filename,
    #     "metadata": metadata,
    #     "most_weighted": factors["most_weighted"],
    #     "confidence": factors["confidence"],
    #     "mentioned": factors["mentioned"]
    #     }

    # comment out for now
    # with open("data/eval/eval_log.jsonl", "a") as f:
    #     f.write(json.dumps(eval_record) + "\n")

    counter = Counter()

    # for result in all_results:
    #     for factor, present in result.items():
    #         if present:
    #             counter[factor] += 1
    for result in all_results:
        for factor in result["most_weighted"]:
            counter[factor] += 1


    total_cases = len(all_results)

    factor_frequencies = {
        factor: counter[factor] / total_cases
        for factor in counter
    }

    # # ===== Lawyer-facing context summary =====
    jurisdictions = {m.get("JURISDICTION") for m in case_metadata if "JURISDICTION" in m}
    courts = {m.get("COURT") for m in case_metadata if "COURT" in m}
    years = sorted(int(m["YEAR"]) for m in case_metadata if "YEAR" in m)

    # print("\n=== Analysis Context ===\n")
    # print(f"Jurisdiction: {', '.join(jurisdictions)}")
    # print(f"Courts: {', '.join(courts)}")

    # if years:
    #     print(f"Years Covered: {years[0]}–{years[-1]}")

    # print(f"Number of Cases Analyzed: {len(case_metadata)}\n")

    # # ===== Factor emphasis summary =====
    # print("=== New York Equitable Distribution Factor Emphasis ===\n")

    # for factor, freq in sorted(factor_frequencies.items(), key=lambda x: -x[1]):
    #     if freq >= 0.6:
    #         label = "Frequently emphasized"
    #     elif freq >= 0.3:
    #         label = "Sometimes emphasized"
    #     else:
    #         label = "Rarely emphasized"

    #     print(f"{label}: {factor} ({freq:.0%} of cases)")


    print("\n=== Equitable Distribution Analysis Summary ===\n")

    print(
        "This analysis reviews a set of divorce opinions and identifies which statutory\n"
        "equitable-distribution factors the court appears to rely on most heavily in\n"
        "reaching its decision. These results reflect dominant judicial reasoning,\n"
        "not merely whether a factor was mentioned.\n"
    )

    print("---- Case Context ----")
    print(f"Jurisdiction analyzed: {', '.join(jurisdictions)}")
    print(f"Courts represented: {', '.join(courts)}")

    if years:
        print(f"Years covered: {years[0]}–{years[-1]}")

    print(f"Number of cases analyzed: {len(case_metadata)}\n")

    print("---- Factor Emphasis (Dominant Judicial Reasoning) ----\n")

    if not counter:
        print("No dominant factors were detected in the analyzed cases.\n")
    else:
        for factor, count in counter.most_common():
            freq = count / total_cases

            if freq >= 0.6:
                label = "Frequently decisive"
            elif freq >= 0.3:
                label = "Sometimes decisive"
            else:
                label = "Rarely decisive"

            readable = factor.replace("_", " ")

            print(
                f"{label}: {readable} "
                f"(appeared as a primary factor in {count} of {total_cases} cases, {freq:.0%})"
            )

    print(
        "\nInterpretation: A factor labeled 'Frequently decisive' appeared to drive the court's\n"
        "reasoning in a majority of the analyzed cases. This summary is descriptive and does\n"
        "not predict outcomes in any individual case."
    )

    # ============================
    # INSERT JUDGE BLOCK HERE
    # ============================

    judge_counter = defaultdict(Counter)

    for metadata, result in zip(case_metadata, all_results):
        judge = metadata.get("JUDGE", "Unknown")

        for factor in result["most_weighted"]:
            judge_counter[judge][factor] += 1


    print("\n=== Judge-Level Factor Tendencies ===\n")

    for judge, counter in judge_counter.items():
        print(f"Judge: {judge}")

        total = sum(counter.values())
        for factor, count in counter.most_common():
            freq = count / total
            readable = factor.replace("_", " ")
            print(f"  - {readable} ({freq:.0%})")

        print()



    print("\n=== Evaluation Against Human Labels ===\n")

    # Load human labels
    human_labels = {}
    with open("data/eval/human_labels.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            human_labels[row["file"]] = row["correct_factor"]

    correct = 0
    total = 0

    for metadata, result in zip(case_metadata, all_results):
        filename = metadata.get("FILE")

        if filename in human_labels:
            total += 1

            human = human_labels[filename]
            model = result["most_weighted"]

            is_correct = human in model

            if is_correct:
                correct += 1

            # ---- PER CASE REPORT ----
            print(f"Case: {filename}")
            print(f"  Model dominant factor(s): {model}")
            print(f"  Human correct factor: {human}")
            print(f"  Result: {'CORRECT' if is_correct else 'WRONG'}\n")


    if total > 0:
        accuracy = correct / total
        print(f"Accuracy: {accuracy:.0%} ({correct}/{total} correct)")
    else:
        print("No labeled cases found.")
