"""
FastAPI Application Configuration.
Reads environment variables from .env file for Supabase, Auth, and LLM integrations.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file if present
load_dotenv(find_dotenv())


@dataclass
class Settings:
    PROJECT_NAME: str = "AI Fitness Platform V1"
    API_V1_STR: str = "/api/v1"
    TESTING: bool = os.getenv("TESTING", "false").lower() in ("true", "1", "yes")

    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xyzcompany.supabase.co")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_anon_key")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-key-min-32-chars-long")

    # LLM Settings (Groq / NVIDIA NIM)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "llama-3.3-70b-versatile")


settings = Settings()
