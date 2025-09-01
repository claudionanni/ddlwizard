# DDL Wizard Test Suite

This directory contains comprehensive testing tools for validating DDL Wizard functionality across different types of schema differences.

## 🧪 Test Scripts Overview

### 1. **Comprehensive Python Test Suite** (`test_ddl_wizard.py`)
The most complete test that creates complex schemas with every type of difference DDL Wizard should detect.

**Features:**
- Creates two complete test databases with realistic schemas
- Tests all difference types: columns, indexes, foreign keys, triggers, functions, procedures
- Validates DDL Wizard's detection capabilities
- Generates detailed test reports
- Includes cleanup functionality

**Usage:**
```bash
# Run with default MySQL settings
python test_ddl_wizard.py

# Run with custom database settings
python test_ddl_wizard.py --host localhost --port 3306 --user root --password mypassword

# Run without cleanup (keep test databases for inspection)
python test_ddl_wizard.py --no-cleanup
```

### 2. **Quick Bash Test** (`quick_test.sh`)
A lightweight bash script for rapid testing with simpler schemas.

**Features:**
- Fast setup and execution
- Simple but effective schema differences
- Good for quick validation during development
- Minimal dependencies (just mysql client)

**Usage:**
```bash
# Run with default settings
./quick_test.sh

# Run with custom database credentials
DB_USER=myuser DB_PASSWORD=mypass ./quick_test.sh
```

### 3. **Docker Compose Test Environment** (`docker-compose.test.yml`)
Complete containerized test environment with MariaDB and MySQL.

**Features:**
- Isolated test environment
- Both MariaDB (source) and MySQL (destination) databases
- Pre-configured with test data
- No local database setup required

**Usage:**
```bash
# Start test environment
docker-compose -f docker-compose.test.yml up --build

# Run tests in containers
docker-compose -f docker-compose.test.yml run ddl-wizard-test

# Clean up
docker-compose -f docker-compose.test.yml down -v
```

## 📋 Test Scenarios Covered

### Table Structure Differences
- ✅ **Missing Columns**: Source has columns that destination lacks
- ✅ **Extra Columns**: Destination has columns that source lacks  
- ✅ **Modified Columns**: Same column with different data types or constraints
- ✅ **Column Order**: Different column positioning

### Index Differences  
- ✅ **Missing Indexes**: Source has indexes that destination lacks
- ✅ **Extra Indexes**: Destination has indexes that source lacks
- ✅ **Modified Indexes**: Same index with different columns or properties
- ✅ **Primary Key Differences**: Different primary key definitions
- ✅ **Unique Key Differences**: Different unique constraint definitions

### Foreign Key Constraints
- ✅ **Missing Foreign Keys**: Source has FK constraints that destination lacks
- ✅ **Extra Foreign Keys**: Destination has FK constraints that source lacks
- ✅ **Modified Foreign Keys**: Same FK with different references or actions
- ✅ **Cascade Rules**: Different ON DELETE/UPDATE behaviors

### Database Objects
- ✅ **Missing Tables**: Tables that exist only in source
- ✅ **Extra Tables**: Tables that exist only in destination
- ✅ **Missing Functions**: User-defined functions only in source
- ✅ **Extra Functions**: User-defined functions only in destination
- ✅ **Modified Functions**: Same function with different implementation
- ✅ **Missing Procedures**: Stored procedures only in source
- ✅ **Extra Procedures**: Stored procedures only in destination
- ✅ **Modified Procedures**: Same procedure with different implementation
- ✅ **Missing Triggers**: Triggers only in source
- ✅ **Extra Triggers**: Triggers only in destination
- ✅ **Modified Triggers**: Same trigger with different logic

### Table Properties
- ✅ **Engine Differences**: Different storage engines (InnoDB vs MyISAM)
- ✅ **Charset Differences**: Different character sets
- ✅ **Collation Differences**: Different collations
- ✅ **Table Comments**: Different or missing table comments

## 🔍 Expected Test Results

When running the tests, DDL Wizard should detect and report:

