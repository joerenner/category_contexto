import json
from unittest.mock import patch, MagicMock
from category_contexto.wikidata import fetch_politicians


MOCK_SPARQL_RESPONSE = {
    "results": {
        "bindings": [
            {
                "person": {"value": "http://www.wikidata.org/entity/Q6279"},
                "personLabel": {"value": "Joe Biden"},
                "personDescription": {"value": "46th president of the United States"},
            },
            {
                "person": {"value": "http://www.wikidata.org/entity/Q22686"},
                "personLabel": {"value": "Donald Trump"},
                "personDescription": {"value": "45th president of the United States"},
            },
        ]
    }
}


def test_fetch_politicians_parses_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_SPARQL_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("category_contexto.wikidata.requests.get", return_value=mock_resp):
        entities = fetch_politicians()

    assert len(entities) == 2
    assert entities[0]["id"] == "Q6279"
    assert entities[0]["name"] == "Joe Biden"
    assert entities[0]["description"] == "46th president of the United States"


def test_fetch_politicians_deduplicates():
    binding = {
        "person": {"value": "http://www.wikidata.org/entity/Q6279"},
        "personLabel": {"value": "Joe Biden"},
        "personDescription": {"value": "46th president of the United States"},
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": {"bindings": [binding, binding]}}
    mock_resp.raise_for_status = MagicMock()

    with patch("category_contexto.wikidata.requests.get", return_value=mock_resp):
        entities = fetch_politicians()

    assert len(entities) == 1
