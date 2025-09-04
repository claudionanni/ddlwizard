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
                    # Get tables (excluding views) with DDL
                    cursor.execute(f"SHOW FULL TABLES FROM `{self.config.schema}` WHERE Table_type = 'BASE TABLE'")
                    tables = cursor.fetchall()
                    for table in tables:
                        table_name = list(table.values())[0]
                        try:
                            ddl = self.get_table_ddl(table_name)
                            objects['tables'].append({'name': table_name, 'ddl': ddl})
                        except Exception as e:
                            print(f"Warning: Failed to get DDL for table {table_name}: {e}")
                            objects['tables'].append({'name': table_name, 'ddl': ''})
                    
                    # Get views with DDL
                    cursor.execute(f"SHOW FULL TABLES FROM `{self.config.schema}` WHERE Table_type = 'VIEW'")
                    views = cursor.fetchall()
                    for view in views:
                        view_name = list(view.values())[0]
                        try:
                            ddl = self.get_view_ddl(view_name)
                            objects['views'].append({'name': view_name, 'ddl': ddl})
                        except Exception as e:
                            print(f"Warning: Failed to get DDL for view {view_name}: {e}")
                            objects['views'].append({'name': view_name, 'ddl': ''})
                    
                    # Get sequences (MariaDB 10.3+) with DDL
                    try:
                        cursor.execute(f"SHOW FULL TABLES FROM `{self.config.schema}` WHERE Table_type = 'SEQUENCE'")
                        sequences = cursor.fetchall()
                        for seq in sequences:
                            seq_name = list(seq.values())[0]
                            try:
                                ddl = self.get_sequence_ddl(seq_name)
                                objects['sequences'].append({'name': seq_name, 'ddl': ddl})
                            except Exception as e:
                                print(f"Warning: Failed to get DDL for sequence {seq_name}: {e}")
                                objects['sequences'].append({'name': seq_name, 'ddl': ''})
                    except Exception:
                        # Sequences not supported in this MariaDB version
                        objects['sequences'] = []
                    
                    # Get procedures with DDL
                    cursor.execute(f"SHOW PROCEDURE STATUS WHERE Db = '{self.config.schema}'")
                    procedures = cursor.fetchall()
                    for proc in procedures:
                        proc_name = proc['Name']
                        try:
                            ddl = self.get_procedure_ddl(proc_name)
                            objects['procedures'].append({'name': proc_name, 'ddl': ddl})
                        except Exception as e:
                            print(f"Warning: Failed to get DDL for procedure {proc_name}: {e}")
                            objects['procedures'].append({'name': proc_name, 'ddl': ''})
                    
                    # Get functions with DDL
                    cursor.execute(f"SHOW FUNCTION STATUS WHERE Db = '{self.config.schema}'")
                    functions = cursor.fetchall()
                    for func in functions:
                        func_name = func['Name']
                        try:
                            ddl = self.get_function_ddl(func_name)
                            objects['functions'].append({'name': func_name, 'ddl': ddl})
                        except Exception as e:
                            print(f"Warning: Failed to get DDL for function {func_name}: {e}")
                            objects['functions'].append({'name': func_name, 'ddl': ''})
                    
                    # Get triggers with DDL
                    cursor.execute(f"SHOW TRIGGERS FROM `{self.config.schema}`")
                    triggers = cursor.fetchall()
                    for trigger in triggers:
                        trigger_name = trigger['Trigger']
                        try:
                            ddl = self.get_trigger_ddl(trigger_name)
                            objects['triggers'].append({'name': trigger_name, 'ddl': ddl})
                        except Exception as e:
                            print(f"Warning: Failed to get DDL for trigger {trigger_name}: {e}")
                            objects['triggers'].append({'name': trigger_name, 'ddl': ''})
                    
                    # Get events with DDL
                    cursor.execute(f"SHOW EVENTS FROM `{self.config.schema}`")
                    events = cursor.fetchall()
                    for event in events:
                        event_name = event['Name']
                        try:
                            ddl = self.get_event_ddl(event_name)
                            objects['events'].append({'name': event_name, 'ddl': ddl})
                        except Exception as e:
                            print(f"Warning: Failed to get DDL for event {event_name}: {e}")
                            objects['events'].append({'name': event_name, 'ddl': ''})
                    
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
    
    def execute_sql_file(self, sql_file_path: str, dry_run: bool = False) -> dict:
        """
        Execute SQL statements from a file with proper DELIMITER handling.
        
        Args:
            sql_file_path: Path to the SQL file to execute
            dry_run: If True, validate SQL but don't execute
            
        Returns:
            dict: Execution results with statistics and any errors
        """
        results = {
            'success': False,
            'executed_statements': 0,
            'failed_statements': 0,
            'errors': [],
            'warnings': [],
            'execution_time': 0
        }
        
        try:
            import time
            start_time = time.time()
            
            # Read SQL file
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            if not sql_content.strip():
                results['warnings'].append("SQL file is empty")
                results['success'] = True
                return results
            
            # Parse SQL with proper DELIMITER handling
            statements = self._parse_sql_with_delimiters(sql_content)
            
            if dry_run:
                # Dry run - just validate syntax
                logger.info(f"Dry run mode: Found {len(statements)} SQL statements")
                results['success'] = True
                results['executed_statements'] = len(statements)
                results['warnings'].append(f"DRY RUN: Would execute {len(statements)} statements")
                return results
            
            # Execute statements
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    for i, statement in enumerate(statements, 1):
                        try:
                            # Skip empty statements
                            if not statement.strip():
                                continue
                                
                            logger.debug(f"Executing statement {i}: {statement[:100]}...")
                            cursor.execute(statement)
                            results['executed_statements'] += 1
                            
                        except Exception as e:
                            error_msg = f"Statement {i} failed: {str(e)}"
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                            results['failed_statements'] += 1
                            
                            # Continue with next statement even if one fails
                            continue
                    
                    # Commit all changes
                    conn.commit()
                    logger.info(f"Successfully executed {results['executed_statements']} statements")
            
            results['success'] = results['failed_statements'] == 0
            results['execution_time'] = time.time() - start_time
            
        except FileNotFoundError:
            error_msg = f"SQL file not found: {sql_file_path}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        except Exception as e:
            error_msg = f"Failed to execute SQL file: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def _parse_sql_with_delimiters(self, sql_content: str) -> list:
        """
        Parse SQL content handling DELIMITER statements properly.
        
        Args:
            sql_content: Raw SQL content
            
        Returns:
            list: List of executable SQL statements
        """
        statements = []
        lines = sql_content.split('\n')
        current_statement = []
        current_delimiter = ';'
        inside_stored_object = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
            
            # Handle DELIMITER commands (skip them, but update delimiter)
            if line.upper().startswith('DELIMITER'):
                # Extract the new delimiter
                parts = line.split()
                if len(parts) >= 2:
                    current_delimiter = parts[1]
                continue
            
            # Check if we're starting a stored procedure/function/trigger
            if current_delimiter == '$$':
                # Collect everything until we hit the delimiter
                current_statement.append(line)
                
                # Check if this line ends with the current delimiter
                if line.endswith(current_delimiter):
                    # Complete stored object
                    if current_statement:
                        # Remove the delimiter from the end and join
                        full_statement = '\n'.join(current_statement)
                        full_statement = full_statement.replace('$$', '').strip()
                        if full_statement:
                            statements.append(full_statement)
                        current_statement = []
                    
                    # Reset delimiter back to semicolon after stored object
                    current_delimiter = ';'
                continue
            
            # Regular statement handling with semicolon delimiter
            current_statement.append(line)
            
            # Check if statement is complete
            if line.endswith(current_delimiter):
                # Complete statement
                if current_statement:
                    full_statement = '\n'.join(current_statement)
                    # Remove the delimiter from the end
                    full_statement = full_statement.rstrip(current_delimiter).strip()
                    if full_statement:
                        statements.append(full_statement)
                    current_statement = []
        
        # Handle any remaining statement
        if current_statement:
            full_statement = '\n'.join(current_statement).strip()
            if full_statement:
                statements.append(full_statement)
        
        return statements
    
    def execute_sql_statement(self, sql_statement: str, dry_run: bool = False) -> dict:
        """
        Execute a single SQL statement.
        
        Args:
            sql_statement: SQL statement to execute
            dry_run: If True, validate SQL but don't execute
            
        Returns:
            dict: Execution results
        """
        results = {
            'success': False,
            'rows_affected': 0,
            'errors': [],
            'warnings': [],
            'execution_time': 0
        }
        
        try:
            import time
            start_time = time.time()
            
            if not sql_statement.strip():
                results['warnings'].append("Empty SQL statement")
                results['success'] = True
                return results
            
            if dry_run:
                # Dry run - just validate
                logger.info(f"Dry run mode: Would execute: {sql_statement[:100]}...")
                results['success'] = True
                results['warnings'].append("DRY RUN: Statement syntax appears valid")
                return results
            
            # Execute statement
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.debug(f"Executing: {sql_statement[:100]}...")
                    cursor.execute(sql_statement)
                    results['rows_affected'] = cursor.rowcount
                    conn.commit()
                    
            results['success'] = True
            results['execution_time'] = time.time() - start_time
            logger.info(f"Successfully executed statement, {results['rows_affected']} rows affected")
            
        except Exception as e:
            error_msg = f"Failed to execute SQL statement: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
