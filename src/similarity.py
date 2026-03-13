import math
import json
#from src.similarity import cosine_similarity

def cosine_similarity(v1, v2):
    dot = sum(a*b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a*a for a in v1))
    mag2 = math.sqrt(sum(b*b for b in v2))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)
def compute_idf(path="data/eval/eval_log.jsonl"):
    from collections import Counter

    factor_counts = Counter()
    total_cases = 0
    seen_files = set()

    with open(path) as f:
        for line in f:
            rec = json.loads(line)

            # avoid counting duplicate runs
            if rec["file"] in seen_files:
                continue

            seen_files.add(rec["file"])
            total_cases += 1

            factors = set(rec.get("most_weighted", []))
            for fct in factors:
                factor_counts[fct] += 1

    idf = {}

    for factor in factor_counts:
        idf[factor] = math.log(total_cases / (1 + factor_counts[factor]))

    return idf
def apply_idf_weights(vector, factors, idf):

    weighted = []

    for val in vector:
        if val > 0:
            weighted.append(val * 2)  # simple importance boost
        else:
            weighted.append(0)

    return weighted

def find_most_similar_cases(query_vector, top_k=8, path="data/eval/eval_log.jsonl"):
    idf = compute_idf(path)
    results = []
    seen = set()
    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            if rec["file"] in seen:
                continue

            seen.add(rec["file"])
            
            vec = rec.get("factor_vector")
            if not vec:
                continue

            weighted_vec = apply_idf_weights(
                vec,
                rec.get("most_weighted", []),
                idf
            )
            score = cosine_similarity(query_vector, weighted_vec)

            results.append({
                "file": rec["file"],
                "judge": rec["metadata"].get("JUDGE", "Unknown"),
                "metadata": rec.get("metadata", {}),
                "score": score,
                "top_factor": rec.get("top_factor"),
                "most_weighted": rec.get("most_weighted", [])
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]