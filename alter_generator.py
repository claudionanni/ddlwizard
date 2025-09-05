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
    
    def generate_rollback_statements(self, table_name: str, differences: List[Dict[str, Any]], dest_table_ddl: str = '') -> List[str]:
        """
        Generate rollback statements for table differences with proper dependency ordering.
        Rollback requires reverse dependency order: DROP FK → DROP INDEX → DROP COLUMN → ADD COLUMN → ADD INDEX → ADD FK
        
        Args:
            table_name: Name of the table
            differences: List of differences found
            dest_table_ddl: DDL of the destination table for constraint analysis
            
        Returns:
            List of rollback SQL statements in dependency-safe order
        """
        rollback_statements = []
        
        # Store destination DDL for use in dependency analysis
        self._destination_table_ddl = dest_table_ddl
        
        # Phase 1: Handle foreign key constraints for columns that will be dropped in rollback
        self._add_foreign_key_drops_for_rollback_column_removal(rollback_statements, table_name, differences)
        
        # Sort differences for rollback in reverse dependency order
        sorted_diffs = sorted(differences, key=lambda x: self._get_rollback_sort_key(x))
        
        for diff in sorted_diffs:
            # Get the difference type, handling both enum and string values
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
            
            # Generate rollback statements based on difference type
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
                # For rollback of ADD_INDEX, we need to drop the index
                idx_name = diff.get('index_name', '')
                if self._is_fulltext_index(diff):
                    rollback_statements.append(f"ALTER TABLE `{table_name}` DROP KEY `{idx_name}`")
                else:
                    rollback_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX `{idx_name}`")
            elif diff_type == ChangeType.REMOVE_INDEX.value:
                # For rollback of REMOVE_INDEX, we need to add the index back
                idx_def = diff.get('index_definition', '')
                if self._is_fulltext_index(diff):
                    fixed_idx_def = self._fix_fulltext_index_syntax(idx_def)
                    rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {fixed_idx_def}")
                else:
                    rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {idx_def}")
            elif diff_type == ChangeType.MODIFY_INDEX.value:
                # For rollback of MODIFY_INDEX, restore the original index definition
                idx_name = diff.get('index_name', '')
                original_def = diff.get('original_definition', '') or diff.get('index_definition', '')
                
                # Drop the current index first
                if self._is_fulltext_index(diff):
                    rollback_statements.append(f"ALTER TABLE `{table_name}` DROP KEY `{idx_name}`")
                else:
                    rollback_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX `{idx_name}`")
                
                # Add back the original index definition
                if self._is_fulltext_index(diff):
                    fixed_idx_def = self._fix_fulltext_index_syntax(original_def)
                    rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {fixed_idx_def}")
                else:
                    rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {original_def}")
            elif diff_type == ChangeType.ADD_CONSTRAINT.value:
                # To rollback adding a constraint, we drop it
                constraint_name = diff.get('constraint_name', '')
                drop_stmt = f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`"
                if drop_stmt not in rollback_statements:
                    rollback_statements.append(drop_stmt)
            elif diff_type == ChangeType.REMOVE_CONSTRAINT.value:
                # To rollback removing a constraint, we add it back
                constraint_def = diff.get('constraint_definition', '')
                rollback_statements.append(f"ALTER TABLE `{table_name}` ADD {constraint_def}")
            elif diff_type == ChangeType.MODIFY_CONSTRAINT.value:
                # To rollback modifying a constraint, we restore the original
                constraint_name = diff.get('constraint_name', '')
                original_def = diff.get('original_definition', '')
                # Drop the modified constraint (avoid duplicate if already added by dependency detection)
                drop_stmt = f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`"
                if drop_stmt not in rollback_statements:
                    rollback_statements.append(drop_stmt)
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
                # Use CONVERT TO CHARACTER SET to update both table and all columns  
                charset = original_collate.split('_')[0] if '_' in original_collate else original_collate
                rollback_statements.append(f"ALTER TABLE `{table_name}` CONVERT TO CHARACTER SET {charset} COLLATE {original_collate}")
        
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
    
    def _get_sort_key(self, diff: Dict[str, Any]) -> int:
        """
        Get sorting key for dependency-safe operation ordering.
        Lower numbers execute first.
        """
        diff_type = diff.get('type')
        if hasattr(diff_type, 'value'):
            diff_type = diff_type.value
            
        # Define execution order priority
        order_map = {
            ChangeType.REMOVE_CONSTRAINT.value: 1,
            ChangeType.REMOVE_INDEX.value: 2,
            ChangeType.MODIFY_INDEX.value: 3,  # Drop and recreate indexes
            ChangeType.MODIFY_COLUMN.value: 4,
            ChangeType.REMOVE_COLUMN.value: 5,
            ChangeType.ADD_COLUMN.value: 6,
            ChangeType.ADD_INDEX.value: 7,
            ChangeType.ADD_CONSTRAINT.value: 8,
            ChangeType.MODIFY_CONSTRAINT.value: 9,
        }
        
        return order_map.get(diff_type, 999)
    
    def _get_rollback_sort_key(self, diff: Dict[str, Any]) -> int:
        """
        Get sorting key for rollback operations - reverse dependency order.
        Lower numbers execute first in rollback.
        """
        diff_type = diff.get('type')
        if hasattr(diff_type, 'value'):
            diff_type = diff_type.value
            
        # Rollback operation priority (what each forward change becomes in rollback)
        rollback_order_map = {
            # Phase 1: Drop constraints and indexes first (reverse of additions)
            ChangeType.ADD_CONSTRAINT.value: 1,   # Rollback: DROP CONSTRAINT
            ChangeType.ADD_INDEX.value: 2,        # Rollback: DROP INDEX
            
            # Phase 2: Drop/modify columns
            ChangeType.ADD_COLUMN.value: 4,       # Rollback: DROP COLUMN
            ChangeType.MODIFY_COLUMN.value: 5,    # Rollback: MODIFY COLUMN
            
            # Phase 3: Add columns back
            ChangeType.REMOVE_COLUMN.value: 7,    # Rollback: ADD COLUMN
            
            # Phase 4: Add indexes and constraints back (after columns exist)
            ChangeType.REMOVE_INDEX.value: 8,     # Rollback: ADD INDEX
            ChangeType.REMOVE_CONSTRAINT.value: 10, # Rollback: ADD CONSTRAINT (after columns added)
            ChangeType.MODIFY_CONSTRAINT.value: 11, # Rollback: DROP + ADD CONSTRAINT (after columns added)
        }
        
        return rollback_order_map.get(diff_type, 999)
    
    def _add_foreign_key_drops_for_rollback_column_removal(self, rollback_statements: List[str], 
                                                          table_name: str, differences: List[Dict[str, Any]]):
        """
        Add DROP FOREIGN KEY statements for rollback when columns will be dropped.
        In rollback, ADD_COLUMN differences become DROP COLUMN operations,
        so we need to drop foreign keys that reference those columns first.
        """
        # Find columns that will be dropped in rollback (ADD_COLUMN in forward = DROP COLUMN in rollback)
        columns_to_drop_in_rollback = []
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
            if diff_type == ChangeType.ADD_COLUMN.value:
                # This was added in forward migration, will be dropped in rollback
                columns_to_drop_in_rollback.append(diff.get('column_name', ''))
        
        if not columns_to_drop_in_rollback:
            return
        
        # Find constraints that reference these columns
        foreign_keys_to_drop = []
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            # Check constraints that were added/modified in forward migration
            if diff_type in [ChangeType.ADD_CONSTRAINT.value, ChangeType.MODIFY_CONSTRAINT.value]:
                constraint_def = diff.get('constraint_definition', '') or diff.get('new_definition', '')
                constraint_name = diff.get('constraint_name', '')
                
                # Check if constraint references a column that will be dropped in rollback
                for col_name in columns_to_drop_in_rollback:
                    if f"`{col_name}`" in constraint_def or f"({col_name})" in constraint_def:
                        if constraint_name not in foreign_keys_to_drop:
                            foreign_keys_to_drop.append(constraint_name)
        
        # Also check existing constraints in destination DDL that might reference columns being dropped
        if hasattr(self, '_destination_table_ddl') and self._destination_table_ddl:
            import re
            fk_pattern = r'CONSTRAINT\s+`?([^`\s]+)`?\s+FOREIGN\s+KEY\s*\(\s*`?([^`\)]+)`?\s*\)'
            dest_ddl = self._destination_table_ddl
            
            for match in re.finditer(fk_pattern, dest_ddl, re.IGNORECASE):
                constraint_name = match.group(1)
                column_name = match.group(2)
                
                if column_name in columns_to_drop_in_rollback:
                    if constraint_name not in foreign_keys_to_drop:
                        foreign_keys_to_drop.append(constraint_name)
        
        # Add the drop statements
        for constraint_name in foreign_keys_to_drop:
            drop_stmt = f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`"
            if drop_stmt not in rollback_statements:
                rollback_statements.append(drop_stmt)
    
    def _add_foreign_key_drops_for_column_removal(self, alter_statements: List[str], 
                                                  table_name: str, differences: List[Dict[str, Any]]):
        """
        Add DROP FOREIGN KEY statements for constraints that reference columns being removed.
        This prevents the "cannot drop column: needed in foreign key constraint" error.
        """
        # Find columns that will be removed
        columns_to_remove = []
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
            if diff_type == ChangeType.REMOVE_COLUMN.value:
                columns_to_remove.append(diff.get('column_name', ''))
        
        if not columns_to_remove:
            return
        
        # Find constraints that reference these columns and add drop statements
        # Check both REMOVE_CONSTRAINT and MODIFY_CONSTRAINT types
        foreign_keys_to_drop = []
        for diff in differences:
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type in [ChangeType.REMOVE_CONSTRAINT.value, ChangeType.MODIFY_CONSTRAINT.value]:
                constraint_def = diff.get('constraint_definition', '') or diff.get('original_definition', '')
                constraint_name = diff.get('constraint_name', '')
                
                # Check if constraint references a column being removed
                for col_name in columns_to_remove:
                    if f"`{col_name}`" in constraint_def or f"({col_name})" in constraint_def:
                        # This constraint references a column being removed, drop it first
                        if constraint_name not in foreign_keys_to_drop:
                            foreign_keys_to_drop.append(constraint_name)
        
        # Also check if any existing foreign keys reference columns being removed
        # This handles cases where the constraint isn't showing up in differences properly
        if hasattr(self, '_destination_table_ddl'):
            # Parse existing foreign keys from destination DDL
            import re
            fk_pattern = r'CONSTRAINT\s+`?([^`\s]+)`?\s+FOREIGN\s+KEY\s*\(\s*`?([^`\)]+)`?\s*\)'
            dest_ddl = getattr(self, '_destination_table_ddl', '')
            
            for match in re.finditer(fk_pattern, dest_ddl, re.IGNORECASE):
                constraint_name = match.group(1)
                column_name = match.group(2)
                
                if column_name in columns_to_remove:
                    if constraint_name not in foreign_keys_to_drop:
                        foreign_keys_to_drop.append(constraint_name)
        
        # Add the drop statements
        for constraint_name in foreign_keys_to_drop:
            drop_stmt = f"ALTER TABLE `{table_name}` DROP FOREIGN KEY IF EXISTS `{constraint_name}`"
            if drop_stmt not in alter_statements:
                alter_statements.append(drop_stmt)
    
    def _is_fulltext_index(self, diff: Dict[str, Any]) -> bool:
        """Check if the index is a FULLTEXT index."""
        idx_def = diff.get('index_definition', '')
        return 'FULLTEXT' in idx_def.upper()
    
    def _fix_fulltext_index_syntax(self, index_definition: str) -> str:
        """
        Fix FULLTEXT index syntax generation.
        
        The issue was: ALTER TABLE products MODIFY COLUMN FULLTEXT KEY ft_search (...)
        Should be: ALTER TABLE products ADD FULLTEXT KEY ft_search (...)
        """
        # Remove any incorrect MODIFY COLUMN prefix
        fixed_def = index_definition.replace('MODIFY COLUMN ', '')
        
        # Ensure proper FULLTEXT syntax
        if not fixed_def.upper().startswith('FULLTEXT'):
            if 'KEY' in fixed_def:
                # Transform: KEY `ft_search` (...) -> FULLTEXT KEY `ft_search` (...)
                fixed_def = fixed_def.replace('KEY', 'FULLTEXT KEY', 1)
            else:
                fixed_def = f"FULLTEXT {fixed_def}"
        
        return fixed_def
    
    def _validate_column_modification(self, table_name: str, col_name: str, 
                                    new_definition: str, diff: Dict[str, Any]) -> bool:
        """
        Validate if a column modification is safe.
        For now, always return True - safety analysis will be handled separately.
        """
        # TODO: Implement comprehensive data safety analysis in a separate feature
        # For now, generate all ALTER statements to ensure deterministic behavior
        return True
    
    def _extract_enum_values(self, column_definition: str) -> List[str]:
        """Extract ENUM values from column definition."""
        import re
        enum_match = re.search(r"enum\((.*?)\)", column_definition.lower())
        if enum_match:
            enum_content = enum_match.group(1)
            # Extract quoted values
            values = re.findall(r"'([^']*)'", enum_content)
            return values
        return []
    
    def _validate_constraint_addition(self, table_name: str, constraint_definition: str) -> bool:
        """
        Validate if adding a constraint is safe.
        Returns False if the constraint might fail due to existing data.
        """
        # For UNIQUE constraints, we should warn about potential duplicates
        if 'UNIQUE' in constraint_definition.upper():
            # This is a basic implementation - in a real scenario, you'd query the database
            # to check for duplicate values
            return True  # Assume safe for now, but add warning
        
        return True
    
    def generate_alter_statements(self, table_name: str, differences: List[Dict[str, Any]], dest_table_ddl: str = '') -> List[str]:
        """
        Generate ALTER statements for table differences with proper dependency ordering.
        
        Args:
            table_name: Name of the table
            differences: List of differences found
            dest_table_ddl: DDL of the destination table for constraint analysis
            
        Returns:
            List of ALTER SQL statements in dependency-safe order
        """
        alter_statements = []
        
        # Store destination DDL for use in dependency analysis
        self._destination_table_ddl = dest_table_ddl
        
        # Phase 1: Drop foreign key constraints that reference columns to be dropped
        self._add_foreign_key_drops_for_column_removal(alter_statements, table_name, differences)
        
        # Phase 2: Drop other constraints and indexes
        for diff in sorted(differences, key=lambda x: self._get_sort_key(x)):
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type == ChangeType.REMOVE_CONSTRAINT.value:
                constraint_name = diff.get('constraint_name', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY IF EXISTS `{constraint_name}`")
            elif diff_type == ChangeType.REMOVE_INDEX.value:
                idx_name = diff.get('index_name', '')
                # Handle FULLTEXT indexes properly
                if self._is_fulltext_index(diff):
                    alter_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX IF EXISTS `{idx_name}`")
                else:
                    alter_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX IF EXISTS `{idx_name}`")
        
        # Phase 3: Modify columns before dropping referenced columns
        for diff in sorted(differences, key=lambda x: self._get_sort_key(x)):
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type == ChangeType.MODIFY_COLUMN.value:
                col_name = diff.get('column_name', '')
                new_def = diff.get('new_definition', '')
                # Validate data compatibility before modifying
                if self._validate_column_modification(table_name, col_name, new_def, diff):
                    fixed_def = self._fix_generated_column_references(new_def, differences)
                    alter_statements.append(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {fixed_def}")
                else:
                    alter_statements.append(f"-- WARNING: Column modification may cause data loss or constraint violations")
                    alter_statements.append(f"-- ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {new_def}")
        
        # Phase 4: Drop columns after modifying dependencies and dropping constraints
        for diff in sorted(differences, key=lambda x: self._get_sort_key(x)):
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type == ChangeType.REMOVE_COLUMN.value:
                col_name = diff.get('column_name', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` DROP COLUMN IF EXISTS `{col_name}`")
        
        # Phase 5: Add new elements with validation
        for diff in sorted(differences, key=lambda x: self._get_sort_key(x)):
            diff_type = diff.get('type')
            if hasattr(diff_type, 'value'):
                diff_type = diff_type.value
                
            if diff_type == ChangeType.ADD_COLUMN.value:
                col_name = diff.get('column_name', '')
                col_def = diff.get('column_definition', '')
                alter_statements.append(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def}")
            elif diff_type == ChangeType.ADD_INDEX.value:
                idx_def = diff.get('index_definition', '')
                # Handle FULLTEXT indexes with proper syntax
                if self._is_fulltext_index(diff):
                    fixed_idx_def = self._fix_fulltext_index_syntax(idx_def)
                    alter_statements.append(f"ALTER TABLE `{table_name}` ADD {fixed_idx_def}")
                else:
                    alter_statements.append(f"ALTER TABLE `{table_name}` ADD {idx_def}")
            elif diff_type == ChangeType.MODIFY_INDEX.value:
                # For index modifications, we need to drop and recreate
                # MariaDB doesn't support direct index modification
                idx_name = diff.get('index_name', '')
                new_idx_def = diff.get('new_definition', '') or diff.get('index_definition', '')
                
                # Drop the existing index first
                if self._is_fulltext_index(diff):
                    # FULLTEXT indexes use DROP KEY
                    alter_statements.append(f"ALTER TABLE `{table_name}` DROP KEY `{idx_name}`")
                else:
                    # Regular indexes use DROP INDEX  
                    alter_statements.append(f"ALTER TABLE `{table_name}` DROP INDEX `{idx_name}`")
                
                # Add the new index definition
                if self._is_fulltext_index(diff):
                    fixed_idx_def = self._fix_fulltext_index_syntax(new_idx_def)
                    alter_statements.append(f"ALTER TABLE `{table_name}` ADD {fixed_idx_def}")
                else:
                    alter_statements.append(f"ALTER TABLE `{table_name}` ADD {new_idx_def}")
            elif diff_type == ChangeType.ADD_CONSTRAINT.value:
                constraint_def = diff.get('constraint_definition', '')
                # Validate constraint before adding
                if self._validate_constraint_addition(table_name, constraint_def):
                    alter_statements.append(f"ALTER TABLE `{table_name}` ADD {constraint_def}")
                else:
                    alter_statements.append(f"-- WARNING: Constraint addition may fail due to existing data")
                    alter_statements.append(f"-- ALTER TABLE `{table_name}` ADD {constraint_def}")
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
                # Use CONVERT TO CHARACTER SET to update both table and all columns
                # Extract charset from collation (e.g., utf8mb4_unicode_ci -> utf8mb4)
                charset = new_collate.split('_')[0] if '_' in new_collate else new_collate
                alter_statements.append(f"ALTER TABLE `{table_name}` CONVERT TO CHARACTER SET {charset} COLLATE {new_collate}")
        
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
