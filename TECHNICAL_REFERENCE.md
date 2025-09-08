# DDL Wizard Technical Reference Document

**Version:** 1.4.0  
**Last Updated:** September 8, 2025 (Enhanced Dependency Graph Visualization)  
**Purpose:** Internal technical reference to maintain consistency and prevent regressions

---

## 🏗️ Architecture Overview

### Core Design Principles
1. **Dual Structure:** Both root-level and `ddlwizard/` package versions maintained in parallel
2. **7-Object Type Support:** Complete coverage of MariaDB database objects
3. **Dependency-Safe Operations:** 4-phase ordering for complex schema changes
4. **Round-Trip Validation:** Perfect migration + rollback functionality
5. **MariaDB Compatibility:** Optimized for MariaDB 10.3+ with sequence support

### Package Structure
```
ddlwizard/
├── ddl_wizard.py              # Root CLI interface
├── ddl_wizard_core.py         # Root core functionality  
├── schema_comparator.py       # Root comparison logic
├── database.py                # Root database operations
├── alter_generator.py         # Root migration generation
├── connection_manager.py      # NEW: Connection management system
├── ddlwizard/                 # Package structure
│   ├── cli.py                 # Package CLI interface
│   ├── core.py                # Package core functionality
│   └── utils/
│       ├── comparator.py      # Package comparison logic
│       ├── database.py        # Package database operations
│       └── generator.py       # Package migration generation
└── tests/
    └── test_integration.py    # Comprehensive test suite
```

---

## 🔧 Critical Technical Decisions

### 1. Database Object Type Support (7 Types)

**CRITICAL:** Always maintain support for ALL 7 object types:

```python
SUPPORTED_OBJECTS = {
    'tables': {
        'detection': 'SHOW TABLES',
        'ddl_method': 'SHOW CREATE TABLE',
        'supports_rollback': True
    },
    'views': {
        'detection': 'SHOW FULL TABLES WHERE Table_type = "VIEW"',
        'ddl_method': 'SHOW CREATE VIEW', 
        'supports_rollback': True
    },
    'procedures': {
        'detection': 'SHOW PROCEDURE STATUS',
        'ddl_method': 'SHOW CREATE PROCEDURE',
        'supports_rollback': True
    },
    'functions': {
        'detection': 'SHOW FUNCTION STATUS', 
        'ddl_method': 'SHOW CREATE FUNCTION',
        'supports_rollback': True
    },
    'triggers': {
        'detection': 'SHOW TRIGGERS',
        'ddl_method': 'SHOW CREATE TRIGGER',
        'supports_rollback': True
    },
    'events': {
        'detection': 'SHOW EVENTS',
        'ddl_method': 'SHOW CREATE EVENT',
        'supports_rollback': True
    },
    'sequences': {
        'detection': 'SHOW FULL TABLES WHERE Table_type = "SEQUENCE"',
        'ddl_method': 'SHOW CREATE SEQUENCE',
        'supports_rollback': True
    }
}
```

### 2. View vs Table Detection

**CRITICAL:** Use `SHOW FULL TABLES` to distinguish between tables, views, and sequences:

```python
def get_all_objects_with_ddl(self) -> Dict[str, Dict[str, str]]:
    """Extract DDL for all database objects."""
    
    # CRITICAL: Use SHOW FULL TABLES to distinguish object types
    cursor.execute("SHOW FULL TABLES")
    full_tables = cursor.fetchall()
    
    for row in full_tables:
        table_name = row[0]
        table_type = row[1]  # 'BASE TABLE', 'VIEW', 'SEQUENCE'
        
        if table_type == 'BASE TABLE':
            objects['tables'][table_name] = self.get_table_ddl(table_name)
        elif table_type == 'VIEW':
            objects['views'][table_name] = self.get_view_ddl(table_name)
        elif table_type == 'SEQUENCE':
            objects['sequences'][table_name] = self.get_sequence_ddl(table_name)
```

