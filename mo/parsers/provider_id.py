"""Provider ID parsing and generation utilities.

Handles extraction and generation of Jellyfin-compatible provider IDs
in bracket notation (e.g., [imdbid-tt1234567], [tmdbid-12345]).
"""

import re
from typing import Dict, Optional

from mo.utils.errors import ValidationError

PROVIDER_PATTERNS = {
    "imdb": re.compile(r"\[imdbid-(tt\d+)\]", re.IGNORECASE),
    "tmdb": re.compile(r"\[tmdbid-(\d+)\]", re.IGNORECASE),
    "tvdb": re.compile(r"\[tvdbid-(\d+)\]", re.IGNORECASE),
}

PROVIDER_VALIDATORS = {
    "imdb": re.compile(r"^tt\d+$"),
    "tmdb": re.compile(r"^\d+$"),
    "tvdb": re.compile(r"^\d+$"),
}


def extract_provider_ids(path: str) -> Dict[str, str]:
    """
    Extract provider IDs from a path using bracket notation.


    Args:
        path: File or directory path containing provider IDs

    Returns:
        Dict[str, str]: Dictionary mapping provider names to IDs
            Example: {"imdb": "tt1234567", "tmdb": "12345"}

    Examples:
        >>> extract_provider_ids("Movie [imdbid-tt1234567]")
        {"imdb": "tt1234567"}
        >>> extract_provider_ids("Show [tmdbid-12345] [tvdbid-67890]")
        {"tmdb": "12345", "tvdb": "67890"}
    """
    provider_ids = {}

    for provider, pattern in PROVIDER_PATTERNS.items():
        match = pattern.search(path)
        if match:
            provider_ids[provider] = match.group(1)

    return provider_ids


def validate_provider_id(provider: str, provider_id: str) -> bool:
    """
    Validate a provider ID format.


    Args:
        provider: Provider name ('imdb', 'tmdb', 'tvdb')
        provider_id: The ID to validate

    Returns:
        bool: True if valid, False otherwise

    Examples:
        >>> validate_provider_id("imdb", "tt1234567")
        True
        >>> validate_provider_id("imdb", "1234567")
        False
        >>> validate_provider_id("tmdb", "12345")
        True
    """
    if provider not in PROVIDER_VALIDATORS:
        return False

    validator = PROVIDER_VALIDATORS[provider]
    return bool(validator.match(provider_id))


def format_provider_id(provider: str, provider_id: str) -> str:
    """
    Format a provider ID into Jellyfin bracket notation.


    Args:
        provider: Provider name ('imdb', 'tmdb', 'tvdb')
        provider_id: The provider ID

    Returns:
        str: Formatted provider ID in bracket notation

    Raises:
        ValidationError: If provider is unsupported or ID format is invalid

    Examples:
        >>> format_provider_id("imdb", "tt1234567")
        "[imdbid-tt1234567]"
        >>> format_provider_id("tmdb", "12345")
        "[tmdbid-12345]"
    """
    if provider not in PROVIDER_VALIDATORS:
        raise ValidationError(
            f"Unsupported provider '{provider}'. "
            f"Supported providers: {', '.join(PROVIDER_VALIDATORS.keys())}"
        )

    if not validate_provider_id(provider, provider_id):
        raise ValidationError(
            f"Invalid {provider} ID format: '{provider_id}'. "
            f"Expected format: {PROVIDER_VALIDATORS[provider].pattern}"
        )

    return f"[{provider}id-{provider_id}]"


def generate_folder_name(
    title: str,
    year: Optional[int] = None,
    provider_ids: Optional[Dict[str, str]] = None,
    include_provider_ids: bool = False,
) -> str:
    """
    Generate a Jellyfin-compatible folder name.


    Args:
        title: Media title
        year: Release year (optional)
        provider_ids: Dictionary of provider IDs (optional)
        include_provider_ids: Whether to include provider IDs in folder name

    Returns:
        str: Formatted folder name

    Raises:
        ValidationError: If title is empty

    Examples:
        >>> generate_folder_name("The Matrix", 1999)
        "The Matrix (1999)"
        >>> generate_folder_name("The Matrix", 1999, {"imdb": "tt0133093"}, True)
        "The Matrix (1999) [imdbid-tt0133093]"
        >>> generate_folder_name("Show", provider_ids={"tmdb": "12345", "tvdb": "67890"}, include_provider_ids=True)
        "Show [tmdbid-12345] [tvdbid-67890]"
    """
    if not title:
        raise ValidationError("Title cannot be empty")

    # Start with title
    parts = [title]

    # Add year if provided
    if year:
        parts.append(f"({year})")

    # Add provider IDs if requested
    if include_provider_ids and provider_ids:
        # Sort provider IDs for consistent ordering (IMDb, TMDB, TVDB)
        provider_order = ["imdb", "tmdb", "tvdb"]
        for provider in provider_order:
            if provider in provider_ids:
                try:
                    formatted = format_provider_id(provider, provider_ids[provider])
                    parts.append(formatted)
                except ValidationError:
                    # Skip invalid provider IDs
                    continue

    return " ".join(parts)


def strip_provider_ids(path: str) -> str:
    """
    Remove all provider IDs from a path.


    Args:
        path: Path containing provider IDs

    Returns:
        str: Path with provider IDs removed

    Examples:
        >>> strip_provider_ids("Movie [imdbid-tt1234567]")
        "Movie"
        >>> strip_provider_ids("Show [tmdbid-12345] [tvdbid-67890]")
        "Show"
    """
    result = path

    # Remove all provider ID patterns
    for pattern in PROVIDER_PATTERNS.values():
        result = pattern.sub("", result)

    # Clean up extra whitespace
    result = " ".join(result.split())

    return result.strip()
