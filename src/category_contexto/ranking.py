from typing import Callable


def compute_blended_rankings(
    entity_ids: list[str],
    graph_similarity_fn: Callable[[str, str], float],
    embedding_similarity_fn: Callable[[str, str], float],
    alpha: float = 0.5,
) -> dict[str, dict[str, int]]:
    rankings: dict[str, dict[str, int]] = {}

    for secret in entity_ids:
        similarities = []
        for other in entity_ids:
            if other == secret:
                continue
            g_sim = graph_similarity_fn(secret, other)
            e_sim = embedding_similarity_fn(secret, other)
            blended = alpha * g_sim + (1 - alpha) * e_sim
            similarities.append((other, blended))

        similarities.sort(key=lambda x: x[1], reverse=True)
        rankings[secret] = {eid: rank + 1 for rank, (eid, _) in enumerate(similarities)}

    return rankings