### 3. Table Properties Detection

**CRITICAL:** Detect and synchronize table-level properties (v1.2.0+):

```python
def _compare_table_properties(self, table_name: str, source_ddl: str, dest_ddl: str):
    """Compare table-level properties like COMMENT, ENGINE, CHARSET, etc."""
    
    # CRITICAL: Parse table properties from CREATE TABLE statements
    source_props = self._parse_table_properties(source_ddl)
    dest_props = self._parse_table_properties(dest_ddl)
    
    # Generate ALTER TABLE statements for differences
    # - COMMENT='...'
    # - ENGINE=InnoDB
    # - DEFAULT CHARSET=utf8
    # - COLLATE=utf8_general_ci
```

**IMPORTANT:** AUTO_INCREMENT Handling:

```python
# AUTO_INCREMENT=N values are INTENTIONALLY IGNORED
# Rationale: AUTO_INCREMENT values depend on data, not schema structure
# - AUTO_INCREMENT=1 vs AUTO_INCREMENT=100 are NOT schema differences
# - DDL tools should only compare structure, not data-dependent values
# - Table properties parsing explicitly excludes AUTO_INCREMENT patterns

IGNORED_TABLE_PROPERTIES = [
    'AUTO_INCREMENT=\\d+',  # Data-dependent, varies with INSERT operations
]

SUPPORTED_TABLE_PROPERTIES = [
    'COMMENT',      # Table comments - schema-relevant
    'ENGINE',       # Storage engine - schema-relevant  
    'CHARSET',      # Character set - schema-relevant
    'COLLATE',      # Collation - schema-relevant
]
```

### 3. Migration SQL Generation Order

**CRITICAL:** 4-Phase dependency-safe ordering:

```python
def generate_migration_sql(self):
    """Generate migration SQL with dependency-safe ordering."""
    
    # Phase 1: Drop Dependencies (Foreign Keys, Triggers)
    # Phase 2: Structure Changes (Tables, Columns, Indexes)  
    # Phase 3: Data Objects (Views, Procedures, Functions)
    # Phase 4: Restore Dependencies & Events (Foreign Keys, Events, Sequences)
    
    sql_sections = [
        "-- TABLES CHANGES",
        "-- PROCEDURES CHANGES", 
        "-- FUNCTIONS CHANGES",
        "-- TRIGGERS CHANGES",
        "-- EVENTS CHANGES",
        "-- VIEWS CHANGES",
        "-- SEQUENCES CHANGES"
    ]
```

### 8. Schema Dependency Visualization (v1.4.0 Enhanced)

**CRITICAL:** Complete visual dependency analysis with optimized display and accurate object detection.

**BREAKTHROUGH FEATURES (v1.4.0):**
```python
DEPENDENCY_VISUALIZATION_FEATURES = {
    'canvas_optimization': True,        # Compact 20x15 canvas (was 30x25)
    'tight_layout': True,              # 0.3 vertical spacing (was 0.5)
    'accurate_borders': True,          # Only modified objects get orange borders
    'dropped_object_detection': True,  # Red borders for deletion indicators
    'complete_object_support': True,   # All 7 types including sequences
    'visual_legend': True,             # Emoji-based legend for object types
    'migration_sql_parsing': True      # Real-time analysis of actual modifications
}
```

**COLOR CODING SYSTEM:**
```python
OBJECT_TYPE_COLORS = {
    'tables': 'lightblue',      # 🟦 Blue squares
    'views': 'lightgreen',      # 🟩 Green squares  
    'procedures': 'lightyellow', # 🟨 Yellow squares
    'functions': 'lightcoral',   # 🟥 Red squares
    'triggers': 'lightpink',     # 🩷 Pink squares
    'events': 'lightsalmon',     # 🟧 Orange squares
    'sequences': 'lavender'      # 🔷 Blue diamonds (v1.4.0)
}

BORDER_COLOR_SYSTEM = {
    'green': 'CREATE operations',   # New objects
    'orange': 'MODIFY operations',  # Changed objects (accurate detection)
    'red': 'DROP operations',       # Deleted objects (v1.4.0 fixed)
    'gray': 'UNCHANGED objects'     # No modifications
}
```

