-- DDL Wizard Advanced Test Data - Destination Schema
-- Complex database with 30+ differences from source for comprehensive testing
-- Created: September 4, 2025

DROP DATABASE IF EXISTS ddw_test_dst;
CREATE DATABASE IF NOT EXISTS ddw_test_dst;
USE ddw_test_dst;

-- Drop existing objects if they exist
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS product_reviews;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS user_profiles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS system_config;
DROP TABLE IF EXISTS payment_methods;
DROP TABLE IF EXISTS shipping_addresses;
DROP TABLE IF EXISTS inventory_tracking;
DROP TABLE IF EXISTS customer_analytics;
DROP TABLE IF EXISTS promotional_campaigns;
DROP TABLE IF EXISTS order_tracking;

DROP VIEW IF EXISTS customer_summary;
DROP VIEW IF EXISTS product_analytics;
DROP VIEW IF EXISTS sales_dashboard;
DROP VIEW IF EXISTS inventory_report;

DROP PROCEDURE IF EXISTS process_order;
DROP PROCEDURE IF EXISTS update_inventory;
DROP PROCEDURE IF EXISTS send_notification;
DROP PROCEDURE IF EXISTS backup_data;

DROP FUNCTION IF EXISTS calculate_discount;
DROP FUNCTION IF EXISTS format_currency;
DROP FUNCTION IF EXISTS generate_slug;
DROP FUNCTION IF EXISTS calculate_commission;

DROP TRIGGER IF EXISTS users_audit_trigger;
DROP TRIGGER IF EXISTS product_price_trigger;
DROP TRIGGER IF EXISTS order_notification_trigger;

DROP EVENT IF EXISTS cleanup_old_logs;
DROP EVENT IF EXISTS generate_reports;

DROP SEQUENCE IF EXISTS order_number_seq;
DROP SEQUENCE IF EXISTS customer_id_seq;

-- =============================================================================
-- TABLES (Mix of modified, missing, and additional tables)
-- =============================================================================

-- Categories table - MODIFIED: Different structure and constraints
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(150) NOT NULL UNIQUE, -- DIFF: Renamed from 'name', increased length. Safety: Rename won't be detected and column dropped.
    category_description TEXT,                  -- DIFF: Renamed from 'description'
    parent_category_id INT,                     -- DIFF: Renamed from 'parent_id'
    status ENUM('Active', 'Inactive') DEFAULT 'Active', -- DIFF: Changed from is_active boolean
    sort_order INT DEFAULT 0,                  -- DIFF: New column
    image_url VARCHAR(500),                    -- DIFF: New column
    seo_title VARCHAR(255),                    -- DIFF: New column
    seo_description TEXT,                      -- DIFF: New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_parent_category_id (parent_category_id), -- DIFF: Renamed index
    INDEX idx_status (status),                         -- DIFF: Different column
    INDEX idx_sort_order (sort_order),                 -- DIFF: New index
    FOREIGN KEY (parent_category_id) REFERENCES categories(category_id) ON DELETE CASCADE -- DIFF: CASCADE instead of SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Product categories with SEO support'; -- DIFF: Different collation and comment

-- Users table - MODIFIED: Different columns and constraints
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(30) NOT NULL UNIQUE,      -- DIFF: Reduced length from 50 to 30
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    date_of_birth DATE,
    gender ENUM('Male', 'Female', 'Other', 'Non-Binary') DEFAULT 'Other', -- DIFF: Added extra value to be superset
    status ENUM('Active', 'Inactive', 'Suspended') DEFAULT 'Active', -- DIFF: Removed 'Pending'
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,     -- DIFF: New column
    last_login TIMESTAMP NULL,
    failed_login_attempts INT DEFAULT 0,
    account_locked_until TIMESTAMP NULL,
    registration_ip VARCHAR(45),              -- DIFF: New column
    email_preferences JSON,                   -- DIFF: New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_last_login (last_login),
    INDEX idx_phone_verified (phone_verified), -- DIFF: New index
    UNIQUE KEY uk_email (email)                -- DIFF: Removed username from unique constraint
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User account management with enhanced verification';

