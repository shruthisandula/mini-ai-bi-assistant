import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from src.config import CSV_PATH, DB_PATH
from src.database import init_database, get_connection

def parse_date(date_str: str) -> Tuple[str, str, int, int]:
    """
    Parses DD-MM-YYYY date format and returns (YYYY-MM-DD, YYYY-MM, year, month).
    """
    dt = datetime.strptime(date_str.strip(), "%d-%m-%Y")
    return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m"), dt.year, dt.month

class IngestionPipeline:
    def __init__(self, csv_path: Path = CSV_PATH, db_path: Path = DB_PATH):
        self.csv_path = csv_path
        self.db_path = db_path
        self.audit_log: List[str] = []

    def run(self) -> Dict[str, Any]:
        """
        Runs the ETL pipeline: Read CSV -> Validate & Clean -> Impute -> Load SQLite.
        """
        init_database(self.db_path)

        if not self.csv_path.exists():
            raise FileNotFoundError(f"Sales CSV not found at: {self.csv_path}")

        records = []
        # First pass to build product price lookup for imputation
        product_prices: Dict[str, List[float]] = {}
        with open(self.csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            raw_rows = list(reader)

        for row in raw_rows:
            prod = row["Product"].strip()
            price_raw = row["Unit_price"].strip()
            if price_raw:
                try:
                    price_val = float(price_raw)
                    product_prices.setdefault(prod, []).append(price_val)
                except ValueError:
                    pass

        # Calculate standard unit price for each product (mode / median)
        product_catalog_price: Dict[str, float] = {}
        for prod, prices in product_prices.items():
            if prices:
                # Use most common price
                product_catalog_price[prod] = max(set(prices), key=prices.count)

        total_rows = len(raw_rows)
        imputed_count = 0
        returned_count = 0
        zero_qty_count = 0

        # Second pass: clean, transform, and load
        for idx, row in enumerate(raw_rows, 1):
            txn_id = row["Transaction_Id"].strip()
            date_raw = row["Order_date"].strip()
            product = row["Product"].strip()
            category = row["Category"].strip()
            region = row["Region"].strip()
            channel = row["Sales_channel"].strip()
            qty_raw = row["Quantity"].strip()
            price_raw = row["Unit_price"].strip()
            discount_raw = row["Discount_amount"].strip()
            status = row["Status"].strip()

            # Date formatting to ISO-8601 YYYY-MM-DD
            iso_date, order_month, year, month = parse_date(date_raw)

            # Quantity handling
            quantity = int(qty_raw)
            if quantity == 0:
                zero_qty_count += 1
                self.audit_log.append(f"Row {idx} ({txn_id}): Quantity is 0 for {product}. Net revenue will be 0.")

            # Price handling & imputation
            is_imputed = 0
            if not price_raw or price_raw.lower() == "nan":
                if product in product_catalog_price:
                    unit_price = product_catalog_price[product]
                    is_imputed = 1
                    imputed_count += 1
                    self.audit_log.append(
                        f"Row {idx} ({txn_id}): Missing unit price for '{product}'. "
                        f"Imputed with catalog price {unit_price:.2f}."
                    )
                else:
                    raise ValueError(f"Missing price for unknown product '{product}' in {txn_id}")
            else:
                unit_price = float(price_raw)

            # Discount handling
            discount_amount = float(discount_raw) if discount_raw else 0.0

            # Revenue calculations
            gross_revenue = quantity * unit_price
            net_revenue = max(0.0, gross_revenue - discount_amount)

            if status.lower() == "returned":
                returned_count += 1
                self.audit_log.append(
                    f"Row {idx} ({txn_id}): Status is 'Returned'. "
                    f"Product: {product}, gross value: {gross_revenue}."
                )

            records.append((
                txn_id, iso_date, order_month, year, month, product, category,
                region, channel, quantity, unit_price, discount_amount,
                gross_revenue, net_revenue, status, is_imputed
            ))

        # Insert records into SQLite (upsert / replace)
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sales;")  # clean slate for idempotent ingestion
        cursor.executemany("""
        INSERT INTO sales (
            transaction_id, order_date, order_month, year, month, product, category,
            region, sales_channel, quantity, unit_price, discount_amount,
            gross_revenue, net_revenue, status, is_imputed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, records)
        conn.commit()
        conn.close()

        # Compute summary stats
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT SUM(net_revenue) as net_rev FROM sales WHERE status = 'Completed';")
        total_net_rev = cur.fetchone()["net_rev"]
        cur.execute("SELECT MIN(order_date) as start_d, MAX(order_date) as end_d FROM sales;")
        date_span = cur.fetchone()
        conn.close()

        return {
            "status": "success",
            "total_records_processed": total_rows,
            "records_inserted": len(records),
            "imputed_records": imputed_count,
            "returned_records": returned_count,
            "zero_quantity_records": zero_qty_count,
            "total_completed_net_revenue": total_net_rev,
            "date_range": f"{date_span['start_d']} to {date_span['end_d']}",
            "audit_log": self.audit_log
        }

if __name__ == "__main__":
    pipeline = IngestionPipeline()
    report = pipeline.run()
    print("=== INGESTION REPORT ===")
    for k, v in report.items():
        if k != "audit_log":
            print(f"{k}: {v}")
    print("\nAudit Log Details:")
    for item in report["audit_log"]:
        print(f" - {item}")
