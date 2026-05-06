from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from app.role import api as role_api
from app.role import ui as role_ui


def test_api_list_roles_uses_service_layer(monkeypatch, test_client):
    """GIVEN the role API list endpoint WHEN the list route is called THEN the service layer provides the returned role payload."""
    fake_roles = [SimpleNamespace(to_dict=lambda: {"id": "1"})]
    monkeypatch.setattr(role_api, "get_roles", lambda sort, status: fake_roles)

    response = test_client.get("/api/v1/roles/?sort=grade&status=all")

    assert response.status_code == 200
    assert response.get_json() == [{"id": "1"}]


def test_api_view_uses_service_layer(monkeypatch, test_client):
    """GIVEN the role API detail endpoint WHEN a role is requested THEN the service layer is used to fetch that role."""
    fake_role = SimpleNamespace(to_dict=lambda include_people=False: {"id": "42"})
    monkeypatch.setattr(role_api, "get_role", lambda id: fake_role)

    response = test_client.get("/api/v1/roles/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 200
    assert response.get_json() == {"id": "42"}


def test_ui_list_roles_uses_service_layer(monkeypatch, test_client):
    """GIVEN the role list page WHEN rendering the page THEN the UI uses the service layer to load roles."""
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

    response = test_client.get("/roles/?sort=grade&status=active")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert rendered["template"] == "list-roles.html"
    assert rendered["context"]["roles"] == ["role1"]
    assert rendered["context"]["form"] is fake_form


class DummyForm:
    def __init__(self, submit=False, name="", grade="", confirm=False):
        self.name = SimpleNamespace(data=name)
        self.grade = SimpleNamespace(data=grade, choices=[])
        self.confirm = SimpleNamespace(data=confirm)
        self.name.errors = []
        self._submit = submit

    def validate_on_submit(self):
        return self._submit


def test_ui_create_get_renders_form(monkeypatch, test_client):
    """GIVEN the create role page WHEN requested via GET THEN the creation form is rendered."""
    fake_form = DummyForm()
    monkeypatch.setattr(role_ui, "RoleForm", lambda: fake_form)

    rendered = {}

    def fake_render_template(template, **context):
        rendered["template"] = template
        rendered["context"] = context
        return "rendered"

    monkeypatch.setattr(role_ui, "render_template", fake_render_template)

    response = test_client.get("/roles/new")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert rendered["template"] == "create-role.html"
    assert rendered["context"]["form"] is fake_form


def test_ui_create_post_success_redirects(monkeypatch, test_client):
    """GIVEN a valid role creation submission WHEN posted THEN the user is redirected to the role detail page."""
    fake_role = SimpleNamespace(id="1", name="Role Name")
    fake_form = DummyForm(submit=True, name="Role Name", grade="Grade 1")
    monkeypatch.setattr(role_ui, "RoleForm", lambda: fake_form)
    monkeypatch.setattr(role_ui, "create_role", lambda name, grade: fake_role)

    response = test_client.post("/roles/new", data={})

    assert response.status_code == 302
    assert "/roles/" in response.headers["Location"]


def test_ui_create_post_invalid_form_renders_form(monkeypatch, test_client):
    """GIVEN a create role submission with validation errors WHEN posted THEN the page is re-rendered instead of redirecting."""
    fake_form = DummyForm(submit=False, name="", grade="")
    monkeypatch.setattr(role_ui, "RoleForm", lambda: fake_form)

    rendered = {}

    def fake_render_template(template, **context):
        rendered["template"] = template
        rendered["context"] = context
        return "rendered"

    monkeypatch.setattr(role_ui, "render_template", fake_render_template)

    response = test_client.post("/roles/new", data={})

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert rendered["template"] == "create-role.html"
    assert rendered["context"]["form"] is fake_form


def test_ui_create_post_duplicate_shows_error(monkeypatch, test_client):
    """GIVEN a duplicate role name WHEN create_role fails with IntegrityError THEN the duplicate error is added to the form."""
    fake_form = DummyForm(submit=True, name="Role Name", grade="Grade 1")
    monkeypatch.setattr(role_ui, "RoleForm", lambda: fake_form)
    monkeypatch.setattr(
        role_ui,
        "create_role",
        lambda name, grade: (_ for _ in ()).throw(IntegrityError("duplicate", params=None, orig=None)),
    )

    rendered = {}

    def fake_render_template(template, **context):
        rendered["template"] = template
        rendered["context"] = context
        return "rendered"

    monkeypatch.setattr(role_ui, "render_template", fake_render_template)

    response = test_client.post("/roles/new", data={})

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert fake_form.name.errors == ["A role with this name already exists."]


def test_ui_edit_get_populates_form(monkeypatch, test_client):
    """GIVEN an existing role WHEN the edit page is viewed THEN the form is populated with current values."""
    fake_role = SimpleNamespace(name="Old name", grade="Grade 1")
    fake_form = DummyForm()
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "RoleForm", lambda: fake_form)

    rendered = {}

    def fake_render_template(template, **context):
        rendered["template"] = template
        rendered["context"] = context
        return "rendered"

    monkeypatch.setattr(role_ui, "render_template", fake_render_template)

    response = test_client.get("/roles/00000000-0000-0000-0000-000000000000/edit")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert fake_form.name.data == "Old name"
    assert fake_form.grade.data == "Grade 1"


