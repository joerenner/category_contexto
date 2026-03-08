# Phase 1: Core Ranking System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the core entity ranking system for one category (US Politics), using Wikidata for entity lists + graph edges, OpenAI for embeddings, and a blended similarity score. Validate that rankings "feel right" via a CLI.

**Architecture:** Data pipeline fetches entities from Wikidata SPARQL, builds a weighted graph (same party/office/era edges), constructs text blurbs from Wikidata facts, embeds them via OpenAI, blends graph + embedding similarity, precomputes all rankings into SQLite.

**Tech Stack:** Python 3.10+, pip, requests, numpy, scipy, openai, sqlite3 (stdlib)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/category_contexto/__init__.py`
- Create: `src/category_contexto/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`
- Create: `.env.example`

**Step 1: Create .gitignore**

```
__pycache__/
*.pyc
.env
*.db
*.egg-info/
dist/
build/
.venv/
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "category-contexto"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "numpy>=1.24",
    "scipy>=1.10",
    "openai>=1.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-mock>=3.10",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]
```

**Step 3: Create src/category_contexto/__init__.py**

Empty file.

**Step 4: Create src/category_contexto/config.py**

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "rankings.db"
```

**Step 5: Create tests/__init__.py and tests/conftest.py**

`tests/__init__.py` — empty file.

`tests/conftest.py`:
```python
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def tmp_db_path(tmp_path):
    return tmp_path / "test_rankings.db"
```

**Step 6: Create .env.example**

```
OPENAI_API_KEY=sk-your-key-here
```

**Step 7: Create data/ directory**

```bash
mkdir -p data
```

**Step 8: Install project in editable mode**

```bash
pip install -e ".[dev]"
```

**Step 9: Run pytest to verify setup**

Run: `pytest --co -q`
Expected: "no tests ran" (but no import errors)

**Step 10: Commit**

```bash
git add .gitignore pyproject.toml src/ tests/ .env.example data/
git commit -m "feat: project scaffolding with deps and config"
```

---

### Task 2: Wikidata Entity Fetcher

**Files:**
- Create: `src/category_contexto/wikidata.py`
- Create: `tests/test_wikidata.py`

**Step 1: Write the failing test**

`tests/test_wikidata.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_wikidata.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write implementation**

`src/category_contexto/wikidata.py`:
```python
import requests

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# Fetch notable US politicians: presidents, senators, house reps, governors, VP, cabinet
POLITICIANS_QUERY = """
SELECT DISTINCT ?person ?personLabel ?personDescription WHERE {
  ?person wdt:P31 wd:Q5 .           # is a human
  ?person wdt:P27 wd:Q30 .           # citizen of USA
  ?person wdt:P39 ?position .         # held some position
  VALUES ?position {
    wd:Q11696      # President of the US
    wd:Q11699      # Vice President of the US
    wd:Q4416090    # US Senator
    wd:Q13218630   # US House Representative
    wd:Q889821     # US state governor
    wd:Q311360     # US Secretary of State
    wd:Q14211      # US Secretary of Defense
    wd:Q842606     # US Attorney General
    wd:Q1255921    # US Secretary of the Treasury
  }
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY ?personLabel
"""


def fetch_politicians() -> list[dict]:
    """Fetch US politicians from Wikidata. Returns list of {id, name, description}."""
    resp = requests.get(
        WIKIDATA_SPARQL_URL,
        params={"query": POLITICIANS_QUERY, "format": "json"},
        headers={"User-Agent": "CategoryContexto/0.1 (https://github.com/joerenner/category_contexto)"},
    )
    resp.raise_for_status()
    return _parse_entity_response(resp.json())


def _parse_entity_response(data: dict) -> list[dict]:
    """Parse SPARQL JSON response into deduplicated entity list."""
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_wikidata.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add src/category_contexto/wikidata.py tests/test_wikidata.py
git commit -m "feat: wikidata entity fetcher for US politicians"
```

---

### Task 3: Wikidata Graph Builder — Edge Fetching

**Files:**
- Create: `src/category_contexto/graph.py`
- Create: `tests/test_graph.py`

**Step 1: Write the failing test**

`tests/test_graph.py`:
```python
from category_contexto.graph import build_graph_from_edges, compute_graph_similarity


