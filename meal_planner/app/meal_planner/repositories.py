"""Persistence repositories for meals and weekly plans."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from .database import Database


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MealRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list(self) -> list[dict]:
        with self.database.read() as connection:
            rows = connection.execute("SELECT * FROM meals ORDER BY name COLLATE NOCASE").fetchall()
        return [self._deserialize(row) for row in rows]

    def get(self, meal_id: str) -> dict | None:
        with self.database.read() as connection:
            row = connection.execute("SELECT * FROM meals WHERE id = ?", (meal_id,)).fetchone()
        return self._deserialize(row) if row else None

    def create(self, values: dict) -> dict:
        meal_id = str(uuid4())
        now = utc_now()
        serialized = self._serialize(values)
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO meals (
                    id, name, description, preference, cooking_effort, image_path,
                    meal_type, protein_source, is_vegetarian, tags_json,
                    nutrition_json, excluded, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meal_id,
                    serialized["name"],
                    serialized["description"],
                    serialized["preference"],
                    serialized["cooking_effort"],
                    serialized["image_path"],
                    serialized["meal_type"],
                    serialized["protein_source"],
                    serialized["is_vegetarian"],
                    serialized["tags_json"],
                    serialized["nutrition_json"],
                    serialized["excluded"],
                    now,
                    now,
                ),
            )
        return self.get(meal_id)  # type: ignore[return-value]

    def update(self, meal_id: str, values: dict) -> dict | None:
        if not values:
            return self.get(meal_id)

        serialized = self._serialize(values, partial=True)
        serialized["updated_at"] = utc_now()
        assignments = ", ".join(f"{column} = ?" for column in serialized)
        parameters = [*serialized.values(), meal_id]
        with self.database.transaction() as connection:
            cursor = connection.execute(
                f"UPDATE meals SET {assignments} WHERE id = ?",  # noqa: S608
                parameters,
            )
            if cursor.rowcount == 0:
                return None
        return self.get(meal_id)

    def delete(self, meal_id: str) -> bool:
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE weekly_plans
                SET updated_at = ?
                WHERE id IN (SELECT plan_id FROM plan_entries WHERE meal_id = ?)
                """,
                (now, meal_id),
            )
            connection.execute(
                """
                UPDATE plan_entries
                SET meal_id = NULL, assignment_type = 'manual', is_manual_override = 0,
                    is_cooked = 0, updated_at = ?
                WHERE meal_id = ?
                """,
                (now, meal_id),
            )
            cursor = connection.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
        return cursor.rowcount > 0

    @staticmethod
    def _serialize(values: dict, *, partial: bool = False) -> dict:
        result = dict(values)
        if "tags" in result:
            result["tags_json"] = json.dumps(result.pop("tags"), separators=(",", ":"))
        if "nutrition" in result:
            result["nutrition_json"] = json.dumps(
                result.pop("nutrition"), separators=(",", ":"), sort_keys=True
            )
        if "excluded" in result:
            result["excluded"] = int(result["excluded"])
        if "is_vegetarian" in result:
            result["is_vegetarian"] = int(result["is_vegetarian"])
        if not partial:
            result.setdefault("description", "")
            result.setdefault("preference", 3)
            result.setdefault("cooking_effort", 3)
            result.setdefault("image_path", None)
            result.setdefault("meal_type", "dinner")
            result.setdefault("protein_source", "other")
            result.setdefault("is_vegetarian", 0)
            result.setdefault("tags_json", "[]")
            result.setdefault("nutrition_json", "{}")
            result.setdefault("excluded", 0)
        return result

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "preference": row["preference"],
            "cooking_effort": row["cooking_effort"],
            "image_path": row["image_path"],
            "meal_type": row["meal_type"],
            "protein_source": row["protein_source"],
            "is_vegetarian": bool(row["is_vegetarian"]),
            "tags": json.loads(row["tags_json"]),
            "nutrition": json.loads(row["nutrition_json"]),
            "excluded": bool(row["excluded"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


class PlanRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def ensure_week(self, week_start: date) -> None:
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO weekly_plans (week_start, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT (week_start) DO NOTHING
                """,
                (week_start.isoformat(), now, now),
            )
            plan_id = connection.execute(
                "SELECT id FROM weekly_plans WHERE week_start = ?", (week_start.isoformat(),)
            ).fetchone()["id"]
            for offset in range(7):
                meal_date = (week_start + timedelta(days=offset)).isoformat()
                connection.execute(
                    """
                    INSERT INTO plan_entries (
                        plan_id, meal_date, meal_id, assignment_type,
                        is_manual_override, created_at, updated_at
                    ) VALUES (?, ?, NULL, 'manual', 0, ?, ?)
                    ON CONFLICT (plan_id, meal_date) DO NOTHING
                    """,
                    (plan_id, meal_date, now, now),
                )

    def get_days(self, week_start: date) -> list[dict]:
        self.ensure_week(week_start)
        with self.database.read() as connection:
            rows = connection.execute(
                """
                SELECT pe.meal_date, pe.meal_id, pe.assignment_type,
                       pe.is_manual_override, pe.is_cooked
                FROM plan_entries pe
                JOIN weekly_plans wp ON wp.id = pe.plan_id
                WHERE wp.week_start = ?
                ORDER BY pe.meal_date
                """,
                (week_start.isoformat(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_last_used(self, before_week_start: date) -> dict[str, date]:
        with self.database.read() as connection:
            rows = connection.execute(
                """
                SELECT pe.meal_id, MAX(pe.meal_date) AS last_used
                FROM plan_entries pe
                WHERE pe.meal_id IS NOT NULL
                  AND pe.is_cooked = 1
                  AND pe.meal_date < ?
                GROUP BY pe.meal_id
                """,
                (before_week_start.isoformat(),),
            ).fetchall()
        return {
            row["meal_id"]: date.fromisoformat(row["last_used"])
            for row in rows
        }

    def replace_generated(
        self, week_start: date, assignments: dict[date, str]
    ) -> None:
        self.ensure_week(week_start)
        now = utc_now()
        with self.database.transaction() as connection:
            plan_id = connection.execute(
                "SELECT id FROM weekly_plans WHERE week_start = ?",
                (week_start.isoformat(),),
            ).fetchone()["id"]
            for meal_date, meal_id in assignments.items():
                connection.execute(
                    """
                    UPDATE plan_entries
                    SET meal_id = ?, assignment_type = 'generated',
                        is_manual_override = 0, is_cooked = 0, updated_at = ?
                    WHERE plan_id = ? AND meal_date = ?
                      AND is_manual_override = 0 AND is_cooked = 0
                    """,
                    (meal_id, now, plan_id, meal_date.isoformat()),
                )
            connection.execute(
                "UPDATE weekly_plans SET updated_at = ? WHERE id = ?",
                (now, plan_id),
            )

    def assign_generated(
        self, week_start: date, meal_date: date, meal_id: str
    ) -> None:
        self.ensure_week(week_start)
        now = utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE plan_entries
                SET meal_id = ?, assignment_type = 'generated',
                    is_manual_override = 0, is_cooked = 0, updated_at = ?
                WHERE plan_id = (
                    SELECT id FROM weekly_plans WHERE week_start = ?
                ) AND meal_date = ? AND is_manual_override = 0 AND is_cooked = 0
                """,
                (meal_id, now, week_start.isoformat(), meal_date.isoformat()),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Expected one generated plan day to be updated")
            connection.execute(
                "UPDATE weekly_plans SET updated_at = ? WHERE week_start = ?",
                (now, week_start.isoformat()),
            )

    def assign(self, week_start: date, meal_date: date, meal_id: str) -> None:
        self.ensure_week(week_start)
        now = utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE plan_entries
                SET meal_id = ?, assignment_type = 'manual', is_manual_override = 1,
                    is_cooked = 0, updated_at = ?
                WHERE plan_id = (
                    SELECT id FROM weekly_plans WHERE week_start = ?
                ) AND meal_date = ?
                """,
                (meal_id, now, week_start.isoformat(), meal_date.isoformat()),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Expected exactly one plan day to be updated")
            connection.execute(
                "UPDATE weekly_plans SET updated_at = ? WHERE week_start = ?",
                (now, week_start.isoformat()),
            )

    def clear(self, week_start: date, meal_date: date) -> None:
        self.ensure_week(week_start)
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE plan_entries
                SET meal_id = NULL, assignment_type = 'manual', is_manual_override = 0,
                    is_cooked = 0, updated_at = ?
                WHERE plan_id = (
                    SELECT id FROM weekly_plans WHERE week_start = ?
                ) AND meal_date = ?
                """,
                (now, week_start.isoformat(), meal_date.isoformat()),
            )
            connection.execute(
                "UPDATE weekly_plans SET updated_at = ? WHERE week_start = ?",
                (now, week_start.isoformat()),
            )

    def set_cooked(
        self, week_start: date, meal_date: date, is_cooked: bool
    ) -> None:
        self.ensure_week(week_start)
        now = utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE plan_entries
                SET is_cooked = ?, updated_at = ?
                WHERE plan_id = (
                    SELECT id FROM weekly_plans WHERE week_start = ?
                ) AND meal_date = ?
                """,
                (
                    int(is_cooked),
                    now,
                    week_start.isoformat(),
                    meal_date.isoformat(),
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Expected exactly one plan day to be updated")
            connection.execute(
                "UPDATE weekly_plans SET updated_at = ? WHERE week_start = ?",
                (now, week_start.isoformat()),
            )
