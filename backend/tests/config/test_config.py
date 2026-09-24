import pytest
from pydantic import ValidationError

from app.config import Settings

_REQUIRED_SETTINGS = {
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "DATABASE_URL",
    "OPENAI_API_KEY",
}


@pytest.mark.parametrize("missing_name", sorted(_REQUIRED_SETTINGS))
def test_settings_fail_when_required_environment_variable_is_missing(
    monkeypatch,
    tmp_path,
    missing_name: str,
) -> None:
    for name in _REQUIRED_SETTINGS:
        monkeypatch.setenv(name, "test-value")
    monkeypatch.delenv(missing_name)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=tmp_path / "missing.env")

    assert missing_name.lower() in str(error.value)
