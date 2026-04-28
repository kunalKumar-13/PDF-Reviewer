"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# --- Model Configuration ---
GENERATION_MODEL: str = "llama-3.3-70b-versatile"

# --- Chunking Configuration ---
CHUNK_SIZE: int = 800        # characters per chunk
CHUNK_OVERLAP: int = 200     # overlap between consecutive chunks
TOP_K_RESULTS: int = 5       # number of relevant chunks to retrieve per query

# --- Storage ---
STORE_DIR: str = os.path.join(os.path.dirname(__file__), "store")

# --- Upload Configuration ---
UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "uploads")
MAX_FILE_SIZE_MB: int = 50

# --- CORS ---
FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
FRONTEND_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", FRONTEND_ORIGIN).split(",")
    if origin.strip()
]
CORS_ORIGIN_REGEX: str = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"https://.*\.vercel\.app",
)

# --- Server ---
HOST: str = "0.0.0.0"
PORT: int = 8000
