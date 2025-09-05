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

from .utils.database import DatabaseManager, DatabaseConfig
from .utils.config import DDLWizardConfig
from .utils.interactive import InteractiveModeManager
from .core import DDLWizardCore, run_complete_migration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ddl_wizard.log')
    ]
)
logger = logging.getLogger(__name__)


def generate_detailed_rollback_sql(comparison: Dict, source_objects: Dict, dest_objects: Dict, alter_generator, get_source_ddl, get_dest_ddl) -> List[str]:
    """Generate detailed rollback SQL for all schema changes."""
    rollback_lines = []
    
    # Add header comment with proper formatting similar to migration script
    from datetime import datetime
    rollback_lines.extend([
        "-- DDL Wizard Rollback Script",
        f"-- Source Schema: {getattr(alter_generator, 'dest_schema', 'unknown')}",
        f"-- Destination Schema: {getattr(alter_generator, 'dest_schema', 'unknown')}",
        f"-- Generated: {datetime.now().isoformat()}",
        "",
        "-- WARNING: Review this script carefully before executing!",
        "-- This script will revert changes made by the migration script.",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
        "-- Detailed rollback for all schema changes",
        ""
    ])
    
    # Process tables that exist in both and may have structural differences
    if 'tables' in comparison:
        tables_comparison = comparison['tables']
        
        # Handle tables that were dropped in migration (only in dest - need to be recreated)
        for table_name in tables_comparison.get('only_in_dest', []):
            try:
                dest_ddl = get_dest_ddl('tables', table_name)
                if dest_ddl:
                    rollback_lines.append(f"-- Rollback table drop: {table_name}")
                    rollback_lines.append(dest_ddl + ";")
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to recreate table {table_name}: {str(e)}")
                continue
        
        # Handle tables that were created in migration (only in source - need to be dropped)
        for table_name in tables_comparison.get('only_in_source', []):
            try:
                rollback_lines.append(f"-- Rollback table creation: {table_name}")
                rollback_lines.append(f"DROP TABLE IF EXISTS `{table_name}`;")
                rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to drop table {table_name}: {str(e)}")
                continue
        
        # Handle tables that exist in both and may have structural differences
        for table_name in comparison['tables'].get('in_both', []):
            try:
                # Fetch DDL directly from the database connections
                source_ddl = get_source_ddl('tables', table_name)
                dest_ddl = get_dest_ddl('tables', table_name) 
                
                if source_ddl and dest_ddl:
                    # Use the comparator to analyze table differences
                    # For rollback, we use the original migration differences (source to dest)
                    # and generate inverse operations to restore the original state
                    from schema_comparator import SchemaComparator
                    temp_comparator = SchemaComparator()
                    differences = temp_comparator.analyze_table_differences(table_name, source_ddl, dest_ddl)
                    
                    if differences:
                        # Generate rollback statements for this table
                        dest_ddl = get_dest_ddl('tables', table_name) if table_name in tables_comparison.get('in_both', []) else ''
                        rollback_statements = alter_generator.generate_rollback_statements(table_name, differences, dest_ddl)
                        for stmt in rollback_statements:
                            rollback_lines.append(stmt + ";")
                        rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process table {table_name}: {str(e)}")
                continue
    
    # Process procedures that exist in both and may have differences
    if 'procedures' in comparison:
        procedures_comparison = comparison['procedures']
        
        for proc_name in procedures_comparison.get('in_both', []):
            try:
                # Get DDL for both versions
                source_ddl = get_source_ddl('procedures', proc_name)
                dest_ddl = get_dest_ddl('procedures', proc_name)
                
                # Only generate rollback if there are actual differences
                source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                
                if source_normalized != dest_normalized and dest_ddl:
                    rollback_lines.append(f"-- Rollback procedure: {proc_name}")
                    rollback_lines.append(f"DROP PROCEDURE IF EXISTS `{proc_name}`;")
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
                    
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process procedure {proc_name}: {str(e)}")
                continue
        
        # Handle procedures that are only in source (created in migration)
        for proc_name in procedures_comparison.get('only_in_source', []):
            try:
                # Drop the created procedure
                rollback_lines.append(f"-- Rollback creation of procedure: {proc_name}")
                rollback_lines.append(f"DROP PROCEDURE IF EXISTS `{proc_name}`;")
                rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process procedure {proc_name}: {str(e)}")
                continue
        
        # Handle procedures that are only in destination (dropped in migration)
        for proc_name in procedures_comparison.get('only_in_dest', []):
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
        
        for func_name in functions_comparison.get('in_both', []):
            try:
                # Get DDL for both versions
                source_ddl = get_source_ddl('functions', func_name)
                dest_ddl = get_dest_ddl('functions', func_name)
                
                # Only generate rollback if there are actual differences
                source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                
                if source_normalized != dest_normalized and dest_ddl:
                    rollback_lines.append(f"-- Rollback function: {func_name}")
                    rollback_lines.append(f"DROP FUNCTION IF EXISTS `{func_name}`;")
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
                    
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process function {func_name}: {str(e)}")
                continue
        
        # Handle functions that are only in source (created in migration)
        for func_name in functions_comparison.get('only_in_source', []):
            try:
                # Drop the created function
                rollback_lines.append(f"-- Rollback creation of function: {func_name}")
                rollback_lines.append(f"DROP FUNCTION IF EXISTS `{func_name}`;")
                rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process function {func_name}: {str(e)}")
                continue
        
        # Handle functions that are only in destination (dropped in migration)
        for func_name in functions_comparison.get('only_in_dest', []):
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
    
    # Process triggers that exist in both and may have differences  
    if 'triggers' in comparison:
        triggers_comparison = comparison['triggers']
        
        for trigger_name in triggers_comparison.get('in_both', []):
            try:
                # Get DDL for both versions
                source_ddl = get_source_ddl('triggers', trigger_name)
                dest_ddl = get_dest_ddl('triggers', trigger_name)
                
                # Only generate rollback if there are actual differences
                source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                
                if source_normalized != dest_normalized and dest_ddl:
                    rollback_lines.append(f"-- Rollback trigger: {trigger_name}")
                    rollback_lines.append(f"DROP TRIGGER IF EXISTS `{trigger_name}`;")
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
                    
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process trigger {trigger_name}: {str(e)}")
                continue
        
        # Handle triggers that are only in source (created in migration)
        for trigger_name in triggers_comparison.get('only_in_source', []):
            try:
                # Drop the created trigger
                rollback_lines.append(f"-- Rollback creation of trigger: {trigger_name}")
                rollback_lines.append(f"DROP TRIGGER IF EXISTS `{trigger_name}`;")
                rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process trigger {trigger_name}: {str(e)}")
                continue
        
        # Handle triggers that are only in destination (dropped in migration)
        for trigger_name in triggers_comparison.get('only_in_dest', []):
            try:
                dest_ddl = get_dest_ddl('triggers', trigger_name)
                if dest_ddl:
                    rollback_lines.append(f"-- Rollback deletion of trigger: {trigger_name}")
                    rollback_lines.append("DELIMITER $$")
                    rollback_lines.append(dest_ddl + "$$")
                    rollback_lines.append("DELIMITER ;")
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to restore trigger {trigger_name}: {str(e)}")
                continue

    # Process events that exist in both and may have differences  
    if 'events' in comparison:
        events_comparison = comparison['events']
        
        for event_name in events_comparison.get('in_both', []):
            try:
                # Get DDL for both versions
                source_ddl = get_source_ddl('events', event_name)
                dest_ddl = get_dest_ddl('events', event_name)
                
                # Only generate rollback if there are actual differences
                source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                
                if source_normalized != dest_normalized and dest_ddl:
                    rollback_lines.append(f"-- Rollback event: {event_name}")
                    rollback_lines.append(f"DROP EVENT IF EXISTS `{event_name}`;")
                    # Apply delimiter adaptation for Events (adds DELIMITER $$ / DELIMITER ;)
                    from schema_comparator import SchemaComparator
                    temp_comparator = SchemaComparator()
                    adapted_ddl = temp_comparator._adapt_ddl_for_destination(dest_ddl, alter_generator.dest_schema)
                    rollback_lines.append(adapted_ddl)
                    rollback_lines.append("")
                    
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process event {event_name}: {str(e)}")
                continue
        
        # Handle events that are only in source (created in migration)
        for event_name in events_comparison.get('only_in_source', []):
            try:
                # Drop the created event
                rollback_lines.append(f"-- Rollback creation of event: {event_name}")
                rollback_lines.append(f"DROP EVENT IF EXISTS `{event_name}`;")
                rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process event {event_name}: {str(e)}")
                continue
        
        # Handle events that are only in destination (dropped in migration)
        for event_name in events_comparison.get('only_in_dest', []):
            try:
                dest_ddl = get_dest_ddl('events', event_name)
                if dest_ddl:
                    rollback_lines.append(f"-- Rollback deletion of event: {event_name}")
                    # Apply delimiter adaptation for Events (adds DELIMITER $$ / DELIMITER ;)
                    from schema_comparator import SchemaComparator
                    temp_comparator = SchemaComparator()
                    adapted_ddl = temp_comparator._adapt_ddl_for_destination(dest_ddl, alter_generator.dest_schema)
                    rollback_lines.append(adapted_ddl)
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to restore event {event_name}: {str(e)}")
                continue

    # Process views that exist in both and may have differences  
    if 'views' in comparison:
        views_comparison = comparison['views']
        
        for view_name in views_comparison.get('in_both', []):
            try:
                # Get DDL for both versions
                source_ddl = get_source_ddl('views', view_name)
                dest_ddl = get_dest_ddl('views', view_name)
                
                # Only generate rollback if there are actual differences
                source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                
                if source_normalized != dest_normalized and dest_ddl:
                    rollback_lines.append(f"-- Rollback view: {view_name}")
                    rollback_lines.append(f"DROP VIEW IF EXISTS `{view_name}`;")
                    rollback_lines.append(dest_ddl + ";")
                    rollback_lines.append("")
                    
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process view {view_name}: {str(e)}")
                continue
        
        # Handle views that are only in source (created in migration)
        for view_name in views_comparison.get('only_in_source', []):
            try:
                # Drop the created view
                rollback_lines.append(f"-- Rollback creation of view: {view_name}")
                rollback_lines.append(f"DROP VIEW IF EXISTS `{view_name}`;")
                rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process view {view_name}: {str(e)}")
                continue
        
        # Handle views that are only in destination (dropped in migration)
        for view_name in views_comparison.get('only_in_dest', []):
            try:
                dest_ddl = get_dest_ddl('views', view_name)
                if dest_ddl:
                    rollback_lines.append(f"-- Rollback deletion of view: {view_name}")
                    rollback_lines.append(dest_ddl + ";")
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to restore view {view_name}: {str(e)}")
                continue

    # Process sequences that exist in both and may have differences  
    if 'sequences' in comparison:
        sequences_comparison = comparison['sequences']
        
        for sequence_name in sequences_comparison.get('in_both', []):
            try:
                # Get DDL for both versions
                source_ddl = get_source_ddl('sequences', sequence_name)
                dest_ddl = get_dest_ddl('sequences', sequence_name)
                
                # Only generate rollback if there are actual differences
                source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                
                if source_normalized != dest_normalized and dest_ddl:
                    rollback_lines.append(f"-- Rollback sequence: {sequence_name}")
                    rollback_lines.append(f"DROP SEQUENCE IF EXISTS `{sequence_name}`;")
                    rollback_lines.append(dest_ddl + ";")
                    rollback_lines.append("")
                    
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process sequence {sequence_name}: {str(e)}")
                continue
        
        # Handle sequences that are only in source (created in migration)
        for sequence_name in sequences_comparison.get('only_in_source', []):
            try:
                # Drop the created sequence
                rollback_lines.append(f"-- Rollback creation of sequence: {sequence_name}")
                rollback_lines.append(f"DROP SEQUENCE IF EXISTS `{sequence_name}`;")
                rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to process sequence {sequence_name}: {str(e)}")
                continue
        
        # Handle sequences that are only in destination (dropped in migration)
        for sequence_name in sequences_comparison.get('only_in_dest', []):
            try:
                dest_ddl = get_dest_ddl('sequences', sequence_name)
                if dest_ddl:
                    rollback_lines.append(f"-- Rollback deletion of sequence: {sequence_name}")
                    rollback_lines.append(dest_ddl + ";")
                    rollback_lines.append("")
            except Exception as e:
                rollback_lines.append(f"-- ERROR: Failed to restore sequence {sequence_name}: {str(e)}")
                continue
    
    # Add closing statements
    rollback_lines.extend([
        "",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
        "-- Rollback script completed."
    ])
    
    return rollback_lines


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments with backward compatibility."""
    # Check if the old --mode syntax is being used
    import sys
    if '--mode' in sys.argv:
        return parse_arguments_legacy()
    else:
        return parse_arguments_new()


def parse_arguments_legacy() -> argparse.Namespace:
    """Parse command line arguments using the legacy --mode syntax."""
    parser = argparse.ArgumentParser(
        description="DDL Wizard - Database DDL Extraction and Comparison Tool (Legacy Mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Legacy global arguments
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--profile', help='Configuration profile to use')
    parser.add_argument('--output-dir', default='./ddl_output', help='Output directory for generated files')
    parser.add_argument('--mode', choices=['compare', 'extract', 'visualize', 'history'], 
                       required=True, help='Operation mode')
    
    # Database connection arguments
    parser.add_argument('--source-host', help='Source database host')
    parser.add_argument('--source-port', type=int, default=3306, help='Source database port')
    parser.add_argument('--source-user', help='Source database username')
    parser.add_argument('--source-password', help='Source database password')
    parser.add_argument('--source-schema', help='Source database schema')
    parser.add_argument('--dest-host', help='Destination database host')
    parser.add_argument('--dest-port', type=int, default=3306, help='Destination database port')
    parser.add_argument('--dest-user', help='Destination database username')
    parser.add_argument('--dest-password', help='Destination database password')
    parser.add_argument('--dest-schema', help='Destination database schema')
    
    # Legacy options
    parser.add_argument('--visualize', action='store_true', help='Generate schema visualizations (legacy)')
    parser.add_argument('--skip-safety-checks', action='store_true', help='Skip safety analysis')
    parser.add_argument('--interactive', action='store_true', help='Enable interactive mode')
    parser.add_argument('--auto-approve', action='store_true', help='Auto-approve migrations')
    parser.add_argument('--dry-run', action='store_true', help='Generate files without executing')
    parser.add_argument('--limit', type=int, default=20, help='Number of records to show (history mode)')
    
    args = parser.parse_args()
    
    # Convert legacy --visualize to --enable-visualization
    if hasattr(args, 'visualize') and args.visualize:
        args.enable_visualization = True
    else:
        args.enable_visualization = getattr(args, 'enable_visualization', True)
    
    return args


def parse_arguments_new() -> argparse.Namespace:
    """Parse command line arguments using the new subcommand syntax."""
    parser = argparse.ArgumentParser(
        description="DDL Wizard - Database DDL Extraction and Comparison Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two databases and generate migration
  python main.py compare --source-host localhost --source-user root --source-schema db1 \\
                              --dest-host localhost --dest-user root --dest-schema db2
  
  # Use configuration file
  python main.py compare --config config/ddl_wizard_config.yaml
  
  # Extract DDL from database
  python main.py extract --source-host localhost --source-user root --source-schema mydb
  
  # Show migration history
  python main.py history
        """
    )
    
    # Global arguments
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--profile', help='Configuration profile to use')
    parser.add_argument('--output-dir', default='./ddl_output', help='Output directory for generated files')
    
    # Create subparsers for different modes
    subparsers = parser.add_subparsers(dest='mode', help='Available modes')
    
    # Compare mode
    compare_parser = subparsers.add_parser('compare', help='Compare schemas and generate migration')
    compare_parser.add_argument('--source-host', help='Source database host')
    compare_parser.add_argument('--source-port', type=int, default=3306, help='Source database port')
    compare_parser.add_argument('--source-user', help='Source database username')
    compare_parser.add_argument('--source-password', help='Source database password')
    compare_parser.add_argument('--source-schema', help='Source database schema')
    compare_parser.add_argument('--dest-host', help='Destination database host')
    compare_parser.add_argument('--dest-port', type=int, default=3306, help='Destination database port')
    compare_parser.add_argument('--dest-user', help='Destination database username')
    compare_parser.add_argument('--dest-password', help='Destination database password')
    compare_parser.add_argument('--dest-schema', help='Destination database schema')
    compare_parser.add_argument('--skip-safety-checks', action='store_true', help='Skip safety analysis')
    compare_parser.add_argument('--enable-visualization', action='store_true', default=True, 
                               help='Generate schema visualizations (default: True)')
    compare_parser.add_argument('--interactive', action='store_true', help='Enable interactive mode')
    compare_parser.add_argument('--auto-approve', action='store_true', help='Auto-approve migrations')
    compare_parser.add_argument('--dry-run', action='store_true', help='Generate files without executing')
    
    # Extract mode
    extract_parser = subparsers.add_parser('extract', help='Extract DDL from database')
    extract_parser.add_argument('--source-host', required=True, help='Database host')
    extract_parser.add_argument('--source-port', type=int, default=3306, help='Database port')
    extract_parser.add_argument('--source-user', required=True, help='Database username')
    extract_parser.add_argument('--source-password', help='Database password')
    extract_parser.add_argument('--source-schema', required=True, help='Database schema')
    
    # Visualize mode
    visualize_parser = subparsers.add_parser('visualize', help='Generate schema visualizations')
    visualize_parser.add_argument('--source-host', required=True, help='Database host')
    visualize_parser.add_argument('--source-port', type=int, default=3306, help='Database port')
    visualize_parser.add_argument('--source-user', required=True, help='Database username')
    visualize_parser.add_argument('--source-password', help='Database password')
    visualize_parser.add_argument('--source-schema', required=True, help='Database schema')
    
    # History mode
    history_parser = subparsers.add_parser('history', help='Show migration history')
    history_parser.add_argument('--limit', type=int, default=20, help='Number of records to show')
    
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
        
        if hasattr(args, 'source_host') and args.source_host and args.source_user and args.source_schema:
            source_db = DatabaseConnection(
                host=args.source_host,
                port=args.source_port,
                user=args.source_user,
                password=args.source_password if args.source_password else "",
                schema=args.source_schema
            )
        
        if hasattr(args, 'dest_host') and args.dest_host and args.dest_user and args.dest_schema:
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
            migration_file="migration.sql",
            rollback_file="rollback.sql"
        )
        
        config = DDLWizardConfig(
            source=source_db,
            destination=dest_db,
            safety=safety_settings,
            output=output_settings
        )
        
        return config


