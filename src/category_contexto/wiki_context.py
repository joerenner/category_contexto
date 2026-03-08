import requests
from time import sleep

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


def fetch_wikipedia_summaries(entity_names: list[str], delay: float = 0.1) -> dict[str, str]:
    """Fetch Wikipedia intro summaries for a list of entity names.

    Returns {entity_name: summary_text} for entities that have Wikipedia pages.
    """
    summaries = {}
    for name in entity_names:
        try:
            resp = requests.get(
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "titles": name,
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True,
                    "format": "json",
                    "redirects": 1,
                },
                headers={"User-Agent": "CategoryContexto/0.1"},
                timeout=10,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id != "-1" and "extract" in page_data:
                    extract = page_data["extract"]
                    # Limit to first 500 chars to keep blurbs reasonable
                    if len(extract) > 500:
                        extract = extract[:500].rsplit(" ", 1)[0] + "..."
                    summaries[name] = extract
            sleep(delay)  # be nice to Wikipedia
        except Exception:
            continue  # skip failures silently
    return summaries
