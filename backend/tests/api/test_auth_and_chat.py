import asyncio
import uuid
from unittest.mock import AsyncMock

from app.auth.dependencies import CurrentUser
from app.database import chats

THREAD_A = {
    "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "title": "Owned thread",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}
THREAD_B = {
    "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "title": "Other thread",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_me_requires_authentication() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/auth/me")

    assert response.status_code == 401


def test_me_returns_current_user(client, test_user: CurrentUser) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(test_user.id),
        "email": test_user.email,
    }


def test_chat_list_is_scoped_to_current_user(client, monkeypatch) -> None:
    list_threads = AsyncMock(return_value=[THREAD_A])
    monkeypatch.setattr(chats, "list_threads", list_threads)

    response = client.get("/chats")

    assert response.status_code == 200
    assert response.json() == [THREAD_A]
    list_threads.assert_awaited_once_with(uuid.UUID("11111111-1111-1111-1111-111111111111"))


def test_chat_messages_reject_a_thread_not_owned_by_user(client, monkeypatch) -> None:
    monkeypatch.setattr(chats, "get_thread", AsyncMock(return_value=None))

    response = client.get(f"/chats/{THREAD_B['id']}/messages")

    assert response.status_code == 404
    assert response.json() == {"detail": "Chat not found"}


def test_citations_cannot_leak_from_another_thread(client, monkeypatch) -> None:
    monkeypatch.setattr(chats, "get_thread", AsyncMock(return_value=THREAD_A))
    citations = AsyncMock(return_value=[])
    monkeypatch.setattr(chats, "list_message_citations", citations)

    response = client.get(
        "/chats/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/messages/"
        "cccccccc-cccc-cccc-cccc-cccccccccccc/citations"
    )

    assert response.status_code == 200
    assert response.json() == []
    citations.assert_awaited_once()


def test_citation_lookup_rejects_message_from_another_thread(monkeypatch) -> None:
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table: str):
            self.table_name = table

        def select(self, *_args):
            return self

        def eq(self, *_args):
            return self

        def maybe_single(self):
            return self

        async def execute(self):
            return Result(None)

    class Client:
        def table(self, table: str):
            return Query(table)

    monkeypatch.setattr(
        chats,
        "get_service_role_client",
        AsyncMock(return_value=Client()),
    )

    result = asyncio.run(
        chats.list_message_citations(
            uuid.UUID("11111111-1111-1111-1111-111111111111"),
            uuid.UUID(THREAD_A["id"]),
            uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        )
    )

    assert result == []
