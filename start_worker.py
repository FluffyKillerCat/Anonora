#!/usr/bin/env python3
"""
Script to start the Celery worker for document processing
"""

import os
import sys
from celery import Celery
from app.core.config import settings

def start_worker():
    """Start the Celery worker"""
    print("🚀 Starting Celery worker for document processing...")
    print(f"📊 Broker URL: {settings.celery_broker_url}")
    print(f"💾 Result Backend: {settings.celery_result_backend}")
    
    # Create Celery app
    celery_app = Celery(
        "document_intelligence",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["app.celery_app"]
    )
    
    # Configure Celery
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )
    
    # Start the worker
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=2',  # Number of worker processes
        '--queues=default',  # Queue name
        '--hostname=worker1@%h'  # Worker hostname
    ])

if __name__ == "__main__":
    start_worker() 