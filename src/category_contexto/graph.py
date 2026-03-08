from collections import defaultdict


def build_graph_from_edges(
    edges: list[tuple[str, str, str, float]],
) -> dict[str, dict[str, list[tuple[str, float]]]]:
    graph: dict[str, dict[str, list[tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
    for entity_a, entity_b, edge_type, weight in edges:
        graph[entity_a][entity_b].append((edge_type, weight))
        graph[entity_b][entity_a].append((edge_type, weight))
    return dict(graph)


def _edge_feature_vector(edge_list: list[tuple[str, float]]) -> dict[str, float]:
    features: dict[str, float] = defaultdict(float)
    for edge_type, weight in edge_list:
        features[edge_type] += weight
    return dict(features)


def _entity_profile(graph: dict, entity_id: str) -> dict[str, float]:
    profile: dict[str, float] = defaultdict(float)
    neighbors = graph.get(entity_id, {})
    for neighbor_id, edge_list in neighbors.items():
        for edge_type, weight in edge_list:
            profile[f"{neighbor_id}:{edge_type}"] = weight
            profile[f"_type:{edge_type}"] += weight
    return dict(profile)


def compute_graph_similarity(graph: dict, entity_a: str, entity_b: str) -> float:
    if entity_a == entity_b:
        return 1.0

    profile_a = _entity_profile(graph, entity_a)
    profile_b = _entity_profile(graph, entity_b)

    if not profile_a or not profile_b:
        return 0.0

    all_keys = set(profile_a.keys()) | set(profile_b.keys())
    intersection = 0.0
    union = 0.0
    for key in all_keys:
        va = profile_a.get(key, 0.0)
        vb = profile_b.get(key, 0.0)
        intersection += min(va, vb)
        union += max(va, vb)

    return intersection / union if union > 0 else 0.0
