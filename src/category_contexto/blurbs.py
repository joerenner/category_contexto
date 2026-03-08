def build_blurb(
    entity: dict,
    props: dict,
    party_labels: dict[str, str],
    position_labels: dict[str, str],
) -> str:
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
    return {
        entity["id"]: build_blurb(
            entity,
            all_props.get(entity["id"], {"parties": set(), "positions": set()}),
            party_labels,
            position_labels,
        )
        for entity in entities
    }
