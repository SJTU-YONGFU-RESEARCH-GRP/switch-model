"""Tests for Spectre engine environment handling."""

from __future__ import annotations

from _pytest.monkeypatch import MonkeyPatch

from switch_model.spectre_engine import _spectre_env


def test_spectre_env_does_not_inject_license_path(monkeypatch: MonkeyPatch) -> None:
    """Spectre subprocess env should inherit the caller environment only."""
    monkeypatch.delenv("LM_LICENSE_FILE", raising=False)
    monkeypatch.setenv("SWITCH_MODEL_TEST_ENV", "1")

    env = _spectre_env()

    assert "LM_LICENSE_FILE" not in env
    assert env.get("SWITCH_MODEL_TEST_ENV") == "1"
