# Meal Planner for Home Assistant

Meal Planner is a Home Assistant add-on for maintaining a meal database and
building persistent weekly plans. It provides a responsive Ingress UI, meal
CRUD with locally stored images and nutrition, manual overrides, deterministic
plan generation based on meal history and preferences, cooked-meal tracking,
and English/Swedish localization.

## Install in Home Assistant

1. In **Settings → Add-ons → Add-on store**, open the repository menu.
2. Add `https://github.com/ArvidSagbrant/HA-Meal-Planner` as a repository.
3. Install **Meal Planner**, configure its language and log level, and start it.
4. Enable **Show in sidebar** to open the Ingress UI from Home Assistant.

All persistent state is stored in the add-on `/data` directory using SQLite.

## Development

The add-on lives in `meal_planner/`. Its backend uses FastAPI with a deliberately
small repository/service/API split so the deterministic planner, MQTT integration,
and AI providers can be added without coupling them to persistence or HTTP.
The image uses Home Assistant's current multi-platform Python base for `amd64`
and `aarch64` and is built directly from its Dockerfile.

```bash
cd meal_planner
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=app .venv/bin/pytest
```

For local use, set a writable data directory and run Uvicorn:

```bash
MEAL_PLANNER_DATA_DIR=./data PYTHONPATH=app \
  .venv/bin/uvicorn meal_planner.main:app --port 8099
```

The API documentation is available at `/api/docs`. Important endpoints are:

- `GET/POST /api/meals`
- `GET/PATCH/DELETE /api/meals/{meal_id}`
- `GET/PUT/DELETE /api/meals/{meal_id}/image`
- `GET /api/plans/{monday}`
- `POST /api/plans/{monday}/generate`
- `PUT/DELETE /api/plans/{monday}/days/{date}`
- `PATCH /api/plans/{monday}/days/{date}/cooked`
- `POST /api/plans/{monday}/days/{date}/regenerate`
- `GET /api/mqtt/status`
- `GET /api/ai/status`
- `POST /api/ai/suggestions`

The add-on automatically uses Home Assistant's Supervisor-provided MQTT service
when available. MQTT Discovery creates stable today and tomorrow sensors; an
external broker or disabled MQTT can be selected in the add-on configuration.

Meal images are signature-validated PNG, JPEG, GIF, or WebP files up to 5 MB.
They are stored beneath `/data/images`, served only through the meal API, and
removed when replaced, explicitly cleared, or when their meal is deleted.

Optional AI assistance supports OpenAI's Responses API and a local llama.cpp
OpenAI-compatible server. Deterministic generation remains authoritative: every
AI refinement is validated against meal IDs, fixed assignments, and all hard
planning constraints before it can be persisted. AI failures fall back to the
deterministic candidate. Meal suggestions are previews that open in the normal
editor and are never inserted automatically.

See [SPECIFICATION.md](SPECIFICATION.md) for the complete product specification.
