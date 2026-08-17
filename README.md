# Meal Planner for Home Assistant

Meal Planner is a Home Assistant add-on for maintaining a meal database and
building persistent weekly plans. The first release provides a responsive
Ingress UI, meal CRUD, manual day assignments, and English/Swedish localization.

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
- `GET /api/plans/{monday}`
- `PUT/DELETE /api/plans/{monday}/days/{date}`

See [SPECIFICATION.md](SPECIFICATION.md) for the complete product specification.
