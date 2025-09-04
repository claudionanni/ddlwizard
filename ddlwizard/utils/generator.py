"""
Alter Statement Generator for DDL Wizard.
"""

from typing import List, Dict, Any
from .comparator import ChangeType


class AlterStatementGenerator:
    """Generates ALTER statements for schema migrations."""
    
    def __init__(self, dest_schema: str = None):
        """
        Initialize the alter statement generator.
        
        Args:
            dest_schema: Destination schema name (optional for backward compatibility)
        """
        self.dest_schema = dest_schema
    
    def generate_rollback_statements(self, table_name: str, differences: List[Dict[str, Any]]) -> List[str]:
        """
        Generate rollback statements for table differences.
        
        Args:
            table_name: Name of the table
            differences: List of differences found
            
        Returns:
            List of rollback SQL statements
        """
        rollback_statements = []
        
        for diff in differences:
            # Get the difference type, handling both enum and string values
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
            
            # Generate basic rollback statements based on difference type
            if diff_type == ChangeType.ADD_COLUMN.value:
                rollback_statements.append(f"ALTER TABLE `{table_name}` DROP COLUMN `{diff.get('column_name')}`")
            elif diff_type == ChangeType.REMOVE_COLUMN.value:
                col_name = diff.get('column_name', '')
                col_def = diff.get('column_definition', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def}")
            elif diff_type == ChangeType.MODIFY_COLUMN.value:
                col_name = diff.get('column_name', '')
                # For rollback, we use original_definition to restore the original state
                rollback_def = diff.get('original_definition', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {rollback_def}")
            elif diff_type == ChangeType.ADD_INDEX.value:
                rollback_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX `{diff.get('index_name')}`")
            elif diff_type == ChangeType.REMOVE_INDEX.value:
                rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {diff.get('index_definition', '')}")
            elif diff_type == ChangeType.ADD_CONSTRAINT.value:
                # To rollback adding a constraint, we drop it
                constraint_name = diff.get('constraint_name', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`")
            elif diff_type == ChangeType.REMOVE_CONSTRAINT.value:
                # To rollback removing a constraint, we add it back
                constraint_def = diff.get('constraint_definition', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {constraint_def}")
            elif diff_type == ChangeType.MODIFY_CONSTRAINT.value:
                # To rollback modifying a constraint, we restore the original
                constraint_name = diff.get('constraint_name', '')
                original_def = diff.get('original_definition', '')
                # Drop the modified constraint and restore the original
                rollback_statements.append(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`")
                rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {original_def}")
            elif diff_type == 'table_comment_modified':
                # Rollback table comment change
                original_comment = diff.get('original_value', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` COMMENT='{original_comment}'")
            elif diff_type == 'table_engine_modified':
                # Rollback table engine change
                original_engine = diff.get('original_value', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` ENGINE={original_engine}")
            elif diff_type == 'table_charset_modified':
                # Rollback table charset change
                original_charset = diff.get('original_value', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` DEFAULT CHARSET={original_charset}")
            elif diff_type == 'table_collate_modified':
                # Rollback table collation change
                original_collate = diff.get('original_value', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` COLLATE={original_collate}")
        
        return rollback_statements
    
    def generate_table_differences_report(self, table_name: str, differences: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable report of table differences.
        
        Args:
            table_name: Name of the table
            differences: List of differences found
            
        Returns:
            String report of differences
        """
        if not differences:
            return f"Table '{table_name}': No differences found"
        
        report_lines = [f"Table '{table_name}' differences:"]
        
        for i, diff in enumerate(differences, 1):
            # Get the difference type, handling both enum and string values
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
            
            if diff_type == ChangeType.ADD_COLUMN.value:
                report_lines.append(f"  {i}. Column ADDED: {diff.get('column_name', 'unknown')} ({diff.get('column_definition', 'no definition')})")
            elif diff_type == ChangeType.REMOVE_COLUMN.value:
                report_lines.append(f"  {i}. Column REMOVED: {diff.get('column_name', 'unknown')}")
            elif diff_type == ChangeType.MODIFY_COLUMN.value:
                report_lines.append(f"  {i}. Column MODIFIED: {diff.get('column_name', 'unknown')}")
                if diff.get('original_definition'):
                    report_lines.append(f"      FROM: {diff['original_definition']}")
                if diff.get('new_definition'):
                    report_lines.append(f"      TO:   {diff['new_definition']}")
            elif diff_type == ChangeType.ADD_INDEX.value:
                report_lines.append(f"  {i}. Index ADDED: {diff.get('index_name', 'unknown')}")
            elif diff_type == ChangeType.REMOVE_INDEX.value:
                report_lines.append(f"  {i}. Index REMOVED: {diff.get('index_name', 'unknown')}")
            elif diff_type == ChangeType.ADD_CONSTRAINT.value:
                report_lines.append(f"  {i}. Foreign Key ADDED: {diff.get('constraint_name', 'unknown')}")
            elif diff_type == ChangeType.REMOVE_CONSTRAINT.value:
                report_lines.append(f"  {i}. Foreign Key REMOVED: {diff.get('constraint_name', 'unknown')}")
            elif diff_type == ChangeType.MODIFY_CONSTRAINT.value:
                report_lines.append(f"  {i}. Foreign Key MODIFIED: {diff.get('constraint_name', 'unknown')}")
            elif diff_type == 'table_comment_modified':
                report_lines.append(f"  {i}. Table COMMENT MODIFIED:")
                report_lines.append(f"      FROM: '{diff.get('original_value', '')}'")
                report_lines.append(f"      TO:   '{diff.get('new_value', '')}'")
            elif diff_type == 'table_engine_modified':
                report_lines.append(f"  {i}. Table ENGINE MODIFIED:")
                report_lines.append(f"      FROM: {diff.get('original_value', '')}")
                report_lines.append(f"      TO:   {diff.get('new_value', '')}")
            elif diff_type == 'table_charset_modified':
                report_lines.append(f"  {i}. Table CHARSET MODIFIED:")
                report_lines.append(f"      FROM: {diff.get('original_value', '')}")
                report_lines.append(f"      TO:   {diff.get('new_value', '')}")
            elif diff_type == 'table_collate_modified':
                report_lines.append(f"  {i}. Table COLLATION MODIFIED:")
                report_lines.append(f"      FROM: {diff.get('original_value', '')}")
                report_lines.append(f"      TO:   {diff.get('new_value', '')}")
            else:
                report_lines.append(f"  {i}. Unknown difference type: {diff_type}")
        
        return '\n'.join(report_lines)
    
    def generate_alter_statements(self, table_name: str, differences: List[Dict[str, Any]]) -> List[str]:
        """
        Generate ALTER statements for table differences with proper dependency ordering.
        
        Args:
            table_name: Name of the table
            differences: List of differences found
            
        Returns:
            List of ALTER SQL statements in dependency-safe order
        """
        alter_statements = []
        
        # Phase 1: Drop constraints and indexes first
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type == ChangeType.REMOVE_CONSTRAINT.value:
                constraint_name = diff.get('constraint_name', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY IF EXISTS `{constraint_name}`")
            elif diff_type == ChangeType.REMOVE_INDEX.value:
                idx_name = diff.get('index_name', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX IF EXISTS `{idx_name}`")
        
        # Phase 2: Modify columns before dropping referenced columns
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type == ChangeType.MODIFY_COLUMN.value:
                col_name = diff.get('column_name', '')
                new_def = diff.get('new_definition', '')
                # Fix generated column references by removing references to columns that will be dropped
                fixed_def = self._fix_generated_column_references(new_def, differences)
                alter_statements.append(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {fixed_def}")
        
        # Phase 3: Drop columns after modifying dependencies
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type == ChangeType.REMOVE_COLUMN.value:
                col_name = diff.get('column_name', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` DROP COLUMN IF EXISTS `{col_name}`")
        
        # Phase 4: Add new elements
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type == ChangeType.ADD_COLUMN.value:
                col_name = diff.get('column_name', '')
                col_def = diff.get('column_definition', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def}")
            elif diff_type == ChangeType.ADD_INDEX.value:
                idx_def = diff.get('index_definition', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` ADD {idx_def}")
            elif diff_type == ChangeType.ADD_CONSTRAINT.value:
                constraint_def = diff.get('constraint_definition', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` ADD {constraint_def}")
            elif diff_type == ChangeType.MODIFY_CONSTRAINT.value:
                constraint_name = diff.get('constraint_name', '')
                constraint_def = diff.get('new_definition', '')
                # For modifying a constraint, we need to drop and recreate it
                alter_statements.append(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY IF EXISTS `{constraint_name}`")
                alter_statements.append(f"ALTER TABLE `{table_name}` ADD {constraint_def}")
            # Handle table property modifications
            elif diff_type == 'table_comment_modified':
                new_comment = diff.get('new_value', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` COMMENT='{new_comment}'")
            elif diff_type == 'table_engine_modified':
                new_engine = diff.get('new_value', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` ENGINE={new_engine}")
            elif diff_type == 'table_charset_modified':
                new_charset = diff.get('new_value', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` DEFAULT CHARSET={new_charset}")
            elif diff_type == 'table_collate_modified':
                new_collate = diff.get('new_value', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` COLLATE={new_collate}")
        
        return alter_statements
    
    def _fix_generated_column_references(self, column_definition: str, differences: List[Dict[str, Any]]) -> str:
        """
        Fix generated column expressions by removing references to columns that will be dropped.
        
        Args:
            column_definition: The column definition containing generated expression
            differences: List of all differences to check for dropped columns
            
        Returns:
            Fixed column definition with dropped column references removed
        """
        if 'GENERATED ALWAYS AS' not in column_definition:
            return column_definition
        
        # Find columns that will be dropped
        dropped_columns = []
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
            if diff_type == ChangeType.REMOVE_COLUMN.value:
                dropped_columns.append(diff.get('column_name', ''))
        
        # Remove references to dropped columns from generated expression
        fixed_def = column_definition
        for dropped_col in dropped_columns:
            if f"`{dropped_col}`" in fixed_def:
                # Simple fix: remove the entire term containing the dropped column
                # This is a basic implementation - could be more sophisticated
                import re
                # Remove patterns like "- `dropped_column`" or "+ `dropped_column`"
                fixed_def = re.sub(rf'[+-]\s*`{dropped_col}`', '', fixed_def)
                # Clean up any double operators
                fixed_def = re.sub(r'\s*\+\s*\+', ' +', fixed_def)
                fixed_def = re.sub(r'\s*-\s*-', ' -', fixed_def)
                # Clean up trailing operators
                fixed_def = re.sub(r'[+-]\s*\)', ')', fixed_def)
        
        return fixed_def
