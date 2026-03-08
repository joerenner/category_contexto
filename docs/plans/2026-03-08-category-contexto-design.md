# Category Contexto — Design Document

## Overview

A Contexto-style word guessing game where each puzzle is scoped to a **category of proper nouns/entities** (politicians, NBA players, musical artists, etc.). Players guess entities and receive a numerical rank indicating how similar their guess is to the secret entity. Similarity is computed via a hybrid approach blending structural knowledge graph signals with contextual embedding signals.

## Key Differences from Original Contexto

- **Proper nouns/entities** instead of common English words
- **Category-scoped** puzzles (politics, NBA, NFL, music, etc.)
- **Current-event awareness** — rankings reflect recent context, not just static relationships
- **Bespoke data sources** per category for deeper similarity nuance (e.g., player stats, voting records)

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Puzzle Service (daily puzzle selection + API)   │
├─────────────────────────────────────────────────┤
│  Ranking Engine (blend + precomputed rankings)  │
├──────────────────────┬──────────────────────────┤
│  Knowledge Graph     │  Embedding Index         │
│  (structural signal) │  (contextual signal)     │
├──────────────────────┴──────────────────────────┤
│  Data Pipeline (refresh per category cadence)   │
│  - Entity list generation (Wikidata + bespoke)  │
│  - News/context scraping                        │
│  - Graph construction                           │
│  - Embedding generation                         │
│  - Ranking precomputation                       │
└─────────────────────────────────────────────────┘
```

### Query-time flow

- **Puzzle selection (daily):** Pick a secret entity from the category, look up its precomputed ranking dictionary.
- **Per guess:** O(1) dictionary lookup → return rank + color.

## Knowledge Graph Layer

Weighted, undirected graph. Nodes = entities, edges = relationships with weights.

### Edge types per category

| Category | Wikidata edges (bootstrap) | Bespoke edges (upgrade path) |
|----------|---------------------------|------------------------------|
| Politics | same party, same country, same office held, served same era | voting record similarity, donor overlap, policy alignment |
| NBA | same team, same position, same draft class | play-style similarity (PER, usage rate, shot distribution), head-to-head stats |
| NFL | same team, same position, same division | yards/game similarity, QB rating clusters |
| Music | same genre, same label, same era | Spotify audio features, collaboration network, streaming demographics |

### Graph similarity

Start with **weighted Jaccard similarity on edge sets**. Upgrade to **graph embeddings (node2vec)** if needed for richer continuous similarity.

### Extensibility pattern

Each category defines a `GraphBuilder` that outputs `(entity_a, entity_b, edge_type, weight)` tuples. A generic `WikidataGraphBuilder` handles bootstrap edges. Category-specific builders (e.g., `NBAStatsGraphBuilder`) ingest domain data. All edges merge into one graph per category.

## Embedding Layer (Contextual Signal)

### Entity blurb construction

Each entity gets a text blurb assembled from multiple sources:

```
[Entity Name]. [Role/title]. [Key facts from Wikidata].
[Recent context: 2-3 sentences from recent news excerpts].
[Category-specific stats summary if available].
```

Each category defines a `BlurbBuilder` (parallel to `GraphBuilder`) that assembles the blurb from available data sources.

### Embedding model

**Start with OpenAI `text-embedding-3-large`** (3072 dims). Cost is trivial at refresh time (~$0.05 per 2000 entity blurbs). Switch to self-hosted (e.g., `nomic-embed-text`) only if quality tuning demands it.

### News freshness

- News API or RSS filtered by entity name + category keywords
- Top 2-3 recent articles per entity, summarized via cheap LLM call
- Appended to base blurb before embedding
- Refresh cadence matches category schedule

## Ranking Engine

### Blending formula

```
final_similarity(A, B) = α × graph_similarity(A, B) + (1 - α) × embedding_similarity(A, B)
```

- `α` is tunable per category
- Both signals normalized to [0, 1] before blending
- Politics: `α ≈ 0.3` (lean contextual). NBA: `α ≈ 0.6` (lean structural).

### Precomputation

Full n×n similarity matrix per category (at ~2000 entities, this is ~4M floats = ~16MB — trivially small). For each entity, sort all others by final similarity → store as ranked dictionary. Any entity can be a daily puzzle without recomputation.

### Storage

`{category}/{entity_id}: {other_entity: rank}` — SQLite to start (zero infra), upgrade to Redis if latency matters at scale.

## Data Pipeline

### Steps per category refresh

1. **Entity list update** — Wikidata SPARQL → filter by notability (Wikipedia page views) → merge manual curations
2. **Graph construction** — Wikidata edges + bespoke edges → merge, normalize weights
3. **Blurb construction** — Wikidata facts + news excerpts + bespoke stats → assemble blurbs
4. **Embedding generation** — batch embed via OpenAI API
5. **Ranking precomputation** — graph similarity matrix + embedding similarity matrix → blend → sort → persist

### Refresh cadences

| Category | Cadence | Trigger |
|----------|---------|---------|
| Politics | Monthly | Cron |
| NBA/NFL/NHL | Monthly in-season, once post-roster-moves in offseason | Cron + manual |
| Music | Quarterly | Cron |

## Tech Stack

- **Language:** Python
- **Wikidata:** `requests` + SPARQL
- **News:** NewsAPI or RSS
- **Embeddings:** OpenAI SDK
- **Similarity computation:** NumPy / SciPy
- **Storage:** SQLite (start), Redis (scale)
- **Scheduling:** Cron or GitHub Actions
- **Bespoke data:** Category-specific (basketball-reference, Spotify API, etc.)

## Scope & Phasing

- **Phase 1:** Core ranking system — one category (politics or NBA), Wikidata-only graph, embedding blurbs, precomputed rankings. Validate that rankings "feel right."
- **Phase 2:** Bespoke data integration for first category. News freshness pipeline. Tune blend weights.
- **Phase 3:** Add more categories. Product layer (API, UI, daily puzzles, sharing).
- **Phase 4:** Scale entity lists to 2000+ per category. Graph embeddings upgrade. User accounts, streaks, leaderboards.
