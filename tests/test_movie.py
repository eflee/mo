"""Tests for movie filename parsing."""

from pathlib import Path

import pytest

from mo.parsers.movie import (
    MovieInfo,
    is_bluray_folder,
    is_dvd_folder,
    parse_movie_filename,
    parse_movie_folder,
)


class TestParseMovieFilename:
    """Test movie filename parsing."""

    def test_title_and_year_parentheses(self):
        """Test parsing title and year in parentheses."""
        result = parse_movie_filename("Inception (2010).mkv")
        assert result is not None
        assert result.title == "Inception"
        assert result.year == 2010

    def test_title_and_year_brackets(self):
        """Test parsing title and year in brackets."""
        result = parse_movie_filename("The Matrix [1999].mkv")
        assert result is not None
        assert result.title == "The Matrix"
        assert result.year == 1999

    def test_title_only_no_year(self):
        """Test parsing title without year."""
        result = parse_movie_filename("SomeMovie.mkv")
        assert result is not None
        assert result.title == "SomeMovie"
        assert result.year is None

    def test_title_with_provider_id(self):
        """Test parsing with provider ID."""
        result = parse_movie_filename("Inception (2010) [imdbid-tt1375666].mkv")
        assert result is not None
        assert result.title == "Inception"
        assert result.year == 2010
        assert result.provider_ids is not None
        assert result.provider_ids["imdb"] == "tt1375666"

    def test_title_with_multiple_provider_ids(self):
        """Test parsing with multiple provider IDs."""
        result = parse_movie_filename("Movie (2020) [imdbid-tt1234567] [tmdbid-12345].mkv")
        assert result is not None
        assert result.title == "Movie"
        assert result.year == 2020
        assert result.provider_ids["imdb"] == "tt1234567"
        assert result.provider_ids["tmdb"] == "12345"

    def test_title_with_dots(self):
        """Test parsing title with dots as separators."""
        result = parse_movie_filename("The.Dark.Knight.(2008).mkv")
        assert result is not None
        assert result.title == "The Dark Knight"
        assert result.year == 2008

    def test_title_with_underscores(self):
        """Test parsing title with underscores."""
        result = parse_movie_filename("The_Dark_Knight_(2008).mkv")
        assert result is not None
        assert result.title == "The Dark Knight"
        assert result.year == 2008

    def test_title_with_dashes(self):
        """Test parsing title with dashes."""
        result = parse_movie_filename("The-Dark-Knight-(2008).mkv")
        assert result is not None
        assert result.title == "The Dark Knight"
        assert result.year == 2008

    def test_title_with_mixed_separators(self):
        """Test parsing title with mixed separators."""
        result = parse_movie_filename("The_Dark.Knight-(2008).mkv")
        assert result is not None
        assert result.title == "The Dark Knight"

    def test_year_at_start_of_range(self):
        """Test year at start of valid range (1900)."""
        result = parse_movie_filename("Old Movie (1900).mkv")
        assert result is not None
        assert result.year == 1900

    def test_year_at_end_of_range(self):
        """Test year at end of valid range (2099)."""
        result = parse_movie_filename("Future Movie (2099).mkv")
        assert result is not None
        assert result.year == 2099

    def test_ignores_invalid_year(self):
        """Test that invalid years are ignored."""
        result = parse_movie_filename("Movie (1899).mkv")
        assert result is not None
        # Year should be None or not 1899
        assert result.year != 1899

    def test_preserves_apostrophes(self):
        """Test that apostrophes are preserved in title."""
        result = parse_movie_filename("Ocean's Eleven (2001).mkv")
        assert result is not None
        assert "Ocean" in result.title

    def test_preserves_ampersands(self):
        """Test that ampersands are preserved."""
        result = parse_movie_filename("Fast & Furious (2009).mkv")
        assert result is not None
        assert result.title == "Fast & Furious"

    def test_with_full_path(self):
        """Test parsing works with full path."""
        result = parse_movie_filename("/movies/Inception (2010)/Inception (2010).mkv")
        assert result is not None
        assert result.title == "Inception"
        assert result.year == 2010

    def test_folder_name_without_extension(self):
        """Test parsing folder name (no extension)."""
        result = parse_movie_filename("Inception (2010)")
        assert result is not None
        assert result.title == "Inception"
        assert result.year == 2010


