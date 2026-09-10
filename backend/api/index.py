"""
Vercel serverless entry point for FastAPI backend.
Vercel looks for api/index.py and serves it as a serverless function.
"""
import sys
import os

# Ensure the backend app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # noqa: F401 — Vercel uses this as the ASGI handler
