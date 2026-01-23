"""
Storage module for The Lathe.

Handles all persistence operations using SQLite.

Responsibilities:
- Task storage and retrieval
- Run history tracking
- Schema management
- Database initialization

Does NOT contain:
- Business logic
- Task execution
- Configuration
"""

from .db import LatheDB

__all__ = ["LatheDB"]
