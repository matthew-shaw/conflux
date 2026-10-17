import csv
from datetime import UTC, datetime
from io import StringIO
from types import SimpleNamespace

import pytest

from app.person import ui as person_ui
from app.role import ui as role_ui
from app.service import ui as service_ui
from app.team import ui as team_ui

UPDATED_AT = datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)
ARCHIVED_AT = datetime(2024, 2, 3, 4, 5, 6, tzinfo=UTC)


@pytest.mark.parametrize(
    ("blueprint", "service_function", "url", "resource", "expected_header", "expected_row"),
    [
        pytest.param(
            person_ui,
            "download_people",
            "/people/download",
            SimpleNamespace(
                id="person-1",
                name="aDA eXAMPLE",
                email_address="ADA@EXAMPLE.COM",
                location="london",
                employment="employee",
                updated_at=UPDATED_AT,
                archived_at=None,
                role_id="role-1",
                team_id="team-1",
                manager_id=None,
                role=SimpleNamespace(name="software engineer"),
                team=SimpleNamespace(name="platform team"),
                manager=None,
            ),
            [
                "ID",
                "NAME",
                "EMAIL_ADDRESS",
                "LOCATION",
                "EMPLOYMENT",
                "UPDATED_AT",
                "ARCHIVED_AT",
                "ROLE_ID",
                "ROLE_NAME",
                "TEAM_ID",
                "TEAM_NAME",
                "MANAGER_ID",
                "MANAGER_NAME",
            ],
            [
                "person-1",
                "Ada Example",
                "ada@example.com",
                "London",
                "Employee",
                "2024-01-02T03:04:05Z",
                "",
                "role-1",
                "Software Engineer",
                "team-1",
                "Platform Team",
                "",
                "",
            ],
            id="people",
        ),
        pytest.param(
            role_ui,
            "download_roles",
            "/roles/download",
            SimpleNamespace(
                id="role-1",
                name="software engineer",
                grade="grade 7",
                profession="software development",
                updated_at=UPDATED_AT,
                archived_at=ARCHIVED_AT,
            ),
            ["ID", "NAME", "GRADE", "PROFESSION", "UPDATED_AT", "ARCHIVED_AT"],
            [
                "role-1",
                "Software Engineer",
                "Grade 7",
                "Software Development",
                "2024-01-02T03:04:05Z",
                "2024-02-03T04:05:06Z",
            ],
            id="roles",
        ),
        pytest.param(
            team_ui,
            "download_teams",
            "/teams/download",
            SimpleNamespace(
                id="team-1",
                name="engineering team",
                archived_at=ARCHIVED_AT,
                updated_at=UPDATED_AT,
            ),
            ["ID", "NAME", "ARCHIVED_AT", "UPDATED_AT"],
            [
                "team-1",
                "Engineering Team",
                "2024-02-03T04:05:06Z",
                "2024-01-02T03:04:05Z",
            ],
            id="teams",
        ),
        pytest.param(
            service_ui,
            "download_services",
            "/services/download",
            SimpleNamespace(
                id="service-1",
                name="case management",
                description="A service, with a comma",
                archived_at=None,
                updated_at=UPDATED_AT,
                team_id="team-1",
                team=SimpleNamespace(name="platform team"),
            ),
            ["ID", "NAME", "DESCRIPTION", "ARCHIVED_AT", "UPDATED_AT", "TEAM_ID", "TEAM_NAME"],
            [
                "service-1",
                "Case Management",
                "A service, with a comma",
                "",
                "2024-01-02T03:04:05Z",
                "team-1",
                "Platform Team",
            ],
            id="services",
        ),
    ],
)
def test_csv_exports_include_all_resource_columns(
    app,
    test_client,
    monkeypatch,
    blueprint,
    service_function,
    url,
    resource,
    expected_header,
    expected_row,
) -> None:
    """GIVEN a resource instance with every persisted field
    WHEN its CSV export is downloaded
    THEN the row contains every model field, foreign-key ID, and related name."""
    monkeypatch.setattr(blueprint, service_function, lambda: [resource])

    response = test_client.get(url)

    assert response.status_code == 200
    rows = list(csv.reader(StringIO(response.get_data(as_text=True).lstrip("\ufeff"))))
    assert rows == [expected_header, expected_row]
