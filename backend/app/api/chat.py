import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import chats

router = APIRouter()


class ThreadCreate(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=255)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)


class ThreadResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: uuid.UUID
    sequence: int
    role: str
    content: str
    created_at: datetime
    updated_at: datetime


class CitationResponse(BaseModel):
    id: uuid.UUID
    ticker: str
    form: str
    fiscal_year: int | None = None
    page: str | None = None
    section: str | None = None
    excerpt: str


@router.post("", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: ThreadCreate,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> ThreadResponse:
    return await chats.create_thread(current_user, payload.title)


@router.get("", response_model=list[ThreadResponse])
async def list_chats(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[ThreadResponse]:
    return await chats.list_threads(current_user.id)


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_chat_messages(
    chat_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[MessageResponse]:
    if await chats.get_thread(current_user.id, chat_id) is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await chats.list_messages(current_user.id, chat_id)


@router.post("/{chat_id}/messages", response_model=list[MessageResponse])
async def post_chat_message(
    chat_id: uuid.UUID,
    payload: MessageCreate,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[MessageResponse]:
    turn = await chats.append_turn(current_user.id, chat_id, payload.content)
    if turn is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return list(turn)


@router.get(
    "/{chat_id}/messages/{message_id}/citations",
    response_model=list[CitationResponse],
)
async def get_message_citations(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[CitationResponse]:
    if await chats.get_thread(current_user.id, chat_id) is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await chats.list_message_citations(current_user.id, chat_id, message_id)