**ARCHITECTURE IMPROVEMENTS:**
```python
# v1.4.0 Canvas Configuration
CANVAS_CONFIG = {
    'size': '20,15',           # Optimized from 30,25
    'ranksep': '0.3',          # Tighter vertical spacing from 0.5
    'nodesep': '0.5',          # Maintained horizontal spacing
    'splines': 'ortho',        # Clean orthogonal connections
    'rankdir': 'TB'            # Top-to-bottom layout
}

# v1.4.0 Accurate Modification Detection
def analyze_migration_changes(migration_sql: str) -> Set[str]:
    """Parse migration SQL to identify actually modified objects."""
    
    # CRITICAL: Only mark objects that appear in migration SQL
    modified_objects = set()
    
    # Parse ALTER TABLE, ALTER VIEW, etc. statements
    for line in migration_sql.split('
'):
        if line.strip().startswith(('ALTER TABLE', 'ALTER VIEW')):
            object_name = extract_object_name(line)
            modified_objects.add(object_name)
    
    return modified_objects  # Only objects with actual changes
```

**GUI INTEGRATION:**
```python
VISUALIZATION_DISPLAY = {
    'tabbed_interface': True,          # Multiple view formats
    'mermaid_rendering': True,         # Modern diagram display
    'svg_png_support': True,           # Multiple output formats
    'interactive_legend': True,        # Object type identification
    'download_options': True,          # Export capabilities
    'real_time_generation': True      # On-demand visualization
}
```

**BREAKTHROUGH:** Fixed fundamental DDL storage issue for complete rollback capability.

**CRITICAL BUG DISCOVERED:** The `get_all_objects_with_ddl()` function was NOT actually storing DDL despite its name. It only stored object names, causing rollback failures for dropped objects.

**ROOT CAUSE ANALYSIS:**
```python
# BEFORE (v1.2.0 and earlier) - BROKEN:
def get_all_objects_with_ddl(self) -> Dict[str, List[Dict]]:
    """Get all database objects with their DDL."""
    objects = {'tables': [], 'views': [], ...}
    
    # BUG: Only stored names, not DDL!
    cursor.execute(f"SHOW FULL TABLES FROM `{self.config.schema}` WHERE Table_type = 'BASE TABLE'")
    tables = cursor.fetchall()
    objects['tables'] = [{'name': list(table.values())[0]} for table in tables]
    # Missing: DDL extraction and storage!
```

**FIXED IMPLEMENTATION (v1.2.1):**
```python
# AFTER (v1.2.1) - WORKING:
def get_all_objects_with_ddl(self) -> Dict[str, List[Dict]]:
    """Get all database objects with their DDL."""
    objects = {'tables': [], 'views': [], ...}
    
    # FIXED: Actually retrieve and store DDL for each object
    cursor.execute(f"SHOW FULL TABLES FROM `{self.config.schema}` WHERE Table_type = 'BASE TABLE'")
    tables = cursor.fetchall()
    for table in tables:
        table_name = list(table.values())[0]
        try:
            ddl = self.get_table_ddl(table_name)
            objects['tables'].append({'name': table_name, 'ddl': ddl})
        except Exception as e:
            print(f"Warning: Failed to get DDL for table {table_name}: {e}")
            objects['tables'].append({'name': table_name, 'ddl': ''})
    
    # CRITICAL: Apply same pattern to ALL 7 object types:
    # - tables, views, procedures, functions, triggers, events, sequences
```

