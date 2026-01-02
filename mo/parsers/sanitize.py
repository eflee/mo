"""Filename sanitization and validation utilities."""

import re
import unicodedata
from typing import Dict

from mo.utils.errors import ValidationError
from mo.utils.platform import get_max_path_length

# Reserved characters that cannot be used in filenames (Windows + Unix)
# Single source of truth for reserved characters
RESERVED_CHARS: Dict[str, str] = {
    "<": "",
    ">": "",
    ":": "",
    '"': "",
    "/": "",
    "\\": "",
    "|": "",
    "?": "",
    "*": "",
}

_RESERVED_CHARS_PATTERN = re.compile("|".join(re.escape(char) for char in RESERVED_CHARS.keys()))


def sanitize_filename(filename: str, replacement: str = "") -> str:
    """Sanitize a filename by removing/replacing reserved characters.

    Args:
        filename: The filename to sanitize
        replacement: String to replace reserved characters with (default: empty string)

    Returns:
        str: Sanitized filename

    Raises:
        ValidationError: If filename becomes empty after sanitization

    Examples:
        >>> sanitize_filename('My Movie: The Sequel')
        'My Movie The Sequel'
        >>> sanitize_filename('File<name>', '_')
        'File_name'
    """
    if not filename:
        raise ValidationError("Filename cannot be empty")

    # Normalize Unicode characters (NFC form)
    sanitized = unicodedata.normalize("NFC", filename)

    # Replace reserved characters
    sanitized = _RESERVED_CHARS_PATTERN.sub(replacement, sanitized)

    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip().strip(".")

    if not sanitized:
        raise ValidationError(
            f"Filename '{filename}' becomes empty after sanitization. "
            "Please provide a filename with valid characters."
        )

    return sanitized


def validate_path_length(path: str) -> None:
    """Validate that a path does not exceed platform-specific limits.

    Args:
        path: The path to validate

    Raises:
        ValidationError: If path exceeds platform maximum length
    """
    max_length = get_max_path_length()

    if len(path) > max_length:
        raise ValidationError(
            f"Path length ({len(path)}) exceeds platform maximum ({max_length} characters). "
            f"Path: {path[:50]}..."
        )


def truncate_filename(filename: str, max_length: int = 255, suffix: str = "") -> str:
    """
    Truncate a filename to a maximum length while preserving the extension.

    Args:
        filename: The filename to truncate
        max_length: Maximum length (default: 255, typical filesystem limit)
        suffix: Optional suffix to add (e.g., hash for uniqueness)

    Returns:
        str: Truncated filename

    Examples:
        >>> truncate_filename('a' * 300 + '.mkv', 255)
        'aaa...aaa.mkv'  # truncated to 255 chars
    """
    if len(filename) <= max_length:
        return filename

    # Split into name and extension
    if "." in filename:
        name, ext = filename.rsplit(".", 1)
        ext = f".{ext}"
    else:
        name, ext = filename, ""

    # Calculate available space
    available = max_length - len(ext) - len(suffix)

    if available <= 0:
        raise ValidationError(
            f"Cannot truncate filename: extension and suffix too long "
            f"(max: {max_length}, ext: {len(ext)}, suffix: {len(suffix)})"
        )

    # Truncate name
    truncated_name = name[:available]

    return f"{truncated_name}{suffix}{ext}"
