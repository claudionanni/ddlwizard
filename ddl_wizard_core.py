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
"""
DDL Wizard Core Module
======================

Core functionality for DDL Wizard that can be used by both CLI and GUI interfaces.
This module contains the main business logic for schema comparison and migration generation.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from database import DatabaseManager, DatabaseConfig
from git_manager import GitManager
from schema_comparator import SchemaComparator
from alter_generator import AlterStatementGenerator
from config_manager import DDLWizardConfig
from safety_analyzer import SafetyAnalyzer
from dependency_manager import DependencyManager
from migration_history import MigrationHistory
from schema_visualizer import SchemaVisualizer, generate_migration_report

logger = logging.getLogger(__name__)


class DDLWizardCore:
    """Core DDL Wizard functionality that can be used by both CLI and GUI."""
    
    def __init__(self, config: DDLWizardConfig):
        """Initialize the core with configuration."""
        self.config = config
        self.source_db = None
        self.dest_db = None
        self.git_manager = None
        self.comparator = SchemaComparator()
        self.alter_generator = None  # Will be initialized when we have dest_schema
        self.safety_analyzer = SafetyAnalyzer()
        self.dependency_manager = None  # Will be initialized when we have database connections
        self.history = MigrationHistory()
        self.visualizer = SchemaVisualizer()
    
    def connect_databases(self, source_config: DatabaseConfig, dest_config: DatabaseConfig) -> bool:
        """
        Connect to source and destination databases.
        
        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration
            
        Returns:
            bool: True if both connections successful, False otherwise
        """
        try:
            logger.info("Connecting to databases...")
            
            self.source_db = DatabaseManager(source_config)
            self.dest_db = DatabaseManager(dest_config)
            
            # Initialize alter generator with destination schema
            self.alter_generator = AlterStatementGenerator(dest_config.schema)
            
            # Initialize dependency manager with source database
            self.dependency_manager = DependencyManager(self.source_db)
            
            # Test connections
            if not self.source_db.test_connection():
                logger.error("Failed to connect to source database")
                return False
                
            if not self.dest_db.test_connection():
                logger.error("Failed to connect to destination database")
                return False
                
            logger.info("Database connections successful")
            return True
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False
    
    def initialize_git_repository(self, output_dir: str) -> bool:
        """
        Initialize git repository for migration tracking.
        
        Args:
            output_dir: Directory for git repository
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.git_manager = GitManager(output_dir)
            self.git_manager.init_repository()
            self.git_manager.create_directory_structure()
            logger.info(f"Initialized git repository at {output_dir}")
            return True
        except Exception as e:
            logger.error(f"Git initialization error: {e}")
            return False
    
    def extract_schema_objects(self) -> Tuple[Dict, Dict]:
        """
        Extract schema objects from both databases.
        
        Returns:
            Tuple[Dict, Dict]: (source_objects, dest_objects)
        """
        if not self.source_db or not self.dest_db:
            raise ValueError("Databases not connected. Call connect_databases() first.")
        
        logger.info("Extracting DDL objects...")
        source_objects = self.source_db.get_all_objects_with_ddl()
        dest_objects = self.dest_db.get_all_objects_with_ddl()
        
        # Save DDL objects to files for comparison
        if self.git_manager:
            logger.debug("Saving source DDL objects to files...")
            self.git_manager.save_all_objects(source_objects, self._get_source_ddl)
            logger.debug("Saving destination DDL objects to files...")
            # Note: We don't save dest objects to avoid conflicts, comparison will handle differences
        
        return source_objects, dest_objects
    
    def _get_source_ddl(self, object_type: str, object_name: str) -> str:
        """Get DDL for a source database object."""
        if object_type == 'tables':
            return self.source_db.get_table_ddl(object_name)
        elif object_type == 'views':
            return self.source_db.get_view_ddl(object_name)
        elif object_type == 'functions':
            return self.source_db.get_function_ddl(object_name)
        elif object_type == 'procedures':
            return self.source_db.get_procedure_ddl(object_name)
        elif object_type == 'triggers':
            return self.source_db.get_trigger_ddl(object_name)
        elif object_type == 'events':
            return self.source_db.get_event_ddl(object_name)
        elif object_type == 'sequences':
            return self.source_db.get_sequence_ddl(object_name)
        return ""
    
    def compare_schemas(self, source_objects: Dict, dest_objects: Dict) -> Dict:
        """
        Compare schema objects and identify differences.
        
        Args:
            source_objects: Source database objects
            dest_objects: Destination database objects
            
        Returns:
            Dict: Comparison results
        """
        logger.info("Comparing schemas...")
        return self.comparator.compare_objects(source_objects, dest_objects)
    
    def perform_safety_analysis(self, migration_operations: List[Dict]) -> List[Any]:
        """
        Perform safety analysis on migration operations.
        
        Args:
            migration_operations: List of migration operations
            
        Returns:
            List[Any]: List of safety warnings
        """
        safety_warnings = []
        if self.config.safety.validate_before_execution:
            logger.info("Performing safety analysis...")
            for operation in migration_operations:
                warnings = self.safety_analyzer.analyze_operation(operation)
                safety_warnings.extend(warnings)
            
            if safety_warnings:
                logger.warning(f"Found {len(safety_warnings)} safety warnings")
                for warning in safety_warnings:
                    logger.warning(f"{warning.level.value}: {warning.message}")
        
        return safety_warnings
    
    def generate_migration_sql(self, comparison: Dict, source_config: DatabaseConfig, dest_config: DatabaseConfig) -> str:
        """
        Generate migration SQL from comparison results.
        
        Args:
            comparison: Schema comparison results
            source_config: Source database configuration
            dest_config: Destination database configuration
            
        Returns:
            str: Generated migration SQL
        """
        def get_source_ddl(object_type: str, object_name: str) -> str:
            if object_type == 'tables':
                return self.source_db.get_table_ddl(object_name)
            elif object_type == 'views':
                return self.source_db.get_view_ddl(object_name)
            elif object_type == 'functions':
                return self.source_db.get_function_ddl(object_name)
            elif object_type == 'procedures':
                return self.source_db.get_procedure_ddl(object_name)
            elif object_type == 'triggers':
                return self.source_db.get_trigger_ddl(object_name)
            elif object_type == 'events':
                return self.source_db.get_event_ddl(object_name)
            elif object_type == 'sequences':
                return self.source_db.get_sequence_ddl(object_name)
            return ""
        
        def get_dest_ddl(object_type: str, object_name: str) -> str:
            if object_type == 'tables':
                return self.dest_db.get_table_ddl(object_name)
            elif object_type == 'views':
                return self.dest_db.get_view_ddl(object_name)
            elif object_type == 'functions':
                return self.dest_db.get_function_ddl(object_name)
            elif object_type == 'procedures':
                return self.dest_db.get_procedure_ddl(object_name)
            elif object_type == 'triggers':
                return self.dest_db.get_trigger_ddl(object_name)
            elif object_type == 'events':
                return self.dest_db.get_event_ddl(object_name)
            elif object_type == 'sequences':
                return self.dest_db.get_sequence_ddl(object_name)
            return ""
        
        logger.info("Generating migration SQL...")
        return self.comparator.generate_migration_sql(
            comparison, get_source_ddl, get_dest_ddl,
            source_config.schema, dest_config.schema
        )
    
    def generate_rollback_sql(self, comparison: Dict, source_objects: Dict, dest_objects: Dict) -> str:
        """
        Generate rollback SQL from comparison results.
        
        Args:
            comparison: Schema comparison results
            source_objects: Source database objects
            dest_objects: Destination database objects
            
        Returns:
            str: Generated rollback SQL
        """
        def get_source_ddl(object_type: str, object_name: str) -> str:
            if object_type == 'tables':
                return self.source_db.get_table_ddl(object_name)
            elif object_type == 'views':
                return self.source_db.get_view_ddl(object_name)
            elif object_type == 'functions':
                return self.source_db.get_function_ddl(object_name)
            elif object_type == 'procedures':
                return self.source_db.get_procedure_ddl(object_name)
            elif object_type == 'triggers':
                return self.source_db.get_trigger_ddl(object_name)
            elif object_type == 'events':
                return self.source_db.get_event_ddl(object_name)
            elif object_type == 'sequences':
                return self.source_db.get_sequence_ddl(object_name)
            return ""
        
        def get_dest_ddl(object_type: str, object_name: str) -> str:
            if object_type == 'tables':
                return self.dest_db.get_table_ddl(object_name)
            elif object_type == 'views':
                return self.dest_db.get_view_ddl(object_name)
            elif object_type == 'functions':
                return self.dest_db.get_function_ddl(object_name)
            elif object_type == 'procedures':
                return self.dest_db.get_procedure_ddl(object_name)
            elif object_type == 'triggers':
                return self.dest_db.get_trigger_ddl(object_name)
            elif object_type == 'events':
                return self.dest_db.get_event_ddl(object_name)
            elif object_type == 'sequences':
                return self.dest_db.get_sequence_ddl(object_name)
            return ""
        
        # Import the rollback generation function from main module
        from ddl_wizard import generate_detailed_rollback_sql
        
        # Generate rollback operations
        rollback_operations = self.dependency_manager.generate_rollback_operations([])
        rollback_sql_lines = [op['sql'] for op in rollback_operations]
        
        # Add detailed rollback for schema changes
        rollback_sql_lines.extend(generate_detailed_rollback_sql(
            comparison, source_objects, dest_objects, 
            self.alter_generator, get_source_ddl, get_dest_ddl
        ))
        
        return "\n".join(rollback_sql_lines)
    
    def generate_migration_report(self, comparison: Dict, safety_warnings: List[Any], 
                                source_config: DatabaseConfig, dest_config: DatabaseConfig) -> Dict:
        """
        Generate migration report data.
        
        Args:
            comparison: Schema comparison results
            safety_warnings: List of safety warnings
            source_config: Source database configuration
            dest_config: Destination database configuration
            
        Returns:
            Dict: Migration report data
        """
        def get_source_ddl(object_type: str, object_name: str) -> str:
            if object_type == 'tables':
                return self.source_db.get_table_ddl(object_name)
            elif object_type == 'views':
                return self.source_db.get_view_ddl(object_name)
            elif object_type == 'functions':
                return self.source_db.get_function_ddl(object_name)
            elif object_type == 'procedures':
                return self.source_db.get_procedure_ddl(object_name)
            elif object_type == 'triggers':
                return self.source_db.get_trigger_ddl(object_name)
            elif object_type == 'events':
                return self.source_db.get_event_ddl(object_name)
            elif object_type == 'sequences':
                return self.source_db.get_sequence_ddl(object_name)
            return ""
        
        def get_dest_ddl(object_type: str, object_name: str) -> str:
            if object_type == 'tables':
                return self.dest_db.get_table_ddl(object_name)
            elif object_type == 'views':
                return self.dest_db.get_view_ddl(object_name)
            elif object_type == 'functions':
                return self.dest_db.get_function_ddl(object_name)
            elif object_type == 'procedures':
                return self.dest_db.get_procedure_ddl(object_name)
            elif object_type == 'triggers':
                return self.dest_db.get_trigger_ddl(object_name)
            elif object_type == 'events':
                return self.dest_db.get_event_ddl(object_name)
            elif object_type == 'sequences':
                return self.dest_db.get_sequence_ddl(object_name)
            return ""
        
        # Generate migration report data from comparison results
        detailed_changes = []
        
        # Add table changes
        if 'tables' in comparison:
            tables_comparison = comparison['tables']
            
            # Tables only in source (to be created)
            for table_name in tables_comparison.get('only_in_source', []):
                detailed_changes.append({
                    'type': 'TABLE',
                    'object_type': 'table',
                    'object_name': table_name,
                    'operation': 'CREATE',
                    'sql': f"CREATE TABLE {table_name}"
                })
            
            # Tables only in destination (to be dropped)
            for table_name in tables_comparison.get('only_in_dest', []):
                detailed_changes.append({
                    'type': 'TABLE',
                    'object_type': 'table',
                    'object_name': table_name,
                    'operation': 'DROP',
                    'sql': f"DROP TABLE {table_name}"
                })
            
            # Tables with differences (to be modified)
            for table_name in tables_comparison.get('in_both', []):
                try:
                    source_ddl = get_source_ddl('tables', table_name)
                    dest_ddl = get_dest_ddl('tables', table_name)
                    if source_ddl and dest_ddl:
                        differences = self.comparator.analyze_table_differences(table_name, source_ddl, dest_ddl)
                        if differences:
                            detailed_changes.append({
                                'type': 'TABLE',
                                'object_type': 'table',
                                'object_name': table_name,
                                'operation': 'MODIFY',
                                'sql': f"ALTER TABLE {table_name}"
                            })
                except Exception:
                    pass
        
        # Add procedure changes
        if 'procedures' in comparison:
            procedures_comparison = comparison['procedures']
            
            # Procedures only in source (to be created)
            for proc_name in procedures_comparison.get('only_in_source', []):
                detailed_changes.append({
                    'type': 'PROCEDURE',
                    'object_type': 'procedure',
                    'object_name': proc_name,
                    'operation': 'CREATE',
                    'sql': f"CREATE PROCEDURE {proc_name}"
                })
            
            # Procedures only in destination (to be dropped)
            for proc_name in procedures_comparison.get('only_in_dest', []):
                detailed_changes.append({
                    'type': 'PROCEDURE',
                    'object_type': 'procedure',
                    'object_name': proc_name,
                    'operation': 'DROP',
                    'sql': f"DROP PROCEDURE {proc_name}"
                })
            
            # Procedures with differences (to be updated)
            for proc_name in procedures_comparison.get('in_both', []):
                try:
                    source_ddl = get_source_ddl('procedures', proc_name)
                    dest_ddl = get_dest_ddl('procedures', proc_name)
                    source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                    dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                    if source_normalized != dest_normalized:
                        detailed_changes.append({
                            'type': 'PROCEDURE',
                            'object_type': 'procedure',
                            'object_name': proc_name,
                            'operation': 'UPDATE',
                            'sql': f"DROP/CREATE PROCEDURE {proc_name}"
                        })
                except Exception:
                    pass
        
        # Add function changes
        if 'functions' in comparison:
            functions_comparison = comparison['functions']
            
            # Functions only in source (to be created)
            for func_name in functions_comparison.get('only_in_source', []):
                detailed_changes.append({
                    'type': 'FUNCTION',
                    'object_type': 'function',
                    'object_name': func_name,
                    'operation': 'CREATE',
                    'sql': f"CREATE FUNCTION {func_name}"
                })
            
            # Functions only in destination (to be dropped)
            for func_name in functions_comparison.get('only_in_dest', []):
                detailed_changes.append({
                    'type': 'FUNCTION',
                    'object_type': 'function',
                    'object_name': func_name,
                    'operation': 'DROP',
                    'sql': f"DROP FUNCTION {func_name}"
                })
            
            # Functions with differences (to be updated)
            for func_name in functions_comparison.get('in_both', []):
                try:
                    source_ddl = get_source_ddl('functions', func_name)
                    dest_ddl = get_dest_ddl('functions', func_name)
                    source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                    dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                    if source_normalized != dest_normalized:
                        detailed_changes.append({
                            'type': 'FUNCTION',
                            'object_type': 'function',
                            'object_name': func_name,
                            'operation': 'UPDATE',
                            'sql': f"DROP/CREATE FUNCTION {func_name}"
                        })
                except Exception:
                    pass

        # Add view changes
        if 'views' in comparison:
            views_comparison = comparison['views']
            
            # Views only in source (to be created)
            for view_name in views_comparison.get('only_in_source', []):
                detailed_changes.append({
                    'type': 'VIEW',
                    'object_type': 'view',
                    'object_name': view_name,
                    'operation': 'CREATE',
                    'sql': f"CREATE VIEW {view_name}"
                })
            
            # Views only in destination (to be dropped)
            for view_name in views_comparison.get('only_in_dest', []):
                detailed_changes.append({
                    'type': 'VIEW',
                    'object_type': 'view',
                    'object_name': view_name,
                    'operation': 'DROP',
                    'sql': f"DROP VIEW {view_name}"
                })
            
            # Views with differences (to be updated)
            for view_name in views_comparison.get('in_both', []):
                try:
                    source_ddl = get_source_ddl('views', view_name)
                    dest_ddl = get_dest_ddl('views', view_name)
                    source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                    dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                    if source_normalized != dest_normalized:
                        detailed_changes.append({
                            'type': 'VIEW',
                            'object_type': 'view',
                            'object_name': view_name,
                            'operation': 'UPDATE',
                            'sql': f"DROP/CREATE VIEW {view_name}"
                        })
                except Exception:
                    pass

        return {
            'source_schema': source_config.schema,
            'dest_schema': dest_config.schema,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'detailed_changes': detailed_changes,
            'safety_warnings': [{'level': w.level.value, 'message': w.message} for w in safety_warnings],
            'comparison_data': comparison  # Include full comparison data for detailed reporting
        }
    
    def generate_schema_visualization(self, source_objects: Dict, dest_objects: Dict, comparison: Dict, output_dir: str):
        """
        Generate schema visualization files including dependency analysis.
        
        Args:
            source_objects: Source database objects
            dest_objects: Destination database objects  
            comparison: Schema comparison results
            output_dir: Output directory for visualization files
        """
        logger.info("Generating schema visualizations...")
        
        # Create schema data structure
        schema_data = {}
        if 'tables' in source_objects:
            schema_data['tables'] = {}
            for table_obj in source_objects['tables']:
                table_name = table_obj['name']
                schema_data['tables'][table_name] = self.source_db.get_table_ddl(table_name)
        
        # Analyze and generate visualizations
        self.visualizer.analyze_schema(schema_data)
        visualization_output_dir = Path(output_dir) / "documentation"
        self.visualizer.export_documentation(str(visualization_output_dir))
        
        logger.info(f"Schema visualizations generated in {visualization_output_dir}")
        
        # Note: Dependency analysis is handled by the schema visualizer with migration report
        # The visualizer already calls the dependency analyzer with both source and destination objects
    
    def record_migration_history(self, migration_name: str, source_config: DatabaseConfig, 
                               dest_config: DatabaseConfig, operation_count: int, 
                               migration_file: str, rollback_file: str, 
                               warning_count: int) -> int:
        """
        Record migration in history.
        
        Args:
            migration_name: Name of the migration
            source_config: Source database configuration
            dest_config: Destination database configuration
            operation_count: Number of operations
            migration_file: Path to migration file
            rollback_file: Path to rollback file
            warning_count: Number of warnings
            
        Returns:
            int: Migration ID
        """
        migration_id = self.history.start_migration(
            migration_name, source_config.schema, dest_config.schema,
            operation_count, migration_file, rollback_file, warning_count
        )
        
        self.history.complete_migration(migration_id, "SUCCESS", 0.0, operation_count, 0, "Migration completed successfully")
        logger.info(f"Migration tracking completed: {migration_id}")
        
        return migration_id
    
    def write_migration_files(self, migration_sql: str, rollback_sql: str, 
                            migration_report_data: Dict, output_dir: str,
                            comparison: Dict = None, source_objects: Dict = None) -> Tuple[str, str, str]:
        """
        Write migration files to disk.
        
        Args:
            migration_sql: Migration SQL content
            rollback_sql: Rollback SQL content
            migration_report_data: Migration report data
            output_dir: Output directory
            comparison: Schema comparison results (for enhanced reporting)
            source_objects: Source database objects (for dependency analysis)
            
        Returns:
            Tuple[str, str, str]: Paths to migration file, rollback file, migration report
        """
        output_path = Path(output_dir)
        
        # Write migration files
        migration_file = output_path / self.config.output.migration_file
        rollback_file = output_path / self.config.output.rollback_file
        migration_report_path = output_path / "migration_report.md"
        migration_summary_path = output_path / "migration_summary.txt"
        
        migration_file.write_text(migration_sql)
        rollback_file.write_text(rollback_sql)
        
        # Generate migration report with enhanced analysis
        if comparison is not None and source_objects is not None:
            # Create enhanced comparison data with source objects for dependency analysis
            enhanced_comparison = comparison.copy()
            enhanced_comparison['source_objects'] = source_objects
            generate_migration_report(enhanced_comparison, migration_sql, str(migration_report_path))
        else:
            # Fallback to standard report generation
            generate_migration_report(migration_report_data, migration_sql, str(migration_report_path))
        
        # Generate migration summary table
        comparison_summary = self._generate_comparison_summary(migration_report_data)
        migration_summary_path.write_text(comparison_summary)
        
        return str(migration_file), str(rollback_file), str(migration_report_path)
    
    def _generate_comparison_summary(self, migration_report_data: Dict) -> str:
        """Generate a detailed text summary of the comparison with tabular format."""
        lines = [
            "DDL Wizard Schema Comparison Report",
            "=" * 50,
            f"Source Schema: {migration_report_data.get('source_schema', 'unknown')}",
            f"Destination Schema: {migration_report_data.get('dest_schema', 'unknown')}",
            f"Generated: {migration_report_data.get('timestamp', 'unknown')}",
            "",
        ]
        
        # Generate tabular summary
        comparison_data = migration_report_data.get('comparison_data', {})
        detailed_changes = migration_report_data.get('detailed_changes', [])
        if comparison_data:
            lines.extend(self._generate_tabular_summary(comparison_data, detailed_changes))
        
        # Add detailed changes if any
        changes = migration_report_data.get('detailed_changes', [])
        total_operations = len(changes)
        
        lines.extend([
            "",
            f"Total Migration Operations: {total_operations}",
            f"Safety Warnings: {len(migration_report_data.get('safety_warnings', []))}",
        ])
        
        if changes:
            lines.append("")
            lines.append("Detailed Changes:")
            lines.append("-" * 20)
            
            # Group changes by object type for better reporting
            object_types = {}
            for change in changes:
                change_type = change.get('operation', 'unknown')
                object_name = change.get('object_name', 'unknown')
                object_type = change.get('object_type', 'unknown')
                
                if object_type not in object_types:
                    object_types[object_type] = []
                object_types[object_type].append(f"{change_type}: {object_name}")
            
            # Add detailed reporting for each object type
            for obj_type, changes_list in object_types.items():
                lines.append(f"  {obj_type.upper()}:")
                for change in changes_list:
                    lines.append(f"    - {change}")
        else:
            lines.append("")
            lines.append("✅ Schemas are in sync - no migration operations required")
        
        # Add safety warnings if any
        safety_warnings = migration_report_data.get('safety_warnings', [])
        if safety_warnings:
            lines.append("")
            lines.append("Safety Warnings:")
            lines.append("-" * 15)
            for warning in safety_warnings:
                lines.append(f"  ⚠️  {warning.get('message', 'Unknown warning')}")
        
        return "\n".join(lines)
    
    def _generate_tabular_summary(self, comparison_data: Dict, detailed_changes: List = None) -> list:
        """Generate a tabular summary of schema comparison results."""
        lines = [
            "Schema Objects Summary",
            "-" * 22,
            ""
        ]
        
        # Define object types with descriptions
        object_types = {
            'tables': 'Tables',
            'views': 'Views', 
            'procedures': 'Procedures',
            'functions': 'Functions',
            'triggers': 'Triggers',
            'events': 'Events',
            'sequences': 'Sequences'
        }
        
        # Count operations by object type from detailed changes (the authoritative source)
        operation_counts = {}
        if detailed_changes:
            for change in detailed_changes:
                operation = change.get('operation', 'unknown')
                obj_type = change.get('object_type', 'unknown').lower()
                
                # Normalize object type names to match comparison_data keys
                if obj_type == 'table':
                    obj_type = 'tables'
                elif obj_type == 'view':
                    obj_type = 'views'
                elif obj_type == 'procedure':
                    obj_type = 'procedures'
                elif obj_type == 'function':
                    obj_type = 'functions'
                elif obj_type == 'trigger':
                    obj_type = 'triggers'
                elif obj_type == 'event':
                    obj_type = 'events'
                elif obj_type == 'sequence':
                    obj_type = 'sequences'
                
                if obj_type not in operation_counts:
                    operation_counts[obj_type] = {'CREATE': 0, 'DROP': 0, 'MODIFY': 0}
                
                if operation in operation_counts[obj_type]:
                    operation_counts[obj_type][operation] += 1
        
        # Create header
        header = f"{'Object Type':<12} {'Source':<8} {'Dest':<8} {'Both':<8} {'Create':<8} {'Drop':<8} {'Modify':<8} {'Total':<8}"
        lines.append(header)
        lines.append("-" * len(header))
        
        total_create_ops = 0
        total_drop_ops = 0
        total_modify_ops = 0
        
        for obj_type, friendly_name in object_types.items():
            if obj_type in comparison_data:
                obj_data = comparison_data[obj_type]
                
                # Calculate counts for display (source/dest/both)
                only_source = len(obj_data.get('only_in_source', []))
                only_dest = len(obj_data.get('only_in_dest', []))
                in_both = len(obj_data.get('in_both', []))
                
                # Get actual operation counts from detailed changes
                ops = operation_counts.get(obj_type, {'CREATE': 0, 'DROP': 0, 'MODIFY': 0})
                will_create = ops['CREATE']
                will_drop = ops['DROP']
                will_modify = ops['MODIFY']
                total_ops = will_create + will_drop + will_modify
                
                total_create_ops += will_create
                total_drop_ops += will_drop
                total_modify_ops += will_modify
                
                # Total counts for source/dest columns
                total_source = only_source + in_both
                total_dest = only_dest + in_both
                
                # Format row
                row = f"{friendly_name:<12} {total_source:<8} {total_dest:<8} {in_both:<8} {will_create:<8} {will_drop:<8} {will_modify:<8} {total_ops:<8}"
                lines.append(row)
        
        total_all_ops = total_create_ops + total_drop_ops + total_modify_ops
        lines.append("-" * len(header))
        lines.append(f"{'TOTAL':<12} {'':<8} {'':<8} {'':<8} {total_create_ops:<8} {total_drop_ops:<8} {total_modify_ops:<8} {total_all_ops:<8}")
        lines.append("")
        
        # Add legend
        lines.extend([
            "Column Descriptions:",
            "  Source:    Total objects in source schema",
            "  Dest:      Total objects in destination schema", 
            "  Both:      Objects existing in both schemas",
            "  Create:    Objects to be created in destination",
            "  Drop:      Objects to be dropped from destination",
            "  Modify:    Objects to be modified (same name, different definition)",
            "  Total:     All operations for this object type",
        ])
        
        return lines


