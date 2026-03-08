from pathlib import Path
from functools import partial

from category_contexto.config import DB_PATH
from category_contexto.wikidata import (
    fetch_politicians,
    fetch_politician_properties,
    fetch_politician_eras,
    fetch_politician_states,
    fetch_wikipedia_titles,
    properties_to_edges,
    era_to_edges,
    state_to_edges,
)
from category_contexto.graph import build_graph_from_edges, compute_graph_similarity
from category_contexto.blurbs import build_blurbs
from category_contexto.wiki_context import fetch_wikipedia_summaries
from category_contexto.embeddings import generate_embeddings, compute_embedding_similarity
from category_contexto.ranking import compute_blended_rankings, make_recency_fn
from category_contexto.storage import RankingStore


def run_politics_pipeline(
    db_path: Path | None = None,
    alpha: float = 0.15,
    max_entities: int = 500,
) -> RankingStore:
    if db_path is None:
        db_path = DB_PATH

    print("Fetching politicians from Wikidata...")
    entities = fetch_politicians()
    if max_entities and len(entities) > max_entities:
        print(f"  Found {len(entities)} entities, limiting to top {max_entities} by notability")
        entities = entities[:max_entities]
    entity_ids = [e["id"] for e in entities]
    print(f"  Using {len(entities)} entities")

    print("Fetching properties...")
    props, party_labels, position_labels = fetch_politician_properties(entity_ids)

    print("Building graph...")
    edges = properties_to_edges(props)
    print(f"  {len(edges)} property edges")

    print("Fetching service eras...")
    eras = fetch_politician_eras(entity_ids)
    era_edges = era_to_edges(eras)
    print(f"  {len(era_edges)} era-overlap edges")

    print("Fetching state representation...")
    states = fetch_politician_states(entity_ids)
    state_edges = state_to_edges(states)
    print(f"  {len(state_edges)} same-state edges")

    all_edges = edges + era_edges + state_edges
    graph = build_graph_from_edges(all_edges)
    print(f"  {len(all_edges)} total edges")

    print("Fetching Wikipedia article titles...")
    wiki_title_map = fetch_wikipedia_titles(entity_ids)
    # Convert from {entity_id: title} to {entity_name: title}
    entity_id_to_name = {e["id"]: e["name"] for e in entities}
    wiki_titles = {entity_id_to_name[eid]: title for eid, title in wiki_title_map.items() if eid in entity_id_to_name}
    print(f"  Found {len(wiki_titles)} Wikipedia article titles")

    print("Fetching Wikipedia summaries...")
    entity_names = [e["name"] for e in entities]
    wiki_summaries = fetch_wikipedia_summaries(entity_names, wiki_titles=wiki_titles)
    print(f"  Got summaries for {len(wiki_summaries)} / {len(entities)} entities")

    print("Building blurbs...")
    blurbs = build_blurbs(entities, props, party_labels, position_labels, wiki_summaries=wiki_summaries)

    print("Generating embeddings...")
    embeddings = generate_embeddings(blurbs)

    print("Computing blended rankings...")
    graph_sim_fn = partial(compute_graph_similarity, graph)
    embed_sim_fn = partial(compute_embedding_similarity, embeddings)
    recency_fn = make_recency_fn(eras)
    rankings = compute_blended_rankings(
        entity_ids, graph_sim_fn, embed_sim_fn,
        alpha=alpha, recency_fn=recency_fn, recency_weight=0.2,
    )

    print("Saving to database...")
    store = RankingStore(db_path)
    entity_names = {e["id"]: e["name"] for e in entities}
    store.save_rankings("politics", rankings, entity_names)
    print(f"  Done. {len(entities)} entities ranked.")

    return store
