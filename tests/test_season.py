"""Tests for season folder detection."""

from pathlib import Path

import pytest

from mo.parsers.season import (
    detect_season_from_path,
    extract_season_number,
    format_season_folder_name,
    is_season_folder,
)


class TestIsSeasonFolder:
    """Test season folder name validation."""

    def test_season_01(self):
        """Test 'Season 01' is recognized."""
        assert is_season_folder("Season 01") is True

    def test_season_1(self):
        """Test 'Season 1' without leading zero is recognized."""
        assert is_season_folder("Season 1") is True

    def test_season_10(self):
        """Test 'Season 10' is recognized."""
        assert is_season_folder("Season 10") is True

    def test_lowercase_season(self):
        """Test lowercase 'season 01' is recognized."""
        assert is_season_folder("season 01") is True

    def test_uppercase_season(self):
        """Test uppercase 'SEASON 01' is recognized."""
        assert is_season_folder("SEASON 01") is True

    def test_mixed_case(self):
        """Test mixed case 'SeAsOn 01' is recognized."""
        assert is_season_folder("SeAsOn 01") is True

    def test_with_extra_spaces(self):
        """Test 'Season  01' with extra spaces is recognized."""
        assert is_season_folder("Season  01") is True

    def test_season_0_specials(self):
        """Test 'Season 0' for specials is recognized."""
        assert is_season_folder("Season 0") is True

    def test_specials_name(self):
        """Test 'Specials' is recognized."""
        assert is_season_folder("Specials") is True

    def test_special_singular(self):
        """Test 'Special' is recognized."""
        assert is_season_folder("Special") is True

    def test_extras(self):
        """Test 'Extras' is recognized as specials."""
        assert is_season_folder("Extras") is True

    def test_extra_singular(self):
        """Test 'Extra' is recognized."""
        assert is_season_folder("Extra") is True

    def test_rejects_s01_abbreviation(self):
        """Test 'S01' abbreviation is NOT recognized (Jellyfin requirement)."""
        assert is_season_folder("S01") is False

    def test_rejects_s1_abbreviation(self):
        """Test 'S1' abbreviation is NOT recognized."""
        assert is_season_folder("S1") is False

    def test_rejects_random_folder(self):
        """Test random folder name is not recognized."""
        assert is_season_folder("Episodes") is False

    def test_rejects_partial_match(self):
        """Test partial match is rejected."""
        assert is_season_folder("Season") is False

    def test_rejects_season_with_text(self):
        """Test 'Season 1 Extended' is rejected."""
        assert is_season_folder("Season 1 Extended") is False


class TestExtractSeasonNumber:
    """Test season number extraction."""

    def test_extract_from_season_01(self):
        """Test extracting from 'Season 01'."""
        assert extract_season_number("Season 01") == 1

    def test_extract_from_season_1(self):
        """Test extracting from 'Season 1'."""
        assert extract_season_number("Season 1") == 1

    def test_extract_from_season_10(self):
        """Test extracting from 'Season 10'."""
        assert extract_season_number("Season 10") == 10

    def test_extract_from_season_100(self):
        """Test extracting from 'Season 100'."""
        assert extract_season_number("Season 100") == 100

    def test_extract_zero_from_specials(self):
        """Test extracting 0 from 'Specials'."""
        assert extract_season_number("Specials") == 0

    def test_extract_zero_from_special(self):
        """Test extracting 0 from 'Special'."""
        assert extract_season_number("Special") == 0

    def test_extract_zero_from_extras(self):
        """Test extracting 0 from 'Extras'."""
        assert extract_season_number("Extras") == 0

    def test_extract_zero_from_season_0(self):
        """Test extracting 0 from 'Season 0'."""
        assert extract_season_number("Season 0") == 0

    def test_returns_none_for_invalid(self):
        """Test returns None for invalid folder name."""
        assert extract_season_number("S01") is None

    def test_returns_none_for_random(self):
        """Test returns None for random folder name."""
        assert extract_season_number("Episodes") is None

    def test_case_insensitive(self):
        """Test extraction is case-insensitive."""
        assert extract_season_number("season 05") == 5
        assert extract_season_number("SEASON 05") == 5


class TestFormatSeasonFolderName:
    """Test season folder name generation."""

    def test_format_season_1(self):
        """Test formatting season 1."""
        assert format_season_folder_name(1) == "Season 01"

    def test_format_season_5(self):
        """Test formatting season 5."""
        assert format_season_folder_name(5) == "Season 05"

    def test_format_season_10(self):
        """Test formatting season 10."""
        assert format_season_folder_name(10) == "Season 10"

    def test_format_season_100(self):
        """Test formatting season 100."""
        assert format_season_folder_name(100) == "Season 100"

    def test_format_season_0_as_specials(self):
        """Test formatting season 0 as 'Specials'."""
        assert format_season_folder_name(0) == "Specials"

    def test_zero_padding(self):
        """Test that single digits are zero-padded."""
        assert format_season_folder_name(1) == "Season 01"
        assert format_season_folder_name(9) == "Season 09"


class TestDetectSeasonFromPath:
    """Test season detection from path hierarchy."""

    def test_detect_from_season_folder(self, tmp_path):
        """Test detecting season from season folder."""
        season_path = tmp_path / "Show" / "Season 01"
        season_path.mkdir(parents=True)

        result = detect_season_from_path(season_path)
        assert result == 1

    def test_detect_from_file_in_season_folder(self, tmp_path):
        """Test detecting season from file in season folder."""
        season_path = tmp_path / "Show" / "Season 02"
        season_path.mkdir(parents=True)
        file_path = season_path / "episode.mkv"

        result = detect_season_from_path(file_path)
        assert result == 2

    def test_detect_from_specials_folder(self, tmp_path):
        """Test detecting season 0 from Specials folder."""
        specials_path = tmp_path / "Show" / "Specials"
        specials_path.mkdir(parents=True)

        result = detect_season_from_path(specials_path)
        assert result == 0

    def test_detect_from_nested_path(self, tmp_path):
        """Test detecting season from deeply nested path."""
        nested_path = tmp_path / "Show" / "Season 03" / "subfolder"
        nested_path.mkdir(parents=True)

        result = detect_season_from_path(nested_path)
        assert result == 3

    def test_returns_none_when_no_season_folder(self, tmp_path):
        """Test returns None when no season folder in path."""
        random_path = tmp_path / "Show" / "Random" / "episode.mkv"

        result = detect_season_from_path(random_path)
        assert result is None

    def test_returns_none_for_root(self, tmp_path):
        """Test returns None for path without season folder."""
        result = detect_season_from_path(tmp_path)
        assert result is None


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_string(self):
        """Test empty string returns False."""
        assert is_season_folder("") is False

    def test_whitespace_only(self):
        """Test whitespace-only returns False."""
        assert is_season_folder("   ") is False

    def test_season_with_leading_whitespace(self):
        """Test season with leading whitespace is handled."""
        assert is_season_folder("  Season 01") is True

    def test_season_with_trailing_whitespace(self):
        """Test season with trailing whitespace is handled."""
        assert is_season_folder("Season 01  ") is True

    def test_extract_handles_whitespace(self):
        """Test extraction handles whitespace."""
        assert extract_season_number("  Season 05  ") == 5
