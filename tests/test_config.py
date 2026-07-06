from __future__ import annotations

from store_assistant.config import load_settings


def test_load_settings_reads_openapi_key_file_when_env_missing(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "openapi_key.txt").write_text("sk-test-key\n", encoding="utf-8")

    settings = load_settings()

    assert settings.openai_api_key == "sk-test-key"


def test_load_settings_prefers_openai_api_key_file_name(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "openai_api_key.txt").write_text("sk-canonical-key\n", encoding="utf-8")
    (tmp_path / "openapi_key.txt").write_text("sk-legacy-key\n", encoding="utf-8")

    settings = load_settings()

    assert settings.openai_api_key == "sk-canonical-key"


def test_openai_api_key_env_takes_precedence_over_key_file(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "openapi_key.txt").write_text("sk-file-key\n", encoding="utf-8")

    settings = load_settings()

    assert settings.openai_api_key == "sk-env-key"
