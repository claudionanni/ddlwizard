# DDL Wizard Complex Test Data

This directory contains advanced test schemas designed to thoroughly test DDL Wizard's capabilities with enterprise-level database structures and complex differences.

## Overview

The complex test data consists of two elaborate MariaDB schemas with **35+ differences** covering all major database object types and modification scenarios.

## Test Schemas

### Source Schema (`source_schema.sql`)
**Complete e-commerce database with:**
- **12 tables**: Comprehensive business logic with users, products, orders, reviews, etc.
- **2 sequences**: Order and invoice numbering systems
- **4 views**: Customer analytics, product analytics, order statistics, revenue reports
- **4 procedures**: Order processing, inventory management, shipping calculation, reporting
- **4 functions**: Discount calculation, currency formatting, email validation, tax rates
- **3 triggers**: User auditing, inventory tracking, order status automation
- **2 events**: Log cleanup and statistics updates
- **Sample data**: Realistic test data in all major tables

**Total: 31 major database objects**

### Destination Schema (`destination_schema.sql`)
**Modified e-commerce database with significant differences:**
- **13 tables**: Mix of modified existing tables + 3 new tables + 2 missing tables
- **2 sequences**: Different configurations + 1 missing + 1 new sequence
- **2 views**: Completely different views (4 missing, 2 new)
- **2 procedures**: Different procedures (4 missing, 2 new)
- **2 functions**: Different functions (4 missing, 2 new)
- **2 triggers**: Different triggers (3 missing, 2 new)
- **1 event**: Different event (2 missing, 1 new)
- **Sample data**: Different data reflecting structural changes

**Total: 24 major database objects with significant structural differences**

## Expected Differences (35+ Operations)

### Table Modifications
1. **categories**: Column renames, new columns, constraint changes, different collation
2. **users**: Enum modifications, new columns, different constraints
3. **user_profiles**: Column renames, enum changes, new indexes
4. **products**: Column renames, new columns, index modifications
5. **product_reviews**: Enhanced rating system, new columns
6. **orders**: Status changes, new tracking columns
7. **order_items**: Commission tracking additions
8. **system_config**: Configuration categorization
9. **audit_log**: Enhanced logging capabilities

### Missing Tables (to be created)
10. **payment_methods**: User payment information
11. **shipping_addresses**: User address management
12. **inventory_tracking**: Inventory movement tracking

### New Tables (to be dropped)
13. **customer_analytics**: Customer segmentation
14. **promotional_campaigns**: Marketing campaigns
15. **order_tracking**: Detailed order tracking

### Sequence Changes
16. **order_number_seq**: Different start value and cache size
17. **invoice_number_seq**: Missing (to be created)
18. **customer_id_seq**: New (to be dropped)

### View Changes
19. **customer_summary**: Missing (to be created)
20. **product_analytics**: Missing (to be created)
21. **order_statistics**: Missing (to be created)
22. **revenue_report**: Missing (to be created)
23. **sales_dashboard**: New (to be dropped)
24. **inventory_report**: New (to be dropped)

### Procedure Changes
25. **process_order**: Missing (to be created)
26. **update_inventory**: Missing (to be created)
27. **calculate_shipping**: Missing (to be created)
28. **generate_report**: Missing (to be created)
29. **send_notification**: New (to be dropped)
30. **backup_data**: New (to be dropped)

### Function Changes
31. **calculate_discount**: Missing (to be created)
32. **format_currency**: Missing (to be created)
33. **validate_email**: Missing (to be created)
34. **get_tax_rate**: Missing (to be created)
35. **generate_slug**: New (to be dropped)
36. **calculate_commission**: New (to be dropped)

### Trigger Changes
37. **users_audit_trigger**: Missing (to be created)
38. **inventory_update_trigger**: Missing (to be created)
39. **order_status_trigger**: Missing (to be created)
40. **product_price_trigger**: New (to be dropped)
41. **order_notification_trigger**: New (to be dropped)

### Event Changes
42. **cleanup_old_logs**: Missing (to be created)
43. **update_statistics**: Missing (to be created)
44. **generate_reports**: New (to be dropped)

