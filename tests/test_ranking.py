import numpy as np
from category_contexto.ranking import compute_blended_rankings, make_recency_fn


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


def test_recency_boosts_contemporaries():
    entity_ids = ["Q1", "Q2", "Q3"]

    # All have equal graph and embedding similarity
    def graph_sim(a, b):
        return 0.5 if a != b else 1.0

    def embed_sim(a, b):
        return 0.5 if a != b else 1.0

    # Q2 is a contemporary of Q1, Q3 is not
    def recency_fn(a, b):
        if {a, b} == {"Q1", "Q2"}:
            return 1.0
        return 0.0

    rankings = compute_blended_rankings(
        entity_ids, graph_sim, embed_sim,
        alpha=0.5, recency_fn=recency_fn, recency_weight=0.3,
    )

    # Q2 should rank higher than Q3 for Q1 (recency boost)
    assert rankings["Q1"]["Q2"] < rankings["Q1"]["Q3"]


def test_make_recency_fn_overlap():
    eras = {
        "Q1": [(2000, 2010)],
        "Q2": [(2005, 2015)],
        "Q3": [(1900, 1910)],
    }
    fn = make_recency_fn(eras)

    # Q1 and Q2 overlap by 5 years, shorter career is 10 years → 0.5
    assert fn("Q1", "Q2") == 0.5

    # Q1 and Q3 have no overlap
    assert fn("Q1", "Q3") == 0.0

    # Unknown entity returns 0
    assert fn("Q1", "Q999") == 0.0


def test_make_recency_fn_full_overlap():
    eras = {
        "Q1": [(2000, 2020)],
        "Q2": [(2005, 2010)],
    }
    fn = make_recency_fn(eras)

    # Q2 is fully contained in Q1; overlap=5, shorter career=5 → 1.0
    assert fn("Q1", "Q2") == 1.0
