"""Meal CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import FileResponse

from ...errors import ImageValidationError
from ...images import MAX_IMAGE_BYTES
from ...schemas import Meal, MealCreate, MealUpdate
from ...services.meals import MealService
from ..dependencies import get_meal_service


router = APIRouter(prefix="/meals", tags=["meals"])
MealServiceDependency = Annotated[MealService, Depends(get_meal_service)]


@router.get("", response_model=list[Meal])
def list_meals(service: MealServiceDependency) -> list[Meal]:
    return service.list_meals()


@router.post("", response_model=Meal, status_code=status.HTTP_201_CREATED)
def create_meal(payload: MealCreate, service: MealServiceDependency) -> Meal:
    return service.create_meal(payload)


@router.get("/{meal_id}", response_model=Meal)
def get_meal(meal_id: str, service: MealServiceDependency) -> Meal:
    return service.get_meal(meal_id)


@router.patch("/{meal_id}", response_model=Meal)
def update_meal(meal_id: str, payload: MealUpdate, service: MealServiceDependency) -> Meal:
    return service.update_meal(meal_id, payload)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(meal_id: str, service: MealServiceDependency) -> Response:
    service.delete_meal(meal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{meal_id}/image", response_model=Meal)
async def upload_image(
    meal_id: str,
    request: Request,
    service: MealServiceDependency,
) -> Meal:
    service.get_meal(meal_id)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            exceeds_limit = int(content_length) > MAX_IMAGE_BYTES
        except ValueError as error:
            raise ImageValidationError("Invalid image content length") from error
        if exceeds_limit:
            raise ImageValidationError("The uploaded image exceeds the 5 MB limit")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_IMAGE_BYTES:
            raise ImageValidationError("The uploaded image exceeds the 5 MB limit")
        chunks.append(chunk)
    return service.save_image(meal_id, b"".join(chunks))


@router.get("/{meal_id}/image", response_class=FileResponse)
def get_image(meal_id: str, service: MealServiceDependency) -> FileResponse:
    path, media_type = service.get_image(meal_id)
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.delete("/{meal_id}/image", response_model=Meal)
def delete_image(meal_id: str, service: MealServiceDependency) -> Meal:
    return service.delete_image(meal_id)
