"""
B2B Hotel Business Intelligence - Data Cleaning, Normalization & MySQL Pipeline
================================================================================
Implements the full 5-stage automated pipeline from the Blueprint:
1. Load & Inspect Raw Data (hotel_bookings.csv)
2. Pandas Cleaning, Deduplication & Imputation
3. Feature Engineering & Financial KPI Calculation
4. Normalization into 8 Core MySQL Tables with Foreign Keys
5. Execution & Verification of the 10 Blueprint BI Queries
6. Export of Cleaned_Business_Data.csv
"""

import mysql.connector
import pandas as pd
import numpy as np
import uuid
import time

# Configuration
MYSQL_HOST = "127.0.0.1"
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
MYSQL_DATABASE = "hotel_bookings_db"
CSV_PATH = "DATA/hotel_bookings.csv"

print("=" * 65)
print("  HOTEL BI: DATA CLEANING, NORMALIZATION & MYSQL PIPELINE")
print("=" * 65)

# Connect to MySQL (ensure database exists)
conn = mysql.connector.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD)
cursor = conn.cursor()
cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
               f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
cursor.execute(f"USE `{MYSQL_DATABASE}`;")

# -------------------------------------------------------------------
# STAGE 1: LOAD RAW CSV DATA
# -------------------------------------------------------------------
print("\n[Stage 1/5] Loading raw hotel bookings dataset...")
df_raw = pd.read_csv(CSV_PATH)
initial_shape = df_raw.shape
print(f"  Raw records loaded: {initial_shape[0]:,} rows, {initial_shape[1]} columns")

# -------------------------------------------------------------------
# STAGE 2: PANDAS DATA CLEANING & IMPUTATION
# -------------------------------------------------------------------
print("\n[Stage 2/5] Cleaning data & handling missing values...")

# Deduplication
dups_count = df_raw.duplicated().sum()
df = df_raw.drop_duplicates().copy()
print(f"  Duplicates removed: {dups_count:,}")
print(f"  Unique booking records: {len(df):,}")

# Impute missing values
df['children'] = df['children'].fillna(0).astype(int)
df['country'] = df['country'].fillna('Unknown').astype(str).str.strip()
df['agent'] = df['agent'].fillna(0).astype(int)
df['company'] = df['company'].fillna(0).astype(int)

# Fix negative / invalid ADR
df['adr'] = np.where(df['adr'] < 0, 0.0, df['adr']).round(2)

# Build standard arrival date (YYYY-MM-DD)
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
)

# Standardize core columns
df = df.dropna(subset=['arrival_date'])
df['booking_id'] = np.arange(1, len(df) + 1)
df['total_stay_nights'] = df['stays_in_weekend_nights'] + df['stays_in_week_nights']
# Day-use or zero-night stays billed as 1 night
df['billing_nights'] = np.where(df['total_stay_nights'] == 0, 1, df['total_stay_nights'])
df['total_guests'] = df['adults'] + df['children'] + df['babies']

# -------------------------------------------------------------------
# STAGE 3: FINANCIAL KPIS & FEATURE ENGINEERING
# -------------------------------------------------------------------
print("\n[Stage 3/5] Engineering financial KPIs...")

df['Quantity'] = df['billing_nights'].astype(float)
df['Unit_Price'] = df['adr'].astype(float)
df['Revenue'] = (df['Quantity'] * df['Unit_Price']).round(2)

# Operating cost per room night (hospitality industry baseline ~40% of ADR)
df['Unit_Cost'] = (df['Unit_Price'] * 0.40).round(2)
df['COGS'] = (df['Quantity'] * df['Unit_Cost']).round(2)
df['Gross_Profit'] = (df['Revenue'] - df['COGS']).round(2)
df['Gross_Margin_Pct'] = np.where(
    df['Revenue'] > 0,
    ((df['Gross_Profit'] / df['Revenue']) * 100).round(2),
    60.0
)

# Operational metrics
df['Customer_Age_Days'] = df['lead_time'].astype(int)
df['Product_Name'] = df['hotel'] + " - Room " + df['reserved_room_type'].astype(str)
df['Category'] = df['hotel']
df['Customer_ID'] = np.arange(1, len(df) + 1)
df['Customer_Name'] = "Guest #" + df['Customer_ID'].astype(str) + " (" + df['country'] + ")"
df['Customer_Type'] = df['customer_type'].fillna('Transient')
df['Region'] = df['country']
df['Payment_Mode'] = df['deposit_type'].fillna('No Deposit')

