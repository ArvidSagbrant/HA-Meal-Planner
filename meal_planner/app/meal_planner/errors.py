"""Application-level errors translated by the API layer."""


class MealPlannerError(Exception):
    """Base class for expected application errors."""


class NotFoundError(MealPlannerError):
    pass


class ConflictError(MealPlannerError):
    pass


class DuplicateAssignmentError(ConflictError):
    pass


class CookedDayError(ConflictError):
    pass


class InvalidOperationError(MealPlannerError):
    pass


class ImageValidationError(InvalidOperationError):
    pass


class PlanningError(MealPlannerError):
    pass


class AIUnavailableError(MealPlannerError):
    pass
