from category_contexto.blurbs import build_blurb, build_blurbs


def test_build_blurb_basic():
    entity = {
        "id": "Q6279",
        "name": "Joe Biden",
        "description": "46th president of the United States",
    }
    props = {
        "parties": {"Q29552"},
        "positions": {"Q11696"},
    }
    party_labels = {"Q29552": "Democratic Party"}
    position_labels = {"Q11696": "President of the United States"}

    blurb = build_blurb(entity, props, party_labels, position_labels)

    assert "Joe Biden" in blurb
    assert "46th president" in blurb
    assert "Democratic Party" in blurb
    assert "President of the United States" in blurb


def test_build_blurb_missing_props():
    entity = {
        "id": "Q999",
        "name": "Unknown Person",
        "description": "",
    }
    props = {"parties": set(), "positions": set()}

    blurb = build_blurb(entity, props, {}, {})
    assert "Unknown Person" in blurb


def test_build_blurbs_batch():
    entities = [
        {"id": "Q1", "name": "Person A", "description": "desc A"},
        {"id": "Q2", "name": "Person B", "description": "desc B"},
    ]
    all_props = {
        "Q1": {"parties": set(), "positions": set()},
        "Q2": {"parties": set(), "positions": set()},
    }
    result = build_blurbs(entities, all_props, {}, {})
    assert len(result) == 2
    assert result["Q1"].startswith("Person A")
    assert result["Q2"].startswith("Person B")
