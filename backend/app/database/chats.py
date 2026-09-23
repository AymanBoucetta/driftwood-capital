import uuid
from typing import Any

from app.auth.dependencies import CurrentUser
from app.database.supabase import get_service_role_client


async def ensure_user(user: CurrentUser) -> None:
    client = await get_service_role_client()
    existing = (
        await client.table("users")
        .select("id")
        .eq("id", str(user.id))
        .maybe_single()
        .execute()
    )
    if existing.data is None:
        await client.table("users").insert(
            {
                "id": str(user.id),
                "name": user.email.split("@", 1)[0],
                "email": user.email,
            }
        ).execute()


async def list_threads(user_id: uuid.UUID) -> list[dict[str, Any]]:
    client = await get_service_role_client()
    response = (
        await client.table("chat_threads")
        .select("id, title, created_at, updated_at")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data or []


async def create_thread(user: CurrentUser, title: str) -> dict[str, Any]:
    await ensure_user(user)
    client = await get_service_role_client()
    response = (
        await client.table("chat_threads")
        .insert({"user_id": str(user.id), "title": title})
        .select("id, title, created_at, updated_at")
        .single()
        .execute()
    )
    return response.data


async def get_thread(user_id: uuid.UUID, thread_id: uuid.UUID) -> dict[str, Any] | None:
    client = await get_service_role_client()
    response = (
        await client.table("chat_threads")
        .select("id, title, created_at, updated_at")
        .eq("id", str(thread_id))
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    return response.data


async def list_messages(user_id: uuid.UUID, thread_id: uuid.UUID) -> list[dict[str, Any]]:
    thread = await get_thread(user_id, thread_id)
    if thread is None:
        return []

    client = await get_service_role_client()
    response = (
        await client.table("chat_messages")
        .select("id, sequence, role, content, created_at, updated_at")
        .eq("thread_id", str(thread_id))
        .order("sequence")
        .execute()
    )
    return response.data or []


async def list_message_citations(
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    message_id: uuid.UUID,
) -> list[dict[str, Any]]:
    thread = await get_thread(user_id, thread_id)
    if thread is None:
        return []

    client = await get_service_role_client()
    message = (
        await client.table("chat_messages")
        .select("id")
        .eq("id", str(message_id))
        .eq("thread_id", str(thread_id))
        .maybe_single()
        .execute()
    )
    if message.data is None:
        return []

    response = (
        await client.table("message_citations")
        .select("id, ticker, form, fiscal_year, page, section, excerpt")
        .eq("message_id", str(message_id))
        .execute()
    )
    return response.data or []


async def append_turn(
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    content: str,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    thread = await get_thread(user_id, thread_id)
    if thread is None:
        return None

    messages = await list_messages(user_id, thread_id)
    sequence = len(messages) + 1
    client = await get_service_role_client()
    user_response = (
        await client.table("chat_messages")
        .insert(
            {
                "thread_id": str(thread_id),
                "sequence": sequence,
                "role": "USER",
                "content": content,
            }
        )
        .select("id, sequence, role, content, created_at, updated_at")
        .single()
        .execute()
    )
    assistant_response = (
        await client.table("chat_messages")
        .insert(
            {
                "thread_id": str(thread_id),
                "sequence": sequence + 1,
                "role": "ASSISTANT",
                "content": "The assistant is not connected to retrieval yet. Your message was saved successfully.",
            }
        )
        .select("id, sequence, role, content, created_at, updated_at")
        .single()
        .execute()
    )
    return user_response.data, assistant_response.data