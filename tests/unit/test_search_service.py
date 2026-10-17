import pytest
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.search.service import search_entries


def test_search_rolls_back_and_reraises_database_errors(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    GIVEN a database error occurs during search
    WHEN search entries are requested
    THEN the session is rolled back and the error is propagated.
    """
    with app.app_context():
        rollback_called = False

        def raise_database_error(statement: object) -> None:
            raise SQLAlchemyError("database unavailable")

        def record_rollback() -> None:
            nonlocal rollback_called
            rollback_called = True

        monkeypatch.setattr(db.session, "execute", raise_database_error)
        monkeypatch.setattr(db.session, "rollback", record_rollback)

        with pytest.raises(SQLAlchemyError, match="database unavailable"):
            search_entries("Platform")

        assert rollback_called
