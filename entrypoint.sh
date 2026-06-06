#!/bin/sh
set -e

echo "Starting entrypoint..."

if [ -n "$POSTGRES_HOST" ]; then
    echo "Ensuring PostGIS extension exists..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
fi

echo "Running migrations..."
python manage.py migrate --noinput

# Видалення старих даних перед завантаженням (щоб уникнути помилок дублікатів)
echo "Cleaning existing data..."
python manage.py shell -c "from vehicles.models import Vehicle; Vehicle.objects.all().delete()" || true

echo "Loading database fixtures..."
python manage.py loaddata users.json vehicles.json driver_locations.json

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec "$@"