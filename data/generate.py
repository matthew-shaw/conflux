"""Generate fictional CSV data for a local Conflux demonstration."""

import csv
import os
import random
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from faker import Faker

DATA_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DATA_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

TEAM_NAMES = (
    "Digital Platforms",
    "Data Engineering",
    "Identity and Access",
    "Customer Services",
    "Developer Experience",
    "Cloud Infrastructure",
    "Business Applications",
    "Cyber Security",
    "Digital Workplace",
    "Payments",
    "Integration Services",
    "Service Operations",
)
ROLE_GRADES = (
    ("Apprentice Developer", "EO"),
    ("Junior Developer", "HEO"),
    ("Developer", "SEO"),
    ("Senior Developer", "G7"),
    ("Lead Developer", "G7"),
    ("Principal Developer", "G7"),
    ("Associate Delivery Manager", "HEO"),
    ("Delivery Manager", "G7"),
    ("Senior Delivery Manager", "G7"),
    ("Head of Delivery Management", "G7"),
    ("Associate Test Engineer", "EO"),
    ("Test Engineer", "SEO"),
    ("Senior Test Engineer", "G7"),
    ("Lead Test Engineer", "G6"),
    ("Trainee Business Analyst", "EO"),
    ("Junior Business Analyst", "HEO"),
    ("Business Analyst", "SEO"),
    ("Senior Business Analyst", "G7"),
    ("Lead Business Analyst", "G7"),
    ("Head of Business Analysis", "G7"),
    ("Associate User Researcher", "EO"),
    ("Junior User Researcher", "HEO"),
    ("User Researcher", "SEO"),
    ("Senior User Researcher", "G7"),
    ("Lead User Researcher", "G7"),
    ("Head of User Research", "G7"),
)
SERVICES = (
    ("Account Management", "Manages customer accounts and profile information."),
    ("Access Gateway", "Provides secure access to internal digital services."),
    ("Analytics Platform", "Collects and presents operational reporting and insights."),
    ("Case Management", "Supports the creation, assignment and tracking of cases."),
    ("Cloud Hosting", "Provides cloud infrastructure for organisational services."),
    ("Content Publishing", "Publishes approved content across digital channels."),
    ("Customer Notifications", "Sends service updates and important notifications."),
    ("Data Exchange", "Moves information securely between organisational systems."),
    ("Document Store", "Stores and retrieves documents used by digital services."),
    ("Employee Directory", "Provides searchable organisational and contact details."),
    ("Identity Service", "Manages user identity and authentication."),
    ("Integration Hub", "Coordinates integrations between internal services."),
    ("Payment Processing", "Processes and reconciles digital payments."),
    ("Reporting Service", "Produces scheduled operational reports."),
    ("Search Platform", "Provides search across services and published information."),
    ("Service Desk", "Coordinates support requests and incident handling."),
    ("Team Workspace", "Provides collaboration tools for delivery teams."),
    ("User Registration", "Supports online registration and account creation."),
)
COMPONENT_NAMES = (
    "Account API",
    "Audit Service",
    "Authentication API",
    "Background Worker",
    "Content API",
    "Document Database",
    "Event Broker",
    "Identity Database",
    "Integration API",
    "Kubernetes Platform",
    "Metrics Dashboard",
    "Notification Worker",
    "Object Storage",
    "Payment API",
    "PostgreSQL Cluster",
    "Redis Cache",
    "Search Index",
    "Web Frontend",
)
LOCALES = ("en_GB", "fr_FR", "es_ES", "de_DE", "it_IT")
PEOPLE_COUNT = 200
EMPLOYMENT_TYPES = ("permanent", "contractor")


def configured_values(name: str) -> list[str]:
    """Return non-empty comma-separated configuration values."""
    values = [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]
    if not values:
        raise SystemExit(f"Set {name} in the project .env file before generating demo data.")
    return values


def timestamp() -> str:
    """Return a recent timezone-aware timestamp suitable for PostgreSQL."""
    value = datetime.now(UTC) - timedelta(days=random.randint(0, 182), seconds=random.randint(0, 86_399))
    return value.isoformat()


def write_csv(filename: str, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    """Write rows to a CSV file in the data directory."""
    with (DATA_DIR / filename).open(mode="w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_demo_data() -> dict[str, int]:
    """Generate linked teams, roles, people, services and components."""
    configured_grades = set(configured_values("GRADES"))
    locations = configured_values("LOCATIONS")
    required_grades = {grade for _, grade in ROLE_GRADES}
    missing_grades = sorted(required_grades - configured_grades)
    if missing_grades:
        raise SystemExit(f"Add these framework grades to GRADES in .env: {', '.join(missing_grades)}")
    fakers = {locale: Faker(locale) for locale in LOCALES}

    teams = [
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "archived_at": "",
            "updated_at": timestamp(),
        }
        for name in TEAM_NAMES
    ]
    roles = []
    for title, grade in ROLE_GRADES:
        roles.append(
            {
                "id": str(uuid.uuid4()),
                "name": title,
                "grade": grade,
                "updated_at": timestamp(),
                "archived_at": "",
            }
        )

    people: list[dict[str, str]] = []
    for _ in range(PEOPLE_COUNT):
        faker = random.choice(tuple(fakers.values()))
        name = faker.name()
        person_id = str(uuid.uuid4())
        email_name = re.sub(r"[^a-z0-9]+", ".", name.casefold()).strip(".") or "person"
        manager_id = random.choice(people)["id"] if people and random.random() < 0.8 else ""
        people.append(
            {
                "id": person_id,
                "name": name,
                "email_address": f"{email_name}.{person_id[:8]}@example.com",
                "location": random.choice(locations),
                "employment_type": random.choice(EMPLOYMENT_TYPES),
                "archived_at": "",
                "updated_at": timestamp(),
                "role_id": random.choice(roles)["id"],
                "team_id": random.choice(teams)["id"],
                "manager_id": manager_id,
            }
        )

    services = [
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "archived_at": "",
            "updated_at": timestamp(),
            "team_id": random.choice(teams)["id"] if random.random() < 0.9 else "",
        }
        for name, description in SERVICES
    ]
    components = [
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "archived_at": "",
            "updated_at": timestamp(),
        }
        for name in COMPONENT_NAMES
    ]
    service_components: list[dict[str, str]] = []
    for service, component in zip(services, components, strict=True):
        linked_components = {component["id"]}
        linked_components.update(item["id"] for item in random.sample(components, k=random.randint(1, 3)))
        service_components.extend(
            {"service_id": service["id"], "component_id": component_id} for component_id in linked_components
        )

    write_csv("teams.csv", ("id", "name", "archived_at", "updated_at"), teams)
    write_csv("roles.csv", ("id", "name", "grade", "updated_at", "archived_at"), roles)
    write_csv(
        "people.csv",
        (
            "id",
            "name",
            "email_address",
            "location",
            "employment_type",
            "archived_at",
            "updated_at",
            "role_id",
            "team_id",
            "manager_id",
        ),
        people,
    )
    write_csv(
        "services.csv",
        ("id", "name", "description", "archived_at", "updated_at", "team_id"),
        services,
    )
    write_csv("components.csv", ("id", "name", "archived_at", "updated_at"), components)
    write_csv("service_components.csv", ("service_id", "component_id"), service_components)

    return {
        "teams": len(teams),
        "roles": len(roles),
        "people": len(people),
        "services": len(services),
        "components": len(components),
        "service_components": len(service_components),
    }


if __name__ == "__main__":
    for table, count in generate_demo_data().items():
        print(f"Generated {count} {table} rows in {DATA_DIR}")
