"""Configuration management for Danki application."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages application configuration with persistent storage."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".danki"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Return default config
        return {
            "api_key": None,
            "translation_language": "English",
            "allow_duplicates": True,
            "window_geometry": None
        }
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save."""
        self._config[key] = value
        self._save_config()
    
    def get_api_key(self) -> Optional[str]:
        """Get stored API key."""
        return self.get("api_key")
    
    def set_api_key(self, api_key: str) -> None:
        """Set and save API key."""
        self.set("api_key", api_key)
    
    def get_translation_language(self) -> str:
        """Get translation language."""
        return self.get("translation_language", "English")
    
    def set_translation_language(self, language: str) -> None:
        """Set translation language."""
        self.set("translation_language", language)


# Global config manager instance
config = ConfigManager()