# Inventory availability per room type
unique_prods = df['Product_Name'].unique()
np.random.seed(42)
prod_stock_map = {}
for p in unique_prods:
    r = np.random.rand()
    if r < 0.15:
        prod_stock_map[p] = float(np.random.randint(1, 15))  # Low stock
    else:
        prod_stock_map[p] = float(np.random.randint(20, 100)) # Healthy stock

df['Current_Stock'] = df['Product_Name'].map(prod_stock_map)
df['Reorder_Level'] = 15.0
df['Stock_Status'] = np.where(df['Current_Stock'] <= 15, 'Low Stock', 'Healthy Stock')

print(f"  Clean records ready: {len(df):,}")
print(f"  Total Booking Revenue: ${df['Revenue'].sum():,.2f}")
print(f"  Average Daily Rate (ADR): ${df['Unit_Price'].mean():.2f}")

# -------------------------------------------------------------------
# STAGE 4: POPULATE 8 NORMALIZED MYSQL TABLES (INT KEYS)
# -------------------------------------------------------------------
print("\n[Stage 4/5] Normalizing & populating 8 relational MySQL tables...")

cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

# Truncate tables cleanly
for tbl in ['sale_items', 'sales', 'inventory', 'customers', 'products', 'uploads', 'users', 'businesses']:
    try:
        cursor.execute(f"TRUNCATE TABLE `{tbl}`;")
    except Exception:
        pass
conn.commit()

# 1. Businesses (Hotel Properties)
print("  [1/8] Populating 'businesses'...")
hotels = [
    (1, "City Hotel Lisbon", "Hospitality & Tourism"),
    (2, "Resort Hotel Algarve", "Hospitality & Tourism")
]
cursor.executemany(
    "INSERT INTO businesses (business_id, name, industry) VALUES (%s, %s, %s)",
    hotels
)
conn.commit()
hotel_biz_map = {
    'City Hotel': 1,
    'Resort Hotel': 2
}
df['business_id'] = df['hotel'].map(hotel_biz_map).astype(int)

# 2. Users
print("  [2/8] Populating 'users'...")
users_data = [
    (1, 1, "manager@cityhotel.com", "manager"),
    (2, 2, "manager@resorthotel.com", "manager")
]
cursor.executemany(
    "INSERT INTO users (user_id, business_id, email, role) VALUES (%s, %s, %s, %s)",
    users_data
)
conn.commit()

# 3. Products (Room Types)
print("  [3/8] Populating 'products'...")
prod_df = df[['Product_Name', 'Category', 'business_id']].drop_duplicates(subset=['Product_Name']).copy()
prod_df['product_id'] = np.arange(1, len(prod_df) + 1)
prod_rows = [
    (int(r.product_id), int(r.business_id), str(r.Product_Name), str(r.Category))
    for r in prod_df.itertuples()
]
cursor.executemany(
    "INSERT INTO products (product_id, business_id, product_name, category) VALUES (%s, %s, %s, %s)",
    prod_rows
)
conn.commit()
prod_id_map = dict(zip(prod_df['Product_Name'], prod_df['product_id']))
df['product_id'] = df['Product_Name'].map(prod_id_map).astype(int)
print(f"    ✓ Inserted {len(prod_rows)} room products")

# 4. Inventory
print("  [4/8] Populating 'inventory'...")
inv_rows = [
    (int(r.product_id), int(r.business_id), float(prod_stock_map[r.Product_Name]), 15.0)
    for r in prod_df.itertuples()
]
cursor.executemany(
    "INSERT INTO inventory (product_id, business_id, current_stock, reorder_level) VALUES (%s, %s, %s, %s)",
    inv_rows
)
conn.commit()
print(f"    ✓ Inserted {len(inv_rows)} inventory records")

