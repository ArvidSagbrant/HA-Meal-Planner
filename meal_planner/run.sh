#!/usr/bin/with-contenv bashio
set -e

export MEAL_PLANNER_DATA_DIR="/data"
export MEAL_PLANNER_INGRESS_ONLY="true"

read_option() {
    local key="$1"
    local default_value="$2"
    local value=""
    if [[ -n "${SUPERVISOR_TOKEN:-}" ]]; then
        value="$(bashio::config "${key}" 2>/dev/null)" || value=""
    elif [[ -f /data/options.json ]]; then
        value="$(jq -r --arg key "${key}" --arg fallback "${default_value}" \
            '.[$key] // $fallback' /data/options.json)"
    fi
    if [[ -z "${value}" || "${value}" == "null" ]]; then
        value="${default_value}"
    fi
    echo "${value}"
}

export MEAL_PLANNER_LANGUAGE="$(read_option 'language' 'en')"
export MEAL_PLANNER_LOG_LEVEL="$(read_option 'log_level' 'INFO')"
export MEAL_PLANNER_REPEAT_AVOIDANCE_WEEKS="$(read_option 'repeat_avoidance_weeks' '2')"
export MEAL_PLANNER_VEGETARIAN_TARGET="$(read_option 'vegetarian_target' '2')"
export MEAL_PLANNER_PREFERENCE_WEIGHT="$(read_option 'preference_weight' '1.0')"
export MEAL_PLANNER_RECENCY_WEIGHT="$(read_option 'recency_weight' '1.0')"
export MEAL_PLANNER_EFFORT_WEIGHT="$(read_option 'effort_weight' '0.6')"
export MEAL_PLANNER_VARIETY_WEIGHT="$(read_option 'variety_weight' '1.0')"
export MEAL_PLANNER_WEEKDAY_EFFORT_TARGET="$(read_option 'weekday_effort_target' '2')"
export MEAL_PLANNER_WEEKEND_EFFORT_TARGET="$(read_option 'weekend_effort_target' '4')"

exec python3 -m uvicorn meal_planner.main:app \
    --host 0.0.0.0 \
    --port 8099
