"""Small dependency container used by HTTP routes."""

from dataclasses import dataclass

from .config import Settings
from .database import Database
from .planner import DeterministicPlanner
from .repositories import MealRepository, PlanRepository
from .services.meals import MealService
from .services.plans import PlanService


@dataclass(slots=True)
class Container:
    settings: Settings
    database: Database
    meals: MealService
    plans: PlanService

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        database = Database(settings.database_path)
        meal_repository = MealRepository(database)
        plan_repository = PlanRepository(database)
        planner = DeterministicPlanner(settings.planner)
        return cls(
            settings=settings,
            database=database,
            meals=MealService(meal_repository),
            plans=PlanService(plan_repository, meal_repository, planner),
        )