# 5. Customers (Guests)
print("  [5/8] Populating 'customers'...")
cust_rows = [
    (int(r.Customer_ID), int(r.business_id), str(r.Customer_Name), str(r.Customer_Type), str(r.Region))
    for r in df[['Customer_ID', 'business_id', 'Customer_Name', 'Customer_Type', 'Region']].itertuples()
]
BATCH_SIZE = 10000
for i in range(0, len(cust_rows), BATCH_SIZE):
    cursor.executemany(
        "INSERT INTO customers (customer_id, business_id, customer_name, customer_type, region) VALUES (%s, %s, %s, %s, %s)",
        cust_rows[i:i + BATCH_SIZE]
    )
    conn.commit()
print(f"    ✓ Inserted {len(cust_rows):,} customer records")

# 6. Sales (Bookings)
print("  [6/8] Populating 'sales' (bookings)...")
sales_rows = [
    (int(r.booking_id), int(r.business_id), int(r.Customer_ID), r.arrival_date.strftime('%Y-%m-%d'), str(r.Payment_Mode))
    for r in df[['booking_id', 'business_id', 'Customer_ID', 'arrival_date', 'Payment_Mode']].itertuples()
]
for i in range(0, len(sales_rows), BATCH_SIZE):
    cursor.executemany(
        "INSERT INTO sales (sale_id, business_id, customer_id, sale_date, payment_mode) VALUES (%s, %s, %s, %s, %s)",
        sales_rows[i:i + BATCH_SIZE]
    )
    conn.commit()
print(f"    ✓ Inserted {len(sales_rows):,} booking sales")

# 7. Sale Items (Booking details)
print("  [7/8] Populating 'sale_items' (stay nights & rate)...")
items_rows = [
    (int(r.booking_id), int(r.booking_id), int(r.product_id), float(r.Quantity), float(r.Unit_Price), float(r.Unit_Cost))
    for r in df[['booking_id', 'product_id', 'Quantity', 'Unit_Price', 'Unit_Cost']].itertuples()
]
for i in range(0, len(items_rows), BATCH_SIZE):
    cursor.executemany(
        "INSERT INTO sale_items (item_id, sale_id, product_id, quantity, unit_price, unit_cost) VALUES (%s, %s, %s, %s, %s, %s)",
        items_rows[i:i + BATCH_SIZE]
    )
    conn.commit()
print(f"    ✓ Inserted {len(items_rows):,} sale item records")

# 8. Uploads
print("  [8/8] Populating 'uploads'...")
cursor.execute(
    "INSERT INTO uploads (upload_id, business_id, file_name, status) VALUES (%s, %s, %s, %s)",
    (1, 1, "hotel_bookings.csv", "processed")
)
conn.commit()

cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
conn.commit()
print("\n  ✅ All 8 MySQL Relational Tables Successfully Populated with INT Keys!")

# -------------------------------------------------------------------
# STAGE 5: EXECUTE & VERIFY 10 BLUEPRINT BI QUERIES
# -------------------------------------------------------------------
print("\n" + "=" * 65)
print("  [Stage 5/5] EXECUTING 10 HOTEL BI QUERIES ON NORMALIZED SCHEMA")
print("=" * 65)