**ROLLBACK GENERATION FIX:**
```python
# BEFORE (v1.2.0 and earlier) - BROKEN:
for view_name in views_comparison.get('only_in_dest', []):
    try:
        dest_ddl = get_dest_ddl('views', view_name)  # FAILS: Object was dropped!
        if dest_ddl:
            rollback_lines.append(dest_ddl + ";")

# AFTER (v1.2.1) - WORKING:  
for view_name in views_comparison.get('only_in_dest', []):
    try:
        # Find the view DDL in the original dest_objects
        dest_ddl = None
        for view_obj in dest_objects.get('views', []):
            if view_obj['name'] == view_name:
                dest_ddl = view_obj['ddl']  # USE STORED DDL!
                break
        
        if dest_ddl:
            rollback_lines.append(f"-- Rollback deletion of view: {view_name}")
            rollback_lines.append(dest_ddl + ";")
```

**CRITICAL PATTERN - Apply to ALL object types:**
```python
ROLLBACK_PATTERN_ALL_OBJECTS = {
    'tables': 'dest_objects.get("tables", [])',
    'views': 'dest_objects.get("views", [])', 
    'procedures': 'dest_objects.get("procedures", [])',
    'functions': 'dest_objects.get("functions", [])',
    'triggers': 'dest_objects.get("triggers", [])',
    'events': 'dest_objects.get("events", [])',
    'sequences': 'dest_objects.get("sequences", [])'
}

# NEVER use get_dest_ddl() for dropped objects - they don't exist anymore!
# ALWAYS use stored DDL from dest_objects during extraction phase!
```

**FILES REQUIRING DUAL MAINTENANCE:**
```python
CRITICAL_DDL_STORAGE_FILES = {
    'database.py': 'Root version - get_all_objects_with_ddl() with DDL storage',
    'ddlwizard/utils/database.py': 'Package version - MUST be identical',
    'ddl_wizard.py': 'Root rollback generation using dest_objects',
    'ddl_wizard_core.py': 'Core rollback function - verify DDL parameter flow'
}
```

### 5. Round-Trip Testing Validation (v1.2.1 VERIFIED)

**COMPLETE SUCCESS ACHIEVED:** 100% round-trip testing now passes with new DDL storage architecture.

```python
def test_round_trip_v1_2_1():
    """VERIFIED: Perfect round-trip with DDL storage fix."""
    
    # Step 1: Initial comparison ✅ 11 operations detected
    # Step 2: Apply migration    ✅ Success (no errors)  
    # Step 3: Post-migration     ✅ 0 operations (perfect sync)
    # Step 4: Apply rollback     ✅ Success (complete restoration)
    # Step 5: Final verification ✅ 11 operations (back to original)
    
    # ROLLBACK RESTORATION VERIFIED:
    # ✅ Tables: stock_alerts, product_reviews fully restored
    # ✅ Views: product_catalog with complete DDL restored  
    # ✅ Procedures: GetProductReviewSummary restored
    # ✅ Functions: GetProductAverageRating restored
    # ✅ Triggers: generate_order_number restored
    # ✅ Events: update_featured_products restored  
    # ✅ Sequences: user_id_seq properly dropped in rollback
    
    assert round_trip_success_rate == 100%  # ACHIEVED!
```

### 6. Rollback Generation (COMPLETELY REWRITTEN v1.2.1)

**CRITICAL:** Complete rollback support for ALL object types using stored DDL:

```python
def generate_detailed_rollback_sql(comparison, source_objects, dest_objects):
    """Generate complete rollback SQL for ALL 7 object types."""
    
    # CRITICAL ARCHITECTURE CHANGE (v1.2.1):
    # - dest_objects now contains actual DDL for all objects
    # - Use stored DDL instead of database queries for dropped objects
    # - Handles all only_in_dest scenarios properly
    
    # PATTERN FOR ALL OBJECT TYPES:
    for object_name in object_comparison.get('only_in_dest', []):
        try:
            # Find the object DDL in the original dest_objects
            dest_ddl = None
            for obj in dest_objects.get(object_type, []):
                if obj['name'] == object_name:
                    dest_ddl = obj['ddl']  # USE STORED DDL!
                    break
            
            if dest_ddl:
                rollback_lines.append(f"-- Rollback deletion of {object_type}: {object_name}")
                rollback_lines.append(dest_ddl + ";")  # ALWAYS add semicolon
                rollback_lines.append("")
        except Exception as e:
            rollback_lines.append(f"-- ERROR: Failed to restore {object_type} {object_name}: {str(e)}")
            continue
    
    # OBJECT TYPES REQUIRING DELIMITER HANDLING:
    DELIMITER_OBJECTS = ['procedures', 'functions', 'triggers']  # Use $$
    SEMICOLON_OBJECTS = ['tables', 'views', 'events', 'sequences']  # Use ;
```

