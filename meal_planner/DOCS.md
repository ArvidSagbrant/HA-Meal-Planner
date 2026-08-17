# Meal Planner

Meal Planner opens from the Home Assistant sidebar through Ingress.

## Configuration

- `language`: `en` for English or `sv` for Swedish.
- `log_level`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`.
- `repeat_avoidance_weeks`: number of previous weeks in which a meal cannot
  reappear in an automatically generated plan (`0` disables this constraint).
- `vegetarian_target`: preferred number of vegetarian meals per week.
- `preference_weight`: influence of a meal's preference rating.
- `recency_weight`: preference for meals that have not been used recently.
- `effort_weight`: influence of weekday and weekend cooking-effort targets.
- `variety_weight`: influence of protein, tag, and vegetarian variety.
- `weekday_effort_target`: preferred weekday cooking effort from 1 to 5.
- `weekend_effort_target`: preferred weekend cooking effort from 1 to 5.

Add at least seven eligible meals, then select **Generate week**. Generation is
deterministic for the same meals, settings, history, and existing plan. Excluded
meals, duplicates within a week, and meals used inside the repeat-avoidance
window are hard constraints. Preference, recency, effort, protein/tag variety,
and the vegetarian target are scored preferences.

Selecting a meal manually creates an override that is preserved when the week
is generated again. Generated days can be regenerated individually without
changing any other day. Use the arrow buttons to browse past and future weeks.
Historical plans are retained and used by future generation. Data is stored in
the add-on's `/data` directory and survives restarts and upgrades.