def extract_mode(config: DDLWizardConfig, args: argparse.Namespace):
    """Extract DDL objects from database."""
    logger.info("Running in extract mode...")
    
    if not config.source.host:
        logger.error("Source database configuration required for extract mode")
        sys.exit(1)
    
    try:
        # Create core instance
        core = DDLWizardCore(config)
        
        # Connect to source database
        source_config = DatabaseConfig(
            host=config.source.host,
            port=config.source.port,
            user=config.source.user,
            password=config.source.password,
            schema=config.source.schema
        )
        
        # Initialize dummy destination for core functionality
        dest_config = DatabaseConfig("dummy", 3306, "dummy", "", "dummy")
        
        if not core.connect_databases(source_config, dest_config):
            logger.error("Failed to connect to source database")
            sys.exit(1)
        
        # Initialize git repository
        if not core.initialize_git_repository(config.output.output_dir):
            logger.error("Failed to initialize git repository")
            sys.exit(1)
        
        # Extract schema objects
        source_objects, _ = core.extract_schema_objects()
        
        logger.info(f"Extracted {len(source_objects)} DDL objects from {source_config.schema}")
        for object_type, objects in source_objects.items():
            logger.info(f"  {object_type}: {len(objects)} objects")
        
        logger.info(f"DDL objects saved to {config.output.output_dir}")
        
    except Exception as e:
        logger.error(f"Extract mode failed: {e}")
        sys.exit(1)


