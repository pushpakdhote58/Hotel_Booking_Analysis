"""
FastAPI backend for Hotel Booking & Customer Reservation Analysis.
Queries MySQL hotel_bookings_db.hotel_bookings table for live data.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import mysql.connector
from mysql.connector import pooling
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------
app = FastAPI(title="Hotel Booking Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# MySQL connection pool
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "root",
    "database": "hotel_bookings_db",
    "port": 3306,
}

pool = pooling.MySQLConnectionPool(
    pool_name="hotel_pool",
    pool_size=5,
    pool_reset_session=True,
    **DB_CONFIG,
)


@contextmanager
def get_db():
    """Yield a cursor from the pool; auto-close connection afterwards."""
    conn = pool.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
    finally:
        cursor.close()
        conn.close()


# ===========================================================================
# 1. Health check
# ===========================================================================
@app.get("/api/health")
def health():
    try:
        with get_db() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ===========================================================================
# 2. KPIs
# ===========================================================================
@app.get("/api/kpis")
def kpis(hotel: Optional[str] = None, year: Optional[int] = None):
    where_parts = []
    params = []
    if hotel and hotel != "all":
        where_parts.append("hotel = %s")
        params.append(hotel)
    if year and year != 0:
        where_parts.append("arrival_date_year = %s")
        params.append(year)
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    with get_db() as cur:
        cur.execute(f"""
            SELECT
                COUNT(*)                                          AS total_bookings,
                ROUND(SUM(CASE WHEN is_canceled = 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100, 2)
                                                                  AS occupancy_rate,
                SUM(revenue)                                      AS total_revenue,
                ROUND(AVG(total_stay_nights), 2)                  AS avg_stay_duration,
                ROUND(SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100, 2)
                                                                  AS cancellation_rate,
                ROUND(AVG(adr), 2)                                AS avg_room_price
            FROM hotel_bookings
            {where_sql}
        """, tuple(params))
        row = cur.fetchone()
    return {k: float(v) if v is not None else 0 for k, v in row.items()}


# ===========================================================================
# 3. Monthly booking trends
# ===========================================================================
MONTH_ORDER = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


@app.get("/api/trends/monthly")
def trends_monthly(hotel: Optional[str] = None, year: Optional[int] = None):
    where_parts = []
    params = []
    if hotel and hotel != "all":
        where_parts.append("hotel = %s")
        params.append(hotel)
    if year and year != 0:
        where_parts.append("arrival_date_year = %s")
        params.append(year)
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    with get_db() as cur:
        cur.execute(f"""
            SELECT
                arrival_date_year                                 AS year,
                arrival_date_month                                AS month,
                COUNT(*)                                          AS total_bookings,
                SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) AS cancellations,
                ROUND(AVG(adr), 2)                                AS avg_adr,
                ROUND(SUM(revenue), 2)                            AS monthly_revenue
            FROM hotel_bookings
            {where_sql}
            GROUP BY arrival_date_year, arrival_date_month
            ORDER BY arrival_date_year,
                     FIELD(arrival_date_month,
                           'January','February','March','April','May','June',
                           'July','August','September','October','November','December')
        """, tuple(params))
        rows = cur.fetchall()
    return [
        {k: float(v) if isinstance(v, (int, float)) and k != "year" and k != "month"
         else (int(v) if k == "year" else v)
         for k, v in r.items()}
        for r in rows
    ]


# ===========================================================================
# 4. Hotels — revenue & bookings by hotel type
# ===========================================================================
@app.get("/api/hotels")
def hotels():
    with get_db() as cur:
        cur.execute("""
            SELECT
                hotel,
                COUNT(*)                                          AS total_bookings,
                ROUND(SUM(revenue), 2)                            AS total_revenue,
                ROUND(AVG(adr), 2)                                AS avg_adr,
                ROUND(SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2)
                                                                  AS cancellation_rate
            FROM hotel_bookings
            GROUP BY hotel
        """)
        rows = cur.fetchall()
    return [{k: float(v) if isinstance(v, (int, float)) and k != "hotel" else v
             for k, v in r.items()} for r in rows]


# ===========================================================================
# 5. Room type breakdown
# ===========================================================================
@app.get("/api/rooms")
def rooms():
    with get_db() as cur:
        cur.execute("""
            SELECT
                reserved_room_type                                AS room_type,
                COUNT(*)                                          AS count,
                ROUND(AVG(adr), 2)                                AS avg_adr,
                ROUND(SUM(revenue), 2)                            AS total_revenue
            FROM hotel_bookings
            GROUP BY reserved_room_type
            ORDER BY count DESC
        """)
        rows = cur.fetchall()
    return [{k: float(v) if isinstance(v, (int, float)) and k != "room_type" else v
             for k, v in r.items()} for r in rows]


# ===========================================================================
# 6. Booking channel distribution
# ===========================================================================
@app.get("/api/channels")
def channels():
    with get_db() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM hotel_bookings")
        total = cur.fetchone()["total"]

        cur.execute("""
            SELECT
                distribution_channel                              AS channel,
                COUNT(*)                                          AS count,
                ROUND(COUNT(*) / %s * 100, 2)                     AS percentage,
                ROUND(SUM(revenue), 2)                            AS revenue
            FROM hotel_bookings
            GROUP BY distribution_channel
            ORDER BY count DESC
        """, (total,))
        rows = cur.fetchall()
    return [{k: float(v) if isinstance(v, (int, float)) and k != "channel" else v
             for k, v in r.items()} for r in rows]


# ===========================================================================
# 7. Top 20 customer nationalities
# ===========================================================================
@app.get("/api/nationalities")
def nationalities():
    with get_db() as cur:
        cur.execute("SELECT SUM(total_guests) AS grand_total FROM hotel_bookings")
        grand_total = cur.fetchone()["grand_total"] or 1

        cur.execute("""
            SELECT
                country,
                SUM(total_guests)                                 AS guest_count,
                ROUND(SUM(total_guests) / %s * 100, 2)           AS share_pct
            FROM hotel_bookings
            GROUP BY country
            ORDER BY guest_count DESC
            LIMIT 20
        """, (float(grand_total),))
        rows = cur.fetchall()
    return [{k: float(v) if isinstance(v, (int, float)) and k != "country" else v
             for k, v in r.items()} for r in rows]


# ===========================================================================
# 8. Cancellation analysis
# ===========================================================================
@app.get("/api/cancellations")
def cancellations():
    result = {}
    with get_db() as cur:
        # By hotel
        cur.execute("""
            SELECT
                hotel,
                COUNT(*)                                          AS total,
                SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) AS canceled,
                ROUND(SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2)
                                                                  AS cancel_rate
            FROM hotel_bookings
            GROUP BY hotel
        """)
        result["by_hotel"] = [
            {k: float(v) if isinstance(v, (int, float)) and k != "hotel" else v
             for k, v in r.items()} for r in cur.fetchall()
        ]

        # By deposit type
        cur.execute("""
            SELECT
                deposit_type,
                COUNT(*)                                          AS total,
                SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) AS canceled,
                ROUND(SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2)
                                                                  AS cancel_rate
            FROM hotel_bookings
            GROUP BY deposit_type
        """)
        result["by_deposit_type"] = [
            {k: float(v) if isinstance(v, (int, float)) and k != "deposit_type" else v
             for k, v in r.items()} for r in cur.fetchall()
        ]

        # By customer type
        cur.execute("""
            SELECT
                customer_type,
                COUNT(*)                                          AS total,
                SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) AS canceled,
                ROUND(SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2)
                                                                  AS cancel_rate
            FROM hotel_bookings
            GROUP BY customer_type
        """)
        result["by_customer_type"] = [
            {k: float(v) if isinstance(v, (int, float)) and k != "customer_type" else v
             for k, v in r.items()} for r in cur.fetchall()
        ]

    return result


# ===========================================================================
# 9. Customer segment analysis
# ===========================================================================
@app.get("/api/segments")
def segments():
    with get_db() as cur:
        cur.execute("""
            SELECT
                customer_type,
                COUNT(*)                                          AS count,
                ROUND(SUM(revenue), 2)                            AS revenue,
                ROUND(AVG(total_stay_nights), 2)                  AS avg_stay
            FROM hotel_bookings
            GROUP BY customer_type
            ORDER BY count DESC
        """)
        rows = cur.fetchall()
    return [{k: float(v) if isinstance(v, (int, float)) and k != "customer_type" else v
             for k, v in r.items()} for r in rows]


# ===========================================================================
# 10. Seasonal analysis (aggregated across years)
# ===========================================================================
@app.get("/api/seasonal")
def seasonal():
    with get_db() as cur:
        cur.execute("""
            SELECT
                arrival_date_month                                AS month_name,
                COUNT(*)                                          AS bookings,
                ROUND(AVG(adr), 2)                                AS avg_adr,
                ROUND(SUM(revenue), 2)                            AS revenue
            FROM hotel_bookings
            GROUP BY arrival_date_month
            ORDER BY FIELD(arrival_date_month,
                           'January','February','March','April','May','June',
                           'July','August','September','October','November','December')
        """)
        rows = cur.fetchall()
    return [{k: float(v) if isinstance(v, (int, float)) and k != "month_name" else v
             for k, v in r.items()} for r in rows]


# ===========================================================================
# 11. Stay duration distribution
# ===========================================================================
@app.get("/api/duration")
def duration():
    with get_db() as cur:
        cur.execute("""
            SELECT
                CASE
                    WHEN total_stay_nights >= 14 THEN '14+'
                    ELSE CAST(total_stay_nights AS CHAR)
                END                                               AS nights,
                COUNT(*)                                          AS count
            FROM hotel_bookings
            GROUP BY nights
            ORDER BY
                CASE WHEN nights = '14+' THEN 999
                     ELSE CAST(nights AS UNSIGNED) END
        """)
        rows = cur.fetchall()
    return [{k: float(v) if isinstance(v, (int, float)) and k != "nights" else v
             for k, v in r.items()} for r in rows]


# ===========================================================================
# 12. Lead time distribution (bucketed)
# ===========================================================================
@app.get("/api/lead-time")
def lead_time():
    with get_db() as cur:
        cur.execute("""
            SELECT
                CASE
                    WHEN lead_time BETWEEN 0   AND 7   THEN '0-7'
                    WHEN lead_time BETWEEN 8   AND 30  THEN '8-30'
                    WHEN lead_time BETWEEN 31  AND 90  THEN '31-90'
                    WHEN lead_time BETWEEN 91  AND 180 THEN '91-180'
                    WHEN lead_time BETWEEN 181 AND 365 THEN '181-365'
                    ELSE '365+'
                END                                               AS bucket,
                COUNT(*)                                          AS count,
                ROUND(SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2)
                                                                  AS cancel_rate
            FROM hotel_bookings
            GROUP BY bucket
            ORDER BY FIELD(bucket, '0-7','8-30','31-90','91-180','181-365','365+')
        """)
        rows = cur.fetchall()
    return [{k: float(v) if isinstance(v, (int, float)) and k != "bucket" else v
             for k, v in r.items()} for r in rows]


# ===========================================================================
# Static files & Directories
# ===========================================================================
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
REPORTS_DIR  = Path(__file__).resolve().parent.parent / "reports"
CHARTS_DIR   = Path(__file__).resolve().parent.parent / "charts"


@app.get("/")
def serve_root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Frontend not found. Place index.html in ../frontend/"}


# Mount reports directory for PDF viewing
if REPORTS_DIR.exists():
    app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

# Mount charts directory for image viewing
if CHARTS_DIR.exists():
    app.mount("/charts", StaticFiles(directory=str(CHARTS_DIR)), name="charts")

# Mount static frontend files AFTER API routes
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