def make_edges():
    """Two politicians sharing party and office; one sharing only party."""
    return [
        ("Q6279", "Q22686", "same_office", 1.0),   # Biden & Trump: both presidents
        ("Q6279", "Q76",    "same_party",  1.0),    # Biden & Obama: same party
        ("Q6279", "Q22686", "same_era",    0.8),    # Biden & Trump: overlapping era
        ("Q76",   "Q6279",  "same_office", 1.0),    # Obama & Biden: both presidents
    ]


def test_build_graph_from_edges():
    graph = build_graph_from_edges(make_edges())
    # Biden should have edges to both Trump and Obama
    assert "Q22686" in graph["Q6279"]
    assert "Q76" in graph["Q6279"]
    # Edge to Trump has 2 edge types (same_office + same_era)
    assert len(graph["Q6279"]["Q22686"]) == 2


def test_graph_similarity_shared_neighbors():
    graph = build_graph_from_edges(make_edges())
    # Biden-Obama share party + office edges = more similar than two unrelated
    sim_biden_obama = compute_graph_similarity(graph, "Q6279", "Q76")
    assert sim_biden_obama > 0.0
    # Biden-Trump share office + era
    sim_biden_trump = compute_graph_similarity(graph, "Q6279", "Q22686")
    assert sim_biden_trump > 0.0


def test_graph_similarity_self_is_one():
    graph = build_graph_from_edges(make_edges())
    assert compute_graph_similarity(graph, "Q6279", "Q6279") == 1.0


def test_graph_similarity_unknown_entity():
    graph = build_graph_from_edges(make_edges())
    assert compute_graph_similarity(graph, "Q6279", "Q99999") == 0.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_graph.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write implementation**

`src/category_contexto/graph.py`:
```python
from collections import defaultdict


def build_graph_from_edges(
    edges: list[tuple[str, str, str, float]],
) -> dict[str, dict[str, list[tuple[str, float]]]]:
    """Build adjacency structure from (entity_a, entity_b, edge_type, weight) tuples.

    Returns: {entity_id: {neighbor_id: [(edge_type, weight), ...]}}
    """
    graph: dict[str, dict[str, list[tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
    for entity_a, entity_b, edge_type, weight in edges:
        graph[entity_a][entity_b].append((edge_type, weight))
        graph[entity_b][entity_a].append((edge_type, weight))
    return dict(graph)


def _edge_feature_vector(edge_list: list[tuple[str, float]]) -> dict[str, float]:
    """Convert edge list to {edge_type: weight} dict, summing duplicate types."""
    features: dict[str, float] = defaultdict(float)
    for edge_type, weight in edge_list:
        features[edge_type] += weight
    return dict(features)


def _entity_profile(graph: dict, entity_id: str) -> dict[str, float]:
    """Build a weighted feature vector for an entity from all its edges.

    Each feature is (neighbor, edge_type) -> weight. This captures both
    WHO they connect to and HOW.
    """
    profile: dict[str, float] = defaultdict(float)
    neighbors = graph.get(entity_id, {})
    for neighbor_id, edge_list in neighbors.items():
        for edge_type, weight in edge_list:
            profile[f"{neighbor_id}:{edge_type}"] = weight
            # Also add type-only features for generalization
            profile[f"_type:{edge_type}"] += weight
    return dict(profile)


def compute_graph_similarity(graph: dict, entity_a: str, entity_b: str) -> float:
    """Weighted Jaccard similarity between two entities based on their edge profiles."""
    if entity_a == entity_b:
        return 1.0

    profile_a = _entity_profile(graph, entity_a)
    profile_b = _entity_profile(graph, entity_b)

    if not profile_a or not profile_b:
        return 0.0

    all_keys = set(profile_a.keys()) | set(profile_b.keys())
    intersection = 0.0
    union = 0.0
    for key in all_keys:
        va = profile_a.get(key, 0.0)
        vb = profile_b.get(key, 0.0)
        intersection += min(va, vb)
        union += max(va, vb)

    return intersection / union if union > 0 else 0.0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_graph.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add src/category_contexto/graph.py tests/test_graph.py
git commit -m "feat: graph builder and weighted Jaccard similarity"
```

---

### Task 4: Wikidata Graph Edge Fetcher

**Files:**
- Modify: `src/category_contexto/wikidata.py`
- Create: `tests/test_wikidata_edges.py`

