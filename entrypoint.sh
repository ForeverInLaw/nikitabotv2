#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to wait for service availability
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1

    echo "Waiting for $service_name to be available at $host:$port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "$service_name is available!"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: $service_name not yet available, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "ERROR: $service_name is not available after $max_attempts attempts"
    exit 1
}

# Wait for database to be ready
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
    wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"
fi

# Wait for Redis to be ready
if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
    wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis"
fi

# Additional database connection test
echo "Testing database connection..."
python -c "
import asyncio
import sys
from app.db.database import engine
from sqlalchemy import text

async def test_connection():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT 1'))
            print('Database connection successful!')
            return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

if not asyncio.run(test_connection()):
    sys.exit(1)
" || {
    echo "ERROR: Database connection test failed"
    exit 1
}

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Database migrations completed successfully!"

# Verify critical directories exist
mkdir -p logs
mkdir -p app/localization/files

echo "Starting Telegram Bot application..."

# Execute the main command
exec "$@"
