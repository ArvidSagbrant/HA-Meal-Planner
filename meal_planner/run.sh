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
export MEAL_PLANNER_NUTRITION_WEIGHT="$(read_option 'nutrition_weight' '0.5')"
export MEAL_PLANNER_CALORIE_TARGET_KCAL="$(read_option 'calorie_target_kcal' '600')"
export MEAL_PLANNER_MAX_CONSECUTIVE_PROTEIN_SOURCE="$(read_option 'max_consecutive_protein_source' '7')"
export MEAL_PLANNER_WEEKDAY_EFFORT_TARGET="$(read_option 'weekday_effort_target' '2')"
export MEAL_PLANNER_WEEKEND_EFFORT_TARGET="$(read_option 'weekend_effort_target' '4')"

export MEAL_PLANNER_AI_PROVIDER="$(read_option 'ai_provider' 'disabled')"
export MEAL_PLANNER_AI_BASE_URL="$(read_option 'ai_base_url' '')"
export MEAL_PLANNER_AI_API_KEY="$(read_option 'ai_api_key' '')"
export MEAL_PLANNER_AI_MODEL="$(read_option 'ai_model' 'gpt-5-mini')"
export MEAL_PLANNER_AI_TIMEOUT_SECONDS="$(read_option 'ai_timeout_seconds' '30')"
export MEAL_PLANNER_AI_TEMPERATURE="$(read_option 'ai_temperature' '0.2')"
export MEAL_PLANNER_AI_REFINEMENT_ENABLED="$(read_option 'ai_refinement_enabled' 'true')"
export MEAL_PLANNER_AI_SUGGESTIONS_ENABLED="$(read_option 'ai_suggestions_enabled' 'true')"

if [[ "${MEAL_PLANNER_AI_PROVIDER}" == "openai" && -z "${MEAL_PLANNER_AI_BASE_URL}" ]]; then
    export MEAL_PLANNER_AI_BASE_URL="https://api.openai.com/v1"
elif [[ "${MEAL_PLANNER_AI_PROVIDER}" == "llamacpp" && -z "${MEAL_PLANNER_AI_BASE_URL}" ]]; then
    export MEAL_PLANNER_AI_BASE_URL="http://localhost:8080/v1"
fi

export MEAL_PLANNER_MQTT_MODE="$(read_option 'mqtt_mode' 'auto')"
export MEAL_PLANNER_MQTT_DISCOVERY_PREFIX="$(read_option 'mqtt_discovery_prefix' 'homeassistant')"
export MEAL_PLANNER_MQTT_TOPIC_PREFIX="$(read_option 'mqtt_topic_prefix' 'meal_planner')"
export MEAL_PLANNER_MQTT_BIRTH_TOPIC="$(read_option 'mqtt_birth_topic' 'homeassistant/status')"
export MEAL_PLANNER_MQTT_ENABLED="false"

if [[ "${MEAL_PLANNER_MQTT_MODE}" == "external" ]]; then
    export MEAL_PLANNER_MQTT_ENABLED="true"
    export MEAL_PLANNER_MQTT_HOST="$(read_option 'mqtt_host' '')"
    export MEAL_PLANNER_MQTT_PORT="$(read_option 'mqtt_port' '1883')"
    export MEAL_PLANNER_MQTT_USERNAME="$(read_option 'mqtt_username' '')"
    export MEAL_PLANNER_MQTT_PASSWORD="$(read_option 'mqtt_password' '')"
    export MEAL_PLANNER_MQTT_TLS="$(read_option 'mqtt_tls' 'false')"
elif [[ "${MEAL_PLANNER_MQTT_MODE}" == "auto" && -n "${SUPERVISOR_TOKEN:-}" ]]; then
    mqtt_host="$(bashio::services 'mqtt' 'host' 2>/dev/null || true)"
    if bashio::var.has_value "${mqtt_host}"; then
        export MEAL_PLANNER_MQTT_ENABLED="true"
        export MEAL_PLANNER_MQTT_HOST="${mqtt_host}"
        export MEAL_PLANNER_MQTT_PORT="$(bashio::services 'mqtt' 'port')"
        export MEAL_PLANNER_MQTT_USERNAME="$(bashio::services 'mqtt' 'username')"
        export MEAL_PLANNER_MQTT_PASSWORD="$(bashio::services 'mqtt' 'password')"
        export MEAL_PLANNER_MQTT_TLS="$(bashio::services 'mqtt' 'ssl')"
        bashio::log.info "Using the Supervisor-provided MQTT service"
    else
        bashio::log.warning "No Supervisor MQTT service was found; MQTT entities are disabled"
    fi
fi

if [[ -n "${SUPERVISOR_TOKEN:-}" ]]; then
    supervisor_timezone="$(bashio::supervisor.timezone 2>/dev/null || true)"
    if [[ -n "${supervisor_timezone}" ]]; then
        export TZ="${supervisor_timezone}"
    fi
fi

exec python3 -m uvicorn meal_planner.main:app \
    --host 0.0.0.0 \
    --port 8099
