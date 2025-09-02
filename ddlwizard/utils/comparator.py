"""
Schema Comparator for DDL Wizard.
Analyzes differences between source and destination schemas.
"""

import re
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class ChangeType(Enum):
    """Types of changes that can be detected in schema comparison."""
    ADD_COLUMN = "column_added"
    REMOVE_COLUMN = "column_removed"
    MODIFY_COLUMN = "column_modified"
    ADD_INDEX = "index_added"
    REMOVE_INDEX = "index_removed"
    MODIFY_INDEX = "index_modified"
    ADD_CONSTRAINT = "constraint_added"
    REMOVE_CONSTRAINT = "constraint_removed"
    MODIFY_CONSTRAINT = "constraint_modified"


class SchemaComparator:
    """Compares database schemas and identifies differences."""
    
    def __init__(self):
        """Initialize the schema comparator."""
        pass
    
    def analyze_table_differences(self, table_name: str, source_ddl: str, dest_ddl: str) -> List[Dict[str, Any]]:
        """
        Analyze differences between source and destination table DDL.
        
        Args:
            table_name: Name of the table being compared
            source_ddl: DDL of the source table
            dest_ddl: DDL of the destination table
            
        Returns:
            List of differences found
        """
        if not source_ddl or not dest_ddl:
            return []
        
        differences = []
        
        # Parse columns from both DDLs
        source_columns = self._parse_columns(source_ddl)
        dest_columns = self._parse_columns(dest_ddl)
        
        # Find column differences
        source_col_names = set(source_columns.keys())
        dest_col_names = set(dest_columns.keys())
        
        # Columns only in source (need to be added to dest to match source)
        for col_name in source_col_names - dest_col_names:
            differences.append({
                'type': ChangeType.ADD_COLUMN.value,
                'column_name': col_name,
                'column_definition': source_columns[col_name],
                'description': f"Add column '{col_name}'"
            })
        
        # Columns only in dest (need to be removed from dest to match source)
        for col_name in dest_col_names - source_col_names:
            differences.append({
                'type': ChangeType.REMOVE_COLUMN.value,
                'column_name': col_name,
                'column_definition': dest_columns[col_name],
                'description': f"Remove column '{col_name}'"
            })
        
        # Columns in both (check for modifications)
        for col_name in source_col_names & dest_col_names:
            source_def = source_columns[col_name].strip()
            dest_def = dest_columns[col_name].strip()
            
            if source_def != dest_def:
                differences.append({
                    'type': ChangeType.MODIFY_COLUMN.value,
                    'column_name': col_name,
                    'original_definition': source_def,
                    'new_definition': dest_def,
                    'description': f"Modify column '{col_name}'"
                })
        
        # Parse and compare indexes
        source_indexes = self._parse_indexes(source_ddl)
        dest_indexes = self._parse_indexes(dest_ddl)
        
        source_idx_names = set(source_indexes.keys())
        dest_idx_names = set(dest_indexes.keys())
        
        # Indexes only in source (need to be added)
        for idx_name in source_idx_names - dest_idx_names:
            differences.append({
                'type': ChangeType.ADD_INDEX.value,
                'index_name': idx_name,
                'index_definition': source_indexes[idx_name],
                'description': f"Add index '{idx_name}'"
            })
        
        # Indexes only in dest (need to be removed)
        for idx_name in dest_idx_names - source_idx_names:
            differences.append({
                'type': ChangeType.REMOVE_INDEX.value,
                'index_name': idx_name,
                'index_definition': dest_indexes[idx_name],
                'description': f"Remove index '{idx_name}'"
            })
        
        # Parse and compare foreign keys
        source_foreign_keys = self._parse_foreign_keys(source_ddl)
        dest_foreign_keys = self._parse_foreign_keys(dest_ddl)
        
        source_fk_names = set(source_foreign_keys.keys())
        dest_fk_names = set(dest_foreign_keys.keys())
        
        # Foreign keys only in source (need to be added)
        for fk_name in source_fk_names - dest_fk_names:
            differences.append({
                'type': ChangeType.ADD_CONSTRAINT.value,
                'constraint_name': fk_name,
                'constraint_definition': source_foreign_keys[fk_name],
                'description': f"Add foreign key constraint '{fk_name}'"
            })
        
        # Foreign keys only in dest (need to be removed)
        for fk_name in dest_fk_names - source_fk_names:
            differences.append({
                'type': ChangeType.REMOVE_CONSTRAINT.value,
                'constraint_name': fk_name,
                'constraint_definition': dest_foreign_keys[fk_name],
                'description': f"Remove foreign key constraint '{fk_name}'"
            })
        
        # Foreign keys in both (check for modifications)
        for fk_name in source_fk_names & dest_fk_names:
            source_def = source_foreign_keys[fk_name].strip()
            dest_def = dest_foreign_keys[fk_name].strip()
            
            if source_def != dest_def:
                differences.append({
                    'type': ChangeType.MODIFY_CONSTRAINT.value,
                    'constraint_name': fk_name,
                    'original_definition': dest_def,
                    'new_definition': source_def,
                    'description': f"Modify foreign key constraint '{fk_name}'"
                })
        
        return differences
    
    def _parse_columns(self, ddl: str) -> Dict[str, str]:
        """
        Parse column definitions from CREATE TABLE DDL.
        
        Args:
            ddl: The CREATE TABLE DDL statement
            
        Returns:
            Dictionary mapping column names to their definitions
        """
        columns = {}
        
        # Remove comments and normalize whitespace
        ddl_clean = re.sub(r'--[^\n]*', '', ddl)
        ddl_clean = re.sub(r'/\*.*?\*/', '', ddl_clean, flags=re.DOTALL)
        
        # Find the column definitions inside the CREATE TABLE statement
        create_match = re.search(r'CREATE\s+TABLE[^(]*\((.*)\)', ddl_clean, re.IGNORECASE | re.DOTALL)
        if not create_match:
            return columns
        
        columns_section = create_match.group(1)
        
        # Split by commas, but be careful about commas inside parentheses
        parts = self._split_sql_parts(columns_section)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # Skip constraints, keys, and indexes
            if re.match(r'^\s*(PRIMARY\s+KEY|UNIQUE|INDEX|KEY|CONSTRAINT|FOREIGN\s+KEY)', part, re.IGNORECASE):
                continue
            
            # Extract column name (first word, possibly quoted)
            col_match = re.match(r'^\s*`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s+(.+)', part)
            if col_match:
                col_name = col_match.group(1)
                col_def = col_match.group(2).strip()
                columns[col_name] = col_def
        
        return columns
    
    def _parse_indexes(self, ddl: str) -> Dict[str, str]:
        """
        Parse index definitions from CREATE TABLE DDL.
        
        Args:
            ddl: The CREATE TABLE DDL statement
            
        Returns:
            Dictionary mapping index names to their definitions
        """
        indexes = {}
        
        # Remove comments and normalize whitespace
        ddl_clean = re.sub(r'--[^\n]*', '', ddl)
        ddl_clean = re.sub(r'/\*.*?\*/', '', ddl_clean, flags=re.DOTALL)
        
        # Find the column definitions inside the CREATE TABLE statement
        create_match = re.search(r'CREATE\s+TABLE[^(]*\((.*)\)', ddl_clean, re.IGNORECASE | re.DOTALL)
        if not create_match:
            return indexes
        
        columns_section = create_match.group(1)
        
        # Split by commas, but be careful about commas inside parentheses
        parts = self._split_sql_parts(columns_section)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Skip foreign key constraints - they are handled separately
            if re.match(r'^\s*CONSTRAINT.*FOREIGN\s+KEY', part, re.IGNORECASE) or \
               re.match(r'^\s*FOREIGN\s+KEY', part, re.IGNORECASE):
                continue
            
            # Look for KEY or INDEX definitions
            key_match = re.match(r'^\s*(UNIQUE\s+)?(KEY|INDEX)\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*\((.*)\)', part, re.IGNORECASE)
            if key_match:
                unique_prefix = key_match.group(1) or ''
                index_type = key_match.group(2)
                index_name = key_match.group(3)
                index_columns = key_match.group(4)
                
                index_def = f"{unique_prefix}{index_type} `{index_name}` ({index_columns})"
                indexes[index_name] = index_def.strip()
        
        return indexes
    
    def _parse_foreign_keys(self, ddl: str) -> Dict[str, str]:
        """
        Parse foreign key constraint definitions from CREATE TABLE DDL.
        
        Args:
            ddl: The CREATE TABLE DDL statement
            
        Returns:
            Dictionary mapping foreign key names to their definitions
        """
        foreign_keys = {}
        
        # Remove comments and normalize whitespace
        ddl_clean = re.sub(r'--[^\n]*', '', ddl)
        ddl_clean = re.sub(r'/\*.*?\*/', '', ddl_clean, flags=re.DOTALL)
        
        # Find the column definitions inside the CREATE TABLE statement
        create_match = re.search(r'CREATE\s+TABLE[^(]*\((.*)\)', ddl_clean, re.IGNORECASE | re.DOTALL)
        if not create_match:
            return foreign_keys
        
        columns_section = create_match.group(1)
        
        # Split by commas, but be careful about commas inside parentheses
        parts = self._split_sql_parts(columns_section)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Look for CONSTRAINT ... FOREIGN KEY definitions
            constraint_fk_match = re.match(
                r'^\s*CONSTRAINT\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s+FOREIGN\s+KEY\s*\((.*?)\)\s+REFERENCES\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*\((.*?)\)(.*)$',
                part, re.IGNORECASE
            )
            if constraint_fk_match:
                fk_name = constraint_fk_match.group(1)
                local_columns = constraint_fk_match.group(2)
                ref_table = constraint_fk_match.group(3)
                ref_columns = constraint_fk_match.group(4)
                on_clauses = constraint_fk_match.group(5).strip()
                
                fk_def = f"CONSTRAINT `{fk_name}` FOREIGN KEY ({local_columns}) REFERENCES `{ref_table}` ({ref_columns})"
                if on_clauses:
                    fk_def += f" {on_clauses}"
                foreign_keys[fk_name] = fk_def.strip()
                continue
            
            # Look for inline FOREIGN KEY definitions (without CONSTRAINT)
            inline_fk_match = re.match(
                r'^\s*FOREIGN\s+KEY\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*\((.*?)\)\s+REFERENCES\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*\((.*?)\)(.*)$',
                part, re.IGNORECASE
            )
            if inline_fk_match:
                fk_name = inline_fk_match.group(1)
                local_columns = inline_fk_match.group(2)
                ref_table = inline_fk_match.group(3)
                ref_columns = inline_fk_match.group(4)
                on_clauses = inline_fk_match.group(5).strip()
                
                fk_def = f"FOREIGN KEY `{fk_name}` ({local_columns}) REFERENCES `{ref_table}` ({ref_columns})"
                if on_clauses:
                    fk_def += f" {on_clauses}"
                foreign_keys[fk_name] = fk_def.strip()
        
        return foreign_keys
    
    def _split_sql_parts(self, sql: str) -> List[str]:
        """
        Split SQL by commas, respecting parentheses nesting.
        
        Args:
            sql: SQL string to split
            
        Returns:
            List of SQL parts
        """
        parts = []
        current_part = ""
        paren_depth = 0
        
        for char in sql:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                parts.append(current_part.strip())
                current_part = ""
                continue
            
            current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    def compare_schemas(self, source_objects: Dict[str, List[Dict]], dest_objects: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Compare complete schemas and return differences.
        
        Args:
            source_objects: Source schema objects
            dest_objects: Destination schema objects
            
        Returns:
            Dictionary containing comparison results
        """
        comparison = {}
        
        # Compare each object type
        for obj_type in ['tables', 'procedures', 'functions', 'triggers', 'events']:
            source_names = {obj['name'] for obj in source_objects.get(obj_type, [])}
            dest_names = {obj['name'] for obj in dest_objects.get(obj_type, [])}
            
            comparison[obj_type] = {
                'only_in_source': list(source_names - dest_names),
                'only_in_dest': list(dest_names - source_names),
                'in_both': list(source_names & dest_names)
            }
        
        return comparison
    
    def _adapt_ddl_for_destination(self, ddl: str, dest_schema: str) -> str:
        """Adapt DDL for destination schema with proper delimiter handling."""
        if not ddl:
            return ""
        
        adapted_ddl = ddl.strip()
        
        # Check if this is a stored procedure, function, or trigger
        ddl_upper = adapted_ddl.upper()
        # Use regex to handle DEFINER clauses between CREATE and object type
        import re
        is_stored_object = bool(re.search(r'CREATE\s+(?:DEFINER[^)]*\)?\s+)?(FUNCTION|PROCEDURE|TRIGGER)', ddl_upper))
        
        if is_stored_object:
            # For stored procedures, functions, and triggers, we need to:
            # 1. Ensure proper semicolons within the body
            # 2. Wrap with DELIMITER commands
            
            # For stored objects, we don't modify semicolons - just wrap with DELIMITER
            # Remove trailing semicolon if present (will be replaced with $$)
            if adapted_ddl.endswith(';'):
                adapted_ddl = adapted_ddl[:-1]
            
            # Wrap with DELIMITER commands and add $$ terminator
            result = f"DELIMITER $$\n{adapted_ddl}$$\nDELIMITER ;"
            return result
        else:
            # For regular DDL (tables, etc.), ensure proper semicolon
            if not adapted_ddl.endswith(';'):
                adapted_ddl += ';'
            return adapted_ddl
    
    def compare_objects(self, source_objects: Dict[str, List[Dict]], dest_objects: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Compare database objects and return comparison results.
        This is an alias for compare_schemas for backward compatibility.
        
        Args:
            source_objects: Source database objects
            dest_objects: Destination database objects
            
        Returns:
            Dictionary containing comparison results
        """
        return self.compare_schemas(source_objects, dest_objects)
    
    def generate_migration_sql(self, comparison: Dict, get_source_ddl_func: Any, get_dest_ddl_func: Any,
                             source_schema: str, dest_schema: str) -> str:
        """
        Generate migration SQL from comparison results.
        
        Args:
            comparison: Schema comparison results
            get_source_ddl_func: Function to get source DDL
            get_dest_ddl_func: Function to get destination DDL
            source_schema: Source schema name
            dest_schema: Destination schema name
            
        Returns:
            Migration SQL script
        """
        from alter_generator import AlterStatementGenerator
        
        sql_lines = [
            "-- DDL Wizard Migration Script",
            f"-- Source Schema: {source_schema}",
            f"-- Destination Schema: {dest_schema}",
            f"-- Generated: {datetime.now().isoformat()}",
            "",
            "-- WARNING: Review this script carefully before executing!",
            "-- This script will modify the destination database structure.",
            "",
            "SET FOREIGN_KEY_CHECKS = 0;",
            ""
        ]
        
        alter_generator = AlterStatementGenerator(dest_schema)
        
        # Helper functions to get DDL using the provided functions
        def get_source_ddl(obj_type: str, obj_name: str) -> Optional[str]:
            return get_source_ddl_func(obj_type, obj_name)
        
        def get_dest_ddl(obj_type: str, obj_name: str) -> Optional[str]:
            return get_dest_ddl_func(obj_type, obj_name)
        
        # Process table changes
        sql_lines.extend([
            "-- TABLES CHANGES",
            "--" + "-" * 48
        ])
        
        if 'tables' in comparison:
            tables_comparison = comparison['tables']
            
            # Tables only in source (to be created)
            for table_name in tables_comparison.get('only_in_source', []):
                try:
                    source_ddl = get_source_ddl('tables', table_name)
                    if source_ddl:
                        sql_lines.append(f"-- Create table: {table_name}")
                        sql_lines.append(source_ddl + ";")
                        sql_lines.append("")
                except Exception:
                    sql_lines.append(f"-- ERROR: Failed to process table {table_name}")
            
            # Tables only in dest (to be dropped)
            for table_name in tables_comparison.get('only_in_dest', []):
                sql_lines.append(f"-- Drop table: {table_name}")
                sql_lines.append(f"DROP TABLE IF EXISTS `{dest_schema}`.`{table_name}`;")
                sql_lines.append("")
            
            # Tables with differences (to be modified)
            for table_name in tables_comparison.get('in_both', []):
                try:
                    source_ddl = get_source_ddl('tables', table_name)
                    dest_ddl = get_dest_ddl('tables', table_name)
                    if source_ddl and dest_ddl:
                        differences = self.analyze_table_differences(table_name, source_ddl, dest_ddl)
                        if differences:
                            sql_lines.append(f"-- Modify table: {table_name}")
                            
                            # Generate the differences report
                            report = alter_generator.generate_table_differences_report(table_name, differences)
                            for line in report.split('\n'):
                                sql_lines.append(f"-- {line}")
                            
                            # Generate ALTER statements
                            alter_statements = alter_generator.generate_alter_statements(table_name, differences)
                            for stmt in alter_statements:
                                sql_lines.append(stmt + ";")
                            sql_lines.append("")
                except Exception as e:
                    sql_lines.append(f"-- ERROR: Failed to process table {table_name}: {str(e)}")
        
        # Process procedure changes
        sql_lines.extend([
            "",
            "-- PROCEDURES CHANGES",
            "--" + "-" * 48
        ])
        
        if 'procedures' in comparison:
            procedures_comparison = comparison['procedures']
            
            # Procedures only in source (to be created)
            for proc_name in procedures_comparison.get('only_in_source', []):
                try:
                    source_ddl = get_source_ddl('procedures', proc_name)
                    if source_ddl:
                        sql_lines.append(f"-- Create procedure: {proc_name}")
                        sql_lines.append(f"DROP PROCEDURE IF EXISTS `{dest_schema}`.`{proc_name}`;")
                        adapted_ddl = self._adapt_ddl_for_destination(source_ddl, dest_schema)
                        sql_lines.append(adapted_ddl)
                        sql_lines.append("")
                except Exception:
                    sql_lines.append(f"-- ERROR: Failed to process procedure {proc_name}")
            
            # Procedures only in dest (to be dropped)
            for proc_name in procedures_comparison.get('only_in_dest', []):
                sql_lines.append(f"-- Drop procedure: {proc_name}")
                sql_lines.append(f"DROP PROCEDURE IF EXISTS `{dest_schema}`.`{proc_name}`;")
                sql_lines.append("")
            
            # Procedures in both (to be updated)
            for proc_name in procedures_comparison.get('in_both', []):
                try:
                    source_ddl = get_source_ddl('procedures', proc_name)
                    dest_ddl = get_dest_ddl('procedures', proc_name)
                    
                    # Normalize whitespace for comparison
                    source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                    dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                    
                    if source_normalized != dest_normalized:
                        sql_lines.append(f"-- Update procedure: {proc_name}")
                        sql_lines.append(f"DROP PROCEDURE IF EXISTS `{dest_schema}`.`{proc_name}`;")
                        adapted_ddl = self._adapt_ddl_for_destination(source_ddl, dest_schema)
                        sql_lines.append(adapted_ddl)
                        sql_lines.append("")
                except Exception:
                    sql_lines.append(f"-- ERROR: Failed to process procedure {proc_name}")
        
        # Process function changes
        if 'functions' in comparison:
            functions_comparison = comparison['functions']
            if (functions_comparison.get('only_in_source') or 
                functions_comparison.get('only_in_dest') or 
                functions_comparison.get('in_both')):
                
                sql_lines.extend([
                    "",
                    "-- FUNCTIONS CHANGES", 
                    "--" + "-" * 48
                ])
                
                # Functions only in source (to be created)
                for func_name in functions_comparison.get('only_in_source', []):
                    try:
                        source_ddl = get_source_ddl('functions', func_name)
                        if source_ddl:
                            sql_lines.append(f"-- Create function: {func_name}")
                            sql_lines.append(f"DROP FUNCTION IF EXISTS `{dest_schema}`.`{func_name}`;")
                            adapted_ddl = self._adapt_ddl_for_destination(source_ddl, dest_schema)
                            sql_lines.append(adapted_ddl)
                            sql_lines.append("")
                    except Exception:
                        sql_lines.append(f"-- ERROR: Failed to process function {func_name}")
                
                # Functions only in dest (to be dropped)
                for func_name in functions_comparison.get('only_in_dest', []):
                    sql_lines.append(f"-- Drop function: {func_name}")
                    sql_lines.append(f"DROP FUNCTION IF EXISTS `{dest_schema}`.`{func_name}`;")
                    sql_lines.append("")
                
                # Functions in both (to be updated)
                for func_name in functions_comparison.get('in_both', []):
                    try:
                        source_ddl = get_source_ddl('functions', func_name)
                        dest_ddl = get_dest_ddl('functions', func_name)
                        
                        # Normalize whitespace for comparison
                        source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                        dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                        
                        if source_normalized != dest_normalized:
                            sql_lines.append(f"-- Update function: {func_name}")
                            sql_lines.append(f"DROP FUNCTION IF EXISTS `{dest_schema}`.`{func_name}`;")
                            adapted_ddl = self._adapt_ddl_for_destination(source_ddl, dest_schema)
                            sql_lines.append(adapted_ddl)
                            sql_lines.append("")
                    except Exception:
                        sql_lines.append(f"-- ERROR: Failed to process function {func_name}")
        
        # Process trigger changes
        if 'triggers' in comparison:
            triggers_comparison = comparison['triggers']
            if (triggers_comparison.get('only_in_source') or 
                triggers_comparison.get('only_in_dest') or 
                triggers_comparison.get('in_both')):
                
                sql_lines.extend([
                    "",
                    "-- TRIGGERS CHANGES", 
                    "--" + "-" * 48
                ])
                
                # Triggers only in source (to be created)
                for trigger_name in triggers_comparison.get('only_in_source', []):
                    try:
                        source_ddl = get_source_ddl('triggers', trigger_name)
                        if source_ddl:
                            sql_lines.append(f"-- Create trigger: {trigger_name}")
                            sql_lines.append(f"DROP TRIGGER IF EXISTS `{dest_schema}`.`{trigger_name}`;")
                            adapted_ddl = self._adapt_ddl_for_destination(source_ddl, dest_schema)
                            sql_lines.append(adapted_ddl)
                            sql_lines.append("")
                    except Exception:
                        sql_lines.append(f"-- ERROR: Failed to process trigger {trigger_name}")
                
                # Triggers only in dest (to be dropped)
                for trigger_name in triggers_comparison.get('only_in_dest', []):
                    sql_lines.append(f"-- Drop trigger: {trigger_name}")
                    sql_lines.append(f"DROP TRIGGER IF EXISTS `{dest_schema}`.`{trigger_name}`;")
                    sql_lines.append("")
                
                # Triggers in both (to be updated)
                for trigger_name in triggers_comparison.get('in_both', []):
                    try:
                        source_ddl = get_source_ddl('triggers', trigger_name)
                        dest_ddl = get_dest_ddl('triggers', trigger_name)
                        
                        # Normalize whitespace for comparison
                        source_normalized = ' '.join(source_ddl.split()) if source_ddl else ''
                        dest_normalized = ' '.join(dest_ddl.split()) if dest_ddl else ''
                        
                        if source_normalized != dest_normalized:
                            sql_lines.append(f"-- Update trigger: {trigger_name}")
                            sql_lines.append(f"DROP TRIGGER IF EXISTS `{dest_schema}`.`{trigger_name}`;")
                            adapted_ddl = self._adapt_ddl_for_destination(source_ddl, dest_schema)
                            sql_lines.append(adapted_ddl)
                            sql_lines.append("")
                    except Exception:
                        sql_lines.append(f"-- ERROR: Failed to process trigger {trigger_name}")
        
        # Add sections for unchanged objects to show what DDL Wizard can compare
        object_types = ['events']
        
        for obj_type in object_types:
            obj_type_upper = obj_type.upper()
            sql_lines.extend([
                "",
                f"-- {obj_type_upper} CHANGES",
                "--" + "-" * 48
            ])
            
            if obj_type in comparison and (
                comparison[obj_type].get('only_in_source') or 
                comparison[obj_type].get('only_in_dest') or 
                comparison[obj_type].get('in_both')
            ):
                # This object type has changes - would be handled above
                # For now, just show placeholder since we don't fully implement all types yet
                sql_lines.append("-- (Changes for this object type not yet implemented)")
            else:
                sql_lines.append("-- <none>")
            sql_lines.append("")
        
        sql_lines.extend([
            "",
            "SET FOREIGN_KEY_CHECKS = 1;",
            "",
            "-- Migration script completed."
        ])
        
        return '\n'.join(sql_lines)