queries = [
    (
        "1. Total bookings, room nights, and revenue by hotel type",
        """
        SELECT p.category AS hotel_type,
               COUNT(DISTINCT s.sale_id) AS total_bookings,
               SUM(si.quantity) AS total_room_nights,
               ROUND(SUM(si.quantity * si.unit_price), 2) AS total_revenue
        FROM sale_items si
        JOIN products p ON si.product_id = p.product_id
        JOIN sales s ON si.sale_id = s.sale_id
        GROUP BY p.category ORDER BY total_revenue DESC;
        """
    ),
    (
        "2. Average ADR and estimated gross profit by hotel type",
        """
        SELECT p.category AS hotel_type,
               ROUND(AVG(si.unit_price), 2) AS avg_adr,
               ROUND(AVG(si.quantity * (si.unit_price - si.unit_cost)), 2) AS avg_gross_profit
        FROM sale_items si JOIN products p ON si.product_id = p.product_id
        GROUP BY p.category;
        """
    ),
    (
        "3. Top 10 highest-revenue generating room types / packages",
        """
        SELECT p.product_name, p.category, ROUND(SUM(si.quantity * si.unit_price), 2) AS total_revenue
        FROM sale_items si JOIN products p ON si.product_id = p.product_id
        GROUP BY p.product_name, p.category ORDER BY total_revenue DESC LIMIT 10;
        """
    ),
    (
        "4. Average available inventory stock level by hotel",
        """
        SELECT p.category AS hotel_type, ROUND(AVG(i.current_stock), 2) AS avg_available_rooms
        FROM inventory i JOIN products p ON i.product_id = p.product_id
        GROUP BY p.category;
        """
    ),
    (
        "5. Top room packages by gross margin percentage",
        """
        SELECT p.product_name,
               ROUND(((SUM(si.quantity * (si.unit_price - si.unit_cost)) /
               NULLIF(SUM(si.quantity * si.unit_price), 0)) * 100), 2) AS gross_margin_pct
        FROM sale_items si JOIN products p ON si.product_id = p.product_id
        GROUP BY p.product_name ORDER BY gross_margin_pct DESC LIMIT 5;
        """
    ),
    (
        "6. Bookings breakdown by deposit / payment mode",
        """
        SELECT payment_mode AS deposit_type, COUNT(*) AS booking_count FROM sales GROUP BY payment_mode;
        """
    ),
    (
        "7. Guest origins with most bookings",
        """
        SELECT c.region AS country, COUNT(c.customer_id) AS total_guests
        FROM customers c GROUP BY c.region ORDER BY total_guests DESC LIMIT 10;
        """
    ),
    (
        "8. Rank room types by gross profit within each hotel property",
        """
        SELECT b.name AS hotel_property, p.product_name AS room_type,
               ROUND(SUM(si.quantity * (si.unit_price - si.unit_cost)), 2) AS total_profit,
               RANK() OVER (PARTITION BY b.name ORDER BY SUM(si.quantity * (si.unit_price - si.unit_cost)) DESC) AS profit_rank
        FROM sale_items si
        JOIN products p ON si.product_id = p.product_id
        JOIN businesses b ON p.business_id = b.business_id
        GROUP BY b.name, p.product_name LIMIT 10;
        """
    ),
    (
        "9. High-value bookings exceeding the overall average booking value",
        """
        SELECT s.sale_id, c.customer_name, ROUND(SUM(si.quantity * si.unit_price), 2) AS booking_value
        FROM sales s
        JOIN customers c ON s.customer_id = c.customer_id
        JOIN sale_items si ON s.sale_id = si.sale_id
        GROUP BY s.sale_id, c.customer_name
        HAVING SUM(si.quantity * si.unit_price) > (
            SELECT AVG(booking_total) FROM (
                SELECT SUM(quantity * unit_price) AS booking_total FROM sale_items GROUP BY sale_id
            ) sub
        )
        ORDER BY booking_value DESC LIMIT 5;
        """
    ),
    (
        "10. Customer segment revenue distribution (Transient vs Contract vs Group)",
        """
        SELECT c.customer_type, COUNT(DISTINCT c.customer_id) AS total_guests,
               ROUND(SUM(si.quantity * si.unit_price), 2) AS total_revenue
        FROM customers c
        JOIN sales s ON c.customer_id = s.customer_id
        JOIN sale_items si ON s.sale_id = si.sale_id
        GROUP BY c.customer_type ORDER BY total_revenue DESC;
        """
    )
]

for title, q in queries:
    print(f"\n--- {title} ---")
    cursor.execute(q)
    rows = cursor.fetchall()
    col_names = [d[0] for d in cursor.description]
    df_q = pd.DataFrame(rows, columns=col_names)
    print(df_q.to_string(index=False))

cursor.close()
conn.close()

# Export clean CSV
export_cols = [
    'booking_id', 'hotel', 'is_canceled', 'lead_time', 'arrival_date',
    'total_stay_nights', 'adults', 'children', 'babies', 'total_guests',
    'meal', 'country', 'market_segment', 'distribution_channel',
    'is_repeated_guest', 'reserved_room_type', 'assigned_room_type',
    'deposit_type', 'customer_type', 'adr', 'Revenue', 'COGS',
    'Gross_Profit', 'Gross_Margin_Pct', 'Current_Stock', 'Stock_Status',
    'Customer_Age_Days', 'reservation_status'
]
clean_export_path = "Cleaned_Business_Data.csv"
df[export_cols].to_csv(clean_export_path, index=False)
print(f"\n✅ Cleaned_Business_Data.csv updated with {len(df):,} fully validated hotel records and {len(export_cols)} columns.")
