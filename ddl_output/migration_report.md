# Database Migration Report
Generated on: 2025-09-04 14:28:23

## Summary
- Source Schema: ddlwizard_source_test
- Destination Schema: ddlwizard_dest_test


## Detailed Changes

### TABLE - stock_alerts
**Operation**: DROP
**SQL**:
```sql
DROP TABLE stock_alerts
```

### TABLE - product_reviews
**Operation**: DROP
**SQL**:
```sql
DROP TABLE product_reviews
```

### TABLE - categories
**Operation**: MODIFY
**SQL**:
```sql
ALTER TABLE categories
```

### TABLE - products
**Operation**: MODIFY
**SQL**:
```sql
ALTER TABLE products
```

### TABLE - order_items
**Operation**: MODIFY
**SQL**:
```sql
ALTER TABLE order_items
```

### TABLE - orders
**Operation**: MODIFY
**SQL**:
```sql
ALTER TABLE orders
```

### TABLE - users
**Operation**: MODIFY
**SQL**:
```sql
ALTER TABLE users
```

### PROCEDURE - GetProductReviewSummary
**Operation**: DROP
**SQL**:
```sql
DROP PROCEDURE GetProductReviewSummary
```

### PROCEDURE - GetUserOrderHistory
**Operation**: UPDATE
**SQL**:
```sql
DROP/CREATE PROCEDURE GetUserOrderHistory
```

### FUNCTION - GetProductAverageRating
**Operation**: DROP
**SQL**:
```sql
DROP FUNCTION GetProductAverageRating
```

### FUNCTION - GetUserTotalSpent
**Operation**: UPDATE
**SQL**:
```sql
DROP/CREATE FUNCTION GetUserTotalSpent
```

## Safety Warnings

