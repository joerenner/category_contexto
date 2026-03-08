import requests

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

POLITICIANS_QUERY = """
SELECT DISTINCT ?person ?personLabel ?personDescription WHERE {
  ?person wdt:P31 wd:Q5 .
  ?person wdt:P27 wd:Q30 .
  ?person wdt:P39 ?position .
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
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY ?personLabel
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
