# Meal Planner – Home Assistant Add-on

## Goal

Create an intuitive Home Assistant add-on for automated weekly meal planning. The add-on maintains a user-managed meal database and generates weekly meal plans using configurable rules and optional AI assistance.

The application should be designed primarily for use through Home Assistant.

## Core requirements

### Meal database

Users must be able to add, edit and delete meals.

Each meal should support at least:

- Name
- Description
- Preference/rating
- Cooking effort
- Image
- Meal type/category
- Protein/source category, e.g. beef, pork, chicken, fish, vegetarian
- Optional tags
- Optional nutritional information

Images should be stored locally by the add-on.

The UI should make browsing and managing meals simple.

### Weekly meal planning

Generate a meal plan for a configurable week, normally Monday–Sunday.

The planner should:

- Select meals from the user's meal database
- Avoid excessive repetition
- Consider meals used during previous weeks
- Consider user preference
- Consider cooking effort
- Produce a varied mix of protein sources
- Include configurable vegetarian meals
- Aim for reasonable nutritional variety
- Avoid selecting the same or very similar meal too frequently

Users must be able to:

- Generate an entire week
- Regenerate an entire week
- Regenerate one specific day
- Manually select/override the meal for any day
- Navigate previous and future weekly plans

Historical plans must be retained and used when generating future plans.

Planning constraints should be configurable where practical.

## Planning engine and deterministic rules

The core meal planning logic must be deterministic and must work without AI.

AI should enhance the planning process, but must not be responsible for enforcing hard planning constraints.

Use the following general planning flow:

`Meal database → deterministic planning engine → optional AI refinement → validation → weekly plan`

The deterministic planning engine should select and score suitable meals based on configurable rules and historical data.

At minimum it should consider:

- How recently each meal was used
- User preference/rating
- Cooking effort
- Protein/source category
- Vegetarian frequency
- Variety across the current week
- Variety compared with previous weeks
- Manual exclusions or constraints

Support both **hard constraints** and **soft preferences**.

Examples of hard constraints:

- Do not select the same meal more than once during the same week
- Do not repeat a meal within a configurable number of previous weeks
- Respect manually excluded meals
- Only select meals that exist in the meal database
- Respect explicitly configured minimum/maximum frequencies where applicable

Examples of soft preferences:

- Prefer highly rated meals
- Avoid using the same protein source on consecutive days
- Spread vegetarian meals across the week
- Avoid several high-effort meals in a row
- Prefer meals that have not been served recently
- Maintain variety compared with previous weeks

Planning parameters should be configurable where practical, including for example:

- Repeat avoidance window
- Target vegetarian meals per week
- Maximum consecutive meals using the same protein/source category
- Weight given to user preference
- Weight given to meal recency
- Weight given to cooking effort
- Desired weekday/weekend cooking effort

The planner should use a scoring or constraint-based approach rather than purely random selection.

Some controlled randomness may be used among similarly scored candidates so that generated weeks are not always identical.

## AI integration

AI should enhance the planner but the basic application must remain functional without AI.

Implement a provider abstraction so different AI backends can be supported.

Initially support:

- Local llama.cpp using its OpenAI-compatible API
- OpenAI API

Configuration should include:

- Provider
- API/base URL
- API key where required
- Model
- Optional advanced parameters

AI can be used for:

1. Generating or refining a weekly plan from available meals
2. Improving variety compared with previous weeks
3. Suggesting new meals to add to the database
4. Optionally estimating categories or nutritional characteristics of meals

The AI should preferably receive a bounded list of valid candidate meals rather than being allowed to freely invent plan entries.

AI responses must use structured output and be validated by the backend.

The AI must not invent meal IDs that do not exist when generating plans.

Any AI-proposed changes must pass through the deterministic validation layer before being accepted.

AI must never be allowed to violate hard planning constraints.

If AI:

- Is unavailable
- Times out
- Returns invalid data
- Suggests unknown meal IDs
- Violates planning constraints

the deterministic candidate plan should be used instead.

Weekly planning must therefore remain fully functional when no AI provider is configured.

## Plan validation

Before a generated plan is persisted, validate that:

- Every referenced meal exists
- Every requested day has a meal
- Hard constraints are satisfied
- Manual overrides are preserved
- No invalid AI-generated values are present

Never replace an existing valid weekly plan unless generation of the replacement succeeds completely.

## Home Assistant integration

Run as a proper Home Assistant add-on.

Provide a Home Assistant Ingress-compatible web UI.

Expose meal information through MQTT Discovery.

At minimum expose:

- Today's meal
- Tomorrow's meal

Consider additional useful entities such as:

- Current week's plan
- Meal image
- Meal cooking effort
- Actions/status related to plan generation

Support:

- Home Assistant Supervisor-provided MQTT broker
- Manually configured external MQTT broker

MQTT configuration should automatically use Supervisor services when available.

Entities should remain stable across add-on restarts.

## Persistence

