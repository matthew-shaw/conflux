from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions import ArchivedEntityError
from app.role import service as role_service


class DummyQuery:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def order_by(self, value):
        self.calls.append(("order_by", value))
        return self

    def options(self, value):
        self.calls.append(("options", value))
        return self

    def where(self, value):
        self.calls.append(("where", value))
        return self


class DummyPagination:
    def __init__(self, items):
        self.items = items


class DummyColumn:
    def __eq__(self, value):
        return ("profession", value)


def make_role_stub() -> SimpleNamespace:
    return SimpleNamespace(
        name="name_col",
        grade="grade_col",
        people="people_relationship",
        updated_at=SimpleNamespace(desc=lambda: "updated_desc"),
        profession=DummyColumn(),
        archived_at=SimpleNamespace(
            is_=lambda value: "not_archived",
            is_not=lambda value: "archived",
        ),
    )


@pytest.mark.parametrize("include_people", [False, True])
def test_get_roles_builds_query(monkeypatch, include_people):
    """GIVEN archived role filters
    WHEN get_roles is called
    THEN the query includes the expected order and where clauses."""
    fake_query = DummyQuery()
    fake_db = SimpleNamespace(
        select=lambda model: fake_query,
        paginate=lambda *args, **kwargs: DummyPagination(["role1", "role2"]),
    )
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "Role", make_role_stub())
    monkeypatch.setattr(role_service, "selectinload", lambda value: "people_eager")

    roles = role_service.get_roles(sort="updated", status="archived", include_people=include_people)

    assert roles.items == ["role1", "role2"]
    expected_options = [("options", "people_eager")] if include_people else []
    assert fake_query.calls == expected_options + [
        ("order_by", "updated_desc"),
        ("where", "archived"),
    ]


def test_get_roles_returns_all_when_status_all(monkeypatch):
    """GIVEN status=all WHEN get_roles is called THEN no archived filter is applied."""
    fake_query = DummyQuery()
    fake_db = SimpleNamespace(
        select=lambda model: fake_query,
        paginate=lambda *args, **kwargs: DummyPagination(["role1"]),
    )
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "Role", make_role_stub())
    monkeypatch.setattr(role_service, "selectinload", lambda value: "people_eager")

    roles = role_service.get_roles(sort="name", status="all")

    assert roles.items == ["role1"]
    assert fake_query.calls == [("order_by", "name_col")]


def test_get_roles_filters_by_profession(monkeypatch):
    """
    GIVEN a profession filter
    WHEN get_roles is called
    THEN an exact profession predicate is added.
    """
    fake_query = DummyQuery()
    fake_db = SimpleNamespace(
        select=lambda model: fake_query,
        paginate=lambda *args, **kwargs: DummyPagination([]),
    )
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "Role", make_role_stub())
    monkeypatch.setattr(role_service, "selectinload", lambda value: "people_eager")

    role_service.get_roles(status="all", profession="Engineering")

    assert fake_query.calls == [
        ("order_by", "name_col"),
        ("where", ("profession", "Engineering")),
    ]


def test_get_role_uses_session_execute(monkeypatch):
    """GIVEN a role ID WHEN get_role is called THEN the database session executes a select query."""
    sentinel = object()
    executed = {}

    class FakeSelect:
        def filter_by(self, id):
            executed["filtered_id"] = id
            return self

    def fake_execute(query):
        executed["query"] = query
        return SimpleNamespace(scalar_one=lambda: sentinel)

    fake_db = SimpleNamespace(
        select=lambda model: FakeSelect(),
        session=SimpleNamespace(execute=fake_execute),
    )
    monkeypatch.setattr(role_service, "db", fake_db)

    assert role_service.get_role(UUID("00000000-0000-0000-0000-000000000000")) is sentinel
    assert isinstance(executed["query"], FakeSelect)


def test_create_role_commits_and_returns_role(monkeypatch):
    """GIVEN valid role data WHEN create_role is called THEN the role is added and committed."""
    created = []

    class FakeRole:
        def __init__(self, name: str, grade: str, profession: str | None = None) -> None:
            self.name = name
            self.grade = grade
            self.profession = profession

    def fake_add(role):
        created.append(role)

    fake_session = SimpleNamespace(add=fake_add, commit=lambda: None, rollback=lambda: None)
    fake_db = SimpleNamespace(session=fake_session)
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "Role", FakeRole)

    role = role_service.create_role("Manager", "Grade 5")

    assert isinstance(role, FakeRole)
    assert role.name == "Manager"
    assert role.grade == "Grade 5"
    assert role.profession is None
    assert created == [role]


def test_create_role_normalises_blank_profession(monkeypatch):
    """
    GIVEN blank profession input
    WHEN a role is created
    THEN no profession is persisted."""

    class FakeRole:
        def __init__(self, name: str, grade: str, profession: str | None = None) -> None:
            self.name = name
            self.grade = grade
            self.profession = profession

    fake_session = SimpleNamespace(add=lambda _: None, commit=lambda: None, rollback=lambda: None)
    monkeypatch.setattr(role_service, "db", SimpleNamespace(session=fake_session))
    monkeypatch.setattr(role_service, "Role", FakeRole)

    role = role_service.create_role("Manager", "Grade 5", "   ")

    assert role.profession is None


