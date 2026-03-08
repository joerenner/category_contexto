import numpy as np
from unittest.mock import patch, MagicMock
from category_contexto.pipeline import run_politics_pipeline
from category_contexto.storage import RankingStore


def test_pipeline_end_to_end(tmp_db_path):
    mock_entities = [
        {"id": "Q1", "name": "Person A", "description": "president"},
        {"id": "Q2", "name": "Person B", "description": "senator"},
        {"id": "Q3", "name": "Person C", "description": "governor"},
    ]
    mock_props = {
        "Q1": {"parties": {"P1"}, "positions": {"O1"}},
        "Q2": {"parties": {"P1"}, "positions": {"O2"}},
        "Q3": {"parties": {"P2"}, "positions": {"O1"}},
    }
    mock_embeddings = {
        "Q1": np.array([1.0, 0.0, 0.0]),
        "Q2": np.array([0.9, 0.1, 0.0]),
        "Q3": np.array([0.0, 0.0, 1.0]),
    }

    with patch("category_contexto.pipeline.fetch_politicians", return_value=mock_entities), \
         patch("category_contexto.pipeline.fetch_politician_properties", return_value=(mock_props, {"P1": "Party A", "P2": "Party B"}, {"O1": "Office 1", "O2": "Office 2"})), \
         patch("category_contexto.pipeline.generate_embeddings", return_value=mock_embeddings):

        store = run_politics_pipeline(db_path=tmp_db_path, alpha=0.5)

    rank = store.lookup_by_name("politics", "Person A", "Person B")
    assert rank is not None
    assert isinstance(rank, int)
    assert rank >= 1

    entities = store.get_entity_list("politics")
    assert len(entities) == 3
