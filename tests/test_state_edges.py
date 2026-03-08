from category_contexto.wikidata import state_to_edges


def test_same_state_edges():
    states = {
        "Q1": {"Q99"},      # California
        "Q2": {"Q99"},      # California
        "Q3": {"Q100"},     # Texas
    }
    edges = state_to_edges(states)

    q1_q2 = [(a, b, t, w) for a, b, t, w in edges if {a, b} == {"Q1", "Q2"}]
    assert len(q1_q2) == 1
    assert q1_q2[0][2] == "same_state"
    assert q1_q2[0][3] == 0.8

    q1_q3 = [(a, b, t, w) for a, b, t, w in edges if {a, b} == {"Q1", "Q3"}]
    assert len(q1_q3) == 0


def test_no_states():
    states = {}
    edges = state_to_edges(states)
    assert len(edges) == 0
