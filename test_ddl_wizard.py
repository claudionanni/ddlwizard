#!/usr/bin/env python3
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
from pathlib import Path
from typing import Dict, Any, Optional

# Add the current directory to Python path so we can import DDL Wizard modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pymysql
    from database import DatabaseManager
    from main import main as ddl_wizard_main
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
                SET NEW.updated_at = CURRENT_TIMESTAMP
            """)
            
            cursor.execute("DROP TRIGGER IF EXISTS tr_products_update_timestamp")
            cursor.execute("""
            CREATE TRIGGER tr_products_update_timestamp
                BEFORE UPDATE ON products
                FOR EACH ROW
                SET NEW.updated_at = CURRENT_TIMESTAMP
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
            
            # Create different trigger
            cursor.execute("DROP TRIGGER IF EXISTS tr_customers_update_timestamp")
            cursor.execute("""
            CREATE TRIGGER tr_customers_update_timestamp
                BEFORE UPDATE ON customers
                FOR EACH ROW
                SET NEW.updated_at = CURRENT_TIMESTAMP
            """)
            
            # Missing trigger that exists in source
            # tr_orders_update_timestamp and tr_products_update_timestamp are not created
            
            conn.commit()
            self.logger.info("✅ Destination database setup completed")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ Error setting up destination database: {e}")
            raise
        finally:
            conn.close()
    
    def populate_test_data(self):
        """Populate both databases with sample data."""
        self.logger.info("📝 Populating test data...")
        
        for config in [self.source_config, self.dest_config]:
            conn = self.create_connection(config)
            cursor = conn.cursor()
            
            try:
                # Insert sample data
                cursor.execute("INSERT IGNORE INTO categories (name, description) VALUES ('Electronics', 'Electronic devices and gadgets')")
                cursor.execute("INSERT IGNORE INTO categories (name, description) VALUES ('Books', 'Physical and digital books')")
                
                cursor.execute("INSERT IGNORE INTO customers (email, first_name, last_name, phone, city, country) VALUES ('john@example.com', 'John', 'Doe', '+1234567890', 'New York', 'USA')")
                cursor.execute("INSERT IGNORE INTO customers (email, first_name, last_name, phone, city, country) VALUES ('jane@example.com', 'Jane', 'Smith', '+1987654321', 'London', 'UK')")
                
                conn.commit()
                self.logger.info(f"✅ Test data populated in {config['database']}")
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"❌ Error populating test data in {config['database']}: {e}")
            finally:
                conn.close()
    
    def run_ddl_wizard_test(self) -> bool:
        """Run DDL Wizard and capture results."""
        self.logger.info("🧙‍♂️ Running DDL Wizard comparison...")
        
        try:
            # Prepare DDL Wizard arguments
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
                '--output-dir', './test_output',
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
                
                self.logger.info("✅ DDL Wizard completed successfully")
                return True
                
            finally:
                # Restore original sys.argv
                sys.argv = original_argv
                
        except Exception as e:
            self.logger.error(f"❌ DDL Wizard failed: {e}")
            return False
    
    def analyze_results(self) -> Dict[str, bool]:
        """Analyze the generated migration files and reports."""
        self.logger.info("🔍 Analyzing DDL Wizard results...")
        
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
            output_dir = Path('./test_output')
            
            migration_file = output_dir / 'migration.sql'
            rollback_file = output_dir / 'rollback.sql'
            comparison_file = output_dir / 'comparison_report.txt'
            
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
    
    def print_test_summary(self, results: Dict[str, bool]):
        """Print a comprehensive test summary."""
        print("\n" + "="*80)
        print("🧙‍♂️ DDL WIZARD TEST RESULTS SUMMARY")
        print("="*80)
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        print(f"\n📊 Overall Results: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        print("\n📁 File Generation Tests:")
        file_tests = ['migration_file_created', 'rollback_file_created', 'comparison_report_created']
        for test in file_tests:
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
            status = "✅ PASS" if results[test] else "❌ FAIL"
            print(f"  {status} - {test.replace('_', ' ').replace('detected ', '').title()}")
        
        print(f"\n📝 Test Log: ddl_wizard_test.log")
        print(f"📂 Output Files: ./test_output/")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! DDL Wizard is working correctly!")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} tests failed. Please review the logs and output files.")
        
        print("="*80)
    
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
        """Run the complete test suite."""
        print("🧪 Starting DDL Wizard Comprehensive Test Suite")
        print("="*50)
        
        try:
            # Setup test databases
            self.setup_source_database()
            self.setup_destination_database()
            self.populate_test_data()
            
            # Run DDL Wizard
            wizard_success = self.run_ddl_wizard_test()
            
            if wizard_success:
                # Analyze results
                results = self.analyze_results()
                self.print_test_summary(results)
            else:
                print("❌ DDL Wizard execution failed. Check logs for details.")
            
        except Exception as e:
            self.logger.error(f"❌ Test suite failed: {e}")
            print(f"❌ Test suite failed: {e}")
        
        finally:
            if cleanup:
                self.cleanup_databases()


def main():
    """Main entry point for the test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DDL Wizard Test Suite")
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', type=int, default=3306, help='Database port')
    parser.add_argument('--user', default='root', help='Database user')
    parser.add_argument('--password', default='password', help='Database password')
    parser.add_argument('--no-cleanup', action='store_true', help='Skip database cleanup')
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = DDLWizardTester()
    
    # Update connection configs
    for config in [tester.source_config, tester.dest_config]:
        config['host'] = args.host
        config['port'] = args.port
        config['user'] = args.user
        config['password'] = args.password
    
    # Run the test suite
    tester.run_full_test_suite(cleanup=not args.no_cleanup)


if __name__ == '__main__':
    main()