class TestDVDBluRayDetection:
    """Test DVD and BluRay folder structure detection."""

    def test_is_dvd_folder_video_ts(self, tmp_path):
        """Test DVD folder detection with VIDEO_TS."""
        video_ts = tmp_path / "Movie" / "VIDEO_TS"
        video_ts.mkdir(parents=True)

        assert is_dvd_folder(video_ts) is True

    def test_is_dvd_folder_parent(self, tmp_path):
        """Test DVD folder detection from parent."""
        video_ts = tmp_path / "Movie" / "VIDEO_TS"
        video_ts.mkdir(parents=True)
        parent = video_ts.parent

        assert is_dvd_folder(parent) is True

    def test_is_not_dvd_folder(self, tmp_path):
        """Test non-DVD folder."""
        regular = tmp_path / "Movie"
        regular.mkdir()

        assert is_dvd_folder(regular) is False

    def test_is_bluray_folder_bdmv(self, tmp_path):
        """Test BluRay folder detection with BDMV."""
        bdmv = tmp_path / "Movie" / "BDMV"
        bdmv.mkdir(parents=True)

        assert is_bluray_folder(bdmv) is True

    def test_is_bluray_folder_parent(self, tmp_path):
        """Test BluRay folder detection from parent."""
        bdmv = tmp_path / "Movie" / "BDMV"
        bdmv.mkdir(parents=True)
        parent = bdmv.parent

        assert is_bluray_folder(parent) is True

    def test_is_not_bluray_folder(self, tmp_path):
        """Test non-BluRay folder."""
        regular = tmp_path / "Movie"
        regular.mkdir()

        assert is_bluray_folder(regular) is False


class TestParseMovieFolder:
    """Test movie folder parsing."""

    def test_parse_regular_folder(self, tmp_path):
        """Test parsing regular movie folder."""
        folder = tmp_path / "Inception (2010)"
        folder.mkdir()

        result = parse_movie_folder(folder)
        assert result is not None
        assert result.title == "Inception"
        assert result.year == 2010
        assert result.is_dvd is False
        assert result.is_bluray is False

    def test_parse_dvd_folder(self, tmp_path):
        """Test parsing DVD folder structure."""
        video_ts = tmp_path / "Movie (2000)" / "VIDEO_TS"
        video_ts.mkdir(parents=True)

        result = parse_movie_folder(video_ts.parent)
        assert result is not None
        assert result.title == "Movie"
        assert result.year == 2000
        assert result.is_dvd is True

    def test_parse_from_video_ts_path(self, tmp_path):
        """Test parsing from VIDEO_TS path itself."""
        video_ts = tmp_path / "Movie (2000)" / "VIDEO_TS"
        video_ts.mkdir(parents=True)

        result = parse_movie_folder(video_ts)
        assert result is not None
        assert result.title == "Movie"
        assert result.year == 2000
        assert result.is_dvd is True

    def test_parse_bluray_folder(self, tmp_path):
        """Test parsing BluRay folder structure."""
        bdmv = tmp_path / "Movie (2010)" / "BDMV"
        bdmv.mkdir(parents=True)

        result = parse_movie_folder(bdmv.parent)
        assert result is not None
        assert result.title == "Movie"
        assert result.year == 2010
        assert result.is_bluray is True

    def test_parse_from_bdmv_path(self, tmp_path):
        """Test parsing from BDMV path itself."""
        bdmv = tmp_path / "Movie (2010)" / "BDMV"
        bdmv.mkdir(parents=True)

        result = parse_movie_folder(bdmv)
        assert result is not None
        assert result.title == "Movie"
        assert result.year == 2010
        assert result.is_bluray is True

    def test_parse_file_path_uses_parent(self, tmp_path):
        """Test parsing file path uses parent folder."""
        folder = tmp_path / "Inception (2010)"
        folder.mkdir()
        file = folder / "movie.mkv"

        result = parse_movie_folder(file)
        assert result is not None
        assert result.title == "Inception"


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_filename(self):
        """Test empty filename."""
        result = parse_movie_filename("")
        assert result is None

    def test_only_extension(self):
        """Test filename with only extension."""
        result = parse_movie_filename(".mkv")
        assert result is None

    def test_title_becomes_empty_after_cleaning(self):
        """Test title that becomes empty after cleaning."""
        result = parse_movie_filename("___(2010).mkv")
        # Should return None since title is empty
        assert result is None

    def test_multiple_years_takes_first(self):
        """Test that multiple years takes first match."""
        result = parse_movie_filename("Movie (2000) (2010).mkv")
        assert result is not None
        # Should take first year
        assert result.year == 2000

    def test_year_in_title(self):
        """Test movie with year in title."""
        result = parse_movie_filename("2001 A Space Odyssey (1968).mkv")
        assert result is not None
        assert result.title == "2001 A Space Odyssey"
        assert result.year == 1968

    def test_colons_removed(self):
        """Test that colons are removed from title (reserved character)."""
        # Note: This tests the interaction with sanitization
        result = parse_movie_filename("Star Wars: Episode IV (1977).mkv")
        assert result is not None
        # Colons should be converted to spaces
        assert "Star Wars" in result.title
