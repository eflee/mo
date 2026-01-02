"""Tests for media scanner."""

import tempfile
from pathlib import Path

import pytest

from mo.media.scanner import ContentType, MediaScanner, ScanResult


class TestMediaScanner:
    """Test media scanner initialization."""

    def test_init_default(self):
        """Test scanner initialization with defaults."""
        scanner = MediaScanner()
        assert scanner.max_depth is None

    def test_init_with_depth(self):
        """Test scanner initialization with max depth."""
        scanner = MediaScanner(max_depth=3)
        assert scanner.max_depth == 3


class TestScanDirectory:
    """Test directory scanning."""

    @pytest.fixture
    def scanner(self):
        """Create a scanner for testing."""
        return MediaScanner()

    @pytest.fixture
    def temp_media_dir(self):
        """Create a temporary directory with media files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create video files
            (tmp_path / "movie.mp4").touch()
            (tmp_path / "video.mkv").touch()
            (tmp_path / "show.avi").touch()

            # Create subtitle files
            (tmp_path / "movie.srt").touch()
            (tmp_path / "video.sub").touch()

            # Create non-media files
            (tmp_path / "readme.txt").touch()
            (tmp_path / "poster.jpg").touch()

            yield tmp_path

    def test_scan_directory_finds_media(self, scanner, temp_media_dir):
        """Test that scanner finds media files."""
        result = scanner.scan_directory(temp_media_dir)

        assert isinstance(result, ScanResult)
        assert len(result.video_files) == 3
        assert len(result.subtitle_files) == 2

        # Check video file extensions
        video_extensions = {vf.extension for vf in result.video_files}
        assert video_extensions == {".mp4", ".mkv", ".avi"}

        # Check subtitle file extensions
        subtitle_extensions = {sf.extension for sf in result.subtitle_files}
        assert subtitle_extensions == {".srt", ".sub"}

    def test_scan_directory_invalid_path(self, scanner, temp_media_dir):
        """Test scanning invalid path raises error."""
        invalid_path = temp_media_dir / "nonexistent"

        with pytest.raises(ValueError, match="not a directory"):
            scanner.scan_directory(invalid_path)

    def test_scan_directory_with_subdirectories(self, scanner):
        """Test scanning with subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create nested structure
            season1 = tmp_path / "Season 1"
            season1.mkdir()
            (season1 / "episode1.mp4").touch()
            (season1 / "episode2.mkv").touch()

            season2 = tmp_path / "Season 2"
            season2.mkdir()
            (season2 / "episode1.mp4").touch()

            result = scanner.scan_directory(tmp_path)

            assert len(result.video_files) == 3

    def test_scan_directory_respects_max_depth(self):
        """Test that max depth is respected."""
        scanner = MediaScanner(max_depth=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create file at root
            (tmp_path / "root.mp4").touch()

            # Create nested file (should be ignored)
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            (subdir / "nested.mp4").touch()

            result = scanner.scan_directory(tmp_path)

            assert len(result.video_files) == 1
            assert result.video_files[0].path.name == "root.mp4"

    def test_scan_directory_ignores_hidden_files(self, scanner):
        """Test that hidden files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create regular file
            (tmp_path / "visible.mp4").touch()

            # Create hidden file
            (tmp_path / ".hidden.mp4").touch()

            # Create hidden directory
            hidden_dir = tmp_path / ".hidden_dir"
            hidden_dir.mkdir()
            (hidden_dir / "video.mp4").touch()

            result = scanner.scan_directory(tmp_path)

            assert len(result.video_files) == 1
            assert result.video_files[0].path.name == "visible.mp4"

    def test_scan_directory_ignores_system_files(self, scanner):
        """Test that system files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create media file
            (tmp_path / "video.mp4").touch()

            # Create system files
            (tmp_path / ".DS_Store").touch()
            (tmp_path / "Thumbs.db").touch()
            (tmp_path / "desktop.ini").touch()

            result = scanner.scan_directory(tmp_path)

            assert len(result.video_files) == 1

    def test_scan_directory_ignores_sample_files(self, scanner):
        """Test that sample files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create regular file
            (tmp_path / "movie.mp4").touch()

            # Create sample files
            (tmp_path / "sample.mp4").touch()
            (tmp_path / "Sample.mkv").touch()
            (tmp_path / "movie-SAMPLE.avi").touch()

            result = scanner.scan_directory(tmp_path)

            assert len(result.video_files) == 1
            assert result.video_files[0].path.name == "movie.mp4"


class TestMediaFileDetection:
    """Test media file detection."""

    @pytest.fixture
    def scanner(self):
        """Create a scanner for testing."""
        return MediaScanner()

    def test_check_media_file_video(self, scanner):
        """Test video file detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Test all video extensions
            for ext in MediaScanner.VIDEO_EXTENSIONS:
                video_file = tmp_path / f"video{ext}"
                video_file.write_text("test")

                media_file = scanner._check_media_file(video_file)

                assert media_file is not None
                assert media_file.file_type == "video"
                assert media_file.extension == ext
                assert media_file.size > 0

    def test_check_media_file_subtitle(self, scanner):
        """Test subtitle file detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Test all subtitle extensions
            for ext in MediaScanner.SUBTITLE_EXTENSIONS:
                subtitle_file = tmp_path / f"subtitle{ext}"
                subtitle_file.write_text("test")

                media_file = scanner._check_media_file(subtitle_file)

                assert media_file is not None
                assert media_file.file_type == "subtitle"
                assert media_file.extension == ext

    def test_check_media_file_non_media(self, scanner):
        """Test non-media file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            text_file = tmp_path / "readme.txt"
            text_file.touch()

            media_file = scanner._check_media_file(text_file)

            assert media_file is None

    def test_check_media_file_case_insensitive(self, scanner):
        """Test that extension matching is case insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Test uppercase extension
            video_file = tmp_path / "video.MP4"
            video_file.touch()

            media_file = scanner._check_media_file(video_file)

            assert media_file is not None
            assert media_file.extension == ".mp4"


class TestContentTypeDetection:
    """Test content type detection."""

    @pytest.fixture
    def scanner(self):
        """Create a scanner for testing."""
        return MediaScanner()

    def test_detect_content_type_single_file(self, scanner):
        """Test dedicated content type with single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "movie.mp4").touch()

            result = scanner.scan_directory(tmp_path)

            assert result.content_type == ContentType.DEDICATED

    def test_detect_content_type_tv_show_seasons(self, scanner):
        """Test dedicated content type for TV show with seasons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create season folders
            season1 = tmp_path / "Season 1"
            season1.mkdir()
            (season1 / "episode1.mp4").touch()
            (season1 / "episode2.mp4").touch()

            season2 = tmp_path / "Season 2"
            season2.mkdir()
            (season2 / "episode1.mp4").touch()

            result = scanner.scan_directory(tmp_path)

            assert result.content_type == ContentType.DEDICATED

    def test_detect_content_type_mixed(self, scanner):
        """Test mixed content type with multiple movies at root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create multiple videos at root level in different folders
            movie1_dir = tmp_path / "Movie 1"
            movie1_dir.mkdir()
            (movie1_dir / "movie1.mp4").touch()

            movie2_dir = tmp_path / "Movie 2"
            movie2_dir.mkdir()
            (movie2_dir / "movie2.mp4").touch()

            result = scanner.scan_directory(tmp_path)

            # This should be MIXED (multiple different items)
            assert result.content_type == ContentType.MIXED

    def test_detect_content_type_single_season(self, scanner):
        """Test dedicated content type for single season."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            season = tmp_path / "Season 1"
            season.mkdir()
            (season / "ep1.mp4").touch()
            (season / "ep2.mp4").touch()
            (season / "ep3.mp4").touch()

            result = scanner.scan_directory(tmp_path)

            assert result.content_type == ContentType.DEDICATED


class TestIgnorePatterns:
    """Test ignore pattern matching."""

    @pytest.fixture
    def scanner(self):
        """Create a scanner for testing."""
        return MediaScanner()

    def test_should_ignore_hidden_files(self, scanner):
        """Test that hidden files are ignored."""
        hidden_file = Path(".hidden")
        assert scanner._should_ignore(hidden_file) is True

    def test_should_ignore_system_files(self, scanner):
        """Test that system files are ignored."""
        for pattern in [".DS_Store", "Thumbs.db", "desktop.ini"]:
            path = Path(pattern)
            assert scanner._should_ignore(path) is True

    def test_should_ignore_sample_files(self, scanner):
        """Test that sample files are ignored."""
        for name in ["sample.mp4", "Sample.mkv", "SAMPLE.avi", "movie-sample.mp4"]:
            path = Path(name)
            assert scanner._should_ignore(path) is True

    def test_should_not_ignore_regular_files(self, scanner):
        """Test that regular files are not ignored."""
        regular_file = Path("movie.mp4")
        assert scanner._should_ignore(regular_file) is False
