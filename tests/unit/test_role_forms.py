from types import SimpleNamespace

import pytest

from app.role import ui as role_ui
from app.role.forms import RoleForm


def test_role_form_requires_profession(app):
    """
    GIVEN a role form
    WHEN its profession field is inspected
    THEN it requires a configured profession rather than offering an unassigned option.
    """
    with app.test_request_context("/"):
        form = RoleForm()

        assert form.profession.validators[0].message == "Select a profession"
        assert form.profession.choices == [("", "Select a profession")]


def test_edit_choices_retain_removed_profession(app):
    """
    GIVEN a role whose profession is no longer configured
    WHEN edit choices are populated
    THEN the saved profession remains selectable.
    """
    app.config["PROFESSIONS"] = ["Engineering"]
    form = SimpleNamespace(profession=SimpleNamespace(choices=[]))
    role = SimpleNamespace(profession="Legal")

    with app.app_context():
        role_ui._set_profession_choices(form, role)

    assert form.profession.choices == [
        ("", "Select a profession"),
        ("Engineering", "Engineering"),
        ("Legal", "Legal"),
    ]


@pytest.mark.parametrize("profession", ["Legal", "Unknown"])
def test_create_rejects_unconfigured_professions(app, profession):
    """
    GIVEN configured profession choices
    WHEN a submitted profession is not configured during creation
    THEN the field fails choice validation.
    """
    app.config["PROFESSIONS"] = ["Engineering"]

    with app.test_request_context("/", method="POST", data={"profession": profession}):
        form = RoleForm()
        form.profession.choices = [
            ("", "Select a profession"),
            ("Engineering", "Engineering"),
        ]

        assert not form.profession.validate(form)
        assert form.profession.data == profession


def test_role_form_rejects_blank_profession(app):
    """
    GIVEN a role form with configured professions
    WHEN no profession is selected
    THEN profession validation fails with a required-field error.
    """
    app.config["PROFESSIONS"] = ["Engineering"]

    with app.test_request_context("/", method="POST", data={"profession": ""}):
        form = RoleForm()
        role_ui._set_profession_choices(form)

        assert not form.profession.validate(form)
        assert form.profession.errors == ["Select a profession"]


def test_edit_allows_current_removed_profession(app):
    """
    GIVEN a role with a profession that is no longer configured
    WHEN the role form is validated with its current profession
    THEN the profession remains valid for editing.
    """
    app.config["PROFESSIONS"] = ["Engineering"]

    with app.test_request_context("/", method="POST", data={"profession": "Legal"}):
        form = RoleForm(role=SimpleNamespace(profession="Legal"))
        form.profession.choices = [
            ("", "Select a profession"),
            ("Engineering", "Engineering"),
            ("Legal", "Legal"),
        ]

        assert form.profession.validate(form)
