-- DDL Wizard Test Data - Source Schema
-- This script creates a sample source database schema for testing DDL Wizard
-- Run this script on your source database instance

-- Create the source database
CREATE DATABASE IF NOT EXISTS ddlwizard_source_test;
USE ddlwizard_source_test;

-- Users table
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB COMMENT='User accounts table';

-- Products table
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    category_id INT,
    stock_quantity INT DEFAULT 0,
    sku VARCHAR(50) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category_id),
    INDEX idx_sku (sku),
    INDEX idx_price (price)
) ENGINE=InnoDB COMMENT='Product catalog';

-- Categories table
CREATE TABLE categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    parent_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_id),
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Product categories';

-- Orders table
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    shipping_address TEXT,
    billing_address TEXT,
    notes TEXT,
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_date (order_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Customer orders';

-- Order items table
CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    INDEX idx_order (order_id),
    INDEX idx_product (product_id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Individual items within orders';

-- Add foreign key constraint to products table
ALTER TABLE products 
ADD CONSTRAINT fk_products_category 
FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;

-- Stored procedure to get user order history
DELIMITER //
CREATE PROCEDURE GetUserOrderHistory(IN user_id_param INT)
BEGIN
    SELECT 
        o.id as order_id,
        o.order_date,
        o.status,
        o.total_amount,
        COUNT(oi.id) as item_count
    FROM orders o
    LEFT JOIN order_items oi ON o.id = oi.order_id
    WHERE o.user_id = user_id_param
    GROUP BY o.id
    ORDER BY o.order_date DESC;
END //
DELIMITER ;

-- Function to calculate user total spent
DELIMITER //
CREATE FUNCTION GetUserTotalSpent(user_id_param INT) 
RETURNS DECIMAL(12,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE total DECIMAL(12,2) DEFAULT 0.00;
    
    SELECT COALESCE(SUM(total_amount), 0.00) INTO total
    FROM orders 
    WHERE user_id = user_id_param AND status IN ('delivered', 'shipped');
    
    RETURN total;
END //
DELIMITER ;

-- Trigger to update product stock when order is placed
DELIMITER //
CREATE TRIGGER update_stock_after_order
    AFTER INSERT ON order_items
    FOR EACH ROW
BEGIN
    UPDATE products 
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE id = NEW.product_id;
END //
DELIMITER ;

-- Event to clean up old cancelled orders (runs daily)
CREATE EVENT IF NOT EXISTS cleanup_cancelled_orders
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
    DELETE FROM orders 
    WHERE status = 'cancelled' 
    AND order_date < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Insert sample data
INSERT INTO categories (name, description) VALUES 
('Electronics', 'Electronic devices and gadgets'),
('Books', 'Books and educational materials'),
('Clothing', 'Apparel and accessories'),
('Home & Garden', 'Home improvement and garden supplies');

INSERT INTO products (name, description, price, category_id, stock_quantity, sku) VALUES 
('Smartphone Pro', 'Latest smartphone with advanced features', 999.99, 1, 50, 'PHONE-001'),
('Laptop Ultra', 'High-performance laptop for professionals', 1299.99, 1, 25, 'LAPTOP-001'),
('Programming Guide', 'Comprehensive programming tutorial', 49.99, 2, 100, 'BOOK-001'),
('Casual T-Shirt', 'Comfortable cotton t-shirt', 19.99, 3, 200, 'SHIRT-001'),
('Garden Hose', '50ft flexible garden hose', 29.99, 4, 75, 'HOSE-001');

INSERT INTO users (username, email, password_hash, first_name, last_name) VALUES 
('johndoe', 'john.doe@example.com', '$2b$12$hash1', 'John', 'Doe'),
('janesmith', 'jane.smith@example.com', '$2b$12$hash2', 'Jane', 'Smith'),
('bobwilson', 'bob.wilson@example.com', '$2b$12$hash3', 'Bob', 'Wilson');

INSERT INTO orders (user_id, status, total_amount, shipping_address) VALUES 
(1, 'delivered', 1049.98, '123 Main St, City, State 12345'),
(2, 'shipped', 69.98, '456 Oak Ave, City, State 12345'),
(3, 'pending', 29.99, '789 Pine Rd, City, State 12345');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES 
(1, 1, 1, 999.99),
(1, 4, 2, 19.99),
(2, 3, 1, 49.99),
(2, 4, 1, 19.99),
(3, 5, 1, 29.99);

-- Create a view for order summaries
CREATE VIEW order_summary AS
SELECT 
    o.id,
    o.order_date,
    u.username,
    u.email,
    o.status,
    o.total_amount,
    COUNT(oi.id) as item_count
FROM orders o
JOIN users u ON o.user_id = u.id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id;

SHOW TABLES;
SELECT 'Source schema created successfully!' as Status;
