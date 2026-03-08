from unittest.mock import patch, MagicMock
from category_contexto.wiki_context import fetch_wikipedia_summaries


def test_fetch_wikipedia_summaries():
    mock_response = {
        "query": {
            "pages": {
                "12345": {
                    "pageid": 12345,
                    "title": "Joe Biden",
                    "extract": "Joseph Robinette Biden Jr. is an American politician who served as the 46th president."
                }
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_response
    mock_resp.raise_for_status = MagicMock()

    with patch("category_contexto.wiki_context.requests.get", return_value=mock_resp), \
         patch("category_contexto.wiki_context.sleep"):
        result = fetch_wikipedia_summaries(["Joe Biden"])

    assert "Joe Biden" in result
    assert "president" in result["Joe Biden"]


def test_fetch_wikipedia_missing_page():
    mock_response = {
        "query": {
            "pages": {
                "-1": {"title": "Nonexistent Person", "missing": ""}
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_response
    mock_resp.raise_for_status = MagicMock()

    with patch("category_contexto.wiki_context.requests.get", return_value=mock_resp), \
         patch("category_contexto.wiki_context.sleep"):
        result = fetch_wikipedia_summaries(["Nonexistent Person"])

    assert len(result) == 0
