-- DDL Wizard Migration Script
-- Source Schema: classicmodels
-- Destination Schema: classicmodels
-- Generated: 2025-09-01T12:56:06.489584

-- WARNING: Review this script carefully before executing!
-- This script will modify the destination database structure.

SET FOREIGN_KEY_CHECKS = 0;

-- TABLES CHANGES
--------------------------------------------------
-- Modify table: payments
-- Table `payments` differences:\n  + ADD FOREIGN KEY `payments_ibfk_1` (customerNumber) -> customers(customerNumber)

ALTER TABLE `classicmodels`.`payments` ADD CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`customerNumber`) REFERENCES `customers` (`customerNumber`);

-- Modify table: offices
-- Table `offices` differences:\n  + ADD COLUMN `phone` varchar(50)

ALTER TABLE `classicmodels`.`offices`\n  ADD COLUMN `phone` varchar(50) NOT NULL;

-- Modify table: products
-- Table `products` differences:\n  - DROP COLUMN `dummy_col`

ALTER TABLE `classicmodels`.`products`\n  DROP COLUMN `dummy_col`;



SET FOREIGN_KEY_CHECKS = 1;

-- Migration script completed.