def test_ui_edit_post_success_redirects(monkeypatch, test_client):
    """GIVEN a valid role edit WHEN posted THEN the user is redirected back to the role list."""
    fake_role = SimpleNamespace(id="1", name="Old name", grade="Grade 1")
    fake_form = DummyForm(submit=True, name="New name", grade="Grade 1")
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "RoleForm", lambda: fake_form)
    monkeypatch.setattr(role_ui, "update_role", lambda id, name, grade=None: fake_role)

    response = test_client.post("/roles/00000000-0000-0000-0000-000000000000/edit", data={})

    assert response.status_code == 302
    assert "/roles/" in response.headers["Location"]


def test_ui_edit_post_duplicate_shows_error(monkeypatch, test_client):
    """GIVEN a duplicate role name WHEN edit_role fails with IntegrityError THEN the duplicate error is attached to the form."""
    fake_role = SimpleNamespace(id="1", name="Old name", grade="Grade 1")
    fake_form = DummyForm(submit=True, name="New name", grade="Grade 1")
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "RoleForm", lambda: fake_form)
    monkeypatch.setattr(
        role_ui,
        "update_role",
        lambda id, name, grade=None: (_ for _ in ()).throw(IntegrityError("duplicate", params=None, orig=None)),
    )

    rendered = {}

    def fake_render_template(template, **context):
        rendered["template"] = template
        rendered["context"] = context
        return "rendered"

    monkeypatch.setattr(role_ui, "render_template", fake_render_template)

    response = test_client.post("/roles/00000000-0000-0000-0000-000000000000/edit", data={})

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert fake_form.name.errors == ["A role with this name already exists."]


def test_ui_archive_get_renders_form(monkeypatch, test_client):
    """GIVEN the archive confirmation page WHEN requested THEN the archive form is rendered."""
    fake_role = SimpleNamespace(name="Archivable role")
    fake_form = DummyForm()
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "ArchiveRoleForm", lambda: fake_form)

    rendered = {}

    def fake_render_template(template, **context):
        rendered["template"] = template
        rendered["context"] = context
        return "rendered"

    monkeypatch.setattr(role_ui, "render_template", fake_render_template)

    response = test_client.get("/roles/00000000-0000-0000-0000-000000000000/archive")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert rendered["template"] == "archive-role.html"


def test_ui_archive_post_success_redirects(monkeypatch, test_client):
    """GIVEN a confirmed archive action WHEN posted THEN the user is redirected to the role list."""
    fake_role = SimpleNamespace(id="1", name="Archivable role")
    fake_form = DummyForm(submit=True, confirm=True)
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "ArchiveRoleForm", lambda: fake_form)
    monkeypatch.setattr(role_ui, "archive_role", lambda id: fake_role)

    response = test_client.post("/roles/00000000-0000-0000-0000-000000000000/archive", data={})

    assert response.status_code == 302
    assert "/roles/" in response.headers["Location"]


def test_ui_restore_post_success_redirects(monkeypatch, test_client):
    """GIVEN a restore confirmation WHEN posted THEN the user is redirected back to the role list."""
    fake_role = SimpleNamespace(id="1", name="Restorable role")
    fake_form = DummyForm(submit=True, confirm=True)
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "RestoreRoleForm", lambda: fake_form)
    monkeypatch.setattr(role_ui, "restore_role", lambda id: fake_role)

    response = test_client.post("/roles/00000000-0000-0000-0000-000000000000/restore", data={})

    assert response.status_code == 302
    assert "/roles/" in response.headers["Location"]


def test_ui_download_returns_csv(monkeypatch, test_client):
    """GIVEN the download endpoint WHEN requested THEN a CSV file is returned with the correct content type and headers."""
    fake_role = SimpleNamespace(
        id="1",
        name="Role One",
        grade="Grade 1",
        updated_at=SimpleNamespace(isoformat=lambda: "2024-01-01T00:00:00"),
        archived_at=None,
    )
    monkeypatch.setattr(role_ui, "get_roles", lambda: [fake_role])

    response = test_client.get("/roles/download")

    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == "attachment; filename=roles.csv"
    assert response.get_data()[:3] == b"\xef\xbb\xbf"
    assert b"ID,NAME,GRADE,UPDATED_AT,ARCHIVED_AT" in response.get_data()
