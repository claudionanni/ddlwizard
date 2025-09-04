-- DDL Wizard Migration Script
-- Source Schema: ddlwizard_source_test
-- Destination Schema: ddlwizard_dest_test
-- Generated: 2025-09-04T17:21:07.088749

-- WARNING: Review this script carefully before executing!
-- This script will modify the destination database structure.

SET FOREIGN_KEY_CHECKS = 0;

-- TABLES CHANGES
--------------------------------------------------
-- Modify table: products
-- Table 'products' differences:
--   1. Column MODIFIED: name
--       FROM: varchar(100) NOT NULL
--       TO:   varchar(150) NOT NULL
ALTER TABLE `products` MODIFY COLUMN `name` varchar(150) NOT NULL;

-- Modify table: orders
-- Table 'orders' differences:
--   1. Column MODIFIED: status
--       FROM: enum('pending','processing','shipped','delivered','cancelled') DEFAULT 'pending'
--       TO:   enum('pending','processing','shipped','delivered','cancelled','refunded') DEFAULT 'pending'
ALTER TABLE `orders` MODIFY COLUMN `status` enum('pending','processing','shipped','delivered','cancelled','refunded') DEFAULT 'pending';


-- PROCEDURES CHANGES
--------------------------------------------------

-- FUNCTIONS CHANGES
--------------------------------------------------

-- TRIGGERS CHANGES
--------------------------------------------------

-- EVENTS CHANGES
--------------------------------------------------

-- VIEWS CHANGES
--------------------------------------------------

-- SEQUENCES CHANGES
--------------------------------------------------

SET FOREIGN_KEY_CHECKS = 1;

-- Migration script completed.