# DDL Wizard Test Data

This directory contains sample SQL scripts to help you test DDL Wizard out of the box. The scripts create two different database schemas with intentional differences to demonstrate the tool's migration capabilities.

## 📋 What's Included

### 🗃️ Source Schema (`source_schema.sql`)
A basic e-commerce database schema including:
- **Tables**: users, products, categories, orders, order_items
- **Stored Procedures**: GetUserOrderHistory
- **Functions**: GetUserTotalSpent
- **Triggers**: update_stock_after_order
- **Events**: cleanup_cancelled_orders
- **Views**: order_summary
- **Sample data** for all tables

### 🗃️ Destination Schema (`destination_schema.sql`)
An enhanced version of the e-commerce schema with:
- **Modified Tables**: Additional columns, changed constraints, new indexes
- **New Tables**: product_reviews, stock_alerts
- **Enhanced Procedures**: Modified signatures and additional procedures
- **New Functions**: GetProductAverageRating
- **Updated Triggers**: Enhanced logic and new triggers
- **Modified Events**: Different schedules and new events
- **Enhanced Views**: Additional columns and new views
- **Extended sample data**

## 🚀 Quick Start

### 1. Set Up Test Databases

**For MariaDB/MySQL:**

```bash
# Create source database
mysql -u root -p < testdata/source_schema.sql

# Create destination database  
mysql -u root -p < testdata/destination_schema.sql
```

**For Docker:**

```bash
# Run MariaDB containers for testing
docker run -d --name ddlwizard-source -e MYSQL_ROOT_PASSWORD=testpass -p 3306:3306 mariadb:latest
docker run -d --name ddlwizard-dest -e MYSQL_ROOT_PASSWORD=testpass -p 3307:3306 mariadb:latest

# Wait for containers to start, then create schemas
sleep 30
docker exec -i ddlwizard-source mysql -u root -ptestpass < testdata/source_schema.sql
docker exec -i ddlwizard-dest mysql -u root -ptestpass < testdata/destination_schema.sql
```

### 2. Test DDL Wizard CLI

```bash
# Compare the two schemas
python main.py compare \
  --source-host localhost --source-port 3306 --source-user root --source-password testpass --source-schema ddlwizard_source_test \
  --dest-host localhost --dest-port 3307 --dest-user root --dest-password testpass --dest-schema ddlwizard_dest_test \
  --output-dir ./test_migration

# Or using single database with different schema names
python main.py compare \
  --source-host localhost --source-user root --source-password yourpass --source-schema ddlwizard_source_test \
  --dest-host localhost --dest-user root --dest-password yourpass --dest-schema ddlwizard_dest_test \
  --output-dir ./test_migration
```

### 3. Test DDL Wizard GUI

```bash
# Start the web interface
streamlit run ddlwizard/gui.py --server.port 8501
```

Then configure the databases in the web interface:

**Source Database:**
- Host: localhost
- Port: 3306 (or 3306 for single DB)
- Username: root  
- Password: testpass (or your password)
- Schema: ddlwizard_source_test

**Destination Database:**
- Host: localhost
- Port: 3307 (or 3306 for single DB)
- Username: root
- Password: testpass (or your password)  
- Schema: ddlwizard_dest_test

## 📊 Expected Results

When you run DDL Wizard on these test schemas, you should see migrations for:

### 🔄 Table Modifications
- **users**: Added columns (full_name, phone), new indexes, constraint changes
- **products**: Added columns (sale_price, min_stock_level, weight, dimensions, is_featured), modified column lengths
- **categories**: Added columns (sort_order, is_active)
- **orders**: Added columns (order_number, tax_amount, shipping_cost, discount_amount, tracking_number), enum changes
- **order_items**: Added discount_amount column, modified computed column

### ➕ New Objects
- **Tables**: product_reviews, stock_alerts
- **Procedures**: GetProductReviewSummary
- **Functions**: GetProductAverageRating  
- **Triggers**: generate_order_number
- **Events**: update_featured_products
- **Views**: product_catalog
- **Data**: Additional sample records

### 🔧 Modified Objects
- **Procedures**: GetUserOrderHistory (signature change)
- **Functions**: GetUserTotalSpent (logic change)
- **Triggers**: update_stock_after_order (enhanced logic)
- **Events**: cleanup_cancelled_orders (schedule change)
- **Views**: order_summary (additional columns)

## 🧹 Cleanup

To remove the test databases:

```sql
DROP DATABASE IF EXISTS ddlwizard_source_test;
DROP DATABASE IF EXISTS ddlwizard_dest_test;
```

Or stop and remove Docker containers:

```bash
docker stop ddlwizard-source ddlwizard-dest
docker rm ddlwizard-source ddlwizard-dest
```

## 💡 Tips

1. **Start Simple**: First try comparing just the table structures by running with `--dry-run`
2. **Check Safety**: Review the generated safety warnings - they're designed to catch potentially dangerous operations
3. **Examine Output**: Look at the generated migration.sql and rollback.sql files to understand what changes would be applied
4. **Use Visualization**: Enable `--enable-visualization` to generate schema diagrams
5. **Test Thoroughly**: Always test migrations on non-production data first

## 🎯 Learning Objectives

These test schemas help demonstrate:
- ✅ Table structure differences detection
- ✅ New table creation
- ✅ Column additions and modifications  
- ✅ Index changes
- ✅ Constraint modifications
- ✅ Stored procedure signature changes
- ✅ Function logic differences
- ✅ Trigger enhancements
- ✅ Event scheduling changes
- ✅ View modifications
- ✅ Safety analysis and warnings
- ✅ Rollback script generation

Happy testing with DDL Wizard! 🧙‍♂️
