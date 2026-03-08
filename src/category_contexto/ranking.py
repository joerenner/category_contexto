from typing import Callable


def compute_blended_rankings(
    entity_ids: list[str],
    graph_similarity_fn: Callable[[str, str], float],
    embedding_similarity_fn: Callable[[str, str], float],
    alpha: float = 0.5,
    recency_fn: Callable[[str, str], float] | None = None,
    recency_weight: float = 0.2,
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
            if recency_fn is not None:
                recency = recency_fn(secret, other)
                blended = (1 - recency_weight) * blended + recency_weight * recency
            similarities.append((other, blended))

        similarities.sort(key=lambda x: x[1], reverse=True)
        rankings[secret] = {eid: rank + 1 for rank, (eid, _) in enumerate(similarities)}

    return rankings


def make_recency_fn(
    eras: dict[str, list[tuple[int, int]]],
) -> Callable[[str, str], float]:
    """Create a recency function from era data.

    Returns a function that computes temporal overlap between two entities,
    normalized to [0, 1].
    """

    def recency_fn(entity_a: str, entity_b: str) -> float:
        periods_a = eras.get(entity_a, [])
        periods_b = eras.get(entity_b, [])
        if not periods_a or not periods_b:
            return 0.0

        # Compute overlap
        total_overlap = 0
        for start_a, end_a in periods_a:
            for start_b, end_b in periods_b:
                overlap_start = max(start_a, start_b)
                overlap_end = min(end_a, end_b)
                if overlap_end > overlap_start:
                    total_overlap += overlap_end - overlap_start

        # Normalize by the shorter career
        total_a = sum(max(0, e - s) for s, e in periods_a)
        total_b = sum(max(0, e - s) for s, e in periods_b)
        min_total = min(total_a, total_b)
        if min_total == 0:
            return 0.0

        return min(1.0, total_overlap / min_total)

    return recency_fn
