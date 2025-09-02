-- DDL Wizard Test Data - Destination Schema
-- This script creates a sample destination database schema for testing DDL Wizard
-- This schema has intentional differences from the source to demonstrate migration capabilities

-- Create the destination database
CREATE DATABASE IF NOT EXISTS ddlwizard_dest_test;
USE ddlwizard_dest_test;

-- Users table (with some differences from source)
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,  -- Added UNIQUE constraint
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    full_name VARCHAR(101) GENERATED ALWAYS AS (CONCAT(first_name, ' ', last_name)) STORED,  -- New generated column
    phone VARCHAR(20),  -- New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    -- Removed INDEX idx_username (already unique)
    INDEX idx_email (email),
    INDEX idx_phone (phone)  -- New index
) ENGINE=InnoDB COMMENT='User accounts table - updated version';

-- Products table (with modifications)
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,  -- Increased length
    description TEXT,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    sale_price DECIMAL(10,2),  -- New column for sale pricing
    category_id INT,
    stock_quantity INT DEFAULT 0,
    min_stock_level INT DEFAULT 5,  -- New column for reorder point
    sku VARCHAR(50) UNIQUE,
    weight DECIMAL(8,3),  -- New column
    dimensions VARCHAR(50),  -- New column
    is_featured BOOLEAN DEFAULT FALSE,  -- New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category_id),
    INDEX idx_sku (sku),
    INDEX idx_price (price),
    INDEX idx_featured (is_featured)  -- New index
) ENGINE=InnoDB COMMENT='Product catalog - enhanced version';

-- Categories table (mostly the same)
CREATE TABLE categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    parent_id INT,
    sort_order INT DEFAULT 0,  -- New column
    is_active BOOLEAN DEFAULT TRUE,  -- New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_id),
    INDEX idx_sort (sort_order),  -- New index
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Product categories - enhanced version';

-- Orders table (with some changes)
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    order_number VARCHAR(20) UNIQUE,  -- New column
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded') DEFAULT 'pending',  -- Added 'refunded'
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    tax_amount DECIMAL(10,2) DEFAULT 0.00,  -- New column
    shipping_cost DECIMAL(8,2) DEFAULT 0.00,  -- New column
    discount_amount DECIMAL(10,2) DEFAULT 0.00,  -- New column
    shipping_address TEXT,
    billing_address TEXT,
    tracking_number VARCHAR(50),  -- New column
    notes TEXT,
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_date (order_date),
    INDEX idx_order_number (order_number),  -- New index
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Customer orders - enhanced version';

-- Order items table (similar but with some additions)
CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(8,2) DEFAULT 0.00,  -- New column
    total_price DECIMAL(12,2) GENERATED ALWAYS AS ((quantity * unit_price) - discount_amount) STORED,  -- Updated calculation
    INDEX idx_order (order_id),
    INDEX idx_product (product_id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Individual items within orders - enhanced version';

-- New table that doesn't exist in source
CREATE TABLE product_reviews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    user_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(100),
    review_text TEXT,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_votes INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_product (product_id),
    INDEX idx_user (user_id),
    INDEX idx_rating (rating),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_product_review (user_id, product_id)
) ENGINE=InnoDB COMMENT='Product reviews and ratings';

-- Add foreign key constraint to products table
ALTER TABLE products 
ADD CONSTRAINT fk_products_category 
FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;

-- Updated stored procedure with different signature
DELIMITER //
CREATE PROCEDURE GetUserOrderHistory(
    IN user_id_param INT,
    IN limit_param INT DEFAULT 10  -- Added parameter with default
)
BEGIN
    SELECT 
        o.id as order_id,
        o.order_number,
        o.order_date,
        o.status,
        o.total_amount,
        o.tax_amount,
        o.shipping_cost,
        COUNT(oi.id) as item_count
    FROM orders o
    LEFT JOIN order_items oi ON o.id = oi.order_id
    WHERE o.user_id = user_id_param
    GROUP BY o.id
    ORDER BY o.order_date DESC
    LIMIT limit_param;
END //
DELIMITER ;

