from types import SimpleNamespace

from app.role import api as role_api
from app.role import ui as role_ui


def test_api_list_roles_uses_service_layer(monkeypatch, client):
    fake_roles = [SimpleNamespace(to_dict=lambda: {"id": "1"})]
    monkeypatch.setattr(role_api, "get_roles", lambda sort, status: fake_roles)

    response = client.get("/api/v1/roles/?sort=grade&status=all")

    assert response.status_code == 200
    assert response.get_json() == [{"id": "1"}]


def test_api_view_uses_service_layer(monkeypatch, client):
    fake_role = SimpleNamespace(to_dict=lambda: {"id": "42"})
    monkeypatch.setattr(role_api, "get_role", lambda id: fake_role)

    response = client.get("/api/v1/roles/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 200
    assert response.get_json() == {"id": "42"}


def test_ui_list_roles_uses_service_layer(monkeypatch, client):
    fake_form = SimpleNamespace(
        sort=SimpleNamespace(data="grade"),
        status=SimpleNamespace(data="active"),
        validate_on_submit=lambda: False,
    )
    monkeypatch.setattr(role_ui, "RoleSortFilterForm", lambda: fake_form)
    monkeypatch.setattr(role_ui, "get_roles", lambda sort, status: ["role1"])

    rendered = {}

    def fake_render_template(template, **context):
        rendered["template"] = template
        rendered["context"] = context
        return "rendered"

    monkeypatch.setattr(role_ui, "render_template", fake_render_template)

    response = client.get("/roles/?sort=grade&status=active")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert rendered["template"] == "list-roles.html"
    assert rendered["context"]["roles"] == ["role1"]
    assert rendered["context"]["form"] is fake_form
