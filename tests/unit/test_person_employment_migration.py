from importlib import import_module

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_person_employment_migration_preserves_and_maps_existing_people() -> None:
    """GIVEN a populated database with the old employment column
    WHEN the migration is upgraded and downgraded
    THEN values, column names, and indexes remain consistent."""
    migration = import_module("migrations.versions.0f0c4d079798_rename_person_employment")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE people (id INTEGER PRIMARY KEY, employment_type VARCHAR NOT NULL)"))
        connection.execute(text("CREATE INDEX ix_people_employment_type ON people (employment_type)"))
        connection.execute(text("INSERT INTO people (id, employment_type) VALUES (1, 'permanent'), (2, 'contractor')"))

        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        assert connection.execute(text("SELECT employment FROM people ORDER BY id")).scalars().all() == [
            "employee",
            "contractor",
        ]
        assert {column["name"] for column in inspect(connection).get_columns("people")} == {"id", "employment"}
        assert [index["name"] for index in inspect(connection).get_indexes("people")] == ["ix_people_employment"]

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()

        assert connection.execute(text("SELECT employment_type FROM people ORDER BY id")).scalars().all() == [
            "permanent",
            "contractor",
        ]
        assert {column["name"] for column in inspect(connection).get_columns("people")} == {
            "id",
            "employment_type",
        }
        assert [index["name"] for index in inspect(connection).get_indexes("people")] == ["ix_people_employment_type"]
    engine.dispose()