This task adds SPARQL queries to fetch the relationship data needed for graph construction: party membership, positions held, and active era.

**Step 1: Write the failing test**

`tests/test_wikidata_edges.py`:
```python
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

    # Biden & Obama share party + position = 2 edges
    biden_obama = [(a, b, t, w) for a, b, t, w in edges
                   if {a, b} == {"Q6279", "Q76"}]
    edge_types = {t for _, _, t, _ in biden_obama}
    assert "same_party" in edge_types
    assert "same_position" in edge_types

    # Biden & Trump share position but NOT party
    biden_trump = [(a, b, t, w) for a, b, t, w in edges
                   if {a, b} == {"Q6279", "Q22686"}]
    edge_types_bt = {t for _, _, t, _ in biden_trump}
    assert "same_position" in edge_types_bt
    assert "same_party" not in edge_types_bt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_wikidata_edges.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

Add to `src/category_contexto/wikidata.py`:
```python
from itertools import combinations

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


def fetch_politician_properties(entity_ids: list[str]) -> dict[str, dict]:
    """Fetch party and position data for a list of entity IDs."""
    entity_values = " ".join(f"wd:{eid}" for eid in entity_ids)
    query = PROPERTIES_QUERY.format(entity_values=entity_values)

    resp = requests.get(
        WIKIDATA_SPARQL_URL,
        params={"query": query, "format": "json"},
        headers={"User-Agent": "CategoryContexto/0.1 (https://github.com/joerenner/category_contexto)"},
    )
    resp.raise_for_status()
    return _parse_properties_response(resp.json())


def _parse_properties_response(data: dict) -> dict[str, dict]:
    """Parse SPARQL properties response into {entity_id: {parties: set, positions: set}}."""
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
    """Convert entity properties into graph edges.

    Creates edges between entities that share parties or positions.
    """
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_wikidata_edges.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add src/category_contexto/wikidata.py tests/test_wikidata_edges.py
git commit -m "feat: fetch politician properties and generate graph edges from Wikidata"
```

---

### Task 5: Blurb Builder

**Files:**
- Create: `src/category_contexto/blurbs.py`
- Create: `tests/test_blurbs.py`

**Step 1: Write the failing test**

`tests/test_blurbs.py`:
```python
from category_contexto.blurbs import build_blurb, build_blurbs


def test_build_blurb_basic():
    entity = {
        "id": "Q6279",
        "name": "Joe Biden",
        "description": "46th president of the United States",
    }
    props = {
        "parties": {"Q29552"},
        "positions": {"Q11696"},
    }
    party_labels = {"Q29552": "Democratic Party"}
    position_labels = {"Q11696": "President of the United States"}

    blurb = build_blurb(entity, props, party_labels, position_labels)

    assert "Joe Biden" in blurb
    assert "46th president" in blurb
    assert "Democratic Party" in blurb
    assert "President of the United States" in blurb


def test_build_blurb_missing_props():
    entity = {
        "id": "Q999",
        "name": "Unknown Person",
        "description": "",
    }
    props = {"parties": set(), "positions": set()}

    blurb = build_blurb(entity, props, {}, {})
    assert "Unknown Person" in blurb


def test_build_blurbs_batch():
    entities = [
        {"id": "Q1", "name": "Person A", "description": "desc A"},
        {"id": "Q2", "name": "Person B", "description": "desc B"},
    ]
    all_props = {
        "Q1": {"parties": set(), "positions": set()},
        "Q2": {"parties": set(), "positions": set()},
    }
    result = build_blurbs(entities, all_props, {}, {})
    assert len(result) == 2
    assert result["Q1"].startswith("Person A")
    assert result["Q2"].startswith("Person B")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_blurbs.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write implementation**

