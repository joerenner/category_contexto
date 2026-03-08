from category_contexto.wikidata import era_to_edges


def test_era_overlap_edges():
    eras = {
        "Q1": [(2009, 2017)],  # Obama era
        "Q2": [(2009, 2017)],  # Biden VP era
        "Q3": [(1850, 1860)],  # old era
    }
    edges = era_to_edges(eras)

    # Q1 and Q2 fully overlap
    q1_q2 = [(a, b, t, w) for a, b, t, w in edges if {a, b} == {"Q1", "Q2"}]
    assert len(q1_q2) == 1
    assert q1_q2[0][3] == 1.0  # full overlap

    # Q1 and Q3 don't overlap
    q1_q3 = [(a, b, t, w) for a, b, t, w in edges if {a, b} == {"Q1", "Q3"}]
    assert len(q1_q3) == 0


def test_era_partial_overlap():
    eras = {
        "Q1": [(2000, 2010)],
        "Q2": [(2005, 2015)],
    }
    edges = era_to_edges(eras)
    q1_q2 = [(a, b, t, w) for a, b, t, w in edges if {a, b} == {"Q1", "Q2"}]
    assert len(q1_q2) == 1
    assert 0 < q1_q2[0][3] < 1.0  # partial overlap
