from unittest.mock import patch, MagicMock
from category_contexto.wikidata import fetch_politician_properties


MOCK_PROPERTIES_RESPONSE = {
    "results": {
        "bindings": [
            {
                "person": {"value": "http://www.wikidata.org/entity/Q6279"},
                "party": {"value": "http://www.wikidata.org/entity/Q29552"},
                "partyLabel": {"value": "Democratic Party"},
                "position": {"value": "http://www.wikidata.org/entity/Q11696"},
                "positionLabel": {"value": "President of the United States"},
            },
            {
                "person": {"value": "http://www.wikidata.org/entity/Q76"},
                "party": {"value": "http://www.wikidata.org/entity/Q29552"},
                "partyLabel": {"value": "Democratic Party"},
                "position": {"value": "http://www.wikidata.org/entity/Q11696"},
                "positionLabel": {"value": "President of the United States"},
            },
            {
                "person": {"value": "http://www.wikidata.org/entity/Q22686"},
                "party": {"value": "http://www.wikidata.org/entity/Q29468"},
                "partyLabel": {"value": "Republican Party"},
                "position": {"value": "http://www.wikidata.org/entity/Q11696"},
                "positionLabel": {"value": "President of the United States"},
            },
        ]
    }
}


def test_fetch_politician_properties():
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_PROPERTIES_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    entity_ids = ["Q6279", "Q76", "Q22686"]

    with patch("category_contexto.wikidata.requests.get", return_value=mock_resp):
        props = fetch_politician_properties(entity_ids)

    assert props["Q6279"]["parties"] == {"Q29552"}
    assert props["Q6279"]["positions"] == {"Q11696"}
    assert props["Q76"]["parties"] == {"Q29552"}
    assert props["Q22686"]["parties"] == {"Q29468"}


def test_properties_to_edges():
    from category_contexto.wikidata import properties_to_edges

    props = {
        "Q6279": {"parties": {"Q29552"}, "positions": {"Q11696"}},
        "Q76":   {"parties": {"Q29552"}, "positions": {"Q11696"}},
        "Q22686": {"parties": {"Q29468"}, "positions": {"Q11696"}},
    }
    edges = properties_to_edges(props)

    biden_obama = [(a, b, t, w) for a, b, t, w in edges
                   if {a, b} == {"Q6279", "Q76"}]
    edge_types = {t for _, _, t, _ in biden_obama}
    assert "same_party" in edge_types
    assert "same_position" in edge_types

    biden_trump = [(a, b, t, w) for a, b, t, w in edges
                   if {a, b} == {"Q6279", "Q22686"}]
    edge_types_bt = {t for _, _, t, _ in biden_trump}
    assert "same_position" in edge_types_bt
    assert "same_party" not in edge_types_bt
