"""
Database management for DDL Wizard.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import pymysql
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str
    port: int
    user: str
    password: str
    schema: str
    
    def __post_init__(self):
        """Validate required fields."""
        if not all([self.host, self.user, self.schema]):
            raise ValueError("Host, user, and schema are required")


class DatabaseManager:
    """Database connection and query manager."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize with database configuration."""
        self.config = config
        self.connection = None
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def _get_connection(self):
        """Get database connection."""
        return pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.schema,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def get_all_objects_with_ddl(self) -> Dict[str, List[Dict]]:
        """Get all database objects with their DDL."""
        objects = {
            'tables': [],
            'views': [],
            'procedures': [],
            'functions': [],
            'triggers': [],
            'events': [],
            'sequences': []
        }
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get tables (excluding views)
                    cursor.execute(f"SHOW FULL TABLES FROM `{self.config.schema}` WHERE Table_type = 'BASE TABLE'")
                    tables = cursor.fetchall()
                    objects['tables'] = [{'name': list(table.values())[0]} for table in tables]
                    
                    # Get views
                    cursor.execute(f"SHOW FULL TABLES FROM `{self.config.schema}` WHERE Table_type = 'VIEW'")
                    views = cursor.fetchall()
                    objects['views'] = [{'name': list(view.values())[0]} for view in views]
                    
                    # Get sequences (MariaDB 10.3+)
                    try:
                        cursor.execute(f"SHOW FULL TABLES FROM `{self.config.schema}` WHERE Table_type = 'SEQUENCE'")
                        sequences = cursor.fetchall()
                        objects['sequences'] = [{'name': list(seq.values())[0]} for seq in sequences]
                    except Exception:
                        # Sequences not supported in this MariaDB version
                        objects['sequences'] = []
                    
                    # Get procedures
                    cursor.execute(f"SHOW PROCEDURE STATUS WHERE Db = '{self.config.schema}'")
                    procedures = cursor.fetchall()
                    objects['procedures'] = [{'name': proc['Name']} for proc in procedures]
                    
                    # Get functions
                    cursor.execute(f"SHOW FUNCTION STATUS WHERE Db = '{self.config.schema}'")
                    functions = cursor.fetchall()
                    objects['functions'] = [{'name': func['Name']} for func in functions]
                    
                    # Get triggers
                    cursor.execute(f"SHOW TRIGGERS FROM `{self.config.schema}`")
                    triggers = cursor.fetchall()
                    objects['triggers'] = [{'name': trigger['Trigger']} for trigger in triggers]
                    
                    # Get events
                    cursor.execute(f"SHOW EVENTS FROM `{self.config.schema}`")
                    events = cursor.fetchall()
                    objects['events'] = [{'name': event['Name']} for event in events]
                    
        except Exception as e:
            logger.error(f"Failed to get database objects: {e}")
            
        return objects
    
    def get_table_ddl(self, table_name: str) -> str:
        """Get DDL for a table."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE TABLE `{self.config.schema}`.`{table_name}`")
                    result = cursor.fetchone()
                    if result:
                        return list(result.values())[1]
        except Exception as e:
            logger.error(f"Failed to get table DDL for {table_name}: {e}")
        return ""
    
    def get_procedure_ddl(self, procedure_name: str) -> str:
        """Get DDL for a procedure."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE PROCEDURE `{self.config.schema}`.`{procedure_name}`")
                    result = cursor.fetchone()
                    if result:
                        return list(result.values())[2]  # Third column contains the DDL
        except Exception as e:
            logger.error(f"Failed to get procedure DDL for {procedure_name}: {e}")
        return ""
    
    def get_function_ddl(self, function_name: str) -> str:
        """Get DDL for a function."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE FUNCTION `{self.config.schema}`.`{function_name}`")
                    result = cursor.fetchone()
                    if result:
                        return list(result.values())[2]  # Third column contains the DDL
        except Exception as e:
            logger.error(f"Failed to get function DDL for {function_name}: {e}")
        return ""
    
    def get_trigger_ddl(self, trigger_name: str) -> str:
        """Get DDL for a trigger."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE TRIGGER `{self.config.schema}`.`{trigger_name}`")
                    result = cursor.fetchone()
                    if result:
                        return list(result.values())[2]  # Third column contains the DDL
        except Exception as e:
            logger.error(f"Failed to get trigger DDL for {trigger_name}: {e}")
        return ""
    
    def get_event_ddl(self, event_name: str) -> str:
        """Get DDL for an event."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE EVENT `{self.config.schema}`.`{event_name}`")
                    result = cursor.fetchone()
                    if result:
                        return list(result.values())[3]  # Fourth column contains the DDL
        except Exception as e:
            logger.error(f"Failed to get event DDL for {event_name}: {e}")
        return ""

    def get_view_ddl(self, view_name: str) -> str:
        """Get DDL for a view."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE VIEW `{self.config.schema}`.`{view_name}`")
                    result = cursor.fetchone()
                    if result:
                        return list(result.values())[1]  # Second column contains the DDL
        except Exception as e:
            logger.error(f"Failed to get view DDL for {view_name}: {e}")
        return ""

    def get_sequence_ddl(self, sequence_name: str) -> str:
        """Get DDL for a sequence (MariaDB 10.3+)."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE SEQUENCE `{self.config.schema}`.`{sequence_name}`")
                    result = cursor.fetchone()
                    if result:
                        return list(result.values())[1]  # Second column contains the DDL
        except Exception as e:
            logger.error(f"Failed to get sequence DDL for {sequence_name}: {e}")
        return ""
