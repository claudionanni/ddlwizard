#!/usr/bin/env python3
"""Debug script to check view comparison logic."""

import sys
sys.path.append('.')

from database import DatabaseManager, DatabaseConfig
from schema_comparator import SchemaComparator

def main():
    # Create database connections
    source_config = DatabaseConfig('127.0.0.1', 10622, 'sstuser', 'sstpwd', 'ddlwizard_source_test')
    dest_config = DatabaseConfig('127.0.0.1', 20622, 'sstuser', 'sstpwd', 'ddlwizard_dest_test')
    
    source_db = DatabaseManager(source_config)
    dest_db = DatabaseManager(dest_config)
    
    # Get all objects
    print("=== EXTRACTING OBJECTS ===")
    source_objects = source_db.get_all_objects_with_ddl()
    dest_objects = dest_db.get_all_objects_with_ddl()
    
    print(f"\nSource views: {len(source_objects.get('views', []))}")
    for view in source_objects.get('views', []):
        print(f"  - {view['name']} (DDL length: {len(view.get('ddl', ''))})")
    
    print(f"\nDestination views: {len(dest_objects.get('views', []))}")
    for view in dest_objects.get('views', []):
        print(f"  - {view['name']} (DDL length: {len(view.get('ddl', ''))})")
    
    # Test comparison
    print("\n=== COMPARING SCHEMAS ===")
    comparator = SchemaComparator()
    comparison = comparator.compare_schemas(source_objects, dest_objects)
    
    print(f"\nView comparison results:")
    if 'views' in comparison:
        views_comp = comparison['views']
        print(f"  Only in source: {views_comp.get('only_in_source', [])}")
        print(f"  Only in dest: {views_comp.get('only_in_dest', [])}")
        print(f"  In both: {views_comp.get('in_both', [])}")
    else:
        print("  ERROR: No 'views' key in comparison!")
        print(f"  Available keys: {list(comparison.keys())}")

    # Helper functions for DDL retrieval
    def get_source_ddl(object_type: str, object_name: str) -> str:
        """Get DDL for source objects."""
        if object_type == 'views':
            return source_db.get_view_ddl(object_name)
        return ""
    
    def get_dest_ddl(object_type: str, object_name: str) -> str:
        """Get DDL for destination objects.""" 
        if object_type == 'views':
            return dest_db.get_view_ddl(object_name)
        return ""

    # Test view SQL generation step by step
    print("\n=== DEBUGGING SQL GENERATION ===")
    
    views_comparison = comparison.get('views', {})
    print(f"Views comparison data: {views_comparison}")
    
    print(f"\nTesting only_in_source views:")
    for view_name in sorted(views_comparison.get('only_in_source', [])):
        print(f"  Processing view: {view_name}")
        try:
            source_ddl = get_source_ddl('views', view_name)
            print(f"    DDL length: {len(source_ddl)}")
            print(f"    DDL preview: {source_ddl[:100]}...")
            if source_ddl:
                print(f"    ✅ Would create view: {view_name}")
            else:
                print(f"    ❌ Empty DDL for view: {view_name}")
        except Exception as e:
            print(f"    💥 Exception for view {view_name}: {e}")
    
    print(f"\nTesting only_in_dest views:")
    for view_name in sorted(views_comparison.get('only_in_dest', [])):
        print(f"  Processing view: {view_name}")
        print(f"    ✅ Would drop view: {view_name}")
    
    # Test migration SQL generation directly
    print("\n=== TESTING MIGRATION SQL GENERATION WITH EXCEPTION HANDLING ===")
    try:
        migration_sql = comparator.generate_migration_sql(
            comparison, get_source_ddl, get_dest_ddl, 
            'ddlwizard_source_test', 'ddlwizard_dest_test'
        )
        print("✅ Migration SQL generated successfully")
    except Exception as e:
        print(f"💥 Exception during migration SQL generation: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\nVIEW SECTIONS IN MIGRATION SQL:")
    lines = migration_sql.split('\n')
    in_view_section = False
    view_section_lines = []
    for i, line in enumerate(lines):
        if '-- VIEWS CHANGES' in line:
            in_view_section = True
            view_section_lines.append(f"{i+1}: {line}")
        elif in_view_section:
            if line.strip().startswith('--') and 'VIEWS' not in line and 'view' not in line.lower() and not line.strip().startswith('-- Create') and not line.strip().startswith('-- Drop') and not line.strip().startswith('-- Update'):
                break
            view_section_lines.append(f"{i+1}: {line}")
    
    print("\n".join(view_section_lines))
    
    if len(view_section_lines) <= 2:  # Only header and maybe separator
        print("\n💥 NO VIEW STATEMENTS GENERATED!")
        print("This indicates a bug in the schema_comparator.py generate_migration_sql function")
    else:
        print(f"\n✅ Generated {len(view_section_lines)} view-related lines")

if __name__ == "__main__":
    main()
