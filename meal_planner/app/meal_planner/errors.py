"""Application-level errors translated by the API layer."""


class MealPlannerError(Exception):
    """Base class for expected application errors."""


class NotFoundError(MealPlannerError):
    pass


class ConflictError(MealPlannerError):
    pass


class InvalidOperationError(MealPlannerError):
    pass

