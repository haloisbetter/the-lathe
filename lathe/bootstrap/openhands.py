"""
OpenHands bootstrap adapter.

This module exists so OpenHands can be removed later
without refactoring the core of The Lathe.
"""

BOOTSTRAP_PROVIDER = "openhands"


def get_provider_name() -> str:
    return BOOTSTRAP_PROVIDER