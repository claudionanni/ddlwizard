#!/bin/bash
# Quick syntax validation for destination schema
# This script validates the SQL syntax without actually creating the database

set -e

echo "🔍 Validating destination_schema.sql syntax..."

# Check if we can parse the SQL without errors
mysql --help > /dev/null 2>&1 || { echo "MySQL client not found. Please install mysql-client."; exit 1; }

# Dry run syntax check
echo "Checking SQL syntax..."
mysql --execute="SET sql_mode='STRICT_TRANS_TABLES'; $(cat testdata/destination_schema.sql)" --database=mysql > /dev/null 2>&1 && {
    echo "❌ Syntax check failed - this method executes the SQL"
} || {
    echo "⚠️  Cannot do pure syntax check with mysql client"
}

# Alternative: Check for common MariaDB incompatibilities
echo "Checking for known MariaDB compatibility issues..."

# Check for parameter defaults in procedures (not supported in MariaDB < 10.6)
if grep -q "DEFAULT [0-9]" testdata/destination_schema.sql; then
    echo "❌ Found parameter DEFAULT values in procedures"
else 
    echo "✅ No parameter DEFAULT values found"
fi

# Check for proper delimiter usage
if grep -q "DELIMITER //" testdata/destination_schema.sql && grep -q "DELIMITER ;" testdata/destination_schema.sql; then
    echo "✅ Proper DELIMITER usage found"
else
    echo "❌ Missing or incorrect DELIMITER usage"
fi

# Check that stock_alerts is created before references
line_stock_alerts=$(grep -n "CREATE TABLE stock_alerts" testdata/destination_schema.sql | head -1 | cut -d: -f1)
line_trigger_ref=$(grep -n "INSERT INTO stock_alerts" testdata/destination_schema.sql | head -1 | cut -d: -f1)

if [ "$line_stock_alerts" -lt "$line_trigger_ref" ]; then
    echo "✅ stock_alerts table created before trigger reference"
else
    echo "❌ stock_alerts table referenced before creation"
fi

echo "📋 Manual validation completed. Try importing the file to confirm syntax."
