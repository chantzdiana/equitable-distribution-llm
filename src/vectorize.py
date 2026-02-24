from src.extract_factors import FACTOR_SCHEMA

def build_factor_vector(mentioned, most_weighted):
    vector = []

    for factor in FACTOR_SCHEMA:
        if factor not in mentioned or not mentioned[factor]:
            vector.append(0.0)
        elif factor in most_weighted:
            rank = most_weighted.index(factor)
            if rank == 0:
                vector.append(1.0)
            elif rank == 1:
                vector.append(0.85)
            else:
                vector.append(0.7)
        else:
            vector.append(0.5)

    return vector