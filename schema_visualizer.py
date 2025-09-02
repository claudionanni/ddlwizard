"""
Visualization and documentation generator for DDL Wizard.
Creates visual representations and documentation of database schemas.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, Any]]
    referenced_by: List[str]
    comment: str = ""


@dataclass
class RelationshipInfo:
    """Information about table relationships."""
    from_table: str
    to_table: str
    from_column: str
    to_column: str
    constraint_name: str
    relationship_type: str = "foreign_key"


class SchemaVisualizer:
    """Creates visual representations of database schemas."""
    
    def __init__(self):
        self.tables: Dict[str, TableInfo] = {}
        self.relationships: List[RelationshipInfo] = {}
    
    def analyze_schema(self, schema_data: Dict[str, Any]):
        """Analyze schema data for visualization."""
        self.tables = {}
        self.relationships = []
        
        # Process tables
        if 'tables' in schema_data:
            for table_name, table_ddl in schema_data['tables'].items():
                self._analyze_table(table_name, table_ddl)
        
        # Extract relationships
        self._extract_relationships()
    
    def _analyze_table(self, table_name: str, table_ddl: str):
        """Analyze individual table structure."""
        try:
            # This is a simplified parser - in production, you'd use a proper SQL parser
            columns = []
            indexes = []
            foreign_keys = []
            
            lines = table_ddl.split('\n')
            in_table_def = False
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('CREATE TABLE'):
                    in_table_def = True
                    continue
                
                if in_table_def and line.startswith('`') and 'int' in line.lower() or 'varchar' in line.lower() or 'decimal' in line.lower():
                    # Column definition
                    parts = line.split()
                    if len(parts) >= 2:
                        col_name = parts[0].strip('`')
                        col_type = parts[1]
                        
                        column_info = {
                            'name': col_name,
                            'type': col_type,
                            'nullable': 'NOT NULL' not in line.upper(),
                            'primary_key': 'PRIMARY KEY' in line.upper(),
                            'auto_increment': 'AUTO_INCREMENT' in line.upper(),
                            'default': self._extract_default(line)
                        }
                        columns.append(column_info)
                
                elif 'KEY' in line.upper() and 'FOREIGN' not in line.upper():
                    # Index definition
                    index_info = self._parse_index(line)
                    if index_info:
                        indexes.append(index_info)
                
                elif 'FOREIGN KEY' in line.upper():
                    # Foreign key definition
                    fk_info = self._parse_foreign_key(line, table_name)
                    if fk_info:
                        foreign_keys.append(fk_info)
            
            self.tables[table_name] = TableInfo(
                name=table_name,
                columns=columns,
                indexes=indexes,
                foreign_keys=foreign_keys,
                referenced_by=[]
            )
        
        except Exception as e:
            logger.error(f"Failed to analyze table {table_name}: {e}")
    
    def _extract_default(self, line: str) -> Optional[str]:
        """Extract default value from column definition."""
        if 'DEFAULT' in line.upper():
            parts = line.upper().split('DEFAULT')
            if len(parts) > 1:
                default_part = parts[1].strip()
                return default_part.split()[0].strip("',\"")
        return None
    
    def _parse_index(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse index definition."""
        try:
            if 'PRIMARY KEY' in line.upper():
                return {
                    'name': 'PRIMARY',
                    'type': 'PRIMARY',
                    'columns': self._extract_columns_from_index(line)
                }
            elif 'UNIQUE' in line.upper():
                return {
                    'name': self._extract_index_name(line),
                    'type': 'UNIQUE',
                    'columns': self._extract_columns_from_index(line)
                }
            elif 'KEY' in line.upper():
                return {
                    'name': self._extract_index_name(line),
                    'type': 'INDEX',
                    'columns': self._extract_columns_from_index(line)
                }
        except Exception as e:
            logger.debug(f"Failed to parse index: {line}, error: {e}")
        return None
    
    def _extract_index_name(self, line: str) -> str:
        """Extract index name from definition."""
        parts = line.strip().split()
        for i, part in enumerate(parts):
            if part.upper() == 'KEY' and i + 1 < len(parts):
                return parts[i + 1].strip('`')
        return "unnamed_index"
    
    def _extract_columns_from_index(self, line: str) -> List[str]:
        """Extract column names from index definition."""
        if '(' in line and ')' in line:
            columns_part = line[line.find('(') + 1:line.rfind(')')]
            return [col.strip('` ') for col in columns_part.split(',')]
        return []
    
    def _parse_foreign_key(self, line: str, table_name: str) -> Optional[Dict[str, Any]]:
        """Parse foreign key definition."""
        try:
            # Simplified FK parsing
            if 'REFERENCES' in line.upper():
                parts = line.split()
                fk_info = {
                    'constraint_name': '',
                    'column': '',
                    'referenced_table': '',
                    'referenced_column': ''
                }
                
                # Extract referenced table and column
                ref_index = -1
                for i, part in enumerate(parts):
                    if part.upper() == 'REFERENCES':
                        ref_index = i
                        break
                
                if ref_index >= 0 and ref_index + 1 < len(parts):
                    ref_table_part = parts[ref_index + 1]
                    fk_info['referenced_table'] = ref_table_part.strip('`')
                
                return fk_info
        except Exception as e:
            logger.debug(f"Failed to parse foreign key: {line}, error: {e}")
        return None
    
    def _extract_relationships(self):
        """Extract relationships between tables."""
        for table_name, table_info in self.tables.items():
            for fk in table_info.foreign_keys:
                if fk['referenced_table']:
                    relationship = RelationshipInfo(
                        from_table=table_name,
                        to_table=fk['referenced_table'],
                        from_column=fk['column'],
                        to_column=fk['referenced_column'],
                        constraint_name=fk['constraint_name']
                    )
                    self.relationships.append(relationship)
                    
                    # Add reverse reference
                    if fk['referenced_table'] in self.tables:
                        self.tables[fk['referenced_table']].referenced_by.append(table_name)
    
    def generate_mermaid_erd(self) -> str:
        """Generate Mermaid Entity Relationship Diagram."""
        mermaid = ["erDiagram"]
        
        # Add tables
        for table_name, table_info in self.tables.items():
            mermaid.append(f"    {table_name} {{")
            
            for column in table_info.columns:
                col_type = column['type']
                col_name = column['name']
                
                # Add type annotations
                annotations = []
                if column['primary_key']:
                    annotations.append("PK")
                if not column['nullable']:
                    annotations.append("NOT NULL")
                if column['auto_increment']:
                    annotations.append("AUTO_INCREMENT")
                
                annotation_str = f" \"{', '.join(annotations)}\"" if annotations else ""
                mermaid.append(f"        {col_type} {col_name}{annotation_str}")
            
            mermaid.append("    }")
        
        # Add relationships
        for rel in self.relationships:
            mermaid.append(f"    {rel.from_table} ||--o{{ {rel.to_table} : {rel.constraint_name}")
        
        return "\n".join(mermaid)
    
    def generate_graphviz_dot(self) -> str:
        """Generate Graphviz DOT format for ER diagram."""
        dot = ["digraph schema {"]
        dot.append("    rankdir=TB;")
        dot.append("    node [shape=record];")
        
        # Add tables
        for table_name, table_info in self.tables.items():
            columns = []
            for column in table_info.columns:
                col_str = f"{column['name']}: {column['type']}"
                if column['primary_key']:
                    col_str = f"<u>{col_str}</u>"  # Underline primary keys
                columns.append(col_str)
            
            columns_str = "|".join(columns)
            dot.append(f'    {table_name} [label="{{{table_name}|{columns_str}}}"];')
        
        # Add relationships
        for rel in self.relationships:
            dot.append(f"    {rel.from_table} -> {rel.to_table} [label=\"{rel.constraint_name}\"];")
        
        dot.append("}")
        return "\n".join(dot)
    
    def generate_html_documentation(self) -> str:
        """Generate HTML documentation for the schema."""
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <title>Database Schema Documentation</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        .table { margin-bottom: 30px; border: 1px solid #ddd; }",
            "        .table-header { background-color: #f5f5f5; padding: 10px; font-weight: bold; }",
            "        .column { padding: 5px 10px; border-bottom: 1px solid #eee; }",
            "        .primary-key { background-color: #ffffcc; }",
            "        .foreign-key { background-color: #ccffcc; }",
            "        .index { margin-top: 10px; font-size: 0.9em; color: #666; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>Database Schema Documentation</h1>",
            f"    <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        ]
        
        # Table of contents
        html.append("    <h2>Tables</h2>")
        html.append("    <ul>")
        for table_name in sorted(self.tables.keys()):
            html.append(f'        <li><a href="#{table_name}">{table_name}</a></li>')
        html.append("    </ul>")
        
        # Table details
        for table_name, table_info in sorted(self.tables.items()):
            html.append(f'    <div class="table" id="{table_name}">')
            html.append(f'        <div class="table-header">{table_name}</div>')
            
            # Columns
            html.append("        <div>")
            html.append("            <h4>Columns</h4>")
            for column in table_info.columns:
                css_class = "column"
                if column['primary_key']:
                    css_class += " primary-key"
                
                nullable = "NULL" if column['nullable'] else "NOT NULL"
                default = f", DEFAULT: {column['default']}" if column['default'] else ""
                auto_inc = ", AUTO_INCREMENT" if column['auto_increment'] else ""
                
                html.append(f'            <div class="{css_class}">')
                html.append(f"                <strong>{column['name']}</strong>: {column['type']} ({nullable}{default}{auto_inc})")
                html.append("            </div>")
            html.append("        </div>")
            
            # Indexes
            if table_info.indexes:
                html.append("        <div class='index'>")
                html.append("            <h4>Indexes</h4>")
                for index in table_info.indexes:
                    columns_str = ", ".join(index['columns'])
                    html.append(f"            <div>{index['name']} ({index['type']}): {columns_str}</div>")
                html.append("        </div>")
            
            # Foreign keys
            if table_info.foreign_keys:
                html.append("        <div class='index'>")
                html.append("            <h4>Foreign Keys</h4>")
                for fk in table_info.foreign_keys:
                    html.append(f"            <div>{fk['constraint_name']}: {fk['column']} → {fk['referenced_table']}.{fk['referenced_column']}</div>")
                html.append("        </div>")
            
            # Referenced by
            if table_info.referenced_by:
                html.append("        <div class='index'>")
                html.append("            <h4>Referenced By</h4>")
                html.append(f"            <div>{', '.join(table_info.referenced_by)}</div>")
                html.append("        </div>")
            
            html.append("    </div>")
        
        html.extend(["</body>", "</html>"])
        return "\n".join(html)
    
    def export_documentation(self, output_dir: str, formats: List[str] = None):
        """Export documentation in multiple formats."""
        if formats is None:
            formats = ['html', 'mermaid', 'dot', 'json']
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        try:
            if 'html' in formats:
                html_content = self.generate_html_documentation()
                with open(output_path / "schema_documentation.html", 'w') as f:
                    f.write(html_content)
                logger.info("Generated HTML documentation")
            
            if 'mermaid' in formats:
                mermaid_content = self.generate_mermaid_erd()
                with open(output_path / "schema_erd.mmd", 'w') as f:
                    f.write(mermaid_content)
                logger.info("Generated Mermaid ERD")
            
            if 'dot' in formats:
                dot_content = self.generate_graphviz_dot()
                with open(output_path / "schema_erd.dot", 'w') as f:
                    f.write(dot_content)
                logger.info("Generated Graphviz DOT file")
            
            if 'json' in formats:
                schema_json = {
                    'tables': {name: {
                        'columns': table.columns,
                        'indexes': table.indexes,
                        'foreign_keys': table.foreign_keys,
                        'referenced_by': table.referenced_by
                    } for name, table in self.tables.items()},
                    'relationships': [
                        {
                            'from_table': rel.from_table,
                            'to_table': rel.to_table,
                            'from_column': rel.from_column,
                            'to_column': rel.to_column,
                            'constraint_name': rel.constraint_name
                        } for rel in self.relationships
                    ]
                }
                
                with open(output_path / "schema_structure.json", 'w') as f:
                    json.dump(schema_json, f, indent=2)
                logger.info("Generated JSON schema structure")
        
        except Exception as e:
            logger.error(f"Failed to export documentation: {e}")


def generate_migration_report(comparison_result: Dict[str, Any], output_file: str):
    """Generate a comprehensive migration report."""
    try:
        report = [
            "# Database Migration Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- Source Schema: {comparison_result.get('source_schema', 'Unknown')}",
            f"- Destination Schema: {comparison_result.get('dest_schema', comparison_result.get('destination_schema', 'Unknown'))}",
            ""
        ]
        
        # Tables summary
        if 'tables' in comparison_result:
            tables_diff = comparison_result['tables']
            
            if 'added' in tables_diff:
                report.append(f"- Tables to add: {len(tables_diff['added'])}")
            if 'removed' in tables_diff:
                report.append(f"- Tables to remove: {len(tables_diff['removed'])}")
            if 'modified' in tables_diff:
                report.append(f"- Tables to modify: {len(tables_diff['modified'])}")
        
        report.append("")
        
        # Detailed changes
        if 'detailed_changes' in comparison_result:
            report.append("## Detailed Changes")
            report.append("")
            
            for change in comparison_result['detailed_changes']:
                report.append(f"### {change.get('type', 'Unknown')} - {change.get('object_name', 'Unknown')}")
                report.append(f"**Operation**: {change.get('operation', 'Unknown')}")
                
                if 'description' in change:
                    report.append(f"**Description**: {change['description']}")
                
                if 'sql' in change:
                    report.append("**SQL**:")
                    report.append("```sql")
                    report.append(change['sql'])
                    report.append("```")
                
                report.append("")
        
        # Safety warnings
        if 'safety_warnings' in comparison_result:
            report.append("## Safety Warnings")
            report.append("")
            
            for warning in comparison_result['safety_warnings']:
                report.append(f"- **{warning.get('level', 'WARNING')}**: {warning.get('message', 'Unknown warning')}")
            
            report.append("")
        
        # Write report
        with open(output_file, 'w') as f:
            f.write("\n".join(report))
        
        logger.info(f"Migration report generated: {output_file}")
    
    except Exception as e:
        logger.error(f"Failed to generate migration report: {e}")


# Import datetime for the documentation function
from datetime import datetime
