import csv
import os
import random
import uuid

from dotenv import load_dotenv
from faker import Faker

# Load .env from project root directory (one level above this script)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

OUTPUT_FILE = "people.csv"

role_ids = [
    "0d759307-2d5e-4650-a06a-8ff7150851cb",
    "e3042a7a-908b-4c99-8241-aeca5dfe8605",
    "22f78d95-f7c3-4e43-8fbb-ddcc8cecfbbc",
    "cdf4dfc1-b602-4226-9c28-7a6c198b629e",
    "be73522e-21c5-41e0-af03-543147404e52",
    "aefa9d2e-340a-4186-9737-f0bb8dfea345",
]

locales = ["en_GB", "fr_FR", "es_ES", "de_DE", "it_IT"]
names_per_gender = 10

# Load locations from env variable, split by comma, strip spaces
locations_str = os.getenv("LOCATIONS", "")
locations = [loc.strip() for loc in locations_str.split(",") if loc.strip()]

faker_instances = {}
for loc in locales:
    faker_instances[(loc, "male")] = Faker(loc)
    faker_instances[(loc, "female")] = Faker(loc)

rows = []
for loc in locales:
    for gender in ["male", "female"]:
        faker = faker_instances[(loc, gender)]
        for _ in range(names_per_gender):
            first = faker.first_name_male() if gender == "male" else faker.first_name_female()
            last = faker.last_name()

            updated_at = faker.past_datetime(start_date="-182d", tzinfo=None)

            row = {
                "id": str(uuid.uuid4()),
                "name": f"{first} {last}",
                "archived_at": None,
                "updated_at": updated_at.isoformat(),
                "role_id": random.choice(role_ids),
                "team_id": None,
                "location": random.choice(locations),
            }
            rows.append(row)

with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "id",
            "name",
            "archived_at",
            "updated_at",
            "role_id",
            "team_id",
            "location",
        ],
    )
    writer.writeheader()
    for row in rows:
        if row["archived_at"] is None:
            row["archived_at"] = ""
        writer.writerow(row)

print(f"Generated {len(rows)} rows in {OUTPUT_FILE}")
