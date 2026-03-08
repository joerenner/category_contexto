from unittest.mock import patch, MagicMock
from category_contexto.wiki_context import fetch_wikipedia_summaries


def test_fetch_wikipedia_summaries_batch():
    mock_response = {
        "query": {
            "pages": {
                "12345": {
                    "pageid": 12345,
                    "title": "Joe Biden",
                    "extract": "Joseph Robinette Biden Jr. is an American politician who served as the 46th president."
                },
                "67890": {
                    "pageid": 67890,
                    "title": "Barack Obama",
                    "extract": "Barack Hussein Obama II is an American politician who served as the 44th president."
                }
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_response
    mock_resp.raise_for_status = MagicMock()

    with patch("category_contexto.wiki_context.requests.get", return_value=mock_resp), \
         patch("category_contexto.wiki_context.sleep"):
        result = fetch_wikipedia_summaries(["Joe Biden", "Barack Obama"])

    assert len(result) == 2
    assert "president" in result["Joe Biden"]
    assert "president" in result["Barack Obama"]


def test_fetch_wikipedia_handles_redirects():
    mock_response = {
        "query": {
            "normalized": [{"from": "jimmy carter", "to": "Jimmy Carter"}],
            "redirects": [{"from": "Jimmy Carter", "to": "Jimmy Carter"}],
            "pages": {
                "12345": {
                    "pageid": 12345,
                    "title": "Jimmy Carter",
                    "extract": "James Earl Carter Jr. was an American politician."
                }
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_response
    mock_resp.raise_for_status = MagicMock()

    with patch("category_contexto.wiki_context.requests.get", return_value=mock_resp), \
         patch("category_contexto.wiki_context.sleep"):
        result = fetch_wikipedia_summaries(["jimmy carter"])

    assert "jimmy carter" in result


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
