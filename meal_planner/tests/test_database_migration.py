import sqlite3
from pathlib import Path

from meal_planner.database import Database, SCHEMA_VERSION


def test_v1_classifications_are_migrated_to_canonical_values(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "v1.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE meals (
            id TEXT PRIMARY KEY,
            protein_source TEXT NOT NULL
        );
        CREATE TABLE plan_entries (
            id INTEGER PRIMARY KEY
        );
        INSERT INTO meals (id, protein_source) VALUES
            ('poultry', 'Fågel'),
            ('beef', 'Nöt'),
            ('halloumi', 'Halloumi'),
            ('quorn', 'Quorn'),
            ('unknown', 'Egen kategori');
        PRAGMA user_version = 1;
        """
    )
    connection.commit()
    connection.close()

    database = Database(database_path)
    database.initialize()

    with database.read() as migrated:
        version = migrated.execute("PRAGMA user_version").fetchone()[0]
        meals = {
            row["id"]: (row["protein_source"], bool(row["is_vegetarian"]))
            for row in migrated.execute(
                "SELECT id, protein_source, is_vegetarian FROM meals"
            )
        }
        cooked_column = next(
            row
            for row in migrated.execute("PRAGMA table_info(plan_entries)")
            if row["name"] == "is_cooked"
        )

    assert version == SCHEMA_VERSION
    assert meals == {
        "poultry": ("poultry", False),
        "beef": ("beef", False),
        "halloumi": ("halloumi", True),
        "quorn": ("quorn", True),
        "unknown": ("other", False),
    }
    assert cooked_column["dflt_value"] == "0"
