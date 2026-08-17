"""Small dependency container used by HTTP routes."""

from dataclasses import dataclass

from .config import Settings
from .database import Database
from .events import ChangeNotifier
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
    mqtt: MqttIntegration

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        database = Database(settings.database_path)
        meal_repository = MealRepository(database)
        plan_repository = PlanRepository(database)
        planner = DeterministicPlanner(settings.planner)
        changes = ChangeNotifier()
        meals = MealService(meal_repository, changes.notify)
        plans = PlanService(
            plan_repository,
            meal_repository,
            planner,
            changes.notify,
        )
        mqtt = MqttIntegration(settings.mqtt, plans, settings.language)
        changes.subscribe(mqtt.publish_state)
        return cls(
            settings=settings,
            database=database,
            changes=changes,
            meals=meals,
            plans=plans,
            mqtt=mqtt,
        )
