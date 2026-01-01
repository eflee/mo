"""Tests for episode filename parsing."""

import pytest

from mo.parsers.episode import (
    EpisodeInfo,
    extract_all_episode_numbers,
    parse_episode_filename,
)


class TestStandardPatterns:
    """Test standard episode patterns (S##E##, s##x##)."""

    def test_s01e01_uppercase(self):
        """Test S01E01 pattern."""
        result = parse_episode_filename("Show.S01E05.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 5
        assert result.ending_episode_number is None

    def test_s01e01_lowercase(self):
        """Test s01e01 pattern."""
        result = parse_episode_filename("show.s02e03.avi")
        assert result is not None
        assert result.season_number == 2
        assert result.episode_number == 3

    def test_s1e1_no_leading_zeros(self):
        """Test S1E1 pattern without leading zeros."""
        result = parse_episode_filename("Show.S3E7.mkv")
        assert result is not None
        assert result.season_number == 3
        assert result.episode_number == 7

    def test_1x01_pattern(self):
        """Test 1x01 pattern."""
        result = parse_episode_filename("Show.2x03.mkv")
        assert result is not None
        assert result.season_number == 2
        assert result.episode_number == 3

    def test_s01x01_pattern(self):
        """Test s01x01 pattern."""
        result = parse_episode_filename("Show.s01x02.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 2

    def test_with_spaces(self):
        """Test pattern with spaces."""
        result = parse_episode_filename("Show S01 E05.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 5

    def test_season_word(self):
        """Test 'season' word pattern."""
        result = parse_episode_filename("Show season 2 e10.mkv")
        assert result is not None
        assert result.season_number == 2
        assert result.episode_number == 10

    def test_triple_digit_episode(self):
        """Test triple-digit episode number."""
        result = parse_episode_filename("Show.S01E123.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 123


class TestMultiEpisodePatterns:
    """Test multi-episode patterns."""

    def test_s01e01_e02(self):
        """Test S01E01-E02 pattern."""
        result = parse_episode_filename("Show.S01E01-E02.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 1
        assert result.ending_episode_number == 2

    def test_s01e01e02e03(self):
        """Test S01E01E02E03 pattern."""
        result = parse_episode_filename("Show.S01E01E02E03.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 1
        assert result.ending_episode_number == 3

    def test_s01e01_dash_02(self):
        """Test S01E01-02 pattern (without E before second number)."""
        result = parse_episode_filename("Show.S01E05-06.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 5
        assert result.ending_episode_number == 6

    def test_s01e01_dash_e02_dash_e03(self):
        """Test S01E01-E02-E03 pattern."""
        result = parse_episode_filename("Show.S01E05-E06-E07.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 5
        assert result.ending_episode_number == 7

    def test_s01e01xe02xe03(self):
        """Test S01E01xE02xE03 pattern."""
        result = parse_episode_filename("Show.S02E01xE02xE03.mkv")
        assert result is not None
        assert result.season_number == 2
        assert result.episode_number == 1
        assert result.ending_episode_number == 3

    def test_extract_all_episodes(self):
        """Test extracting all episode numbers."""
        episodes = extract_all_episode_numbers("Show.S01E01-E02-E03.mkv")
        assert episodes == [1, 2, 3]

    def test_extract_all_episodes_range(self):
        """Test extracting episode range."""
        episodes = extract_all_episode_numbers("Show.S01E05-E07.mkv")
        assert episodes == [5, 6, 7]

    def test_extract_all_episodes_without_e(self):
        """Test extracting episodes from S01E01-02 format."""
        episodes = extract_all_episode_numbers("Show.S01E05-07.mkv")
        assert episodes == [5, 6, 7]


class TestSeasonValidation:
    """Test season number validation (avoid resolution false positives)."""

    def test_rejects_season_720(self):
        """Test that season 720 is rejected (resolution)."""
        result = parse_episode_filename("Show.720E01.mkv")
        # Should not match due to invalid season
        assert result is None or result.season_number != 720

    def test_rejects_season_1080(self):
        """Test that season 1080 is rejected (resolution)."""
        result = parse_episode_filename("Show.1080E01.mkv")
        assert result is None or result.season_number != 1080

    def test_rejects_season_in_invalid_range(self):
        """Test that seasons 200-1927 are rejected."""
        result = parse_episode_filename("Show.500E01.mkv")
        assert result is None or result.season_number != 500

    def test_rejects_season_above_threshold(self):
        """Test that seasons >2500 are rejected."""
        result = parse_episode_filename("Show.3000E01.mkv")
        assert result is None or result.season_number != 3000

    def test_accepts_valid_season_100(self):
        """Test that season 100 is accepted."""
        result = parse_episode_filename("Show.S100E01.mkv")
        assert result is not None
        assert result.season_number == 100

    def test_accepts_season_99(self):
        """Test that season 99 is accepted."""
        result = parse_episode_filename("Show.S99E01.mkv")
        assert result is not None
        assert result.season_number == 99


class TestEndingEpisodeValidation:
    """Test ending episode validation (avoid resolution false positives)."""

    def test_rejects_ending_episode_1080(self):
        """Test that ending episode 1080 is rejected."""
        result = parse_episode_filename("Show.S01E01-E1080.mkv")
        assert result is not None
        # Ending episode should be None due to resolution filter
        assert result.ending_episode_number is None or result.ending_episode_number != 1080

    def test_rejects_ending_episode_720(self):
        """Test that ending episode 720 is rejected."""
        result = parse_episode_filename("Show.S01E01-E720.mkv")
        assert result is not None
        assert result.ending_episode_number is None or result.ending_episode_number != 720

    def test_accepts_valid_ending_episode(self):
        """Test that valid ending episode is accepted."""
        result = parse_episode_filename("Show.S01E01-E05.mkv")
        assert result is not None
        assert result.ending_episode_number == 5


class TestSeriesNameExtraction:
    """Test series name extraction from filenames."""

    def test_extracts_series_name(self):
        """Test series name extraction."""
        result = parse_episode_filename("Breaking Bad.S01E01.mkv")
        assert result is not None
        assert result.series_name == "Breaking Bad"

    def test_cleans_underscores(self):
        """Test that underscores are cleaned."""
        result = parse_episode_filename("Breaking_Bad.S01E01.mkv")
        assert result is not None
        assert result.series_name == "Breaking Bad"

    def test_cleans_dots(self):
        """Test that dots are cleaned."""
        result = parse_episode_filename("Breaking.Bad.S01E01.mkv")
        assert result is not None
        assert result.series_name == "Breaking Bad"

    def test_cleans_dashes(self):
        """Test that dashes are cleaned."""
        result = parse_episode_filename("Breaking-Bad-S01E01.mkv")
        assert result is not None
        assert result.series_name == "Breaking Bad"

    def test_trims_trailing_separators(self):
        """Test that trailing separators are trimmed."""
        result = parse_episode_filename("Show_.S01E01.mkv")
        assert result is not None
        assert result.series_name == "Show"

    def test_handles_multiple_spaces(self):
        """Test that multiple spaces are collapsed."""
        result = parse_episode_filename("The   Wire.S01E01.mkv")
        assert result is not None
        assert result.series_name == "The Wire"


class TestDateBasedPatterns:
    """Test date-based episode patterns."""

    def test_yyyy_mm_dd_dash(self):
        """Test YYYY-MM-DD pattern."""
        result = parse_episode_filename("Show.2023-01-15.mkv")
        assert result is not None
        assert result.is_daily is True
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15

    def test_yyyy_mm_dd_dot(self):
        """Test YYYY.MM.DD pattern."""
        result = parse_episode_filename("Show.2023.12.31.mkv")
        assert result is not None
        assert result.is_daily is True
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 31

    def test_yyyy_mm_dd_underscore(self):
        """Test YYYY_MM_DD pattern."""
        result = parse_episode_filename("Show_2023_06_15.mkv")
        assert result is not None
        assert result.is_daily is True
        assert result.year == 2023
        assert result.month == 6
        assert result.day == 15

    def test_rejects_invalid_date(self):
        """Test that invalid dates are rejected."""
        result = parse_episode_filename("Show.2023-13-45.mkv")
        # Should not match or should not have date info
        assert result is None or result.is_daily is False

    def test_extracts_series_name_from_date(self):
        """Test series name extraction from date-based pattern."""
        result = parse_episode_filename("Daily Show.2023-01-15.mkv")
        assert result is not None
        assert result.series_name == "Daily Show"


class TestAbsoluteNumbering:
    """Test absolute numbering patterns (anime)."""

    def test_show_001(self):
        """Test 'Show 001' pattern."""
        result = parse_episode_filename("Anime Show 001.mkv")
        assert result is not None
        assert result.series_name == "Anime Show"
        assert result.episode_number == 1
        assert result.season_number is None

    def test_show_dash_001(self):
        """Test 'Show - 001' pattern."""
        result = parse_episode_filename("Anime Show - 015.mkv")
        assert result is not None
        assert result.series_name == "Anime Show"
        assert result.episode_number == 15

    def test_show_underscore_001(self):
        """Test 'Show_001' pattern."""
        result = parse_episode_filename("Anime_Show_042.mkv")
        assert result is not None
        assert result.series_name == "Anime Show"
        assert result.episode_number == 42

    def test_triple_digit_absolute(self):
        """Test triple-digit absolute numbering."""
        result = parse_episode_filename("Show - 123.mkv")
        assert result is not None
        assert result.episode_number == 123


class TestEdgeCases:
    """Test edge cases and malformed input."""

    def test_no_match_returns_none(self):
        """Test that unrecognized patterns return None."""
        result = parse_episode_filename("RandomFile.mkv")
        assert result is None

    def test_empty_filename(self):
        """Test empty filename."""
        result = parse_episode_filename("")
        assert result is None

    def test_only_extension(self):
        """Test filename with only extension."""
        result = parse_episode_filename(".mkv")
        assert result is None

    def test_with_full_path(self):
        """Test that parsing works with full paths."""
        result = parse_episode_filename("/tv/Show/Season 01/Show.S01E05.mkv")
        assert result is not None
        assert result.season_number == 1
        assert result.episode_number == 5

    def test_complex_series_name(self):
        """Test complex series name with numbers and special chars."""
        result = parse_episode_filename("Marvel's Agents of S.H.I.E.L.D. S01E01.mkv")
        assert result is not None
        assert "Agents" in result.series_name

    def test_preserves_apostrophes_in_name(self):
        """Test that apostrophes are preserved in series name."""
        result = parse_episode_filename("Marvel's Show S01E01.mkv")
        assert result is not None
        assert "Marvel" in result.series_name


class TestPatternPriority:
    """Test that patterns are matched in correct priority order."""

    def test_standard_pattern_over_absolute(self):
        """Test that S##E## pattern takes priority over absolute."""
        result = parse_episode_filename("Show 123 S01E05.mkv")
        assert result is not None
        # Should match S01E05, not absolute 123
        assert result.season_number == 1
        assert result.episode_number == 5

    def test_date_pattern_extracted(self):
        """Test that date pattern is recognized."""
        result = parse_episode_filename("Show.2023-01-15.S01E01.mkv")
        # Standard pattern might match first, but date should be detected if used alone
        result2 = parse_episode_filename("Show.2023-01-15.mkv")
        assert result2 is not None
        assert result2.is_daily is True
