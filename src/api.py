from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from src.config import BASE_DIR, HOST, PORT
from src.assistant import BIAssistant
from src.database import get_schema_summary, get_connection
from src.ingestion import IngestionPipeline

app = FastAPI(
    title="Mini AI Business Intelligence Assistant API",
    description="Natural language to deterministic SQL engine for sales analytics",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = BIAssistant()

# Mount static frontend assets
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

class QueryRequest(BaseModel):
    question: str = Field(..., json_schema_extra={"example": "What is the total revenue?"}, min_length=1)

class QueryResponse(BaseModel):
    status: str
    question: str
    intent: Optional[str] = None
    sql_query: Optional[str] = None
    answer: Optional[str] = None
    explanation: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    chart_config: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None
    engine_mode: Optional[str] = None
    error: Optional[str] = None
    security_flag: Optional[bool] = None
    supported_examples: Optional[List[str]] = None

@app.get("/")
async def serve_root():
    """Serves the main BI Assistant interactive Web UI."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Mini AI BI Assistant API is running. UI index.html not found."}

@app.get("/api/health")
async def health_check():
    """System health check endpoint."""
    return {"status": "healthy", "service": "Mini AI BI Assistant"}

@app.post("/api/query", response_model=QueryResponse)
async def process_user_query(req: QueryRequest):
    """
    Translates a natural language question into validated SQL, executes it,
    and returns deterministic answers and charts.
    """
    result = assistant.ask(req.question)
    return JSONResponse(content=result)

@app.get("/api/kpis")
async def get_overview_kpis():
    """Calculates top-level KPI summary cards for the sales dashboard."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Total Net Revenue & Orders
        cur.execute("""
            SELECT 
                SUM(CASE WHEN status = 'Completed' THEN net_revenue ELSE 0 END) AS total_revenue,
                SUM(gross_revenue) AS gross_revenue,
                COUNT(CASE WHEN status = 'Completed' THEN 1 END) AS completed_orders,
                COUNT(CASE WHEN status = 'Returned' THEN 1 END) AS returned_orders,
                SUM(CASE WHEN status = 'Completed' THEN quantity ELSE 0 END) AS total_units
            FROM sales;
        """)
        totals = dict(cur.fetchone())

        # Top Product
        cur.execute("""
            SELECT product, SUM(net_revenue) as rev
            FROM sales
            WHERE status = 'Completed'
            GROUP BY product
            ORDER BY rev DESC LIMIT 1;
        """)
        top_prod_row = cur.fetchone()
        top_product = {"name": top_prod_row["product"], "revenue": top_prod_row["rev"]} if top_prod_row else {}

        # Top Region
        cur.execute("""
            SELECT region, SUM(net_revenue) as rev
            FROM sales
            WHERE status = 'Completed'
            GROUP BY region
            ORDER BY rev DESC LIMIT 1;
        """)
        top_reg_row = cur.fetchone()
        top_region = {"name": top_reg_row["region"], "revenue": top_reg_row["rev"]} if top_reg_row else {}

        # Peak Month
        cur.execute("""
            SELECT order_month, SUM(net_revenue) as rev
            FROM sales
            WHERE status = 'Completed'
            GROUP BY order_month
            ORDER BY rev DESC LIMIT 1;
        """)
        peak_m_row = cur.fetchone()
        peak_month = {"month": peak_m_row["order_month"], "revenue": peak_m_row["rev"]} if peak_m_row else {}

        aov = totals["total_revenue"] / totals["completed_orders"] if totals["completed_orders"] else 0.0

        return {
            "total_revenue": totals["total_revenue"],
            "gross_revenue": totals["gross_revenue"],
            "completed_orders": totals["completed_orders"],
            "returned_orders": totals["returned_orders"],
            "total_units_sold": totals["total_units"],
            "average_order_value": round(aov, 2),
            "top_product": top_product,
            "top_region": top_region,
            "peak_month": peak_month
        }
    finally:
        conn.close()

@app.get("/api/sample-queries")
async def get_sample_queries():
    """Returns the list of recommended questions covering challenge requirements."""
    return {"questions": assistant.get_sample_questions()}

@app.get("/api/schema")
async def get_schema():
    """Introspects the sales table schema and distinct categories."""
    return get_schema_summary()

@app.post("/api/reingest")
async def trigger_reingest():
    """Triggers the ETL ingestion pipeline to reload and clean sales data."""
    pipeline = IngestionPipeline()
    report = pipeline.run()
    return report

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host=HOST, port=PORT, reload=True)
