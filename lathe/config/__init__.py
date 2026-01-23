"""
Configuration module for The Lathe.

Handles loading and validation of configuration from YAML files.
"""

from .loader import ConfigLoader, LatheConfig

__all__ = ["ConfigLoader", "LatheConfig"]