def visualize_mode(config: DDLWizardConfig, args: argparse.Namespace):
    """Generate schema visualizations."""
    logger.info("Running in visualize mode...")
    
    if not config.source.host:
        logger.error("Source database configuration required for visualize mode")
        sys.exit(1)
    
    try:
        # Create core instance
        core = DDLWizardCore(config)
        
        # Connect to source database
        source_config = DatabaseConfig(
            host=config.source.host,
            port=config.source.port,
            user=config.source.user,
            password=config.source.password,
            schema=config.source.schema
        )
        
        # Initialize dummy destination for core functionality
        dest_config = DatabaseConfig("dummy", 3306, "dummy", "", "dummy")
        
        if not core.connect_databases(source_config, dest_config):
            logger.error("Failed to connect to source database")
            sys.exit(1)
        
        # Extract schema objects
        source_objects, _ = core.extract_schema_objects()
        
        # Generate visualizations
        core.generate_schema_visualization(source_objects, config.output.output_dir)
        
        logger.info("Schema visualizations generated successfully!")
        
    except Exception as e:
        logger.error(f"Visualize mode failed: {e}")
        sys.exit(1)


def history_mode(config: DDLWizardConfig, args: argparse.Namespace):
    """Show migration history."""
    logger.info("Running in history mode...")
    
    try:
        from migration_history import MigrationHistory
        
        history = MigrationHistory()
        migrations = history.get_migration_history(limit=args.limit)
        
        if not migrations:
            print("No migration history found.")
            return
        
        print(f"\nMigration History (Last {len(migrations)} migrations):")
        print("-" * 80)
        
        for migration in migrations:
            print(f"ID: {migration['id']}")
            print(f"Name: {migration['migration_name']}")
            print(f"Source: {migration['source_schema']} → Destination: {migration['destination_schema']}")
            print(f"Status: {migration['status']}")
            print(f"Operations: {migration['operation_count']}")
            print(f"Started: {migration['start_time']}")
            if migration['end_time']:
                print(f"Completed: {migration['end_time']}")
            print("-" * 80)
        
        # Show summary statistics
        from collections import Counter
        
        statuses = [m['status'] for m in migrations]
        status_counts = Counter(statuses)
        
        print(f"\nSummary:")
        for status, count in status_counts.items():
            print(f"{status}: {count}")
        
        success_rate = (status_counts.get('SUCCESS', 0) / len(migrations)) * 100 if migrations else 0
        print(f"Success rate: {success_rate:.1f}%")
        
    except Exception as e:
        logger.error(f"History mode failed: {e}")
        sys.exit(1)


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
                
        print(f"\n✅ Schema comparison and migration generation completed successfully!")
        print(f"Migration ID: {results['migration_id']}")
        print(f"Operations: {results['operation_count']}")
        print(f"Safety warnings: {len(results['safety_warnings'])}")
        print(f"Migration file: {results['migration_file']}")
        print(f"Rollback file: {results['rollback_file']}")
        print(f"Migration report: {results['migration_report_file']}")
        
        if getattr(args, 'dry_run', False):
            print("✅ Dry run completed successfully!")
        else:
            print("✅ Migration analysis completed successfully!")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if getattr(args, 'verbose', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


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
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
