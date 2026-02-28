
import os
import json
from collections import Counter, defaultdict
#from extract_factors import extract_factors, extract_factors_llm
from src.extract_factors import extract_factors_llm, extract_factors
import csv
import random
import re
from src.vectorize import build_factor_vector


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

def truncate_text(text, mode="first_half"):
    words = text.split()
    half = len(words) // 2

    if mode == "first_half":
        return " ".join(words[:half])

    elif mode == "second_half":
        return " ".join(words[half:])

    elif mode == "middle":
        quarter = len(words) // 4
        return " ".join(words[quarter:quarter * 3])

    else:
        return text


if __name__ == "__main__":
    cases = load_cases_from_folder("data/raw/eval_cases")

    all_results = []
    case_metadata = []
    truncation_scores = []
    noise_scores = []
    # For aggregating runs per case
    case_run_outputs = {}
    os.makedirs("data/eval", exist_ok=True)
    with open("data/eval/eval_log.jsonl", "w") as f:

        for filename, text in cases:
            rule_based = extract_factors(text)
            print("RULE-BASED:", rule_based)

            metadata = extract_metadata(text)
            metadata["FILE"] = filename
            case_metadata.append(metadata)

            RUNS_PER_CASE = 2
            run_outputs = []

            for run_idx in range(RUNS_PER_CASE):
                out = extract_factors_llm(text, use_cache=False)
                run_outputs.append(out)
                # Build factor vector for each run
                vector = build_factor_vector(
                    out["mentioned"],
                    out["most_weighted"]
                )

                # Truncation Robustness Test
                full_top1 = out["most_weighted"][0] if out["most_weighted"] else None
                trunc_modes = ["first_half", "second_half", "middle"]
                trunc_matches = 0
                for mode in trunc_modes:
                    truncated_text = truncate_text(text, mode)
                    trunc_result = extract_factors_llm(truncated_text)
                    trunc_top1 = (
                        trunc_result["most_weighted"][0]
                        if trunc_result["most_weighted"]
                        else None
                    )
                    if trunc_top1 == full_top1:
                        trunc_matches += 1
                truncation_score = trunc_matches / len(trunc_modes)
                truncation_scores.append(truncation_score)

                # Noise Robustness Test
                noisy_text = add_noise(text)
                noisy_result = extract_factors_llm(noisy_text)
                noise_top1 = (
                    noisy_result["most_weighted"][0]
                    if noisy_result["most_weighted"]
                    else None
                )
                noise_score = 1.0 if noise_top1 == full_top1 else 0.0
                noise_scores.append(noise_score)

                # Compute run-level stability (all runs per case)
                if RUNS_PER_CASE == 1:
                    run_stability = 1.0
                else:
                    top1_predictions = [r["most_weighted"][0] if r["most_weighted"] else "NONE" for r in run_outputs]
                    most_common = Counter(top1_predictions).most_common(1)[0]
                    run_stability = most_common[1] / RUNS_PER_CASE

                eval_record = {
                    "file": filename,
                    "metadata": metadata,
                    "run_index": run_idx,
                    "most_weighted": out["most_weighted"],
                    "confidence": out["confidence"],
                    "mentioned": out["mentioned"],
                    "truncation_robustness": truncation_score,
                    "noise_robustness": noise_score,
                    "factor_vector": vector,
                    "explanation": out["explanation"],
                    "top_factor": out["most_weighted"][0] if out["most_weighted"] else None,
                    "stability": run_stability
                }
                f.write(json.dumps(eval_record) + "\n")

            # Stability computation (after all runs)
            top1_predictions = [r["most_weighted"][0] if r["most_weighted"] else "NONE" for r in run_outputs]
            print(f"Run-level Top1s for {filename}: {top1_predictions}")
            if RUNS_PER_CASE == 1:
                stability_score = 1.0
            else:
                most_common = Counter(top1_predictions).most_common(1)[0]
                stability_score = most_common[1] / RUNS_PER_CASE
            # Optionally, log stability_score separately or aggregate as needed

    

    counter = Counter()

    print(
        """
        This analysis reviews a set of divorce opinions and identifies which statutory
        equitable-distribution factors the court appears to rely on most heavily in
        reaching its decision. These results reflect dominant judicial reasoning,
        not merely whether a factor was mentioned.
        """
    )
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
    
    print("\n=== Similar Case Test ===\n")

    from src.similarity import find_most_similar_cases
    from src.vectorize import build_factor_vector

    # Use the LAST analyzed case as the query
    if all_results:
        last_result = all_results[-1]
        query_vector = build_factor_vector(
            last_result["mentioned"],
            last_result["most_weighted"]
        )
        # --- DEBUG PRINT ---
        print("\nDEBUG — Query Case:", case_metadata[-1]["FILE"])
        print("DEBUG — Query Vector:", query_vector)

        similar_cases = find_most_similar_cases(query_vector, top_k=8)

        for s in similar_cases:
            print(f"Case: {s['file']}")
            print(f"  Similarity: {s['score']:.2f}")
            print(f"  Judge: {s['judge']}")
            print(f"  Top Factor: {s['top_factor']}\n")
            print(f"  (Vector stored in eval_log for this case)")
        

        print("\n=== Truncation Robustness Summary ===\n")

        trunc_scores = []

        with open("data/eval/eval_log.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                trunc_scores.append(rec.get("truncation_robustness", 0))

        if trunc_scores:
            avg_trunc = sum(trunc_scores) / len(trunc_scores)
            print(f"Average Truncation Robustness: {avg_trunc:.2f}")
            print(f"Perfectly Robust Cases: {sum(1 for s in trunc_scores if s == 1.0)}/{len(trunc_scores)}")

        print("\n=== Noise Robustness Summary ===\n")

        noise_scores = []

        with open("data/eval/eval_log.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                noise_scores.append(rec.get("noise_robustness", 0))

        if noise_scores:
            avg_noise = sum(noise_scores) / len(noise_scores)
            print(f"Average Noise Robustness: {avg_noise:.2f}")
            print(f"Robust to Noise Cases: {sum(1 for s in noise_scores if s == 1.0)}/{len(noise_scores)}")

        print("\n=== User Case Simulation ===\n")

        from src.user_similarity import analyze_user_case

        sample_text = """
        The wife supported the husband through medical school.
        The court emphasized her contributions to his career
        as the primary factor in distributing marital property.
        """

        user_result = analyze_user_case(sample_text)

        print("User Most Weighted:", user_result["analysis"]["most_weighted"])
        print("\nMost Similar Cases:")

        for case in user_result["similar_cases"]:
            print(case)

    
    # ============================
    # SAVE RESULTS SUMMARY
    # ============================
    from datetime import datetime
    import os

    results_summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dataset_size": total,
        "top_1_accuracy": correct_top1 / total if total > 0 else 0,
        "top_3_accuracy": correct_top3 / total if total > 0 else 0,
        "avg_stability": sum(stability_scores) / len(stability_scores) if stability_scores else 0,
        "avg_truncation_robustness": sum(truncation_scores) / len(truncation_scores) if truncation_scores else 0,
        "avg_noise_robustness": sum(noise_scores) / len(noise_scores) if noise_scores else 0,
        "perfectly_stable_cases": sum(1 for s in stability_scores if s == 1.0),
        "perfectly_robust_cases": sum(1 for s in truncation_scores if s == 1.0),
        "noise_robust_cases": sum(1 for s in noise_scores if s == 1.0),
        "per_factor_accuracy": {
            factor: factor_correct[factor] / factor_total[factor]
            for factor in factor_total
        }
    }

    os.makedirs("data/eval", exist_ok=True)
    
    # Append to summary log
    summary_log_path = "data/eval/results_summary.jsonl"
    with open(summary_log_path, "a") as f:
        f.write(json.dumps(results_summary) + "\n")
    
    print("\n✅ Results summary saved to data/eval/results_summary.jsonl")