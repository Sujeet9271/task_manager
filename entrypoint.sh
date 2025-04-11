#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define the project directory
PROJECT_DIR="/app"

# Perform database migrations
echo "Running makemigrations..."
# python3 $PROJECT_DIR/manage.py makemigrations
# python3 $PROJECT_DIR/manage.py migrate
python3 $PROJECT_DIR/manage.py crontab add

# Collect static files
echo "Collecting static files..."
python3 $PROJECT_DIR/manage.py collectstatic --no-input

service cron start
# Start Django development server
echo "Starting Django development server..."
# exec python3 $PROJECT_DIR/manage.py runserver 0.0.0.0:8000
exec daphne -b 0.0.0.0 -p 8000 task_manager.asgi:application
