#!/usr/bin/env python3
"""
Test script to check Celery task queuing
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.celery_app import celery_app, process_document_task, test_simple_task
from app.core.config import settings

def test_celery_connection():
    """Test Celery connection and task queuing"""
    print("🔍 Testing Celery configuration...")
    print(f"📊 Broker URL: {settings.celery_broker_url}")
    print(f"💾 Result Backend: {settings.celery_result_backend}")
    
    try:
        # Test connection
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        print(f"👷 Active workers: {len(active_workers) if active_workers else 0}")
        
        # Test simple task queuing first
        print("📤 Queuing simple test task...")
        simple_task = test_simple_task.delay("Hello from test!")
        print(f"✅ Simple task queued with ID: {simple_task.id}")
        
        # Check simple task status
        simple_result = simple_task.get(timeout=10)
        print(f"📋 Simple task result: {simple_result}")
        
        # Test document processing task
        print("📤 Queuing document processing task...")
        task = process_document_task.delay("test_file.pdf", "test-doc-id")
        print(f"✅ Document task queued with ID: {task.id}")
        
        # Check task status
        result = task.get(timeout=30)
        print(f"📋 Document task result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_redis_connection():
    """Test Redis connection"""
    print("\n🔍 Testing Redis connection...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        
        # Check Celery queues
        queue_length = r.llen('celery')
        print(f"📊 Celery queue length: {queue_length}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Celery queue test...\n")
    
    redis_ok = test_redis_connection()
    celery_ok = test_celery_connection()
    
    if redis_ok and celery_ok:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed!") 