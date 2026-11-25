"""
Load Hotel Bookings CSV into MySQL Database
============================================
Connects to local MySQL server, creates the 'hotel_bookings_db' database,
and loads hotel_bookings.csv with optimized batch inserts.

Usage:
    python load_data_to_mysql.py
"""

import mysql.connector
import pandas as pd
import numpy as np
import sys
import time

# ============================================================
# CONFIGURATION
# ============================================================
MYSQL_HOST = "127.0.0.1"
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
MYSQL_DATABASE = "hotel_bookings_db"
BATCH_SIZE = 5000
CSV_PATH = "DATA/hotel_bookings.csv"
# ============================================================


def create_connection(database=None):
    """Create and return a MySQL connection."""
    config = {
        "host": MYSQL_HOST,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
    }
    if database:
        config["database"] = database
    return mysql.connector.connect(**config)


def create_database_and_table():
    """Create hotel_bookings_db and hotel_bookings table."""
    conn = create_connection()
    cursor = conn.cursor()

    print(f"[1/3] Creating database '{MYSQL_DATABASE}'...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                   f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor.execute(f"USE `{MYSQL_DATABASE}`;")

    print("[2/3] Creating table 'hotel_bookings'...")
    cursor.execute("DROP TABLE IF EXISTS `hotel_bookings`;")
    cursor.execute("""
    CREATE TABLE `hotel_bookings` (
        `booking_id`                        INT AUTO_INCREMENT PRIMARY KEY,
        `hotel`                             VARCHAR(50) NOT NULL,
        `is_canceled`                       TINYINT NOT NULL,
        `lead_time`                         INT NOT NULL,
        `arrival_date_year`                 INT NOT NULL,
        `arrival_date_month`                VARCHAR(20) NOT NULL,
        `arrival_date_week_number`          INT NOT NULL,
        `arrival_date_day_of_month`         INT NOT NULL,
        `arrival_date`                      DATE,
        `stays_in_weekend_nights`           INT NOT NULL,
        `stays_in_week_nights`              INT NOT NULL,
        `total_stay_nights`                 INT NOT NULL,
        `adults`                            INT NOT NULL,
        `children`                          INT DEFAULT 0,
        `babies`                            INT NOT NULL,
        `total_guests`                      INT NOT NULL,
        `meal`                              VARCHAR(50),
        `country`                           VARCHAR(10),
        `market_segment`                    VARCHAR(50),
        `distribution_channel`              VARCHAR(50),
        `is_repeated_guest`                 TINYINT NOT NULL,
        `previous_cancellations`            INT NOT NULL,
        `previous_bookings_not_canceled`    INT NOT NULL,
        `reserved_room_type`                VARCHAR(10),
        `assigned_room_type`                VARCHAR(10),
        `room_type_mismatch`                TINYINT DEFAULT 0,
        `booking_changes`                   INT NOT NULL,
        `deposit_type`                      VARCHAR(50),
        `agent`                             INT DEFAULT 0,
        `company`                           INT DEFAULT 0,
        `days_in_waiting_list`              INT NOT NULL,
        `customer_type`                     VARCHAR(50),
        `adr`                               DECIMAL(10, 2) NOT NULL,
        `revenue`                           DECIMAL(12, 2) NOT NULL,
        `required_car_parking_spaces`       INT NOT NULL,
        `total_of_special_requests`         INT NOT NULL,
        `reservation_status`                VARCHAR(50),
        `reservation_status_date`           DATE,

        INDEX idx_hotel (`hotel`),
        INDEX idx_arrival_date (`arrival_date`),
        INDEX idx_is_canceled (`is_canceled`),
        INDEX idx_market_segment (`market_segment`),
        INDEX idx_customer_type (`customer_type`),
        INDEX idx_country (`country`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("    Database and table created successfully!\n")


def load_hotel_bookings():
    """Load and ingest hotel_bookings.csv into MySQL."""
    print(f"[3/3] Loading data from '{CSV_PATH}' into MySQL...")

    df = pd.read_csv(CSV_PATH)
    total_raw = len(df)
    print(f"    Read {total_raw:,} records from CSV.")

    # Impute missing values
    df['children'] = df['children'].fillna(0).astype(int)
    df['country'] = df['country'].fillna('Unknown').astype(str).str.strip()
    df['agent'] = df['agent'].fillna(0).astype(int)
    df['company'] = df['company'].fillna(0).astype(int)
    df['adr'] = np.where(df['adr'] < 0, 0.0, df['adr']).round(2)

    # Derived dates
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    month_nums = df['arrival_date_month'].map(month_map)
    df['arrival_date'] = pd.to_datetime(
        df['arrival_date_year'].astype(str) + '-' +
        month_nums.astype(str).str.zfill(2) + '-' +
        df['arrival_date_day_of_month'].astype(str).str.zfill(2),
        errors='coerce'
    ).dt.strftime('%Y-%m-%d')

    df['reservation_status_date'] = pd.to_datetime(
        df['reservation_status_date'], errors='coerce'
    ).dt.strftime('%Y-%m-%d')

    # Derived features
    df['total_stay_nights'] = df['stays_in_weekend_nights'] + df['stays_in_week_nights']
    billing_nights = np.where(df['total_stay_nights'] == 0, 1, df['total_stay_nights'])
    df['revenue'] = (billing_nights * df['adr']).round(2)
    df['total_guests'] = df['adults'] + df['children'] + df['babies']
    df['room_type_mismatch'] = np.where(df['reserved_room_type'] != df['assigned_room_type'], 1, 0)

    # Replace remaining NaN with None
    df = df.replace({np.nan: None})

    columns = [
        'hotel', 'is_canceled', 'lead_time', 'arrival_date_year',
        'arrival_date_month', 'arrival_date_week_number',
        'arrival_date_day_of_month', 'arrival_date',
        'stays_in_weekend_nights', 'stays_in_week_nights',
        'total_stay_nights', 'adults', 'children', 'babies',
        'total_guests', 'meal', 'country', 'market_segment',
        'distribution_channel', 'is_repeated_guest',
        'previous_cancellations', 'previous_bookings_not_canceled',
        'reserved_room_type', 'assigned_room_type',
        'room_type_mismatch', 'booking_changes', 'deposit_type',
        'agent', 'company', 'days_in_waiting_list',
        'customer_type', 'adr', 'revenue',
        'required_car_parking_spaces', 'total_of_special_requests',
        'reservation_status', 'reservation_status_date'
    ]

    col_names = ", ".join([f"`{c}`" for c in columns])
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = f"INSERT INTO `hotel_bookings` ({col_names}) VALUES ({placeholders})"

    conn = create_connection(database=MYSQL_DATABASE)
    cursor = conn.cursor()

    start_time = time.time()
    for i in range(0, total_raw, BATCH_SIZE):
        batch = df[columns].iloc[i:i + BATCH_SIZE]
        rows = [tuple(r) for r in batch.itertuples(index=False, name=None)]
        cursor.executemany(insert_sql, rows)
        conn.commit()
        loaded = min(i + BATCH_SIZE, total_raw)
        elapsed = time.time() - start_time
        print(f"    {loaded:>7,} / {total_raw:,} rows ({loaded*100//total_raw}%) [{elapsed:.1f}s]", end="\r")

    print(f"\n    Successfully loaded {total_raw:,} records in {time.time()-start_time:.1f}s\n")

    # Quick verify
    cursor.execute("SELECT COUNT(*) FROM `hotel_bookings`;")
    print(f"  Verified row count: {cursor.fetchone()[0]:,} rows in MySQL.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  HOTEL BOOKINGS -> MYSQL INGESTION")
    print("=" * 60)
    create_database_and_table()
    load_hotel_bookings()
    print("  Ingestion complete!")
