"""Movie filename parser compatible with Jellyfin.

Extracts title, year, and provider IDs from movie filenames and folder names.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from mo.parsers.provider_id import extract_provider_ids


@dataclass
class MovieInfo:
    """
    Parsed movie information from a filename or folder.

    Single Responsibility: Data structure for movie metadata.
    """

    title: str
    year: Optional[int] = None
    provider_ids: Optional[Dict[str, str]] = None
    is_dvd: bool = False
    is_bluray: bool = False


# Compiled regex patterns (DRY - compile once)

# Year pattern: (1900-2099) in parentheses or brackets
_YEAR_PATTERN = re.compile(
    r"""
    [\(\[]                      # Opening parenthesis or bracket
    (?P<year>19\d{2}|20\d{2})   # Year: 1900-2099
    [\)\]]                      # Closing parenthesis or bracket
    """,
    re.VERBOSE,
)

# DVD/BluRay folder patterns
_DVD_FOLDERS = {"VIDEO_TS", "AUDIO_TS"}
_BLURAY_FOLDERS = {"BDMV", "CERTIFICATE"}


def parse_movie_filename(filename: str) -> Optional[MovieInfo]:
    """
    Parse movie information from a filename or folder name.

    Single Responsibility: Only parses filename patterns.

    Extracts:
    - Title (before year or end of filename)
    - Year (if present in parentheses or brackets)
    - Provider IDs (if present in bracket notation)

    Args:
        filename: Movie filename or folder name

    Returns:
        MovieInfo | None: Parsed movie info, or None if unable to parse

    Examples:
        >>> parse_movie_filename("Inception (2010).mkv")
        MovieInfo(title="Inception", year=2010)

        >>> parse_movie_filename("The Matrix [1999] [imdbid-tt0133093].mkv")
        MovieInfo(title="The Matrix", year=1999, provider_ids={"imdb": "tt0133093"})

        >>> parse_movie_filename("SomeMovie.mkv")
        MovieInfo(title="SomeMovie", year=None)
    """
    # Extract filename without path and extension
    path = Path(filename)
    name = path.stem if path.suffix else path.name

    # Handle empty stem case (e.g., ".mkv")
    if not name or name.startswith("."):
        return None

    # Extract provider IDs first
    provider_ids = extract_provider_ids(name)

    # Try to extract year
    year_match = _YEAR_PATTERN.search(name)
    year = int(year_match.group("year")) if year_match else None

    # Extract title (everything before year or provider IDs)
    if year_match:
        # Title is everything before the year
        title = name[: year_match.start()].strip()
    else:
        # No year, title is everything before provider IDs or end of string
        title = name

    # Remove provider IDs from title
    for provider, pid in provider_ids.items():
        # Remove [providerid-value] patterns
        title = re.sub(rf"\[{provider}id-{re.escape(pid)}\]", "", title, flags=re.IGNORECASE)

    # Clean title
    title = _clean_title(title)

    if not title:
        return None

    return MovieInfo(title=title, year=year, provider_ids=provider_ids if provider_ids else None)


def _clean_title(title: str) -> str:
    """
    Clean movie title by removing common artifacts.

    Args:
        title: Raw title string

    Returns:
        str: Cleaned title
    """
    if not title:
        return ""

    # Replace common separators with spaces
    title = re.sub(r"[._-]+", " ", title)

    # Remove multiple spaces
    title = " ".join(title.split())

    # Strip whitespace
    title = title.strip()

    return title


def is_dvd_folder(path: Path) -> bool:
    """
    Check if a path is a DVD folder structure.

    Single Responsibility: Only checks for DVD structure.

    Args:
        path: Path to check

    Returns:
        bool: True if path contains DVD structure

    Examples:
        >>> is_dvd_folder(Path("/movies/Movie/VIDEO_TS"))
        True

        >>> is_dvd_folder(Path("/movies/Movie/"))
        False (unless it contains VIDEO_TS subfolder)
    """
    if not path.is_dir():
        path = path.parent

    # Check if current folder is a DVD folder
    if path.name in _DVD_FOLDERS:
        return True

    # Check if any child folder is a DVD folder
    try:
        for child in path.iterdir():
            if child.is_dir() and child.name in _DVD_FOLDERS:
                return True
    except (PermissionError, OSError):
        pass

    return False


def is_bluray_folder(path: Path) -> bool:
    """
    Check if a path is a BluRay folder structure.

    Single Responsibility: Only checks for BluRay structure.

    Args:
        path: Path to check

    Returns:
        bool: True if path contains BluRay structure

    Examples:
        >>> is_bluray_folder(Path("/movies/Movie/BDMV"))
        True

        >>> is_bluray_folder(Path("/movies/Movie/"))
        False (unless it contains BDMV subfolder)
    """
    if not path.is_dir():
        path = path.parent

    # Check if current folder is a BluRay folder
    if path.name in _BLURAY_FOLDERS:
        return True

    # Check if any child folder is a BluRay folder
    try:
        for child in path.iterdir():
            if child.is_dir() and child.name in _BLURAY_FOLDERS:
                return True
    except (PermissionError, OSError):
        pass

    return False


def parse_movie_folder(folder_path: Path) -> Optional[MovieInfo]:
    """
    Parse movie information from a folder.

    Single Responsibility: Only parses folder structure.

    Handles DVD/BluRay detection and uses folder name for metadata.

    Args:
        folder_path: Path to movie folder

    Returns:
        MovieInfo | None: Parsed movie info

    Examples:
        >>> parse_movie_folder(Path("/movies/Inception (2010)"))
        MovieInfo(title="Inception", year=2010)

        >>> parse_movie_folder(Path("/movies/Movie/VIDEO_TS"))
        MovieInfo(title="Movie", is_dvd=True)
    """
    if not folder_path.is_dir():
        folder_path = folder_path.parent

    # Check for DVD/BluRay structure
    is_dvd = is_dvd_folder(folder_path)
    is_br = is_bluray_folder(folder_path)

    # Use parent folder name if this is a DVD/BluRay structure folder
    if folder_path.name in _DVD_FOLDERS or folder_path.name in _BLURAY_FOLDERS:
        folder_path = folder_path.parent

    # Parse folder name
    info = parse_movie_filename(folder_path.name)

    if info:
        info.is_dvd = is_dvd
        info.is_bluray = is_br

    return info
