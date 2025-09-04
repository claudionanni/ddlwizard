-- DDL Wizard Migration Script
-- Source Schema: ddlwizard_source_test
-- Destination Schema: ddlwizard_dest_test
-- Generated: 2025-09-04T14:28:23.597294

-- WARNING: Review this script carefully before executing!
-- This script will modify the destination database structure.

SET FOREIGN_KEY_CHECKS = 0;

-- TABLES CHANGES
--------------------------------------------------
-- Drop table: stock_alerts
DROP TABLE IF EXISTS `ddlwizard_dest_test`.`stock_alerts`;

-- Drop table: product_reviews
DROP TABLE IF EXISTS `ddlwizard_dest_test`.`product_reviews`;

-- Modify table: categories
-- Table 'categories' differences:
--   1. Column REMOVED: sort_order
--   2. Column REMOVED: is_active
--   3. Index REMOVED: idx_sort
ALTER TABLE `categories` DROP INDEX IF EXISTS `idx_sort`;
ALTER TABLE `categories` DROP COLUMN IF EXISTS `sort_order`;
ALTER TABLE `categories` DROP COLUMN IF EXISTS `is_active`;

-- Modify table: products
-- Table 'products' differences:
--   1. Column REMOVED: weight
--   2. Column REMOVED: min_stock_level
--   3. Column REMOVED: sale_price
--   4. Column REMOVED: is_featured
--   5. Column REMOVED: dimensions
--   6. Column MODIFIED: name
--       FROM: varchar(100) NOT NULL
--       TO:   varchar(150) NOT NULL
--   7. Index REMOVED: idx_featured
ALTER TABLE `products` DROP INDEX IF EXISTS `idx_featured`;
ALTER TABLE `products` MODIFY COLUMN `name` varchar(150) NOT NULL;
ALTER TABLE `products` DROP COLUMN IF EXISTS `weight`;
ALTER TABLE `products` DROP COLUMN IF EXISTS `min_stock_level`;
ALTER TABLE `products` DROP COLUMN IF EXISTS `sale_price`;
ALTER TABLE `products` DROP COLUMN IF EXISTS `is_featured`;
ALTER TABLE `products` DROP COLUMN IF EXISTS `dimensions`;

-- Modify table: order_items
-- Table 'order_items' differences:
--   1. Column REMOVED: discount_amount
--   2. Column MODIFIED: total_price
--       FROM: decimal(12,2) GENERATED ALWAYS AS (`quantity` * `unit_price`) STORED
--       TO:   decimal(12,2) GENERATED ALWAYS AS (`quantity` * `unit_price` - `discount_amount`) STORED
ALTER TABLE `order_items` MODIFY COLUMN `total_price` decimal(12,2) GENERATED ALWAYS AS (`quantity` * `unit_price` ) STORED;
ALTER TABLE `order_items` DROP COLUMN IF EXISTS `discount_amount`;

-- Modify table: orders
-- Table 'orders' differences:
--   1. Column REMOVED: discount_amount
--   2. Column REMOVED: tracking_number
--   3. Column REMOVED: order_number
--   4. Column REMOVED: shipping_cost
--   5. Column REMOVED: tax_amount
--   6. Column MODIFIED: status
--       FROM: enum('pending','processing','shipped','delivered','cancelled') DEFAULT 'pending'
--       TO:   enum('pending','processing','shipped','delivered','cancelled','refunded') DEFAULT 'pending'
--   7. Index REMOVED: idx_order_number
--   8. Index REMOVED: order_number
ALTER TABLE `orders` DROP INDEX IF EXISTS `idx_order_number`;
ALTER TABLE `orders` DROP INDEX IF EXISTS `order_number`;
ALTER TABLE `orders` MODIFY COLUMN `status` enum('pending','processing','shipped','delivered','cancelled','refunded') DEFAULT 'pending';
ALTER TABLE `orders` DROP COLUMN IF EXISTS `discount_amount`;
ALTER TABLE `orders` DROP COLUMN IF EXISTS `tracking_number`;
ALTER TABLE `orders` DROP COLUMN IF EXISTS `order_number`;
ALTER TABLE `orders` DROP COLUMN IF EXISTS `shipping_cost`;
ALTER TABLE `orders` DROP COLUMN IF EXISTS `tax_amount`;

