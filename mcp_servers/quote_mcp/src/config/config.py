import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR / ".env")

API_BASE_URL = os.getenv("QUOTE_API_URL")
API_USERNAME = os.getenv("QUOTE_API_USERNAME")
API_PASSWORD = os.getenv("QUOTE_API_PASSWORD")
GET_PRICE_API = os.getenv("GET_PRICE_API")

if not GET_PRICE_API:
    raise ValueError("GET_PRICE_API is missing from .env")
