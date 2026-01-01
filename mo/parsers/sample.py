"""Sample file detection compatible with Jellyfin.

Based on Jellyfin's sample file filtering logic.

Jellyfin uses sample detection to automatically filter out promotional
sample files during library scanning. This prevents sample files from
appearing in the media library alongside actual content.
"""

import re
from pathlib import Path


_SAMPLE_PATTERN = re.compile(r"(?:^|[^a-z])sample(?:[^a-z]|$)", re.IGNORECASE)


def is_sample_file(filename: str) -> bool:
    """
    Check if a filename indicates a sample file.

    Jellyfin ignores files matching the pattern \bsample\b (case-insensitive).
    This matches the word "sample" with word boundaries, so:
    - "sample.mkv" matches
    - "movie-sample.mkv" matches
    - "sample-scene.mkv" matches
    - "samplesize.txt" does NOT match (no word boundary)

    Args:
        filename: Filename to check (can include path)

    Returns:
        bool: True if filename appears to be a sample file

    Examples:
        >>> is_sample_file("sample.mkv")
        True

        >>> is_sample_file("Movie-sample.mkv")
        True

        >>> is_sample_file("Movie Sample Scene.mkv")
        True

        >>> is_sample_file("samplesize.txt")
        False

        >>> is_sample_file("Movie.mkv")
        False
    """
    # Extract filename without path
    path = Path(filename)
    name = path.name

    # Check for sample pattern
    return _SAMPLE_PATTERN.search(name) is not None


def filter_sample_files(filenames: list[str]) -> list[str]:
    """
    Filter out sample files from a list of filenames.

    Args:
        filenames: List of filenames

    Returns:
        List[str]: Filtered list without sample files

    Examples:
        >>> filter_sample_files(["movie.mkv", "sample.mkv", "movie-sample.mkv"])
        ['movie.mkv']
    """
    return [f for f in filenames if not is_sample_file(f)]


def detect_sample_files(filenames: list[str]) -> list[str]:
    """
    Detect sample files from a list of filenames.

    Args:
        filenames: List of filenames

    Returns:
        List[str]: List of sample files

    Examples:
        >>> detect_sample_files(["movie.mkv", "sample.mkv", "movie-sample.mkv"])
        ['sample.mkv', 'movie-sample.mkv']
    """
    return [f for f in filenames if is_sample_file(f)]
