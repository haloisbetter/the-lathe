"""
Configuration loader for The Lathe.

Loads configuration from YAML files with environment variable overrides.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "data/lathe.db"
    schema_path: str = "lathe/storage/schema.sql"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


@dataclass
class ExecutorConfig:
    """Executor configuration."""
    type: str = "openhands"
    timeout: int = 300
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LatheConfig:
    """
    Main configuration for The Lathe.

    All configuration is loaded from YAML files and can be overridden
    by environment variables.
    """
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LatheConfig":
        """Create config from dictionary."""
        return cls(
            database=DatabaseConfig(**data.get("database", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            executor=ExecutorConfig(**data.get("executor", {})),
        )


class ConfigLoader:
    """
    Loads configuration from YAML files with environment variable support.

    Search order:
    1. Path specified in LATHE_CONFIG environment variable
    2. ./lathe.yml
    3. ./lathe.yaml
    4. ~/.lathe/config.yml
    5. Default configuration
    """

    DEFAULT_PATHS = [
        Path("lathe.yml"),
        Path("lathe.yaml"),
        Path.home() / ".lathe" / "config.yml",
    ]

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> LatheConfig:
        """
        Load configuration from file or defaults.

        Args:
            config_path: Optional explicit path to config file

        Returns:
            LatheConfig instance
        """
        if config_path:
            return cls._load_from_path(config_path)

        env_path = os.environ.get("LATHE_CONFIG")
        if env_path:
            return cls._load_from_path(Path(env_path))

        for path in cls.DEFAULT_PATHS:
            if path.exists():
                return cls._load_from_path(path)

        return LatheConfig()

    @classmethod
    def _load_from_path(cls, path: Path) -> LatheConfig:
        """Load configuration from a specific path."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return LatheConfig.from_dict(data)

    @classmethod
    def save_example(cls, path: Path) -> None:
        """Save an example configuration file."""
        example = {
            "database": {
                "path": "data/lathe.db",
                "schema_path": "lathe/storage/schema.sql",
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": None,
            },
            "executor": {
                "type": "openhands",
                "timeout": 300,
                "options": {},
            },
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(example, f, default_flow_style=False, sort_keys=False)
