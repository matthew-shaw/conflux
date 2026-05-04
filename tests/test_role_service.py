from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from app.role import service as role_service


class DummyQuery:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def order_by(self, value):
        self.calls.append(("order_by", value))
        return self

    def where(self, value):
        self.calls.append(("where", value))
        return self


class DummyResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


def make_role_stub() -> SimpleNamespace:
    return SimpleNamespace(
        name="name_col",
        grade="grade_col",
        updated_at=SimpleNamespace(desc=lambda: "updated_desc"),
        archived_at=SimpleNamespace(
            is_=lambda value: "not_archived",
            is_not=lambda value: "archived",
        ),
    )


def test_get_roles_builds_query(monkeypatch):
    fake_query = DummyQuery()
    fake_db = SimpleNamespace(
        select=lambda model: fake_query,
        session=SimpleNamespace(execute=lambda query: DummyResult(["role1", "role2"])),
    )
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "Role", make_role_stub())

    roles = role_service.get_roles(sort="updated", status="archived")

    assert roles == ["role1", "role2"]
    assert fake_query.calls == [("order_by", "updated_desc"), ("where", "archived")]


def test_get_roles_returns_all_when_status_all(monkeypatch):
    fake_query = DummyQuery()
    fake_db = SimpleNamespace(
        select=lambda model: fake_query,
        session=SimpleNamespace(execute=lambda query: DummyResult(["role1"])),
    )
    monkeypatch.setattr(role_service, "db", fake_db)
    monkeypatch.setattr(role_service, "Role", make_role_stub())

    roles = role_service.get_roles(sort="name", status="all")

    assert roles == ["role1"]
    assert fake_query.calls == [("order_by", "name_col")]


def test_get_role_delegates_to_db_get_or_404(monkeypatch):
    sentinel = object()
    fake_db = SimpleNamespace(get_or_404=lambda model, id: sentinel)
    monkeypatch.setattr(role_service, "db", fake_db)

    assert role_service.get_role(UUID("00000000-0000-0000-0000-000000000000")) is sentinel


def test_create_role_commits_and_returns_role(monkeypatch):
    created = []

    class FakeRole:
        def __init__(self, name: str, grade: str) -> None:
            self.name = name
            self.grade = grade

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
    assert created == [role]


def test_create_role_rolls_back_on_integrity_error(monkeypatch):
    class FakeRole:
        def __init__(self, name: str, grade: str) -> None:
            self.name = name
            self.grade = grade

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
    updated_role = SimpleNamespace(name="Old name")
    commit_called = False

    def nonlocal_set_true():
        nonlocal commit_called
        commit_called = True

    fake_db = SimpleNamespace(
        get_or_404=lambda model, id: updated_role,
        session=SimpleNamespace(commit=nonlocal_set_true, rollback=lambda: None),
    )
    monkeypatch.setattr(role_service, "db", fake_db)

    role = role_service.update_role(UUID("00000000-0000-0000-0000-000000000000"), "New name")

    assert role is updated_role
    assert updated_role.name == "New name"
    assert commit_called is True


def test_update_role_rolls_back_on_integrity_error(monkeypatch):
    updated_role = SimpleNamespace(name="Old name")
    rollback_called = False

    def fake_commit():
        raise IntegrityError("duplicate", params=None, orig=None)

    def fake_rollback():
        nonlocal rollback_called
        rollback_called = True

    fake_db = SimpleNamespace(
        get_or_404=lambda model, id: updated_role,
        session=SimpleNamespace(commit=fake_commit, rollback=fake_rollback),
    )
    monkeypatch.setattr(role_service, "db", fake_db)

    with pytest.raises(IntegrityError):
        role_service.update_role(UUID("00000000-0000-0000-0000-000000000000"), "New name")

    assert rollback_called is True
    assert updated_role.name == "New name"


def test_archive_role_sets_archived_at_and_commits(monkeypatch):
    fake_role = SimpleNamespace(archived_at=None)
    commit_called = False

    def fake_commit():
        nonlocal commit_called
        commit_called = True

    fake_db = SimpleNamespace(
        get_or_404=lambda model, id: fake_role,
        session=SimpleNamespace(commit=fake_commit),
    )
    monkeypatch.setattr(role_service, "db", fake_db)

    role = role_service.archive_role(UUID("00000000-0000-0000-0000-000000000000"))

    assert role is fake_role
    assert role.archived_at is not None
    assert commit_called is True


def test_restore_role_clears_archived_at_and_commits(monkeypatch):
    fake_role = SimpleNamespace(archived_at="2024-01-01T00:00:00Z")
    commit_called = False

    def fake_commit():
        nonlocal commit_called
        commit_called = True

    fake_db = SimpleNamespace(
        get_or_404=lambda model, id: fake_role,
        session=SimpleNamespace(commit=fake_commit),
    )
    monkeypatch.setattr(role_service, "db", fake_db)

    role = role_service.restore_role(UUID("00000000-0000-0000-0000-000000000000"))

    assert role is fake_role
    assert role.archived_at is None
    assert commit_called is True
