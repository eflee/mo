"""Season folder detection compatible with Jellyfin.

Based on Jellyfin's season folder recognition logic.
"""

import re
from pathlib import Path
from typing import Optional


# Season folder pattern (DRY - compile once)
# Jellyfin recognizes "Season ##" format (with or without leading zeros)
# NOT abbreviated formats like "S01"
_SEASON_FOLDER_PATTERN = re.compile(
    r"""
    ^                           # Start of string
    season                      # Literal "season"
    \s*                         # Optional whitespace
    (?P<season>\d{1,4})         # Season number (1-4 digits)
    $                           # End of string
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Special season names
_SPECIALS_NAMES = {
    "specials",
    "special",
    "extras",
    "extra",
    "season 0",
    "season0",
}


def is_season_folder(folder_name: str) -> bool:
    """
    Check if a folder name represents a season folder.

    Single Responsibility: Only validates season folder naming.

    Jellyfin recognizes:
    - "Season ##" format (case-insensitive)
    - "Season 0" for specials
    - NOT abbreviated formats like "S01"

    Args:
        folder_name: Name of the folder (not full path)

    Returns:
        bool: True if folder name matches Jellyfin season format

    Examples:
        >>> is_season_folder("Season 01")
        True

        >>> is_season_folder("Season 1")
        True

        >>> is_season_folder("season 02")
        True

        >>> is_season_folder("S01")
        False

        >>> is_season_folder("Specials")
        True
    """
    # Clean folder name
    name = folder_name.strip().lower()

    # Check for special names
    if name in _SPECIALS_NAMES:
        return True

    # Check against season pattern
    match = _SEASON_FOLDER_PATTERN.match(name)
    return match is not None


def extract_season_number(folder_name: str) -> Optional[int]:
    """
    Extract season number from a folder name.

    Single Responsibility: Only extracts season number.

    Args:
        folder_name: Name of the folder

    Returns:
        int | None: Season number (0 for specials), or None if not a season folder

    Examples:
        >>> extract_season_number("Season 01")
        1

        >>> extract_season_number("Season 2")
        2

        >>> extract_season_number("Specials")
        0

        >>> extract_season_number("S01")
        None
    """
    # Clean folder name
    name = folder_name.strip().lower()

    # Check for specials
    if name in _SPECIALS_NAMES:
        return 0

    # Try to extract season number
    match = _SEASON_FOLDER_PATTERN.match(name)
    if match:
        return int(match.group("season"))

    return None


def format_season_folder_name(season_number: int) -> str:
    """
    Generate a Jellyfin-compatible season folder name.

    Single Responsibility: Only generates folder names.

    Args:
        season_number: Season number

    Returns:
        str: Formatted folder name (e.g., "Season 01", "Specials")

    Examples:
        >>> format_season_folder_name(1)
        'Season 01'

        >>> format_season_folder_name(0)
        'Specials'

        >>> format_season_folder_name(12)
        'Season 12'
    """
    if season_number == 0:
        return "Specials"

    # Zero-pad to 2 digits
    return f"Season {season_number:02d}"


def detect_season_from_path(path: Path) -> Optional[int]:
    """
    Detect season number from a path.

    Single Responsibility: Only detects season from directory structure.

    Checks parent directories for season folder names.

    Args:
        path: File or directory path

    Returns:
        int | None: Season number if found in path hierarchy

    Examples:
        >>> detect_season_from_path(Path("/shows/MyShow/Season 01/episode.mkv"))
        1

        >>> detect_season_from_path(Path("/shows/MyShow/Specials/extra.mkv"))
        0

        >>> detect_season_from_path(Path("/shows/MyShow/episode.mkv"))
        None
    """
    # Check current path and all parents
    current = path if path.is_dir() else path.parent

    for parent in [current] + list(current.parents):
        season_num = extract_season_number(parent.name)
        if season_num is not None:
            return season_num

    return None
