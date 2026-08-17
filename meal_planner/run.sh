#!/usr/bin/with-contenv bashio
set -e

export MEAL_PLANNER_DATA_DIR="/data"
export MEAL_PLANNER_INGRESS_ONLY="true"

if [[ -n "${SUPERVISOR_TOKEN:-}" ]]; then
    export MEAL_PLANNER_LANGUAGE="$(bashio::config 'language')"
    export MEAL_PLANNER_LOG_LEVEL="$(bashio::config 'log_level')"
elif [[ -f /data/options.json ]]; then
    export MEAL_PLANNER_LANGUAGE="$(jq -r '.language // "en"' /data/options.json)"
    export MEAL_PLANNER_LOG_LEVEL="$(jq -r '.log_level // "INFO"' /data/options.json)"
else
    export MEAL_PLANNER_LANGUAGE="en"
    export MEAL_PLANNER_LOG_LEVEL="INFO"
fi

exec python3 -m uvicorn meal_planner.main:app \
    --host 0.0.0.0 \
    --port 8099
