"""Tests for provider ID parsing and generation utilities."""

import pytest

from mo.parsers.provider_id import (
    extract_provider_ids,
    format_provider_id,
    generate_folder_name,
    strip_provider_ids,
    validate_provider_id,
)
from mo.utils.errors import ValidationError


class TestExtractProviderIds:
    """Test extract_provider_ids function."""

    def test_extract_imdb_id(self):
        """Test extracting IMDb ID."""
        result = extract_provider_ids("Movie [imdbid-tt1234567]")
        assert result == {"imdb": "tt1234567"}

    def test_extract_tmdb_id(self):
        """Test extracting TMDB ID."""
        result = extract_provider_ids("Show [tmdbid-12345]")
        assert result == {"tmdb": "12345"}

    def test_extract_tvdb_id(self):
        """Test extracting TVDB ID."""
        result = extract_provider_ids("Series [tvdbid-67890]")
        assert result == {"tvdb": "67890"}

    def test_extract_multiple_ids(self):
        """Test extracting multiple provider IDs."""
        result = extract_provider_ids(
            "Movie [imdbid-tt1234567] [tmdbid-12345] [tvdbid-67890]"
        )
        assert result == {"imdb": "tt1234567", "tmdb": "12345", "tvdb": "67890"}

    def test_case_insensitive(self):
        """Test case-insensitive extraction."""
        result = extract_provider_ids("Movie [IMDBID-tt1234567]")
        assert result == {"imdb": "tt1234567"}

        result = extract_provider_ids("Movie [ImDbId-tt1234567]")
        assert result == {"imdb": "tt1234567"}

    def test_no_provider_ids(self):
        """Test path without provider IDs."""
        result = extract_provider_ids("Movie (2024)")
        assert result == {}

    def test_partial_match(self):
        """Test that incomplete patterns are not matched."""
        result = extract_provider_ids("Movie [imdbid-]")
        assert result == {}

    def test_from_full_path(self):
        """Test extraction from full file path."""
        result = extract_provider_ids(
            "/media/Movies/The Matrix (1999) [imdbid-tt0133093]/movie.mkv"
        )
        assert result == {"imdb": "tt0133093"}


class TestValidateProviderId:
    """Test validate_provider_id function."""

    def test_valid_imdb_id(self):
        """Test valid IMDb ID."""
        assert validate_provider_id("imdb", "tt1234567") is True
        assert validate_provider_id("imdb", "tt0") is True

    def test_invalid_imdb_id(self):
        """Test invalid IMDb ID."""
        assert validate_provider_id("imdb", "1234567") is False
        assert validate_provider_id("imdb", "tt") is False
        assert validate_provider_id("imdb", "abc123") is False

    def test_valid_tmdb_id(self):
        """Test valid TMDB ID."""
        assert validate_provider_id("tmdb", "12345") is True
        assert validate_provider_id("tmdb", "0") is True

    def test_invalid_tmdb_id(self):
        """Test invalid TMDB ID."""
        assert validate_provider_id("tmdb", "tt12345") is False
        assert validate_provider_id("tmdb", "abc") is False

    def test_valid_tvdb_id(self):
        """Test valid TVDB ID."""
        assert validate_provider_id("tvdb", "67890") is True
        assert validate_provider_id("tvdb", "0") is True

    def test_invalid_tvdb_id(self):
        """Test invalid TVDB ID."""
        assert validate_provider_id("tvdb", "tt67890") is False
        assert validate_provider_id("tvdb", "xyz") is False

    def test_unsupported_provider(self):
        """Test unsupported provider."""
        assert validate_provider_id("invalid", "12345") is False


class TestFormatProviderId:
    """Test format_provider_id function."""

    def test_format_imdb_id(self):
        """Test formatting IMDb ID."""
        assert format_provider_id("imdb", "tt1234567") == "[imdbid-tt1234567]"

    def test_format_tmdb_id(self):
        """Test formatting TMDB ID."""
        assert format_provider_id("tmdb", "12345") == "[tmdbid-12345]"

    def test_format_tvdb_id(self):
        """Test formatting TVDB ID."""
        assert format_provider_id("tvdb", "67890") == "[tvdbid-67890]"

    def test_unsupported_provider_raises_error(self):
        """Test error for unsupported provider."""
        with pytest.raises(ValidationError, match="Unsupported provider"):
            format_provider_id("invalid", "12345")

    def test_invalid_id_format_raises_error(self):
        """Test error for invalid ID format."""
        with pytest.raises(ValidationError, match="Invalid imdb ID format"):
            format_provider_id("imdb", "12345")  # Missing 'tt' prefix

        with pytest.raises(ValidationError, match="Invalid tmdb ID format"):
            format_provider_id("tmdb", "tt12345")  # Should be numeric only