-- User profiles - MODIFIED: Different structure
CREATE TABLE user_profiles (
    profile_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    avatar_url VARCHAR(500),
    bio TEXT,
    website VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    currency VARCHAR(3) DEFAULT 'USD',
    notification_preferences JSON,
    privacy_settings JSON,
    membership_type ENUM('Basic', 'Premium', 'VIP') DEFAULT 'Basic', -- DIFF: Different enum values
    membership_expires DATETIME NULL,          -- DIFF: Renamed from subscription_expires
    lifetime_value DECIMAL(12,2) DEFAULT 0.00, -- DIFF: Renamed from total_purchases
    reward_points INT DEFAULT 0,               -- DIFF: Renamed from loyalty_points
    referral_code VARCHAR(20) UNIQUE,
    date_of_last_purchase DATETIME NULL,       -- DIFF: New column
    preferred_payment_method VARCHAR(50),      -- DIFF: New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_membership_type (membership_type), -- DIFF: Renamed index
    INDEX idx_referral_code (referral_code),
    INDEX idx_lifetime_value (lifetime_value)    -- DIFF: New index
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Extended user profile with membership tracking';

-- Products table - MODIFIED: Significant changes
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(300) NOT NULL,        -- DIFF: Renamed from 'name', increased length
    description TEXT,
    short_description VARCHAR(500),
    category_id INT,
    brand VARCHAR(100),
    model VARCHAR(100),
    weight DECIMAL(8,3),
    dimensions JSON,
    base_price DECIMAL(10,2) NOT NULL,         -- DIFF: Renamed from 'price'
    sale_price DECIMAL(10,2),                  -- DIFF: New column
    cost DECIMAL(10,2),
    margin_percentage DECIMAL(5,2),            -- DIFF: New column
    tax_class VARCHAR(50) DEFAULT 'standard',
    product_status ENUM('Draft', 'Active', 'Inactive', 'Discontinued', 'Coming_Soon') DEFAULT 'Draft', -- DIFF: Added 'Coming_Soon'
    is_digital BOOLEAN DEFAULT FALSE,
    requires_shipping BOOLEAN DEFAULT TRUE,
    stock_quantity INT DEFAULT 0,
    low_stock_threshold INT DEFAULT 10,
    manage_stock BOOLEAN DEFAULT TRUE,
    allow_backorders BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,         -- DIFF: Renamed from 'featured'
    downloadable_files JSON,
    product_tags VARCHAR(1000),                -- DIFF: New column
    meta_title VARCHAR(255),
    meta_description TEXT,
    meta_keywords VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL,
    INDEX idx_sku (sku),
    INDEX idx_category (category_id),
    INDEX idx_product_status (product_status),  -- DIFF: Renamed index
    INDEX idx_is_featured (is_featured),        -- DIFF: Renamed index
    INDEX idx_brand_model (brand, model),
    INDEX idx_price_range (base_price, sale_price), -- DIFF: New index
    FULLTEXT KEY ft_search (product_name, description, short_description, product_tags) -- DIFF: Added product_tags
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Product catalog with enhanced pricing and tagging';

-- Product reviews - MODIFIED: Enhanced review system
CREATE TABLE product_reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    user_id INT NOT NULL,
    overall_rating TINYINT NOT NULL CHECK (overall_rating BETWEEN 1 AND 5), -- DIFF: Renamed from 'rating'
    quality_rating TINYINT CHECK (quality_rating BETWEEN 1 AND 5),         -- DIFF: New column
    value_rating TINYINT CHECK (value_rating BETWEEN 1 AND 5),             -- DIFF: New column
    title VARCHAR(255),
    review_text TEXT,
    pros TEXT,                                  -- DIFF: New column
    cons TEXT,                                  -- DIFF: New column
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_votes INT DEFAULT 0,
    total_votes INT DEFAULT 0,
    review_status ENUM('Pending', 'Approved', 'Rejected', 'Spam', 'Flagged') DEFAULT 'Pending', -- DIFF: Added 'Flagged'
    moderator_notes TEXT,                       -- DIFF: Renamed from 'admin_notes'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_product_id (product_id),
    INDEX idx_user_id (user_id),
    INDEX idx_overall_rating (overall_rating),  -- DIFF: Renamed index
    INDEX idx_review_status (review_status),    -- DIFF: Renamed index
    INDEX idx_created_at (created_at),
    INDEX idx_helpful_votes (helpful_votes),    -- DIFF: New index
    UNIQUE KEY uk_user_product (user_id, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Enhanced product reviews with multiple rating dimensions';

-- Orders table - MODIFIED: Enhanced order management
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    order_status ENUM('Pending', 'Confirmed', 'Processing', 'Shipped', 'Delivered', 'Cancelled', 'Refunded', 'Returned') DEFAULT 'Pending', -- DIFF: Added Confirmed/Returned
    payment_status ENUM('Pending', 'Paid', 'Failed', 'Refunded', 'Partially_Refunded', 'Authorized') DEFAULT 'Pending', -- DIFF: Compatible superset with extra 'Authorized'
    currency VARCHAR(3) DEFAULT 'USD',
    subtotal DECIMAL(12,2) NOT NULL,
    tax_amount DECIMAL(12,2) DEFAULT 0.00,
    shipping_amount DECIMAL(12,2) DEFAULT 0.00,
    discount_amount DECIMAL(12,2) DEFAULT 0.00,
    handling_fee DECIMAL(10,2) DEFAULT 0.00,   -- DIFF: New column
    total_amount DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(50),
    payment_reference VARCHAR(255),
    transaction_id VARCHAR(255),               -- DIFF: New column
    billing_address JSON,
    shipping_address JSON,
    shipping_method VARCHAR(100),
    tracking_number VARCHAR(100),
    estimated_delivery DATE,                   -- DIFF: New column
    notes TEXT,
    internal_notes TEXT,
    coupon_code VARCHAR(50),
    referral_source VARCHAR(100),
    source_campaign VARCHAR(100),              -- DIFF: New column
    ip_address VARCHAR(45),
    user_agent TEXT,
    confirmed_at TIMESTAMP NULL,               -- DIFF: New column
    shipped_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    INDEX idx_order_number (order_number),
    INDEX idx_user_id (user_id),
    INDEX idx_order_status (order_status),      -- DIFF: Renamed index
    INDEX idx_payment_status (payment_status),
    INDEX idx_created_at (created_at),
    INDEX idx_total_amount (total_amount),
    INDEX idx_tracking_number (tracking_number), -- DIFF: New index
    INDEX idx_confirmed_at (confirmed_at)        -- DIFF: New index
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Enhanced order management with detailed tracking';

-- Order items - MODIFIED: Enhanced item tracking
CREATE TABLE order_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    product_sku VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    product_variant VARCHAR(255),              -- DIFF: New column
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(12,2) NOT NULL,
    product_options JSON,
    tax_amount DECIMAL(10,2) DEFAULT 0.00,
    discount_amount DECIMAL(10,2) DEFAULT 0.00,
    commission_rate DECIMAL(5,4) DEFAULT 0.0000, -- DIFF: New column
    commission_amount DECIMAL(10,2) DEFAULT 0.00, -- DIFF: New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id),
    INDEX idx_product_sku (product_sku),
    INDEX idx_commission_rate (commission_rate) -- DIFF: New index
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Order items with commission tracking';

-- System config - MODIFIED: Enhanced configuration
CREATE TABLE system_config (
    config_id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    config_type ENUM('string', 'number', 'boolean', 'json', 'encrypted') DEFAULT 'string', -- DIFF: Compatible superset with extra 'encrypted'
    config_category VARCHAR(50) DEFAULT 'general', -- DIFF: New column
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    requires_restart BOOLEAN DEFAULT FALSE,    -- DIFF: New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key),
    INDEX idx_is_public (is_public),
    INDEX idx_config_category (config_category) -- DIFF: New index
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Enhanced system configuration with categories';

-- Audit log - MODIFIED: Enhanced logging
CREATE TABLE audit_log (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    session_id VARCHAR(255),                   -- DIFF: New column
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    record_id VARCHAR(100),
    old_values JSON,
    new_values JSON,
    severity ENUM('Info', 'Warning', 'Error', 'Critical') DEFAULT 'Info', -- DIFF: New column
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_url VARCHAR(1000),                 -- DIFF: New column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_table_name (table_name),
    INDEX idx_created_at (created_at),
    INDEX idx_severity (severity),             -- DIFF: New index
    INDEX idx_session_id (session_id),        -- DIFF: New index
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Enhanced audit trail with session tracking';

-- Payment methods - MISSING: This table doesn't exist in destination
-- Shipping addresses - MISSING: This table doesn't exist in destination

-- NEW TABLES: These don't exist in source
CREATE TABLE customer_analytics (
    analytics_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(12,2) DEFAULT 0.00,
    average_order_value DECIMAL(10,2) DEFAULT 0.00,
    first_order_date DATE,
    last_order_date DATE,
    favorite_category_id INT,
    preferred_payment_method VARCHAR(50),
    customer_segment ENUM('New', 'Regular', 'VIP', 'Churned') DEFAULT 'New',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (favorite_category_id) REFERENCES categories(category_id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_customer_segment (customer_segment),
    INDEX idx_total_spent (total_spent)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Customer analytics and segmentation';

CREATE TABLE promotional_campaigns (
    campaign_id INT AUTO_INCREMENT PRIMARY KEY,
    campaign_name VARCHAR(255) NOT NULL,
    campaign_type ENUM('Discount', 'BOGO', 'Free_Shipping', 'Cashback') NOT NULL,
    discount_percentage DECIMAL(5,2),
    discount_amount DECIMAL(10,2),
    minimum_order_amount DECIMAL(10,2),
    maximum_discount DECIMAL(10,2),
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    usage_limit INT,
    current_usage INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_campaign_type (campaign_type),
    INDEX idx_start_end_date (start_date, end_date),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Marketing campaigns and promotions';

CREATE TABLE order_tracking (
    tracking_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    status_update VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    tracking_details TEXT,
    estimated_delivery DATETIME,
    actual_delivery DATETIME,
    carrier VARCHAR(100),
    tracking_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    INDEX idx_order_id (order_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Detailed order tracking information';

-- =============================================================================
-- SEQUENCES (Different from source)
-- =============================================================================

CREATE SEQUENCE order_number_seq 
    START WITH 200000          -- DIFF: Different start value
    INCREMENT BY 1 
    MINVALUE 200000           -- DIFF: Different minimum
    MAXVALUE 999999999 
    CACHE 50                  -- DIFF: Different cache size
    CYCLE;

-- DIFF: Different sequence
CREATE SEQUENCE customer_id_seq 
    START WITH 10000 
    INCREMENT BY 1 
    MINVALUE 10000 
    MAXVALUE 9999999999 
    CACHE 25 
    NOCYCLE;

-- invoice_number_seq - MISSING: This sequence doesn't exist in destination

-- =============================================================================
-- VIEWS (Different views from source)
-- =============================================================================

-- Customer summary - MISSING: This view doesn't exist in destination
-- Product analytics - MISSING: This view doesn't exist in destination

-- NEW VIEWS: These don't exist in source
CREATE VIEW sales_dashboard AS
SELECT 
    DATE(o.created_at) AS sale_date,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.user_id) AS unique_customers,
    SUM(o.total_amount) AS daily_revenue,
    AVG(o.total_amount) AS avg_order_value,
    SUM(oi.quantity) AS total_items_sold,
    COUNT(CASE WHEN o.order_status = 'Delivered' THEN 1 END) AS delivered_orders,
    COUNT(CASE WHEN o.order_status = 'Cancelled' THEN 1 END) AS cancelled_orders
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY DATE(o.created_at)
ORDER BY sale_date DESC;

CREATE VIEW inventory_report AS
SELECT 
    p.product_id,
    p.sku,
    p.product_name,
    p.brand,
    c.category_name,
    p.base_price,
    p.sale_price,
    p.stock_quantity,
    p.low_stock_threshold,
    p.product_status,
    CASE 
        WHEN p.stock_quantity <= 0 THEN 'Out of Stock'
        WHEN p.stock_quantity <= p.low_stock_threshold THEN 'Low Stock'
        ELSE 'In Stock'
    END AS stock_status,
    COALESCE(SUM(oi.quantity), 0) AS total_sold_last_30_days
FROM products p
LEFT JOIN categories c ON p.category_id = c.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id 
    AND o.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    AND o.order_status NOT IN ('Cancelled', 'Refunded')
GROUP BY p.product_id, p.sku, p.product_name, p.brand, c.category_name, 
         p.base_price, p.sale_price, p.stock_quantity, p.low_stock_threshold, p.product_status;

-- =============================================================================
-- STORED PROCEDURES (Different procedures)
-- =============================================================================
DELIMITER $$

-- Procedure to process a new order
CREATE PROCEDURE process_order(
    IN p_user_id INT,
    IN p_order_data JSON,
    OUT p_order_id INT,
    OUT p_result_message VARCHAR(255)
)
BEGIN
    DECLARE v_order_number VARCHAR(50);
    DECLARE v_total_amount DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_error_count INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_result_message = 'Error processing order: Database error occurred!!';
        SET p_order_id = 0;
    END;

    START TRANSACTION;

    -- Generate order number
    SET v_order_number = CONCAT('ORD-', NEXTVAL(order_number_seq));

    -- Validate user exists and is active
    SELECT COUNT(*) INTO v_error_count
    FROM users
    WHERE user_id = p_user_id AND status = 'Active';

    IF v_error_count = 0 THEN
        SET p_result_message = 'Error: User not found or inactive';
        SET p_order_id = 0;
        ROLLBACK;
    ELSE
        -- Extract total amount from JSON
        SET v_total_amount = JSON_UNQUOTE(JSON_EXTRACT(p_order_data, '$.total_amount'));

        -- Create order
        INSERT INTO orders (
            order_number, user_id, status, payment_status,
            currency, subtotal, tax_amount, shipping_amount,
            total_amount, billing_address, shipping_address
        ) VALUES (
            v_order_number, p_user_id, 'Pending', 'Pending',
            'USD', v_total_amount, 0.00, 0.00,
            v_total_amount,
            JSON_EXTRACT(p_order_data, '$.billing_address'),
            JSON_EXTRACT(p_order_data, '$.shipping_address')
        );

        SET p_order_id = LAST_INSERT_ID();
        SET p_result_message = CONCAT('Order created successfully: ', v_order_number);

        COMMIT;
    END IF;
END$$


-- Process order - MISSING: This procedure doesn't exist in destination
-- Update inventory - MISSING: This procedure doesn't exist in destination

-- NEW PROCEDURES: These don't exist in source
CREATE PROCEDURE send_notification(
    IN p_user_id INT,
    IN p_notification_type VARCHAR(50),
    IN p_message TEXT,
    OUT p_result_message VARCHAR(255)
)
BEGIN
    DECLARE v_email VARCHAR(255);
    DECLARE v_preferences JSON;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET p_result_message = 'Error sending notification: Database error occurred';
    END;

    -- Get user email and preferences
    SELECT u.email, up.notification_preferences
    INTO v_email, v_preferences
    FROM users u
    LEFT JOIN user_profiles up ON u.user_id = up.user_id
    WHERE u.user_id = p_user_id;
    
    -- Log notification attempt
    INSERT INTO audit_log (user_id, action, new_values)
    VALUES (p_user_id, 'NOTIFICATION_SENT', 
            JSON_OBJECT('type', p_notification_type, 'message', p_message));
    
    SET p_result_message = CONCAT('Notification sent to: ', v_email);
END$$

CREATE PROCEDURE backup_data(
    IN p_table_name VARCHAR(100),
    IN p_backup_type ENUM('FULL', 'INCREMENTAL'),
    OUT p_result_message VARCHAR(255)
)
BEGIN
    DECLARE v_record_count INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET p_result_message = 'Error during backup: Database error occurred';
    END;
    
    -- This is a simplified backup procedure
    CASE p_table_name
        WHEN 'orders' THEN
            SELECT COUNT(*) INTO v_record_count FROM orders;
        WHEN 'users' THEN
            SELECT COUNT(*) INTO v_record_count FROM users;
        WHEN 'products' THEN
            SELECT COUNT(*) INTO v_record_count FROM products;
        ELSE
            SET v_record_count = 0;
    END CASE;
    
    -- Log backup operation
    INSERT INTO audit_log (action, table_name, new_values)
    VALUES ('BACKUP_COMPLETED', p_table_name, 
            JSON_OBJECT('type', p_backup_type, 'record_count', v_record_count));
    
    SET p_result_message = CONCAT('Backup completed for ', p_table_name, ': ', v_record_count, ' records');
END$$

DELIMITER ;

-- =============================================================================
-- FUNCTIONS (Different functions)
-- =============================================================================

DELIMITER $$

-- Calculate discount - MISSING: This function doesn't exist in destination
-- Format currency - MISSING: This function doesn't exist in destination

-- NEW FUNCTIONS: These don't exist in source
CREATE FUNCTION generate_slug(p_text VARCHAR(255))
RETURNS VARCHAR(255)
NO SQL
DETERMINISTIC
BEGIN
    DECLARE v_slug VARCHAR(255);
    
    -- Convert to lowercase and replace spaces/special chars with hyphens
    SET v_slug = LOWER(p_text);
    SET v_slug = REGEXP_REPLACE(v_slug, '[^a-z0-9]+', '-');
    SET v_slug = TRIM(BOTH '-' FROM v_slug);
    
    RETURN v_slug;
END$$

CREATE FUNCTION calculate_commission(
    p_product_id INT,
    p_sale_amount DECIMAL(12,2)
)
RETURNS DECIMAL(10,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_commission_rate DECIMAL(5,4) DEFAULT 0.0500; -- 5% default
    DECLARE v_commission_amount DECIMAL(10,2);
    DECLARE v_category_id INT;
    
    -- Get product category
    SELECT category_id INTO v_category_id
    FROM products 
    WHERE product_id = p_product_id;
    
    -- Set commission rates based on category
    CASE v_category_id
        WHEN 1 THEN SET v_commission_rate = 0.0300; -- Electronics: 3%
        WHEN 2 THEN SET v_commission_rate = 0.0250; -- Computers: 2.5%
        WHEN 3 THEN SET v_commission_rate = 0.0400; -- Mobile: 4%
        WHEN 4 THEN SET v_commission_rate = 0.0600; -- Home & Garden: 6%
        WHEN 6 THEN SET v_commission_rate = 0.0800; -- Books: 8%
        ELSE SET v_commission_rate = 0.0500;        -- Default: 5%
    END CASE;
    
    SET v_commission_amount = p_sale_amount * v_commission_rate;
    
    RETURN v_commission_amount;
END$$

DELIMITER ;

-- =============================================================================
-- TRIGGERS (Different triggers)
-- =============================================================================

DELIMITER $$

-- Users audit trigger - MISSING: This trigger doesn't exist in destination

-- NEW TRIGGERS: These don't exist in source
CREATE TRIGGER product_price_trigger
BEFORE UPDATE ON products
FOR EACH ROW
BEGIN
    -- Log price changes
    IF OLD.base_price != NEW.base_price OR OLD.sale_price != NEW.sale_price THEN
        INSERT INTO audit_log (action, table_name, record_id, old_values, new_values)
        VALUES ('PRICE_CHANGE', 'products', NEW.product_id,
                JSON_OBJECT('base_price', OLD.base_price, 'sale_price', OLD.sale_price),
                JSON_OBJECT('base_price', NEW.base_price, 'sale_price', NEW.sale_price));
    END IF;
    
    -- Calculate margin percentage
    IF NEW.cost > 0 THEN
        SET NEW.margin_percentage = ((NEW.base_price - NEW.cost) / NEW.base_price) * 100;
    END IF;
END$$

CREATE TRIGGER order_notification_trigger
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    IF OLD.order_status != NEW.order_status THEN
        -- Log status change
        INSERT INTO audit_log (user_id, action, table_name, record_id, old_values, new_values)
        VALUES (NEW.user_id, 'ORDER_STATUS_CHANGE', 'orders', NEW.order_id,
                JSON_OBJECT('status', OLD.order_status),
                JSON_OBJECT('status', NEW.order_status));
        
        -- Insert tracking update
        INSERT INTO order_tracking (order_id, status_update, created_at)
        VALUES (NEW.order_id, CONCAT('Order status changed to: ', NEW.order_status), CURRENT_TIMESTAMP);
    END IF;
END$$

DELIMITER ;

-- =============================================================================
-- EVENTS (Different events)
-- =============================================================================

DELIMITER $$

-- Cleanup old logs - MISSING: This event doesn't exist in destination

-- NEW EVENT: This doesn't exist in source
CREATE EVENT generate_reports
ON SCHEDULE EVERY 1 WEEK
STARTS (CURRENT_DATE + INTERVAL 1 DAY)
DO
BEGIN
    -- Update customer analytics
    INSERT INTO customer_analytics (
        user_id, total_orders, total_spent, average_order_value, 
        first_order_date, last_order_date, customer_segment
    )
    SELECT 
        u.user_id,
        COALESCE(COUNT(o.order_id), 0),
        COALESCE(SUM(o.total_amount), 0),
        COALESCE(AVG(o.total_amount), 0),
        MIN(o.created_at),
        MAX(o.created_at),
        CASE 
            WHEN COUNT(o.order_id) = 0 THEN 'New'
            WHEN COUNT(o.order_id) = 1 THEN 'Regular'
            WHEN SUM(o.total_amount) > 1000 THEN 'VIP'
            WHEN MAX(o.created_at) < DATE_SUB(CURRENT_DATE, INTERVAL 6 MONTH) THEN 'Churned'
            ELSE 'Regular'
        END
    FROM users u
    LEFT JOIN orders o ON u.user_id = o.user_id 
        AND o.order_status NOT IN ('Cancelled', 'Refunded')
    GROUP BY u.user_id
    ON DUPLICATE KEY UPDATE
        total_orders = VALUES(total_orders),
        total_spent = VALUES(total_spent),
        average_order_value = VALUES(average_order_value),
        last_order_date = VALUES(last_order_date),
        customer_segment = VALUES(customer_segment);
    
    -- Log report generation
    INSERT INTO audit_log (action, new_values)
    VALUES ('WEEKLY_REPORTS_GENERATED', 
            JSON_OBJECT('generation_date', CURRENT_DATE));
END$$

DELIMITER ;

-- =============================================================================
-- SAMPLE DATA INSERTION (Different from source)
-- =============================================================================

-- Insert sample categories with different data
INSERT INTO categories (category_name, category_description, parent_category_id, status, sort_order) VALUES
('Electronics & Tech', 'Electronic devices and technology products', NULL, 'Active', 1),
('Computer Hardware', 'Desktop and laptop computers', 1, 'Active', 2),
('Mobile & Tablets', 'Smartphones, tablets, and mobile accessories', 1, 'Active', 3),
('Home Improvement', 'Tools and supplies for home improvement', NULL, 'Active', 4),
('Outdoor Furniture', 'Patio and garden furniture', 4, 'Active', 5),
('Literature', 'Books and reading materials', NULL, 'Active', 6),
('Science Fiction', 'Sci-fi novels and stories', 6, 'Active', 7),
('Technical Manuals', 'Technical and educational books', 6, 'Active', 8),
('Gaming', 'Video games and gaming accessories', 1, 'Active', 9);

-- Now add the 'name' column with unique values to prepare for migration
-- This ensures no duplicate entries when UNIQUE constraint is added
ALTER TABLE categories ADD COLUMN name VARCHAR(100);
UPDATE categories SET name = CASE category_id
    WHEN 1 THEN 'Electronics'
    WHEN 2 THEN 'Computers'  
    WHEN 3 THEN 'Mobile'
    WHEN 4 THEN 'Home'
    WHEN 5 THEN 'Furniture'
    WHEN 6 THEN 'Books'
    WHEN 7 THEN 'SciFi'
    WHEN 8 THEN 'Manuals'
    WHEN 9 THEN 'Games'
    ELSE CONCAT('Category_', category_id)
END;

-- Insert sample users with different data
INSERT INTO users (username, email, password_hash, first_name, last_name, phone, date_of_birth, gender, status, email_verified, phone_verified) VALUES
('john_doe_2024', 'john.doe.new@example.com', '$2y$10$newhash1', 'John', 'Doe', '+1-555-1001', '1985-03-15', 'Male', 'Active', TRUE, TRUE),
('jane_s', 'jane.smith.updated@example.com', '$2y$10$newhash2', 'Jane', 'Smith', '+1-555-1002', '1990-07-22', 'Female', 'Active', TRUE, FALSE),
('robert_wilson', 'robert.wilson@example.com', '$2y$10$newhash3', 'Robert', 'Wilson', '+1-555-1003', '1982-11-08', 'Male', 'Active', TRUE, TRUE),
('alice_j_new', 'alice.johnson.new@example.com', '$2y$10$newhash4', 'Alice', 'Johnson', '+1-555-1004', '1995-01-30', 'Female', 'Active', TRUE, FALSE),
('charlie_davis', 'charlie.davis@example.com', '$2y$10$newhash5', 'Charlie', 'Davis', '+1-555-1005', '1978-09-12', 'Male', 'Suspended', FALSE, FALSE),
('sarah_miller', 'sarah.miller@example.com', '$2y$10$newhash6', 'Sarah', 'Miller', '+1-555-1006', '1992-05-18', 'Female', 'Active', TRUE, TRUE);

-- Insert user profiles with different structure
INSERT INTO user_profiles (user_id, bio, timezone, language, currency, membership_type, lifetime_value, reward_points, referral_code) VALUES
(1, 'Technology professional and gadget enthusiast', 'America/New_York', 'en', 'USD', 'VIP', 1850.25, 1850, 'NEWREF001'),
(2, 'Interior designer and book collector', 'America/Los_Angeles', 'en', 'USD', 'Basic', 325.75, 326, 'NEWREF002'),
(3, 'Outdoor adventure guide', 'America/Denver', 'en', 'USD', 'Premium', 1275.50, 1276, 'NEWREF003'),
(4, 'Graduate student in computer science', 'Europe/London', 'en', 'GBP', 'Basic', 125.00, 125, 'NEWREF004'),
(5, 'Retired engineer', 'America/Phoenix', 'en', 'USD', 'Premium', 450.00, 450, 'NEWREF005'),
(6, 'Marketing specialist', 'America/Miami', 'en', 'USD', 'VIP', 2100.75, 2101, 'NEWREF006');

-- Insert sample products with different structure
INSERT INTO products (sku, product_name, description, category_id, brand, base_price, sale_price, cost, product_status, stock_quantity, is_featured, product_tags) VALUES
('NEWLAPTOP001', 'Ultra Performance Gaming Laptop', 'High-end gaming laptop with RTX graphics and 32GB RAM', 2, 'GameTech', 1899.99, 1699.99, 1200.00, 'Active', 8, TRUE, 'gaming,laptop,high-performance,RTX'),
('NEWPHONE001', 'Smartphone Elite Edition', 'Premium smartphone with AI camera and 5G', 3, 'PhoneMax', 1199.99, 999.99, 650.00, 'Active', 15, TRUE, 'smartphone,5G,AI,camera,premium'),
('NEWBOOK001', 'Advanced Programming Techniques', 'Comprehensive guide to modern software development', 8, 'DevBooks', 79.99, NULL, 35.00, 'Active', 50, FALSE, 'programming,software,development,advanced'),
('NEWCHAIR001', 'Executive Leather Office Chair', 'Premium leather office chair with massage function', 5, 'LuxuryOffice', 599.99, 499.99, 250.00, 'Active', 5, TRUE, 'office,chair,leather,massage,executive'),
('NEWTABLET001', 'Creative Pro Tablet', 'Professional drawing tablet with pressure sensitivity', 3, 'ArtTech', 899.99, NULL, 450.00, 'Active', 12, FALSE, 'tablet,drawing,creative,professional,art'),
('NEWGAME001', 'Adventure Quest VR Game', 'Virtual reality adventure game', 9, 'VRStudios', 59.99, 39.99, 20.00, 'Coming_Soon', 0, TRUE, 'VR,game,adventure,virtual-reality');

-- Insert sample system configuration with different structure
INSERT INTO system_config (config_key, config_value, config_type, config_category, description, is_public, requires_restart) VALUES
('store_name', 'Premium E-Commerce Hub', 'string', 'general', 'The name of the online store', TRUE, FALSE),
('default_currency', 'USD', 'string', 'financial', 'Default currency for the store', TRUE, FALSE),
('enable_tax_calculation', 'true', 'boolean', 'financial', 'Whether tax calculation is enabled', FALSE, TRUE),
('free_shipping_minimum', '75.00', 'number', 'shipping', 'Minimum order amount for free shipping', TRUE, FALSE),
('max_failed_logins', '3', 'number', 'security', 'Maximum failed login attempts before account lock', FALSE, TRUE),
('enable_reviews', 'true', 'boolean', 'features', 'Whether product reviews are enabled', TRUE, FALSE),
('commission_rate_default', '0.05', 'number', 'financial', 'Default commission rate for affiliates', FALSE, FALSE);

-- Insert promotional campaigns
INSERT INTO promotional_campaigns (campaign_name, campaign_type, discount_percentage, start_date, end_date, is_active, usage_limit) VALUES
('Summer Sale 2025', 'Discount', 20.00, '2025-06-01 00:00:00', '2025-08-31 23:59:59', TRUE, 1000),
('Holiday Special', 'Free_Shipping', NULL, '2025-11-15 00:00:00', '2025-12-31 23:59:59', TRUE, NULL),
('New Customer Welcome', 'Discount', 15.00, '2025-01-01 00:00:00', '2025-12-31 23:59:59', TRUE, 5000);

-- =============================================================================
-- SUMMARY OF DIFFERENCES FROM SOURCE
-- =============================================================================

-- TABLES:
-- 1. categories - Column renames, constraint changes, new columns, different collation
-- 2. users - Column changes, enum modifications, new columns, different constraints
-- 3. user_profiles - Column renames, enum changes, new columns, different indexes
-- 4. products - Column renames, new columns, index changes, different constraints
-- 5. product_reviews - Column renames, new rating columns, enhanced status enum
-- 6. orders - Status enum changes, new columns, enhanced tracking
-- 7. order_items - New commission columns, enhanced tracking
-- 8. system_config - New columns, enhanced categorization
-- 9. audit_log - New columns, enhanced logging capabilities
-- 10. payment_methods - MISSING (doesn't exist in destination)
-- 11. shipping_addresses - MISSING (doesn't exist in destination)
-- 12. customer_analytics - NEW (doesn't exist in source)
-- 13. promotional_campaigns - NEW (doesn't exist in source)
-- 14. order_tracking - NEW (doesn't exist in source)

-- SEQUENCES:
-- 1. order_number_seq - Different start value, cache size
-- 2. invoice_number_seq - MISSING (doesn't exist in destination)
-- 3. customer_id_seq - NEW (doesn't exist in source)

-- VIEWS:
-- 1. customer_summary - MISSING (doesn't exist in destination)
-- 2. product_analytics - MISSING (doesn't exist in destination)
-- 3. order_statistics - MISSING (doesn't exist in destination)
-- 4. revenue_report - MISSING (doesn't exist in destination)
-- 5. sales_dashboard - NEW (doesn't exist in source)
-- 6. inventory_report - NEW (doesn't exist in source)

-- PROCEDURES:
-- 1. process_order - MISSING (doesn't exist in destination)
-- 2. update_inventory - MISSING (doesn't exist in destination)
-- 3. calculate_shipping - MISSING (doesn't exist in destination)
-- 4. generate_report - MISSING (doesn't exist in destination)
-- 5. send_notification - NEW (doesn't exist in source)
-- 6. backup_data - NEW (doesn't exist in source)

-- FUNCTIONS:
-- 1. calculate_discount - MISSING (doesn't exist in destination)
-- 2. format_currency - MISSING (doesn't exist in destination)
-- 3. validate_email - MISSING (doesn't exist in source)
-- 4. get_tax_rate - MISSING (doesn't exist in source)
-- 5. generate_slug - NEW (doesn't exist in source)
-- 6. calculate_commission - NEW (doesn't exist in source)

-- TRIGGERS:
-- 1. users_audit_trigger - MISSING (doesn't exist in destination)
-- 2. inventory_update_trigger - MISSING (doesn't exist in destination)
-- 3. order_status_trigger - MISSING (doesn't exist in destination)
-- 4. product_price_trigger - NEW (doesn't exist in source)
-- 5. order_notification_trigger - NEW (doesn't exist in source)

-- EVENTS:
-- 1. cleanup_old_logs - MISSING (doesn't exist in destination)
-- 2. update_statistics - MISSING (doesn't exist in destination)
-- 3. generate_reports - NEW (doesn't exist in source)

-- EXPECTED TOTAL DIFFERENCES: 35+ operations covering:
-- - Table modifications (structure, constraints, indexes)
-- - Missing tables/objects (to be created)
-- - New tables/objects (to be dropped)
-- - Column additions, removals, modifications
-- - Index and constraint changes
-- - Complete object replacements

-- This comprehensive test data should generate 30+ DDL operations
-- for thorough testing of the DDL Wizard's capabilities.
