import os
import json
import csv
import random
import re
from collections import Counter, defaultdict

from src.extract_factors import extract_factors_llm
from src.vectorize import build_factor_vector

print("\n=== Georgetown Statutory Interpretation Benchmark ===")

# -----------------------------
# Data Loading
# -----------------------------

def load_cases(folder):
    cases = []
    for file in os.listdir(folder):
        if file.endswith(".txt"):
            with open(os.path.join(folder, file)) as f:
                cases.append((file, f.read()))
    return cases


def extract_metadata(text):
    metadata = {}
    for line in text.splitlines():
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        key = key.strip().upper()
        if key in {"JURISDICTION", "COURT", "YEAR", "JUDGE"}:
            metadata[key] = value.strip()
    return metadata


# -----------------------------
# Robustness Tests
# -----------------------------

def truncate_text(text, mode):
    words = text.split()
    half = len(words) // 2
    quarter = len(words) // 4

    if mode == "first_half":
        return " ".join(words[:half])
    if mode == "second_half":
        return " ".join(words[half:])
    if mode == "middle":
        return " ".join(words[quarter:quarter*3])

    return text


def add_noise(text):
    text = re.sub(r"[^\w\s]", "", text)
    sentences = text.split(".")
    sentences = [s for s in sentences if random.random() > 0.1]
    return ". ".join(sentences).lower()


def truncation_test(text, full_top1):
    modes = ["first_half", "second_half", "middle"]
    matches = 0

    for mode in modes:
        truncated = truncate_text(text, mode)
        result = extract_factors_llm(truncated)
        top = result["most_weighted"][0] if result["most_weighted"] else None

        if top == full_top1:
            matches += 1

    return matches / len(modes)


def noise_test(text, full_top1):
    noisy = add_noise(text)
    result = extract_factors_llm(noisy)
    top = result["most_weighted"][0] if result["most_weighted"] else None

    return 1.0 if top == full_top1 else 0.0


# -----------------------------
# Evaluation Pipeline
# -----------------------------

def evaluate_cases(cases):

    eval_records = []
    case_results = []
    metadata_list = []

    trunc_scores = []
    noise_scores = []

    for filename, text in cases:
        print(f"\nProcessing case: {filename}")

        metadata = extract_metadata(text)
        metadata["FILE"] = filename
        metadata_list.append(metadata)

        RUNS = 1
        run_outputs = []

        for _ in range(RUNS):
            out = extract_factors_llm(text, use_cache=False)
            run_outputs.append(out)

        full_top1 = run_outputs[0]["most_weighted"][0] if run_outputs[0]["most_weighted"] else None

        case_trunc = truncation_test(text, full_top1)
        case_noise = noise_test(text, full_top1)
        trunc_scores.append(case_trunc)
        noise_scores.append(case_noise)
        print(f"  Truncation robustness: {case_trunc:.2f}")
        print(f"  Noise robustness: {case_noise:.2f}")

        # stability
        top_predictions = [
            r["most_weighted"][0] if r["most_weighted"] else "NONE"
            for r in run_outputs
        ]

        most_common = Counter(top_predictions).most_common(1)[0]
        stability = most_common[1] / RUNS
        print("  Top factor predictions:", top_predictions)
        print(f"  Stability score: {stability:.2f}")

        for run_idx, out in enumerate(run_outputs):

            vector = build_factor_vector(
                out["mentioned"],
                out["most_weighted"]
            )

            record = {
                "file": filename,
                "metadata": metadata,
                "run_index": run_idx,
                "most_weighted": out["most_weighted"],
                "confidence": out["confidence"],
                "mentioned": out["mentioned"],
                "truncation_robustness": case_trunc,
                "noise_robustness": case_noise,
                "factor_vector": vector,
                "explanation": out["explanation"],
                "top_factor": out["most_weighted"][0] if out["most_weighted"] else None,
                "stability": stability
            }

            eval_records.append(record)
        print("  Dominant factor:", top_predictions[0])  
        case_results.append(run_outputs[0])

    return eval_records, case_results, metadata_list, trunc_scores, noise_scores


# -----------------------------
# Accuracy Evaluation
# -----------------------------

def evaluate_against_labels(results, metadata):

    labels = {}
    with open("data/eval/human_labels.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels[row["file"].strip().lower()] = row["correct_factor"]

    top1 = 0
    top3 = 0
    total = 0

    for meta, res in zip(metadata, results):

        file = meta["FILE"].strip().lower()

        if file not in labels:
            continue

        total += 1
        human = labels[file].strip().lower()
        model = [m.lower() for m in res["most_weighted"]]

        if model and model[0] == human:
            top1 += 1

        if human in model:
            top3 += 1

    return top1, top3, total


# -----------------------------
# Main
# -----------------------------

if __name__ == "__main__":

    cases = load_cases("data/raw/eval_cases") + load_cases("data/raw/ny_real_snippets")

    eval_records, results, metadata, trunc_scores, noise_scores = evaluate_cases(cases)

    os.makedirs("data/eval", exist_ok=True)

    with open("data/eval/eval_log.jsonl", "w") as f:
        for rec in eval_records:
            f.write(json.dumps(rec) + "\n")

    top1, top3, total = evaluate_against_labels(results, metadata)

    stability_scores = [r["stability"] for r in eval_records]

    summary = {
        "top_1_accuracy": top1 / total if total else 0,
        "top_3_accuracy": top3 / total if total else 0,
        "avg_stability": sum(stability_scores) / len(stability_scores),
        "avg_truncation_robustness": sum(trunc_scores) / len(trunc_scores),
        "avg_noise_robustness": sum(noise_scores) / len(noise_scores)
    }

    with open("data/eval/run_history.jsonl", "a") as f:
        f.write(json.dumps(summary) + "\n")

    print("\n=== Evaluation Complete ===")
    
    top1_acc = top1/total if total else 0
    top3_acc = top3/total if total else 0

    print(f"\nTop-1 Accuracy: {top1/total:.0%} ({top1}/{total})")
    print(f"Top-3 Accuracy: {top3/total:.0%} ({top3}/{total})")

    print(f"\nAverage Stability: {summary['avg_stability']:.2f}")
    print(f"Average Truncation Robustness: {summary['avg_truncation_robustness']:.2f}")
    print(f"Average Noise Robustness: {summary['avg_noise_robustness']:.2f}")

    print("\nEvaluation logs saved to:")
    print("data/eval/eval_log.jsonl")
    print("data/eval/run_history.jsonl")