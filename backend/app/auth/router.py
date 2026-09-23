from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser, get_current_user

router = APIRouter()


@router.get("/me", response_model=CurrentUser)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> CurrentUser:
    return current_user