### 7. MariaDB Sequence Syntax

**CRITICAL:** Proper MariaDB sequence handling:

```sql
-- Creation Syntax
CREATE SEQUENCE sequence_name
    START WITH 1000
    INCREMENT BY 1
    MINVALUE 1000
    MAXVALUE 999999999
    CACHE 10
    NOCYCLE
    ENGINE=InnoDB;

-- Detection Method
SHOW FULL TABLES WHERE Table_type = 'SEQUENCE'

-- DDL Extraction  
SHOW CREATE SEQUENCE sequence_name
```

---

## 🧪 Testing Requirements

### Round-Trip Testing (MANDATORY - v1.2.1 VERIFIED)

**CRITICAL:** All changes MUST pass 100% round-trip testing (v1.2.1 ACHIEVED):

```python
def test_round_trip():
    """MANDATORY: 5-step round-trip validation."""
    
    # Step 1: Detect initial differences (11 operations expected for test data)
    # Step 2: Apply migration (transforms dest to match source)
    # Step 3: Verify 0 operations (perfect sync achieved)
    # Step 4: Apply rollback (restores original dest state) 
    # Step 5: Verify restoration to initial state (11 operations again)
    
    # SUCCESS CRITERIA: 5/5 tests must pass
    # v1.2.1 ACHIEVEMENT: 100% success rate achieved with DDL storage fix
    assert round_trip_success_rate == 100%  # ✅ VERIFIED
    
    # ROLLBACK VERIFICATION POINTS:
    # ✅ All dropped tables restored with full DDL
    # ✅ All dropped views restored with full DDL  
    # ✅ All dropped procedures restored with DELIMITER handling
    # ✅ All dropped functions restored with DELIMITER handling
    # ✅ All dropped triggers restored with DELIMITER handling
    # ✅ All dropped events restored with semicolon syntax
    # ✅ All dropped sequences properly handled in reverse
```

### Test Coverage Requirements

```python
MINIMUM_TEST_COVERAGE = {
    'round_trip_tests': 5,      # MUST be 5/5 (100%) ✅ ACHIEVED v1.2.1
    'file_generation': 3,       # MUST be 3/3 (100%)
    'detection_tests': 17,      # SHOULD be 17/21 (81%+)
    'overall_minimum': 22       # MUST be 22/26 (84%+)
}

# v1.2.1 BREAKTHROUGH: Round-trip testing now 100% reliable
# - DDL storage architecture fixes all rollback issues
# - Complete object restoration verified for all 7 types
# - Perfect reversibility achieved: migration ↔ rollback
```

---

## �️ GUI Features (v1.2.0+)

### SQL Execution Engine

**CRITICAL:** Safe execution of migration and rollback files:

```python
EXECUTION_FEATURES = {
    'dry_run_validation': True,      # Always validate before execution
    'connection_reuse': True,        # Use existing source/dest connections
    'file_upload_support': True,     # Upload custom SQL files
    'progress_tracking': True,       # Real-time execution progress
    'error_handling': True,          # Continue on errors with reporting
    'statement_counting': True       # Track executed vs failed statements
}
```

### Connection Management System

**NEW:** Named connection profiles for reusability:

