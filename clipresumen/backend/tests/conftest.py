"""Pytest session setup.

Point the app at an in-memory SQLite database before any app module imports,
so the module-level engine in app.core.database can be created without a
Postgres driver. Real deployments use the Postgres DATABASE_URL from .env.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
