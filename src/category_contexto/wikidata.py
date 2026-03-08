from itertools import combinations

import requests

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

POLITICIANS_QUERY = """
SELECT DISTINCT ?person ?personLabel ?personDescription ?sitelinks WHERE {
  ?person wdt:P31 wd:Q5 .
  ?person wdt:P27 wd:Q30 .
  ?person wdt:P39 ?position .
  ?person wikibase:sitelinks ?sitelinks .
  VALUES ?position {
    wd:Q11696
    wd:Q11699
    wd:Q4416090
    wd:Q13218630
    wd:Q889821
    wd:Q311360
    wd:Q14211
    wd:Q842606
    wd:Q1255921
  }
  FILTER(?sitelinks > 15)
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY DESC(?sitelinks)
"""


def fetch_politicians() -> list[dict]:
    resp = requests.get(
        WIKIDATA_SPARQL_URL,
        params={"query": POLITICIANS_QUERY, "format": "json"},
        headers={"User-Agent": "CategoryContexto/0.1 (https://github.com/joerenner/category_contexto)"},
    )
    resp.raise_for_status()
    return _parse_entity_response(resp.json())


def _parse_entity_response(data: dict) -> list[dict]:
    seen = set()
    entities = []
    for binding in data["results"]["bindings"]:
        qid = binding["person"]["value"].split("/")[-1]
        if qid in seen:
            continue
        seen.add(qid)
        entities.append({
            "id": qid,
            "name": binding["personLabel"]["value"],
            "description": binding.get("personDescription", {}).get("value", ""),
        })
    return entities


PROPERTIES_QUERY = """
SELECT ?person ?party ?partyLabel ?position ?positionLabel WHERE {{
  VALUES ?person {{ {entity_values} }}
  OPTIONAL {{ ?person wdt:P102 ?party . }}
  OPTIONAL {{ ?person wdt:P39 ?position . }}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "en" .
  }}
}}
"""


PROPERTIES_BATCH_SIZE = 200


def fetch_politician_properties(entity_ids: list[str]) -> tuple[dict[str, dict], dict[str, str], dict[str, str]]:
    """Fetch properties in batches to avoid URL length limits."""
    all_props: dict[str, dict] = {}
    all_party_labels: dict[str, str] = {}
    all_position_labels: dict[str, str] = {}
    for i in range(0, len(entity_ids), PROPERTIES_BATCH_SIZE):
        batch = entity_ids[i : i + PROPERTIES_BATCH_SIZE]
        entity_values = " ".join(f"wd:{eid}" for eid in batch)
        query = PROPERTIES_QUERY.format(entity_values=entity_values)

        resp = requests.get(
            WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "CategoryContexto/0.1 (https://github.com/joerenner/category_contexto)"},
        )
        resp.raise_for_status()
        batch_props, batch_party_labels, batch_position_labels = _parse_properties_response(resp.json())
        all_props.update(batch_props)
        all_party_labels.update(batch_party_labels)
        all_position_labels.update(batch_position_labels)
    return all_props, all_party_labels, all_position_labels


def _parse_properties_response(data: dict) -> tuple[dict[str, dict], dict[str, str], dict[str, str]]:
    props: dict[str, dict] = {}
    party_labels: dict[str, str] = {}
    position_labels: dict[str, str] = {}
    for binding in data["results"]["bindings"]:
        qid = binding["person"]["value"].split("/")[-1]
        if qid not in props:
            props[qid] = {"parties": set(), "positions": set()}
        if "party" in binding:
            party_id = binding["party"]["value"].split("/")[-1]
            props[qid]["parties"].add(party_id)
            if "partyLabel" in binding:
                party_labels[party_id] = binding["partyLabel"]["value"]
        if "position" in binding:
            position_id = binding["position"]["value"].split("/")[-1]
            props[qid]["positions"].add(position_id)
            if "positionLabel" in binding:
                position_labels[position_id] = binding["positionLabel"]["value"]
    return props, party_labels, position_labels


def properties_to_edges(props: dict[str, dict]) -> list[tuple[str, str, str, float]]:
    edges = []
    entity_ids = list(props.keys())

    for a, b in combinations(entity_ids, 2):
        shared_parties = props[a]["parties"] & props[b]["parties"]
        shared_positions = props[a]["positions"] & props[b]["positions"]

        for party in shared_parties:
            edges.append((a, b, "same_party", 1.0))
        for position in shared_positions:
            edges.append((a, b, "same_position", 1.0))

    return edges
