from datetime import date, timedelta

import pytest

from meal_planner.planner import (
    DeterministicPlanner,
    MealCandidate,
    PlanSlot,
    PlannerSettings,
    PlanningFailure,
    PlanningHistory,
)


WEEK_START = date(2026, 8, 17)


def meal(
    index: int,
    *,
    preference: int = 3,
    effort: int = 2,
    protein: str = "other",
    vegetarian: bool = False,
    excluded: bool = False,
    nutrition: dict[str, float] | None = None,
) -> MealCandidate:
    return MealCandidate(
        id=f"meal-{index}",
        name=f"Meal {index:02d}",
        preference=preference,
        cooking_effort=effort,
        protein_source=protein,
        is_vegetarian=vegetarian,
        tags=(),
        nutrition=nutrition or {},
        excluded=excluded,
    )


def empty_slots() -> list[PlanSlot]:
    return [PlanSlot(WEEK_START + timedelta(days=offset)) for offset in range(7)]


def test_full_week_is_unique_deterministic_and_excludes_opted_out_meals() -> None:
    meals = [meal(index) for index in range(8)] + [meal(99, excluded=True)]
    planner = DeterministicPlanner(PlannerSettings())

    first = planner.generate_week(
        week_start=WEEK_START,
        meals=meals,
        slots=empty_slots(),
        history=PlanningHistory(),
    )
    second = planner.generate_week(
        week_start=WEEK_START,
        meals=list(reversed(meals)),
        slots=empty_slots(),
        history=PlanningHistory(),
    )

    assert first.assignments == second.assignments
    assert len(set(first.assignments.values())) == 7
    assert "meal-99" not in first.assignments.values()


def test_manual_override_is_preserved() -> None:
    slots = empty_slots()
    slots[2] = PlanSlot(slots[2].date, "meal-7", is_manual_override=True)

    result = DeterministicPlanner(PlannerSettings()).generate_week(
        week_start=WEEK_START,
        meals=[meal(index) for index in range(8)],
        slots=slots,
        history=PlanningHistory(),
    )

    assert result.assignments[WEEK_START + timedelta(days=2)] == "meal-7"
    assert list(result.assignments.values()).count("meal-7") == 1


def test_recent_meals_are_hard_excluded() -> None:
    recent_ids = {"meal-0", "meal-1"}
    history = PlanningHistory(
        {
            meal_id: WEEK_START - timedelta(days=7)
            for meal_id in recent_ids
        }
    )

    result = DeterministicPlanner(
        PlannerSettings(repeat_avoidance_weeks=2)
    ).generate_week(
        week_start=WEEK_START,
        meals=[meal(index) for index in range(9)],
        slots=empty_slots(),
        history=history,
    )

    assert recent_ids.isdisjoint(result.assignments.values())


def test_preference_and_effort_influence_selection() -> None:
    settings = PlannerSettings(
        repeat_avoidance_weeks=0,
        vegetarian_target=0,
        preference_weight=1,
        recency_weight=0,
        effort_weight=1,
        variety_weight=0,
        weekday_effort_target=1,
        weekend_effort_target=5,
    )
    meals = [meal(index, preference=3, effort=3) for index in range(7)]
    meals.extend(
        [
            meal(10, preference=5, effort=1),
            meal(11, preference=5, effort=5),
        ]
    )

    result = DeterministicPlanner(settings).generate_week(
        week_start=WEEK_START,
        meals=meals,
        slots=empty_slots(),
        history=PlanningHistory(),
    )

    assert result.assignments[WEEK_START] == "meal-10"
    assert result.assignments[WEEK_START + timedelta(days=5)] == "meal-11"


