# Changelog

## 0.2.1

- Replace free-text protein/source values with a localized predefined catalog.
- Add an explicit vegetarian property to meals.
- Add cooked-day tracking and use only cooked meals for repeat history.
- Preserve and lock cooked plan entries until they are unmarked.
- Migrate existing Swedish and English protein/source values automatically.

## 0.2.0

- Add deterministic, score-based full-week generation.
- Preserve manual overrides while generating and prevent duplicate weekly meals.
- Use historical plans and configurable repeat avoidance during generation.
- Add configurable preference, recency, effort, variety, and vegetarian scoring.
- Add single-day regeneration without changing the rest of the week.

## 0.1.1

- Normalize duplicate leading slashes added by Home Assistant Ingress so API
  requests reach the FastAPI routes.

## 0.1.0

- Add the Home Assistant add-on scaffold and Ingress web application.
- Add persistent meal CRUD and weekly manual meal assignment.
- Add English and Swedish localization.
