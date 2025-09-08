#!/usr/bin/env python3
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
from config_manager import DDLWizardConfig
from interactive_mode import InteractiveModeManager
from ddl_wizard_core import DDLWizardCore, run_complete_migration

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


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DDL Wizard - Database DDL Extraction and Comparison Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two databases and generate migration
  python ddl_wizard.py compare --source-host localhost --source-user root --source-schema db1 \\
                              --dest-host localhost --dest-user root --dest-schema db2
  
  # Use configuration file
  python ddl_wizard.py compare --config config.yaml
  
  # Extract DDL from database
  python ddl_wizard.py extract --source-host localhost --source-user root --source-schema mydb
  
  # Show migration history
  python ddl_wizard.py history
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