class TestGenerateFolderName:
    """Test generate_folder_name function."""

    def test_title_only(self):
        """Test generating folder name with title only."""
        assert generate_folder_name("The Matrix") == "The Matrix"

    def test_title_and_year(self):
        """Test generating folder name with title and year."""
        assert generate_folder_name("The Matrix", 1999) == "The Matrix (1999)"

    def test_with_single_provider_id(self):
        """Test generating folder name with single provider ID."""
        result = generate_folder_name(
            "The Matrix",
            1999,
            {"imdb": "tt0133093"},
            include_provider_ids=True,
        )
        assert result == "The Matrix (1999) [imdbid-tt0133093]"

    def test_with_multiple_provider_ids(self):
        """Test generating folder name with multiple provider IDs."""
        result = generate_folder_name(
            "The Matrix",
            1999,
            {"imdb": "tt0133093", "tmdb": "12345", "tvdb": "67890"},
            include_provider_ids=True,
        )
        # Should be in consistent order: IMDb, TMDB, TVDB
        assert result == (
            "The Matrix (1999) [imdbid-tt0133093] [tmdbid-12345] [tvdbid-67890]"
        )

    def test_provider_ids_not_included_by_default(self):
        """Test that provider IDs are not included by default."""
        result = generate_folder_name(
            "The Matrix", 1999, {"imdb": "tt0133093"}
        )
        assert result == "The Matrix (1999)"

    def test_empty_title_raises_error(self):
        """Test error for empty title."""
        with pytest.raises(ValidationError, match="Title cannot be empty"):
            generate_folder_name("")

    def test_skips_invalid_provider_ids(self):
        """Test that invalid provider IDs are skipped."""
        result = generate_folder_name(
            "Movie",
            2024,
            {"imdb": "invalid", "tmdb": "12345"},
            include_provider_ids=True,
        )
        # Should only include valid TMDB ID
        assert result == "Movie (2024) [tmdbid-12345]"

    def test_consistent_provider_order(self):
        """Test that provider IDs are always in consistent order."""
        # Provide in reverse order
        result = generate_folder_name(
            "Movie",
            provider_ids={"tvdb": "3", "imdb": "tt1", "tmdb": "2"},
            include_provider_ids=True,
        )
        # Should be reordered to IMDb, TMDB, TVDB
        assert result == "Movie [imdbid-tt1] [tmdbid-2] [tvdbid-3]"


class TestStripProviderIds:
    """Test strip_provider_ids function."""

    def test_strip_single_provider_id(self):
        """Test stripping single provider ID."""
        assert strip_provider_ids("Movie [imdbid-tt1234567]") == "Movie"

    def test_strip_multiple_provider_ids(self):
        """Test stripping multiple provider IDs."""
        result = strip_provider_ids(
            "Movie [imdbid-tt1234567] [tmdbid-12345] [tvdbid-67890]"
        )
        assert result == "Movie"

    def test_strip_with_year(self):
        """Test stripping provider IDs while preserving year."""
        result = strip_provider_ids("The Matrix (1999) [imdbid-tt0133093]")
        assert result == "The Matrix (1999)"

    def test_no_provider_ids(self):
        """Test path without provider IDs."""
        result = strip_provider_ids("Movie (2024)")
        assert result == "Movie (2024)"

    def test_cleans_extra_whitespace(self):
        """Test that extra whitespace is cleaned up."""
        result = strip_provider_ids("Movie   [imdbid-tt1234567]   ")
        assert result == "Movie"

    def test_case_insensitive(self):
        """Test case-insensitive stripping."""
        result = strip_provider_ids("Movie [IMDBID-tt1234567]")
        assert result == "Movie"
