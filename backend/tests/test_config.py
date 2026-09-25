from app.core.config import Settings


def test_default_settings():
    settings = Settings(_env_file=None)

    assert settings.app_name == "Guardian Nexus Backend"
    assert settings.app_env == "development"
    assert settings.debug is True
    assert settings.cors_origin_list == ["http://localhost:3000"]
    assert settings.assemblyai_api_key is None
    assert settings.nebius_api_key is None
    assert settings.tavily_api_key is None


def test_cors_origin_list_normalization():
    settings = Settings(
        CORS_ORIGINS="http://localhost:3000, https://example.com, ,"
    )

    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "https://example.com",
    ]


def test_settings_accept_environment_values(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Guardian")
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DEBUG", "false")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test Guardian"
    assert settings.app_env == "testing"
    assert settings.debug is False
