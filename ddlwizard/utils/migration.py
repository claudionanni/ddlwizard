"""
Migration history and tracking for DDL Wizard.
Tracks applied migrations, rollback scripts, and migration metadata.
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class MigrationRecord:
    """Represents a migration execution record."""
    id: Optional[int] = None
    migration_name: str = ""
    source_schema: str = ""
    destination_schema: str = ""
    executed_at: str = ""
    execution_time: float = 0.0
    status: str = "PENDING"  # PENDING, SUCCESS, FAILED, ROLLED_BACK
    operations_count: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    migration_file: str = ""
    rollback_file: str = ""
    safety_warnings: int = 0
    git_commit: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MigrationHistory:
    """Manages migration history and tracking."""
    
    def __init__(self, history_db_path: str = ".ddl_wizard_history.db"):
        self.db_path = Path(history_db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize the migration history database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create migrations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        migration_name TEXT NOT NULL,
                        source_schema TEXT NOT NULL,
                        destination_schema TEXT NOT NULL,
                        executed_at TEXT NOT NULL,
                        execution_time REAL DEFAULT 0.0,
                        status TEXT DEFAULT 'PENDING',
                        operations_count INTEGER DEFAULT 0,
                        successful_operations INTEGER DEFAULT 0,
                        failed_operations INTEGER DEFAULT 0,
                        migration_file TEXT,
                        rollback_file TEXT,
                        safety_warnings INTEGER DEFAULT 0,
                        git_commit TEXT,
                        notes TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create operation details table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS migration_operations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        migration_id INTEGER,
                        operation_order INTEGER,
                        operation_type TEXT,
                        table_name TEXT,
                        sql_statement TEXT,
                        status TEXT DEFAULT 'PENDING',
                        execution_time REAL DEFAULT 0.0,
                        error_message TEXT,
                        FOREIGN KEY (migration_id) REFERENCES migrations (id)
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_migrations_executed_at ON migrations (executed_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_migrations_status ON migrations (status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_operations_migration_id ON migration_operations (migration_id)")
                
                conn.commit()
                logger.debug(f"Migration history database initialized: {self.db_path}")
        
        except Exception as e:
            logger.error(f"Failed to initialize migration history database: {e}")
            raise
    
    def start_migration(self, migration_name: str, source_schema: str, destination_schema: str,
                       operations_count: int, migration_file: str, rollback_file: str,
                       safety_warnings: int = 0, git_commit: str = "") -> int:
        """Start tracking a new migration."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO migrations (
                        migration_name, source_schema, destination_schema, executed_at,
                        status, operations_count, migration_file, rollback_file,
                        safety_warnings, git_commit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    migration_name, source_schema, destination_schema, datetime.now().isoformat(),
                    'RUNNING', operations_count, migration_file, rollback_file,
                    safety_warnings, git_commit
                ))
                
                migration_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Started tracking migration {migration_id}: {migration_name}")
                return migration_id
        
        except Exception as e:
            logger.error(f"Failed to start migration tracking: {e}")
            raise
    
    def complete_migration(self, migration_id: int, status: str, execution_time: float,
                          successful_operations: int, failed_operations: int, notes: str = ""):
        """Complete migration tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE migrations 
                    SET status = ?, execution_time = ?, successful_operations = ?,
                        failed_operations = ?, notes = ?
                    WHERE id = ?
                """, (status, execution_time, successful_operations, failed_operations, notes, migration_id))
                
                conn.commit()
                logger.info(f"Completed migration tracking {migration_id}: {status}")
        
        except Exception as e:
            logger.error(f"Failed to complete migration tracking: {e}")
    
    def record_operation(self, migration_id: int, operation_order: int, operation_type: str,
                        table_name: str, sql_statement: str, status: str = "SUCCESS",
                        execution_time: float = 0.0, error_message: str = ""):
        """Record individual operation execution."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO migration_operations (
                        migration_id, operation_order, operation_type, table_name,
                        sql_statement, status, execution_time, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    migration_id, operation_order, operation_type, table_name,
                    sql_statement, status, execution_time, error_message
                ))
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to record operation: {e}")
    
    def get_migration_history(self, limit: int = 50) -> List[MigrationRecord]:
        """Get migration history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, migration_name, source_schema, destination_schema, executed_at,
                           execution_time, status, operations_count, successful_operations,
                           failed_operations, migration_file, rollback_file, safety_warnings,
                           git_commit, notes
                    FROM migrations 
                    ORDER BY executed_at DESC 
                    LIMIT ?
                """, (limit,))
                
                records = []
                for row in cursor.fetchall():
                    records.append(MigrationRecord(
                        id=row[0], migration_name=row[1], source_schema=row[2],
                        destination_schema=row[3], executed_at=row[4], execution_time=row[5],
                        status=row[6], operations_count=row[7], successful_operations=row[8],
                        failed_operations=row[9], migration_file=row[10], rollback_file=row[11],
                        safety_warnings=row[12], git_commit=row[13], notes=row[14]
                    ))
                
                return records
        
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    def get_migration_details(self, migration_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific migration."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get migration record
                cursor.execute("""
                    SELECT id, migration_name, source_schema, destination_schema, executed_at,
                           execution_time, status, operations_count, successful_operations,
                           failed_operations, migration_file, rollback_file, safety_warnings,
                           git_commit, notes
                    FROM migrations WHERE id = ?
                """, (migration_id,))
                
                migration_row = cursor.fetchone()
                if not migration_row:
                    return None
                
                migration = MigrationRecord(
                    id=migration_row[0], migration_name=migration_row[1], 
                    source_schema=migration_row[2], destination_schema=migration_row[3],
                    executed_at=migration_row[4], execution_time=migration_row[5],
                    status=migration_row[6], operations_count=migration_row[7],
                    successful_operations=migration_row[8], failed_operations=migration_row[9],
                    migration_file=migration_row[10], rollback_file=migration_row[11],
                    safety_warnings=migration_row[12], git_commit=migration_row[13],
                    notes=migration_row[14]
                )
                
                # Get operation details
                cursor.execute("""
                    SELECT operation_order, operation_type, table_name, sql_statement,
                           status, execution_time, error_message
                    FROM migration_operations 
                    WHERE migration_id = ? 
                    ORDER BY operation_order
                """, (migration_id,))
                
                operations = []
                for op_row in cursor.fetchall():
                    operations.append({
                        'order': op_row[0],
                        'type': op_row[1],
                        'table': op_row[2],
                        'sql': op_row[3],
                        'status': op_row[4],
                        'execution_time': op_row[5],
                        'error': op_row[6]
                    })
                
                return {
                    'migration': migration.to_dict(),
                    'operations': operations
                }
        
        except Exception as e:
            logger.error(f"Failed to get migration details: {e}")
            return None
    
    def mark_migration_rolled_back(self, migration_id: int, rollback_notes: str = ""):
        """Mark a migration as rolled back."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE migrations 
                    SET status = 'ROLLED_BACK', notes = ?
                    WHERE id = ?
                """, (rollback_notes, migration_id))
                
                conn.commit()
                logger.info(f"Migration {migration_id} marked as rolled back")
        
        except Exception as e:
            logger.error(f"Failed to mark migration as rolled back: {e}")
    
    def export_history(self, output_file: str, format: str = "json"):
        """Export migration history to file."""
        try:
            history = self.get_migration_history(limit=1000)
            
            if format.lower() == "json":
                data = [record.to_dict() for record in history]
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                import csv
                with open(output_file, 'w', newline='') as f:
                    if history:
                        writer = csv.DictWriter(f, fieldnames=history[0].to_dict().keys())
                        writer.writeheader()
                        for record in history:
                            writer.writerow(record.to_dict())
            
            logger.info(f"Migration history exported to {output_file}")
        
        except Exception as e:
            logger.error(f"Failed to export migration history: {e}")
    
    def cleanup_old_records(self, days_to_keep: int = 90):
        """Clean up old migration records."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old operation records first (foreign key constraint)
                cursor.execute("""
                    DELETE FROM migration_operations 
                    WHERE migration_id IN (
                        SELECT id FROM migrations WHERE executed_at < ?
                    )
                """, (cutoff_date,))
                
                # Delete old migration records
                cursor.execute("DELETE FROM migrations WHERE executed_at < ?", (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old migration records")
        
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get migration statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total migrations
                cursor.execute("SELECT COUNT(*) FROM migrations")
                total_migrations = cursor.fetchone()[0]
                
                # Success rate
                cursor.execute("SELECT COUNT(*) FROM migrations WHERE status = 'SUCCESS'")
                successful_migrations = cursor.fetchone()[0]
                
                # Recent activity (last 30 days)
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute("SELECT COUNT(*) FROM migrations WHERE executed_at > ?", (thirty_days_ago,))
                recent_migrations = cursor.fetchone()[0]
                
                # Average execution time
                cursor.execute("SELECT AVG(execution_time) FROM migrations WHERE status = 'SUCCESS'")
                avg_execution_time = cursor.fetchone()[0] or 0.0
                
                return {
                    'total_migrations': total_migrations,
                    'successful_migrations': successful_migrations,
                    'success_rate': (successful_migrations / total_migrations * 100) if total_migrations > 0 else 0,
                    'recent_migrations_30_days': recent_migrations,
                    'average_execution_time': avg_execution_time
                }
        
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
