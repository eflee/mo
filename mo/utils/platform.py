"""Platform-specific helper functions."""

import sys
from pathlib import Path

from platformdirs import user_config_dir


def get_user_config_dir() -> Path:
    """
    Get the platform-specific user configuration directory.

    Returns:
        Path: User config directory
            - macOS: ~/Library/Application Support/mo
            - Linux: ~/.config/mo
            - Windows: %APPDATA%/mo
    """
    return Path(user_config_dir("mo", appauthor=False))


def get_platform_name() -> str:
    """
    Get the current platform name.

    Returns:
        str: Platform name ('darwin', 'linux', 'win32', etc.)
    """
    return sys.platform


def get_max_path_length() -> int:
    """
    Get the maximum path length for the current platform.

    Returns:
        int: Maximum path length in characters
            - Windows: 260 (unless long path support enabled)
            - macOS/Linux: 4096
    """
    if sys.platform == "win32":
        return 260
    return 4096
