"""SQLite connection management and forward-only schema setup."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


SCHEMA_VERSION = 1


class Database:
    """Own SQLite connections while keeping persistence concerns isolated."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            current_version = connection.execute("PRAGMA user_version").fetchone()[0]
            if current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema {current_version} is newer than supported "
                    f"schema {SCHEMA_VERSION}"
                )
            if current_version == 0:
                self._create_schema(connection)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE meals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                preference INTEGER NOT NULL DEFAULT 3 CHECK (preference BETWEEN 1 AND 5),
                cooking_effort INTEGER NOT NULL DEFAULT 3 CHECK (cooking_effort BETWEEN 1 AND 5),
                image_path TEXT,
                meal_type TEXT NOT NULL DEFAULT 'dinner',
                protein_source TEXT NOT NULL DEFAULT 'other',
                tags_json TEXT NOT NULL DEFAULT '[]',
                nutrition_json TEXT NOT NULL DEFAULT '{}',
                excluded INTEGER NOT NULL DEFAULT 0 CHECK (excluded IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE weekly_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE plan_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
                meal_date TEXT NOT NULL,
                meal_id TEXT REFERENCES meals(id) ON DELETE SET NULL,
                assignment_type TEXT NOT NULL DEFAULT 'manual',
                is_manual_override INTEGER NOT NULL DEFAULT 1 CHECK (is_manual_override IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (plan_id, meal_date)
            );

            CREATE INDEX idx_plan_entries_meal_id ON plan_entries(meal_id);
            CREATE INDEX idx_plan_entries_meal_date ON plan_entries(meal_date);
            """
        )
