"""CLI for running the pipeline and playing a round of Category Contexto."""
import argparse
import random
import sys
from pathlib import Path

from category_contexto.config import DB_PATH
from category_contexto.pipeline import run_politics_pipeline
from category_contexto.storage import RankingStore


def cmd_refresh(args):
    run_politics_pipeline(db_path=DB_PATH, alpha=args.alpha)


def cmd_play(args):
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
    store = RankingStore(DB_PATH)
    entity_name = args.entity

    entities = store.get_entity_list("politics")
    secret = None
    for e in entities:
        if e["name"].lower() == entity_name.lower():
            secret = e
            break

    if not secret:
        print(f"Entity '{entity_name}' not found.")
        sys.exit(1)

    print(f"\nTop {args.top} most similar to: {secret['name']}\n")

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
