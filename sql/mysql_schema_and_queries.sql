-- ============================================================
-- B2B Hotel Business Intelligence - MySQL Schema & 10 BI Queries
-- Database: hotel_bookings_db
-- ============================================================

CREATE DATABASE IF NOT EXISTS `hotel_bookings_db`
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `hotel_bookings_db`;

-- ============================================================
-- SECTION 1: NORMALIZED MULTI-TENANT SCHEMA (8 Core Tables)
-- All Primary & Foreign Keys use INT for native Power BI support
-- ============================================================

-- 1. businesses (Hotel Properties)
CREATE TABLE IF NOT EXISTS `businesses` (
    `business_id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `industry` VARCHAR(100) DEFAULT 'Hospitality & Tourism',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. users (Platform Administrators & Hotel Managers)
CREATE TABLE IF NOT EXISTS `users` (
    `user_id` INT AUTO_INCREMENT PRIMARY KEY,
    `business_id` INT,
    `email` VARCHAR(255) UNIQUE NOT NULL,
    `role` VARCHAR(50) DEFAULT 'owner',
    FOREIGN KEY (`business_id`) REFERENCES `businesses`(`business_id`) ON DELETE CASCADE
);

-- 3. products (Room Types & Packages)
CREATE TABLE IF NOT EXISTS `products` (
    `product_id` INT AUTO_INCREMENT PRIMARY KEY,
    `business_id` INT,
    `product_name` VARCHAR(255) NOT NULL,
    `category` VARCHAR(100),
    UNIQUE KEY `uq_biz_prod` (`business_id`, `product_name`),
    FOREIGN KEY (`business_id`) REFERENCES `businesses`(`business_id`) ON DELETE CASCADE
);

-- 4. customers (Guests & Corporate Accounts)
CREATE TABLE IF NOT EXISTS `customers` (
    `customer_id` INT AUTO_INCREMENT PRIMARY KEY,
    `business_id` INT,
    `customer_name` VARCHAR(255) NOT NULL,
    `customer_type` VARCHAR(50) DEFAULT 'Transient',
    `region` VARCHAR(100),
    UNIQUE KEY `uq_biz_cust` (`business_id`, `customer_name`),
    FOREIGN KEY (`business_id`) REFERENCES `businesses`(`business_id`) ON DELETE CASCADE
);

-- 5. sales (Bookings / Reservations)
CREATE TABLE IF NOT EXISTS `sales` (
    `sale_id` INT AUTO_INCREMENT PRIMARY KEY,
    `business_id` INT,
    `customer_id` INT,
    `sale_date` DATE NOT NULL,
    `payment_mode` VARCHAR(50) DEFAULT 'No Deposit',
    FOREIGN KEY (`business_id`) REFERENCES `businesses`(`business_id`) ON DELETE CASCADE,
    FOREIGN KEY (`customer_id`) REFERENCES `customers`(`customer_id`)
);

-- 6. sale_items (Booking Stay Details: Nights, ADR, Revenue, Operating Cost)
CREATE TABLE IF NOT EXISTS `sale_items` (
    `item_id` INT AUTO_INCREMENT PRIMARY KEY,
    `sale_id` INT,
    `product_id` INT,
    `quantity` DECIMAL(10, 2) NOT NULL,
    `unit_price` DECIMAL(12, 2) NOT NULL,
    `unit_cost` DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (`sale_id`) REFERENCES `sales`(`sale_id`) ON DELETE CASCADE,
    FOREIGN KEY (`product_id`) REFERENCES `products`(`product_id`)
);

-- 7. inventory (Room Capacity & Availability Monitoring)
CREATE TABLE IF NOT EXISTS `inventory` (
    `product_id` INT PRIMARY KEY,
    `business_id` INT,
    `current_stock` DECIMAL(10, 2) DEFAULT 0,
    `reorder_level` DECIMAL(10, 2) DEFAULT 15,
    FOREIGN KEY (`product_id`) REFERENCES `products`(`product_id`) ON DELETE CASCADE,
    FOREIGN KEY (`business_id`) REFERENCES `businesses`(`business_id`) ON DELETE CASCADE
);

-- 8. uploads (File Ingestion Audit Logs)
CREATE TABLE IF NOT EXISTS `uploads` (
    `upload_id` INT AUTO_INCREMENT PRIMARY KEY,
    `business_id` INT,
    `file_name` VARCHAR(255) NOT NULL,
    `status` VARCHAR(50) DEFAULT 'processed',
    `uploaded_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`business_id`) REFERENCES `businesses`(`business_id`) ON DELETE CASCADE
);


