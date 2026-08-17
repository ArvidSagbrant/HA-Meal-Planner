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
- `mqtt_mode`: `auto` uses the MQTT service supplied by Home Assistant
  Supervisor, `external` uses the broker fields below, and `disabled` turns off
  MQTT publishing. `auto` is the default and does not prevent the add-on from
  starting when no broker is installed.
- `mqtt_host`, `mqtt_port`, `mqtt_username`, `mqtt_password`, and `mqtt_tls`:
  external broker connection settings. They are ignored in `auto` mode.
- `mqtt_discovery_prefix`: Home Assistant MQTT Discovery prefix (normally
  `homeassistant`).
- `mqtt_topic_prefix`: base topic for Meal Planner state (normally
  `meal_planner`).
- `mqtt_birth_topic`: Home Assistant birth topic used to republish discovery
  and current state after a restart (normally `homeassistant/status`).

Add at least seven eligible meals, then select **Generate week**. Generation is
deterministic for the same meals, settings, history, and existing plan. Excluded
meals, duplicates within a week, and meals used inside the repeat-avoidance
window are hard constraints. Preference, recency, effort, protein/tag variety,
and the vegetarian target are scored preferences.

Protein/source is selected from a localized catalog: poultry, fish, beef, pork,
lamb, seafood, eggs, halloumi, tofu, tempeh, quorn, legumes, or other. A meal's
vegetarian status is controlled separately with the **Vegetarian** checkbox.

Selecting a meal manually creates an override that is preserved when the week
is generated again. Generated days can be regenerated individually without
changing any other day. Use the arrow buttons to browse past and future weeks.
Historical plans are retained, and their cooked entries are used by future
generation. Data is stored in the add-on's `/data` directory and survives
restarts and upgrades.

Mark a planned day as **Cooked** after the meal was actually prepared. Only
cooked meals are included in repeat-avoidance history, so skipped or replaced
plans do not prevent those meals from being selected later. A cooked day is
locked against assignment changes and regeneration; unmark it first to edit the
day.

## Home Assistant entities

When MQTT is connected, Home Assistant MQTT Discovery creates two entities with
stable IDs:

- `sensor.meal_planner_today`
- `sensor.meal_planner_tomorrow`

Their state is the planned meal name, or a localized message when no meal is
planned. Attributes include the date, meal ID, assignment type, cooked/manual
flags, protein source, vegetarian status, tags, preference, and cooking effort.
The add-on republishes both entities after meal or plan changes and whenever
Home Assistant announces that it has restarted.