`src/category_contexto/blurbs.py`:
```python
def build_blurb(
    entity: dict,
    props: dict,
    party_labels: dict[str, str],
    position_labels: dict[str, str],
) -> str:
    """Build a text blurb for an entity from its Wikidata data."""
    parts = [entity["name"] + "."]

    if entity.get("description"):
        parts.append(entity["description"].capitalize() + ".")

    positions = [position_labels[p] for p in props.get("positions", set()) if p in position_labels]
    if positions:
        parts.append("Positions held: " + ", ".join(positions) + ".")

    parties = [party_labels[p] for p in props.get("parties", set()) if p in party_labels]
    if parties:
        parts.append("Party: " + ", ".join(parties) + ".")

    return " ".join(parts)


def build_blurbs(
    entities: list[dict],
    all_props: dict[str, dict],
    party_labels: dict[str, str],
    position_labels: dict[str, str],
) -> dict[str, str]:
    """Build blurbs for all entities. Returns {entity_id: blurb}."""
    return {
        entity["id"]: build_blurb(
            entity,
            all_props.get(entity["id"], {"parties": set(), "positions": set()}),
            party_labels,
            position_labels,
        )
        for entity in entities
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_blurbs.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add src/category_contexto/blurbs.py tests/test_blurbs.py
git commit -m "feat: blurb builder for entity text descriptions"
```

---

### Task 6: Embedding Generation

**Files:**
- Create: `src/category_contexto/embeddings.py`
- Create: `tests/test_embeddings.py`

**Step 1: Write the failing test**

`tests/test_embeddings.py`:
```python
import numpy as np
from unittest.mock import patch, MagicMock
from category_contexto.embeddings import generate_embeddings, compute_embedding_similarity


def test_generate_embeddings():
    mock_embedding = [0.1] * 3072
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=mock_embedding, index=0),
        MagicMock(embedding=mock_embedding, index=1),
    ]

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_response

    blurbs = {"Q1": "Person A. President.", "Q2": "Person B. Senator."}

    with patch("category_contexto.embeddings.get_openai_client", return_value=mock_client):
        result = generate_embeddings(blurbs)

    assert "Q1" in result
    assert "Q2" in result
    assert len(result["Q1"]) == 3072


def test_compute_embedding_similarity():
    embeddings = {
        "Q1": np.array([1.0, 0.0, 0.0]),
        "Q2": np.array([1.0, 0.0, 0.0]),
        "Q3": np.array([0.0, 1.0, 0.0]),
    }
    # Identical vectors = similarity 1.0
    assert compute_embedding_similarity(embeddings, "Q1", "Q2") == 1.0
    # Orthogonal vectors = similarity 0.0
    assert compute_embedding_similarity(embeddings, "Q1", "Q3") == 0.0


def test_compute_embedding_similarity_normalized():
    embeddings = {
        "Q1": np.array([3.0, 0.0, 0.0]),
        "Q2": np.array([0.0, 5.0, 0.0]),
    }
    # Should still work with unnormalized vectors
    sim = compute_embedding_similarity(embeddings, "Q1", "Q2")
    assert abs(sim - 0.0) < 1e-6
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_embeddings.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write implementation**

`src/category_contexto/embeddings.py`:
```python
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100


def get_openai_client() -> OpenAI:
    return OpenAI()


def generate_embeddings(blurbs: dict[str, str]) -> dict[str, np.ndarray]:
    """Generate embeddings for all entity blurbs via OpenAI API.

    Returns {entity_id: numpy array of embedding}.
    """
    client = get_openai_client()
    entity_ids = list(blurbs.keys())
    texts = [blurbs[eid] for eid in entity_ids]
    result = {}

    for i in range(0, len(texts), BATCH_SIZE):
        batch_ids = entity_ids[i : i + BATCH_SIZE]
        batch_texts = texts[i : i + BATCH_SIZE]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch_texts,
        )
        for j, embedding_obj in enumerate(response.data):
            result[batch_ids[j]] = np.array(embedding_obj.embedding)

    return result


def compute_embedding_similarity(
    embeddings: dict[str, np.ndarray], entity_a: str, entity_b: str
) -> float:
    """Compute cosine similarity between two entity embeddings."""
    vec_a = embeddings[entity_a]
    vec_b = embeddings[entity_b]
    dot = np.dot(vec_a, vec_b)
    norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if norm == 0:
        return 0.0
    return float(dot / norm)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_embeddings.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add src/category_contexto/embeddings.py tests/test_embeddings.py
git commit -m "feat: OpenAI embedding generation and cosine similarity"
```

---

### Task 7: Ranking Engine — Blend and Precompute

**Files:**
- Create: `src/category_contexto/ranking.py`
- Create: `tests/test_ranking.py`

**Step 1: Write the failing test**

`tests/test_ranking.py`:
```python
import numpy as np
from category_contexto.ranking import compute_blended_rankings


