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
- `nutrition_weight`: influence of known energy, protein, fibre, and adjacent
  nutritional variety (`0` ignores nutrition during generation).
- `calorie_target_kcal`: preferred energy per serving; `0` disables the calorie
  target while retaining other known nutrition scoring.
- `max_consecutive_protein_source`: hard limit for generated meals using the
  same protein/source on consecutive days (`7` disables the limit). Manual and
  cooked assignments remain preserved.
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
- `ai_provider`: `disabled` (default), `openai`, or `llamacpp`.
- `ai_base_url`: API base URL ending in `/v1`. Leave empty for
  `https://api.openai.com/v1` with OpenAI or `http://localhost:8080/v1` with
  llama.cpp. A llama.cpp server on another host must use an address reachable
  from the add-on container.
- `ai_api_key`: required for OpenAI and optional for a protected compatible
  server. It is treated as a secret and is never returned by the runtime API.
- `ai_model`: provider-specific model identifier.
- `ai_timeout_seconds`: request timeout from 1 to 300 seconds.
- `ai_temperature`: sampling temperature from 0 to 2 for compatible local
  providers. OpenAI model controls use provider defaults for broad model
  compatibility.
- `ai_refinement_enabled`: allow AI refinement after deterministic generation.
- `ai_suggestions_enabled`: show the AI meal-suggestion action.

Add at least seven eligible meals, then select **Generate week**. Generation is
deterministic for the same meals, settings, history, and existing plan. Excluded
meals, duplicates within a week, meals used inside the repeat-avoidance window,
and the configured consecutive protein/source maximum are hard constraints.
Preference, recency, effort, protein/tag variety, nutrition, and the vegetarian
target are scored preferences. The deterministic search can backtrack when a
locally best choice would prevent a complete valid week.

Protein/source is selected from a localized catalog: poultry, fish, beef, pork,
lamb, seafood, eggs, halloumi, tofu, tempeh, quorn, legumes, or other. A meal's
vegetarian status is controlled separately with the **Vegetarian** checkbox.
Optional nutrition fields are per serving: energy, protein, carbohydrates, fat,
and fibre. Missing values are allowed and are never guessed by the deterministic
planner.

Meal images can be uploaded from the editor in PNG, JPEG, GIF, or WebP format,
up to 5 MB. They are stored under `/data/images`, included in the meal browser
and weekly view, and removed automatically when their meal is deleted.

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
flags, protein source, vegetarian status, tags, preference, cooking effort, and
known nutrition.
The add-on republishes both entities after meal or plan changes and whenever
Home Assistant announces that it has restarted.

## Optional AI assistance

AI is disabled by default. When enabled, weekly generation always starts with
the deterministic planner. The provider receives a bounded catalog of valid
meal IDs and may propose a complete alternative week. The backend then checks
that all seven dates exist, all meal IDs are known, manual and cooked entries
are unchanged, repeat avoidance is respected, excluded meals are not used, and
there are no duplicates. Only a proposal that passes every check is saved.

Provider timeouts, connection failures, malformed JSON, unknown IDs, and rule
violations are logged without secrets and cause the deterministic candidate to
be used. For rejected HTTP requests, a bounded structured error message from
the provider is logged when available. The add-on therefore remains fully
usable when AI is disabled or temporarily unavailable.

Select **Suggest meals** above the meal database to request new ideas. A
suggestion is never saved automatically: **Review and add** first opens the
normal meal editor so every field can be checked or changed.
