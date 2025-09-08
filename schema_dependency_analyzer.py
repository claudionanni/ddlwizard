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
Schema Dependency Visualizer for DDL Wizard
Creates visual representations of database object dependencies
"""

import logging
import re
import json
from typing import Dict, List, Any, Set, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
@dataclass
class DependencyNode:
    """Represents a database object in the dependency graph"""
    name: str
    object_type: str  # 'table', 'view', 'procedure', 'function', 'trigger', 'event'
    schema: str
    dependencies: Set[str]  # Objects this depends on
    dependents: Set[str]    # Objects that depend on this
    source_type: str = 'source'  # 'source', 'destination_only'


@dataclass
class DependencyRelation:
    """Represents a dependency relationship between objects"""
    source_object: str
    source_type: str
    target_object: str
    target_type: str
    relation_type: str  # 'references', 'triggers_on', 'views', 'calls', etc.
    description: str


class SchemaDependencyAnalyzer:
    """Analyzes and visualizes dependencies between database objects"""
    
    def __init__(self):
        self.nodes = {}  # Dict[str, DependencyNode]
        self.relations = []  # List[DependencyRelation]
    
    def analyze_schema_dependencies(self, schema_objects: Dict[str, List[Dict]], dest_objects: Dict[str, List[Dict]] = None) -> Dict[str, Any]:
        """
        Analyze dependencies between schema objects, including destination objects for migration impact
        
        Args:
            schema_objects: Dictionary containing lists of source database objects by type
            dest_objects: Optional dictionary containing destination objects (for migration impact analysis)
            
        Returns:
            Dictionary containing dependency analysis results
        """
        self.nodes = {}
        self.relations = []
        
        # Create nodes for all source objects
        self._create_nodes(schema_objects, 'source')
        
        # If destination objects provided, add destination-only objects that will be dropped
        if dest_objects:
            self._add_destination_only_objects(schema_objects, dest_objects)
        
        # Analyze dependencies for source objects
        self._analyze_table_dependencies(schema_objects)
        self._analyze_view_dependencies(schema_objects)
        self._analyze_procedure_dependencies(schema_objects)
        self._analyze_function_dependencies(schema_objects)
        self._analyze_trigger_dependencies(schema_objects)
        self._analyze_event_dependencies(schema_objects)
        self._analyze_sequence_dependencies(schema_objects)
        
        # If destination objects exist, analyze dependencies for destination-only objects too
        if dest_objects:
            self._analyze_destination_dependencies(dest_objects)
        
        return {
            'nodes': {name: self._node_to_dict(node) for name, node in self.nodes.items()},
            'relations': [self._relation_to_dict(rel) for rel in self.relations],
            'summary': self._generate_summary()
        }
    
    def _create_nodes(self, schema_objects: Dict[str, List[Dict]], source_type: str = 'source'):
        """Create dependency nodes for all objects"""
        object_types = ['tables', 'views', 'procedures', 'functions', 'triggers', 'events', 'sequences']
        
        for obj_type in object_types:
            if obj_type in schema_objects:
                for obj in schema_objects[obj_type]:
                    node_name = obj['name']
                    self.nodes[node_name] = DependencyNode(
                        name=node_name,
                        object_type=obj_type[:-1],  # Remove 's' from plural
                        schema=obj.get('schema', 'unknown'),
                        source_type=source_type,
                        dependencies=set(),
                        dependents=set()
                    )
    
    def _analyze_table_dependencies(self, schema_objects: Dict[str, List[Dict]]):
        """Analyze foreign key dependencies between tables"""
        if 'tables' not in schema_objects:
            return
        
        for table in schema_objects['tables']:
            table_name = table['name']
            ddl = table.get('ddl', '')
            
            # Find foreign key references
            fk_refs = self._extract_foreign_key_references(ddl)
            for ref_table in fk_refs:
                if ref_table in self.nodes:
                    self._add_dependency(table_name, ref_table, 'foreign_key', 
                                       f"Table {table_name} has foreign key to {ref_table}")
    
    def _analyze_view_dependencies(self, schema_objects: Dict[str, List[Dict]]):
        """Analyze view dependencies on tables and other views"""
        if 'views' not in schema_objects:
            return
        
        for view in schema_objects['views']:
            view_name = view['name']
            ddl = view.get('ddl', '')
            
            # Extract table/view references from view definition
            referenced_objects = self._extract_table_references_from_sql(ddl)
            for ref_obj in referenced_objects:
                if ref_obj in self.nodes:
                    self._add_dependency(view_name, ref_obj, 'references', 
                                       f"View {view_name} references {ref_obj}")
    
    def _analyze_procedure_dependencies(self, schema_objects: Dict[str, List[Dict]]):
        """Analyze stored procedure dependencies"""
        if 'procedures' not in schema_objects:
            return
        
        for proc in schema_objects['procedures']:
            proc_name = proc['name']
            ddl = proc.get('ddl', '')
            
            # Extract table references
            referenced_tables = self._extract_table_references_from_sql(ddl)
            for ref_table in referenced_tables:
                if ref_table in self.nodes:
                    self._add_dependency(proc_name, ref_table, 'operates_on', 
                                       f"Procedure {proc_name} operates on {ref_table}")
            
            # Extract function calls
            called_functions = self._extract_function_calls(ddl)
            for func_name in called_functions:
                if func_name in self.nodes:
                    self._add_dependency(proc_name, func_name, 'calls', 
                                       f"Procedure {proc_name} calls function {func_name}")
    
    def _analyze_function_dependencies(self, schema_objects: Dict[str, List[Dict]]):
        """Analyze function dependencies"""
        if 'functions' not in schema_objects:
            return
        
        for func in schema_objects['functions']:
            func_name = func['name']
            ddl = func.get('ddl', '')
            
            # Extract table references
            referenced_tables = self._extract_table_references_from_sql(ddl)
            for ref_table in referenced_tables:
                if ref_table in self.nodes:
                    self._add_dependency(func_name, ref_table, 'reads_from', 
                                       f"Function {func_name} reads from {ref_table}")
    
    def _analyze_trigger_dependencies(self, schema_objects: Dict[str, List[Dict]]):
        """Analyze trigger dependencies"""
        if 'triggers' not in schema_objects:
            return
        
        for trigger in schema_objects['triggers']:
            trigger_name = trigger['name']
            ddl = trigger.get('ddl', '')
            
            # Extract the table this trigger is on
            trigger_table = self._extract_trigger_table(ddl)
            if trigger_table and trigger_table in self.nodes:
                self._add_dependency(trigger_name, trigger_table, 'triggers_on', 
                                   f"Trigger {trigger_name} is on table {trigger_table}")
            
            # Extract other table references in trigger body
            referenced_tables = self._extract_table_references_from_sql(ddl)
            for ref_table in referenced_tables:
                if ref_table in self.nodes and ref_table != trigger_table:
                    self._add_dependency(trigger_name, ref_table, 'references', 
                                       f"Trigger {trigger_name} references {ref_table}")
    
    def _analyze_event_dependencies(self, schema_objects: Dict[str, List[Dict]]):
        """Analyze event dependencies"""
        if 'events' not in schema_objects:
            return
        
        for event in schema_objects['events']:
            event_name = event['name']
            ddl = event.get('ddl', '')
            
            # Extract table references
            referenced_tables = self._extract_table_references_from_sql(ddl)
            for ref_table in referenced_tables:
                if ref_table in self.nodes:
                    self._add_dependency(event_name, ref_table, 'operates_on', 
                                       f"Event {event_name} operates on {ref_table}")
    
    def _analyze_sequence_dependencies(self, schema_objects: Dict[str, List[Dict]]):
        """Analyze sequence dependencies"""
        if 'sequences' not in schema_objects:
            return
        
        # Sequences typically have minimal dependencies, mainly used by tables for auto-increment
        # We could add logic to detect which tables use which sequences, but for now
        # sequences are standalone objects with no explicit dependencies
        for sequence in schema_objects['sequences']:
            sequence_name = sequence['name']
            # Sequences are typically standalone objects
            # Future enhancement: analyze which tables use this sequence for auto-increment
            pass
    
    def _extract_foreign_key_references(self, ddl: str) -> Set[str]:
        """Extract foreign key table references from DDL"""
        references = set()
        
        # Pattern for FOREIGN KEY ... REFERENCES table_name
        fk_pattern = r'FOREIGN\s+KEY.*?REFERENCES\s+(?:`)?(\w+)(?:`)?'
        matches = re.findall(fk_pattern, ddl, re.IGNORECASE | re.MULTILINE)
        references.update(matches)
        
        return references
    
    def _extract_table_references_from_sql(self, sql: str) -> Set[str]:
        """Extract table/view references from SQL statement"""
        references = set()
        
        # Remove comments and strings to avoid false positives
        cleaned_sql = self._clean_sql_for_parsing(sql)
        
        # Common patterns for table references
        patterns = [
            r'FROM\s+(?:`)?(\w+)(?:`)?',
            r'JOIN\s+(?:`)?(\w+)(?:`)?',
            r'UPDATE\s+(?:`)?(\w+)(?:`)?',
            r'INSERT\s+INTO\s+(?:`)?(\w+)(?:`)?',
            r'DELETE\s+FROM\s+(?:`)?(\w+)(?:`)?',
            r'INTO\s+(?:`)?(\w+)(?:`)?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, cleaned_sql, re.IGNORECASE)
            references.update(matches)
        
        # Filter out common SQL keywords and functions
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'ORDER', 'GROUP', 'HAVING', 'LIMIT',
            'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
            'TABLE', 'VIEW', 'INDEX', 'CONSTRAINT', 'PRIMARY', 'FOREIGN',
            'KEY', 'REFERENCES', 'NULL', 'NOT', 'DEFAULT', 'AUTO_INCREMENT',
            'UNIQUE', 'CHECK', 'IF', 'EXISTS', 'CASCADE', 'RESTRICT',
            'SET', 'DECLARE', 'BEGIN', 'END', 'WHILE', 'FOR', 'LOOP',
            'DUAL', 'INFORMATION_SCHEMA'
        }
        
        return {ref for ref in references if ref.upper() not in sql_keywords}
    
    def _extract_function_calls(self, sql: str) -> Set[str]:
        """Extract function calls from SQL"""
        functions = set()
        
        # Pattern for function calls (name followed by parentheses)
        func_pattern = r'(\w+)\s*\('
        matches = re.findall(func_pattern, sql, re.IGNORECASE)
        
        # Filter out built-in functions and keywords
        builtin_functions = {
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'NOW', 'CURDATE', 'CURTIME',
            'DATE', 'TIME', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND',
            'CONCAT', 'SUBSTRING', 'LENGTH', 'UPPER', 'LOWER', 'TRIM',
            'ROUND', 'CEIL', 'FLOOR', 'ABS', 'RAND', 'COALESCE', 'IFNULL',
            'CASE', 'WHEN', 'THEN', 'ELSE', 'IF', 'NULLIF', 'GREATEST',
            'LEAST', 'CAST', 'CONVERT', 'FORMAT', 'JSON_EXTRACT'
        }
        
        for func in matches:
            if func.upper() not in builtin_functions and func in self.nodes:
                functions.add(func)
        
        return functions
    
    def _extract_trigger_table(self, trigger_ddl: str) -> Optional[str]:
        """Extract the table name from trigger DDL"""
        # Pattern for CREATE TRIGGER ... ON table_name
        pattern = r'CREATE\s+TRIGGER.*?ON\s+(?:`)?(\w+)(?:`)?'
        match = re.search(pattern, trigger_ddl, re.IGNORECASE | re.MULTILINE)
        return match.group(1) if match else None
    
    def _clean_sql_for_parsing(self, sql: str) -> str:
        """Clean SQL for parsing by removing comments and strings"""
        # Remove single-line comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        
        # Remove multi-line comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Remove string literals (simplified)
        sql = re.sub(r"'[^']*'", '', sql)
        sql = re.sub(r'"[^"]*"', '', sql)
        
        return sql
    
    def _add_dependency(self, source: str, target: str, relation_type: str, description: str):
        """Add a dependency relationship"""
        if source in self.nodes and target in self.nodes:
            source_node = self.nodes[source]
            target_node = self.nodes[target]
            
            source_node.dependencies.add(target)
            target_node.dependents.add(source)
            
            self.relations.append(DependencyRelation(
                source_object=source,
                source_type=source_node.object_type,
                target_object=target,
                target_type=target_node.object_type,
                relation_type=relation_type,
                description=description
            ))
    
    def _node_to_dict(self, node: DependencyNode) -> Dict[str, Any]:
        """Convert node to dictionary for serialization"""
        return {
            'name': node.name,
            'object_type': node.object_type,
            'schema': node.schema,
            'source_type': getattr(node, 'source_type', 'source'),
            'dependencies': list(node.dependencies),
            'dependents': list(node.dependents),
            'dependency_count': len(node.dependencies),
            'dependent_count': len(node.dependents)
        }
    
    def _relation_to_dict(self, relation: DependencyRelation) -> Dict[str, Any]:
        """Convert relation to dictionary for serialization"""
        return {
            'source_object': relation.source_object,
            'source_type': relation.source_type,
            'target_object': relation.target_object,
            'target_type': relation.target_type,
            'relation_type': relation.relation_type,
            'description': relation.description
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate dependency analysis summary"""
        summary = {
            'total_objects': len(self.nodes),
            'total_relations': len(self.relations),
            'objects_by_type': {},
            'relations_by_type': {},
            'most_dependent_objects': [],
            'most_referenced_objects': [],
            'isolated_objects': []
        }
        
        # Count objects by type
        for node in self.nodes.values():
            obj_type = node.object_type
            if obj_type not in summary['objects_by_type']:
                summary['objects_by_type'][obj_type] = 0
            summary['objects_by_type'][obj_type] += 1
        
        # Count relations by type
        for relation in self.relations:
            rel_type = relation.relation_type
            if rel_type not in summary['relations_by_type']:
                summary['relations_by_type'][rel_type] = 0
            summary['relations_by_type'][rel_type] += 1
        
        # Find most dependent objects (have many dependencies)
        dependent_objects = sorted(
            [(name, len(node.dependencies)) for name, node in self.nodes.items()],
            key=lambda x: x[1], reverse=True
        )[:5]
        summary['most_dependent_objects'] = [
            {'name': name, 'dependency_count': count} for name, count in dependent_objects
        ]
        
        # Find most referenced objects (many dependents)
        referenced_objects = sorted(
            [(name, len(node.dependents)) for name, node in self.nodes.items()],
            key=lambda x: x[1], reverse=True
        )[:5]
        summary['most_referenced_objects'] = [
            {'name': name, 'dependent_count': count} for name, count in referenced_objects
        ]
        
        # Find isolated objects (no dependencies or dependents)
        isolated = [
            name for name, node in self.nodes.items()
            if len(node.dependencies) == 0 and len(node.dependents) == 0
        ]
        summary['isolated_objects'] = isolated
        
        return summary
    
    def _add_destination_only_objects(self, source_objects: Dict[str, List[Dict]], dest_objects: Dict[str, List[Dict]]):
        """Add destination-only objects that will be dropped by migration"""
        object_types = ['tables', 'views', 'procedures', 'functions', 'triggers', 'events']
        
        for obj_type in object_types:
            if obj_type in dest_objects:
                # Get names of objects in source and destination
                source_names = {obj['name'] for obj in source_objects.get(obj_type, [])}
                dest_names = {obj['name'] for obj in dest_objects.get(obj_type, [])}
                
                # Find objects only in destination (will be dropped)
                only_in_dest = dest_names - source_names
                
                for obj_name in only_in_dest:
                    # Find the actual object from destination
                    dest_obj = next((obj for obj in dest_objects[obj_type] if obj['name'] == obj_name), None)
                    if dest_obj:
                        self.nodes[obj_name] = DependencyNode(
                            name=obj_name,
                            object_type=obj_type[:-1],  # Remove 's' from plural
                            schema=dest_obj.get('schema', 'unknown'),
                            source_type='destination_only',  # Mark as destination-only
                            dependencies=set(),
                            dependents=set()
                        )
    
    def _analyze_destination_dependencies(self, dest_objects: Dict[str, List[Dict]]):
        """Analyze dependencies for destination-only objects that will be dropped"""
        # Only analyze dependencies for destination-only objects
        dest_only_nodes = {name: node for name, node in self.nodes.items() 
                          if getattr(node, 'source_type', 'source') == 'destination_only'}
        
        if not dest_only_nodes:
            return
        
        # For each destination-only object, check what depends on it
        for obj_type in ['tables', 'views', 'procedures', 'functions', 'triggers', 'events']:
            if obj_type not in dest_objects:
                continue
                
            for obj in dest_objects[obj_type]:
                obj_name = obj['name']
                
                # Only process if this is a destination-only object
                if obj_name not in dest_only_nodes:
                    continue
                
                # Check what other objects might depend on this destination-only object
                # This helps show what will be broken when this object is dropped
                for other_name, other_node in self.nodes.items():
                    if other_name != obj_name and getattr(other_node, 'source_type', 'source') == 'source':
                        # Check if the source object might reference this destination-only object
                        # This is a simplified check - in a real scenario, you'd analyze DDL more thoroughly
                        self._check_potential_dependency(other_name, obj_name, obj_type[:-1])
    
    def _check_potential_dependency(self, source_obj: str, dest_obj: str, dest_obj_type: str):
        """Check if source object potentially depends on destination object that will be dropped"""
        # This is a simplified implementation
        # In practice, you might want to analyze DDL of source objects to see if they reference dest_obj
        
        # For now, we'll create a potential dependency warning
        # You could enhance this by actually parsing the source object's DDL
        if source_obj in self.nodes and dest_obj in self.nodes:
            self._add_dependency(source_obj, dest_obj, 'potential_break', 
                               f"WARNING: {source_obj} may break when {dest_obj} ({dest_obj_type}) is dropped")

    def generate_graphviz_dot(self, analysis_result: Dict[str, Any], migration_info: Dict[str, Any] = None) -> str:
        """Generate Graphviz DOT format for visualization with migration highlighting"""
        
        # MASSIVE sizing for maximum readability
        num_objects = len(analysis_result['nodes'])
        
        # ULTRA-LARGE objects with COMPACT spacing for maximum readability
        width, height = 20, 15  # More manageable canvas size (was 30,25)
        node_sep, rank_sep = 0.75, 0.3  # Further reduced vertical spacing for tighter layout (was 0.5)
        
        dot_lines = []
        dot_lines.append('digraph schema_dependencies {')
        dot_lines.append('    rankdir=TB;')  # Top-bottom for large objects
        dot_lines.append(f'    size="{width},{height}!";')
        dot_lines.append('    ratio=fill;')
        dot_lines.append('    bgcolor=white;')
        dot_lines.append('    node [shape=box, style=filled, fontsize=160, fontname="Arial Black"];')  # LARGER fonts (140->160)
        dot_lines.append('    edge [fontsize=100, fontname="Arial Bold"];')  # Larger edge fonts
        dot_lines.append(f'    graph [label="Schema Migration Impact", labelloc="t", fontsize=180, fontname="Arial Black", nodesep={node_sep}, ranksep={rank_sep}];')
        dot_lines.append('')
        
        # NO LEGEND IN MAIN GRAPH - will be shown separately
        
        # Add main schema container with MASSIVE objects
        dot_lines.append('    // MASSIVE Schema Objects for Maximum Readability')
        dot_lines.append('')
        
        # Extract migration-affected objects
        migration_objects = set()
        migration_actions = {}
        
        # First, check for destination-only objects (will be dropped)
        for name, node_data in analysis_result['nodes'].items():
            source_type = node_data.get('source_type', 'source')
            if source_type == 'destination_only':
                migration_objects.add(name)
                migration_actions[name] = 'drop'
        
        # Then process migration_info if provided
        if migration_info:
            # Get objects from comparison data
            for obj_type in ['tables', 'views', 'procedures', 'functions', 'triggers', 'events', 'sequences']:
                if obj_type in migration_info:
                    type_data = migration_info[obj_type]
                    
                    # Objects to be created (only in source)
                    for obj_name in type_data.get('only_in_source', []):
                        migration_objects.add(obj_name)
                        migration_actions[obj_name] = 'create'
                    
                    # Objects to be dropped (only in dest) - might already be added above
                    for obj_name in type_data.get('only_in_dest', []):
                        migration_objects.add(obj_name)
                        migration_actions[obj_name] = 'drop'
                    
                    # Objects that exist in both schemas - check if they're actually modified
                    for obj_name in type_data.get('in_both', []):
                        # Only mark as modified if this object appears in migration SQL
                        # This prevents marking all objects as modified when only some actually change
                        # For now, don't mark in_both objects as modified by default
                        # They will be marked as modified only if they appear in migration SQL comments
                        pass
        
        # Additionally, parse migration SQL to find actually modified objects
        # Try to read migration.sql from the output directory
        migration_sql_content = None
        if hasattr(self, '_output_dir') and self._output_dir:
            migration_sql_path = Path(self._output_dir) / 'migration.sql'
            if migration_sql_path.exists():
                try:
                    with open(migration_sql_path, 'r') as f:
                        migration_sql_content = f.read()
                except Exception:
                    pass
        
        if migration_sql_content:
            import re
            # Parse migration SQL for modification comments
            modify_patterns = {
                'table': r'-- Modify table: (\w+)',
                'view': r'-- Modify view: (\w+)', 
                'procedure': r'-- Modify procedure: (\w+)',
                'function': r'-- Modify function: (\w+)',
                'trigger': r'-- Modify trigger: (\w+)',
                'event': r'-- Modify event: (\w+)',
                'sequence': r'-- Modify sequence: (\w+)'
            }
            
            for obj_type, pattern in modify_patterns.items():
                matches = re.findall(pattern, migration_sql_content, re.IGNORECASE)
                for obj_name in matches:
                    migration_objects.add(obj_name)
                    migration_actions[obj_name] = 'modify'
        
        # Define colors for different object types
        type_colors = {
            'table': 'lightblue',
            'view': 'lightgreen',
            'procedure': 'lightyellow',
            'function': 'lightcoral',
            'trigger': 'lightpink',
            'event': 'lightsalmon',
            'sequence': 'lavender'
        }
        
        # Define border colors for migration actions
        action_colors = {
            'create': 'green',
            'drop': 'red',
            'modify': 'orange',
            'unchanged': 'gray'
        }
        
        # Add nodes (inside schema container)
        for name, node_data in analysis_result['nodes'].items():
            obj_type = node_data['object_type']
            source_type = node_data.get('source_type', 'source')
            color = type_colors.get(obj_type, 'lightgray')
            
            # Determine migration status
            is_affected = name in migration_objects
            action = migration_actions.get(name, 'unchanged')
            border_color = action_colors.get(action, 'black')
            
            # Create label with dependency counts
            dep_count = node_data['dependency_count']
            dependent_count = node_data['dependent_count']
            
            # ULTRA-LARGE readable objects with REDUCED spacing and THICK borders
            if source_type == 'destination_only':
                # Keep the object type-specific fill color, but use red border for dropped objects
                label = f"{name}\\n[{obj_type.upper()}]\\n⚠ WILL BE DROPPED"
                dot_lines.append(f'    "{name}" [fillcolor={color}, color=red, penwidth=40, label="{label}", width=26, height=12, fontsize=160, fontname="Arial Black"];')
            elif is_affected:
                action_label = action.upper()
                if action == 'create':
                    label = f"{name}\\n[{obj_type.upper()}]\\n✓ {action_label}"
                    dot_lines.append(f'    "{name}" [fillcolor={color}, color={border_color}, penwidth=40, label="{label}", width=26, height=12, fontsize=160, fontname="Arial Black"];')
                elif action == 'modify':
                    label = f"{name}\\n[{obj_type.upper()}]\\n⚡ {action_label}"
                    dot_lines.append(f'    "{name}" [fillcolor={color}, color={border_color}, penwidth=40, label="{label}", width=26, height=12, fontsize=160, fontname="Arial Black"];')
                else:
                    label = f"{name}\\n[{obj_type.upper()}]\\n✗ {action_label}"
                    dot_lines.append(f'    "{name}" [fillcolor={color}, color={border_color}, penwidth=40, label="{label}", width=26, height=12, fontsize=160, fontname="Arial Black"];')
            else:
                label = f"{name}\\n[{obj_type.upper()}]"
                dot_lines.append(f'    "{name}" [fillcolor={color}, color=gray, penwidth=25, label="{label}", width=22, height=10, fontsize=140, fontname="Arial Bold"];')
        
        # Add only important relationships (reduce clutter)
        important_relations = []
        for relation in analysis_result['relations']:
            source = relation['source_object']
            target = relation['target_object']
            rel_type = relation['relation_type']
            
            # Only show the most important relationship types
            if rel_type in ['foreign_key', 'references']:
                important_relations.append(relation)
        
        # Group relations by type for cleaner display
        for relation in important_relations:
            source = relation['source_object']
            target = relation['target_object']
            rel_type = relation['relation_type']
            
            # Balanced edge styles - large and readable
            if rel_type == 'foreign_key':
                style = 'color=blue, penwidth=6, fontsize=90'
                label = 'FK'
            elif rel_type == 'references':
                style = 'color=green, penwidth=5, style=dashed, fontsize=90'
                label = 'REF'
            else:
                continue  # Skip other relation types to reduce clutter
            
            dot_lines.append(f'    "{source}" -> "{target}" [{style}, label="{label}"];')
        
        dot_lines.append('}')
        
        return '\n'.join(dot_lines)
    
    def generate_mermaid_diagram(self, analysis_result: Dict[str, Any]) -> str:
        """Generate Mermaid diagram format for web visualization"""
        mermaid_lines = []
        mermaid_lines.append('graph TD')
        
        # Add style definitions
        mermaid_lines.append('    classDef table fill:#87CEEB')
        mermaid_lines.append('    classDef view fill:#90EE90')
        mermaid_lines.append('    classDef procedure fill:#FFFFE0')
        mermaid_lines.append('    classDef function fill:#F08080')
        mermaid_lines.append('    classDef trigger fill:#FFB6C1')
        mermaid_lines.append('    classDef event fill:#FFA07A')
        mermaid_lines.append('')
        
        # Add nodes with classes
        node_classes = {}
        for name, node_data in analysis_result['nodes'].items():
            obj_type = node_data['object_type']
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name)
            
            dep_count = node_data['dependency_count']
            dependent_count = node_data['dependent_count']
            
            mermaid_lines.append(f'    {safe_name}["{name}<br/>({obj_type})<br/>Deps: {dep_count} | Used: {dependent_count}"]')
            node_classes[name] = safe_name
            
            # Apply class based on object type
            if obj_type in ['table', 'view', 'procedure', 'function', 'trigger', 'event']:
                mermaid_lines.append(f'    class {safe_name} {obj_type}')
        
        mermaid_lines.append('')
        
        # Add relationships
        for relation in analysis_result['relations']:
            source = relation['source_object']
            target = relation['target_object']
            rel_type = relation['relation_type']
            
            source_safe = node_classes.get(source, re.sub(r'[^a-zA-Z0-9]', '_', source))
            target_safe = node_classes.get(target, re.sub(r'[^a-zA-Z0-9]', '_', target))
            
            # Different arrow styles for different relations
            arrow_styles = {
                'foreign_key': '-->',
                'references': '-.->',
                'operates_on': '==>',
                'triggers_on': '==>',
                'calls': '-->'
            }
            
            arrow = arrow_styles.get(rel_type, '-->')
            mermaid_lines.append(f'    {source_safe} {arrow} {target_safe}')
        
        return '\n'.join(mermaid_lines)
    
    def export_to_file(self, analysis_result: Dict[str, Any], output_dir: str, migration_info: Dict[str, Any] = None):
        """Export dependency analysis to various formats"""
        # Store output directory for migration SQL parsing
        self._output_dir = output_dir
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Export JSON data
        json_file = output_path / 'schema_dependencies.json'
        with open(json_file, 'w') as f:
            json.dump(analysis_result, f, indent=2)
        
        # Export Graphviz DOT with migration highlighting
        dot_file = output_path / 'schema_dependencies.dot'
        with open(dot_file, 'w') as f:
            f.write(self.generate_graphviz_dot(analysis_result, migration_info))
        
        # Try to convert DOT to SVG automatically
        try:
            import subprocess
            svg_file = output_path / 'schema_dependencies_dot.svg'
            png_file = output_path / 'schema_dependencies_dot.png'
            
            # Generate SVG
            subprocess.run([
                'dot', '-Tsvg', str(dot_file), '-o', str(svg_file)
            ], check=True, capture_output=True)
            logger.info(f"Generated DOT SVG: {svg_file}")
            
            # Generate PNG
            subprocess.run([
                'dot', '-Tpng', str(dot_file), '-o', str(png_file)
            ], check=True, capture_output=True)
            logger.info(f"Generated DOT PNG: {png_file}")
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"Could not generate DOT graphics (Graphviz may not be installed): {e}")
        except Exception as e:
            logger.warning(f"Unexpected error generating DOT graphics: {e}")
        
        # Export Mermaid diagram
        mermaid_file = output_path / 'schema_dependencies.mmd'
        with open(mermaid_file, 'w') as f:
            f.write(self.generate_mermaid_diagram(analysis_result))
        
        # Export text report
        report_file = output_path / 'dependency_report.txt'
        with open(report_file, 'w') as f:
            f.write(self.generate_text_report(analysis_result))
        
        logger.info(f"Dependency analysis exported to {output_dir}")
    
    def generate_text_report(self, analysis_result: Dict[str, Any]) -> str:
        """Generate a text-based dependency report"""
        report = []
        summary = analysis_result['summary']
        
        report.append("SCHEMA DEPENDENCY ANALYSIS REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Summary statistics
        report.append("📊 SUMMARY")
        report.append("-" * 20)
        report.append(f"Total objects: {summary['total_objects']}")
        report.append(f"Total relationships: {summary['total_relations']}")
        report.append("")
        
        # Objects by type
        report.append("Objects by type:")
        for obj_type, count in summary['objects_by_type'].items():
            report.append(f"  {obj_type}: {count}")
        report.append("")
        
        # Relations by type
        report.append("Relationships by type:")
        for rel_type, count in summary['relations_by_type'].items():
            report.append(f"  {rel_type}: {count}")
        report.append("")
        
        # Most dependent objects
        if summary['most_dependent_objects']:
            report.append("🔗 MOST DEPENDENT OBJECTS")
            report.append("-" * 30)
            for obj in summary['most_dependent_objects']:
                if obj['dependency_count'] > 0:
                    report.append(f"  {obj['name']}: {obj['dependency_count']} dependencies")
            report.append("")
        
        # Most referenced objects
        if summary['most_referenced_objects']:
            report.append("📍 MOST REFERENCED OBJECTS")
            report.append("-" * 30)
            for obj in summary['most_referenced_objects']:
                if obj['dependent_count'] > 0:
                    report.append(f"  {obj['name']}: {obj['dependent_count']} dependents")
            report.append("")
        
        # Isolated objects
        if summary['isolated_objects']:
            report.append("🏝️  ISOLATED OBJECTS")
            report.append("-" * 20)
            for obj in summary['isolated_objects']:
                report.append(f"  {obj}")
            report.append("")
        
        # Detailed relationships
        report.append("🔍 DETAILED RELATIONSHIPS")
        report.append("-" * 30)
        for relation in analysis_result['relations']:
            source = relation['source_object']
            target = relation['target_object']
            rel_type = relation['relation_type']
            description = relation['description']
            report.append(f"  {source} --[{rel_type}]--> {target}")
            report.append(f"    {description}")
        
        return "\n".join(report)
