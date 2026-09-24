import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser
from app.main import app


@pytest.fixture
def test_user() -> CurrentUser:
    return CurrentUser(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email="analyst@example.com",
    )


@pytest.fixture
def client(test_user: CurrentUser) -> TestClient:
    from app.auth.dependencies import get_current_user

    async def override_current_user() -> CurrentUser:
        return test_user

    app.dependency_overrides[get_current_user] = override_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()
