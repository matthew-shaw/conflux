import csv
from pathlib import Path

from data import generate


def test_generated_teams_use_configured_types(monkeypatch, tmp_path: Path) -> None:
    """
    GIVEN a configured list of team types
    WHEN demo data is generated
    THEN every generated team has one of those types in the teams CSV.
    """
    configured = {
        "GRADES": ["EO", "HEO", "SEO", "G7", "G6"],
        "LOCATIONS": ["London"],
        "PROFESSIONS": [
            "Software Development",
            "Product and Delivery",
            "Quality Assurance Testing",
            "User-Centred Design",
        ],
        "TEAM_TYPES": ["Configured Type A", "Configured Type B"],
    }
    monkeypatch.setattr(generate, "configured_values", lambda name: configured[name])
    monkeypatch.setattr(generate, "DATA_DIR", tmp_path)

    counts = generate.generate_demo_data()

    with (tmp_path / "teams.csv").open(newline="", encoding="utf-8") as teams_file:
        reader = csv.DictReader(teams_file)
        fieldnames = reader.fieldnames
        teams = list(reader)

    assert counts["teams"] == len(teams)
    assert fieldnames is not None
    assert "type" in fieldnames
    assert len(teams) == len(generate.TEAM_NAMES)
    assert all(team["type"] in configured["TEAM_TYPES"] for team in teams)
