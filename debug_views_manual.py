#!/usr/bin/env python3
"""Debug script to test the exact view SQL generation logic."""

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
    
    # Get comparison
    source_objects = source_db.get_all_objects_with_ddl()
    dest_objects = dest_db.get_all_objects_with_ddl()
    
    comparator = SchemaComparator()
    comparison = comparator.compare_schemas(source_objects, dest_objects)
    
    # Helper functions
    def get_source_ddl(object_type: str, object_name: str) -> str:
        if object_type == 'views':
            return source_db.get_view_ddl(object_name)
        return ""
    
    def get_dest_ddl(object_type: str, object_name: str) -> str:
        if object_type == 'views':
            return dest_db.get_view_ddl(object_name)
        return ""
    
    # Manually replicate the view processing logic from schema_comparator.py
    print("=== MANUALLY REPLICATING VIEW PROCESSING LOGIC ===")
    
    views_comparison = comparison['views']
    dest_schema = 'ddlwizard_dest_test'
    sql_lines = []
    
    print(f"Views comparison: {views_comparison}")
    
    # Check if we should process views at all
    should_process = (views_comparison.get('only_in_source') or 
                     views_comparison.get('only_in_dest') or 
                     views_comparison.get('in_both'))
    print(f"Should process views: {should_process}")
    
    if should_process:
        sql_lines.extend([
            "",
            "-- VIEWS CHANGES", 
            "--" + "-" * 48
        ])
        
        # Views only in source (to be created)
        print(f"\nProcessing only_in_source views: {views_comparison.get('only_in_source', [])}")
        for view_name in sorted(views_comparison.get('only_in_source', [])):
            print(f"  Processing view: {view_name}")
            try:
                print(f"    Getting source DDL...")
                source_ddl = get_source_ddl('views', view_name)
                print(f"    Source DDL length: {len(source_ddl)}")
                
                if source_ddl:
                    print(f"    Source DDL exists, adding CREATE statements...")
                    sql_lines.append(f"-- Create view: {view_name}")
                    sql_lines.append(f"DROP VIEW IF EXISTS `{dest_schema}`.`{view_name}`;")
                    
                    print(f"    Adapting DDL for destination...")
                    adapted_ddl = comparator._adapt_ddl_for_destination(source_ddl, dest_schema)
                    print(f"    Adapted DDL length: {len(adapted_ddl)}")
                    
                    sql_lines.append(adapted_ddl)
                    sql_lines.append("")
                    print(f"    ✅ Successfully processed view: {view_name}")
                else:
                    print(f"    ❌ Empty source DDL for view: {view_name}")
            except Exception as e:
                print(f"    💥 Exception processing view {view_name}: {e}")
                import traceback
                traceback.print_exc()
                sql_lines.append(f"-- ERROR: Failed to process view {view_name}")
        
        # Views only in dest (to be dropped)
        print(f"\nProcessing only_in_dest views: {views_comparison.get('only_in_dest', [])}")
        for view_name in sorted(views_comparison.get('only_in_dest', [])):
            print(f"  Processing view: {view_name}")
            sql_lines.append(f"-- Drop view: {view_name}")
            sql_lines.append(f"DROP VIEW IF EXISTS `{dest_schema}`.`{view_name}`;")
            sql_lines.append("")
            print(f"    ✅ Successfully processed view: {view_name}")
    
    print(f"\n=== GENERATED SQL LINES ===")
    for i, line in enumerate(sql_lines):
        print(f"{i+1}: {line}")
    
    print(f"\nTotal lines generated: {len(sql_lines)}")

if __name__ == "__main__":
    main()