## Usage Instructions

### 1. Load Test Schemas

```bash
# Load source schema
mysql -h source_host -P source_port -u username -p ddlwizard_source_test < source_schema.sql

# Load destination schema  
mysql -h dest_host -P dest_port -u username -p ddlwizard_dest_test < destination_schema.sql
```

### 2. Run DDL Wizard Comparison

```bash
python ddl_wizard.py --mode compare \
  --source-host source_host --source-port source_port \
  --source-user username --source-password password \
  --source-schema ddlwizard_source_test \
  --dest-host dest_host --dest-port dest_port \
  --dest-user username --dest-password password \
  --dest-schema ddlwizard_dest_test \
  --output-dir /tmp/complex_test
```

### 3. Expected Results

The comparison should generate:
- **Migration SQL**: 35+ DDL operations to transform destination → source
- **Rollback SQL**: Complete reverse transformation with full object recreation
- **Analysis Report**: Detailed breakdown of all differences

### 4. Validation Tests

```bash
# Test deterministic generation
for i in {1..3}; do
  python ddl_wizard.py --mode compare [same params] --output-dir /tmp/test$i
done

# Verify identical output (excluding timestamps)
diff <(sed 's/-- Generated: .*//' /tmp/test1/migration.sql) \
     <(sed 's/-- Generated: .*//' /tmp/test2/migration.sql)
```

## Test Categories Covered

### ✅ Object Type Coverage
- **Tables**: Structure modifications, constraints, indexes
- **Views**: Complete replacement scenarios
- **Procedures**: Complex business logic changes
- **Functions**: Utility function variations
- **Triggers**: Event-driven automation changes
- **Events**: Scheduled task modifications
- **Sequences**: Numbering system changes

### ✅ Change Type Coverage
- **CREATE**: New objects in source not in destination
- **DROP**: Objects in destination not in source
- **ALTER**: Structural modifications to existing objects
- **REPLACE**: Complete object redefinition

### ✅ Complexity Scenarios
- **Foreign Key Dependencies**: Cross-table relationships
- **Index Modifications**: Performance optimization changes
- **Data Type Changes**: Column type and constraint modifications
- **Enum Modifications**: Value additions and changes
- **JSON Column Usage**: Modern data structure storage
- **Collation Differences**: Character set variations

## Performance Expectations

With this complex test data:
- **Analysis Time**: ~2-5 seconds for full comparison
- **Migration Size**: ~200-400 lines of DDL SQL
- **Rollback Size**: ~300-500 lines of DDL SQL
- **Memory Usage**: Moderate (handling 35+ object differences)

## Quality Assurance

This test data is designed to validate:
1. **Deterministic Output**: Identical results across multiple runs
2. **Round-Trip Consistency**: Perfect reversibility with rollback SQL
3. **Enterprise Scalability**: Handling complex real-world scenarios
4. **Error Handling**: Graceful handling of complex dependencies
5. **Performance**: Efficient processing of large object sets

## Troubleshooting

### Common Issues
- **Permission Errors**: Ensure database users have full DDL privileges
- **Character Set Issues**: Verify both databases use utf8mb4
- **Foreign Key Constraints**: Check that constraint validation is consistent
- **Sequence Support**: Ensure MariaDB 10.3+ for sequence support

### Debug Commands
```bash
# Check object counts
mysql -e "SELECT COUNT(*) as tables FROM information_schema.tables WHERE table_schema='ddlwizard_source_test'"
mysql -e "SELECT COUNT(*) as views FROM information_schema.views WHERE table_schema='ddlwizard_source_test'"
mysql -e "SELECT COUNT(*) as routines FROM information_schema.routines WHERE routine_schema='ddlwizard_source_test'"

# Verify schema loading
mysql -e "SHOW TABLES FROM ddlwizard_source_test"
mysql -e "SHOW PROCEDURE STATUS WHERE Db='ddlwizard_source_test'"
```

---

**This complex test data represents enterprise-level database schemas and provides comprehensive validation of DDL Wizard's advanced capabilities.**