def test_vegetarian_target_is_met_when_candidates_are_available() -> None:
    assert meal(9, protein="halloumi").is_vegetarian is False
    meals = [meal(index, protein="meat") for index in range(7)]
    meals.extend(
        [
            meal(10, protein="halloumi", vegetarian=True),
            meal(11, protein="legumes", vegetarian=True),
        ]
    )

    result = DeterministicPlanner(
        PlannerSettings(
            vegetarian_target=2,
            preference_weight=0,
            recency_weight=0,
            effort_weight=0,
            variety_weight=1,
        )
    ).generate_week(
        week_start=WEEK_START,
        meals=meals,
        slots=empty_slots(),
        history=PlanningHistory(),
    )

    selected = {meal_id for meal_id in result.assignments.values()}
    assert {"meal-10", "meal-11"}.issubset(selected)


def test_generation_fails_if_hard_constraints_cannot_fill_week() -> None:
    with pytest.raises(PlanningFailure, match="Not enough eligible meals"):
        DeterministicPlanner(PlannerSettings()).generate_week(
            week_start=WEEK_START,
            meals=[meal(index) for index in range(6)],
            slots=empty_slots(),
            history=PlanningHistory(),
        )


def test_regenerate_day_changes_only_requested_generated_slot() -> None:
    meals = [meal(index) for index in range(9)]
    planner = DeterministicPlanner(PlannerSettings(repeat_avoidance_weeks=0))
    generated = planner.generate_week(
        week_start=WEEK_START,
        meals=meals,
        slots=empty_slots(),
        history=PlanningHistory(),
    )
    slots = [
        PlanSlot(day, meal_id, is_manual_override=False)
        for day, meal_id in sorted(generated.assignments.items())
    ]
    target = WEEK_START + timedelta(days=3)

    replacement, _score = planner.regenerate_day(
        week_start=WEEK_START,
        meal_date=target,
        meals=meals,
        slots=slots,
        history=PlanningHistory(),
    )

    assert replacement != generated.assignments[target]
    assert replacement not in {
        meal_id for day, meal_id in generated.assignments.items() if day != target
    }


def test_manual_day_cannot_be_regenerated() -> None:
    slots = empty_slots()
    slots[0] = PlanSlot(WEEK_START, "meal-0", is_manual_override=True)

    with pytest.raises(PlanningFailure, match="manual override"):
        DeterministicPlanner(PlannerSettings()).regenerate_day(
            week_start=WEEK_START,
            meal_date=WEEK_START,
            meals=[meal(index) for index in range(8)],
            slots=slots,
            history=PlanningHistory(),
        )


def test_maximum_consecutive_protein_source_is_a_hard_constraint() -> None:
    meals = [meal(index, protein="poultry", preference=5) for index in range(4)]
    meals += [meal(index + 10, protein="fish") for index in range(3)]

    result = DeterministicPlanner(
        PlannerSettings(
            repeat_avoidance_weeks=0,
            vegetarian_target=0,
            variety_weight=0,
            max_consecutive_protein_source=2,
        )
    ).generate_week(
        week_start=WEEK_START,
        meals=meals,
        slots=empty_slots(),
        history=PlanningHistory(),
    )

    by_id = {candidate.id: candidate for candidate in meals}
    sources = [
        by_id[result.assignments[WEEK_START + timedelta(days=offset)]].protein_source
        for offset in range(7)
    ]
    assert all(
        len(set(sources[index : index + 3])) > 1
        for index in range(len(sources) - 2)
    )


def test_nutrition_score_prefers_configured_calorie_target() -> None:
    meals = [meal(index) for index in range(7)]
    meals += [
        meal(
            10,
            nutrition={"calories_kcal": 600, "protein_g": 25, "fiber_g": 8},
        ),
        meal(
            11,
            nutrition={"calories_kcal": 1400, "protein_g": 5, "fiber_g": 1},
        ),
    ]

    result = DeterministicPlanner(
        PlannerSettings(
            repeat_avoidance_weeks=0,
            vegetarian_target=0,
            preference_weight=0,
            recency_weight=0,
            effort_weight=0,
            variety_weight=0,
            nutrition_weight=1,
            calorie_target_kcal=600,
        )
    ).generate_week(
        week_start=WEEK_START,
        meals=meals,
        slots=empty_slots(),
        history=PlanningHistory(),
    )

    assert result.assignments[WEEK_START] == "meal-10"
