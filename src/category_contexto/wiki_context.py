import requests
from time import sleep

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKI_BATCH_SIZE = 50  # Wikipedia API limit


def fetch_wikipedia_summaries(
    entity_names: list[str],
    wiki_titles: dict[str, str] | None = None,
    delay: float = 0.5,
) -> dict[str, str]:
    """Fetch Wikipedia intro summaries in batches of 50.

    Returns {entity_name: summary_text} for entities that have Wikipedia pages.
    Uses the Wikipedia API's batch capability (up to 50 titles per request).

    If wiki_titles is provided (mapping entity_name -> wikipedia_title), those
    titles are used for lookup instead of the entity names directly.
    """
    summaries = {}
    # Build a lookup from lowercase name to original name for matching
    name_lookup = {name.lower(): name for name in entity_names}

    # Build mapping from wiki title -> entity name so we can map results back
    if wiki_titles:
        title_to_entity = {title: name for name, title in wiki_titles.items()}
    else:
        title_to_entity = {}

    for i in range(0, len(entity_names), WIKI_BATCH_SIZE):
        entity_batch = entity_names[i : i + WIKI_BATCH_SIZE]
        # Use wiki titles for lookup when available, fall back to entity name
        if wiki_titles:
            batch = [wiki_titles.get(name, name) for name in entity_batch]
        else:
            batch = entity_batch
        try:
            resp = requests.get(
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "titles": "|".join(batch),
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True,
                    "format": "json",
                    "redirects": 1,
                },
                headers={"User-Agent": "CategoryContexto/0.1 (https://github.com/joerenner/category_contexto)"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            # Build redirect map: normalized/redirected title -> original query title
            title_map = {}
            for name in batch:
                title_map[name] = name
            for norm in data.get("query", {}).get("normalized", []):
                title_map[norm["to"]] = norm["from"]
            for redir in data.get("query", {}).get("redirects", []):
                original_from = title_map.get(redir["from"], redir["from"])
                title_map[redir["to"]] = original_from

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id == "-1" or "extract" not in page_data:
                    continue
                extract = page_data["extract"]
                if not extract.strip():
                    continue
                # Limit to first 500 chars
                if len(extract) > 500:
                    extract = extract[:500].rsplit(" ", 1)[0] + "..."

                # Map back to original entity name
                page_title = page_data.get("title", "")
                original_name = title_map.get(page_title, page_title)
                # If we used wiki_titles, map the wiki title back to entity name
                if original_name in title_to_entity:
                    matched_name = title_to_entity[original_name]
                else:
                    # Match against our entity names (case-insensitive)
                    matched_name = name_lookup.get(original_name.lower(), original_name)
                summaries[matched_name] = extract

            sleep(delay)  # be nice to Wikipedia
        except Exception:
            continue  # skip failed batches

    return summaries
