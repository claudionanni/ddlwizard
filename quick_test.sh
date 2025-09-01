#!/bin/bash

# DDL Wizard Quick Test Script
# A simple bash script to quickly test DDL Wizard functionality

set -e

echo "🧙‍♂️ DDL Wizard Quick Test Script"
echo "================================="

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-password}"
SOURCE_DB="ddl_test_source_quick"
DEST_DB="ddl_test_dest_quick"

# Check if mysql command is available
if ! command -v mysql &> /dev/null; then
    echo "❌ Error: mysql command not found. Please install MySQL client."
    exit 1
fi

# Function to execute SQL
execute_sql() {
    local database=$1
    local sql=$2
    echo "📝 Executing SQL in $database..."
    mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "$sql" "$database" 2>/dev/null || {
        # If database doesn't exist, create it first
        mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS \`$database\`" 2>/dev/null
        mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "$sql" "$database"
    }
}

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up test databases..."
    mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "DROP DATABASE IF EXISTS \`$SOURCE_DB\`" 2>/dev/null || true
    mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "DROP DATABASE IF EXISTS \`$DEST_DB\`" 2>/dev/null || true
}

# Set trap for cleanup on exit
trap cleanup EXIT

echo "🏗️  Setting up test databases..."

# Create databases
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS \`$SOURCE_DB\`" 2>/dev/null
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS \`$DEST_DB\`" 2>/dev/null

# Create source schema (complete)
echo "📋 Creating source schema..."
execute_sql "$SOURCE_DB" "
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_name (last_name, first_name),
    INDEX idx_users_active (is_active)
) ENGINE=InnoDB;

CREATE TABLE posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    status ENUM('draft', 'published', 'archived') DEFAULT 'draft',
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,
    FOREIGN KEY fk_posts_user (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_posts_user (user_id),
    INDEX idx_posts_status (status),
    INDEX idx_posts_published (published_at)
) ENGINE=InnoDB;

CREATE TABLE comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY fk_comments_post (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY fk_comments_user (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_comments_post (post_id),
    INDEX idx_comments_user (user_id),
    INDEX idx_comments_approved (is_approved)
) ENGINE=InnoDB;
"

# Create destination schema (with differences)
echo "📋 Creating destination schema with differences..."
execute_sql "$DEST_DB" "
-- Users table - missing phone column and index
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    old_field VARCHAR(100),  -- Extra column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_old (old_field)  -- Extra index
) ENGINE=InnoDB;

-- Posts table - missing foreign key constraint
CREATE TABLE posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    status ENUM('draft', 'published', 'archived') DEFAULT 'draft',
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,
    INDEX idx_posts_user (user_id),
    INDEX idx_posts_status (status)
) ENGINE=InnoDB;

-- Comments table - complete but missing one FK
CREATE TABLE comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY fk_comments_post (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    INDEX idx_comments_post (post_id),
    INDEX idx_comments_user (user_id),
    INDEX idx_comments_approved (is_approved)
) ENGINE=InnoDB;

-- Extra table that doesn't exist in source
CREATE TABLE temp_data (
    id INT PRIMARY KEY AUTO_INCREMENT,
    data VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
"

echo "✅ Test databases created successfully!"

# Run DDL Wizard
echo "🧙‍♂️ Running DDL Wizard..."
python main.py \
    --mode compare \
    --source-host "$DB_HOST" \
    --source-port "$DB_PORT" \
    --source-user "$DB_USER" \
    --source-password "$DB_PASSWORD" \
    --source-schema "$SOURCE_DB" \
    --dest-host "$DB_HOST" \
    --dest-port "$DB_PORT" \
    --dest-user "$DB_USER" \
    --dest-password "$DB_PASSWORD" \
    --dest-schema "$DEST_DB" \
    --output-dir ./quick_test_output \
    --auto-approve \
    --verbose

echo ""
echo "🔍 Test Results:"
echo "================"

# Check if files were generated
if [ -f "./quick_test_output/migration.sql" ]; then
    echo "✅ Migration file generated"
    echo "📄 Migration preview:"
    head -20 "./quick_test_output/migration.sql"
    echo ""
else
    echo "❌ Migration file not generated"
fi

if [ -f "./quick_test_output/comparison_report.txt" ]; then
    echo "✅ Comparison report generated"
    echo "📄 Report preview:"
    head -30 "./quick_test_output/comparison_report.txt"
else
    echo "❌ Comparison report not generated"
fi

echo ""
echo "📂 Full output available in: ./quick_test_output/"
echo "🎉 Quick test completed!"
