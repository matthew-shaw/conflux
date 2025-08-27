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

team_ids = [
    "8bc3137e-ed74-4a10-bd38-c76534cacac1",
    "eb4746e9-a3b3-4d39-8a18-0f4e60753782",
    "d184bbe9-a3f9-4f6b-a029-7620249b760a",
    "58d8ebbc-1163-4f21-88cc-bbd683a5798d",
    "9436960c-b70d-4884-82d0-1e649ca5e34c",
    "32907451-9cfc-46e0-aebc-d6ebe73deac0",
    "a9d45861-8c5b-4964-9cef-c754159a815d",
    "1aa5cff3-195c-4483-bdfe-1db792d0bd2e",
    "b95bd40c-dfda-48d3-8b5a-5791e55d9133",
    "26608f84-4529-4c5f-bb4f-2aacdced303a",
    "83325cae-9fe6-4339-b673-25d82c29d3d8",
    "e8625bf0-2363-483a-aa59-dea0ff1b2b1a",
    "08183a46-5624-4502-9e3e-161c7a2cf727",
    "8194a6be-cb81-41fc-86da-682d1d957db2",
    "8ddf7ba5-310b-44e3-8cda-dd1788e613d9",
    "f15b021a-2d28-47a1-af93-64bca0723fe5",
    "693d8b5f-8945-4a0c-96a8-01d24499ebc1",
    "98a50f61-6d39-4616-aab6-eefdaac0066e",
    "cba521a7-eed7-4cf1-a5a0-4f782849e24f",
    "1f94ed1f-0a2b-4d79-8b50-b26bc504a0c9",
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
                "team_id": random.choice(team_ids),
                "location": random.choice(locations),
                "manager_id": None,  # placeholder
            }
            rows.append(row)

# Assign managers randomly (not self)
ids = [r["id"] for r in rows]
for row in rows:
    possible_managers = [i for i in ids if i != row["id"]]
    row["manager_id"] = random.choice(possible_managers)

# Write CSV
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
            "manager_id",
        ],
    )
    writer.writeheader()
    for row in rows:
        if row["archived_at"] is None:
            row["archived_at"] = ""
        writer.writerow(row)

print(f"Generated {len(rows)} rows in {OUTPUT_FILE}")
