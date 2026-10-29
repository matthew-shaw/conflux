import importlib

import pytest

import config


@pytest.mark.parametrize("setting_name", ["GRADES", "LOCATIONS", "PROFESSIONS", "TEAM_TYPES"])
@pytest.mark.parametrize("setting", [None, "", " ,  "])
def test_list_configuration_is_empty_for_blank_settings(
    monkeypatch: pytest.MonkeyPatch,
    setting_name: str,
    setting: str | None,
):
    """
    GIVEN an unset or blank list configuration environment setting
    WHEN configuration is loaded
    THEN no values are configured for that setting.
    """
    if setting is None:
        monkeypatch.delenv(setting_name, raising=False)
    else:
        monkeypatch.setenv(setting_name, setting)

    loaded_config = importlib.reload(config)

    assert getattr(loaded_config.Config, setting_name) == []


@pytest.mark.parametrize("setting_name", ["GRADES", "LOCATIONS", "PROFESSIONS", "TEAM_TYPES"])
def test_list_configuration_trims_and_preserves_values(
    monkeypatch: pytest.MonkeyPatch,
    setting_name: str,
):
    """
    GIVEN a comma-separated list configuration environment setting
    WHEN configuration is loaded
    THEN trimmed non-blank values retain their configured order and spelling.
    """
    monkeypatch.setenv(setting_name, " Engineering,Product Design, , delivery ")

    loaded_config = importlib.reload(config)

    assert getattr(loaded_config.Config, setting_name) == [
        "Engineering",
        "Product Design",
        "delivery",
    ]
