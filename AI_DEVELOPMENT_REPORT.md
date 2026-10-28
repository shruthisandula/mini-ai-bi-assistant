# Engineering Reflection & AI Development Report
**Project:** Mini AI Business Intelligence Assistant  
**Author:** Graduate Engineer Trainee Candidate  

---

### 1. Which AI tools were used?
For this project, I used **Cursor**, **Antigravity**, and **ChatGPT** as my primary AI coding assistants. I used them like a pair programmer to help me explore the sales dataset, scaffold the backend structure, brainstorm security edge cases, and write automated test cases.

In the application backend, I built a **Natural Language to SQL Engine** that translates plain English business questions into SQLite queries so it runs fast and reliably without needing any paid API key.

---

### 2. How was AI used during development?
I used AI at different stages of the development workflow:

1. **Architecture Planning:**  
   I discussed approaches with the AI for converting plain English questions into database queries. We chose a deterministic query generator for the core questions to guarantee 100% calculation accuracy and sub-3ms response times.

2. **Scaffolding Code:**  
   I used the AI assistant to quickly generate boilerplate code for FastAPI endpoints, Pydantic data models, and the SQLite connection helper. This helped me move much faster and focus on business logic.

3. **Security Scenarios:**  
   I used AI to brainstorm possible security risks, such as SQL injection attacks using semicolons (`;`) or comment tags (`--`). Using these ideas, I implemented a strict security validator that blocks any dangerous query.

4. **Writing Automated Tests:**  
   I used AI to help write 15 unit and integration test cases using `pytest` to test the challenge questions, missing price handling, and security protections.

5. **Frontend Interface:**  
   I used AI to help style a colorful, bright web interface with interactive Chart.js charts and summary metric cards.

---

### 3. Which problems were encountered?
When I inspected the raw sales CSV data (`ai_bi_assistant_sales_data - GET.csv`), I found several real-world data issues:

1. **Missing Unit Price in Row 51 (TXN0051):**  
   Row 51 had an order for `Laptop Stand` where the `Unit_price` was completely blank (`5,,0,Completed`). If unhandled, this crashed number conversion or gave null revenue.

2. **Returned Order in Row 33 (TXN0033):**  
   Row 33 was an order for 2 Monitors at ₹9,500 each (₹19,000 total), but the status was `Returned`. If an analytics system blindly adds up all sales, it inflates company revenue by ₹19,000.

3. **Zero Quantity in Row 34 (TXN0034):**  
   Row 34 had a quantity of `0` at price 900. While mathematically resulting in ₹0, it was an anomaly that needed clean handling.

4. **Date Formats (DD-MM-YYYY):**  
   The CSV used dates like `03-01-2026`. In SQLite, date functions like `strftime` and chronological sorting only work reliably when dates are formatted as ISO `YYYY-MM-DD`.

5. **AI Calculation Errors:**  
   Standard AI language models often make arithmetic mistakes when calculating sums from text.

---

### 4. How were they debugged and resolved?

1. **Automated Price Imputation (`src/ingestion.py`):**  
   Instead of deleting row 51 and losing data, I checked all other transactions for "Laptop Stand" and found every single one was priced at ₹1,200. During data loading, the pipeline automatically fills in ₹1,200 for row 51 and marks it with an audit flag (`is_imputed = 1`).

2. **Separating Net Revenue from Gross Sales:**  
   In the database, I separated gross sales from net revenue. For revenue calculations, I filter active sales with `WHERE status = 'Completed'` so returned orders are not counted as profit, and I explicitly mention the excluded ₹19,000 return in the answer.

3. **ISO Date Normalization:**  
   During CSV ingestion, I converted all dates to standard `YYYY-MM-DD` and added a clean `order_month` column (`YYYY-MM`) with indexes for fast monthly trend calculations.

4. **Security Filter (`src/security.py`):**  
   To prevent SQL injection or accidental database modification, I built a security validator:
   - Queries must strictly begin with `SELECT` or `WITH`.
   - Dangerous commands like `DROP`, `DELETE`, `UPDATE`, and `INSERT` are completely blocked.
   - Semicolons (`;`) and comments (`--`) are rejected to prevent query stacking.
   - Only the `sales` table can be queried.
   - A `LIMIT 100` clause is automatically added if not provided to prevent memory overload.

5. **Deterministic Database Calculations:**  
   All numbers shown to the user come directly from SQL execution in SQLite. The assistant only formats the numbers into English; it never invents or guesses numbers.

---

### 5. What would you improve with another day of work?

If I had another day to work on this project, I would add:

1. **Conversational Memory:**  
   Allow users to ask follow-up questions (e.g. asking *"Which region had highest sales?"* and then asking *"What was their best product?"* without having to repeat the region).

2. **Dynamic Chart Suggestions:**  
   Automatically choose the best chart type (bar, line, or pie) based on what the user asks.

3. **Query Caching:**  
   Store answers to common questions in memory so repeat questions load instantly in under 1ms.

4. **Role-Based Access Control:**  
   Add user logins so regional managers only see data for their specific territory.

5. **Excel and PDF Export:**  
   Add one-click download buttons to export executive summary reports as styled PDF or Excel files.
