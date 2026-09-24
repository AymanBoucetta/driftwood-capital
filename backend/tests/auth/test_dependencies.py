import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.auth.dependencies import CurrentUser, get_access_token, get_current_user


def test_get_access_token_requires_bearer_credentials() -> None:
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_access_token(None))

    assert error.value.status_code == 401
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}


def test_get_current_user_returns_verified_supabase_user(monkeypatch) -> None:
    class FakeAuth:
        async def get_user(self, *, jwt: str):
            assert jwt == "valid-token"
            return type(
                "Response",
                (),
                {
                    "user": type(
                        "User",
                        (),
                        {
                            "id": "22222222-2222-2222-2222-222222222222",
                            "email": "verified@example.com",
                        },
                    )()
                },
            )()

    fake_client = type("Client", (), {"auth": FakeAuth()})()

    async def fake_create_client(*args, **kwargs):
        return fake_client

    monkeypatch.setattr("app.auth.dependencies.acreate_client", fake_create_client)

    result = asyncio.run(get_current_user("valid-token"))

    assert result == CurrentUser(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        email="verified@example.com",
    )