All application state must survive container/add-on restarts.

Store persistent data under `/data`.

Persist at minimum:

- Meal database
- Images/metadata
- Weekly plans
- Planning history
- User preferences
- AI configuration excluding secrets where Home Assistant configuration provides a better mechanism

Use an appropriate lightweight database such as SQLite.

Database schema should support future migrations.

## Frontend

Frontend must support:

- English
- Swedish

All backend code, API names, database fields, comments and logs should be in English.

Do not hard-code frontend text. Use localization files.

Provide a responsive interface suitable for both desktop and mobile Home Assistant clients.

The primary weekly view should clearly display the seven days and their selected meals, preferably including meal images.

## Configuration

Provide configuration for at least:

- MQTT
- AI provider
- AI model
- Language
- Logging level
- Planning preferences
- Vegetarian frequency / target
- Repeat avoidance/history window

Supported logging levels should include:

- DEBUG
- INFO
- WARNING
- ERROR

Do not log API keys, MQTT passwords or other secrets.

## Architecture

Keep the project modular.

Separate at least:

- Database/storage
- Meal management
- Planning engine
- AI providers
- MQTT/Home Assistant integration
- API
- Frontend

The planning engine should not depend directly on a specific AI provider.

Prefer simple, maintainable solutions over unnecessary complexity.

## Reliability

The application should:

- Start without an AI provider configured
- Handle unavailable AI providers gracefully
- Handle unavailable MQTT gracefully
- Validate configuration
- Validate AI responses
- Preserve existing plans if generation fails
- Provide useful error messages in both logs and frontend

## Testing

Add automated tests for important backend functionality, especially:

- Meal CRUD
- Weekly plan generation
- Regenerating individual days
- Manual overrides
- Historical repeat avoidance
- Persistence
- AI response parsing/validation
- MQTT entity payload generation

## Deliverable

Produce a complete, working Home Assistant add-on rather than a prototype.

Include:

- Add-on configuration
- Dockerfile
- Backend
- Frontend
- Database initialization/migrations
- MQTT Discovery
- AI provider implementation
- English and Swedish localization
- Tests
- README with installation and configuration instructions

Use sensible defaults where requirements are unspecified.

Make reasonable implementation decisions without requiring clarification for minor details.

## Planning engine and deterministic rules

The core meal planning logic must be deterministic and must work without AI.

AI should enhance the planning process, but must not be responsible for enforcing hard planning constraints.

Use the following general planning flow:

`Meal database → deterministic planning engine → optional AI refinement → validation → weekly plan`

The deterministic planning engine should select and score suitable meals based on configurable rules and historical data.

At minimum it should consider:

- How recently each meal was used
- User preference/rating
- Cooking effort
- Protein/source category
- Vegetarian frequency
- Variety across the current week
- Variety compared with previous weeks
- Manual exclusions or constraints

Support both **hard constraints** and **soft preferences**.

Examples of hard constraints:

- Do not select the same meal more than once during the same week
- Do not repeat a meal within a configurable number of previous weeks
- Respect manually excluded meals
- Only select meals that exist in the meal database
- Respect explicitly configured minimum/maximum frequencies where applicable

Examples of soft preferences:

- Prefer highly rated meals
- Avoid using the same protein source on consecutive days
- Spread vegetarian meals across the week
- Avoid several high-effort meals in a row
- Prefer meals that have not been served recently
- Maintain variety compared with previous weeks

Planning parameters should be configurable where practical, including for example:

- Repeat avoidance window
- Target vegetarian meals per week
- Maximum consecutive meals using the same protein/source category
- Weight given to user preference
- Weight given to meal recency
- Weight given to cooking effort
- Desired weekday/weekend cooking effort

The planner should use a scoring or constraint-based approach rather than purely random selection.

Some controlled randomness may be used among similarly scored candidates so that generated weeks are not always identical.

## AI refinement

After the deterministic planner has produced a valid candidate plan, AI may optionally be used to improve the selection.

AI can consider more subjective factors such as:

- Whether the week feels varied
- Complementary cuisines and meal styles
- Overall balance
- Similarity between meals that deterministic categories may not capture
- Suggestions for replacing a meal with another suitable candidate

The AI should preferably receive a bounded list of valid candidate meals rather than being allowed to freely invent plan entries.

Any AI-proposed changes must pass through the deterministic validation layer before being accepted.

AI must never be allowed to violate hard planning constraints.

If AI:

- Is unavailable
- Times out
- Returns invalid data
- Suggests unknown meal IDs
- Violates planning constraints

the deterministic candidate plan should be used instead.

Weekly planning must therefore remain fully functional when no AI provider is configured.

## Plan validation

Before a generated plan is persisted, validate that:

- Every referenced meal exists
- Every requested day has a meal
- Hard constraints are satisfied
- Manual overrides are preserved
- No invalid AI-generated values are present

Never replace an existing valid weekly plan unless generation of the replacement succeeds completely.
