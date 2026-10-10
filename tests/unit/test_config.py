import importlib

import pytest

import config


@pytest.mark.parametrize("setting", [None, "", " ,  "])
def test_professions_configuration_is_empty_for_blank_settings(monkeypatch: pytest.MonkeyPatch, setting: str | None):
    """
    GIVEN an unset or blank PROFESSIONS environment setting
    WHEN configuration is loaded
    THEN no professions are configured.
    """
    if setting is None:
        monkeypatch.delenv("PROFESSIONS", raising=False)
    else:
        monkeypatch.setenv("PROFESSIONS", setting)

    loaded_config = importlib.reload(config)

    assert loaded_config.Config.PROFESSIONS == []


def test_professions_configuration_trims_and_preserves_values(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    GIVEN a comma-separated PROFESSIONS environment setting
    WHEN configuration is loaded
    THEN trimmed non-blank values retain their configured order and spelling.
    """
    monkeypatch.setenv("PROFESSIONS", " Engineering,Product Design, , delivery ")

    loaded_config = importlib.reload(config)

    assert loaded_config.Config.PROFESSIONS == [
        "Engineering",
        "Product Design",
        "delivery",
    ]
