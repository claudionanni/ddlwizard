"""
Copyright (C) 2025 Claudio Nanni
This file is part of DDL Wizard.

DDL Wizard is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

DDL Wizard is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with DDL Wizard.  If not, see <https://www.gnu.org/licenses/>.
"""

#!/usr/bin/env python3
import pymysql

def test_connection(host, port, user, password, database=None):
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        with connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES")
            databases = [row[0] for row in cursor.fetchall()]
            print(f"✓ Connected to {host}:{port} as {user}")
            print(f"Available databases: {databases}")
        connection.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed to {host}:{port} as {user}: {e}")
        return False

if __name__ == "__main__":
    print("Testing database connections...")
    
    # Test source database
    print("\n--- Source Database ---")
    test_connection('127.0.0.1', 10622, 'sstuser', 'sstpass')
    
    # Test destination database
    print("\n--- Destination Database ---")
    test_connection('127.0.0.1', 20622, 'sstuser', 'sstpass')
