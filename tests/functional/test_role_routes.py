from types import SimpleNamespace

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Person, Role
from app.role import api as role_api
from app.role import ui as role_ui


def test_api_list_roles_uses_service_layer(monkeypatch, test_client):
    """GIVEN the role API list endpoint
    WHEN the list route is called
    THEN the service layer provides the returned role payload."""
    fake_roles = [SimpleNamespace(to_dict=lambda: {"id": "1"})]
    requested = {}

    def fake_get_roles(**kwargs):
        requested.update(kwargs)
        return fake_roles

    monkeypatch.setattr(
        role_api,
        "get_roles",
        fake_get_roles,
    )

    response = test_client.get("/api/v1/roles/?sort=grade&status=all&profession=Engineering")

    assert response.status_code == 200
    assert response.get_json() == [{"id": "1"}]
    assert requested["profession"] == "Engineering"


def test_api_list_roles_does_not_load_people(app, test_client):
    """GIVEN a role with many people WHEN one role is requested THEN no people are loaded or returned."""
    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        db.session.add(role)
        db.session.flush()
        db.session.add_all(
            [
                Person(
                    name=f"Person {index}",
                    email_address=f"person{index}@example.com",
                    location="London",
                    employment_type="permanent",
                    role_id=role.id,
                )
                for index in range(100)
            ]
        )
        db.session.commit()

    loaded_people = []

    def record_load(person, context):
        loaded_people.append(person)

    event.listen(Person, "load", record_load)
    try:
        response = test_client.get("/api/v1/roles/?per_page=1")
    finally:
        event.remove(Person, "load", record_load)

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert "people" not in response.get_json()[0]
    assert loaded_people == []


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
        profession=SimpleNamespace(data="Engineering"),
        per_page=SimpleNamespace(data=25),
        validate_on_submit=lambda: False,
    )
    fake_roles = SimpleNamespace(
        items=["role1"],
        page=1,
        per_page=25,
        total=1,
        pages=1,
    )
    monkeypatch.setattr(
        role_ui,
        "RoleSortFilterForm",
        lambda *args, **kwargs: fake_form,
    )
    requested = {}

    def fake_get_roles(**kwargs):
        requested.update(kwargs)
        return fake_roles

    monkeypatch.setattr(
        role_ui,
        "get_roles",
        fake_get_roles,
    )

    rendered = {}

    def fake_render_template(template, **context):
        rendered["template"] = template
        rendered["context"] = context
        return "rendered"

    monkeypatch.setattr(role_ui, "render_template", fake_render_template)

    response = test_client.get("/roles/?sort=grade&status=active&profession=Engineering")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert rendered["template"] == "list-roles.html"
    assert rendered["context"]["roles"].items == ["role1"]
    assert rendered["context"]["form"] is fake_form
    assert requested["profession"] == "Engineering"
    assert requested["include_people"] is True


def test_role_profession_filter_combines_status_and_pagination(app, test_client):
    """
    GIVEN active, archived, assigned and unassigned roles
    WHEN the Roles page and collection API are filtered by profession
    THEN exact matches are paginated, links retain the filter, and unmatched values return no roles.
    """
    app.config["PROFESSIONS"] = ["Engineering", "Product"]
    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        db.session.add_all(
            [
                Role(name="Engineering Active", grade="Grade 1", profession="Engineering"),
                Role(
                    name="Engineering Archived",
                    grade="Grade 2",
                    profession="Engineering",
                ),
                Role(name="Unassigned Active", grade="Grade 3"),
                Role(name="Product Active", grade="Grade 4", profession="Product"),
            ]
        )
        db.session.commit()
        archived = db.session.execute(db.select(Role).where(Role.name == "Engineering Archived")).scalar_one()
        archived.archived_at = db.func.now()
        db.session.commit()

    response = test_client.get("/roles/?profession=Engineering&status=all&sort=name&per_page=1")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Showing 1 to 1 of 2 roles" in body
    assert "profession=Engineering" in body
    assert "Engineering Active" in body
    assert "Engineering Archived" not in body

    response = test_client.get("/api/v1/roles/?profession=Engineering&status=all&per_page=1")

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert response.get_json()[0]["profession"] == "Engineering"

    response = test_client.get("/api/v1/roles/?profession=Missing&status=all")

    assert response.status_code == 200
    assert response.get_json() == []

    response = test_client.get("/roles/?status=active&per_page=50")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Unassigned Active" in body
    assert "None" in body


class DummyForm:
    def __init__(self, submit=False, name="", grade="", profession="", confirm=False):
        self.name = SimpleNamespace(data=name)
        self.grade = SimpleNamespace(data=grade, choices=[])
        self.profession = SimpleNamespace(data=profession, choices=[])
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
    monkeypatch.setattr(role_ui, "create_role", lambda name, grade, profession=None: fake_role)

    response = test_client.post("/roles/new", data={})

    assert response.status_code == 302
    assert "/roles/" in response.headers["Location"]


