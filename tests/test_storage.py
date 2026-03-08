from category_contexto.storage import RankingStore


def test_save_and_lookup(tmp_db_path):
    store = RankingStore(tmp_db_path)
    rankings = {
        "Q1": {"Q2": 1, "Q3": 2},
        "Q2": {"Q1": 1, "Q3": 2},
    }
    entities = {
        "Q1": "Joe Biden",
        "Q2": "Barack Obama",
        "Q3": "Donald Trump",
    }
    store.save_rankings("politics", rankings, entities)

    assert store.lookup("politics", "Q1", "Q2") == 1
    assert store.lookup("politics", "Q1", "Q3") == 2
    assert store.lookup("politics", "Q1", "Q999") is None


def test_lookup_by_name(tmp_db_path):
    store = RankingStore(tmp_db_path)
    rankings = {"Q1": {"Q2": 1, "Q3": 2}}
    entities = {
        "Q1": "Joe Biden",
        "Q2": "Barack Obama",
        "Q3": "Donald Trump",
    }
    store.save_rankings("politics", rankings, entities)

    assert store.lookup_by_name("politics", "Joe Biden", "Barack Obama") == 1
    assert store.lookup_by_name("politics", "Joe Biden", "donald trump") == 2


def test_get_entity_list(tmp_db_path):
    store = RankingStore(tmp_db_path)
    rankings = {"Q1": {"Q2": 1}}
    entities = {"Q1": "Joe Biden", "Q2": "Barack Obama"}
    store.save_rankings("politics", rankings, entities)

    result = store.get_entity_list("politics")
    assert len(result) == 2
    names = {e["name"] for e in result}
    assert "Joe Biden" in names
