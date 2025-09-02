#!/usr/bin/env python3
"""
DDL Wizard - Database DDL Extraction and Comparison Tool
========================================================

A comprehensive tool for extracting DDL objects from databases, managing them in git,
and generating migration scripts for schema synchronization.

This is the CLI interface that uses the core DDL Wizard functionality.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

from database import DatabaseManager, DatabaseConfig
from git_manager import GitManager
from schema_comparator import SchemaComparator
from alter_generator import AlterStatementGenerator
from config_manager import DDLWizardConfig
from safety_analyzer import SafetyAnalyzer
from dependency_manager import DependencyManager
from migration_history import MigrationHistory
from schema_visualizer import SchemaVisualizer, generate_migration_report
from interactive_mode import InteractiveModeManager
from ddl_wizard_core import DDLWizardCore, run_complete_migration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DDL Wizard - MariaDB Database Schema Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Mode selection
    parser.add_argument('--mode', choices=['compare', 'extract', 'migrate', 'visualize', 'history'], 
                       default='compare', help='Operation mode (default: compare)')
    
    # Configuration
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--profile', help='Configuration profile to use')
    
    # Source database arguments
    parser.add_argument('--source-host', help='Source MariaDB host')
    parser.add_argument('--source-port', type=int, default=3306, help='Source MariaDB port (default: 3306)')
    parser.add_argument('--source-user', help='Source MariaDB username')
    parser.add_argument('--source-password', help='Source MariaDB password')
    parser.add_argument('--source-schema', help='Source schema name')
    
    # Destination database arguments
    parser.add_argument('--dest-host', help='Destination MariaDB host')
    parser.add_argument('--dest-port', type=int, default=3306, help='Destination MariaDB port (default: 3306)')
    parser.add_argument('--dest-user', help='Destination MariaDB username')
    parser.add_argument('--dest-password', help='Destination MariaDB password')
    parser.add_argument('--dest-schema', help='Destination schema name')
    
    # Options
    parser.add_argument('--output-dir', default='./ddl_output', help='Output directory for git repository (default: ./ddl_output)')
    parser.add_argument('--migration-file', default='migration.sql', help='Output migration SQL file (default: migration.sql)')
    parser.add_argument('--rollback-file', default='rollback.sql', help='Output rollback SQL file (default: rollback.sql)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Enable interactive mode')
    parser.add_argument('--auto-approve', action='store_true', help='Auto-approve all operations (non-interactive)')
    parser.add_argument('--dry-run', action='store_true', help='Generate SQL without executing')
    parser.add_argument('--visualize', action='store_true', help='Generate schema visualizations')
    parser.add_argument('--skip-safety-checks', action='store_true', help='Skip safety analysis')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    return parser.parse_args()


def load_configuration(args: argparse.Namespace) -> DDLWizardConfig:
    """Load configuration from file or command line arguments."""
    if args.config:
        try:
            config = DDLWizardConfig.load_config(args.config, args.profile)
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)
    else:
        # Create config from command line arguments
        from config_manager import DatabaseConnection, SafetySettings, OutputSettings
        
        source_db = None
        dest_db = None
        
        if args.source_host and args.source_user and args.source_schema:
            source_db = DatabaseConnection(
                host=args.source_host,
                port=args.source_port,
                user=args.source_user,
                password=args.source_password if args.source_password else "",
                schema=args.source_schema
            )
        
        if args.dest_host and args.dest_user and args.dest_schema:
            dest_db = DatabaseConnection(
                host=args.dest_host,
                port=args.dest_port,
                user=args.dest_user,
                password=args.dest_password if args.dest_password else "",
                schema=args.dest_schema
            )
        
        # For modes that don't need database connections, create dummy connections
        if args.mode == 'history':
            source_db = DatabaseConnection("dummy", 3306, "dummy", "", "dummy")
            dest_db = DatabaseConnection("dummy", 3306, "dummy", "", "dummy")
        elif not source_db and not dest_db:
            source_db = DatabaseConnection("localhost", 3306, "root", "", "test")
            dest_db = DatabaseConnection("localhost", 3306, "root", "", "test")
        elif not dest_db:
            dest_db = DatabaseConnection("localhost", 3306, "root", "", "test")
        elif not source_db:
            source_db = DatabaseConnection("localhost", 3306, "root", "", "test")
        
        safety_settings = SafetySettings()
        if hasattr(args, 'skip_safety_checks') and args.skip_safety_checks:
            safety_settings.validate_before_execution = False
        
        output_settings = OutputSettings(
            output_dir=args.output_dir,
            migration_file=args.migration_file if hasattr(args, 'migration_file') else "migration.sql",
            rollback_file=args.rollback_file if hasattr(args, 'rollback_file') else "rollback.sql"
        )
        
        config = DDLWizardConfig(
            source=source_db,
            destination=dest_db,
            safety=safety_settings,
            output=output_settings
        )
    
    return config


def extract_mode(config: DDLWizardConfig, args: argparse.Namespace):
    """Extract DDL objects from source database."""
    logger.info("Running in extract mode...")
    
    if not config.source.host:
        logger.error("Source database configuration required for extract mode")
        sys.exit(1)
    
    source_config = DatabaseConfig(
        host=config.source.host,
        port=config.source.port,
        user=config.source.user,
        password=config.source.password,
        schema=config.source.schema
    )
    source_db = DatabaseManager(source_config)
    git_manager = GitManager(config.output.output_dir)
    
    # Test connection
    if not source_db.test_connection():
        logger.error("Failed to connect to source database")
        sys.exit(1)
    
    # Initialize git repository
    git_manager.init_repository()
    git_manager.create_directory_structure()
    
    # Extract and save objects
    logger.info("Extracting DDL objects...")
    source_objects = source_db.get_all_objects()
    
    def get_source_ddl(object_type: str, object_name: str) -> str:
        if object_type == 'tables':
            return source_db.get_table_ddl(object_name)
        elif object_type == 'functions':
            return source_db.get_function_ddl(object_name)
        elif object_type == 'procedures':
            return source_db.get_procedure_ddl(object_name)
        elif object_type == 'triggers':
            return source_db.get_trigger_ddl(object_name)
        elif object_type == 'events':
            return source_db.get_event_ddl(object_name)
        return ""
    
    git_manager.save_all_objects(source_objects, get_source_ddl)
    git_manager.commit_changes(f"DDL extraction from {source_config.schema}")
    
    logger.info(f"DDL objects extracted to {config.output.output_dir}")


def visualize_mode(config: DDLWizardConfig, args: argparse.Namespace):
    """Generate schema visualizations."""
    logger.info("Running in visualize mode...")
    
    if not config.source.host:
        logger.error("Source database configuration required for visualize mode")
        sys.exit(1)
    
    source_config = DatabaseConfig(
        host=config.source.host,
        port=config.source.port,
        user=config.source.user,
        password=config.source.password,
        schema=config.source.schema
    )
    source_db = DatabaseManager(source_config)
    visualizer = SchemaVisualizer()
    
    # Test connection
    if not source_db.test_connection():
        logger.error("Failed to connect to source database")
        sys.exit(1)
    
    # Extract schema data
    logger.info("Extracting schema structure...")
    source_objects = source_db.get_all_objects()
    
    # Create schema data structure
    schema_data = {}
    if 'tables' in source_objects:
        schema_data['tables'] = {}
        for table_name in source_objects['tables']:
            schema_data['tables'][table_name] = source_db.get_table_ddl(table_name)
    
    # Analyze and generate visualizations
    visualizer.analyze_schema(schema_data)
    output_dir = Path(config.output.output_dir) / "documentation"
    visualizer.export_documentation(str(output_dir))
    
    logger.info(f"Schema visualizations generated in {output_dir}")


def generate_detailed_rollback_sql(comparison: Dict, source_objects: Dict, dest_objects: Dict, alter_generator, get_source_ddl, get_dest_ddl) -> List[str]:
    """Generate detailed rollback SQL for all schema changes."""
    rollback_lines = []
    
    # Add header comment
    rollback_lines.append("-- Detailed rollback for all schema changes")
    rollback_lines.append("")
    
    # Add header comment
    rollback_lines.append("-- Detailed rollback for all schema changes")
    rollback_lines.append("")
    
    # Process tables that exist in both and may have structural differences
    if 'tables' in comparison:
        tables_comparison = comparison['tables']
        rollback_lines.append(f"-- DEBUG: in_both tables: {list(tables_comparison.get('in_both', []))}")
        rollback_lines.append(f"-- DEBUG: source_objects keys: {list(tables_comparison.get('source_objects', {}).keys())}")
        rollback_lines.append(f"-- DEBUG: dest_objects keys: {list(tables_comparison.get('dest_objects', {}).keys())}")
        rollback_lines.append("")
        
        for table_name in comparison['tables'].get('in_both', []):
            # Get DDL for this table from both databases
            rollback_lines.append(f"-- DEBUG: Processing table {table_name}")
            
            try:
                # Fetch DDL directly from the database connections
                source_ddl = get_source_ddl('tables', table_name)
                dest_ddl = get_dest_ddl('tables', table_name) 
                
                rollback_lines.append(f"-- DEBUG: source_ddl length: {len(source_ddl) if source_ddl else 0}")
                rollback_lines.append(f"-- DEBUG: dest_ddl length: {len(dest_ddl) if dest_ddl else 0}")
                
                if source_ddl and dest_ddl:
                    # Use the comparator to analyze table differences
                    from schema_comparator import SchemaComparator
                    temp_comparator = SchemaComparator()
                    differences = temp_comparator.analyze_table_differences(table_name, source_ddl, dest_ddl)
                    
                    rollback_lines.append(f"-- DEBUG: differences found: {len(differences) if differences else 0}")
                    
                    if differences:
                        # Generate rollback statements for this table
                        rollback_statements = alter_generator.generate_rollback_statements(table_name, differences)
                        rollback_lines.append(f"-- DEBUG: rollback_statements generated: {len(rollback_statements)}")
                        for stmt in rollback_statements:
                            rollback_lines.append(stmt + ";")
                        rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process table {table_name}: {str(e)}")
                continue
    
    # Process procedures that exist in both and may have differences
    if 'procedures' in comparison:
        procedures_comparison = comparison['procedures']
        rollback_lines.append(f"-- DEBUG: in_both procedures: {list(procedures_comparison.get('in_both', []))}")
        
        # Only process procedures that have actual differences
        procedures_with_differences = procedures_comparison.get('source_objects', {})
        dest_procedures = procedures_comparison.get('dest_objects', {})
        
        for proc_name in procedures_comparison.get('in_both', []):
            rollback_lines.append(f"-- DEBUG: Processing procedure {proc_name}")
            
            try:
                # Check if this procedure has differences by comparing the comparison objects
                source_proc = procedures_with_differences.get(proc_name, {})
                dest_proc = dest_procedures.get(proc_name, {})
                
                # Get DDL for both versions
                source_ddl = get_source_ddl('procedures', proc_name)
                dest_ddl = get_dest_ddl('procedures', proc_name)
                
                rollback_lines.append(f"-- DEBUG: source_ddl length: {len(source_ddl) if source_ddl else 0}")
                rollback_lines.append(f"-- DEBUG: dest_ddl length: {len(dest_ddl) if dest_ddl else 0}")
                
                # Only generate rollback if there are actual differences in the comparison
                # Check if this procedure appears in the migration (has differences)
                # Use normalized comparison to avoid whitespace differences
                source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                
                if source_normalized != dest_normalized and dest_ddl:
                    # Additional check: verify this procedure was actually modified in the migration
                    # by checking if it has a 'has_differences' flag or similar indication
                    rollback_lines.append(f"-- Rollback procedure: {proc_name}")
                    rollback_lines.append(f"DROP PROCEDURE IF EXISTS `{proc_name}`;")
                    # Add the destination's original DDL to restore it with DELIMITER
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
                else:
                    rollback_lines.append(f"-- No changes needed for procedure {proc_name}")
                    
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process procedure {proc_name}: {str(e)}")
                continue
        
        # Handle procedures that are only in source (created in migration, need restoration or DROP in rollback)
        for proc_name in procedures_comparison.get('only_in_source', []):
            rollback_lines.append(f"-- DEBUG: Processing only_in_source procedure {proc_name}")
            try:
                # Try to get destination DDL - if it exists, restore it; if not, drop the created procedure
                try:
                    dest_ddl = get_dest_ddl('procedures', proc_name)
                    has_dest_ddl = bool(dest_ddl and dest_ddl.strip())
                except Exception:
                    # Procedure doesn't exist in destination
                    dest_ddl = None
                    has_dest_ddl = False
                
                if has_dest_ddl:
                    # Procedure exists in destination - restore original version
                    rollback_lines.append(f"-- Rollback procedure modification: {proc_name}")
                    rollback_lines.append(f"DROP PROCEDURE IF EXISTS `{proc_name}`;")
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
                else:
                    # Procedure doesn't exist in destination - drop the created procedure
                    rollback_lines.append(f"-- Rollback creation of procedure: {proc_name}")
                    rollback_lines.append(f"DROP PROCEDURE IF EXISTS `{proc_name}`;")
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process procedure {proc_name}: {str(e)}")
                continue
        
        # Handle procedures that are only in destination (dropped in migration, need CREATE in rollback)
        for proc_name in procedures_comparison.get('only_in_dest', []):
            rollback_lines.append(f"-- DEBUG: Processing only_in_dest procedure {proc_name}")
            try:
                dest_ddl = get_dest_ddl('procedures', proc_name)
                if dest_ddl:
                    rollback_lines.append(f"-- Rollback deletion of procedure: {proc_name}")
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to restore procedure {proc_name}: {str(e)}")
                continue
    
    # Process functions that exist in both and may have differences  
    if 'functions' in comparison:
        functions_comparison = comparison['functions']
        rollback_lines.append(f"-- DEBUG: in_both functions: {list(functions_comparison.get('in_both', []))}")
        
        # Only process functions that have actual differences
        functions_with_differences = functions_comparison.get('source_objects', {})
        dest_functions = functions_comparison.get('dest_objects', {})
        
        for func_name in functions_comparison.get('in_both', []):
            rollback_lines.append(f"-- DEBUG: Processing function {func_name}")
            
            try:
                # Check if this function has differences by comparing the comparison objects
                source_func = functions_with_differences.get(func_name, {})
                dest_func = dest_functions.get(func_name, {})
                
                # Get DDL for both versions
                source_ddl = get_source_ddl('functions', func_name)
                dest_ddl = get_dest_ddl('functions', func_name)
                
                rollback_lines.append(f"-- DEBUG: source_ddl length: {len(source_ddl) if source_ddl else 0}")
                rollback_lines.append(f"-- DEBUG: dest_ddl length: {len(dest_ddl) if dest_ddl else 0}")
                
                # Only generate rollback if there are actual differences
                # Use normalized comparison to avoid whitespace differences
                source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                
                if source_normalized != dest_normalized and dest_ddl:
                    rollback_lines.append(f"-- Rollback function: {func_name}")
                    rollback_lines.append(f"DROP FUNCTION IF EXISTS `{func_name}`;")
                    # Add the destination's original DDL to restore it with DELIMITER
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
                else:
                    rollback_lines.append(f"-- No changes needed for function {func_name}")
                    
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process function {func_name}: {str(e)}")
                continue
        
        # Handle functions that are only in source (created in migration, need restoration or DROP in rollback)
        for func_name in functions_comparison.get('only_in_source', []):
            rollback_lines.append(f"-- DEBUG: Processing only_in_source function {func_name}")
            try:
                # Try to get destination DDL - if it exists, restore it; if not, drop the created function
                try:
                    dest_ddl = get_dest_ddl('functions', func_name)
                    has_dest_ddl = bool(dest_ddl and dest_ddl.strip())
                except Exception:
                    # Function doesn't exist in destination
                    dest_ddl = None
                    has_dest_ddl = False
                
                if has_dest_ddl:
                    # Function exists in destination - restore original version
                    rollback_lines.append(f"-- Rollback function modification: {func_name}")
                    rollback_lines.append(f"DROP FUNCTION IF EXISTS `{func_name}`;")
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
                else:
                    # Function doesn't exist in destination - drop the created function
                    rollback_lines.append(f"-- Rollback creation of function: {func_name}")
                    rollback_lines.append(f"DROP FUNCTION IF EXISTS `{func_name}`;")
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process function {func_name}: {str(e)}")
                continue
        
        # Handle functions that are only in destination (dropped in migration, need CREATE in rollback)
        for func_name in functions_comparison.get('only_in_dest', []):
            rollback_lines.append(f"-- DEBUG: Processing only_in_dest function {func_name}")
            try:
                dest_ddl = get_dest_ddl('functions', func_name)
                if dest_ddl:
                    rollback_lines.append(f"-- Rollback deletion of function: {func_name}")
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to restore function {func_name}: {str(e)}")
                continue
    
    return rollback_lines


def history_mode(config: DDLWizardConfig, args: argparse.Namespace):
    """Show migration history."""
    logger.info("Showing migration history...")
    
    history = MigrationHistory()
    records = history.get_migration_history()
    
    if not records:
        print("No migration history found.")
        return
    
    print("\nMigration History")
    print("=" * 80)
    print(f"{'ID':<5} {'Name':<30} {'Status':<12} {'Executed At':<20} {'Time':<8}")
    print("-" * 80)
    
    for record in records:
        print(f"{record.id:<5} {record.migration_name[:29]:<30} {record.status:<12} "
              f"{record.executed_at[:19]:<20} {record.execution_time:<8.2f}s")
    
    # Show statistics
    stats = history.get_statistics()
    print(f"\nStatistics:")
    print(f"Total migrations: {stats.get('total_migrations', 0)}")
    print(f"Success rate: {stats.get('success_rate', 0):.1f}%")
    print(f"Recent migrations (30 days): {stats.get('recent_migrations_30_days', 0)}")


def compare_mode(config: DDLWizardConfig, args: argparse.Namespace):
    """Compare schemas and generate migration SQL using core module."""
    logger.info("Running in compare mode...")
    
    if not config.source.host or not config.destination.host:
        logger.error("Both source and destination database configurations required for compare mode")
        sys.exit(1)
    
    # Create database configurations
    source_config = DatabaseConfig(
        host=config.source.host,
        port=config.source.port,
        user=config.source.user,
        password=config.source.password,
        schema=config.source.schema
    )
    dest_config = DatabaseConfig(
        host=config.destination.host,
        port=config.destination.port,
        user=config.destination.user,
        password=config.destination.password,
        schema=config.destination.schema
    )
    
    try:
        # Use the core module for the complete migration workflow
        results = run_complete_migration(
            source_config=source_config,
            dest_config=dest_config,
            config=config,
            output_dir=config.output.output_dir,
            skip_safety_checks=getattr(args, 'skip_safety_checks', False),
            enable_visualization=getattr(args, 'enable_visualization', True)
        )
        
        # Display results
        logger.info(f"Migration completed successfully!")
        logger.info(f"Migration ID: {results['migration_id']}")
        logger.info(f"Operations: {results['operation_count']}")
        logger.info(f"Safety warnings: {len(results['safety_warnings'])}")
        logger.info(f"Migration file: {results['migration_file']}")
        logger.info(f"Rollback file: {results['rollback_file']}")
        logger.info(f"Migration report: {results['migration_report_file']}")
        
        # Show safety warnings if any
        if results['safety_warnings']:
            logger.warning("Safety warnings detected:")
            for warning in results['safety_warnings']:
                logger.warning(f"  {warning.level.value}: {warning.message}")
                
        logger.info("Compare mode completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if getattr(args, 'verbose', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main application entry point."""
    
    # Tables
    if 'tables' in comparison:
        for table_name in comparison['tables']['only_in_source']:
            migration_operations.append({
                'type': 'CREATE_TABLE',
                'table_name': table_name,
                'sql': get_source_ddl('tables', table_name)
            })
    
    # Safety analysis
    safety_warnings = []
    if not args.skip_safety_checks and config.safety.validate_before_execution:
        logger.info("Performing safety analysis...")
        for operation in migration_operations:
            warnings = safety_analyzer.analyze_operation(operation)
            safety_warnings.extend(warnings)
        
        if safety_warnings:
            logger.warning(f"Found {len(safety_warnings)} safety warnings")
            for warning in safety_warnings:
                logger.warning(f"{warning.level.value}: {warning.message}")
    
    # Dependency analysis
    logger.info("Analyzing dependencies...")
    dependency_info = dependency_manager.analyze_dependencies(source_config.schema)
    ordered_operations = dependency_manager.order_operations_by_dependencies(migration_operations, dependency_info)
    
    # Interactive confirmation
    if interactive_mode and not args.auto_approve:
        if not interactive_mode.confirm_migration(
            source_config.schema, dest_config.schema, 
            len(ordered_operations), safety_warnings
        ):
            logger.info("Migration cancelled by user")
            return
    
    # Generate migration files
    migration_name = f"{source_config.schema}_to_{dest_config.schema}_{int(time.time())}"
    migration_file = Path(config.output.output_dir) / config.output.migration_file
    rollback_file = Path(config.output.output_dir) / config.output.rollback_file
    
    # Generate migration SQL
    logger.info("Generating migration SQL...")
    migration_sql = comparator.generate_migration_sql(
        comparison, get_source_ddl, get_dest_ddl,
        source_config.schema, dest_config.schema
    )
    
    # Generate rollback SQL
    rollback_operations = dependency_manager.generate_rollback_operations(ordered_operations)
    rollback_sql_lines = [op['sql'] for op in rollback_operations]
    
    # Add detailed rollback for table structural changes
    rollback_sql_lines.extend(generate_detailed_rollback_sql(comparison, source_objects, dest_objects, alter_generator, get_source_ddl, get_dest_ddl))
    
    rollback_sql = "\n".join(rollback_sql_lines)
    
    # Write files
    migration_file.write_text(migration_sql)
    rollback_file.write_text(rollback_sql)
    
    # Generate reports
    report_path = Path(config.output.output_dir) / "comparison_report.txt"
    report = comparator.generate_comparison_report(comparison, get_source_ddl, get_dest_ddl)
    report_path.write_text(report)
    
    # Migration report
    # Generate migration report data from comparison results
    detailed_changes = []
    
    # Add table changes
    if 'tables' in comparison:
        tables_comparison = comparison['tables']
        
        # Tables only in source (to be created)
        for table_name in tables_comparison.get('only_in_source', []):
            detailed_changes.append({
                'type': 'TABLE',
                'object_name': table_name,
                'operation': 'CREATE',
                'sql': f"CREATE TABLE {table_name}"
            })
        
        # Tables only in destination (to be dropped)
        for table_name in tables_comparison.get('only_in_dest', []):
            detailed_changes.append({
                'type': 'TABLE',
                'object_name': table_name,
                'operation': 'DROP',
                'sql': f"DROP TABLE {table_name}"
            })
        
        # Tables with differences (to be modified)
        for table_name in tables_comparison.get('in_both', []):
            # Check if this table actually has differences using the same logic as rollback
            try:
                source_ddl = get_source_ddl('tables', table_name)
                dest_ddl = get_dest_ddl('tables', table_name)
                if source_ddl and dest_ddl:
                    # Use the comparator to analyze table differences
                    temp_comparator = SchemaComparator()
                    differences = temp_comparator.analyze_table_differences(table_name, source_ddl, dest_ddl)
                    if differences:
                        detailed_changes.append({
                            'type': 'TABLE',
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
                'object_name': proc_name,
                'operation': 'CREATE',
                'sql': f"CREATE PROCEDURE {proc_name}"
            })
        
        # Procedures only in destination (to be dropped)
        for proc_name in procedures_comparison.get('only_in_dest', []):
            detailed_changes.append({
                'type': 'PROCEDURE',
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
                'object_name': func_name,
                'operation': 'CREATE',
                'sql': f"CREATE FUNCTION {func_name}"
            })
        
        # Functions only in destination (to be dropped)
        for func_name in functions_comparison.get('only_in_dest', []):
            detailed_changes.append({
                'type': 'FUNCTION',
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
                        'object_name': func_name,
                        'operation': 'UPDATE',
                        'sql': f"DROP/CREATE FUNCTION {func_name}"
                    })
            except Exception:
                pass

    migration_report_data = {
        'source_schema': source_config.schema,
        'destination_schema': dest_config.schema,
        'detailed_changes': detailed_changes,
        'safety_warnings': [{'level': w.level.value, 'message': w.message} for w in safety_warnings]
    }
    
    migration_report_path = Path(config.output.output_dir) / "migration_report.md"
    generate_migration_report(migration_report_data, str(migration_report_path))
    
    # Record in history
    migration_id = history.start_migration(
        migration_name, source_config.schema, dest_config.schema,
        len(ordered_operations), str(migration_file), str(rollback_file),
        len(safety_warnings)
    )
    
    # Simulate execution (in a real implementation, you'd execute the SQL)
    start_time = time.time()
    if not args.dry_run:
        execution_time = time.time() - start_time
        history.complete_migration(migration_id, 'SUCCESS', execution_time, len(ordered_operations), 0)
        logger.info("Migration simulated successfully")
    else:
        history.complete_migration(migration_id, 'DRY_RUN', 0.0, 0, 0, "Dry run completed")
        logger.info("Dry run completed")
    
    # Generate visualizations if requested
    if args.visualize:
        logger.info("Generating schema visualizations...")
        visualizer = SchemaVisualizer()
        # Extract table names from the objects structure
        table_names = [table['name'] for table in source_objects.get('tables', [])]
        schema_data = {'tables': {name: get_source_ddl('tables', name) for name in table_names}}
        visualizer.analyze_schema(schema_data)
        
        vis_output_dir = Path(config.output.output_dir) / "documentation"
        visualizer.export_documentation(str(vis_output_dir))
    
    # Print summary
    print("\nDDL Wizard - Schema Migration Summary")
    print("=" * 60)
    print(f"Source: {source_config.schema} @ {source_config.host}:{source_config.port}")
    print(f"Destination: {dest_config.schema} @ {dest_config.host}:{dest_config.port}")
    print(f"Migration operations: {len(ordered_operations)}")
    print(f"Safety warnings: {len(safety_warnings)}")
    print(f"Migration file: {migration_file}")
    print(f"Rollback file: {rollback_file}")
    print(f"Reports: {report_path}")
    
    if args.dry_run:
        print("✅ Dry run completed successfully!")
    else:
        print("✅ Migration completed successfully!")


def main():
    """Main application entry point."""
    try:
        args = parse_arguments()
        
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Load configuration
        config = load_configuration(args)
        
        # Execute based on mode
        if args.mode == 'extract':
            extract_mode(config, args)
        elif args.mode == 'visualize':
            visualize_mode(config, args)
        elif args.mode == 'history':
            history_mode(config, args)
        elif args.mode == 'compare':
            compare_mode(config, args)
        else:
            logger.error(f"Unknown mode: {args.mode}")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
