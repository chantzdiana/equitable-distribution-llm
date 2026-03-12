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



def find_most_similar_cases(query_vector, top_k=8, path="data/eval/eval_log.jsonl"):
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

            score = cosine_similarity(query_vector, vec)

            results.append({
                "file": rec["file"],
                "judge": rec["metadata"].get("JUDGE", "Unknown"),
                "score": score,
                "top_factor": rec.get("top_factor"),
                "most_weighted": rec.get("most_weighted", [])
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]