def test_create_role_rolls_back_on_integrity_error(monkeypatch):
    """GIVEN a duplicate role name WHEN create_role fails THEN the session rollback is invoked."""

    class FakeRole:
        def __init__(self, name: str, grade: str, profession: str | None = None) -> None:
            self.name = name
            self.grade = grade
            self.profession = profession

    rollback_called = False

    def fake_commit():
        raise IntegrityError("duplicate", params=None, orig=None)

    def fake_rollback():
        nonlocal rollback_called
        rollback_called = True

    fake_session = SimpleNamespace(add=lambda _: None, commit=fake_commit, rollback=fake_rollback)
    fake_db = SimpleNamespace(session=fake_session)
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "Role", FakeRole)

    with pytest.raises(IntegrityError):
        role_service.create_role("Manager", "Grade 5")

    assert rollback_called is True


def test_update_role_commits_updated_name(monkeypatch):
    """
    GIVEN an existing role
    WHEN update_role is called
    THEN the name is updated and the transaction is committed.
    """
    updated_role = SimpleNamespace(name="Old name", grade="Grade 1", profession=None, archived_at=None)
    commit_called = False

    def nonlocal_set_true():
        nonlocal commit_called
        commit_called = True

    fake_db = SimpleNamespace(session=SimpleNamespace(commit=nonlocal_set_true, rollback=lambda: None))
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "get_role", lambda id: updated_role)

    role_service.update_role(UUID("00000000-0000-0000-0000-000000000000"), "New name", "Grade 1")

    assert updated_role.name == "New name"
    assert commit_called is True


def test_update_role_changes_and_clears_profession(monkeypatch):
    """
    GIVEN an existing role
    WHEN its profession is updated or cleared
    THEN the value is persisted."""
    updated_role = SimpleNamespace(name="Old name", grade="Grade 1", profession="Engineering", archived_at=None)
    monkeypatch.setattr(
        role_service,
        "db",
        SimpleNamespace(session=SimpleNamespace(commit=lambda: None, rollback=lambda: None)),
    )
    monkeypatch.setattr(role_service, "get_role", lambda id: updated_role)

    role_service.update_role(UUID("00000000-0000-0000-0000-000000000000"), "New name", "Grade 1", "Data")
    assert updated_role.profession == "Data"

    role_service.update_role(UUID("00000000-0000-0000-0000-000000000000"), "New name", "Grade 1", "")
    assert updated_role.profession is None


def test_update_role_rejects_archived_role(monkeypatch):
    """
    GIVEN an archived role
    WHEN its profession is changed
    THEN the update is rejected.
    """
    updated_role = SimpleNamespace(
        name="Old name",
        grade="Grade 1",
        profession="Engineering",
        archived_at="archived",
    )
    commit_called = False

    def commit() -> None:
        nonlocal commit_called
        commit_called = True

    monkeypatch.setattr(role_service, "db", SimpleNamespace(session=SimpleNamespace(commit=commit)))
    monkeypatch.setattr(role_service, "get_role", lambda id: updated_role)

    with pytest.raises(ArchivedEntityError):
        role_service.update_role(UUID("00000000-0000-0000-0000-000000000000"), "New name", "Grade 1", "Data")

    assert updated_role.profession == "Engineering"
    assert commit_called is False


def test_update_role_rolls_back_on_integrity_error(monkeypatch):
    """
    GIVEN an IntegrityError during update_role
    WHEN the service saves changes
    THEN rollback is called."""
    updated_role = SimpleNamespace(name="Old name", grade="Grade 1", profession=None, archived_at=None)
    rollback_called = False

    def fake_commit():
        raise IntegrityError("duplicate", params=None, orig=None)

    def fake_rollback():
        nonlocal rollback_called
        rollback_called = True

    fake_db = SimpleNamespace(session=SimpleNamespace(commit=fake_commit, rollback=fake_rollback))
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "get_role", lambda id: updated_role)

    with pytest.raises(IntegrityError):
        role_service.update_role(UUID("00000000-0000-0000-0000-000000000000"), "New name", "Grade 1")

    assert rollback_called is True
    assert updated_role.name == "New name"


def test_archive_role_sets_archived_at_and_commits(monkeypatch):
    """GIVEN an active role WHEN archive_role is called THEN archived_at is set and the session commits."""
    fake_role = SimpleNamespace(archived_at=None)
    commit_called = False

    def fake_commit():
        nonlocal commit_called
        commit_called = True

    fake_db = SimpleNamespace(session=SimpleNamespace(commit=fake_commit, rollback=lambda: None))
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "get_role", lambda id: fake_role)

    role_service.archive_role(UUID("00000000-0000-0000-0000-000000000000"))

    assert fake_role.archived_at is not None
    assert commit_called is True


def test_restore_role_clears_archived_at_and_commits(monkeypatch):
    """GIVEN an archived role WHEN restore_role is called THEN archived_at is cleared and the session commits."""
    fake_role = SimpleNamespace(archived_at="2024-01-01T00:00:00Z")
    commit_called = False

    def fake_commit():
        nonlocal commit_called
        commit_called = True

    fake_db = SimpleNamespace(session=SimpleNamespace(commit=fake_commit, rollback=lambda: None))
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "get_role", lambda id: fake_role)

    role_service.restore_role(UUID("00000000-0000-0000-0000-000000000000"))

    assert fake_role.archived_at is None
    assert commit_called is True
