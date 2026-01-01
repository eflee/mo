"""Tests for sample file detection."""

import pytest

from mo.parsers.sample import (
    detect_sample_files,
    filter_sample_files,
    is_sample_file,
)


class TestIsSampleFile:
    """Test sample file detection."""

    def test_sample_mkv(self):
        """Test 'sample.mkv' is detected."""
        assert is_sample_file("sample.mkv") is True

    def test_uppercase_sample(self):
        """Test 'SAMPLE.mkv' is detected (case-insensitive)."""
        assert is_sample_file("SAMPLE.mkv") is True

    def test_mixed_case_sample(self):
        """Test 'SaMpLe.mkv' is detected."""
        assert is_sample_file("SaMpLe.mkv") is True

    def test_movie_sample(self):
        """Test 'Movie-sample.mkv' is detected."""
        assert is_sample_file("Movie-sample.mkv") is True

    def test_sample_movie(self):
        """Test 'sample-movie.mkv' is detected."""
        assert is_sample_file("sample-movie.mkv") is True

    def test_sample_with_spaces(self):
        """Test 'Movie Sample.mkv' is detected."""
        assert is_sample_file("Movie Sample.mkv") is True

    def test_sample_scene(self):
        """Test 'sample-scene.mkv' is detected."""
        assert is_sample_file("sample-scene.mkv") is True

    def test_sample_with_underscores(self):
        """Test 'movie_sample_scene.mkv' is detected."""
        assert is_sample_file("movie_sample_scene.mkv") is True

    def test_rejects_samplesize(self):
        """Test 'samplesize.txt' is NOT detected (no word boundary)."""
        assert is_sample_file("samplesize.txt") is False

    def test_rejects_sampling(self):
        """Test 'sampling.mkv' is NOT detected (no word boundary)."""
        assert is_sample_file("sampling.mkv") is False

    def test_rejects_example(self):
        """Test 'example.mkv' is NOT detected (different word)."""
        assert is_sample_file("example.mkv") is False

    def test_rejects_regular_movie(self):
        """Test regular movie filename is not detected."""
        assert is_sample_file("Movie.mkv") is False

    def test_rejects_episode_file(self):
        """Test episode filename is not detected."""
        assert is_sample_file("Show.S01E01.mkv") is False

    def test_with_full_path(self):
        """Test detection works with full path."""
        assert is_sample_file("/movies/Movie/sample.mkv") is True

    def test_sample_at_start(self):
        """Test 'sample - Movie.mkv' is detected."""
        assert is_sample_file("sample - Movie.mkv") is True

    def test_sample_at_end(self):
        """Test 'Movie - sample.mkv' is detected."""
        assert is_sample_file("Movie - sample.mkv") is True

    def test_sample_in_middle(self):
        """Test 'Movie sample scene.mkv' is detected."""
        assert is_sample_file("Movie sample scene.mkv") is True


class TestFilterSampleFiles:
    """Test filtering sample files from lists."""

    def test_filters_sample_files(self):
        """Test filtering removes sample files."""
        files = ["movie.mkv", "sample.mkv", "show.mkv", "movie-sample.mkv"]
        result = filter_sample_files(files)
        assert result == ["movie.mkv", "show.mkv"]

    def test_preserves_non_samples(self):
        """Test filtering preserves non-sample files."""
        files = ["movie1.mkv", "movie2.mkv", "movie3.mkv"]
        result = filter_sample_files(files)
        assert result == files

    def test_filters_all_samples(self):
        """Test filtering when all files are samples."""
        files = ["sample.mkv", "SAMPLE.avi", "movie-sample.mkv"]
        result = filter_sample_files(files)
        assert result == []

    def test_empty_list(self):
        """Test filtering empty list."""
        result = filter_sample_files([])
        assert result == []

    def test_preserves_order(self):
        """Test filtering preserves file order."""
        files = ["a.mkv", "b.mkv", "sample.mkv", "c.mkv"]
        result = filter_sample_files(files)
        assert result == ["a.mkv", "b.mkv", "c.mkv"]


class TestDetectSampleFiles:
    """Test detecting sample files from lists."""

    def test_detects_sample_files(self):
        """Test detecting sample files."""
        files = ["movie.mkv", "sample.mkv", "show.mkv", "movie-sample.mkv"]
        result = detect_sample_files(files)
        assert set(result) == {"sample.mkv", "movie-sample.mkv"}

    def test_detects_none_when_no_samples(self):
        """Test detecting when no samples present."""
        files = ["movie1.mkv", "movie2.mkv", "movie3.mkv"]
        result = detect_sample_files(files)
        assert result == []

    def test_detects_all_samples(self):
        """Test detecting when all files are samples."""
        files = ["sample.mkv", "SAMPLE.avi", "movie-sample.mkv"]
        result = detect_sample_files(files)
        assert len(result) == 3

    def test_empty_list(self):
        """Test detecting from empty list."""
        result = detect_sample_files([])
        assert result == []

    def test_preserves_order(self):
        """Test detection preserves order."""
        files = ["sample1.mkv", "movie.mkv", "sample2.mkv"]
        result = detect_sample_files(files)
        assert result == ["sample1.mkv", "sample2.mkv"]


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_filename(self):
        """Test empty filename."""
        assert is_sample_file("") is False

    def test_only_extension(self):
        """Test filename with only extension."""
        assert is_sample_file(".mkv") is False

    def test_sample_with_no_extension(self):
        """Test 'sample' with no extension is detected."""
        assert is_sample_file("sample") is True

    def test_filename_only_sample(self):
        """Test filename that is only 'sample'."""
        assert is_sample_file("sample") is True

    def test_case_sensitivity(self):
        """Test various case combinations."""
        assert is_sample_file("SaMpLe.mkv") is True
        assert is_sample_file("SAMPLE.MKV") is True
        assert is_sample_file("sample.MKV") is True

    def test_multiple_extensions(self):
        """Test file with multiple extensions."""
        assert is_sample_file("sample.en.mkv") is True
        assert is_sample_file("movie.sample.backup.mkv") is True
