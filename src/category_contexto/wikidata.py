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


ERA_QUERY = """
SELECT ?person ?position ?positionLabel ?start ?end WHERE {{
  VALUES ?person {{ {entity_values} }}
  ?person p:P39 ?statement .
  ?statement ps:P39 ?position .
  OPTIONAL {{ ?statement pq:P580 ?start . }}
  OPTIONAL {{ ?statement pq:P582 ?end . }}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "en" .
  }}
}}
"""


def fetch_politician_eras(entity_ids: list[str]) -> dict[str, list[tuple[int, int]]]:
    """Fetch service periods for entities. Returns {entity_id: [(start_year, end_year), ...]}."""
    eras: dict[str, list[tuple[int, int]]] = {}
    for i in range(0, len(entity_ids), PROPERTIES_BATCH_SIZE):
        batch = entity_ids[i : i + PROPERTIES_BATCH_SIZE]
        entity_values = " ".join(f"wd:{eid}" for eid in batch)
        query = ERA_QUERY.format(entity_values=entity_values)

        resp = requests.get(
            WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "CategoryContexto/0.1 (https://github.com/joerenner/category_contexto)"},
        )
        resp.raise_for_status()
        batch_eras = _parse_era_response(resp.json())
        for qid, periods in batch_eras.items():
            eras.setdefault(qid, []).extend(periods)
    return eras


def _parse_year(value: str) -> int | None:
    """Extract year from a Wikidata date value, returning None if unparseable."""
    try:
        return int(value[:4])
    except (ValueError, IndexError):
        return None


def _parse_era_response(data: dict) -> dict[str, list[tuple[int, int]]]:
    eras: dict[str, list[tuple[int, int]]] = {}
    for binding in data["results"]["bindings"]:
        if "start" not in binding:
            continue
        start_year = _parse_year(binding["start"]["value"])
        if start_year is None:
            continue
        qid = binding["person"]["value"].split("/")[-1]
        if "end" in binding:
            end_year = _parse_year(binding["end"]["value"])
            if end_year is None:
                end_year = 2026
        else:
            end_year = 2026
        eras.setdefault(qid, []).append((start_year, end_year))
    return eras


def era_to_edges(eras: dict[str, list[tuple[int, int]]]) -> list[tuple[str, str, str, float]]:
    """Generate same_era edges weighted by overlap of service periods."""
    edges = []
    entity_ids = list(eras.keys())

    for a, b in combinations(entity_ids, 2):
        overlap = _compute_overlap_years(eras[a], eras[b])
        if overlap <= 0:
            continue
        total_a = _compute_total_years(eras[a])
        total_b = _compute_total_years(eras[b])
        max_total = max(total_a, total_b)
        if max_total == 0:
            continue
        weight = overlap / max_total
        edges.append((a, b, "same_era", weight))

    return edges


def _compute_overlap_years(
    periods_a: list[tuple[int, int]], periods_b: list[tuple[int, int]]
) -> int:
    """Compute total overlap in years between two sets of service periods."""
    total = 0
    for start_a, end_a in periods_a:
        for start_b, end_b in periods_b:
            overlap_start = max(start_a, start_b)
            overlap_end = min(end_a, end_b)
            if overlap_end > overlap_start:
                total += overlap_end - overlap_start
    return total


def _compute_total_years(periods: list[tuple[int, int]]) -> int:
    """Compute total years of service across all periods."""
    return sum(max(0, end - start) for start, end in periods)


STATE_QUERY = """
SELECT ?person ?state ?stateLabel WHERE {{
  VALUES ?person {{ {entity_values} }}
  ?person p:P39 ?statement .
  {{
    ?statement pq:P768 ?state .
  }} UNION {{
    ?statement pq:P1001 ?state .
  }}
  ?state wdt:P31/wdt:P279* wd:Q35657 .
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "en" .
  }}
}}
"""


def fetch_politician_states(entity_ids: list[str]) -> dict[str, set[str]]:
    """Fetch US states represented by each politician.

    Returns {entity_id: {state_qid, ...}}.
    """
    states: dict[str, set[str]] = {}
    for i in range(0, len(entity_ids), PROPERTIES_BATCH_SIZE):
        batch = entity_ids[i : i + PROPERTIES_BATCH_SIZE]
        entity_values = " ".join(f"wd:{eid}" for eid in batch)
        query = STATE_QUERY.format(entity_values=entity_values)

        resp = requests.get(
            WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "CategoryContexto/0.1 (https://github.com/joerenner/category_contexto)"},
        )
        resp.raise_for_status()

        for binding in resp.json()["results"]["bindings"]:
            qid = binding["person"]["value"].split("/")[-1]
            state_qid = binding["state"]["value"].split("/")[-1]
            states.setdefault(qid, set()).add(state_qid)

    return states


def state_to_edges(states: dict[str, set[str]]) -> list[tuple[str, str, str, float]]:
    """Generate same_state edges for politicians who represented the same state."""
    edges = []
    entity_ids = list(states.keys())

    for a, b in combinations(entity_ids, 2):
        shared_states = states[a] & states[b]
        if shared_states:
            edges.append((a, b, "same_state", 0.8))

    return edges


SITELINKS_QUERY = """
SELECT ?person ?article WHERE {{
  VALUES ?person {{ {entity_values} }}
  ?article schema:about ?person .
  ?article schema:isPartOf <https://en.wikipedia.org/> .
}}
"""


def fetch_wikipedia_titles(entity_ids: list[str]) -> dict[str, str]:
    """Fetch English Wikipedia article titles for entities.

    Returns {entity_id: "Wikipedia_Article_Title"}.
    """
    all_titles: dict[str, str] = {}
    for i in range(0, len(entity_ids), PROPERTIES_BATCH_SIZE):
        batch = entity_ids[i : i + PROPERTIES_BATCH_SIZE]
        entity_values = " ".join(f"wd:{eid}" for eid in batch)
        query = SITELINKS_QUERY.format(entity_values=entity_values)

        resp = requests.get(
            WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "CategoryContexto/0.1 (https://github.com/joerenner/category_contexto)"},
        )
        resp.raise_for_status()

        for binding in resp.json()["results"]["bindings"]:
            qid = binding["person"]["value"].split("/")[-1]
            # Extract title from URL: https://en.wikipedia.org/wiki/Joe_Biden -> Joe Biden
            article_url = binding["article"]["value"]
            title = article_url.split("/wiki/")[-1].replace("_", " ")
            all_titles[qid] = title

    return all_titles


POSITION_TO_BRANCH = {
    # Executive
    "Q11696": "executive",      # President
    "Q11699": "executive",      # Vice President
    "Q311360": "executive",     # Secretary of State
    "Q14211": "executive",      # Secretary of Defense
    "Q842606": "executive",     # Attorney General
    "Q1255921": "executive",    # Secretary of Treasury
    # Legislative
    "Q4416090": "legislative",  # US Senator
    "Q13218630": "legislative", # US House Representative
    # State executive
    "Q889821": "state_executive", # Governor
}


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

        # same_branch: check if any positions map to the same branch
        branches_a = {POSITION_TO_BRANCH[p] for p in props[a]["positions"] if p in POSITION_TO_BRANCH}
        branches_b = {POSITION_TO_BRANCH[p] for p in props[b]["positions"] if p in POSITION_TO_BRANCH}
        shared_branches = branches_a & branches_b
        if shared_branches and not shared_positions:
            edges.append((a, b, "same_branch", 0.5))

    return edges