def test_ui_create_post_invalid_form_renders_form(monkeypatch, test_client):
    """GIVEN a create role submission with validation errors
    WHEN posted
    THEN the page is re-rendered instead of redirecting."""
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
    """GIVEN a duplicate role name
    WHEN create_role fails with IntegrityError
    THEN the duplicate error is added to the form."""
    fake_form = DummyForm(submit=True, name="Role Name", grade="Grade 1")
    monkeypatch.setattr(role_ui, "RoleForm", lambda: fake_form)
    monkeypatch.setattr(
        role_ui,
        "create_role",
        lambda name, grade, profession=None: (_ for _ in ()).throw(IntegrityError("duplicate", params=None, orig=None)),
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
    fake_role = SimpleNamespace(name="Old name", grade="Grade 1", profession="Engineering")
    fake_form = DummyForm()
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "RoleForm", lambda *args, **kwargs: fake_form)

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
    assert fake_form.profession.data == "Engineering"


def test_ui_edit_post_success_redirects(monkeypatch, test_client):
    """GIVEN a valid role edit WHEN posted THEN the user is redirected back to the role list."""
    fake_role = SimpleNamespace(id="1", name="Old name", grade="Grade 1", profession=None)
    fake_form = DummyForm(submit=True, name="New name", grade="Grade 1")
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "RoleForm", lambda *args, **kwargs: fake_form)
    monkeypatch.setattr(role_ui, "update_role", lambda id, name, grade=None, profession=None: fake_role)

    response = test_client.post("/roles/00000000-0000-0000-0000-000000000000/edit", data={})

    assert response.status_code == 302
    assert "/roles/" in response.headers["Location"]


def test_ui_edit_post_duplicate_shows_error(monkeypatch, test_client):
    """GIVEN a duplicate role name
    WHEN edit_role fails with IntegrityError
    THEN the duplicate error is attached to the form."""
    fake_role = SimpleNamespace(id="1", name="Old name", grade="Grade 1", profession=None)
    fake_form = DummyForm(submit=True, name="New name", grade="Grade 1")
    monkeypatch.setattr(role_ui, "get_role", lambda id: fake_role)
    monkeypatch.setattr(role_ui, "RoleForm", lambda *args, **kwargs: fake_form)
    monkeypatch.setattr(
        role_ui,
        "update_role",
        lambda id, name, grade=None, profession=None: (_ for _ in ()).throw(
            IntegrityError("duplicate", params=None, orig=None)
        ),
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
    """GIVEN the download endpoint WHEN requested
    THEN a CSV file is returned with the correct content type and headers."""
    fake_role = SimpleNamespace(
        id="1",
        name="Role One",
        grade="Grade 1",
        profession="Engineering",
        updated_at=SimpleNamespace(isoformat=lambda: "2024-01-01T00:00:00"),
        archived_at=None,
    )
    monkeypatch.setattr(
        role_ui,
        "download_roles",
        lambda: [fake_role],
    )

    response = test_client.get("/roles/download")

    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == "attachment; filename=roles.csv"
    assert response.get_data()[:3] == b"\xef\xbb\xbf"
    assert b"ID,NAME,GRADE,PROFESSION,UPDATED_AT,ARCHIVED_AT" in response.get_data()
    assert b"1,Role One,Grade 1,Engineering,2024-01-01T00:00:00," in response.get_data()


def test_api_view_includes_only_active_people(app, test_client):
    """GIVEN a role with active and archived people
    WHEN the role API detail endpoint is called
    THEN the returned JSON includes only active people."""
    from datetime import datetime, timezone

    from app import db
    from app.models import Person, Role

    with app.app_context():
        role = Role(name="API Role", grade="Senior")
        db.session.add(role)
        db.session.commit()

        p_active = Person(
            name="Active Person",
            email_address="active@example.com",
            location="London",
            employment_type="permanent",
            role_id=role.id,
        )
        p_archived = Person(
            name="Archived Person",
            email_address="archived@example.com",
            location="London",
            employment_type="permanent",
            role_id=role.id,
        )
        p_archived.archived_at = datetime.now(timezone.utc)
        db.session.add_all([p_active, p_archived])
        db.session.commit()

        assert len(role.people) == 2
        assert len(role.active_people) == 1

    # Request the API detail with people included
    response = test_client.get(f"/api/v1/roles/{role.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert "people" in data
    assert isinstance(data["people"], list)
    # Only the active person should be included
    assert any(p.get("name") == "Active Person" for p in data["people"])
    assert not any(p.get("name") == "Archived Person" for p in data["people"])
