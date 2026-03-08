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
        with self._connect() as conn:
            row = conn.execute(
                "SELECT rank FROM rankings WHERE category = ? AND secret_id = ? AND guess_id = ?",
                (category, secret_id, guess_id),
            ).fetchone()
        return row[0] if row else None

    def lookup_by_name(
        self, category: str, secret_name: str, guess_name: str
    ) -> int | None:
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
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT entity_id, name FROM entities WHERE category = ?",
                (category,),
            ).fetchall()
        return [{"id": row[0], "name": row[1]} for row in rows]
