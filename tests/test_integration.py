import pytest
from category_contexto.pipeline import run_politics_pipeline


@pytest.mark.integration
def test_real_pipeline(tmp_db_path):
    """Smoke test: run the real pipeline (requires OPENAI_API_KEY).

    Run with: pytest tests/test_integration.py -m integration -v
    """
    store = run_politics_pipeline(db_path=tmp_db_path, alpha=0.3)

    entities = store.get_entity_list("politics")
    assert len(entities) > 50, f"Expected 50+ entities, got {len(entities)}"

    rank_obama = store.lookup_by_name("politics", "Joe Biden", "Barack Obama")
    assert rank_obama is not None, "Obama not found in rankings"
    assert rank_obama < 50, f"Expected Obama in top 50 for Biden, got #{rank_obama}"
