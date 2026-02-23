
import os
import json
from collections import Counter, defaultdict
#from extract_factors import extract_factors, extract_factors_llm
from src.extract_factors import extract_factors_llm, extract_factors
import csv
import random
import re


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




def add_noise(text):
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # Randomly drop 10% of sentences
    sentences = text.split(".")
    sentences = [s for s in sentences if random.random() > 0.1]

    # Lowercase everything
    text = ". ".join(sentences).lower()

    return text


if __name__ == "__main__":
    cases = load_cases_from_folder("data/raw/ny_real_snippets") + load_cases_from_folder("data/raw/long_cases")

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

            RUNS_PER_CASE = 2   # you can change to 3–7 later

            run_outputs = []

            for _ in range(RUNS_PER_CASE):
                out = extract_factors_llm(text)
                run_outputs.append(out)

            # Use first run for normal pipeline
            factors = run_outputs[0]
            all_results.append(factors)
            
            # -------------------------
            # Noise Robustness Test (single-case demo)
            # -------------------------
            if filename == "ny_obrien_full.txt":
                noisy_text = add_noise(text)
                noisy_result = extract_factors_llm(noisy_text)

                print("\n--- Noise Robustness Test ---")
                print("Original Top-1:",
                      factors["most_weighted"][0] if factors["most_weighted"] else None)

                print("Noisy Top-1:",
                      noisy_result["most_weighted"][0] if noisy_result["most_weighted"] else None)

            # -------------------------
            # Stability computation
            # -------------------------
            top1_predictions = []

            for r in run_outputs:
                if r["most_weighted"]:
                    top1_predictions.append(r["most_weighted"][0])
                else:
                    top1_predictions.append("NONE")

            # Most common top factor
            most_common = Counter(top1_predictions).most_common(1)[0]
            stability_score = most_common[1] / RUNS_PER_CASE

            # ---- Evaluation logging ----
            eval_record = {
                "file": filename,
                "metadata": metadata,
                "most_weighted": factors["most_weighted"],
                "confidence": factors["confidence"],
                "mentioned": factors["mentioned"],
                "stability": stability_score,
                "explanation": factors["explanation"],
                "top_factor": factors["most_weighted"][0] if factors["most_weighted"] else None
    
            }

            f.write(json.dumps(eval_record) + "\n")

    

    counter = Counter()

    
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

    correct_top1 = 0
    correct_top3 = 0
    total = 0

    for metadata, result in zip(case_metadata, all_results):
        filename = metadata.get("FILE")

        if filename in human_labels:
            total += 1

            human = human_labels[filename]
            model = result["most_weighted"]

            top1_correct = (len(model) > 0 and model[0] == human)
            top3_correct = (human in model)

            if top1_correct:
                correct_top1 += 1
            if top3_correct:
                correct_top3 += 1

            # ---- PER CASE REPORT ----
            print(f"Case: {filename}")
            print(f"  Model dominant factor(s): {model}")
            print(f"  Human correct factor: {human}")
            print(f"  Result: {'TOP1 CORRECT' if top1_correct else 'WRONG'}\n")
            print(f"  Result: {'Top3 CORRECT' if top3_correct else 'WRONG'}\n")



    if total > 0:
        top1_acc = correct_top1 / total
        top3_acc = correct_top3 / total

        print(f"Top-1 Accuracy: {top1_acc:.0%} ({correct_top1}/{total})")
        print(f"Top-3 Accuracy: {top3_acc:.0%} ({correct_top3}/{total})")
    else:
        print("No labeled cases found.")

    print("\n=== Per-Factor Accuracy ===\n")

    factor_correct = Counter()
    factor_total = Counter()

    for metadata, result in zip(case_metadata, all_results):
        filename = metadata.get("FILE")

        if filename in human_labels:
            human = human_labels[filename]
            model = result["most_weighted"]

            factor_total[human] += 1

            if len(model) > 0 and model[0] == human:
                factor_correct[human] += 1

    for factor in factor_total:
        acc = factor_correct[factor] / factor_total[factor]
        readable = factor.replace("_", " ")
        print(f"{readable}: {acc:.0%} ({factor_correct[factor]}/{factor_total[factor]})")
    
    print("\n=== Stability Summary ===\n")

    stability_scores = []

    with open("data/eval/eval_log.jsonl") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            stability_scores.append(rec.get("stability", 0))

    if stability_scores:
        avg_stability = sum(stability_scores) / len(stability_scores)
        print(f"Average Stability: {avg_stability:.2f}")

        print(f"Perfectly Stable Cases: {sum(1 for s in stability_scores if s == 1.0)}/{len(stability_scores)}")    
    
    
    print("\n=== Confidence Distribution ===\n")

    conf_counter = Counter()

    with open("data/eval/eval_log.jsonl") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            conf_counter[rec.get("confidence", "unknown")] += 1

    for k, v in conf_counter.items():
        print(f"{k}: {v} cases")