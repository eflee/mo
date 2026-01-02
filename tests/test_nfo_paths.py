"""Tests for NFO path determination."""

import tempfile
from pathlib import Path

from mo.media.scanner import ContentType
from mo.nfo.paths import NFOPathResolver


class TestGetMovieNFOPath:
    """Test movie NFO path determination."""

    def test_dedicated_folder_uses_movie_nfo(self):
        """Test that dedicated folders use movie.nfo."""
        video_file = Path("/movies/Inception (2010)/Inception.mkv")
        nfo_path = NFOPathResolver.get_movie_nfo_path(
            video_file,
            ContentType.DEDICATED,
        )
        assert nfo_path == Path("/movies/Inception (2010)/movie.nfo")

    def test_mixed_folder_uses_filename_nfo(self):
        """Test that mixed folders use <filename>.nfo."""
        video_file = Path("/movies/Inception.mkv")
        nfo_path = NFOPathResolver.get_movie_nfo_path(
            video_file,
            ContentType.MIXED,
        )
        assert nfo_path == Path("/movies/Inception.nfo")

    def test_dvd_structure_uses_video_ts_nfo(self):
        """Test DVD structure uses VIDEO_TS.nfo."""
        video_file = Path("/movies/Inception (2010)/VIDEO_TS/VTS_01_1.VOB")
        nfo_path = NFOPathResolver.get_movie_nfo_path(
            video_file,
            ContentType.DEDICATED,
            is_dvd=True,
        )
        assert nfo_path == Path("/movies/Inception (2010)/VIDEO_TS/VIDEO_TS.nfo")

    def test_dvd_structure_from_parent(self):
        """Test DVD structure when already in parent directory."""
        video_file = Path("/movies/Inception (2010)/movie.iso")
        nfo_path = NFOPathResolver.get_movie_nfo_path(
            video_file,
            ContentType.DEDICATED,
            is_dvd=True,
        )
        assert nfo_path.name == "VIDEO_TS.nfo"
        assert "VIDEO_TS" in str(nfo_path)

    def test_bluray_structure_uses_bdmv_nfo(self):
        """Test Blu-ray structure uses bdmv.nfo."""
        video_file = Path("/movies/Inception (2010)/BDMV/STREAM/00000.m2ts")
        nfo_path = NFOPathResolver.get_movie_nfo_path(
            video_file,
            ContentType.DEDICATED,
            is_bluray=True,
        )
        assert nfo_path == Path("/movies/Inception (2010)/BDMV/bdmv.nfo")


class TestGetTVShowNFOPath:
    """Test TV show NFO path determination."""

    def test_tvshow_nfo_in_series_root(self):
        """Test that tvshow.nfo is placed in series root."""
        series_root = Path("/tv/Breaking Bad")
        nfo_path = NFOPathResolver.get_tvshow_nfo_path(series_root)
        assert nfo_path == Path("/tv/Breaking Bad/tvshow.nfo")


class TestGetEpisodeNFOPath:
    """Test episode NFO path determination."""

    def test_episode_nfo_matches_filename(self):
        """Test that episode NFO matches video filename."""
        video_file = Path("/tv/Breaking Bad/Season 1/S01E01.mkv")
        nfo_path = NFOPathResolver.get_episode_nfo_path(video_file)
        assert nfo_path == Path("/tv/Breaking Bad/Season 1/S01E01.nfo")

    def test_episode_nfo_different_extensions(self):
        """Test episode NFO with different video extensions."""
        for ext in [".mp4", ".avi", ".mkv", ".m4v"]:
            video_file = Path(f"/tv/Show/episode{ext}")
            nfo_path = NFOPathResolver.get_episode_nfo_path(video_file)
            assert nfo_path.suffix == ".nfo"
            assert nfo_path.stem == "episode"


class TestIsDVDStructure:
    """Test DVD structure detection."""

    def test_detects_video_ts_directory(self):
        """Test detection of VIDEO_TS directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_ts = tmp_path / "VIDEO_TS"
            video_ts.mkdir()

            assert NFOPathResolver.is_dvd_structure(tmp_path) is True

    def test_detects_video_ts_from_inside(self):
        """Test detection when path is inside VIDEO_TS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_ts = tmp_path / "VIDEO_TS"
            video_ts.mkdir()
            vob_file = video_ts / "VTS_01_1.VOB"
            vob_file.touch()

            assert NFOPathResolver.is_dvd_structure(video_ts) is True
            assert NFOPathResolver.is_dvd_structure(vob_file) is True

    def test_rejects_non_dvd_structure(self):
        """Test that non-DVD structures are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            movie_file = tmp_path / "movie.mkv"
            movie_file.touch()

            assert NFOPathResolver.is_dvd_structure(tmp_path) is False

    def test_case_insensitive_video_ts(self):
        """Test that VIDEO_TS detection is case-insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create lowercase video_ts
            video_ts = tmp_path / "video_ts"
            video_ts.mkdir()

            # Path with uppercase should still detect it
            assert NFOPathResolver.is_dvd_structure(video_ts) is True


class TestIsBlurayStructure:
    """Test Blu-ray structure detection."""

    def test_detects_bdmv_directory(self):
        """Test detection of BDMV directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            bdmv = tmp_path / "BDMV"
            bdmv.mkdir()

            assert NFOPathResolver.is_bluray_structure(tmp_path) is True

    def test_detects_bdmv_from_inside(self):
        """Test detection when path is inside BDMV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            bdmv = tmp_path / "BDMV"
            bdmv.mkdir()
            stream = bdmv / "STREAM"
            stream.mkdir()
            m2ts_file = stream / "00000.m2ts"
            m2ts_file.touch()

            assert NFOPathResolver.is_bluray_structure(bdmv) is True
            assert NFOPathResolver.is_bluray_structure(m2ts_file) is True

    def test_rejects_non_bluray_structure(self):
        """Test that non-Blu-ray structures are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            movie_file = tmp_path / "movie.mkv"
            movie_file.touch()

            assert NFOPathResolver.is_bluray_structure(tmp_path) is False

    def test_case_insensitive_bdmv(self):
        """Test that BDMV detection is case-insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create lowercase bdmv
            bdmv = tmp_path / "bdmv"
            bdmv.mkdir()

            assert NFOPathResolver.is_bluray_structure(bdmv) is True


class TestPathResolverEdgeCases:
    """Test edge cases in path resolution."""

    def test_handles_paths_with_spaces(self):
        """Test handling paths with spaces."""
        video_file = Path("/movies/The Dark Knight (2008)/The Dark Knight.mkv")
        nfo_path = NFOPathResolver.get_movie_nfo_path(
            video_file,
            ContentType.DEDICATED,
        )
        assert nfo_path == Path("/movies/The Dark Knight (2008)/movie.nfo")

    def test_handles_paths_with_special_chars(self):
        """Test handling paths with special characters."""
        video_file = Path("/tv/It's Always Sunny/Season 1/episode.mkv")
        nfo_path = NFOPathResolver.get_episode_nfo_path(video_file)
        assert nfo_path == Path("/tv/It's Always Sunny/Season 1/episode.nfo")

    def test_handles_deeply_nested_paths(self):
        """Test handling deeply nested paths."""
        video_file = Path("/media/tv/shows/Breaking Bad/Season 1/episode.mkv")
        nfo_path = NFOPathResolver.get_episode_nfo_path(video_file)
        assert nfo_path.parent == video_file.parent
        assert nfo_path.stem == video_file.stem
