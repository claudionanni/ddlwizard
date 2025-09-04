# DDL Wizard Technical Reference Document

**Version:** 1.2.0  
**Last Updated:** September 4, 2025  
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

### 4. Rollback Generation

**CRITICAL:** Complete rollback support for ALL object types:

```python
def generate_detailed_rollback_sql(comparison, source_objects, dest_objects):
    """Generate complete rollback SQL for ALL 7 object types."""
    
    # MUST include rollback for:
    # 1. Tables (column/index changes)
    # 2. Procedures (drop/recreate with original)
    # 3. Functions (drop/recreate with original)
    # 4. Triggers (drop/recreate with original) 
    # 5. Events (drop/recreate with original) + SEMICOLONS
    # 6. Views (drop/recreate with original) + SEMICOLONS
    # 7. Sequences (drop/recreate with original) + SEMICOLONS
    
    # CRITICAL: Add semicolons to DDL statements
    rollback_lines.append(dest_ddl + ";")  # NOT dest_ddl alone
```

### 5. MariaDB Sequence Syntax

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

### Round-Trip Testing (MANDATORY)

**CRITICAL:** All changes MUST pass 100% round-trip testing:

```python
def test_round_trip():
    """MANDATORY: 5-step round-trip validation."""
    
    # Step 1: Detect initial differences (7 operations expected)
    # Step 2: Apply migration (42 statements expected)
    # Step 3: Verify 0 operations (perfect sync)
    # Step 4: Apply rollback (37+ statements expected)  
    # Step 5: Verify restoration to initial state
    
    # SUCCESS CRITERIA: 5/5 tests must pass
    assert round_trip_success_rate == 100%
```

### Test Coverage Requirements

```python
MINIMUM_TEST_COVERAGE = {
    'round_trip_tests': 5,      # MUST be 5/5 (100%)
    'file_generation': 3,       # MUST be 3/3 (100%)
    'detection_tests': 17,      # SHOULD be 17/21 (81%+)
    'overall_minimum': 22       # MUST be 22/26 (84%+)
}
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

### Dual Maintenance Required

**CRITICAL:** Changes must be applied to BOTH versions:

1. **Root Level Files:**
   - `ddl_wizard.py` ↔ `ddlwizard/cli.py`
   - `database.py` ↔ `ddlwizard/utils/database.py`
   - `schema_comparator.py` ↔ `ddlwizard/utils/comparator.py`
   - `alter_generator.py` ↔ `ddlwizard/utils/generator.py`

2. **Synchronization Checklist:**
   ```bash
   # After making changes, verify both versions:
   diff database.py ddlwizard/utils/database.py
   diff schema_comparator.py ddlwizard/utils/comparator.py
   diff alter_generator.py ddlwizard/utils/generator.py
   ```

---

## 🚨 Regression Prevention Checklist

### Before ANY Code Changes

- [ ] Identify which object types are affected
- [ ] Check if changes affect both root and package versions
- [ ] Verify rollback generation includes ALL object types
- [ ] Ensure DDL statements end with semicolons
- [ ] Test round-trip functionality

### After Code Changes

- [ ] Run comprehensive test suite
- [ ] Verify 100% round-trip success (5/5 tests)
- [ ] Check overall coverage ≥84% (22/26 tests)
- [ ] Validate both root and package versions work
- [ ] Test with real MariaDB instances

### Critical Files to Never Break

```python
CRITICAL_FILES = {
    'database.py': 'DDL extraction for all 7 object types + SQL execution',
    'schema_comparator.py': 'Migration SQL generation', 
    'ddl_wizard.py': 'Rollback generation with Views/Events/Sequences',
    'connection_manager.py': 'Named connection profiles and persistence',
    'ddl_wizard_gui.py': 'GUI with execution and connection management',
    'tests/test_integration.py': 'Comprehensive validation'
}
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
    'round_trip_success': 100,     # 5/5 tests MANDATORY
    'overall_coverage': 84.6,      # 22/26 tests minimum
    'object_type_support': 7,      # All 7 types MANDATORY
    'mariadb_compatibility': True, # MariaDB 10.3+ sequences
    'rollback_functionality': True # Complete rollback MANDATORY
}
```

### Release Checklist

- [ ] v1.2.0+ feature parity maintained
- [ ] All 7 database object types supported
- [ ] 100% round-trip testing success
- [ ] Both root and package versions working
- [ ] MariaDB compatibility verified
- [ ] Documentation updated

---

## 🔗 Related Documents

- `README.md` - User-facing documentation
- `tests/test_integration.py` - Comprehensive test suite
- `CONTRIBUTING.md` - Development guidelines  
- Git tags `v1.0.0`, `v1.1.0`, `v1.2.0` - Release history

---

**⚠️ CRITICAL REMINDER:** Any changes that break the 100% round-trip testing success rate or reduce the 7-object type support are considered regressions and must be fixed immediately.

This document should be consulted before making ANY changes to DDL Wizard core functionality.
