import csv
import uuid

from faker import Faker

OUTPUT_FILE = "people.csv"

locales = ["en_GB", "fr_FR", "es_ES", "de_DE", "it_IT"]
names_per_gender = 10

faker_instances = {}
for loc in locales:
    faker_instances[(loc, "male")] = Faker(loc)
    faker_instances[(loc, "female")] = Faker(loc)

Faker.seed(0)

rows = []
for loc in locales:
    for gender in ["male", "female"]:
        faker = faker_instances[(loc, gender)]
        for _ in range(names_per_gender):
            if gender == "male":
                first = faker.first_name_male()
            else:
                first = faker.first_name_female()
            last = faker.last_name()

            # Generate a timezone aware datetime within last 6 months
            updated_at = faker.past_datetime(start_date="-182d", tzinfo=None)

            row = {
                "id": str(uuid.uuid4()),
                "name": f"{first} {last}",
                "archived_at": None,
                "updated_at": updated_at.isoformat(),
                "role_id": None,
                "team_id": None,
            }
            rows.append(row)

with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "name", "archived_at", "updated_at", "role_id", "team_id"])
    writer.writeheader()
    for row in rows:
        if row["archived_at"] is None:
            row["archived_at"] = ""
        writer.writerow(row)

print(f"Generated {len(rows)} rows in {OUTPUT_FILE}")
