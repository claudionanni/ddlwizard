"""
DDL parser and analyzer for detecting structural differences in database objects.
"""

import re
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes that can be made to database objects."""
    ADD_COLUMN = "ADD_COLUMN"
    DROP_COLUMN = "DROP_COLUMN"
    MODIFY_COLUMN = "MODIFY_COLUMN"
    ADD_INDEX = "ADD_INDEX"
    DROP_INDEX = "DROP_INDEX"
    ADD_CONSTRAINT = "ADD_CONSTRAINT"
    DROP_CONSTRAINT = "DROP_CONSTRAINT"
    ADD_FOREIGN_KEY = "ADD_FOREIGN_KEY"
    DROP_FOREIGN_KEY = "DROP_FOREIGN_KEY"
    CHANGE_ENGINE = "CHANGE_ENGINE"
    CHANGE_CHARSET = "CHANGE_CHARSET"
    CHANGE_COLLATION = "CHANGE_COLLATION"


@dataclass
class ColumnDefinition:
    """Represents a table column definition."""
    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    auto_increment: bool = False
    charset: Optional[str] = None
    collation: Optional[str] = None
    comment: Optional[str] = None
    position: int = 0
    
    def __eq__(self, other):
        if not isinstance(other, ColumnDefinition):
            return False
        return (self.name == other.name and 
                self.data_type == other.data_type and
                self.nullable == other.nullable and
                self.default == other.default and
                self.auto_increment == other.auto_increment and
                self.charset == other.charset and
                self.collation == other.collation)


@dataclass
class IndexDefinition:
    """Represents a table index definition."""
    name: str
    columns: List[str]
    index_type: str = "BTREE"
    is_unique: bool = False
    is_primary: bool = False
    
    def __eq__(self, other):
        if not isinstance(other, IndexDefinition):
            return False
        return (self.name == other.name and
                self.columns == other.columns and
                self.index_type == other.index_type and
                self.is_unique == other.is_unique and
                self.is_primary == other.is_primary)


@dataclass
class ForeignKeyDefinition:
    """Represents a foreign key constraint definition."""
    name: str
    columns: List[str]
    referenced_table: str
    referenced_columns: List[str]
    on_delete: Optional[str] = None
    on_update: Optional[str] = None
    
    def __eq__(self, other):
        if not isinstance(other, ForeignKeyDefinition):
            return False
        return (self.name == other.name and
                self.columns == other.columns and
                self.referenced_table == other.referenced_table and
                self.referenced_columns == other.referenced_columns and
                self.on_delete == other.on_delete and
                self.on_update == other.on_update)


@dataclass
class TableStructure:
    """Represents the complete structure of a table."""
    name: str
    columns: Dict[str, ColumnDefinition]
    indexes: Dict[str, IndexDefinition]
    foreign_keys: Dict[str, ForeignKeyDefinition]
    engine: str = "InnoDB"
    charset: str = "utf8mb4"
    collation: str = "utf8mb4_general_ci"
    comment: Optional[str] = None
    
    def get_column_names(self) -> List[str]:
        """Get ordered list of column names."""
        return sorted(self.columns.keys(), key=lambda col: self.columns[col].position)


class DDLAnalyzer:
    """Analyzes DDL statements to extract structural information."""
    
    def __init__(self):
        pass
    
    def parse_create_table(self, ddl: str) -> TableStructure:
        """Parse CREATE TABLE statement and extract structure."""
        if not ddl or not ddl.strip():
            raise ValueError("Empty DDL statement")
        
        # Extract table name
        table_name_match = re.search(r'CREATE\s+TABLE\s+`?([^`\s]+)`?', ddl, re.IGNORECASE)
        if not table_name_match:
            raise ValueError("Could not extract table name from DDL")
        
        table_name = table_name_match.group(1)
        
        # Initialize table structure
        table = TableStructure(name=table_name, columns={}, indexes={}, foreign_keys={})
        
        # Extract table options
        self._extract_table_options(ddl, table)
        
        # Extract columns
        self._extract_columns(ddl, table)
        
        # Extract indexes
        self._extract_indexes(ddl, table)
        
        # Extract foreign keys
        self._extract_foreign_keys(ddl, table)
        
        return table
    
    def _extract_table_options(self, ddl: str, table: TableStructure):
        """Extract table-level options like ENGINE, CHARSET, etc."""
        # Extract ENGINE
        engine_match = re.search(r'ENGINE\s*=\s*(\w+)', ddl, re.IGNORECASE)
        if engine_match:
            table.engine = engine_match.group(1)
        
        # Extract DEFAULT CHARSET
        charset_match = re.search(r'DEFAULT\s+CHARSET\s*=\s*(\w+)', ddl, re.IGNORECASE)
        if charset_match:
            table.charset = charset_match.group(1)
        
        # Extract COLLATE
        collate_match = re.search(r'COLLATE\s*=\s*(\w+)', ddl, re.IGNORECASE)
        if collate_match:
            table.collation = collate_match.group(1)
        
        # Extract COMMENT
        comment_match = re.search(r'COMMENT\s*=\s*[\'"]([^\'"]*)[\'"]', ddl, re.IGNORECASE)
        if comment_match:
            table.comment = comment_match.group(1)
    
    def _extract_columns(self, ddl: str, table: TableStructure):
        """Extract column definitions from CREATE TABLE statement."""
        # Find the column definitions section
        match = re.search(r'CREATE\s+TABLE[^(]*\((.*)\)', ddl, re.IGNORECASE | re.DOTALL)
        if not match:
            return
        
        content = match.group(1)
        
        # Split by lines and process each potential column definition
        lines = content.split('\n')
        position = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('PRIMARY KEY') or line.startswith('KEY') or line.startswith('UNIQUE') or line.startswith('CONSTRAINT'):
                continue
            
            # Remove trailing comma
            line = line.rstrip(',')
            
            column = self._parse_column_definition(line, position)
            if column:
                table.columns[column.name] = column
                position += 1
    
    def _parse_column_definition(self, line: str, position: int) -> Optional[ColumnDefinition]:
        """Parse a single column definition line."""
        # Basic column pattern: `column_name` data_type [options]
        match = re.match(r'`?([^`\s]+)`?\s+([^,\s]+(?:\([^)]*\))?)', line, re.IGNORECASE)
        if not match:
            return None
        
        column_name = match.group(1)
        data_type = match.group(2)
        
        column = ColumnDefinition(name=column_name, data_type=data_type, position=position)
        
        # Check for NOT NULL
        column.nullable = 'NOT NULL' not in line.upper()
        
        # Check for AUTO_INCREMENT
        column.auto_increment = 'AUTO_INCREMENT' in line.upper()
        
        # Extract DEFAULT value
        default_match = re.search(r'DEFAULT\s+([^,\s]+(?:\s+[^,\s]+)*)', line, re.IGNORECASE)
        if default_match:
            default_value = default_match.group(1).strip()
            # Remove quotes if present
            if default_value.startswith("'") and default_value.endswith("'"):
                default_value = default_value[1:-1]
            column.default = default_value
        
        # Extract CHARACTER SET
        charset_match = re.search(r'CHARACTER\s+SET\s+(\w+)', line, re.IGNORECASE)
        if charset_match:
            column.charset = charset_match.group(1)
        
        # Extract COLLATE
        collate_match = re.search(r'COLLATE\s+(\w+)', line, re.IGNORECASE)
        if collate_match:
            column.collation = collate_match.group(1)
        
        # Extract COMMENT
        comment_match = re.search(r'COMMENT\s+[\'"]([^\'"]*)[\'"]', line, re.IGNORECASE)
        if comment_match:
            column.comment = comment_match.group(1)
        
        return column
    
    def _extract_indexes(self, ddl: str, table: TableStructure):
        """Extract index definitions from CREATE TABLE statement."""
        # Find the column definitions section
        match = re.search(r'CREATE\s+TABLE[^(]*\((.*)\)', ddl, re.IGNORECASE | re.DOTALL)
        if not match:
            return
        
        content = match.group(1)
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip().rstrip(',')
            
            # Primary key
            if line.upper().startswith('PRIMARY KEY'):
                index = self._parse_primary_key(line)
                if index:
                    table.indexes[index.name] = index
            
            # Unique key
            elif line.upper().startswith('UNIQUE KEY') or line.upper().startswith('UNIQUE'):
                index = self._parse_unique_key(line)
                if index:
                    table.indexes[index.name] = index
            
            # Regular key
            elif line.upper().startswith('KEY'):
                index = self._parse_regular_key(line)
                if index:
                    table.indexes[index.name] = index
    
    def _extract_foreign_keys(self, ddl: str, table: TableStructure):
        """Extract foreign key constraint definitions from CREATE TABLE statement."""
        # Find the column definitions section
        match = re.search(r'CREATE\s+TABLE[^(]*\((.*)\)', ddl, re.IGNORECASE | re.DOTALL)
        if not match:
            return
        
        content = match.group(1)
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip().rstrip(',')
            
            # Foreign key constraint
            if 'CONSTRAINT' in line.upper() and 'FOREIGN KEY' in line.upper():
                fk = self._parse_foreign_key(line)
                if fk:
                    table.foreign_keys[fk.name] = fk
    
    def _parse_primary_key(self, line: str) -> Optional[IndexDefinition]:
        """Parse PRIMARY KEY definition."""
        match = re.search(r'PRIMARY\s+KEY\s*\(([^)]+)\)', line, re.IGNORECASE)
        if not match:
            return None
        
        columns_str = match.group(1)
        columns = [col.strip().strip('`') for col in columns_str.split(',')]
        
        return IndexDefinition(
            name='PRIMARY',
            columns=columns,
            is_primary=True,
            is_unique=True
        )
    
    def _parse_unique_key(self, line: str) -> Optional[IndexDefinition]:
        """Parse UNIQUE KEY definition."""
        match = re.search(r'UNIQUE(?:\s+KEY)?\s+`?([^`\s]+)`?\s*\(([^)]+)\)', line, re.IGNORECASE)
        if not match:
            return None
        
        index_name = match.group(1)
        columns_str = match.group(2)
        columns = [col.strip().strip('`') for col in columns_str.split(',')]
        
        return IndexDefinition(
            name=index_name,
            columns=columns,
            is_unique=True
        )
    
    def _parse_regular_key(self, line: str) -> Optional[IndexDefinition]:
        """Parse regular KEY definition."""
        match = re.search(r'KEY\s+`?([^`\s]+)`?\s*\(([^)]+)\)', line, re.IGNORECASE)
        if not match:
            return None
        
        index_name = match.group(1)
        columns_str = match.group(2)
        columns = [col.strip().strip('`') for col in columns_str.split(',')]
        
        return IndexDefinition(
            name=index_name,
            columns=columns
        )
    
    def _parse_foreign_key(self, line: str) -> Optional[ForeignKeyDefinition]:
        """Parse FOREIGN KEY constraint definition."""
        # Pattern: CONSTRAINT `fk_name` FOREIGN KEY (`column`) REFERENCES `table` (`ref_column`)
        match = re.search(
            r'CONSTRAINT\s+`?([^`\s]+)`?\s+FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+`?([^`\s(]+)`?\s*\(([^)]+)\)',
            line, re.IGNORECASE
        )
        if not match:
            return None
        
        fk_name = match.group(1)
        columns_str = match.group(2)
        ref_table = match.group(3)
        ref_columns_str = match.group(4)
        
        columns = [col.strip().strip('`') for col in columns_str.split(',')]
        ref_columns = [col.strip().strip('`') for col in ref_columns_str.split(',')]
        
        # Extract ON DELETE/UPDATE actions
        on_delete = None
        on_update = None
        
        on_delete_match = re.search(r'ON\s+DELETE\s+(\w+(?:\s+\w+)*)', line, re.IGNORECASE)
        if on_delete_match:
            on_delete = on_delete_match.group(1).upper()
        
        on_update_match = re.search(r'ON\s+UPDATE\s+(\w+(?:\s+\w+)*)', line, re.IGNORECASE)
        if on_update_match:
            on_update = on_update_match.group(1).upper()
        
        return ForeignKeyDefinition(
            name=fk_name,
            columns=columns,
            referenced_table=ref_table,
            referenced_columns=ref_columns,
            on_delete=on_delete,
            on_update=on_update
        )
    
    def compare_table_structures(self, source: TableStructure, dest: TableStructure) -> List[Dict[str, Any]]:
        """Compare two table structures and return list of differences."""
        differences = []
        
        # Compare table-level options
        if source.engine != dest.engine:
            differences.append({
                'type': ChangeType.CHANGE_ENGINE,
                'from': dest.engine,
                'to': source.engine
            })
        
        if source.charset != dest.charset:
            differences.append({
                'type': ChangeType.CHANGE_CHARSET,
                'from': dest.charset,
                'to': source.charset
            })
        
        if source.collation != dest.collation:
            differences.append({
                'type': ChangeType.CHANGE_COLLATION,
                'from': dest.collation,
                'to': source.collation
            })
        
        # Compare columns
        source_columns = set(source.columns.keys())
        dest_columns = set(dest.columns.keys())
        
        # Columns to add (in source but not in dest)
        for col_name in source_columns - dest_columns:
            differences.append({
                'type': ChangeType.ADD_COLUMN,
                'column': source.columns[col_name]
            })
        
        # Columns to drop (in dest but not in source)
        for col_name in dest_columns - source_columns:
            differences.append({
                'type': ChangeType.DROP_COLUMN,
                'column': dest.columns[col_name]
            })
        
        # Columns to modify (different definitions)
        for col_name in source_columns & dest_columns:
            source_col = source.columns[col_name]
            dest_col = dest.columns[col_name]
            
            if source_col != dest_col:
                differences.append({
                    'type': ChangeType.MODIFY_COLUMN,
                    'column_name': col_name,
                    'from': dest_col,
                    'to': source_col
                })
        
        # Compare indexes
        source_indexes = set(source.indexes.keys())
        dest_indexes = set(dest.indexes.keys())
        
        # Indexes to add
        for idx_name in source_indexes - dest_indexes:
            differences.append({
                'type': ChangeType.ADD_INDEX,
                'index': source.indexes[idx_name]
            })
        
        # Indexes to drop
        for idx_name in dest_indexes - source_indexes:
            differences.append({
                'type': ChangeType.DROP_INDEX,
                'index': dest.indexes[idx_name]
            })
        
        # Indexes to modify (different definitions)
        for idx_name in source_indexes & dest_indexes:
            source_idx = source.indexes[idx_name]
            dest_idx = dest.indexes[idx_name]
            
            if source_idx != dest_idx:
                differences.append({
                    'type': ChangeType.DROP_INDEX,
                    'index': dest_idx
                })
                differences.append({
                    'type': ChangeType.ADD_INDEX,
                    'index': source_idx
                })
        
        # Compare foreign keys
        source_fks = set(source.foreign_keys.keys())
        dest_fks = set(dest.foreign_keys.keys())
        
        # Foreign keys to add
        for fk_name in source_fks - dest_fks:
            differences.append({
                'type': ChangeType.ADD_FOREIGN_KEY,
                'foreign_key': source.foreign_keys[fk_name]
            })
        
        # Foreign keys to drop
        for fk_name in dest_fks - source_fks:
            differences.append({
                'type': ChangeType.DROP_FOREIGN_KEY,
                'foreign_key': dest.foreign_keys[fk_name]
            })
        
        # Foreign keys to modify (different definitions)
        for fk_name in source_fks & dest_fks:
            source_fk = source.foreign_keys[fk_name]
            dest_fk = dest.foreign_keys[fk_name]
            
            if source_fk != dest_fk:
                differences.append({
                    'type': ChangeType.DROP_FOREIGN_KEY,
                    'foreign_key': dest_fk
                })
                differences.append({
                    'type': ChangeType.ADD_FOREIGN_KEY,
                    'foreign_key': source_fk
                })
        
        return differences
