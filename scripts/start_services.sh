#!/bin/bash

# Anonora - Service Startup Script

echo "Starting Anonora services..."

# Check if Redis is running
echo "Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis is not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
else
    echo "Redis is running"
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Please activate it first:"
    echo "   source venv/bin/activate"
    exit 1
fi

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A app.celery_app worker --loglevel=info --concurrency=2 --daemon

# Start Celery beat for scheduled tasks (optional)
echo "Starting Celery beat for scheduled tasks..."
celery -A app.celery_app beat --loglevel=info --daemon

# Start FastAPI application
echo " Starting FastAPI application..."
python main.py 