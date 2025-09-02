"""
Test configuration for DDL Wizard
"""
import pytest
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def sample_config():
    """Sample configuration for tests"""
    return {
        'database': {
            'host': 'localhost',
            'user': 'test_user',
            'password': 'test_pass',
            'database': 'test_db'
        }
    }
