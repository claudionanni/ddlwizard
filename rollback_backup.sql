-- DDL Wizard Rollback Script
-- Source Schema: ddlwizard_dest_test
-- Destination Schema: ddlwizard_dest_test
-- Generated: 2025-09-04T20:20:20.785202

-- WARNING: Review this script carefully before executing!
-- This script will revert changes made by the migration script.

SET FOREIGN_KEY_CHECKS = 0;

-- Detailed rollback for all schema changes

-- Rollback table drop: product_reviews
CREATE TABLE `product_reviews` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `product_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `rating` int(11) NOT NULL CHECK (`rating` >= 1 and `rating` <= 5),
  `title` varchar(100) DEFAULT NULL,
  `review_text` text DEFAULT NULL,
  `is_verified_purchase` tinyint(1) DEFAULT 0,
  `helpful_votes` int(11) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_product_review` (`user_id`,`product_id`),
  KEY `idx_product` (`product_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_rating` (`rating`),
  CONSTRAINT `product_reviews_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `product_reviews_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci COMMENT='Product reviews and ratings';

-- Rollback table drop: stock_alerts
CREATE TABLE `stock_alerts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `product_id` int(11) NOT NULL,
  `alert_type` enum('LOW_STOCK','OUT_OF_STOCK') NOT NULL,
  `is_resolved` tinyint(1) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `resolved_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_product` (`product_id`),
  KEY `idx_type` (`alert_type`),
  KEY `idx_resolved` (`is_resolved`),
  CONSTRAINT `stock_alerts_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci COMMENT='Stock level alerts';

ALTER TABLE `order_items` ADD COLUMN `discount_amount` decimal(8,2) DEFAULT 0.00;
ALTER TABLE `order_items` MODIFY COLUMN `total_price` decimal(12,2) GENERATED ALWAYS AS (`quantity` * `unit_price` - `discount_amount`) STORED;
ALTER TABLE `order_items` COMMENT='Individual items within orders - enhanced version';

ALTER TABLE `categories` ADD COLUMN `sort_order` int(11) DEFAULT 0;
ALTER TABLE `categories` ADD COLUMN `is_active` tinyint(1) DEFAULT 1;
ALTER TABLE `categories` ADD KEY `idx_sort` (`sort_order`);
ALTER TABLE `categories` COMMENT='Product categories - enhanced version';

ALTER TABLE `users` ADD COLUMN `phone` varchar(20) DEFAULT NULL;
ALTER TABLE `users` ADD COLUMN `full_name` varchar(101) GENERATED ALWAYS AS (concat(`first_name`,' ',`last_name`)) STORED;
ALTER TABLE `users` DROP INDEX `idx_username`;
ALTER TABLE `users` ADD UNIQUE KEY `email` (`email`);
ALTER TABLE `users` ADD KEY `idx_phone` (`phone`);
ALTER TABLE `users` COMMENT='User accounts table - updated version';

ALTER TABLE `orders` ADD COLUMN `discount_amount` decimal(10,2) DEFAULT 0.00;
ALTER TABLE `orders` ADD COLUMN `tracking_number` varchar(50) DEFAULT NULL;
ALTER TABLE `orders` ADD COLUMN `shipping_cost` decimal(8,2) DEFAULT 0.00;
ALTER TABLE `orders` ADD COLUMN `tax_amount` decimal(10,2) DEFAULT 0.00;
ALTER TABLE `orders` ADD COLUMN `order_number` varchar(20) DEFAULT NULL;
ALTER TABLE `orders` MODIFY COLUMN `status` enum('pending','processing','shipped','delivered','cancelled','refunded') DEFAULT 'pending';
ALTER TABLE `orders` ADD UNIQUE KEY `order_number` (`order_number`);
ALTER TABLE `orders` ADD KEY `idx_order_number` (`order_number`);
ALTER TABLE `orders` COMMENT='Customer orders - enhanced version';

ALTER TABLE `products` ADD COLUMN `sale_price` decimal(10,2) DEFAULT NULL;
ALTER TABLE `products` ADD COLUMN `weight` decimal(8,3) DEFAULT NULL;
ALTER TABLE `products` ADD COLUMN `dimensions` varchar(50) DEFAULT NULL;
ALTER TABLE `products` ADD COLUMN `min_stock_level` int(11) DEFAULT 5;
ALTER TABLE `products` ADD COLUMN `is_featured` tinyint(1) DEFAULT 0;
ALTER TABLE `products` MODIFY COLUMN `name` varchar(150) NOT NULL;
ALTER TABLE `products` ADD KEY `idx_featured` (`is_featured`);
ALTER TABLE `products` COMMENT='Product catalog - enhanced version';

-- Rollback procedure: GetUserOrderHistory
DROP PROCEDURE IF EXISTS `GetUserOrderHistory`;
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` PROCEDURE `GetUserOrderHistory`(
    IN user_id_param INT,
    IN limit_param INT  
)
BEGIN
    
    IF limit_param IS NULL OR limit_param <= 0 THEN
        SET limit_param = 10;
    END IF;
    
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
END$$
DELIMITER ;

-- Rollback deletion of procedure: GetProductReviewSummary
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` PROCEDURE `GetProductReviewSummary`(IN product_id_param INT)
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
END$$
DELIMITER ;

-- Rollback function: GetUserTotalSpent
DROP FUNCTION IF EXISTS `GetUserTotalSpent`;
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` FUNCTION `GetUserTotalSpent`(user_id_param INT) RETURNS decimal(12,2)
    READS SQL DATA
    DETERMINISTIC
BEGIN
    DECLARE total DECIMAL(12,2) DEFAULT 0.00;
    
    
    SELECT COALESCE(SUM(total_amount + tax_amount + shipping_cost - discount_amount), 0.00) INTO total
    FROM orders 
    WHERE user_id = user_id_param AND status IN ('delivered', 'shipped');
    
    RETURN total;
END$$
DELIMITER ;

-- Rollback deletion of function: GetProductAverageRating
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` FUNCTION `GetProductAverageRating`(product_id_param INT) RETURNS decimal(3,2)
    READS SQL DATA
    DETERMINISTIC
BEGIN
    DECLARE avg_rating DECIMAL(3,2) DEFAULT 0.00;
    
    SELECT COALESCE(AVG(rating), 0.00) INTO avg_rating
    FROM product_reviews 
    WHERE product_id = product_id_param;
    
    RETURN avg_rating;
END$$
DELIMITER ;

-- Rollback trigger: update_stock_after_order
DROP TRIGGER IF EXISTS `update_stock_after_order`;
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` TRIGGER update_stock_after_order
    AFTER INSERT ON order_items
    FOR EACH ROW
BEGIN
    UPDATE products 
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE id = NEW.product_id;
    
    
    INSERT INTO stock_alerts (product_id, alert_type, created_at)
    SELECT NEW.product_id, 'LOW_STOCK', NOW()
    FROM products p
    WHERE p.id = NEW.product_id 
    AND p.stock_quantity <= p.min_stock_level;
END$$
DELIMITER ;

-- Rollback deletion of trigger: generate_order_number
DELIMITER $$
CREATE DEFINER=`sstuser`@`%` TRIGGER generate_order_number
    BEFORE INSERT ON orders
    FOR EACH ROW
BEGIN
    IF NEW.order_number IS NULL THEN
        
        SET NEW.order_number = CONCAT('ORD-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(FLOOR(RAND() * 999999), 6, '0'));
    END IF;
END$$
DELIMITER ;

-- Rollback event: cleanup_cancelled_orders
DROP EVENT IF EXISTS `cleanup_cancelled_orders`;
CREATE DEFINER=`sstuser`@`%` EVENT `cleanup_cancelled_orders` ON SCHEDULE EVERY 7 DAY STARTS '2025-09-04 20:20:12' ON COMPLETION NOT PRESERVE ENABLE DO DELETE FROM orders 
    WHERE status = 'cancelled' 
    AND order_date < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- Rollback deletion of event: update_featured_products
CREATE DEFINER=`sstuser`@`%` EVENT `update_featured_products` ON SCHEDULE EVERY 1 WEEK STARTS '2025-09-04 20:20:12' ON COMPLETION NOT PRESERVE ENABLE DO UPDATE products p
    SET is_featured = (
        SELECT COUNT(*) > 10
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE oi.product_id = p.id
        AND o.order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    );

-- Rollback deletion of view: product_catalog
CREATE ALGORITHM=UNDEFINED DEFINER=`sstuser`@`%` SQL SECURITY DEFINER VIEW `product_catalog` AS select `p`.`id` AS `id`,`p`.`name` AS `name`,`p`.`description` AS `description`,`p`.`price` AS `price`,`p`.`sale_price` AS `sale_price`,coalesce(`p`.`sale_price`,`p`.`price`) AS `effective_price`,`c`.`name` AS `category_name`,`p`.`stock_quantity` AS `stock_quantity`,`p`.`is_featured` AS `is_featured`,coalesce(avg(`pr`.`rating`),0) AS `avg_rating`,count(`pr`.`id`) AS `review_count` from ((`products` `p` left join `categories` `c` on(`p`.`category_id` = `c`.`id`)) left join `product_reviews` `pr` on(`p`.`id` = `pr`.`product_id`)) where `c`.`is_active` = 1 group by `p`.`id`;

-- Rollback creation of sequence: user_id_seq
DROP SEQUENCE IF EXISTS `user_id_seq`;


SET FOREIGN_KEY_CHECKS = 1;

-- Rollback script completed.