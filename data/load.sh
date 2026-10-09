#!/bin/sh
set -eu

printf '%s\n' "WARNING: This replaces all Conflux demo data in the local Compose database."
printf '%s' "Continue? [y/N] "
read -r answer
case "$answer" in
  y|Y|yes|YES) ;;
  *) printf '%s\n' "Import cancelled."; exit 1 ;;
esac

docker compose exec -T db sh -c \
  'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" --set ON_ERROR_STOP=1 --single-transaction --file /data/load.sql'
