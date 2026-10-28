import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database & Data Paths
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CSV_CANDIDATE_PATHS = [
    DATA_DIR / "ai_bi_assistant_sales_data.csv",
    BASE_DIR / "JD and Assessment for GETs" / "ai_bi_assistant_sales_data - GET.csv",
    BASE_DIR / "ai_bi_assistant_sales_data - GET.csv",
]

CSV_PATH = None
for candidate in CSV_CANDIDATE_PATHS:
    if candidate.exists():
        CSV_PATH = candidate
        break

if not CSV_PATH:
    # Default to data dir path
    CSV_PATH = DATA_DIR / "ai_bi_assistant_sales_data.csv"

DB_PATH = DATA_DIR / "sales_bi.db"

# Server Configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8000))

# Optional LLM API Keys (Supports Gemini, Groq, or OpenAI)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
