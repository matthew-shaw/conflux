#!/bin/sh

docker compose exec mimisbrunnr psql \
  -U mimir \
  -d mimisbrunnr \
  -c "\
TRUNCATE TABLE teams, roles, people CASCADE;

COPY teams (ID, NAME, UPDATED_AT, ARCHIVED_AT) \
FROM '/data/teams.csv' \
WITH (FORMAT csv, HEADER true);

COPY roles (ID, NAME, GRADE, UPDATED_AT, ARCHIVED_AT) \
FROM '/data/roles.csv' \
WITH (FORMAT csv, HEADER true);

COPY people (ID, NAME, ROLE_ID, TEAM_ID, LOCATION, MANAGER_ID, UPDATED_AT, ARCHIVED_AT) \
FROM '/data/people.csv' \
WITH (FORMAT csv, HEADER true);"