-- Modify table: users
-- Table 'users' differences:
--   1. Column REMOVED: full_name
--   2. Column REMOVED: phone
--   3. Index ADDED: idx_username
--   4. Index REMOVED: idx_phone
--   5. Index REMOVED: email
ALTER TABLE `users` DROP INDEX IF EXISTS `idx_phone`;
ALTER TABLE `users` DROP INDEX IF EXISTS `email`;
ALTER TABLE `users` DROP COLUMN IF EXISTS `full_name`;
ALTER TABLE `users` DROP COLUMN IF EXISTS `phone`;
ALTER TABLE `users` ADD KEY `idx_username` (`username`);


-- PROCEDURES CHANGES
--------------------------------------------------
-- Drop procedure: GetProductReviewSummary
DROP PROCEDURE IF EXISTS `ddlwizard_dest_test`.`GetProductReviewSummary`;

-- Update procedure: GetUserOrderHistory
DROP PROCEDURE IF EXISTS `ddlwizard_dest_test`.`GetUserOrderHistory`;
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` PROCEDURE `GetUserOrderHistory`(IN user_id_param INT)
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
END$$
DELIMITER ;


-- FUNCTIONS CHANGES
--------------------------------------------------
-- Drop function: GetProductAverageRating
DROP FUNCTION IF EXISTS `ddlwizard_dest_test`.`GetProductAverageRating`;

-- Update function: GetUserTotalSpent
DROP FUNCTION IF EXISTS `ddlwizard_dest_test`.`GetUserTotalSpent`;
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` FUNCTION `GetUserTotalSpent`(user_id_param INT) RETURNS decimal(12,2)
    READS SQL DATA
    DETERMINISTIC
BEGIN
    DECLARE total DECIMAL(12,2) DEFAULT 0.00;
    
    SELECT COALESCE(SUM(total_amount), 0.00) INTO total
    FROM orders 
    WHERE user_id = user_id_param AND status IN ('delivered', 'shipped');
    
    RETURN total;
END$$
DELIMITER ;


-- TRIGGERS CHANGES
--------------------------------------------------
-- Drop trigger: generate_order_number
DROP TRIGGER IF EXISTS `ddlwizard_dest_test`.`generate_order_number`;

-- Update trigger: update_stock_after_order
DROP TRIGGER IF EXISTS `ddlwizard_dest_test`.`update_stock_after_order`;
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` TRIGGER update_stock_after_order
    AFTER INSERT ON order_items
    FOR EACH ROW
BEGIN
    UPDATE products 
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE id = NEW.product_id;
END$$
DELIMITER ;


-- EVENTS CHANGES
--------------------------------------------------
-- Drop event: update_featured_products
DROP EVENT IF EXISTS `ddlwizard_dest_test`.`update_featured_products`;

-- Update event: cleanup_cancelled_orders
DROP EVENT IF EXISTS `ddlwizard_dest_test`.`cleanup_cancelled_orders`;
CREATE DEFINER=`sstuser`@`%` EVENT `cleanup_cancelled_orders` ON SCHEDULE EVERY 1 DAY STARTS '2025-09-04 14:27:13' ON COMPLETION NOT PRESERVE ENABLE DO DELETE FROM orders 
    WHERE status = 'cancelled' 
    AND order_date < DATE_SUB(NOW(), INTERVAL 30 DAY);


-- VIEWS CHANGES
--------------------------------------------------
-- Drop view: product_catalog
DROP VIEW IF EXISTS `ddlwizard_dest_test`.`product_catalog`;


-- SEQUENCES CHANGES
--------------------------------------------------
-- Drop sequence: test_seq
DROP SEQUENCE IF EXISTS `ddlwizard_dest_test`.`test_seq`;


SET FOREIGN_KEY_CHECKS = 1;

-- Migration script completed.