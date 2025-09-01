"""
Dependency manager for DDL Wizard.
Handles foreign key dependencies and determines safe execution order for migrations.
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class ForeignKeyConstraint:
    """Represents a foreign key constraint."""
    name: str
    table: str
    columns: List[str]
    referenced_table: str
    referenced_columns: List[str]
    on_delete: str = "RESTRICT"
    on_update: str = "RESTRICT"


@dataclass
class ViewDependency:
    """Represents a view dependency."""
    view_name: str
    depends_on_tables: List[str]
    depends_on_views: List[str]


@dataclass
class DependencyInfo:
    """Complete dependency information for a schema."""
    foreign_keys: List[ForeignKeyConstraint]
    views: List[ViewDependency]
    table_dependencies: Dict[str, Set[str]]  # table -> set of tables it depends on
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """Get complete dependency graph including tables and views."""
        graph = defaultdict(set)
        
        # Add FK dependencies
        for fk in self.foreign_keys:
            graph[fk.table].add(fk.referenced_table)
        
        # Add view dependencies
        for view in self.views:
            for table in view.depends_on_tables:
                graph[view.view_name].add(table)
            for dep_view in view.depends_on_views:
                graph[view.view_name].add(dep_view)
        
        return dict(graph)


class DependencyManager:
    """Manages database object dependencies and execution order."""
    
    def __init__(self, database_manager):
        self.db_manager = database_manager
    
    def analyze_dependencies(self, schema: str) -> DependencyInfo:
        """Analyze all dependencies in a schema."""
        foreign_keys = self._get_foreign_keys(schema)
        views = self._get_view_dependencies(schema)
        
        # Build table dependency graph
        table_deps = defaultdict(set)
        for fk in foreign_keys:
            table_deps[fk.table].add(fk.referenced_table)
        
        return DependencyInfo(
            foreign_keys=foreign_keys,
            views=views,
            table_dependencies=dict(table_deps)
        )
    
    def _get_foreign_keys(self, schema: str) -> List[ForeignKeyConstraint]:
        """Extract foreign key constraints from schema."""
        foreign_keys = []
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for foreign key constraints
                cursor.execute("""
                    SELECT 
                        kcu.CONSTRAINT_NAME,
                        kcu.TABLE_NAME,
                        kcu.COLUMN_NAME,
                        kcu.REFERENCED_TABLE_NAME,
                        kcu.REFERENCED_COLUMN_NAME,
                        rc.DELETE_RULE,
                        rc.UPDATE_RULE
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                    JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc 
                        ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                        AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
                    WHERE kcu.CONSTRAINT_SCHEMA = %s
                        AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
                    ORDER BY kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
                """, (schema,))
                
                # Group by constraint name
                fk_data = defaultdict(lambda: {
                    'table': '',
                    'columns': [],
                    'referenced_table': '',
                    'referenced_columns': [],
                    'on_delete': 'RESTRICT',
                    'on_update': 'RESTRICT'
                })
                
                for row in cursor.fetchall():
                    constraint_name, table_name, column_name, ref_table, ref_column, delete_rule, update_rule = row
                    
                    fk_info = fk_data[constraint_name]
                    fk_info['table'] = table_name
                    fk_info['columns'].append(column_name)
                    fk_info['referenced_table'] = ref_table
                    fk_info['referenced_columns'].append(ref_column)
                    fk_info['on_delete'] = delete_rule or 'RESTRICT'
                    fk_info['on_update'] = update_rule or 'RESTRICT'
                
                # Convert to ForeignKeyConstraint objects
                for constraint_name, fk_info in fk_data.items():
                    foreign_keys.append(ForeignKeyConstraint(
                        name=constraint_name,
                        table=fk_info['table'],
                        columns=fk_info['columns'],
                        referenced_table=fk_info['referenced_table'],
                        referenced_columns=fk_info['referenced_columns'],
                        on_delete=fk_info['on_delete'],
                        on_update=fk_info['on_update']
                    ))
        
        except Exception as e:
            logger.error(f"Failed to extract foreign keys: {e}")
        
        return foreign_keys
    
    def _get_view_dependencies(self, schema: str) -> List[ViewDependency]:
        """Extract view dependencies from schema."""
        views = []
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all views in schema
                cursor.execute("""
                    SELECT TABLE_NAME, VIEW_DEFINITION
                    FROM INFORMATION_SCHEMA.VIEWS
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                """, (schema,))
                
                for view_name, view_definition in cursor.fetchall():
                    # Parse view definition to find table dependencies
                    table_deps, view_deps = self._parse_view_dependencies(view_definition, schema)
                    
                    views.append(ViewDependency(
                        view_name=view_name,
                        depends_on_tables=table_deps,
                        depends_on_views=view_deps
                    ))
        
        except Exception as e:
            logger.error(f"Failed to extract view dependencies: {e}")
        
        return views
    
    def _parse_view_dependencies(self, view_definition: str, schema: str) -> Tuple[List[str], List[str]]:
        """Parse view definition to extract table and view dependencies."""
        import re
        
        # Simple regex to find table/view references
        # This is a basic implementation - production code might need more sophisticated parsing
        table_pattern = r'FROM\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?|JOIN\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?'
        
        tables = set()
        views = set()
        
        matches = re.findall(table_pattern, view_definition, re.IGNORECASE)
        for match in matches:
            table_name = match[0] or match[1]
            if table_name:
                # Check if it's a table or view by querying information_schema
                try:
                    with self.db_manager.get_connection() as conn:
                        cursor = conn.cursor()
                        
                        # Check if it's a table
                        cursor.execute("""
                            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND TABLE_TYPE = 'BASE TABLE'
                        """, (schema, table_name))
                        
                        if cursor.fetchone()[0] > 0:
                            tables.add(table_name)
                        else:
                            # Check if it's a view
                            cursor.execute("""
                                SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS
                                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                            """, (schema, table_name))
                            
                            if cursor.fetchone()[0] > 0:
                                views.add(table_name)
                
                except Exception:
                    # If we can't determine, assume it's a table
                    tables.add(table_name)
        
        return list(tables), list(views)
    
    def order_operations_by_dependencies(self, operations: List[Dict], dependency_info: DependencyInfo) -> List[Dict]:
        """Order operations to respect dependencies."""
        dependency_graph = dependency_info.get_dependency_graph()
        
        # Separate operations by type
        create_ops = []
        alter_ops = []
        drop_ops = []
        
        for op in operations:
            if op.get('operation_type') == 'CREATE':
                create_ops.append(op)
            elif op.get('operation_type') == 'ALTER':
                alter_ops.append(op)
            elif op.get('operation_type') == 'DROP':
                drop_ops.append(op)
        
        ordered_operations = []
        
        # 1. First, disable foreign key checks if needed
        if dependency_info.foreign_keys:
            ordered_operations.append({
                'operation_type': 'SYSTEM',
                'sql': 'SET FOREIGN_KEY_CHECKS = 0;',
                'description': 'Disable foreign key checks'
            })
        
        # 2. Order CREATE operations by dependencies (dependencies first)
        ordered_creates = self._topological_sort_operations(create_ops, dependency_graph)
        ordered_operations.extend(ordered_creates)
        
        # 3. ALTER operations (can be done in any order with FK checks disabled)
        ordered_operations.extend(alter_ops)
        
        # 4. Order DROP operations by reverse dependencies (dependent objects first)
        reverse_graph = self._reverse_dependency_graph(dependency_graph)
        ordered_drops = self._topological_sort_operations(drop_ops, reverse_graph)
        ordered_operations.extend(ordered_drops)
        
        # 5. Re-enable foreign key checks
        if dependency_info.foreign_keys:
            ordered_operations.append({
                'operation_type': 'SYSTEM',
                'sql': 'SET FOREIGN_KEY_CHECKS = 1;',
                'description': 'Re-enable foreign key checks'
            })
        
        return ordered_operations
    
    def _topological_sort_operations(self, operations: List[Dict], dependency_graph: Dict[str, Set[str]]) -> List[Dict]:
        """Sort operations using topological sort based on dependencies."""
        # Extract table names from operations
        op_tables = {}
        for op in operations:
            table_name = op.get('table_name')
            if table_name:
                op_tables[table_name] = op
        
        # Perform topological sort
        sorted_tables = self._topological_sort(list(op_tables.keys()), dependency_graph)
        
        # Return operations in sorted order
        sorted_ops = []
        for table in sorted_tables:
            if table in op_tables:
                sorted_ops.append(op_tables[table])
        
        # Add any operations without table names at the end
        for op in operations:
            if not op.get('table_name'):
                sorted_ops.append(op)
        
        return sorted_ops
    
    def _topological_sort(self, nodes: List[str], dependency_graph: Dict[str, Set[str]]) -> List[str]:
        """Perform topological sort on dependency graph."""
        # Build in-degree count
        in_degree = defaultdict(int)
        for node in nodes:
            in_degree[node] = 0
        
        for node in nodes:
            for dependent in dependency_graph.get(node, set()):
                if dependent in in_degree:
                    in_degree[dependent] += 1
        
        # Queue of nodes with no dependencies
        queue = deque([node for node in nodes if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            # Remove this node from graph and update in-degrees
            for dependent in dependency_graph.get(node, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for circular dependencies
        if len(result) != len(nodes):
            logger.warning("Circular dependency detected in schema objects")
            # Add remaining nodes in original order
            for node in nodes:
                if node not in result:
                    result.append(node)
        
        return result
    
    def _reverse_dependency_graph(self, graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        """Reverse the dependency graph."""
        reversed_graph = defaultdict(set)
        
        for node, dependencies in graph.items():
            for dep in dependencies:
                reversed_graph[dep].add(node)
        
        return dict(reversed_graph)
    
    def generate_rollback_operations(self, migration_operations: List[Dict]) -> List[Dict]:
        """Generate rollback operations for a set of migration operations."""
        rollback_ops = []
        
        # Reverse the operations and generate opposite operations
        for op in reversed(migration_operations):
            rollback_op = self._generate_rollback_operation(op)
            if rollback_op:
                rollback_ops.append(rollback_op)
        
        return rollback_ops
    
    def _generate_rollback_operation(self, operation: Dict) -> Optional[Dict]:
        """Generate rollback operation for a single operation."""
        op_type = operation.get('operation_type')
        
        if op_type == 'CREATE':
            return {
                'operation_type': 'DROP',
                'table_name': operation.get('table_name'),
                'sql': f"DROP TABLE IF EXISTS {operation.get('table_name')};",
                'description': f"Rollback: Drop table {operation.get('table_name')}"
            }
        
        elif op_type == 'DROP':
            # For DROP operations, rollback would be CREATE (but we can't easily recreate)
            return {
                'operation_type': 'MANUAL',
                'table_name': operation.get('table_name'),
                'sql': f"-- MANUAL ROLLBACK REQUIRED: Recreate dropped table {operation.get('table_name')}",
                'description': f"Manual rollback required for dropped table"
            }
        
        elif op_type == 'ALTER':
            # For ALTER operations, we'd need to generate reverse ALTER
            return {
                'operation_type': 'MANUAL',
                'table_name': operation.get('table_name'),
                'sql': f"-- MANUAL ROLLBACK REQUIRED: Reverse ALTER on table {operation.get('table_name')}",
                'description': f"Manual rollback required for ALTER operation"
            }
        
        return None
