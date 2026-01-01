"""Tests for filename sanitization and validation utilities."""

import pytest

from mo.parsers.sanitize import (
    RESERVED_CHARS,
    sanitize_filename,
    truncate_filename,
    validate_path_length,
)
from mo.utils.errors import ValidationError


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    def test_removes_reserved_characters(self):
        """Test that all reserved characters are removed."""
        # Test each reserved character individually
        for char in RESERVED_CHARS.keys():
            result = sanitize_filename(f"before{char}after")
            assert char not in result
            assert result == "beforeafter"

    def test_removes_multiple_reserved_characters(self):
        """Test removing multiple reserved characters."""
        assert sanitize_filename('Movie: The "Sequel"') == 'Movie The Sequel'
        assert sanitize_filename("File<name>with|chars") == "Filenamewithchars"
        assert sanitize_filename("Path/with\\slashes") == "Pathwithslashes"

    def test_custom_replacement(self):
        """Test using custom replacement string."""
        assert sanitize_filename("File: Name", replacement="_") == "File_ Name"
        assert sanitize_filename("A/B/C", replacement="-") == "A-B-C"

    def test_strips_whitespace_and_dots(self):
        """Test removal of leading/trailing whitespace and dots."""
        assert sanitize_filename("  filename  ") == "filename"
        assert sanitize_filename("...filename...") == "filename"
        assert sanitize_filename("  ..filename..  ") == "filename"

    def test_normalizes_unicode(self):
        """Test Unicode normalization (NFC)."""
        # Combining characters should be normalized
        result = sanitize_filename("café")  # NFC form
        assert result == "café"

    def test_empty_filename_raises_error(self):
        """Test that empty filename raises ValidationError."""
        with pytest.raises(ValidationError, match="Filename cannot be empty"):
            sanitize_filename("")

    def test_filename_becomes_empty_after_sanitization(self):
        """Test error when filename becomes empty after sanitization."""
        with pytest.raises(
            ValidationError, match="becomes empty after sanitization"
        ):
            sanitize_filename(":::...")  # Only reserved chars and dots

    def test_preserves_valid_characters(self):
        """Test that valid characters are preserved."""
        valid = "Movie Name (2024) - Part 1"
        assert sanitize_filename(valid) == valid

    def test_preserves_extension(self):
        """Test that file extensions are preserved."""
        assert sanitize_filename("movie.mkv") == "movie.mkv"
        assert sanitize_filename("file:name.mp4") == "filename.mp4"


class TestValidatePathLength:
    """Test validate_path_length function."""

    def test_valid_path_does_not_raise(self):
        """Test that valid path length does not raise error."""
        validate_path_length("/short/path")  # Should not raise

    def test_exceeds_platform_maximum(self, monkeypatch):
        """Test error when path exceeds platform maximum."""
        # Mock get_max_path_length to return a small value
        monkeypatch.setattr("mo.parsers.sanitize.get_max_path_length", lambda: 50)

        long_path = "/very/long/path/" + "a" * 100
        with pytest.raises(ValidationError, match="exceeds platform maximum"):
            validate_path_length(long_path)

    def test_error_message_truncates_long_path(self, monkeypatch):
        """Test that error message truncates very long paths."""
        monkeypatch.setattr("mo.parsers.sanitize.get_max_path_length", lambda: 50)

        long_path = "/path/" + "a" * 200
        with pytest.raises(ValidationError) as exc_info:
            validate_path_length(long_path)

        # Error message should contain truncated path
        assert "Path: /path/" in str(exc_info.value)
        assert "..." in str(exc_info.value)


class TestTruncateFilename:
    """Test truncate_filename function."""

    def test_no_truncation_needed(self):
        """Test that short filenames are not truncated."""
        short = "short.mkv"
        assert truncate_filename(short, max_length=255) == short

    def test_truncates_long_filename(self):
        """Test truncation of long filename."""
        long_name = "a" * 300 + ".mkv"
        result = truncate_filename(long_name, max_length=255)

        assert len(result) == 255
        assert result.endswith(".mkv")
        assert result.startswith("a")

    def test_preserves_extension(self):
        """Test that file extension is preserved."""
        long_name = "a" * 300 + ".mp4"
        result = truncate_filename(long_name, max_length=100)

        assert result.endswith(".mp4")
        assert len(result) == 100

    def test_no_extension(self):
        """Test truncation of filename without extension."""
        long_name = "a" * 300
        result = truncate_filename(long_name, max_length=100)

        assert len(result) == 100
        assert "." not in result

    def test_with_suffix(self):
        """Test truncation with suffix."""
        long_name = "a" * 300 + ".mkv"
        suffix = "-hash123"
        result = truncate_filename(long_name, max_length=100, suffix=suffix)

        assert len(result) == 100
        assert result.endswith("-hash123.mkv")

    def test_extension_too_long_raises_error(self):
        """Test error when extension and suffix are too long."""
        filename = "name.extension_that_is_very_long"
        with pytest.raises(
            ValidationError, match="extension and suffix too long"
        ):
            truncate_filename(filename, max_length=20, suffix="-suffix")

    def test_multiple_dots_in_filename(self):
        """Test handling of multiple dots (uses last one as extension)."""
        filename = "a" * 300 + ".part1.mkv"
        result = truncate_filename(filename, max_length=100)

        # Should preserve only the last extension
        assert result.endswith(".mkv")
        assert len(result) == 100
