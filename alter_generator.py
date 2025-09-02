"""
Alter Statement Generator for DDL Wizard.
"""

from typing import List, Dict, Any
from schema_comparator import ChangeType


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
                orig_def = diff.get('original_definition', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {orig_def}")
            elif diff_type == ChangeType.ADD_INDEX.value:
                rollback_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX `{diff.get('index_name')}`")
            elif diff_type == ChangeType.REMOVE_INDEX.value:
                rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {diff.get('index_definition', '')}")
        
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
            else:
                report_lines.append(f"  {i}. Unknown difference type: {diff_type}")
        
        return '\n'.join(report_lines)
    
    def generate_alter_statements(self, table_name: str, differences: List[Dict[str, Any]]) -> List[str]:
        """
        Generate ALTER statements for table differences.
        
        Args:
            table_name: Name of the table
            differences: List of differences found
            
        Returns:
            List of ALTER SQL statements
        """
        alter_statements = []
        
        for diff in differences:
            # Get the difference type, handling both enum and string values
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
            
            # Generate basic ALTER statements based on difference type
            if diff_type == ChangeType.ADD_COLUMN.value:
                col_name = diff.get('column_name', '')
                col_def = diff.get('column_definition', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def}")
            elif diff_type == ChangeType.REMOVE_COLUMN.value:
                col_name = diff.get('column_name', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` DROP COLUMN `{col_name}`")
            elif diff_type == ChangeType.MODIFY_COLUMN.value:
                col_name = diff.get('column_name', '')
                new_def = diff.get('new_definition', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {new_def}")
            elif diff_type == ChangeType.ADD_INDEX.value:
                idx_def = diff.get('index_definition', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` ADD {idx_def}")
            elif diff_type == ChangeType.REMOVE_INDEX.value:
                idx_name = diff.get('index_name', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX `{idx_name}`")
        
        return alter_statements
