import numpy as np
from category_contexto.ranking import compute_blended_rankings


def test_compute_blended_rankings_basic():
    entity_ids = ["Q1", "Q2", "Q3"]

    def graph_sim(a, b):
        if {a, b} == {"Q1", "Q2"}:
            return 0.8
        if {a, b} == {"Q1", "Q3"}:
            return 0.2
        if {a, b} == {"Q2", "Q3"}:
            return 0.5
        if a == b:
            return 1.0
        return 0.0

    def embed_sim(a, b):
        if {a, b} == {"Q1", "Q2"}:
            return 0.6
        if {a, b} == {"Q1", "Q3"}:
            return 0.9
        if {a, b} == {"Q2", "Q3"}:
            return 0.3
        if a == b:
            return 1.0
        return 0.0

    rankings = compute_blended_rankings(entity_ids, graph_sim, embed_sim, alpha=0.5)

    # For Q1: Q2 blend=0.7, Q3 blend=0.55 → Q2 rank 1, Q3 rank 2
    assert rankings["Q1"]["Q2"] == 1
    assert rankings["Q1"]["Q3"] == 2

    for eid in entity_ids:
        assert eid not in rankings[eid]
        assert len(rankings[eid]) == 2


def test_blended_rankings_alpha_zero_ignores_graph():
    entity_ids = ["Q1", "Q2", "Q3"]

    def graph_sim(a, b):
        return 0.9 if {a, b} == {"Q1", "Q2"} else 0.0

    def embed_sim(a, b):
        return 0.9 if {a, b} == {"Q1", "Q3"} else 0.0

    rankings = compute_blended_rankings(entity_ids, graph_sim, embed_sim, alpha=0.0)
    assert rankings["Q1"]["Q3"] == 1
    assert rankings["Q1"]["Q2"] == 2
