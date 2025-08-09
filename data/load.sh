#!/bin/sh
docker compose exec mimisbrunnr psql \
  -U mimir \
  -d mimisbrunnr \
  -c "\
COPY roles (id, name, grade, updated_at, archived_at) \
FROM '/data/roles.csv' \
WITH (FORMAT csv, HEADER true);"