-- ============================================================
-- SECTION 2: 10 CORE HOTEL BI ANALYTICAL QUERIES
-- ============================================================

-- Query 1: Total bookings, nights sold, and revenue per room category
SELECT p.category AS room_category,
       COUNT(DISTINCT s.sale_id) AS total_bookings,
       SUM(si.quantity) AS total_room_nights,
       ROUND(SUM(si.quantity * si.unit_price), 2) AS total_revenue
FROM sale_items si
JOIN products p ON si.product_id = p.product_id
JOIN sales s ON si.sale_id = s.sale_id
GROUP BY p.category
ORDER BY total_room_nights DESC;

-- Query 2: Average Daily Rate (ADR) and estimated gross profit by room category
SELECT p.category AS room_category,
       ROUND(AVG(si.unit_price), 2) AS avg_adr,
       ROUND(AVG(si.quantity * (si.unit_price - si.unit_cost)), 2) AS avg_gross_profit
FROM sale_items si
JOIN products p ON si.product_id = p.product_id
GROUP BY p.category
ORDER BY avg_gross_profit DESC;

-- Query 3: Top 10 highest-revenue generating room types / packages
SELECT p.product_name,
       p.category AS room_category,
       ROUND(SUM(si.quantity * si.unit_price), 2) AS total_revenue
FROM sale_items si
JOIN products p ON si.product_id = p.product_id
GROUP BY p.product_name, p.category
ORDER BY total_revenue DESC
LIMIT 10;

-- Query 4: Average available inventory stock level by room category
SELECT p.category AS room_category,
       ROUND(AVG(i.current_stock), 2) AS avg_available_rooms
FROM inventory i
JOIN products p ON i.product_id = p.product_id
GROUP BY p.category;

-- Query 5: Top room packages by gross margin percentage
SELECT p.product_name,
       ROUND(((SUM(si.quantity * (si.unit_price - si.unit_cost)) /
       NULLIF(SUM(si.quantity * si.unit_price), 0)) * 100), 2) AS gross_margin_pct
FROM sale_items si
JOIN products p ON si.product_id = p.product_id
GROUP BY p.product_name
ORDER BY gross_margin_pct DESC
LIMIT 10;

-- Query 6: Bookings breakdown by deposit / payment mode
SELECT payment_mode AS deposit_type,
       COUNT(*) AS booking_count
FROM sales
GROUP BY payment_mode;

-- Query 7: Guest origins with most bookings
SELECT c.region AS country,
       COUNT(c.customer_id) AS total_guests
FROM customers c
GROUP BY c.region
ORDER BY total_guests DESC
LIMIT 10;

-- Query 8: Rank room types by gross profit within each hotel property (Window Function)
SELECT b.name AS hotel_property,
       p.product_name AS room_type,
       ROUND(SUM(si.quantity * (si.unit_price - si.unit_cost)), 2) AS total_profit,
       RANK() OVER (PARTITION BY b.name
                    ORDER BY SUM(si.quantity * (si.unit_price - si.unit_cost)) DESC) AS profit_rank
FROM sale_items si
JOIN products p ON si.product_id = p.product_id
JOIN businesses b ON p.business_id = b.business_id
GROUP BY b.name, p.product_name;

-- Query 9: High-value bookings exceeding the overall average booking value
SELECT s.sale_id,
       c.customer_name,
       ROUND(SUM(si.quantity * si.unit_price), 2) AS booking_value
FROM sales s
JOIN customers c ON s.customer_id = c.customer_id
JOIN sale_items si ON s.sale_id = si.sale_id
GROUP BY s.sale_id, c.customer_name
HAVING SUM(si.quantity * si.unit_price) > (
    SELECT AVG(booking_total) FROM (
        SELECT SUM(quantity * unit_price) AS booking_total
        FROM sale_items
        GROUP BY sale_id
    ) sub
)
ORDER BY booking_value DESC
LIMIT 10;

-- Query 10: Customer segment revenue distribution (Transient vs Contract vs Group)
SELECT c.customer_type,
       COUNT(DISTINCT c.customer_id) AS total_guests,
       ROUND(SUM(si.quantity * si.unit_price), 2) AS total_revenue
FROM customers c
JOIN sales s ON c.customer_id = s.customer_id
JOIN sale_items si ON s.sale_id = si.sale_id
GROUP BY c.customer_type
ORDER BY total_revenue DESC;
