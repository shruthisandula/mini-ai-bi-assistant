import sqlite3
from typing import List, Dict, Any, Tuple
from pathlib import Path
from src.config import DB_PATH

def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def init_database(db_path: Path = DB_PATH) -> None:
    """Initializes the database schema and indexes."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Create primary sales table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        transaction_id TEXT PRIMARY KEY,
        order_date DATE NOT NULL,
        order_month TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        product TEXT NOT NULL,
        category TEXT NOT NULL,
        region TEXT NOT NULL,
        sales_channel TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity >= 0),
        unit_price REAL NOT NULL CHECK(unit_price >= 0),
        discount_amount REAL NOT NULL DEFAULT 0.0 CHECK(discount_amount >= 0),
        gross_revenue REAL NOT NULL,
        net_revenue REAL NOT NULL,
        status TEXT NOT NULL,
        is_imputed INTEGER DEFAULT 0
    );
    """)

    # Create analytical view for clean monthly summaries
    cursor.execute("""
    CREATE VIEW IF NOT EXISTS v_monthly_sales AS
    SELECT 
        order_month,
        COUNT(*) AS total_transactions,
        SUM(CASE WHEN status = 'Completed' THEN quantity ELSE 0 END) AS total_units_sold,
        SUM(CASE WHEN status = 'Completed' THEN gross_revenue ELSE 0 END) AS total_gross_revenue,
        SUM(CASE WHEN status = 'Completed' THEN discount_amount ELSE 0 END) AS total_discount,
        SUM(CASE WHEN status = 'Completed' THEN net_revenue ELSE 0 END) AS total_net_revenue
    FROM sales
    GROUP BY order_month
    ORDER BY order_month ASC;
    """)

    # Create performance indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_order_date ON sales(order_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_order_month ON sales(order_month);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_category ON sales(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_region ON sales(region);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_status ON sales(status);")

    conn.commit()
    conn.close()

def execute_query(query: str, db_path: Path = DB_PATH) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Executes a read-only SQL query and returns (columns, records).
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        records = [dict(row) for row in rows]
        return columns, records
    finally:
        conn.close()

def get_schema_summary(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Returns database schema metadata for LLM prompt context and UI introspection."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(sales);")
        columns_info = [{"name": row["name"], "type": row["type"]} for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) AS count FROM sales;")
        total_rows = cursor.fetchone()["count"]

        cursor.execute("SELECT DISTINCT product FROM sales ORDER BY product;")
        products = [row["product"] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT region FROM sales ORDER BY region;")
        regions = [row["region"] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT category FROM sales ORDER BY category;")
        categories = [row["category"] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT sales_channel FROM sales ORDER BY sales_channel;")
        channels = [row["sales_channel"] for row in cursor.fetchall()]

        cursor.execute("SELECT MIN(order_date) as min_date, MAX(order_date) as max_date FROM sales;")
        date_range = dict(cursor.fetchone())

        return {
            "table_name": "sales",
            "columns": columns_info,
            "total_rows": total_rows,
            "products": products,
            "regions": regions,
            "categories": categories,
            "sales_channels": channels,
            "date_range": date_range
        }
    finally:
        conn.close()
