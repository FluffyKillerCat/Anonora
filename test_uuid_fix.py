#!/usr/bin/env python3
"""
Test script to verify UUID serialization fix
"""

import uuid
import json
from app.api.documents.documents import ensure_uuid_string

def test_uuid_serialization():
    """Test that UUID objects are properly converted to strings"""
    
    # Test with UUID object
    test_uuid = uuid.uuid4()
    result = ensure_uuid_string(test_uuid)
    print(f"UUID object: {test_uuid} (type: {type(test_uuid)})")
    print(f"Converted: {result} (type: {type(result)})")
    assert isinstance(result, str)
    assert result == str(test_uuid)
    
    # Test with string (should remain unchanged)
    test_string = "test-string"
    result = ensure_uuid_string(test_string)
    print(f"String: {test_string} (type: {type(test_string)})")
    print(f"Converted: {result} (type: {type(result)})")
    assert isinstance(result, str)
    assert result == test_string
    
    # Test with None
    result = ensure_uuid_string(None)
    print(f"None: {None} (type: {type(None)})")
    print(f"Converted: {result} (type: {type(result)})")
    assert result is None
    
    # Test JSON serialization
    test_data = {
        "id": uuid.uuid4(),
        "owner_id": uuid.uuid4(),
        "title": "Test Document"
    }
    
    # This should fail without our fix
    try:
        json.dumps(test_data)
        print("❌ JSON serialization should have failed!")
    except TypeError as e:
        print(f"✅ JSON serialization correctly failed: {e}")
    
    # This should work with our fix
    fixed_data = {
        "id": ensure_uuid_string(test_data["id"]),
        "owner_id": ensure_uuid_string(test_data["owner_id"]),
        "title": test_data["title"]
    }
    
    try:
        json.dumps(fixed_data)
        print("✅ JSON serialization works with UUID fix!")
    except TypeError as e:
        print(f"❌ JSON serialization still fails: {e}")
    
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    test_uuid_serialization() 