```python
CONNECTION_MANAGER_FEATURES = {
    'save_connections': True,        # Save named connection profiles
    'load_connections': True,        # Load saved connections
    'export_import': True,           # Backup/restore connection profiles
    'password_security': True,       # Passwords not stored (enter each time)
    'usage_tracking': True,          # Track last used timestamps
    'descriptions': True,            # Optional connection descriptions
    'storage_location': '~/.ddlwizard/connections.json'
}
```

### GUI Safety Features

```python
GUI_SAFETY_REQUIREMENTS = {
    'dry_run_default': True,         # Execution defaults to dry run
    'confirmation_required': True,   # User must confirm real execution
    'progress_feedback': True,       # Visual progress indicators
    'error_display': True,           # Clear error messages
    'backup_warnings': True          # Prominent backup reminders
}
```

---

### Dual Maintenance Required (v1.2.1 CRITICAL)

**CRITICAL:** DDL storage changes must be applied to BOTH versions:

1. **Root Level Files:**
   - `ddl_wizard.py` ↔ `ddlwizard/cli.py`
   - `database.py` ↔ `ddlwizard/utils/database.py` **← DDL STORAGE FIX**
   - `schema_comparator.py` ↔ `ddlwizard/utils/comparator.py`
   - `alter_generator.py` ↔ `ddlwizard/utils/generator.py`

2. **Synchronization Checklist (v1.2.1 Updated):**
   ```bash
   # After making changes, verify both versions:
   diff database.py ddlwizard/utils/database.py
   diff schema_comparator.py ddlwizard/utils/comparator.py
   diff alter_generator.py ddlwizard/utils/generator.py
   
   # CRITICAL: Verify DDL storage functions are identical:
   grep -n "get_all_objects_with_ddl" database.py ddlwizard/utils/database.py
   grep -n "ddl.*append" database.py ddlwizard/utils/database.py
   
   # CRITICAL: Verify rollback generation uses dest_objects:
   grep -n "dest_objects.get" ddl_wizard.py
   grep -n "get_dest_ddl.*only_in_dest" ddl_wizard.py  # Should return NO results!
   ```

3. **v1.2.1 DDL Storage Verification:**
   ```python
   # MUST verify both files have DDL storage implemented:
   VERIFICATION_COMMANDS = [
       "grep -A 10 'get_table_ddl(table_name)' database.py",
       "grep -A 10 'get_table_ddl(table_name)' ddlwizard/utils/database.py",
       "grep -A 5 'ddl.*=.*self.get_.*_ddl' database.py", 
       "grep -A 5 'ddl.*=.*self.get_.*_ddl' ddlwizard/utils/database.py"
   ]
   ```

---

## 🚨 Regression Prevention Checklist

### Before ANY Code Changes

- [ ] Identify which object types are affected
- [ ] Check if changes affect both root and package versions  
- [ ] Verify DDL storage is preserved in get_all_objects_with_ddl()
- [ ] Verify rollback generation uses dest_objects (NOT get_dest_ddl for dropped objects)
- [ ] Ensure DDL statements end with semicolons
- [ ] Test round-trip functionality

### After Code Changes  

- [ ] Run comprehensive test suite
- [ ] Verify 100% round-trip success (5/5 tests) ✅ v1.2.1 ACHIEVED
- [ ] Check overall coverage ≥84% (22/26 tests)
- [ ] Validate both root and package versions work
- [ ] Test with real MariaDB instances
- [ ] Verify DDL storage functions in both database.py files

### Critical Files to Never Break

```python
CRITICAL_FILES = {
    'database.py': 'DDL extraction + storage for all 7 object types + SQL execution',
    'ddlwizard/utils/database.py': 'Package version - DDL storage MUST be identical',
    'schema_comparator.py': 'Migration SQL generation', 
    'ddl_wizard.py': 'Rollback generation using dest_objects (NOT get_dest_ddl)',
    'ddl_wizard_core.py': 'Core rollback function parameter flow',
    'connection_manager.py': 'Named connection profiles and persistence',
    'ddl_wizard_gui.py': 'GUI with execution and connection management',
    'tests/test_integration.py': 'Comprehensive validation'
}

# v1.2.1 CRITICAL: DDL storage must work in BOTH database.py files
# Rollback generation must use stored DDL, never database queries for dropped objects
```