### Schema Comparison Report
```
TABLES:
  Only in source: 1 (product_reviews)
  Only in destination: 1 (temp_analytics) 
  In both schemas: 5
  With differences: 4
    Table `categories` differences:
      + ADD COLUMN `description` TEXT
      + ADD COLUMN `slug` VARCHAR(100) UNIQUE
      + ADD INDEX `idx_categories_slug` (slug)
    Table `products` differences:
      + ADD COLUMN `short_description` VARCHAR(500)
      + ADD FOREIGN KEY `fk_products_category` (category_id) -> categories(id)
      - DROP COLUMN `legacy_field`
    [... more differences ...]

FUNCTIONS:
  Only in source: 1 (GetUserTotalSpent)
  With differences: 1 (CalculateOrderTotal)

PROCEDURES:
  Only in source: 1 (GetProductsByCategory)
  With differences: 1 (GetUserOrderHistory)

TRIGGERS:
  Only in source: 2 (tr_products_update_timestamp, tr_orders_calculate_total)
  Only in destination: 1 (tr_temp_analytics_validation)
```

### Generated Migration SQL
The migration script should include:
```sql
-- Add missing columns
ALTER TABLE `categories` ADD COLUMN `description` TEXT;
ALTER TABLE `categories` ADD COLUMN `slug` VARCHAR(100) UNIQUE;

-- Add missing foreign keys  
ALTER TABLE `products` ADD CONSTRAINT `fk_products_category` 
  FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE CASCADE;

-- Drop extra columns
ALTER TABLE `products` DROP COLUMN `legacy_field`;

-- Create missing functions
CREATE FUNCTION GetUserTotalSpent(p_user_id INT) RETURNS DECIMAL(12,2) ...

-- Drop and recreate modified procedures
DROP PROCEDURE IF EXISTS GetUserOrderHistory;
CREATE PROCEDURE GetUserOrderHistory(IN p_user_id INT) ...
```

## 🛠️ Customizing Tests

### Adding New Test Cases

1. **Modify Schema Files**: Edit `test_data/source_init.sql` and `test_data/dest_init.sql`
2. **Update Test Logic**: Modify the validation logic in `test_ddl_wizard.py`
3. **Add Assertions**: Include new checks in the `analyze_results()` method

### Testing with Different Database Versions

The test suite supports various database configurations:

```bash
# Test with different MySQL/MariaDB versions
DB_HOST=mysql-8.0.server DB_PORT=3306 python test_ddl_wizard.py
DB_HOST=mariadb-10.11.server DB_PORT=3306 python test_ddl_wizard.py
```

### Custom Test Databases

You can point the tests to existing databases:

```bash
python test_ddl_wizard.py \
  --host your-db-server.com \
  --port 3306 \
  --user your_user \
  --password your_password \
  --no-cleanup
```

## 📊 Test Output Files

After running tests, you'll find:

```
test_output/                 # Main test output directory
├── migration.sql           # Generated migration script
├── rollback.sql            # Generated rollback script  
├── comparison_report.txt   # Detailed comparison report
├── migration_report.md     # Markdown migration report
└── [tables|functions|procedures|triggers|events]/
    └── *.sql              # Individual object DDL files

ddl_wizard_test.log         # Detailed test execution log
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check if database is running
   mysql -h localhost -u root -p -e "SELECT VERSION();"
   
   # Verify credentials
   mysql -h localhost -u root -p
   ```

2. **Permission Denied**
   ```bash
   # Grant necessary privileges
   GRANT ALL PRIVILEGES ON *.* TO 'test_user'@'%';
   FLUSH PRIVILEGES;
   ```

3. **Module Import Errors**
   ```bash
   # Install requirements
   pip install -r requirements.txt
   
   # Check Python path
   export PYTHONPATH=/path/to/ddlwizard:$PYTHONPATH
   ```

4. **Docker Issues**
   ```bash
   # Reset Docker environment
   docker-compose -f docker-compose.test.yml down -v
   docker-compose -f docker-compose.test.yml up --build --force-recreate
   ```

### Debug Mode

Run tests with verbose logging:
```bash
python test_ddl_wizard.py --verbose
tail -f ddl_wizard_test.log
```

## 🎯 Success Criteria

A successful test run should show:
- ✅ All expected files generated
- ✅ All schema differences detected correctly
- ✅ Migration SQL syntactically correct
- ✅ No false positives or missed differences
- ✅ Proper handling of foreign key dependencies
- ✅ Correct rollback script generation

## 🚀 Continuous Integration

For CI/CD integration, use the Docker setup:

```yaml
# .github/workflows/test.yml
name: DDL Wizard Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run DDL Wizard Tests
        run: |
          docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
          docker-compose -f docker-compose.test.yml down -v
```

This comprehensive test suite ensures DDL Wizard works correctly across all supported schema difference types and database configurations.
