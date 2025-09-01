"""
Schema comparison and migration SQL generation for DDL Wizard.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional
from difflib import unified_diff
from pathlib import Path
from ddl_analyzer import DDLAnalyzer, TableStructure
from alter_generator import AlterStatementGenerator

logger = logging.getLogger(__name__)


class SchemaComparator:
    """Compares schemas and generates migration SQL."""
    
    def __init__(self):
        self.ddl_analyzer = DDLAnalyzer()
    
    def compare_objects(self, source_objects: Dict, dest_objects: Dict) -> Dict[str, Dict]:
        """Compare database objects between source and destination."""
        comparison_result = {}
        
        all_object_types = set(source_objects.keys()) | set(dest_objects.keys())
        
        for object_type in all_object_types:
            source_set = {obj['name'] for obj in source_objects.get(object_type, [])}
            dest_set = {obj['name'] for obj in dest_objects.get(object_type, [])}
            
            comparison_result[object_type] = {
                'only_in_source': source_set - dest_set,
                'only_in_dest': dest_set - source_set,
                'in_both': source_set & dest_set,
                'source_objects': {obj['name']: obj for obj in source_objects.get(object_type, [])},
                'dest_objects': {obj['name']: obj for obj in dest_objects.get(object_type, [])}
            }
            
            logger.debug(f"{object_type}: {len(source_set)} source, {len(dest_set)} dest, "
                        f"{len(comparison_result[object_type]['only_in_source'])} only in source, "
                        f"{len(comparison_result[object_type]['only_in_dest'])} only in dest")
        
        return comparison_result
    
    def analyze_table_differences(self, table_name: str, source_ddl: str, dest_ddl: str) -> List[Dict]:
        """Analyze structural differences between two table DDL statements."""
        try:
            source_structure = self.ddl_analyzer.parse_create_table(source_ddl)
            dest_structure = self.ddl_analyzer.parse_create_table(dest_ddl)
            
            differences = self.ddl_analyzer.compare_table_structures(source_structure, dest_structure)
            
            logger.debug(f"Table `{table_name}`: Found {len(differences)} structural differences")
            return differences
            
        except Exception as e:
            logger.error(f"Failed to analyze table differences for `{table_name}`: {e}")
            return []
    
    def compare_ddl_content(self, source_ddl: str, dest_ddl: str, object_name: str) -> Dict:
        """Compare DDL content between source and destination."""
        # Normalize DDL for comparison (remove schema names, formatting differences)
        source_normalized = self._normalize_ddl(source_ddl)
        dest_normalized = self._normalize_ddl(dest_ddl)
        
        if source_normalized == dest_normalized:
            return {'is_different': False, 'diff': None}
        
        # Generate unified diff
        diff_lines = list(unified_diff(
            dest_normalized.splitlines(keepends=True),
            source_normalized.splitlines(keepends=True),
            fromfile=f"dest/{object_name}",
            tofile=f"source/{object_name}",
            lineterm=''
        ))
        
        return {
            'is_different': True,
            'diff': ''.join(diff_lines)
        }
    
    def _normalize_ddl(self, ddl: str) -> str:
        """Normalize DDL for comparison."""
        if not ddl:
            return ""
        
        # Remove comments
        lines = []
        for line in ddl.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        # Join and normalize whitespace
        normalized = ' '.join(lines)
        normalized = ' '.join(normalized.split())  # Normalize whitespace
        
        return normalized.lower()
    
    def generate_migration_sql(self, comparison: Dict, source_ddl_func, dest_ddl_func, 
                             source_schema: str, dest_schema: str) -> str:
        """Generate migration SQL to sync destination with source."""
        migration_lines = [
            "-- DDL Wizard Migration Script",
            f"-- Source Schema: {source_schema}",
            f"-- Destination Schema: {dest_schema}",
            f"-- Generated: {self._get_timestamp()}",
            "",
            "-- WARNING: Review this script carefully before executing!",
            "-- This script will modify the destination database structure.",
            "",
            "SET FOREIGN_KEY_CHECKS = 0;",
            ""
        ]
        
        # Initialize ALTER statement generator
        alter_generator = AlterStatementGenerator(dest_schema)
        
        # Process in order: tables, functions, procedures, triggers, events
        object_order = ['tables', 'functions', 'procedures', 'triggers', 'events']
        
        for object_type in object_order:
            if object_type not in comparison:
                continue
                
            comp = comparison[object_type]
            migration_lines.extend(self._generate_type_migration(
                object_type, comp, source_ddl_func, dest_ddl_func, dest_schema, alter_generator
            ))
        
        migration_lines.extend([
            "",
            "SET FOREIGN_KEY_CHECKS = 1;",
            "",
            "-- Migration script completed."
        ])
        
        return '\n'.join(migration_lines)
    
    def _generate_type_migration(self, object_type: str, comparison: Dict, 
                               source_ddl_func, dest_ddl_func, dest_schema: str, 
                               alter_generator: AlterStatementGenerator) -> List[str]:
        """Generate migration SQL for a specific object type."""
        lines = []
        
        # Check if there are any changes needed
        has_changes = (comparison['only_in_source'] or comparison['only_in_dest'] or 
                      any(self._has_ddl_differences(obj_name, object_type, source_ddl_func, dest_ddl_func) 
                          for obj_name in comparison['in_both']))
        
        if not has_changes:
            return lines
        
        lines.append(f"-- {object_type.upper()} CHANGES")
        lines.append("-" * 50)
        
        # Drop objects that exist only in destination
        for obj_name in comparison['only_in_dest']:
            drop_sql = self._generate_drop_statement(object_type, obj_name, dest_schema)
            if drop_sql:
                lines.append(f"-- Drop {object_type[:-1]} that exists only in destination")
                lines.append(drop_sql)
                lines.append("")
        
        # Create objects that exist only in source
        for obj_name in comparison['only_in_source']:
            source_ddl = source_ddl_func(object_type, obj_name)
            if source_ddl:
                create_sql = self._adapt_ddl_for_destination(source_ddl, dest_schema)
                lines.append(f"-- Create {object_type[:-1]} from source")
                lines.append(create_sql + ";")
                lines.append("")
        
        # Handle objects that exist in both but are different
        for obj_name in comparison['in_both']:
            source_ddl = source_ddl_func(object_type, obj_name)
            dest_ddl = dest_ddl_func(object_type, obj_name)
            
            if object_type == 'tables' and source_ddl and dest_ddl:
                # For tables, analyze structural differences and generate ALTER statements
                differences = self.analyze_table_differences(obj_name, source_ddl, dest_ddl)
                
                if differences:
                    lines.append(f"-- Modify table: {obj_name}")
                    
                    # Generate detailed difference report
                    diff_report = alter_generator.generate_table_differences_report(obj_name, differences)
                    for report_line in diff_report.split('\n'):
                        lines.append(f"-- {report_line}")
                    lines.append("")
                    
                    # Generate ALTER statements
                    alter_statements = alter_generator.generate_alter_statements(obj_name, differences)
                    for stmt in alter_statements:
                        lines.append(stmt + ";")
                        lines.append("")
            
            elif self._has_ddl_differences(obj_name, object_type, source_ddl_func, dest_ddl_func):
                # For non-table objects, use drop/recreate approach
                lines.append(f"-- Update {object_type[:-1]}: {obj_name}")
                
                # For functions, procedures, triggers, events - drop and recreate
                drop_sql = self._generate_drop_statement(object_type, obj_name, dest_schema)
                if drop_sql:
                    lines.append(drop_sql)
                
                if source_ddl:
                    create_sql = self._adapt_ddl_for_destination(source_ddl, dest_schema)
                    lines.append(create_sql + ";")
                    lines.append("")
        
        lines.append("")
        return lines
    
    def _has_ddl_differences(self, obj_name: str, object_type: str, source_ddl_func, dest_ddl_func) -> bool:
        """Check if DDL differs between source and destination."""
        source_ddl = source_ddl_func(object_type, obj_name)
        dest_ddl = dest_ddl_func(object_type, obj_name)
        
        comparison = self.compare_ddl_content(source_ddl, dest_ddl, obj_name)
        return comparison['is_different']
    
    def _generate_drop_statement(self, object_type: str, obj_name: str, schema: str) -> str:
        """Generate DROP statement for an object."""
        if object_type == 'tables':
            return f"DROP TABLE IF EXISTS `{schema}`.`{obj_name}`;"
        elif object_type == 'functions':
            return f"DROP FUNCTION IF EXISTS `{schema}`.`{obj_name}`;"
        elif object_type == 'procedures':
            return f"DROP PROCEDURE IF EXISTS `{schema}`.`{obj_name}`;"
        elif object_type == 'triggers':
            return f"DROP TRIGGER IF EXISTS `{schema}`.`{obj_name}`;"
        elif object_type == 'events':
            return f"DROP EVENT IF EXISTS `{schema}`.`{obj_name}`;"
        return ""
    
    def _adapt_ddl_for_destination(self, ddl: str, dest_schema: str) -> str:
        """Adapt DDL for destination schema."""
        # Basic schema replacement - might need more sophisticated logic
        # This is a simplified version
        if not ddl:
            return ""
        
        # Remove any existing schema qualifiers and replace with destination schema
        # This is a basic implementation - production code would need more robust parsing
        adapted_ddl = ddl.strip()
        
        # Remove trailing semicolon if present
        if adapted_ddl.endswith(';'):
            adapted_ddl = adapted_ddl[:-1]
        
        return adapted_ddl
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for migration script."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def generate_comparison_report(self, comparison: Dict, source_ddl_func, dest_ddl_func) -> str:
        """Generate a human-readable comparison report."""
        report_lines = [
            "DDL Wizard Schema Comparison Report",
            "=" * 40,
            ""
        ]
        
        # Initialize ALTER statement generator for detailed reporting
        alter_generator = AlterStatementGenerator("destination")
        
        for object_type, comp in comparison.items():
            report_lines.append(f"{object_type.upper()}:")
            report_lines.append(f"  Only in source: {len(comp['only_in_source'])}")
            if comp['only_in_source']:
                for obj in sorted(comp['only_in_source']):
                    report_lines.append(f"    + {obj}")
            
            report_lines.append(f"  Only in destination: {len(comp['only_in_dest'])}")
            if comp['only_in_dest']:
                for obj in sorted(comp['only_in_dest']):
                    report_lines.append(f"    - {obj}")
            
            # For objects in both, show detailed differences for tables
            different_objects = []
            for obj_name in comp['in_both']:
                if object_type == 'tables':
                    source_ddl = source_ddl_func(object_type, obj_name)
                    dest_ddl = dest_ddl_func(object_type, obj_name)
                    
                    if source_ddl and dest_ddl:
                        differences = self.analyze_table_differences(obj_name, source_ddl, dest_ddl)
                        if differences:
                            different_objects.append((obj_name, differences))
                else:
                    if self._has_ddl_differences(obj_name, object_type, source_ddl_func, dest_ddl_func):
                        different_objects.append((obj_name, None))
            
            report_lines.append(f"  In both schemas: {len(comp['in_both'])}")
            if different_objects:
                report_lines.append(f"  With differences: {len(different_objects)}")
                for obj_name, differences in different_objects:
                    if object_type == 'tables' and differences:
                        diff_report = alter_generator.generate_table_differences_report(obj_name, differences)
                        for line in diff_report.split('\n'):
                            report_lines.append(f"    {line}")
                    else:
                        report_lines.append(f"    ~ {obj_name}")
            
            report_lines.append("")
        
        return '\n'.join(report_lines)
