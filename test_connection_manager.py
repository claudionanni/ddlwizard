#!/usr/bin/env python3
"""
Test Connection Manager Functionality
=====================================

Quick test to verify the connection manager works correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from connection_manager import ConnectionManager
from database import DatabaseConfig

def test_connection_manager():
    """Test the connection manager functionality."""
    print("🧪 Testing Connection Manager...")
    
    # Create test connection manager
    test_dir = "/tmp/ddlwizard_test"
    cm = ConnectionManager(test_dir)
    
    # Test saving a connection
    print("\n1. Testing save connection...")
    test_config = DatabaseConfig(
        host="test-host",
        port=3306,
        user="test-user",
        password="test-pass",
        schema="test-schema"
    )
    
    success = cm.save_connection("test-connection", test_config, "Test connection for unit testing")
    print(f"   Save result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    # Test listing connections
    print("\n2. Testing list connections...")
    connections = cm.list_connections()
    print(f"   Found {len(connections)} connections")
    for name, info in connections.items():
        print(f"   - {name}: {info['user']}@{info['host']}:{info['port']}/{info['schema']}")
        print(f"     Description: {info['description']}")
    
    # Test loading connection
    print("\n3. Testing load connection...")
    loaded_config = cm.load_connection("test-connection")
    if loaded_config:
        print(f"   ✅ Loaded: {loaded_config.user}@{loaded_config.host}:{loaded_config.port}/{loaded_config.schema}")
        print(f"   Password cleared: {'✅ YES' if not loaded_config.password else '❌ NO'}")
    else:
        print("   ❌ Failed to load connection")
    
    # Test updating connection
    print("\n4. Testing update connection...")
    updated_config = DatabaseConfig(
        host="updated-host",
        port=3307,
        user="updated-user",
        password="",
        schema="updated-schema"
    )
    
    success = cm.update_connection("test-connection", updated_config, "Updated test connection")
    print(f"   Update result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    # Test export
    print("\n5. Testing export connections...")
    export_file = "/tmp/test_connections_export.json"
    success = cm.export_connections(export_file)
    print(f"   Export result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    if success and os.path.exists(export_file):
        print(f"   Export file size: {os.path.getsize(export_file)} bytes")
    
    # Test delete connection
    print("\n6. Testing delete connection...")
    success = cm.delete_connection("test-connection")
    print(f"   Delete result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    # Verify deletion
    final_connections = cm.list_connections()
    print(f"   Remaining connections: {len(final_connections)}")
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    try:
        import shutil
        shutil.rmtree(test_dir)
        if os.path.exists(export_file):
            os.unlink(export_file)
        print("   ✅ Cleanup completed")
    except Exception as e:
        print(f"   ⚠️ Cleanup warning: {e}")
    
    print("\n🎉 Connection Manager test completed!")

if __name__ == "__main__":
    test_connection_manager()
