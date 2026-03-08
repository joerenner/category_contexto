from category_contexto.graph import build_graph_from_edges, compute_graph_similarity


def make_edges():
    return [
        ("Q6279", "Q22686", "same_office", 1.0),
        ("Q6279", "Q76",    "same_party",  1.0),
        ("Q6279", "Q22686", "same_era",    0.8),
        ("Q76",   "Q6279",  "same_office", 1.0),
    ]


def test_build_graph_from_edges():
    graph = build_graph_from_edges(make_edges())
    assert "Q22686" in graph["Q6279"]
    assert "Q76" in graph["Q6279"]
    assert len(graph["Q6279"]["Q22686"]) == 2


def test_graph_similarity_shared_neighbors():
    graph = build_graph_from_edges(make_edges())
    sim_biden_obama = compute_graph_similarity(graph, "Q6279", "Q76")
    assert sim_biden_obama > 0.0
    sim_biden_trump = compute_graph_similarity(graph, "Q6279", "Q22686")
    assert sim_biden_trump > 0.0


def test_graph_similarity_self_is_one():
    graph = build_graph_from_edges(make_edges())
    assert compute_graph_similarity(graph, "Q6279", "Q6279") == 1.0


def test_graph_similarity_unknown_entity():
    graph = build_graph_from_edges(make_edges())
    assert compute_graph_similarity(graph, "Q6279", "Q99999") == 0.0
