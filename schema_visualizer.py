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

"""
Visualization and documentation generator for DDL Wizard.
Creates visual representations and documentation of database schemas.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass
import json

# Import the new analyzers
from data_loss_analyzer import DataLossAnalyzer
from schema_dependency_analyzer import SchemaDependencyAnalyzer

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


def generate_migration_report(comparison_result: Dict[str, Any], migration_sql: str, output_file: str):
    """Generate a comprehensive migration report with data loss analysis and dependency visualization."""
    try:
        from datetime import datetime
        
        # Initialize analyzers
        data_loss_analyzer = DataLossAnalyzer()
        dependency_analyzer = SchemaDependencyAnalyzer()
        
        # Analyze data loss risks
        data_loss_warnings = data_loss_analyzer.analyze_migration_sql(migration_sql, comparison_result)
        
        # Generate dependency analysis if schema objects are available
        dependency_analysis = None
        if 'source_objects' in comparison_result:
            dest_objects = comparison_result.get('dest_objects', comparison_result.get('destination_objects'))
            print(f"🔍 VISUALIZER DEBUG: source_objects found")
            print(f"🔍 VISUALIZER DEBUG: dest_objects = {dest_objects is not None}")
            if dest_objects:
                print(f"🔍 VISUALIZER DEBUG: dest_objects keys = {list(dest_objects.keys())}")
            dependency_analysis = dependency_analyzer.analyze_schema_dependencies(
                comparison_result['source_objects'],
                dest_objects
            )
        else:
            print(f"❌ VISUALIZER DEBUG: No source_objects in comparison_result")
        
        report = [
            "# Database Migration Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- Source Schema: {comparison_result.get('source_schema', 'Unknown')}",
            f"- Destination Schema: {comparison_result.get('dest_schema', comparison_result.get('destination_schema', 'Unknown'))}",
            ""
        ]
        
        # Add data loss analysis section
        if data_loss_warnings:
            report.append("## ⚠️  DATA LOSS RISK ANALYSIS")
            report.append("")
            
            # Group warnings by risk level
            risk_groups = {}
            for warning in data_loss_warnings:
                risk_level = warning.risk_level.value
                if risk_level not in risk_groups:
                    risk_groups[risk_level] = []
                risk_groups[risk_level].append(warning)
            
            # Display warnings by severity
            for risk_level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if risk_level in risk_groups:
                    warnings = risk_groups[risk_level]
                    icon = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '⚡', 'LOW': 'ℹ️'}[risk_level]
                    
                    report.append(f"### {icon} {risk_level} Risk Operations ({len(warnings)})")
                    report.append("")
                    
                    for warning in warnings:
                        report.append(f"**{warning.operation}**: {warning.object_name}")
                        report.append(f"- **Impact**: {warning.impact}")
                        report.append(f"- **Mitigation**: {warning.mitigation}")
                        if warning.sql_statement:
                            report.append(f"- **SQL**: `{warning.sql_statement[:100]}...`")
                        report.append("")
            
            # Add summary statistics
            total_warnings = len(data_loss_warnings)
            critical_count = len(risk_groups.get('CRITICAL', []))
            high_count = len(risk_groups.get('HIGH', []))
            
            report.append(f"**Risk Summary**: {total_warnings} total warnings ({critical_count} critical, {high_count} high risk)")
            report.append("")
            
            if critical_count > 0:
                report.append("🛑 **RECOMMENDATION**: Do not proceed without addressing critical risks!")
                report.append("")
        else:
            report.append("## ✅ DATA LOSS ANALYSIS")
            report.append("")
            report.append("No potential data loss operations detected.")
            report.append("")
        
        # Add dependency analysis section
        if dependency_analysis:
            summary = dependency_analysis['summary']
            report.append("## 🔗 SCHEMA DEPENDENCY ANALYSIS")
            report.append("")
            
            report.append(f"- **Total Objects**: {summary['total_objects']}")
            report.append(f"- **Total Relationships**: {summary['total_relations']}")
            report.append("")
            
            # Objects by type
            if summary['objects_by_type']:
                report.append("### Objects by Type")
                for obj_type, count in summary['objects_by_type'].items():
                    report.append(f"- {obj_type.title()}: {count}")
                report.append("")
            
            # Most referenced objects (critical dependencies)
            if summary['most_referenced_objects']:
                report.append("### 📍 Most Referenced Objects (Critical Dependencies)")
                report.append("")
                for obj in summary['most_referenced_objects'][:5]:
                    if obj['dependent_count'] > 0:
                        report.append(f"- **{obj['name']}**: {obj['dependent_count']} dependents")
                report.append("")
                report.append("⚠️  **Note**: Changes to these objects may impact many other database objects.")
                report.append("")
            
            # Most dependent objects
            if summary['most_dependent_objects']:
                report.append("### 🔗 Most Dependent Objects")
                report.append("")
                for obj in summary['most_dependent_objects'][:5]:
                    if obj['dependency_count'] > 0:
                        report.append(f"- **{obj['name']}**: {obj['dependency_count']} dependencies")
                report.append("")
            
            # Isolated objects
            if summary['isolated_objects']:
                report.append("### 🏝️  Isolated Objects")
                report.append("")
                report.append("The following objects have no dependencies and are not referenced by other objects:")
                for obj in summary['isolated_objects'][:10]:  # Limit to first 10
                    report.append(f"- {obj}")
                if len(summary['isolated_objects']) > 10:
                    report.append(f"- ... and {len(summary['isolated_objects']) - 10} more")
                report.append("")
        
        # Tables summary
        if 'tables' in comparison_result:
            tables_diff = comparison_result['tables']
            
            report.append("## 📊 MIGRATION SUMMARY")
            report.append("")
            
            if 'only_in_source' in tables_diff:
                report.append(f"- Tables to add: {len(tables_diff['only_in_source'])}")
            if 'only_in_dest' in tables_diff:
                report.append(f"- Tables to remove: {len(tables_diff['only_in_dest'])}")
            if 'in_both' in tables_diff:
                report.append(f"- Tables to potentially modify: {len(tables_diff['in_both'])}")
        
        report.append("")
        
        # Detailed changes section
        report.append("## 📋 DETAILED CHANGES")
        report.append("")
        
        # Add sections for each object type
        object_types = ['tables', 'views', 'procedures', 'functions', 'triggers', 'events', 'sequences']
        
        for obj_type in object_types:
            if obj_type in comparison_result:
                obj_diff = comparison_result[obj_type]
                
                # Only add section if there are changes
                has_changes = (
                    obj_diff.get('only_in_source', []) or 
                    obj_diff.get('only_in_dest', []) or
                    obj_diff.get('in_both', [])
                )
                
                if has_changes:
                    report.append(f"### {obj_type.title()}")
                    report.append("")
                    
                    if obj_diff.get('only_in_source'):
                        report.append(f"**To be added ({len(obj_diff['only_in_source'])}):**")
                        for obj_name in obj_diff['only_in_source']:
                            report.append(f"- {obj_name}")
                        report.append("")
                    
                    if obj_diff.get('only_in_dest'):
                        report.append(f"**To be removed ({len(obj_diff['only_in_dest'])}):**")
                        for obj_name in obj_diff['only_in_dest']:
                            report.append(f"- {obj_name}")
                        report.append("")
                    
                    if obj_diff.get('in_both'):
                        report.append(f"**Exists in both (potential modifications) ({len(obj_diff['in_both'])}):**")
                        for obj_name in obj_diff['in_both']:
                            report.append(f"- {obj_name}")
                        report.append("")
        
        # Add visualization files info
        if dependency_analysis:
            report.append("## 📊 VISUALIZATION FILES")
            report.append("")
            report.append("The following visualization files have been generated:")
            report.append("- `schema_dependencies.json` - Raw dependency data")
            report.append("- `schema_dependencies.dot` - Graphviz format (use with `dot` command)")
            report.append("- `schema_dependencies.mmd` - Mermaid diagram (use with Mermaid tools)")
            report.append("- `dependency_report.txt` - Detailed text report")
            report.append("")
            report.append("**To generate visual diagrams:**")
            report.append("```bash")
            report.append("# For PNG image using Graphviz")
            report.append("dot -Tpng schema_dependencies.dot -o schema_dependencies.png")
            report.append("")
            report.append("# For SVG using Graphviz")
            report.append("dot -Tsvg schema_dependencies.dot -o schema_dependencies.svg")
            report.append("```")
            report.append("")
        
        # Add migration execution recommendations
        report.append("## 🚀 EXECUTION RECOMMENDATIONS")
        report.append("")
        
        if data_loss_warnings:
            critical_warnings = [w for w in data_loss_warnings if w.risk_level.value == 'CRITICAL']
            high_warnings = [w for w in data_loss_warnings if w.risk_level.value == 'HIGH']
            
            if critical_warnings:
                report.append("1. **🛑 STOP**: Critical data loss risks detected!")
                report.append("   - Review all critical warnings above")
                report.append("   - Export affected data before proceeding")
                report.append("   - Consider excluding risky operations")
                report.append("")
            elif high_warnings:
                report.append("1. **⚠️  CAUTION**: High data loss risks detected!")
                report.append("   - Review all high-risk warnings above")
                report.append("   - Test migration on a copy first")
                report.append("   - Ensure backups are available")
                report.append("")
        
        report.append("2. **💾 Backup**: Always create full database backup before migration")
        report.append("3. **🧪 Test**: Test migration on development/staging environment first")
        report.append("4. **📊 Monitor**: Monitor system performance after migration")
        report.append("5. **📋 Rollback**: Keep rollback script ready in case of issues")
        report.append("")
        
        # Write the report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        # Export dependency visualizations if available
        if dependency_analysis:
            output_dir = Path(output_file).parent
            # Pass comparison_result as migration_info for enhanced visualization
            dependency_analyzer.export_to_file(dependency_analysis, str(output_dir), comparison_result)
        
        logger.info(f"Enhanced migration report generated: {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to generate enhanced migration report: {e}")
        # Fallback to basic report
        _generate_basic_migration_report(comparison_result, output_file)


def _generate_basic_migration_report(comparison_result: Dict[str, Any], output_file: str):
    """Fallback basic migration report generation."""
    try:
        from datetime import datetime
        
        report = [
            "# Database Migration Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- Source Schema: {comparison_result.get('source_schema', 'Unknown')}",
            f"- Destination Schema: {comparison_result.get('dest_schema', comparison_result.get('destination_schema', 'Unknown'))}",
            ""
        ]
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
