#!/bin/sh
python generate.py

docker compose exec mimisbrunnr psql \
  -U mimir \
  -d mimisbrunnr \
  -c "\
TRUNCATE TABLE roles, people CASCADE;

COPY roles (id, name, grade, updated_at, archived_at) \
FROM '/data/roles.csv' \
WITH (FORMAT csv, HEADER true);

COPY people (id, name, archived_at, updated_at, role_id, team_id, location) \
FROM '/data/people.csv' \
WITH (FORMAT csv, HEADER true);"
