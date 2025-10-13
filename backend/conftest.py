"""Pytest configuration for backend tests."""
import os

# Default to SQLite for local and CI test environments unless explicitly overridden.
os.environ.setdefault("USE_SQLITE", "1")