def test_compute_blended_rankings_basic():
    entity_ids = ["Q1", "Q2", "Q3"]

    def graph_sim(a, b):
        if {a, b} == {"Q1", "Q2"}:
            return 0.8
        if {a, b} == {"Q1", "Q3"}:
            return 0.2
        if {a, b} == {"Q2", "Q3"}:
            return 0.5
        if a == b:
            return 1.0
        return 0.0

    def embed_sim(a, b):
        if {a, b} == {"Q1", "Q2"}:
            return 0.6
        if {a, b} == {"Q1", "Q3"}:
            return 0.9
        if {a, b} == {"Q2", "Q3"}:
            return 0.3
        if a == b:
            return 1.0
        return 0.0

    # alpha=0.5: equal weight
    rankings = compute_blended_rankings(entity_ids, graph_sim, embed_sim, alpha=0.5)

    # For Q1 as secret: Q2 graph=0.8 embed=0.6 blend=0.7, Q3 graph=0.2 embed=0.9 blend=0.55
    # So Q2 should be rank 1 (closest), Q3 rank 2
    assert rankings["Q1"]["Q2"] == 1
    assert rankings["Q1"]["Q3"] == 2

    # Every entity should have rankings for all others
    for eid in entity_ids:
        assert eid not in rankings[eid]  # shouldn't rank self
        assert len(rankings[eid]) == 2


def test_blended_rankings_alpha_zero_ignores_graph():
    entity_ids = ["Q1", "Q2", "Q3"]

    def graph_sim(a, b):
        # Q2 is graph-close to Q1
        return 0.9 if {a, b} == {"Q1", "Q2"} else 0.0

    def embed_sim(a, b):
        # Q3 is embed-close to Q1
        return 0.9 if {a, b} == {"Q1", "Q3"} else 0.0

    # alpha=0 means only embedding signal
    rankings = compute_blended_rankings(entity_ids, graph_sim, embed_sim, alpha=0.0)
    assert rankings["Q1"]["Q3"] == 1  # Q3 wins on embedding alone
    assert rankings["Q1"]["Q2"] == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ranking.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write implementation**

`src/category_contexto/ranking.py`:
```python
from typing import Callable


def compute_blended_rankings(
    entity_ids: list[str],
    graph_similarity_fn: Callable[[str, str], float],
    embedding_similarity_fn: Callable[[str, str], float],
    alpha: float = 0.5,
) -> dict[str, dict[str, int]]:
    """Compute blended similarity rankings for all entities.

    For each entity, ranks all other entities by:
        final_sim = alpha * graph_sim + (1 - alpha) * embed_sim

    Returns {entity_id: {other_entity_id: rank}} where rank 1 = most similar.
    """
    rankings: dict[str, dict[str, int]] = {}

    for secret in entity_ids:
        similarities = []
        for other in entity_ids:
            if other == secret:
                continue
            g_sim = graph_similarity_fn(secret, other)
            e_sim = embedding_similarity_fn(secret, other)
            blended = alpha * g_sim + (1 - alpha) * e_sim
            similarities.append((other, blended))

        # Sort by blended similarity descending, rank 1 = most similar
        similarities.sort(key=lambda x: x[1], reverse=True)
        rankings[secret] = {eid: rank + 1 for rank, (eid, _) in enumerate(similarities)}

    return rankings
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ranking.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add src/category_contexto/ranking.py tests/test_ranking.py
git commit -m "feat: blended ranking engine with tunable alpha"
```

---

### Task 8: SQLite Storage

**Files:**
- Create: `src/category_contexto/storage.py`
- Create: `tests/test_storage.py`

**Step 1: Write the failing test**