def run_complete_migration(source_config: DatabaseConfig, dest_config: DatabaseConfig, 
                         config: DDLWizardConfig, output_dir: str, 
                         skip_safety_checks: bool = False, 
                         enable_visualization: bool = False) -> Dict[str, Any]:
    """
    Run a complete migration workflow using the core functionality.
    
    This function provides a high-level interface that can be used by both CLI and GUI.
    
    Args:
        source_config: Source database configuration
        dest_config: Destination database configuration
        config: DDL Wizard configuration
        output_dir: Output directory for files
        skip_safety_checks: Whether to skip safety analysis
        enable_visualization: Whether to generate visualizations
        
    Returns:
        Dict[str, Any]: Results containing file paths, operation count, warnings, etc.
    """
    core = DDLWizardCore(config)
    
    # Connect to databases
    if not core.connect_databases(source_config, dest_config):
        raise RuntimeError("Failed to connect to databases")
    
    # Initialize git repository
    if not core.initialize_git_repository(output_dir):
        raise RuntimeError("Failed to initialize git repository")
    
    # Extract schema objects
    source_objects, dest_objects = core.extract_schema_objects()
    
    # Compare schemas
    comparison = core.compare_schemas(source_objects, dest_objects)
    
    # Perform safety analysis
    migration_operations = []  # TODO: Extract from comparison
    safety_warnings = []
    if not skip_safety_checks:
        safety_warnings = core.perform_safety_analysis(migration_operations)
    
    # Generate migration SQL
    migration_sql = core.generate_migration_sql(comparison, source_config, dest_config)
    
    # Generate rollback SQL
    rollback_sql = core.generate_rollback_sql(comparison, source_objects, dest_objects)
    
    # Generate migration report
    migration_report_data = core.generate_migration_report(comparison, safety_warnings, source_config, dest_config)
    
    # Generate schema visualization if requested
    if enable_visualization:
        core.generate_schema_visualization(source_objects, dest_objects, comparison, output_dir)
    
    # Write files
    migration_file, rollback_file, migration_report_file = core.write_migration_files(
        migration_sql, rollback_sql, migration_report_data, output_dir, 
        comparison, source_objects
    )
    
    # Record in history
    operation_count = len(migration_report_data['detailed_changes'])
    migration_name = f"{source_config.schema}_to_{dest_config.schema}_{int(time.time())}"
    migration_id = core.record_migration_history(
        migration_name, source_config, dest_config, operation_count, 
        migration_file, rollback_file, len(safety_warnings)
    )
    
    return {
        'migration_id': migration_id,
        'migration_file': migration_file,
        'rollback_file': rollback_file,
        'migration_report_file': migration_report_file,
        'output_dir': output_dir,
        'operation_count': operation_count,
        'safety_warnings': safety_warnings,
        'comparison': comparison,
        'migration_sql': migration_sql,
        'rollback_sql': rollback_sql
    }
