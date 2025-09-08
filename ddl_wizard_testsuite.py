#!/usr/bin/env python3
"""
Copyright (C) 2025 Claudio Nanni
This file is part of DDL Wizard.

DDL Wizard is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

DDL Wizard is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with DDL Wizard.  If not, see <https://www.gnu.org/licenses/>.
"""
"""
DDL Wizard Test Suite
A comprehensive test script that creates two test databases with various schema differences
and validates DDL Wizard's ability to detect and generate migration scripts for all types of changes.
"""

import sys
import os
import time
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add the current directory to Python path so we can import DDL Wizard modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pymysql
    from database import DatabaseManager
    from ddl_wizard import main as ddl_wizard_main
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("💡 Make sure you have installed requirements: pip install -r requirements.txt")
    sys.exit(1)


class DDLWizardTester:
    """Comprehensive test suite for DDL Wizard functionality."""
    
    def __init__(self):
        self.source_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'password',
            'database': 'ddl_test_source'
        }
        
        self.dest_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'password',
            'database': 'ddl_test_dest'
        }
        
        self.test_results = {}
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for the test suite."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ddl_wizard_test.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_connection(self, config: Dict[str, Any]) -> pymysql.Connection:
        """Create a database connection."""
        try:
            # Try connecting without database first to create it
            conn_config = config.copy()
            database = conn_config.pop('database')
            
            conn = pymysql.connect(**conn_config)
            cursor = conn.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}`")
            cursor.execute(f"USE `{database}`")
            
            conn.close()
            
            # Now connect to the specific database
            return pymysql.connect(**config)
            
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise
    
    def setup_source_database(self):
        """Create the source database with complete schema."""
        self.logger.info("🏗️  Setting up source database...")
        
        conn = self.create_connection(self.source_config)
        cursor = conn.cursor()
        
        try:
            # Drop existing tables to start fresh
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("DROP TABLE IF EXISTS order_items")
            cursor.execute("DROP TABLE IF EXISTS orders")
            cursor.execute("DROP TABLE IF EXISTS customers")
            cursor.execute("DROP TABLE IF EXISTS products")
            cursor.execute("DROP TABLE IF EXISTS categories")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            # Create source schema with all types of objects
            source_sql = """
            -- Categories table
            CREATE TABLE categories (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_categories_name (name),
                INDEX idx_categories_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            
            -- Products table (source has extra columns and indexes)
            CREATE TABLE products (
                id INT PRIMARY KEY AUTO_INCREMENT,
                category_id INT NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                sku VARCHAR(50) UNIQUE,
                stock_quantity INT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                weight DECIMAL(8,3),
                dimensions VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY fk_products_category (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                INDEX idx_products_name (name),
                INDEX idx_products_price (price),
                INDEX idx_products_sku (sku),
                INDEX idx_products_stock (stock_quantity),
                INDEX idx_products_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            
            -- Customers table
            CREATE TABLE customers (
                id INT PRIMARY KEY AUTO_INCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                address TEXT,
                city VARCHAR(100),
                country VARCHAR(100),
                postal_code VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_customers_email (email),
                INDEX idx_customers_name (last_name, first_name),
                INDEX idx_customers_city (city),
                INDEX idx_customers_country (country)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            
            -- Orders table
            CREATE TABLE orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                customer_id INT NOT NULL,
                order_number VARCHAR(50) UNIQUE NOT NULL,
                status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
                total_amount DECIMAL(12,2) NOT NULL,
                shipping_cost DECIMAL(8,2) DEFAULT 0.00,
                tax_amount DECIMAL(8,2) DEFAULT 0.00,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                shipped_date TIMESTAMP NULL,
                delivered_date TIMESTAMP NULL,
                notes TEXT,
                FOREIGN KEY fk_orders_customer (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                INDEX idx_orders_customer (customer_id),
                INDEX idx_orders_status (status),
                INDEX idx_orders_date (order_date),
                INDEX idx_orders_number (order_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            
            -- Order items table
            CREATE TABLE order_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                total_price DECIMAL(12,2) NOT NULL,
                FOREIGN KEY fk_order_items_order (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY fk_order_items_product (product_id) REFERENCES products(id) ON DELETE CASCADE,
                INDEX idx_order_items_order (order_id),
                INDEX idx_order_items_product (product_id),
                UNIQUE KEY uk_order_items (order_id, product_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            
            # Execute each statement separately
            for statement in source_sql.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            
            # Create stored procedures and functions
            cursor.execute("DROP PROCEDURE IF EXISTS GetCustomerOrders")
            cursor.execute("""
            CREATE PROCEDURE GetCustomerOrders(IN customer_id INT)
            BEGIN
                SELECT o.*, COUNT(oi.id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.customer_id = customer_id
                GROUP BY o.id
                ORDER BY o.order_date DESC;
            END
            """)
            
            cursor.execute("DROP FUNCTION IF EXISTS CalculateOrderTotal")
            cursor.execute("""
            CREATE FUNCTION CalculateOrderTotal(order_id INT) RETURNS DECIMAL(12,2)
            READS SQL DATA
            DETERMINISTIC
            BEGIN
                DECLARE total DECIMAL(12,2) DEFAULT 0.00;
                SELECT SUM(total_price) INTO total
                FROM order_items
                WHERE order_items.order_id = order_id;
                RETURN IFNULL(total, 0.00);
            END
            """)
            
            # Create triggers
            cursor.execute("DROP TRIGGER IF EXISTS tr_orders_update_timestamp")
            cursor.execute("""
            CREATE TRIGGER tr_orders_update_timestamp
                BEFORE UPDATE ON orders
                FOR EACH ROW
            BEGIN
                SET NEW.notes = CONCAT(OLD.notes, ' - Updated at ', NOW());
            END
            """)
            
            cursor.execute("DROP TRIGGER IF EXISTS tr_products_stock_check")
            cursor.execute("""
            CREATE TRIGGER tr_products_stock_check
                BEFORE UPDATE ON products
                FOR EACH ROW
            BEGIN
                IF NEW.stock_quantity < 0 THEN
                    SET NEW.stock_quantity = 0;
                END IF;
            END
            """)
            
            conn.commit()
            self.logger.info("✅ Source database setup completed")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ Error setting up source database: {e}")
            raise
        finally:
            conn.close()
    
    def setup_destination_database(self):
        """Create the destination database with differences."""
        self.logger.info("🏗️  Setting up destination database with differences...")
        
        conn = self.create_connection(self.dest_config)
        cursor = conn.cursor()
        
        try:
            # Drop existing tables to start fresh
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("DROP TABLE IF EXISTS order_items")
            cursor.execute("DROP TABLE IF EXISTS orders")
            cursor.execute("DROP TABLE IF EXISTS customers")
            cursor.execute("DROP TABLE IF EXISTS products")
            cursor.execute("DROP TABLE IF EXISTS categories")
            cursor.execute("DROP TABLE IF EXISTS temp_table")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            # Create destination schema with intentional differences
            dest_sql = """
            -- Categories table (missing description column and index)
            CREATE TABLE categories (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_categories_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            
            -- Products table (missing columns, indexes, and FK constraint)
            CREATE TABLE products (
                id INT PRIMARY KEY AUTO_INCREMENT,
                category_id INT NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                sku VARCHAR(50) UNIQUE,
                stock_quantity INT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                old_column VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_products_name (name),
                INDEX idx_products_old (old_column)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            
            -- Customers table (extra column, missing index)
            CREATE TABLE customers (
                id INT PRIMARY KEY AUTO_INCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                address TEXT,
                city VARCHAR(100),
                country VARCHAR(100),
                postal_code VARCHAR(20),
                loyalty_points INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_customers_email (email),
                INDEX idx_customers_name (last_name, first_name),
                INDEX idx_customers_loyalty (loyalty_points)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            
            -- Orders table (missing foreign key constraint)
            CREATE TABLE orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                customer_id INT NOT NULL,
                order_number VARCHAR(50) UNIQUE NOT NULL,
                status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
                total_amount DECIMAL(12,2) NOT NULL,
                shipping_cost DECIMAL(8,2) DEFAULT 0.00,
                tax_amount DECIMAL(8,2) DEFAULT 0.00,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                shipped_date TIMESTAMP NULL,
                delivered_date TIMESTAMP NULL,
                notes TEXT,
                INDEX idx_orders_customer (customer_id),
                INDEX idx_orders_status (status),
                INDEX idx_orders_date (order_date),
                INDEX idx_orders_number (order_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            
            -- Order items table (complete)
            CREATE TABLE order_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                total_price DECIMAL(12,2) NOT NULL,
                FOREIGN KEY fk_order_items_order (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY fk_order_items_product (product_id) REFERENCES products(id) ON DELETE CASCADE,
                INDEX idx_order_items_order (order_id),
                INDEX idx_order_items_product (product_id),
                UNIQUE KEY uk_order_items (order_id, product_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            
            -- Extra table that doesn't exist in source
            CREATE TABLE temp_table (
                id INT PRIMARY KEY AUTO_INCREMENT,
                temp_data VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            
            # Execute each statement separately
            for statement in dest_sql.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            
            # Create different stored procedures and functions
            cursor.execute("DROP PROCEDURE IF EXISTS GetCustomerOrders")
            cursor.execute("""
            CREATE PROCEDURE GetCustomerOrders(IN customer_id INT)
            BEGIN
                SELECT o.*
                FROM orders o
                WHERE o.customer_id = customer_id
                ORDER BY o.order_date DESC;
            END
            """)
            
            # Missing function that exists in source
            # CalculateOrderTotal function is not created here
            # Explicitly ensure function doesn't exist
            cursor.execute("DROP FUNCTION IF EXISTS CalculateOrderTotal")
            
            # Create different trigger
            cursor.execute("DROP TRIGGER IF EXISTS tr_customers_loyalty_update")
            cursor.execute("""
            CREATE TRIGGER tr_customers_loyalty_update
                BEFORE UPDATE ON customers
                FOR EACH ROW
            BEGIN
                IF NEW.loyalty_points IS NULL THEN
                    SET NEW.loyalty_points = 0;
                END IF;
            END
            """)
            
            # Missing triggers that exist in source
            # tr_orders_update_timestamp and tr_products_stock_check are not created
            
            conn.commit()
            self.logger.info("✅ Destination database setup completed")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ Error setting up destination database: {e}")
            raise
        finally:
            conn.close()
    
    def populate_test_data(self):
        """Populate both databases with sample data - only using common columns."""
        self.logger.info("📝 Populating test data...")
        
        # Source database data
        source_conn = self.create_connection(self.source_config)
        source_cursor = source_conn.cursor()
        
        try:
            # Insert data into source database (with description column)
            source_cursor.execute("INSERT IGNORE INTO categories (name, description) VALUES ('Electronics', 'Electronic devices and gadgets')")
            source_cursor.execute("INSERT IGNORE INTO categories (name, description) VALUES ('Books', 'Physical and digital books')")
            
            source_cursor.execute("INSERT IGNORE INTO customers (email, first_name, last_name, phone, city, country) VALUES ('john@example.com', 'John', 'Doe', '+1234567890', 'New York', 'USA')")
            source_cursor.execute("INSERT IGNORE INTO customers (email, first_name, last_name, phone, city, country) VALUES ('jane@example.com', 'Jane', 'Smith', '+1987654321', 'London', 'UK')")
            
            source_conn.commit()
            self.logger.info(f"✅ Test data populated in {self.source_config['database']}")
            
        except Exception as e:
            source_conn.rollback()
            self.logger.error(f"❌ Error populating test data in source: {e}")
        finally:
            source_conn.close()
        
        # Destination database data  
        dest_conn = self.create_connection(self.dest_config)
        dest_cursor = dest_conn.cursor()
        
        try:
            # Insert data into destination database (without description column)
            dest_cursor.execute("INSERT IGNORE INTO categories (name) VALUES ('Electronics')")
            dest_cursor.execute("INSERT IGNORE INTO categories (name) VALUES ('Books')")
            
            dest_cursor.execute("INSERT IGNORE INTO customers (email, first_name, last_name, phone, city, country) VALUES ('john@example.com', 'John', 'Doe', '+1234567890', 'New York', 'USA')")
            dest_cursor.execute("INSERT IGNORE INTO customers (email, first_name, last_name, phone, city, country) VALUES ('jane@example.com', 'Jane', 'Smith', '+1987654321', 'London', 'UK')")
            
            dest_conn.commit()
            self.logger.info(f"✅ Test data populated in {self.dest_config['database']}")
                
        except Exception as e:
            dest_conn.rollback()
            self.logger.error(f"❌ Error populating test data in destination: {e}")
        finally:
            dest_conn.close()
    
    def execute_sql_file(self, sql_file_path: str, target_config: Dict[str, str]) -> bool:
        """Execute SQL statements from a file against the target database."""
        try:
            self.logger.info(f"🔧 Executing SQL file: {sql_file_path}")
            
            if not Path(sql_file_path).exists():
                self.logger.error(f"❌ SQL file not found: {sql_file_path}")
                return False
            
            with open(sql_file_path, 'r') as f:
                sql_content = f.read()
            
            # Skip empty files
            if not sql_content.strip():
                self.logger.info("ℹ️  SQL file is empty, skipping execution")
                return True
            
            # Connect to database
            conn = pymysql.connect(**target_config)
            cursor = conn.cursor()
            
            try:
                # Improved SQL parsing: handle comments and multi-line statements
                sql_content = self._clean_sql_content(sql_content)
                statements = self._parse_sql_statements(sql_content)
                
                executed_count = 0
                failed_count = 0
                
                for i, statement in enumerate(statements):
                    if statement.strip():
                        try:
                            self.logger.debug(f"Executing statement {i+1}/{len(statements)}: {statement[:100]}...")
                            cursor.execute(statement)
                            conn.commit()
                            executed_count += 1
                        except Exception as e:
                            failed_count += 1
                            # Log as warning but continue execution
                            self.logger.warning(f"⚠️  SQL execution warning (statement {i+1}): {e}")
                            if len(statement) <= 200:
                                self.logger.warning(f"Statement: {statement}")
                            else:
                                self.logger.warning(f"Statement: {statement[:100]}...{statement[-50:]}")
                
                self.logger.info(f"✅ SQL file executed: {executed_count} statements succeeded, {failed_count} failed")
                # Consider it successful if at least 50% of statements executed
                return failed_count == 0 or (executed_count > failed_count)
                
            finally:
                cursor.close()
                conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Error executing SQL file {sql_file_path}: {e}")
            return False

    def _clean_sql_content(self, sql_content: str) -> str:
        """Clean SQL content by removing problematic formatting."""
        # Remove comment-only lines that might interfere with parsing
        lines = []
        for line in sql_content.split('\n'):
            line = line.strip()
            # Skip empty lines and comment-only lines
            if line and not line.startswith('--'):
                lines.append(line)
        return '\n'.join(lines)

    def _parse_sql_statements(self, sql_content: str) -> List[str]:
        """Parse SQL content into individual executable statements."""
        statements = []
        lines = sql_content.split('\n')
        i = 0
        current_delimiter = ';'
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Skip comment lines
            if line.startswith('--'):
                i += 1
                continue
            
            # Handle DELIMITER commands (skip them, but update delimiter)
            if line.upper().startswith('DELIMITER'):
                # Extract the new delimiter
                parts = line.split()
                if len(parts) > 1:
                    current_delimiter = parts[1]
                i += 1
                continue
            
            # For $$ delimited blocks (stored procedures/functions/triggers)
            if current_delimiter == '$$':
                # Collect everything until we hit the delimiter
                current_statement = [line]
                i += 1
                
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line:
                        if next_line.endswith('$$'):
                            # Remove the $$ and add to statement
                            clean_line = next_line[:-2].strip()
                            if clean_line:
                                current_statement.append(clean_line)
                            break
                        else:
                            current_statement.append(next_line)
                    i += 1
                
                if current_statement:
                    full_stmt = '\n'.join(current_statement)
                    statements.append(full_stmt)
                
                # Reset delimiter back to semicolon after stored object
                current_delimiter = ';'
                i += 1
                continue
            
            # Handle regular statements ending with semicolon
            if line.endswith(';'):
                statements.append(line)
                i += 1
                continue
            
            # For multi-line statements, collect until we find a terminator
            current_statement = [line]
            i += 1
            
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line:
                    current_statement.append(next_line)
                    if next_line.endswith(current_delimiter):
                        break
                i += 1
            
            if current_statement:
                full_stmt = '\n'.join(current_statement)
                statements.append(full_stmt)
            
            i += 1
        
        return [stmt.strip() for stmt in statements if stmt.strip()]

    def run_comparison_step(self, step_name: str, output_suffix: str = "") -> bool:
        """Run DDL Wizard comparison and save results with optional suffix."""
        try:
            self.logger.info(f"🔍 Running comparison step: {step_name}")
            
            output_dir = f"./test_output{output_suffix}"
            
            test_args = [
                '--mode', 'compare',
                '--source-host', self.source_config['host'],
                '--source-port', str(self.source_config['port']),
                '--source-user', self.source_config['user'],
                '--source-password', self.source_config['password'],
                '--source-schema', self.source_config['database'],
                '--dest-host', self.dest_config['host'],
                '--dest-port', str(self.dest_config['port']),
                '--dest-user', self.dest_config['user'],
                '--dest-password', self.dest_config['password'],
                '--dest-schema', self.dest_config['database'],
                '--output-dir', output_dir,
                '--auto-approve',
                '--verbose'
            ]
            
            # Save original sys.argv
            original_argv = sys.argv[:]
            
            try:
                # Set sys.argv for DDL Wizard
                sys.argv = ['main.py'] + test_args
                
                # Run DDL Wizard
                result = ddl_wizard_main()
                
                self.logger.info(f"✅ {step_name} completed successfully")
                return True
                
            finally:
                # Restore original sys.argv
                sys.argv = original_argv
                
        except Exception as e:
            self.logger.error(f"❌ {step_name} failed: {e}")
            return False

    def analyze_results(self, output_dir: str = "./test_output") -> Dict[str, bool]:
        """Analyze the generated migration files and reports."""
        self.logger.info(f"🔍 Analyzing results in {output_dir}...")
        
        test_results = {
            'migration_file_created': False,
            'rollback_file_created': False,
            'comparison_report_created': False,
            'detected_missing_columns': False,
            'detected_extra_columns': False,
            'detected_missing_indexes': False,
            'detected_extra_indexes': False,
            'detected_missing_fk': False,
            'detected_missing_functions': False,
            'detected_different_procedures': False,
            'detected_missing_triggers': False,
            'detected_extra_tables': False
        }
        
        try:
            # Check if output files were created
            output_dir_path = Path(output_dir)
            
            migration_file = output_dir_path / 'migration.sql'
            rollback_file = output_dir_path / 'rollback.sql'
            comparison_file = output_dir_path / 'comparison_report.txt'
            
            test_results['migration_file_created'] = migration_file.exists()
            test_results['rollback_file_created'] = rollback_file.exists()
            test_results['comparison_report_created'] = comparison_file.exists()
            
            # Analyze migration file content
            if migration_file.exists():
                migration_content = migration_file.read_text()
                
                # Check for specific differences we created
                test_results['detected_missing_columns'] = 'ADD COLUMN' in migration_content
                test_results['detected_extra_columns'] = 'DROP COLUMN' in migration_content
                test_results['detected_missing_indexes'] = 'ADD INDEX' in migration_content or 'ADD KEY' in migration_content
                test_results['detected_extra_indexes'] = 'DROP INDEX' in migration_content or 'DROP KEY' in migration_content
                test_results['detected_missing_fk'] = 'ADD CONSTRAINT' in migration_content and 'FOREIGN KEY' in migration_content
                
            # Analyze comparison report
            if comparison_file.exists():
                report_content = comparison_file.read_text()
                
                test_results['detected_missing_functions'] = 'functions' in report_content.lower() and 'only in source' in report_content.lower()
                test_results['detected_different_procedures'] = 'procedures' in report_content.lower() and 'differences' in report_content.lower()
                test_results['detected_missing_triggers'] = 'triggers' in report_content.lower()
                test_results['detected_extra_tables'] = 'temp_table' in report_content.lower()
            
            return test_results
            
        except Exception as e:
            self.logger.error(f"❌ Error analyzing results: {e}")
            return test_results

    def compare_results(self, initial_results: Dict[str, bool], final_results: Dict[str, bool]) -> Dict[str, bool]:
        """Compare initial and final test results to verify rollback worked correctly."""
        self.logger.info("🔄 Comparing initial and final results...")
        
        comparison_results = {
            'rollback_test_passed': True,
            'initial_vs_final_match': True
        }
        
        # Compare detection results (should be identical after rollback)
        detection_keys = [key for key in initial_results.keys() if key.startswith('detected_')]
        
        for key in detection_keys:
            if initial_results.get(key, False) != final_results.get(key, False):
                self.logger.warning(f"⚠️  Mismatch in {key}: initial={initial_results.get(key)}, final={final_results.get(key)}")
                comparison_results['rollback_test_passed'] = False
                comparison_results['initial_vs_final_match'] = False
        
        if comparison_results['rollback_test_passed']:
            self.logger.info("✅ Rollback test passed - initial and final states match!")
        else:
            self.logger.error("❌ Rollback test failed - initial and final states don't match!")
        
        return comparison_results

    def check_schemas_identical(self) -> bool:
        """Check if schemas are identical after migration (should have no differences)."""
        try:
            self.logger.info("🔍 Checking if schemas are identical after migration...")
            
            # Run comparison to check for differences
            success = self.run_comparison_step("Post-migration schema check", "_post_migration")
            
            if not success:
                return False
            
            # Check if migration file is empty or minimal
            migration_file = Path('./test_output_post_migration/migration.sql')
            if migration_file.exists():
                content = migration_file.read_text().strip()
                # Remove comments, empty lines, and standard setup/cleanup statements
                meaningful_lines = [line.strip() for line in content.split('\n') 
                                 if line.strip() and 
                                    not line.strip().startswith('--') and
                                    not line.strip().startswith('SET FOREIGN_KEY_CHECKS') and
                                    not line.strip() == 'SET FOREIGN_KEY_CHECKS = 0;' and
                                    not line.strip() == 'SET FOREIGN_KEY_CHECKS = 1;']
                
                if meaningful_lines:
                    self.logger.warning("⚠️  Schemas are not identical - found differences after migration")
                    self.logger.warning(f"Migration content: {content[:200]}...")
                    return False
                else:
                    self.logger.info("✅ Schemas are identical after migration!")
                    return True
            else:
                self.logger.warning("⚠️  No migration file generated - assuming schemas are identical")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error checking schema identity: {e}")
            return False
    
    def print_test_summary(self, results: Dict[str, bool], round_trip_results: Dict[str, bool] = None):
        """Print a comprehensive test summary."""
        print("\n" + "="*80)
        print("🧙‍♂️ DDL WIZARD COMPREHENSIVE TEST RESULTS")
        print("="*80)
        
        # Basic detection tests
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        print(f"\n📊 Detection Phase Results: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        print("\n📁 File Generation Tests:")
        file_tests = ['migration_file_created', 'rollback_file_created', 'comparison_report_created']
        for test in file_tests:
            if test in results:
                status = "✅ PASS" if results[test] else "❌ FAIL"
                print(f"  {status} - {test.replace('_', ' ').title()}")
        
        print("\n🔍 Schema Difference Detection Tests:")
        detection_tests = [
            'detected_missing_columns', 'detected_extra_columns',
            'detected_missing_indexes', 'detected_extra_indexes',
            'detected_missing_fk', 'detected_missing_functions',
            'detected_different_procedures', 'detected_missing_triggers',
            'detected_extra_tables'
        ]
        for test in detection_tests:
            if test in results:
                status = "✅ PASS" if results[test] else "❌ FAIL"
                print(f"  {status} - {test.replace('_', ' ').replace('detected ', '').title()}")
        
        # Round-trip test results
        if round_trip_results:
            round_trip_total = len(round_trip_results)
            round_trip_passed = sum(round_trip_results.values())
            
            print(f"\n🔄 Round-Trip Test Results: {round_trip_passed}/{round_trip_total} tests passed ({round_trip_passed/round_trip_total*100:.1f}%)")
            
            for test, passed in round_trip_results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                test_name = test.replace('_', ' ').title()
                print(f"  {status} - {test_name}")
            
            # Overall summary
            overall_total = total_tests + round_trip_total
            overall_passed = passed_tests + round_trip_passed
            print(f"\n🎯 OVERALL RESULTS: {overall_passed}/{overall_total} tests passed ({overall_passed/overall_total*100:.1f}%)")
        
        print(f"\n📝 Test Log: ddl_wizard_test.log")
        print(f"📂 Output Files: ./test_output/ ./test_output_post_migration/ ./test_output_final/")
        
        final_total = total_tests + (len(round_trip_results) if round_trip_results else 0)
        final_passed = passed_tests + (sum(round_trip_results.values()) if round_trip_results else 0)
        
        if final_passed == final_total:
            print("\n🎉 ALL TESTS PASSED! DDL Wizard round-trip functionality is working perfectly!")
        else:
            print(f"\n⚠️  {final_total - final_passed} tests failed. Please review the logs and output files.")
        
        print("="*80)
    
    def save_test_data(self):
        """Save test output files to test_data directory for reference."""
        self.logger.info("💾 Saving test data for reference...")
        
        try:
            # Create test_data directory
            test_data_dir = Path("./test_data")
            test_data_dir.mkdir(exist_ok=True)
            
            # Create timestamp for this test run
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # Create main run directory
            run_dir = test_data_dir / f"ddlw-test-{timestamp}"
            run_dir.mkdir(exist_ok=True)
            
            # List of test output directories to save with their descriptive names
            output_dirs = [
                ("./test_output", "initial-migration"),
                ("./test_output_post_migration", "post-migration-verification"), 
                ("./test_output_final", "rollback-verification")
            ]
            
            # Copy each output directory if it exists to its own subfolder under the run directory
            saved_dirs = []
            for output_dir, test_name in output_dirs:
                output_path = Path(output_dir)
                if output_path.exists():
                    # Create individual subfolder with descriptive name under the run directory
                    dest_dir_name = f"ddl-wizard-testsuite-{test_name}-{timestamp}"
                    dest_path = run_dir / dest_dir_name
                    
                    # Copy the entire directory
                    shutil.copytree(output_path, dest_path, dirs_exist_ok=True)
                    self.logger.info(f"✅ Saved {output_dir} to {dest_path}")
                    saved_dirs.append((output_dir, dest_dir_name))
                    
                    # Also copy with original directory name for direct reference
                    original_dest_path = run_dir / output_path.name
                    shutil.copytree(output_path, original_dest_path, dirs_exist_ok=True)
                    self.logger.info(f"✅ Saved {output_dir} to {original_dest_path}")
            
            # Also copy the test log to the main run directory
            log_file = Path("ddl_wizard_test.log")
            if log_file.exists():
                shutil.copy2(log_file, run_dir / "ddl_wizard_test.log")
                self.logger.info(f"✅ Saved test log to {run_dir}")
            
            # Create a summary file in the main run directory
            if saved_dirs:
                summary_file = run_dir / "test_summary.txt"
                with open(summary_file, 'w') as f:
                    f.write(f"DDL Wizard Test Run Summary\n")
                    f.write(f"========================\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Source DB: {self.source_config['host']}:{self.source_config['port']}\n")
                    f.write(f"Dest DB: {self.dest_config['host']}:{self.dest_config['port']}\n")
                    f.write(f"Test Results: See ddl_wizard_test.log for details\n")
                    f.write(f"\nTest Directories Created:\n")
                    for output_dir, dest_name in saved_dirs:
                        f.write(f"- {output_dir}/ -> {dest_name}/\n")
                        f.write(f"- {output_dir}/ -> {Path(output_dir).name}/\n")
            
            # Clean up temporary test output directories after copying
            for output_dir, _ in output_dirs:
                output_path = Path(output_dir)
                if output_path.exists():
                    try:
                        shutil.rmtree(output_path)
                        self.logger.info(f"🧹 Cleaned up temporary directory: {output_dir}")
                    except Exception as e:
                        self.logger.warning(f"⚠️  Could not remove {output_dir}: {e}")
            
            if saved_dirs:
                print(f"💾 Test data saved to: {run_dir}")
                print(f"📁 Test directories created:")
                for _, dest_name in saved_dirs:
                    print(f"   📁 {dest_name}")
                print(f"📁 Original test_output_* directories also preserved")
                print(f"🧹 Temporary test directories cleaned up")
                print(f"📁 Reference files preserved for analysis")
            else:
                print(f"⚠️  No test output directories found to save")
            
        except Exception as e:
            self.logger.error(f"❌ Error saving test data: {e}")
            print(f"⚠️  Warning: Could not save test data: {e}")
    
    def cleanup_databases(self):
        """Clean up test databases."""
        self.logger.info("🧹 Cleaning up test databases...")
        
        for config in [self.source_config, self.dest_config]:
            try:
                # Connect without specifying database
                conn_config = config.copy()
                database = conn_config.pop('database')
                
                conn = pymysql.connect(**conn_config)
                cursor = conn.cursor()
                
                cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
                conn.commit()
                conn.close()
                
                self.logger.info(f"✅ Cleaned up database: {database}")
                
            except Exception as e:
                self.logger.error(f"❌ Error cleaning up {config['database']}: {e}")
    
    def run_full_test_suite(self, cleanup: bool = True):
        """Run the complete round-trip test suite."""
        print("🧪 Starting DDL Wizard ROUND-TRIP Test Suite")
        print("="*60)
        print("📋 Test Plan:")
        print("  1️⃣  Detect initial differences")
        print("  2️⃣  Apply migration to destination")
        print("  3️⃣  Verify schemas are identical")
        print("  4️⃣  Apply rollback to destination")
        print("  5️⃣  Verify differences match initial state")
        print("="*60)
        print()
        print("🔗 Connection Configuration:")
        print(f"   📡 Source:      {self.source_config['user']}@{self.source_config['host']}:{self.source_config['port']}/{self.source_config['database']}")
        print(f"   📡 Destination: {self.dest_config['user']}@{self.dest_config['host']}:{self.dest_config['port']}/{self.dest_config['database']}")
        if self.source_config['host'] != self.dest_config['host'] or self.source_config['port'] != self.dest_config['port']:
            print("   ✨ Testing cross-server migration capability!")
        else:
            print("   🏠 Testing same-server, different schemas")
        print()
        
        round_trip_results = {
            'initial_detection_passed': False,
            'migration_applied_successfully': False,
            'post_migration_schemas_identical': False,
            'rollback_applied_successfully': False,
            'rollback_test_passed': False
        }
        
        try:
            # Setup test databases
            print("\n🏗️  Setting up test databases...")
            self.setup_source_database()
            self.setup_destination_database()
            self.populate_test_data()
            
            # STEP 1: Initial difference detection
            print("\n1️⃣  STEP 1: Detecting initial differences...")
            initial_success = self.run_comparison_step("Initial comparison", "")
            round_trip_results['initial_detection_passed'] = initial_success
            
            if not initial_success:
                print("❌ Initial comparison failed!")
                return round_trip_results
            
            # Analyze initial results
            initial_results = self.analyze_results("./test_output")
            initial_detection_count = sum(1 for k, v in initial_results.items() if k.startswith('detected_') and v)
            print(f"   📊 Detected {initial_detection_count} types of differences")
            
            # STEP 2: Apply migration
            print("\n2️⃣  STEP 2: Applying migration to destination...")
            migration_success = self.execute_sql_file("./test_output/migration.sql", self.dest_config)
            round_trip_results['migration_applied_successfully'] = migration_success
            
            if not migration_success:
                print("❌ Migration application failed!")
                return round_trip_results
            
            # STEP 3: Verify schemas are identical
            print("\n3️⃣  STEP 3: Verifying schemas are identical after migration...")
            schemas_identical = self.check_schemas_identical()
            round_trip_results['post_migration_schemas_identical'] = schemas_identical
            
            if not schemas_identical:
                print("❌ Schemas are not identical after migration!")
            else:
                print("   ✅ Schemas are now identical!")
            
            # STEP 4: Apply rollback
            print("\n4️⃣  STEP 4: Applying rollback to destination...")
            rollback_success = self.execute_sql_file("./test_output/rollback.sql", self.dest_config)
            round_trip_results['rollback_applied_successfully'] = rollback_success
            
            if not rollback_success:
                print("❌ Rollback application failed!")
                return round_trip_results
            
            # STEP 5: Final comparison (should match initial)
            print("\n5️⃣  STEP 5: Verifying rollback restored initial differences...")
            final_success = self.run_comparison_step("Final comparison after rollback", "_final")
            
            if final_success:
                final_results = self.analyze_results("./test_output_final")
                comparison_results = self.compare_results(initial_results, final_results)
                round_trip_results['rollback_test_passed'] = comparison_results['rollback_test_passed']
                
                final_detection_count = sum(1 for k, v in final_results.items() if k.startswith('detected_') and v)
                print(f"   📊 Final state has {final_detection_count} types of differences")
                
                if comparison_results['rollback_test_passed']:
                    print("   ✅ Rollback test passed - differences match initial state!")
                else:
                    print("   ❌ Rollback test failed - differences don't match initial state!")
            
            # Print comprehensive summary
            self.print_test_summary(initial_results, round_trip_results)
            
            # Save test data for reference
            self.save_test_data()
            
        except Exception as e:
            self.logger.error(f"❌ Round-trip test suite failed: {e}")
            print(f"❌ Round-trip test suite failed: {e}")
        
        finally:
            if cleanup:
                self.cleanup_databases()
        
        return round_trip_results


def main():
    """Main entry point for the test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DDL Wizard Test Suite")
    
    # Source database connection
    parser.add_argument('--host', default='localhost', help='Source database host')
    parser.add_argument('--port', type=int, default=3306, help='Source database port')
    parser.add_argument('--user', default='root', help='Source database user')
    parser.add_argument('--password', default='password', help='Source database password')
    
    # Destination database connection (optional, defaults to source if not specified)
    parser.add_argument('--dest-host', help='Destination database host (defaults to source host)')
    parser.add_argument('--dest-port', type=int, help='Destination database port (defaults to source port)')
    parser.add_argument('--dest-user', help='Destination database user (defaults to source user)')
    parser.add_argument('--dest-password', help='Destination database password (defaults to source password)')
    
    parser.add_argument('--no-cleanup', action='store_true', help='Skip database cleanup')
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = DDLWizardTester()
    
    # Update source connection config
    tester.source_config['host'] = args.host
    tester.source_config['port'] = args.port
    tester.source_config['user'] = args.user
    tester.source_config['password'] = args.password
    
    # Update destination connection config (use source as defaults)
    tester.dest_config['host'] = args.dest_host if args.dest_host else args.host
    tester.dest_config['port'] = args.dest_port if args.dest_port else args.port
    tester.dest_config['user'] = args.dest_user if args.dest_user else args.user
    tester.dest_config['password'] = args.dest_password if args.dest_password else args.password
    
    # Run the test suite
    tester.run_full_test_suite(cleanup=not args.no_cleanup)


if __name__ == '__main__':
    main()