`tests/test_storage.py`:
```python
from category_contexto.storage import RankingStore


def test_save_and_lookup(tmp_db_path):
    store = RankingStore(tmp_db_path)
    rankings = {
        "Q1": {"Q2": 1, "Q3": 2},
        "Q2": {"Q1": 1, "Q3": 2},
    }
    entities = {
        "Q1": "Joe Biden",
        "Q2": "Barack Obama",
        "Q3": "Donald Trump",
    }
    store.save_rankings("politics", rankings, entities)

    assert store.lookup("politics", "Q1", "Q2") == 1
    assert store.lookup("politics", "Q1", "Q3") == 2
    assert store.lookup("politics", "Q1", "Q999") is None


def test_lookup_by_name(tmp_db_path):
    store = RankingStore(tmp_db_path)
    rankings = {"Q1": {"Q2": 1, "Q3": 2}}
    entities = {
        "Q1": "Joe Biden",
        "Q2": "Barack Obama",
        "Q3": "Donald Trump",
    }
    store.save_rankings("politics", rankings, entities)

    assert store.lookup_by_name("politics", "Joe Biden", "Barack Obama") == 1
    assert store.lookup_by_name("politics", "Joe Biden", "donald trump") == 2  # case insensitive


def test_get_entity_list(tmp_db_path):
    store = RankingStore(tmp_db_path)
    rankings = {"Q1": {"Q2": 1}}
    entities = {"Q1": "Joe Biden", "Q2": "Barack Obama"}
    store.save_rankings("politics", rankings, entities)

    result = store.get_entity_list("politics")
    assert len(result) == 2
    names = {e["name"] for e in result}
    assert "Joe Biden" in names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write implementation**

`src/category_contexto/storage.py`:
```python
import json
import sqlite3
from pathlib import Path


class RankingStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        db_path_parent = self.db_path.parent
        db_path_parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    category TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    PRIMARY KEY (category, entity_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rankings (
                    category TEXT NOT NULL,
                    secret_id TEXT NOT NULL,
                    guess_id TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    PRIMARY KEY (category, secret_id, guess_id)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def save_rankings(
        self,
        category: str,
        rankings: dict[str, dict[str, int]],
        entities: dict[str, str],
    ):
        """Save precomputed rankings and entity names for a category."""
        with self._connect() as conn:
            conn.execute("DELETE FROM entities WHERE category = ?", (category,))
            conn.execute("DELETE FROM rankings WHERE category = ?", (category,))

            conn.executemany(
                "INSERT INTO entities (category, entity_id, name) VALUES (?, ?, ?)",
                [(category, eid, name) for eid, name in entities.items()],
            )

            rows = []
            for secret_id, guesses in rankings.items():
                for guess_id, rank in guesses.items():
                    rows.append((category, secret_id, guess_id, rank))
            conn.executemany(
                "INSERT INTO rankings (category, secret_id, guess_id, rank) VALUES (?, ?, ?, ?)",
                rows,
            )

    def lookup(self, category: str, secret_id: str, guess_id: str) -> int | None:
        """Look up the rank of a guess for a given secret entity."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT rank FROM rankings WHERE category = ? AND secret_id = ? AND guess_id = ?",
                (category, secret_id, guess_id),
            ).fetchone()
        return row[0] if row else None

    def lookup_by_name(
        self, category: str, secret_name: str, guess_name: str
    ) -> int | None:
        """Look up rank by entity names (case-insensitive)."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT r.rank FROM rankings r
                JOIN entities e1 ON r.category = e1.category AND r.secret_id = e1.entity_id
                JOIN entities e2 ON r.category = e2.category AND r.guess_id = e2.entity_id
                WHERE r.category = ?
                  AND LOWER(e1.name) = LOWER(?)
                  AND LOWER(e2.name) = LOWER(?)
                """,
                (category, secret_name, guess_name),
            ).fetchone()
        return row[0] if row else None

    def get_entity_list(self, category: str) -> list[dict]:
        """Get all entities for a category."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT entity_id, name FROM entities WHERE category = ?",
                (category,),
            ).fetchall()
        return [{"id": row[0], "name": row[1]} for row in rows]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add src/category_contexto/storage.py tests/test_storage.py
git commit -m "feat: SQLite ranking storage with name-based lookup"
```

---

### Task 9: Pipeline Orchestrator

**Files:**
- Create: `src/category_contexto/pipeline.py`
- Create: `tests/test_pipeline.py`

**Step 1: Write the failing test**

`tests/test_pipeline.py`:
```python
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
         patch("category_contexto.pipeline.fetch_politician_properties", return_value=mock_props), \
         patch("category_contexto.pipeline.generate_embeddings", return_value=mock_embeddings):

        store = run_politics_pipeline(db_path=tmp_db_path, alpha=0.5)

    # Should be able to look up rankings
    rank = store.lookup_by_name("politics", "Person A", "Person B")
    assert rank is not None
    assert isinstance(rank, int)
    assert rank >= 1

    # All entities should exist
    entities = store.get_entity_list("politics")
    assert len(entities) == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write implementation**

`src/category_contexto/pipeline.py`:
```python
from pathlib import Path
from functools import partial

from category_contexto.config import DB_PATH
from category_contexto.wikidata import (
    fetch_politicians,
    fetch_politician_properties,
    properties_to_edges,
)
from category_contexto.graph import build_graph_from_edges, compute_graph_similarity
from category_contexto.blurbs import build_blurbs
from category_contexto.embeddings import generate_embeddings, compute_embedding_similarity
from category_contexto.ranking import compute_blended_rankings
from category_contexto.storage import RankingStore


def run_politics_pipeline(
    db_path: Path | None = None,
    alpha: float = 0.3,
) -> RankingStore:
    """Run the full pipeline for the politics category.

    1. Fetch entities from Wikidata
    2. Fetch properties and build graph
    3. Build blurbs and generate embeddings
    4. Compute blended rankings
    5. Store in SQLite
    """
    if db_path is None:
        db_path = DB_PATH

    print("Fetching politicians from Wikidata...")
    entities = fetch_politicians()
    entity_ids = [e["id"] for e in entities]
    print(f"  Found {len(entities)} entities")

    print("Fetching properties...")
    props = fetch_politician_properties(entity_ids)

    print("Building graph...")
    edges = properties_to_edges(props)
    graph = build_graph_from_edges(edges)
    print(f"  {len(edges)} edges")

    print("Building blurbs...")
    # For now, use empty label dicts — blurbs will just use raw IDs
    # TODO: fetch labels for parties/positions from Wikidata
    party_labels = {}
    position_labels = {}
    blurbs = build_blurbs(entities, props, party_labels, position_labels)

    print("Generating embeddings...")
    embeddings = generate_embeddings(blurbs)

    print("Computing blended rankings...")
    graph_sim_fn = partial(compute_graph_similarity, graph)
    embed_sim_fn = partial(compute_embedding_similarity, embeddings)
    rankings = compute_blended_rankings(entity_ids, graph_sim_fn, embed_sim_fn, alpha=alpha)

    print("Saving to database...")
    store = RankingStore(db_path)
    entity_names = {e["id"]: e["name"] for e in entities}
    store.save_rankings("politics", rankings, entity_names)
    print(f"  Done. {len(entities)} entities ranked.")

    return store
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline.py -v`
Expected: 1 PASSED

**Step 5: Commit**

```bash
git add src/category_contexto/pipeline.py tests/test_pipeline.py
git commit -m "feat: end-to-end pipeline orchestrator for politics category"
```

---

### Task 10: CLI for Inspection and Play

**Files:**
- Create: `src/category_contexto/cli.py`

This task does NOT use TDD — it's a developer tool for manual validation.

**Step 1: Write the CLI**

`src/category_contexto/cli.py`:
```python
"""CLI for running the pipeline and playing a round of Category Contexto."""
import argparse
import random
import sys
from pathlib import Path

from category_contexto.config import DB_PATH
from category_contexto.pipeline import run_politics_pipeline
from category_contexto.storage import RankingStore


def cmd_refresh(args):
    """Run the data pipeline to refresh rankings."""
    run_politics_pipeline(db_path=DB_PATH, alpha=args.alpha)


def cmd_play(args):
    """Play a round of Category Contexto."""
    store = RankingStore(DB_PATH)
    entities = store.get_entity_list("politics")

    if not entities:
        print("No entities found. Run 'refresh' first.")
        sys.exit(1)

    secret = random.choice(entities)
    total_entities = len(entities)
    print(f"Category: Politics | {total_entities} entities")
    print("Guess the politician! Type 'quit' to give up.\n")

    guesses = 0
    while True:
        guess = input("Your guess: ").strip()
        if not guess:
            continue
        if guess.lower() == "quit":
            print(f"\nThe answer was: {secret['name']}")
            break

        rank = store.lookup_by_name("politics", secret["name"], guess)
        if rank is None:
            print(f"  '{guess}' not found in entity list. Try again.")
            continue

        guesses += 1

        if rank == 0 or guess.lower() == secret["name"].lower():
            print(f"\n  You got it! The answer was {secret['name']}!")
            print(f"  Guesses: {guesses}")
            break

        # Color coding
        if rank <= 50:
            color = "\033[92m"  # green
        elif rank <= 300:
            color = "\033[93m"  # yellow
        else:
            color = "\033[91m"  # red
        reset = "\033[0m"

        print(f"  {color}{guess}: #{rank} / {total_entities - 1}{reset}")


def cmd_inspect(args):
    """Inspect rankings for a specific entity."""
    store = RankingStore(DB_PATH)
    entity_name = args.entity

    entities = store.get_entity_list("politics")
    # Find the secret entity
    secret = None
    for e in entities:
        if e["name"].lower() == entity_name.lower():
            secret = e
            break

    if not secret:
        print(f"Entity '{entity_name}' not found.")
        sys.exit(1)

    print(f"\nTop {args.top} most similar to: {secret['name']}\n")

    # Get all rankings for this secret
    with store._connect() as conn:
        rows = conn.execute(
            """
            SELECT e.name, r.rank FROM rankings r
            JOIN entities e ON r.category = e.category AND r.guess_id = e.entity_id
            WHERE r.category = 'politics' AND r.secret_id = ?
            ORDER BY r.rank ASC
            LIMIT ?
            """,
            (secret["id"], args.top),
        ).fetchall()

    for name, rank in rows:
        print(f"  #{rank:>4}  {name}")


def main():
    parser = argparse.ArgumentParser(description="Category Contexto")
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh_parser = subparsers.add_parser("refresh", help="Run data pipeline")
    refresh_parser.add_argument("--alpha", type=float, default=0.3, help="Graph weight (0-1)")

    play_parser = subparsers.add_parser("play", help="Play a round")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect rankings for an entity")
    inspect_parser.add_argument("entity", help="Entity name to inspect")
    inspect_parser.add_argument("--top", type=int, default=20, help="Number of results")

    args = parser.parse_args()

    if args.command == "refresh":
        cmd_refresh(args)
    elif args.command == "play":
        cmd_play(args)
    elif args.command == "inspect":
        cmd_inspect(args)


if __name__ == "__main__":
    main()
```

**Step 2: Add CLI entry point to pyproject.toml**

Add to `pyproject.toml`:
```toml
[project.scripts]
contexto = "category_contexto.cli:main"
```

**Step 3: Reinstall and test**

```bash
pip install -e ".[dev]"
contexto --help
```

Expected: Help text showing refresh, play, inspect subcommands.

**Step 4: Commit**

```bash
git add src/category_contexto/cli.py pyproject.toml
git commit -m "feat: CLI for pipeline refresh, play, and inspect commands"
```

---

### Task 11: Integration Test — Run Pipeline Against Real Wikidata

**Files:**
- Create: `tests/test_integration.py`

This is a manual smoke test marked with `@pytest.mark.integration` so it doesn't run in CI.

**Step 1: Write integration test**

`tests/test_integration.py`:
```python
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

    # Sanity check: Biden should be more similar to Obama than to a random entity
    rank_obama = store.lookup_by_name("politics", "Joe Biden", "Barack Obama")
    assert rank_obama is not None, "Obama not found in rankings"
    assert rank_obama < 50, f"Expected Obama in top 50 for Biden, got #{rank_obama}"
```

**Step 2: Add pytest marker config**

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests that hit real APIs (deselect with '-m \"not integration\"')",
]
```

**Step 3: Commit**

```bash
git add tests/test_integration.py pyproject.toml
git commit -m "feat: integration smoke test for real pipeline run"
```

---

## Summary

| Task | Component | Tests |
|------|-----------|-------|
| 1 | Project scaffolding | — |
| 2 | Wikidata entity fetcher | 2 |
| 3 | Graph builder + Jaccard similarity | 4 |
| 4 | Wikidata edge fetcher | 2 |
| 5 | Blurb builder | 3 |
| 6 | Embedding generation + cosine sim | 3 |
| 7 | Ranking engine (blend) | 2 |
| 8 | SQLite storage | 3 |
| 9 | Pipeline orchestrator | 1 |
| 10 | CLI (refresh, play, inspect) | — |
| 11 | Integration smoke test | 1 |

After Task 11, run `contexto refresh` then `contexto inspect "Joe Biden"` to validate rankings feel right. Iterate on alpha, blurb content, and edge weights from there.
