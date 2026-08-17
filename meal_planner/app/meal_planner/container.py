"""Small dependency container used by HTTP routes."""

from dataclasses import dataclass

from .ai import AIService, build_ai_provider
from .config import Settings
from .database import Database
from .events import ChangeNotifier
from .images import MealImageStore
from .mqtt import MqttIntegration
from .planner import DeterministicPlanner
from .repositories import MealRepository, PlanRepository
from .services.meals import MealService
from .services.plans import PlanService


@dataclass(slots=True)
class Container:
    settings: Settings
    database: Database
    changes: ChangeNotifier
    meals: MealService
    plans: PlanService
    ai: AIService
    mqtt: MqttIntegration

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        database = Database(settings.database_path)
        meal_repository = MealRepository(database)
        plan_repository = PlanRepository(database)
        planner = DeterministicPlanner(settings.planner)
        changes = ChangeNotifier()
        meals = MealService(
            meal_repository,
            MealImageStore(settings.data_dir),
            changes.notify,
        )
        ai = AIService(
            settings.ai,
            build_ai_provider(settings.ai),
            planner,
            meal_repository,
            settings.language,
        )
        plans = PlanService(
            plan_repository,
            meal_repository,
            planner,
            ai=ai,
            on_change=changes.notify,
        )
        mqtt = MqttIntegration(settings.mqtt, plans, settings.language)
        changes.subscribe(mqtt.publish_state)
        return cls(
            settings=settings,
            database=database,
            changes=changes,
            meals=meals,
            plans=plans,
            ai=ai,
            mqtt=mqtt,
        )
