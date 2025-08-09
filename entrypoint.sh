#!/bin/sh
set -e

# Run DB migrations
flask db upgrade

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:5000 -w 4 --access-logfile - mimir:app
