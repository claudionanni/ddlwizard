"""
ALTER statement generator for DDL Wizard.
Generates ALTER TABLE statements to transform destination tables to match source tables.
"""

import logging
from typing import Dict, List, Any, Optional
from ddl_analyzer import ChangeType, ColumnDefinition, IndexDefinition, ForeignKeyDefinition, TableStructure

logger = logging.getLogger(__name__)


class AlterStatementGenerator:
    """Generates ALTER TABLE statements for schema synchronization."""
    
    def __init__(self, dest_schema: str):
        self.dest_schema = dest_schema
    
    def generate_alter_statements(self, table_name: str, differences: List[Dict[str, Any]]) -> List[str]:
        """Generate ALTER TABLE statements from a list of differences."""
        if not differences:
            return []
        
        statements = []
        alter_clauses = []
        separate_statements = []
        
        # Group changes by type and generate appropriate clauses
        for diff in differences:
            change_type = diff['type']
            
            if change_type == ChangeType.ADD_COLUMN:
                clause = self._generate_add_column_clause(diff['column'])
                if clause:
                    alter_clauses.append(clause)
            
            elif change_type == ChangeType.DROP_COLUMN:
                clause = self._generate_drop_column_clause(diff['column'])
                if clause:
                    alter_clauses.append(clause)
            
            elif change_type == ChangeType.MODIFY_COLUMN:
                clause = self._generate_modify_column_clause(diff['column_name'], diff['to'])
                if clause:
                    alter_clauses.append(clause)
            
            elif change_type == ChangeType.ADD_INDEX:
                stmt = self._generate_add_index_statement(table_name, diff['index'])
                if stmt:
                    separate_statements.append(stmt)
            
            elif change_type == ChangeType.DROP_INDEX:
                stmt = self._generate_drop_index_statement(table_name, diff['index'])
                if stmt:
                    separate_statements.append(stmt)
            
            elif change_type == ChangeType.ADD_FOREIGN_KEY:
                stmt = self._generate_add_foreign_key_statement(table_name, diff['foreign_key'])
                if stmt:
                    separate_statements.append(stmt)
            
            elif change_type == ChangeType.DROP_FOREIGN_KEY:
                stmt = self._generate_drop_foreign_key_statement(table_name, diff['foreign_key'])
                if stmt:
                    separate_statements.append(stmt)
            
            elif change_type == ChangeType.CHANGE_ENGINE:
                clause = f"ENGINE = {diff['to']}"
                alter_clauses.append(clause)
            
            elif change_type == ChangeType.CHANGE_CHARSET:
                clause = f"DEFAULT CHARACTER SET = {diff['to']}"
                alter_clauses.append(clause)
            
            elif change_type == ChangeType.CHANGE_COLLATION:
                clause = f"COLLATE = {diff['to']}"
                alter_clauses.append(clause)
        
        # Combine column/table changes into single ALTER TABLE statement
        if alter_clauses:
            alter_sql = f"ALTER TABLE `{self.dest_schema}`.`{table_name}`\n  " + ",\n  ".join(alter_clauses)
            statements.append(alter_sql)
        
        # Add separate index statements
        statements.extend(separate_statements)
        
        return statements
    
    def _generate_add_column_clause(self, column: ColumnDefinition) -> str:
        """Generate ADD COLUMN clause."""
        clause = f"ADD COLUMN `{column.name}` {column.data_type}"
        
        if not column.nullable:
            clause += " NOT NULL"
        
        if column.default is not None:
            if column.default.upper() in ['CURRENT_TIMESTAMP', 'NULL']:
                clause += f" DEFAULT {column.default}"
            else:
                clause += f" DEFAULT '{column.default}'"
        
        if column.auto_increment:
            clause += " AUTO_INCREMENT"
        
        if column.charset:
            clause += f" CHARACTER SET {column.charset}"
        
        if column.collation:
            clause += f" COLLATE {column.collation}"
        
        if column.comment:
            clause += f" COMMENT '{column.comment}'"
        
        return clause
    
    def _generate_drop_column_clause(self, column: ColumnDefinition) -> str:
        """Generate DROP COLUMN clause."""
        return f"DROP COLUMN `{column.name}`"
    
    def _generate_modify_column_clause(self, column_name: str, column: ColumnDefinition) -> str:
        """Generate MODIFY COLUMN clause."""
        clause = f"MODIFY COLUMN `{column.name}` {column.data_type}"
        
        if not column.nullable:
            clause += " NOT NULL"
        
        if column.default is not None:
            if column.default.upper() in ['CURRENT_TIMESTAMP', 'NULL']:
                clause += f" DEFAULT {column.default}"
            else:
                clause += f" DEFAULT '{column.default}'"
        
        if column.auto_increment:
            clause += " AUTO_INCREMENT"
        
        if column.charset:
            clause += f" CHARACTER SET {column.charset}"
        
        if column.collation:
            clause += f" COLLATE {column.collation}"
        
        if column.comment:
            clause += f" COMMENT '{column.comment}'"
        
        return clause
    
    def _generate_add_index_statement(self, table_name: str, index: IndexDefinition) -> str:
        """Generate ADD INDEX statement."""
        if index.is_primary:
            columns_str = ", ".join([f"`{col}`" for col in index.columns])
            return f"ALTER TABLE `{self.dest_schema}`.`{table_name}` ADD PRIMARY KEY ({columns_str})"
        
        index_type = "UNIQUE " if index.is_unique else ""
        columns_str = ", ".join([f"`{col}`" for col in index.columns])
        
        return f"ALTER TABLE `{self.dest_schema}`.`{table_name}` ADD {index_type}INDEX `{index.name}` ({columns_str})"
    
    def _generate_drop_index_statement(self, table_name: str, index: IndexDefinition) -> str:
        """Generate DROP INDEX statement."""
        if index.is_primary:
            return f"ALTER TABLE `{self.dest_schema}`.`{table_name}` DROP PRIMARY KEY"
        
        return f"ALTER TABLE `{self.dest_schema}`.`{table_name}` DROP INDEX `{index.name}`"
    
    def _generate_add_foreign_key_statement(self, table_name: str, foreign_key: ForeignKeyDefinition) -> str:
        """Generate ADD FOREIGN KEY statement."""
        columns_str = ", ".join([f"`{col}`" for col in foreign_key.columns])
        ref_columns_str = ", ".join([f"`{col}`" for col in foreign_key.referenced_columns])
        
        stmt = f"ALTER TABLE `{self.dest_schema}`.`{table_name}` ADD CONSTRAINT `{foreign_key.name}` " \
               f"FOREIGN KEY ({columns_str}) REFERENCES `{foreign_key.referenced_table}` ({ref_columns_str})"
        
        if foreign_key.on_delete:
            stmt += f" ON DELETE {foreign_key.on_delete}"
        
        if foreign_key.on_update:
            stmt += f" ON UPDATE {foreign_key.on_update}"
        
        return stmt
    
    def _generate_drop_foreign_key_statement(self, table_name: str, foreign_key: ForeignKeyDefinition) -> str:
        """Generate DROP FOREIGN KEY statement."""
        return f"ALTER TABLE `{self.dest_schema}`.`{table_name}` DROP FOREIGN KEY `{foreign_key.name}`"
    
    def generate_table_differences_report(self, table_name: str, differences: List[Dict[str, Any]]) -> str:
        """Generate a human-readable report of table differences."""
        if not differences:
            return f"Table `{table_name}`: No differences found"
        
        report_lines = [f"Table `{table_name}` differences:"]
        
        for diff in differences:
            change_type = diff['type']
            
            if change_type == ChangeType.ADD_COLUMN:
                col = diff['column']
                report_lines.append(f"  + ADD COLUMN `{col.name}` {col.data_type}")
            
            elif change_type == ChangeType.DROP_COLUMN:
                col = diff['column']
                report_lines.append(f"  - DROP COLUMN `{col.name}`")
            
            elif change_type == ChangeType.MODIFY_COLUMN:
                col_name = diff['column_name']
                from_col = diff['from']
                to_col = diff['to']
                report_lines.append(f"  ~ MODIFY COLUMN `{col_name}`: {from_col.data_type} -> {to_col.data_type}")
            
            elif change_type == ChangeType.ADD_INDEX:
                idx = diff['index']
                idx_type = "PRIMARY" if idx.is_primary else ("UNIQUE" if idx.is_unique else "INDEX")
                report_lines.append(f"  + ADD {idx_type} `{idx.name}` ({', '.join(idx.columns)})")
            
            elif change_type == ChangeType.DROP_INDEX:
                idx = diff['index']
                idx_type = "PRIMARY" if idx.is_primary else ("UNIQUE" if idx.is_unique else "INDEX")
                report_lines.append(f"  - DROP {idx_type} `{idx.name}`")
            
            elif change_type == ChangeType.ADD_FOREIGN_KEY:
                fk = diff['foreign_key']
                columns_str = ", ".join(fk.columns)
                ref_columns_str = ", ".join(fk.referenced_columns)
                report_lines.append(f"  + ADD FOREIGN KEY `{fk.name}` ({columns_str}) -> {fk.referenced_table}({ref_columns_str})")
            
            elif change_type == ChangeType.DROP_FOREIGN_KEY:
                fk = diff['foreign_key']
                report_lines.append(f"  - DROP FOREIGN KEY `{fk.name}`")
            
            elif change_type == ChangeType.CHANGE_ENGINE:
                report_lines.append(f"  ~ CHANGE ENGINE: {diff['from']} -> {diff['to']}")
            
            elif change_type == ChangeType.CHANGE_CHARSET:
                report_lines.append(f"  ~ CHANGE CHARSET: {diff['from']} -> {diff['to']}")
            
            elif change_type == ChangeType.CHANGE_COLLATION:
                report_lines.append(f"  ~ CHANGE COLLATION: {diff['from']} -> {diff['to']}")
        
        return "\n".join(report_lines)

    def generate_rollback_statements(self, table_name: str, differences: List[Dict[str, Any]]) -> List[str]:
        """Generate rollback ALTER TABLE statements from a list of differences."""
        if not differences:
            return []
        
        statements = []
        alter_clauses = []
        separate_statements = []
        
        # Generate reverse operations for rollback
        for diff in reversed(differences):  # Reverse order for rollback
            change_type = diff['type']
            
            # Reverse operations for rollback
            if change_type == ChangeType.ADD_COLUMN:
                # Rollback: DROP the column that was added
                clause = f"DROP COLUMN `{diff['column'].name}`"
                alter_clauses.append(clause)
            
            elif change_type == ChangeType.DROP_COLUMN:
                # Rollback: ADD the column that was dropped
                clause = self._generate_add_column_clause(diff['column'])
                if clause:
                    alter_clauses.append(clause)
            
            elif change_type == ChangeType.MODIFY_COLUMN:
                # Rollback: MODIFY back to original column definition
                clause = self._generate_modify_column_clause(diff['column_name'], diff['from'])
                if clause:
                    alter_clauses.append(clause)
            
            elif change_type == ChangeType.ADD_INDEX:
                # Rollback: DROP the index that was added
                stmt = self._generate_drop_index_statement(table_name, diff['index'])
                if stmt:
                    separate_statements.append(stmt)
            
            elif change_type == ChangeType.DROP_INDEX:
                # Rollback: ADD the index that was dropped
                stmt = self._generate_add_index_statement(table_name, diff['index'])
                if stmt:
                    separate_statements.append(stmt)
            
            elif change_type == ChangeType.ADD_FOREIGN_KEY:
                # Rollback: DROP the foreign key that was added
                stmt = self._generate_drop_foreign_key_statement(table_name, diff['foreign_key'])
                if stmt:
                    separate_statements.append(stmt)
            
            elif change_type == ChangeType.DROP_FOREIGN_KEY:
                # Rollback: ADD the foreign key that was dropped
                stmt = self._generate_add_foreign_key_statement(table_name, diff['foreign_key'])
                if stmt:
                    separate_statements.append(stmt)
        
        # Combine column/table changes into single ALTER TABLE statement
        if alter_clauses:
            alter_sql = f"ALTER TABLE `{self.dest_schema}`.`{table_name}`\n  " + ",\n  ".join(alter_clauses)
            statements.append(alter_sql)
        
        # Add separate index statements
        statements.extend(separate_statements)
        
        return statements
    
    def generate_stored_object_migration(self, object_type: str, obj_name: str, 
                                       source_ddl: str, dest_ddl: str = None) -> List[str]:
        """Generate migration statements for stored procedures, functions, and triggers.
        
        Uses the drop-and-recreate approach as recommended for these object types.
        """
        statements = []
        
        # Generate DROP statement if object exists in destination
        if dest_ddl:
            drop_stmt = self._generate_drop_statement(object_type, obj_name)
            if drop_stmt:
                statements.append(drop_stmt)
        
        # Generate CREATE statement from source
        if source_ddl:
            create_stmt = self._adapt_ddl_for_destination(source_ddl)
            if create_stmt:
                statements.append(create_stmt + ";")
        
        return statements
    
    def generate_stored_object_rollback(self, object_type: str, obj_name: str, 
                                      source_ddl: str, dest_ddl: str = None) -> List[str]:
        """Generate rollback statements for stored procedures, functions, and triggers.
        
        For rollback, drop the object that was created/modified and recreate the original.
        """
        statements = []
        
        # Drop the current object (that was created from source)
        drop_stmt = self._generate_drop_statement(object_type, obj_name)
        if drop_stmt:
            statements.append(drop_stmt)
        
        # Recreate the original object if it existed in destination
        if dest_ddl:
            create_stmt = self._adapt_ddl_for_destination(dest_ddl)
            if create_stmt:
                statements.append(create_stmt + ";")
        
        return statements
    
    def _generate_drop_statement(self, object_type: str, obj_name: str) -> str:
        """Generate DROP statement for database objects."""
        if object_type == 'functions':
            return f"DROP FUNCTION IF EXISTS `{self.dest_schema}`.`{obj_name}`;"
        elif object_type == 'procedures':
            return f"DROP PROCEDURE IF EXISTS `{self.dest_schema}`.`{obj_name}`;"
        elif object_type == 'triggers':
            return f"DROP TRIGGER IF EXISTS `{self.dest_schema}`.`{obj_name}`;"
        elif object_type == 'events':
            return f"DROP EVENT IF EXISTS `{self.dest_schema}`.`{obj_name}`;"
        return ""
    
    def _adapt_ddl_for_destination(self, ddl: str) -> str:
        """Adapt DDL for destination schema."""
        if not ddl:
            return ""
        
        # Remove trailing semicolon if present
        adapted_ddl = ddl.strip()
        if adapted_ddl.endswith(';'):
            adapted_ddl = adapted_ddl[:-1]
        
        return adapted_ddl
