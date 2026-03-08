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


def fetch_politician_properties(entity_ids: list[str]) -> dict[str, dict]:
    """Fetch properties in batches to avoid URL length limits."""
    all_props: dict[str, dict] = {}
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
        batch_props = _parse_properties_response(resp.json())
        all_props.update(batch_props)
    return all_props


def _parse_properties_response(data: dict) -> dict[str, dict]:
    props: dict[str, dict] = {}
    for binding in data["results"]["bindings"]:
        qid = binding["person"]["value"].split("/")[-1]
        if qid not in props:
            props[qid] = {"parties": set(), "positions": set()}
        if "party" in binding:
            props[qid]["parties"].add(binding["party"]["value"].split("/")[-1])
        if "position" in binding:
            props[qid]["positions"].add(binding["position"]["value"].split("/")[-1])
    return props


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