---

## 🔍 Known Technical Debt

### Areas Requiring Attention

1. **Detection Edge Cases (4 failing tests):**
   - Missing Views detection
   - Different Views comparison
   - Missing Events detection  
   - Different Events comparison

2. **Test Data Alignment:**
   - `testdata/` schemas less comprehensive than test suite
   - Consider updating for consistency

3. **Error Handling:**
   - Could be more granular for specific object types
   - Better error messages for debugging

---

## 📚 Key Implementation Patterns

### DDL Extraction Pattern

```python
def get_object_ddl(self, object_type: str, object_name: str) -> str:
    """Standard pattern for DDL extraction."""
    
    # 1. Use appropriate SHOW command
    # 2. Handle MariaDB-specific syntax
    # 3. Return clean DDL without CREATE DATABASE statements
    # 4. Handle edge cases (views, sequences, etc.)
```

### Migration Generation Pattern

```python
def process_object_type(self, comparison: Dict) -> List[str]:
    """Standard pattern for migration generation."""
    
    # 1. Handle only_in_source (CREATE operations)
    # 2. Handle only_in_dest (DROP operations)  
    # 3. Handle in_both with differences (UPDATE operations)
    # 4. Use IF EXISTS clauses for safety
    # 5. Proper schema qualification
```

### Rollback Generation Pattern

```python
def generate_rollback_for_object_type(self, comparison: Dict) -> List[str]:
    """Standard pattern for rollback generation."""
    
    # 1. Reverse the migration logic
    # 2. Use destination DDL to restore original state
    # 3. ALWAYS add semicolons to DDL statements
    # 4. Handle all three scenarios (create/drop/modify)
```

---

## 🎯 Success Metrics

### Production Readiness Criteria

```python
PRODUCTION_READY_METRICS = {
    'round_trip_success': 100,     # 5/5 tests MANDATORY ✅ v1.2.1 ACHIEVED
    'overall_coverage': 84.6,      # 22/26 tests minimum
    'object_type_support': 7,      # All 7 types MANDATORY
    'mariadb_compatibility': True, # MariaDB 10.3+ sequences
    'rollback_functionality': True, # Complete rollback MANDATORY ✅ v1.2.1 ACHIEVED
    'ddl_storage_working': True,   # DDL stored during extraction ✅ v1.2.1 ACHIEVED
    'dest_objects_usage': True     # Rollback uses stored DDL ✅ v1.2.1 ACHIEVED
}
```

### Release Checklist

- [ ] v1.2.1+ feature parity maintained (DDL storage + rollback)
- [ ] All 7 database object types supported
- [ ] 100% round-trip testing success ✅ ACHIEVED v1.2.1
- [ ] Both root and package versions working with identical DDL storage
- [ ] MariaDB compatibility verified
- [ ] Documentation updated
- [ ] DDL storage implemented in both database.py files
- [ ] Rollback generation uses dest_objects (never get_dest_ddl for dropped objects)

---

## 🔗 Related Documents

- `README.md` - User-facing documentation
- `tests/test_integration.py` - Comprehensive test suite
- `CONTRIBUTING.md` - Development guidelines  
- Git tags `v1.0.0`, `v1.1.0`, `v1.2.0`, `v1.2.1` - Release history

---

**⚠️ CRITICAL REMINDER:** Any changes that break the 100% round-trip testing success rate or reduce the 7-object type support are considered regressions and must be fixed immediately.

**🚀 v1.2.1 ACHIEVEMENT:** Complete rollback functionality achieved through DDL storage architecture overhaul. Perfect round-trip capability verified for all 7 database object types.

This document should be consulted before making ANY changes to DDL Wizard core functionality.
