import os
import re
import json
from typing import Dict, Any, Optional, Tuple, List
from src.config import GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY
from src.database import get_schema_summary

SYSTEM_PROMPT = """You are an expert AI Business Intelligence Assistant and SQL Engineer for a Sales Database.
Your goal is to translate user business questions into safe, deterministic SQLite queries.

DATABASE SCHEMA:
Table: sales
Columns:
- transaction_id (TEXT): Unique ID (e.g. TXN0001)
- order_date (DATE): ISO format 'YYYY-MM-DD' (Between 2026-01-03 and 2026-06-28)
- order_month (TEXT): 'YYYY-MM' (e.g. '2026-01', '2026-02')
- year (INTEGER): 2026
- month (INTEGER): 1 to 6
- product (TEXT): 'Desk', 'Keyboard', 'Laptop Stand', 'Monitor', 'Office Chair', 'USB-C Hub', 'Wireless Mouse'
- category (TEXT): 'Accessories', 'Electronics', 'Furniture'
- region (TEXT): 'East', 'North', 'South', 'West'
- sales_channel (TEXT): 'Online', 'Retail'
- quantity (INTEGER): Number of items ordered (>= 0)
- unit_price (REAL): Unit price in INR
- discount_amount (REAL): Discount deducted in INR
- gross_revenue (REAL): quantity * unit_price
- net_revenue (REAL): gross_revenue - discount_amount
- status (TEXT): 'Completed' or 'Returned'
- is_imputed (INTEGER): 1 if missing price was imputed, 0 otherwise

BUSINESS RULES:
1. Revenue Questions: Unless explicitly asking about gross sales or returns, always calculate net revenue on completed orders: WHERE status = 'Completed'.
2. Net Revenue formula: (quantity * unit_price) - discount_amount, or the precomputed `net_revenue` column.
3. Dates: The order_month is 'YYYY-MM'. For monthly trends, group by order_month ORDER BY order_month ASC.
4. Security: ONLY generate single SELECT queries. NEVER generate DROP, DELETE, UPDATE, INSERT, ALTER, or PRAGMA.
5. If the user asks a question unrelated to the sales database (e.g., weather, history, coding questions), output: {"error": "Out of scope. I can only assist with sales data questions."}

OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{
  "sql": "SELECT ...",
  "explanation": "Short plain English explanation of the query logic",
  "chart_type": "bar" | "line" | "doughnut" | "metric_card" | "table",
  "x_key": "column_for_x_axis",
  "y_key": "column_for_y_axis"
}
"""

FEW_SHOT_EXAMPLES = """
Example 1: "What is the total revenue?"
{
  "sql": "SELECT SUM(net_revenue) AS total_revenue, SUM(gross_revenue) AS gross_revenue, SUM(discount_amount) AS total_discounts FROM sales WHERE status = 'Completed';",
  "explanation": "Calculates net revenue, gross revenue, and total discounts for completed sales.",
  "chart_type": "metric_card",
  "x_key": "total_revenue",
  "y_key": "total_revenue"
}

Example 2: "Which product generated the highest revenue?"
{
  "sql": "SELECT product, SUM(net_revenue) AS total_revenue, SUM(quantity) AS units_sold FROM sales WHERE status = 'Completed' GROUP BY product ORDER BY total_revenue DESC LIMIT 1;",
  "explanation": "Ranks products by total net revenue to identify the top performer.",
  "chart_type": "bar",
  "x_key": "product",
  "y_key": "total_revenue"
}

Example 3: "What is the monthly revenue trend?"
{
  "sql": "SELECT order_month, SUM(net_revenue) AS monthly_revenue FROM sales WHERE status = 'Completed' GROUP BY order_month ORDER BY order_month ASC;",
  "explanation": "Aggregates net revenue chronologically by month.",
  "chart_type": "line",
  "x_key": "order_month",
  "y_key": "monthly_revenue"
}

Example 4: "Which region generated the highest sales?"
{
  "sql": "SELECT region, SUM(net_revenue) AS total_revenue, SUM(quantity) AS units_sold FROM sales WHERE status = 'Completed' GROUP BY region ORDER BY total_revenue DESC LIMIT 1;",
  "explanation": "Finds the region with highest net sales.",
  "chart_type": "bar",
  "x_key": "region",
  "y_key": "total_revenue"
}

Example 5: "How did revenue change between January and February?"
{
  "sql": "SELECT order_month, SUM(net_revenue) AS monthly_revenue FROM sales WHERE status = 'Completed' AND order_month IN ('2026-01', '2026-02') GROUP BY order_month ORDER BY order_month ASC;",
  "explanation": "Fetches revenue for January and February 2026 for comparative change analysis.",
  "chart_type": "bar",
  "x_key": "order_month",
  "y_key": "monthly_revenue"
}
"""

class LLMTextToSQL:
    """
    Vectorless RAG / Text-to-SQL Agent with LLM provider integrations (Gemini, Groq, OpenAI).
    """

    def __init__(self):
        self.gemini_key = GEMINI_API_KEY
        self.groq_key = GROQ_API_KEY
        self.openai_key = OPENAI_API_KEY

    def is_llm_available(self) -> bool:
        return bool(self.gemini_key or self.groq_key or self.openai_key)

    def generate_sql(self, user_question: str) -> Optional[Dict[str, Any]]:
        """
        Calls available LLM provider to translate user question into SQL.
        Returns parsed JSON dict or None if LLM is unavailable or fails.
        """
        if not self.is_llm_available():
            return None

        prompt = f"{SYSTEM_PROMPT}\n\nFEW-SHOT EXAMPLES:\n{FEW_SHOT_EXAMPLES}\n\nUSER QUESTION: {user_question}\n\nJSON Response:"

        # Try Google Gemini first
        if self.gemini_key:
            res = self._call_gemini(prompt)
            if res:
                return res

        # Try Groq
        if self.groq_key:
            res = self._call_groq(prompt)
            if res:
                return res

        # Try OpenAI
        if self.openai_key:
            res = self._call_openai(prompt)
            if res:
                return res

        return None

    def _call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return self._parse_json_response(response.text)
        except Exception as e:
            print(f"[LLM Warning] Gemini call failed: {e}")
            return None

    def _call_groq(self, prompt: str) -> Optional[Dict[str, Any]]:
        try:
            from groq import Groq
            client = Groq(api_key=self.groq_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            content = completion.choices[0].message.content
            return self._parse_json_response(content)
        except Exception as e:
            print(f"[LLM Warning] Groq call failed: {e}")
            return None

    def _call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            }
            resp = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return self._parse_json_response(content)
        except Exception as e:
            print(f"[LLM Warning] OpenAI call failed: {e}")
            return None
        return None

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError:
            # Try to extract JSON between first { and last }
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
        return None