-- New stored procedure not in source
DELIMITER //
CREATE PROCEDURE GetProductReviewSummary(IN product_id_param INT)
BEGIN
    SELECT 
        p.name as product_name,
        COUNT(pr.id) as total_reviews,
        AVG(pr.rating) as average_rating,
        COUNT(CASE WHEN pr.rating = 5 THEN 1 END) as five_star_count,
        COUNT(CASE WHEN pr.rating = 4 THEN 1 END) as four_star_count,
        COUNT(CASE WHEN pr.rating = 3 THEN 1 END) as three_star_count,
        COUNT(CASE WHEN pr.rating = 2 THEN 1 END) as two_star_count,
        COUNT(CASE WHEN pr.rating = 1 THEN 1 END) as one_star_count
    FROM products p
    LEFT JOIN product_reviews pr ON p.id = pr.product_id
    WHERE p.id = product_id_param
    GROUP BY p.id, p.name;
END //
DELIMITER ;

-- Modified function with different logic
DELIMITER //
CREATE FUNCTION GetUserTotalSpent(user_id_param INT) 
RETURNS DECIMAL(12,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE total DECIMAL(12,2) DEFAULT 0.00;
    
    -- Updated to include tax and shipping, exclude discount
    SELECT COALESCE(SUM(total_amount + tax_amount + shipping_cost - discount_amount), 0.00) INTO total
    FROM orders 
    WHERE user_id = user_id_param AND status IN ('delivered', 'shipped');
    
    RETURN total;
END //
DELIMITER ;

-- New function not in source
DELIMITER //
CREATE FUNCTION GetProductAverageRating(product_id_param INT) 
RETURNS DECIMAL(3,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE avg_rating DECIMAL(3,2) DEFAULT 0.00;
    
    SELECT COALESCE(AVG(rating), 0.00) INTO avg_rating
    FROM product_reviews 
    WHERE product_id = product_id_param;
    
    RETURN avg_rating;
END //
DELIMITER ;

-- Different trigger with updated logic
DELIMITER //
CREATE TRIGGER update_stock_after_order
    AFTER INSERT ON order_items
    FOR EACH ROW
BEGIN
    UPDATE products 
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE id = NEW.product_id;
    
    -- Additional logic: check if stock is below minimum
    INSERT INTO stock_alerts (product_id, alert_type, created_at)
    SELECT NEW.product_id, 'LOW_STOCK', NOW()
    FROM products p
    WHERE p.id = NEW.product_id 
    AND p.stock_quantity <= p.min_stock_level;
END //
DELIMITER ;

-- New trigger not in source
DELIMITER //
CREATE TRIGGER generate_order_number
    BEFORE INSERT ON orders
    FOR EACH ROW
BEGIN
    IF NEW.order_number IS NULL THEN
        SET NEW.order_number = CONCAT('ORD-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(NEW.id, 6, '0'));
    END IF;
END //
DELIMITER ;

-- Different event with modified schedule
CREATE EVENT IF NOT EXISTS cleanup_cancelled_orders
ON SCHEDULE EVERY 7 DAY  -- Weekly instead of daily
STARTS CURRENT_TIMESTAMP
DO
    DELETE FROM orders 
    WHERE status = 'cancelled' 
    AND order_date < DATE_SUB(NOW(), INTERVAL 90 DAY);  -- 90 days instead of 30

-- New event not in source
CREATE EVENT IF NOT EXISTS update_featured_products
ON SCHEDULE EVERY 1 WEEK
STARTS CURRENT_TIMESTAMP
DO
    UPDATE products p
    SET is_featured = (
        SELECT COUNT(*) > 10
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE oi.product_id = p.id
        AND o.order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    );

-- Create table for stock alerts (referenced in trigger)
CREATE TABLE stock_alerts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    alert_type ENUM('LOW_STOCK', 'OUT_OF_STOCK') NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    INDEX idx_product (product_id),
    INDEX idx_type (alert_type),
    INDEX idx_resolved (is_resolved),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Stock level alerts';

-- Insert sample data with some differences
INSERT INTO categories (name, description, sort_order, is_active) VALUES 
('Electronics', 'Electronic devices and gadgets', 1, TRUE),
('Books', 'Books and educational materials', 2, TRUE),
('Clothing', 'Apparel and accessories', 3, TRUE),
('Home & Garden', 'Home improvement and garden supplies', 4, TRUE),
('Sports & Outdoors', 'Sports equipment and outdoor gear', 5, TRUE);  -- New category

INSERT INTO products (name, description, price, sale_price, category_id, stock_quantity, min_stock_level, sku, weight, is_featured) VALUES 
('Smartphone Pro', 'Latest smartphone with advanced features', 999.99, 899.99, 1, 50, 10, 'PHONE-001', 0.180, TRUE),
('Laptop Ultra', 'High-performance laptop for professionals', 1299.99, NULL, 1, 25, 5, 'LAPTOP-001', 2.100, TRUE),
('Programming Guide', 'Comprehensive programming tutorial', 49.99, 39.99, 2, 100, 20, 'BOOK-001', 0.500, FALSE),
('Casual T-Shirt', 'Comfortable cotton t-shirt', 19.99, NULL, 3, 200, 50, 'SHIRT-001', 0.200, FALSE),
('Garden Hose', '50ft flexible garden hose', 29.99, 24.99, 4, 75, 15, 'HOSE-001', 3.200, FALSE),
('Tennis Racket', 'Professional grade tennis racket', 129.99, NULL, 5, 30, 5, 'RACKET-001', 0.300, FALSE);  -- New product

INSERT INTO users (username, email, password_hash, first_name, last_name, phone) VALUES 
('johndoe', 'john.doe@example.com', '$2b$12$hash1', 'John', 'Doe', '+1-555-0101'),
('janesmith', 'jane.smith@example.com', '$2b$12$hash2', 'Jane', 'Smith', '+1-555-0102'),
('bobwilson', 'bob.wilson@example.com', '$2b$12$hash3', 'Bob', 'Wilson', '+1-555-0103'),
('alicecooper', 'alice.cooper@example.com', '$2b$12$hash4', 'Alice', 'Cooper', '+1-555-0104');  -- New user

-- Generate order numbers for existing orders
INSERT INTO orders (user_id, order_number, status, total_amount, tax_amount, shipping_cost, shipping_address) VALUES 
(1, 'ORD-20250901-000001', 'delivered', 1049.98, 84.00, 15.00, '123 Main St, City, State 12345'),
(2, 'ORD-20250901-000002', 'shipped', 69.98, 5.60, 10.00, '456 Oak Ave, City, State 12345'),
(3, 'ORD-20250902-000003', 'pending', 29.99, 2.40, 8.00, '789 Pine Rd, City, State 12345'),
(4, 'ORD-20250902-000004', 'processing', 159.98, 12.80, 12.00, '321 Elm St, City, State 12345');  -- New order

INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_amount) VALUES 
(1, 1, 1, 999.99, 100.00),  -- Applied discount
(1, 4, 2, 19.99, 0.00),
(2, 3, 1, 49.99, 10.00),   -- Applied discount
(2, 4, 1, 19.99, 0.00),
(3, 5, 1, 29.99, 5.00),    -- Applied discount
(4, 6, 1, 129.99, 0.00);   -- New item

-- Insert sample reviews
INSERT INTO product_reviews (product_id, user_id, rating, title, review_text, is_verified_purchase) VALUES 
(1, 1, 5, 'Excellent phone!', 'Best smartphone I have ever owned. Great camera and battery life.', TRUE),
(1, 2, 4, 'Good but pricey', 'Great features but quite expensive. Worth it if you can afford it.', FALSE),
(2, 3, 5, 'Perfect for work', 'Outstanding performance for professional use. Highly recommended.', TRUE),
(3, 2, 4, 'Great learning resource', 'Very comprehensive guide. Helped me learn programming quickly.', TRUE),
(4, 4, 3, 'Average quality', 'Decent t-shirt but nothing special. Fits as expected.', TRUE);

-- Enhanced view with more information
CREATE VIEW order_summary AS
SELECT 
    o.id,
    o.order_number,
    o.order_date,
    u.username,
    u.email,
    u.full_name,
    o.status,
    o.total_amount,
    o.tax_amount,
    o.shipping_cost,
    o.discount_amount,
    COUNT(oi.id) as item_count,
    COALESCE(AVG(pr.rating), 0) as avg_product_rating
FROM orders o
JOIN users u ON o.user_id = u.id
LEFT JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN product_reviews pr ON oi.product_id = pr.product_id
GROUP BY o.id;

-- New view not in source
CREATE VIEW product_catalog AS
SELECT 
    p.id,
    p.name,
    p.description,
    p.price,
    p.sale_price,
    COALESCE(p.sale_price, p.price) as effective_price,
    c.name as category_name,
    p.stock_quantity,
    p.is_featured,
    COALESCE(AVG(pr.rating), 0) as avg_rating,
    COUNT(pr.id) as review_count
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN product_reviews pr ON p.id = pr.product_id
WHERE c.is_active = TRUE
GROUP BY p.id;

SHOW TABLES;
SELECT 'Destination schema created successfully!' as Status;
