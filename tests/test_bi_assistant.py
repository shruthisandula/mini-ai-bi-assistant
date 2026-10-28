import pytest
from src.assistant import BIAssistant
from src.security import SQLValidator
from src.ingestion import IngestionPipeline
from src.database import get_schema_summary, execute_query
from fastapi.testclient import TestClient
from src.api import app

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database is ingested and clean prior to tests."""
    pipeline = IngestionPipeline()
    pipeline.run()

@pytest.fixture
def assistant():
    return BIAssistant()

@pytest.fixture
def client():
    return TestClient(app)

# -------------------------------------------------------------
# 1. Ingestion & Data Quality Tests
# -------------------------------------------------------------
def test_etl_ingestion_and_cleaning():
    """Validates that dirty data (missing price, returned status, dates) is correctly cleaned and loaded."""
    pipeline = IngestionPipeline()
    report = pipeline.run()

    assert report["status"] == "success"
    assert report["records_inserted"] == 51
    assert report["imputed_records"] == 1
    assert report["returned_records"] == 1
    assert report["zero_quantity_records"] == 1
    assert report["total_completed_net_revenue"] == 1445200.0

    # Verify TXN0051 (Laptop Stand) was imputed to 1200.0
    _, rows = execute_query("SELECT unit_price, is_imputed FROM sales WHERE transaction_id = 'TXN0051';")
    assert len(rows) == 1
    assert rows[0]["unit_price"] == 1200.0
    assert rows[0]["is_imputed"] == 1

# -------------------------------------------------------------
# 2. Functional Challenge Questions Tests (Q1 - Q5)
# -------------------------------------------------------------
def test_q1_total_revenue(assistant):
    """Test Challenge Question 1: What is the total revenue?"""
    res = assistant.ask("What is the total revenue?")
    assert res["status"] == "success"
    assert "1,445,200" in res["answer"]
    assert res["row_count"] == 1
    assert res["rows"][0]["total_net_revenue"] == 1445200.0
    assert "sales" in res["sql_query"].lower()

def test_q2_highest_revenue_product(assistant):
    """Test Challenge Question 2: Which product generated the highest revenue?"""
    res = assistant.ask("Which product generated the highest revenue?")
    assert res["status"] == "success"
    assert "Monitor" in res["answer"]
    assert res["row_count"] == 1
    assert res["rows"][0]["product"] == "Monitor"
    assert res["rows"][0]["total_revenue"] == 473000.0

def test_q3_monthly_revenue_trend(assistant):
    """Test Challenge Question 3: What is the monthly revenue trend?"""
    res = assistant.ask("What is the monthly revenue trend?")
    assert res["status"] == "success"
    assert res["row_count"] == 6  # 6 months (Jan to Jun 2026)
    assert "May 2026" in res["answer"]  # Peak month
    assert res["chart_config"] is not None
    assert res["chart_config"]["type"] == "line"

def test_q4_highest_sales_region(assistant):
    """Test Challenge Question 4: Which region generated the highest sales?"""
    res = assistant.ask("Which region generated the highest sales?")
    assert res["status"] == "success"
    assert "South" in res["answer"]
    assert res["rows"][0]["region"] == "South"
    assert res["rows"][0]["total_revenue"] == 411200.0

def test_q5_revenue_change_between_months(assistant):
    """Test Challenge Question 5: How did revenue change between two months?"""
    res = assistant.ask("How did revenue change between January and February?")
    assert res["status"] == "success"
    assert res["row_count"] == 2
    assert "January 2026" in res["answer"]
    assert "February 2026" in res["answer"]
    assert "24,350" in res["answer"]
    assert "+11.58%" in res["answer"]

# -------------------------------------------------------------
# 3. Security Guardrail & Injection Tests
# -------------------------------------------------------------
def test_security_guardrail_destructive_drop():
    """Ensure DROP TABLE attempt is blocked by AST/Regex guardrail."""
    is_valid, _, err = SQLValidator.sanitize_and_validate("DROP TABLE sales;")
    assert is_valid is False
    assert "Security violation" in err

def test_security_guardrail_destructive_delete():
    """Ensure DELETE statement is blocked."""
    is_valid, _, err = SQLValidator.sanitize_and_validate("DELETE FROM sales WHERE region = 'North';")
    assert is_valid is False
    assert "Security violation" in err

def test_security_guardrail_query_chaining():
    """Ensure semicolon chaining is blocked."""
    is_valid, _, err = SQLValidator.sanitize_and_validate("SELECT * FROM sales; DROP TABLE sales;")
    assert is_valid is False
    assert "Multiple statements" in err

def test_security_guardrail_unauthorized_table():
    """Ensure queries against sqlite_master or non-whitelisted tables are rejected."""
    is_valid, _, err = SQLValidator.sanitize_and_validate("SELECT * FROM sqlite_master;")
    assert is_valid is False
    assert "Unauthorized table access" in err

# -------------------------------------------------------------
# 4. Invalid Questions & Edge Case Tests
# -------------------------------------------------------------
def test_invalid_out_of_scope_question(assistant):
    """Ensure out-of-scope questions receive clear guidance."""
    res = assistant.ask("What is the weather in Paris?")
    assert res["status"] == "error"
    assert "could not understand your question" in res["error"]
    assert len(res["supported_examples"]) > 0

def test_edge_case_empty_input(assistant):
    """Ensure empty or whitespace queries are safely rejected."""
    res = assistant.ask("   ")
    assert res["status"] == "error"
    assert "empty" in res["error"]

# -------------------------------------------------------------
# 5. FastAPI Integration Tests
# -------------------------------------------------------------
def test_api_health_endpoint(client):
    """Test /api/health."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_api_kpis_endpoint(client):
    """Test /api/kpis summary cards."""
    resp = client.get("/api/kpis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_revenue"] == 1445200.0
    assert data["completed_orders"] == 50
    assert data["top_product"]["name"] == "Monitor"

def test_api_query_endpoint(client):
    """Test POST /api/query."""
    resp = client.post("/api/query", json={"question": "What is the total revenue?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "total_net_revenue" in data["columns"]
