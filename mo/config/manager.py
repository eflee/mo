"""Configuration management with hierarchical loading.

Supports hierarchical configuration loading:
1. Local .mo.conf in current directory
2. User config in platform-specific config directory
3. Error if neither exists
"""

import configparser
from pathlib import Path
from typing import Any, Dict, List, Optional

from mo.utils.errors import ConfigError
from mo.utils.platform import get_user_config_dir

# Default configuration file names (DRY - single source of truth)
LOCAL_CONFIG_NAME = ".mo.conf"
USER_CONFIG_NAME = "config"


class Config:
    """
    Configuration manager with hierarchical loading.

    Single Responsibility: Manages configuration loading, accessing, and saving.

    Loads configuration from:
    1. Local .mo.conf in current directory (highest priority)
    2. User config directory (platform-specific)

    Raises ConfigError if no configuration file is found.
    """

    def __init__(self, local_path: Optional[Path] = None, user_path: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            local_path: Path to local config file (default: ./.mo.conf)
            user_path: Path to user config file (default: platform-specific)
        """
        self._parser = configparser.ConfigParser()
        self._local_path = local_path or Path.cwd() / LOCAL_CONFIG_NAME
        self._user_path = user_path or get_user_config_dir() / USER_CONFIG_NAME
        self._active_config_path: Optional[Path] = None

        self._load()

    def _load(self) -> None:
        """
        Load configuration from hierarchical sources.

        Single Responsibility: Only handles loading logic.

        Raises:
            ConfigError: If no configuration file is found
        """
        # Try local config first
        if self._local_path.exists():
            self._parser.read(self._local_path)
            self._active_config_path = self._local_path
            return

        # Try user config
        if self._user_path.exists():
            self._parser.read(self._user_path)
            self._active_config_path = self._user_path
            return

        # No config found - raise error
        raise ConfigError(
            f"No configuration file found. Please create one of:\n"
            f"  - Local: {self._local_path}\n"
            f"  - User:  {self._user_path}\n\n"
            f"See .mo.conf.example for a template."
        )

    def get(self, section: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """
        Get a configuration value.

        Single Responsibility: Only retrieves values.

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if not found

        Returns:
            str | None: Configuration value or fallback
        """
        return self._parser.get(section, key, fallback=fallback)

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """
        Get a boolean configuration value.

        Single Responsibility: Only retrieves boolean values.

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if not found

        Returns:
            bool: Configuration value or fallback
        """
        return self._parser.getboolean(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """
        Get an integer configuration value.

        Single Responsibility: Only retrieves integer values.

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if not found

        Returns:
            int: Configuration value or fallback
        """
        return self._parser.getint(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Single Responsibility: Only sets values (does not save).

        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        if not self._parser.has_section(section):
            self._parser.add_section(section)

        self._parser.set(section, key, str(value))

    def save(self, target: Optional[str] = None) -> None:
        """
        Save configuration to file.

        Single Responsibility: Only handles saving.

        Args:
            target: Target location ('local' or 'user'). If None, saves to active config.

        Raises:
            ConfigError: If target is invalid or no active config
        """
        if target == "local":
            save_path = self._local_path
        elif target == "user":
            save_path = self._user_path
        elif target is None:
            if self._active_config_path is None:
                raise ConfigError("No active configuration to save")
            save_path = self._active_config_path
        else:
            raise ConfigError(f"Invalid target '{target}'. Use 'local' or 'user'")

        # Ensure parent directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(save_path, "w") as f:
                self._parser.write(f)
        except OSError as e:
            raise ConfigError(f"Failed to save configuration to {save_path}: {e}")

    def get_libraries(self) -> Dict[str, str]:
        """
        Get all configured libraries.

        Single Responsibility: Only retrieves library configuration.

        Returns:
            Dict[str, str]: Dictionary mapping library names to paths
        """
        if not self._parser.has_section("libraries"):
            return {}

        return dict(self._parser.items("libraries"))

    def get_library_types(self) -> Dict[str, str]:
        """
        Get all library types.

        Single Responsibility: Only retrieves library type configuration.

        Returns:
            Dict[str, str]: Dictionary mapping library names to types ('movie' or 'show')
        """
        if not self._parser.has_section("library_types"):
            return {}

        return dict(self._parser.items("library_types"))

    def get_sections(self) -> List[str]:
        """
        Get all configuration sections.

        Returns:
            List[str]: List of section names
        """
        return self._parser.sections()

    def get_all(self, section: str) -> Dict[str, str]:
        """
        Get all key-value pairs in a section.

        Args:
            section: Configuration section

        Returns:
            Dict[str, str]: Dictionary of all keys and values in section
        """
        if not self._parser.has_section(section):
            return {}

        return dict(self._parser.items(section))

    def remove_library(self, name: str) -> None:
        """
        Remove a library from configuration.

        Single Responsibility: Only removes library entries.

        Args:
            name: Library name to remove
        """
        if self._parser.has_section("libraries") and self._parser.has_option("libraries", name):
            self._parser.remove_option("libraries", name)

        if self._parser.has_section("library_types") and self._parser.has_option(
            "library_types", name
        ):
            self._parser.remove_option("library_types", name)

    @property
    def config_path(self) -> Optional[Path]:
        """
        Get the active configuration file path.

        Returns:
            Path | None: Path to active config file
        """
        return self._active_config_path

    def __repr__(self) -> str:
        """String representation showing active config path."""
        return f"Config(active={self._active_config_path})"
