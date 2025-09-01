"""
Database connection and management utilities for DDL Wizard.
"""

import pymysql
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Configuration for database connection."""
    host: str
    port: int
    user: str
    password: str
    schema: str
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not all([self.host, self.user, self.password, self.schema]):
            raise ValueError("All database connection parameters are required")


class DatabaseManager:
    """Manages MariaDB connections and DDL extraction."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.schema,
                charset='utf8mb4'
            )
            logger.debug(f"Connected to {self.config.host}:{self.config.port}/{self.config.schema}")
            yield conn
        except pymysql.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
                logger.debug("Database connection closed")
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_tables(self) -> List[Dict[str, str]]:
        """Get all tables in the schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_TYPE 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s 
                ORDER BY TABLE_NAME
            """, (self.config.schema,))
            
            tables = []
            for row in cursor.fetchall():
                tables.append({
                    'name': row[0],
                    'type': row[1]
                })
            return tables
    
    def get_table_ddl(self, table_name: str) -> str:
        """Get CREATE TABLE statement for a specific table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
            result = cursor.fetchone()
            if result:
                return result[1]
            return ""
    
    def get_functions(self) -> List[Dict[str, str]]:
        """Get all functions in the schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ROUTINE_NAME, ROUTINE_TYPE 
                FROM INFORMATION_SCHEMA.ROUTINES 
                WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'FUNCTION'
                ORDER BY ROUTINE_NAME
            """, (self.config.schema,))
            
            functions = []
            for row in cursor.fetchall():
                functions.append({
                    'name': row[0],
                    'type': row[1]
                })
            return functions
    
    def get_function_ddl(self, function_name: str) -> str:
        """Get CREATE FUNCTION statement for a specific function."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SHOW CREATE FUNCTION `{function_name}`")
            result = cursor.fetchone()
            if result:
                return result[2]  # Third column contains the CREATE statement
            return ""
    
    def get_procedures(self) -> List[Dict[str, str]]:
        """Get all stored procedures in the schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ROUTINE_NAME, ROUTINE_TYPE 
                FROM INFORMATION_SCHEMA.ROUTINES 
                WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'
                ORDER BY ROUTINE_NAME
            """, (self.config.schema,))
            
            procedures = []
            for row in cursor.fetchall():
                procedures.append({
                    'name': row[0],
                    'type': row[1]
                })
            return procedures
    
    def get_procedure_ddl(self, procedure_name: str) -> str:
        """Get CREATE PROCEDURE statement for a specific procedure."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SHOW CREATE PROCEDURE `{procedure_name}`")
            result = cursor.fetchone()
            if result:
                return result[2]  # Third column contains the CREATE statement
            return ""
    
    def get_triggers(self) -> List[Dict[str, str]]:
        """Get all triggers in the schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE 
                FROM INFORMATION_SCHEMA.TRIGGERS 
                WHERE TRIGGER_SCHEMA = %s
                ORDER BY TRIGGER_NAME
            """, (self.config.schema,))
            
            triggers = []
            for row in cursor.fetchall():
                triggers.append({
                    'name': row[0],
                    'event': row[1],
                    'table': row[2]
                })
            return triggers
    
    def get_trigger_ddl(self, trigger_name: str) -> str:
        """Get CREATE TRIGGER statement for a specific trigger."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SHOW CREATE TRIGGER `{trigger_name}`")
            result = cursor.fetchone()
            if result:
                return result[2]  # Third column contains the CREATE statement
            return ""
    
    def get_events(self) -> List[Dict[str, str]]:
        """Get all events in the schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT EVENT_NAME, STATUS, EVENT_TYPE 
                FROM INFORMATION_SCHEMA.EVENTS 
                WHERE EVENT_SCHEMA = %s
                ORDER BY EVENT_NAME
            """, (self.config.schema,))
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'name': row[0],
                    'status': row[1],
                    'type': row[2]
                })
            return events
    
    def get_event_ddl(self, event_name: str) -> str:
        """Get CREATE EVENT statement for a specific event."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SHOW CREATE EVENT `{event_name}`")
            result = cursor.fetchone()
            if result:
                return result[3]  # Fourth column contains the CREATE statement
            return ""
    
    def get_all_objects(self) -> Dict[str, List[Dict[str, str]]]:
        """Get all database objects organized by type."""
        return {
            'tables': self.get_tables(),
            'functions': self.get_functions(),
            'procedures': self.get_procedures(),
            'triggers': self.get_triggers(),
            'events': self.get_events()
        }
