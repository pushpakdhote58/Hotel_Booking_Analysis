-- =====================================================================
-- Project 30: Hotel Booking & Customer Reservation Analysis
-- 10 Core SQL Analytical Tasks
-- Database: hotel_bookings_db
-- =====================================================================

USE `hotel_bookings_db`;

-- ---------------------------------------------------------------------
-- Task 1: Count total hotel bookings
-- ---------------------------------------------------------------------
SELECT 
    COUNT(*) AS total_hotel_bookings,
    COUNT(DISTINCT booking_id) AS verified_unique_bookings
FROM `hotel_bookings`;


-- ---------------------------------------------------------------------
-- Task 2: Calculate occupancy rate
-- Occupancy rate: proportion of booked stays that actually completed check-out
-- ---------------------------------------------------------------------
SELECT 
    hotel,
    COUNT(*) AS total_bookings,
    SUM(CASE WHEN is_canceled = 0 THEN 1 ELSE 0 END) AS occupied_stays,
    ROUND(SUM(CASE WHEN is_canceled = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS occupancy_rate_pct
FROM `hotel_bookings`
GROUP BY hotel;


-- ---------------------------------------------------------------------
-- Task 3: Find room type-wise bookings
-- ---------------------------------------------------------------------
SELECT 
    reserved_room_type AS room_type,
    COUNT(*) AS total_bookings,
    SUM(stays_in_weekend_nights + stays_in_week_nights) AS total_room_nights,
    ROUND(AVG(adr), 2) AS avg_room_price_adr,
    ROUND(SUM((CASE WHEN (stays_in_weekend_nights + stays_in_week_nights) = 0 THEN 1 ELSE (stays_in_weekend_nights + stays_in_week_nights) END) * adr), 2) AS total_revenue
FROM `hotel_bookings`
GROUP BY reserved_room_type
ORDER BY total_bookings DESC;


-- ---------------------------------------------------------------------
-- Task 4: Calculate total revenue
-- ---------------------------------------------------------------------
SELECT 
    hotel,
    ROUND(SUM((CASE WHEN (stays_in_weekend_nights + stays_in_week_nights) = 0 THEN 1 ELSE (stays_in_weekend_nights + stays_in_week_nights) END) * adr), 2) AS total_booked_revenue,
    ROUND(SUM(CASE WHEN is_canceled = 0 THEN (CASE WHEN (stays_in_weekend_nights + stays_in_week_nights) = 0 THEN 1 ELSE (stays_in_weekend_nights + stays_in_week_nights) END) * adr ELSE 0 END), 2) AS realized_check_out_revenue
FROM `hotel_bookings`
GROUP BY hotel
WITH ROLLUP;


-- ---------------------------------------------------------------------
-- Task 5: Find average booking duration
-- ---------------------------------------------------------------------
SELECT 
    hotel,
    ROUND(AVG(stays_in_weekend_nights + stays_in_week_nights), 2) AS avg_total_stay_nights,
    ROUND(AVG(stays_in_weekend_nights), 2) AS avg_weekend_nights,
    ROUND(AVG(stays_in_week_nights), 2) AS avg_week_nights
FROM `hotel_bookings`
GROUP BY hotel;


-- ---------------------------------------------------------------------
-- Task 6: Identify top booking channels
-- ---------------------------------------------------------------------
SELECT 
    distribution_channel,
    market_segment,
    COUNT(*) AS total_bookings,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM `hotel_bookings`), 2) AS booking_share_pct,
    ROUND(SUM((CASE WHEN (stays_in_weekend_nights + stays_in_week_nights) = 0 THEN 1 ELSE (stays_in_weekend_nights + stays_in_week_nights) END) * adr), 2) AS total_revenue
FROM `hotel_bookings`
GROUP BY distribution_channel, market_segment
ORDER BY total_bookings DESC
LIMIT 10;


-- ---------------------------------------------------------------------
-- Task 7: Calculate cancellation percentage
-- ---------------------------------------------------------------------
SELECT 
    hotel,
    COUNT(*) AS total_reservations,
    SUM(is_canceled) AS total_cancellations,
    ROUND(SUM(is_canceled) * 100.0 / COUNT(*), 2) AS cancellation_rate_pct
FROM `hotel_bookings`
GROUP BY hotel;


-- ---------------------------------------------------------------------
-- Task 8: Find monthly booking trends
-- ---------------------------------------------------------------------
SELECT 
    arrival_date_year,
    arrival_date_month,
    COUNT(*) AS total_bookings,
    SUM(is_canceled) AS cancellations,
    ROUND(AVG(adr), 2) AS avg_adr,
    ROUND(SUM((CASE WHEN (stays_in_weekend_nights + stays_in_week_nights) = 0 THEN 1 ELSE (stays_in_weekend_nights + stays_in_week_nights) END) * adr), 2) AS monthly_revenue
FROM `hotel_bookings`
GROUP BY arrival_date_year, arrival_date_month
ORDER BY arrival_date_year, 
         CASE arrival_date_month
             WHEN 'January' THEN 1 WHEN 'February' THEN 2 WHEN 'March' THEN 3
             WHEN 'April' THEN 4 WHEN 'May' THEN 5 WHEN 'June' THEN 6
             WHEN 'July' THEN 7 WHEN 'August' THEN 8 WHEN 'September' THEN 9
             WHEN 'October' THEN 10 WHEN 'November' THEN 11 WHEN 'December' THEN 12
         END;


-- ---------------------------------------------------------------------
-- Task 9: Rank hotels by revenue
-- ---------------------------------------------------------------------
SELECT 
    hotel,
    ROUND(SUM((CASE WHEN (stays_in_weekend_nights + stays_in_week_nights) = 0 THEN 1 ELSE (stays_in_weekend_nights + stays_in_week_nights) END) * adr), 2) AS total_revenue,
    COUNT(*) AS total_bookings,
    ROUND(AVG(adr), 2) AS avg_room_price,
    RANK() OVER (ORDER BY SUM((CASE WHEN (stays_in_weekend_nights + stays_in_week_nights) = 0 THEN 1 ELSE (stays_in_weekend_nights + stays_in_week_nights) END) * adr) DESC) AS revenue_rank
FROM `hotel_bookings`
GROUP BY hotel;


-- ---------------------------------------------------------------------
-- Task 10: Find customer nationality distribution
-- ---------------------------------------------------------------------
SELECT 
    country AS customer_nationality,
    COUNT(*) AS guest_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM `hotel_bookings`), 2) AS share_percentage
FROM `hotel_bookings`
WHERE country IS NOT NULL AND country != 'NULL'
GROUP BY country
ORDER BY guest_count DESC
LIMIT 20;
