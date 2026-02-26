"""Configuration loader for the Enterprise AI Assistant."""

import os
import yaml
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

# Load .env BEFORE any other imports that might need env vars
_project_root = Path(__file__).parent.parent
_env_paths = [
    _project_root / ".env",
    Path.cwd() / ".env",
    Path(".env"),
]

_env_loaded = False
for _env_path in _env_paths:
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=True)
        _env_loaded = True
        print(f"[CONFIG] Loaded .env from: {_env_path.absolute()}")
        break

if not _env_loaded:
    # Fine on HuggingFace Spaces where secrets are set as env vars
    pass

from logger.logging import get_logger
logger = get_logger(__name__)


class ConfigLoader:
    """Loads configuration from YAML files and environment variables."""

    def __init__(self, config_file: str = "config/config.yaml"):
        try:
            self.config_file = config_file
            self.config_data = self.load_config()
            logger.info("ConfigLoader initialized successfully")

        except Exception as e:
            error_msg = f"Error in ConfigLoader Class Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def load_config(self):
        """Load configuration from YAML file."""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r') as file:
                    return yaml.safe_load(file) or {}
            else:
                logger.warning(f"Config file {self.config_file} not found.")
                return {}

        except Exception as e:
            error_msg = f"Error loading configuration -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        try:
            keys = key.split('.')
            value = self.config_data

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value

        except Exception as e:
            logger.error(f"Error getting config key {key} -> {str(e)}")
            return default

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable (already loaded from .env file)."""
        try:
            return os.getenv(key, default)

        except Exception as e:
            logger.error(f"Error getting environment variable {key} -> {str(e)}")
            return default

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        try:
            key_mapping = {
                "groq": "GROQ_API_KEY",
            }

            env_key = key_mapping.get(provider.lower())
            if env_key:
                return self.get_env(env_key)
            else:
                logger.warning(f"Unknown provider: {provider}")
                return None

        except Exception as e:
            logger.error(f"Error getting API key for {provider} -> {str(e)}")
            return None

    def reload(self):
        """Reload configuration and .env file."""
        try:
            load_dotenv(override=True)
            self.config_data = self.load_config()
            logger.info("Configuration reloaded successfully")

        except Exception as e:
            error_msg = f"Error reloading configuration -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
