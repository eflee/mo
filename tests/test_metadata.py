"""Tests for media metadata extraction."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mo.media.metadata import AudioTrack, MediaInfo, MediaMetadataExtractor, VideoTrack


class TestMediaMetadataExtractor:
    """Test metadata extractor initialization."""

    def test_init_requires_pymediainfo(self):
        """Test that initialization checks for pymediainfo."""
        with patch("mo.media.metadata.PyMediaInfo", None):
            with pytest.raises(ImportError, match="pymediainfo is required"):
                MediaMetadataExtractor()

    def test_init_success(self):
        """Test successful initialization."""
        extractor = MediaMetadataExtractor()
        assert extractor is not None


class TestExtractMetadata:
    """Test metadata extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a metadata extractor for testing."""
        return MediaMetadataExtractor()

    @pytest.fixture
    def mock_media_info(self):
        """Mock pymediainfo response."""
        # Create mock tracks
        general_track = Mock()
        general_track.track_type = "General"
        general_track.duration = 3600000  # 1 hour in milliseconds

        video_track = Mock()
        video_track.track_type = "Video"
        video_track.codec_id = "avc1"
        video_track.format = "AVC"
        video_track.width = 1920
        video_track.height = 1080
        video_track.duration = 3600000
        video_track.frame_rate = 23.976

        audio_track = Mock()
        audio_track.track_type = "Audio"
        audio_track.codec_id = "mp4a"
        audio_track.format = "AAC"
        audio_track.language = "en"
        audio_track.channel_s = 2

        # Create mock MediaInfo
        mock_info = Mock()
        mock_info.tracks = [general_track, video_track, audio_track]

        return mock_info

    def test_extract_success(self, extractor, mock_media_info):
        """Test successful metadata extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_file = tmp_path / "video.mp4"
            video_file.write_text("fake video content")

            with patch("mo.media.metadata.PyMediaInfo.parse", return_value=mock_media_info):
                info = extractor.extract(video_file)

            assert info is not None
            assert info.file_path == video_file
            assert info.duration == 3600.0  # seconds
            assert info.file_size > 0

            # Check video track
            assert len(info.video_tracks) == 1
            video = info.video_tracks[0]
            assert video.codec == "avc1"
            assert video.width == 1920
            assert video.height == 1080
            assert video.duration == 3600.0
            assert video.frame_rate == 23.976

            # Check audio track
            assert len(info.audio_tracks) == 1
            audio = info.audio_tracks[0]
            assert audio.codec == "mp4a"
            assert audio.language == "en"
            assert audio.channels == 2

    def test_extract_nonexistent_file(self, extractor):
        """Test extraction of nonexistent file returns None."""
        nonexistent = Path("/nonexistent/file.mp4")
        info = extractor.extract(nonexistent)

        assert info is None

    def test_extract_handles_errors(self, extractor):
        """Test that extraction handles errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_file = tmp_path / "video.mp4"
            video_file.write_text("corrupted")

            with patch("mo.media.metadata.PyMediaInfo.parse", side_effect=Exception("Parse error")):
                info = extractor.extract(video_file)

            assert info is None

    def test_extract_no_duration_uses_video_track(self, extractor):
        """Test that video track duration is used if general track has no duration."""
        # Mock with no general track duration
        video_track = Mock()
        video_track.track_type = "Video"
        video_track.codec_id = "avc1"
        video_track.format = None
        video_track.width = 1920
        video_track.height = 1080
        video_track.duration = 7200000  # 2 hours
        video_track.frame_rate = None

        general_track = Mock()
        general_track.track_type = "General"
        general_track.duration = None

        mock_info = Mock()
        mock_info.tracks = [general_track, video_track]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_file = tmp_path / "video.mp4"
            video_file.write_text("test")

            with patch("mo.media.metadata.PyMediaInfo.parse", return_value=mock_info):
                info = extractor.extract(video_file)

            assert info.duration == 7200.0

    def test_extract_no_tracks(self, extractor):
        """Test extraction with no video/audio tracks."""
        general_track = Mock()
        general_track.track_type = "General"
        general_track.duration = 1000

        mock_info = Mock()
        mock_info.tracks = [general_track]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_file = tmp_path / "video.mp4"
            video_file.write_text("test")

            with patch("mo.media.metadata.PyMediaInfo.parse", return_value=mock_info):
                info = extractor.extract(video_file)

            assert info.duration == 1.0
            assert info.video_tracks is None
            assert info.audio_tracks is None

    def test_get_duration_convenience_method(self, extractor, mock_media_info):
        """Test get_duration convenience method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_file = tmp_path / "video.mp4"
            video_file.write_text("test")

            with patch("mo.media.metadata.PyMediaInfo.parse", return_value=mock_media_info):
                duration = extractor.get_duration(video_file)

            assert duration == 3600.0

    def test_get_duration_nonexistent_file(self, extractor):
        """Test get_duration with nonexistent file."""
        nonexistent = Path("/nonexistent/file.mp4")
        duration = extractor.get_duration(nonexistent)

        assert duration is None


class TestVideoTrack:
    """Test VideoTrack dataclass."""

    def test_video_track_creation(self):
        """Test creating a video track."""
        track = VideoTrack(
            codec="H264",
            width=1920,
            height=1080,
            duration=3600.0,
            frame_rate=24.0,
        )

        assert track.codec == "H264"
        assert track.width == 1920
        assert track.height == 1080
        assert track.duration == 3600.0
        assert track.frame_rate == 24.0

    def test_video_track_defaults(self):
        """Test video track with default values."""
        track = VideoTrack()

        assert track.codec is None
        assert track.width is None
        assert track.height is None
        assert track.duration is None
        assert track.frame_rate is None


class TestAudioTrack:
    """Test AudioTrack dataclass."""

    def test_audio_track_creation(self):
        """Test creating an audio track."""
        track = AudioTrack(
            codec="AAC",
            language="en",
            channels=2,
        )

        assert track.codec == "AAC"
        assert track.language == "en"
        assert track.channels == 2

    def test_audio_track_defaults(self):
        """Test audio track with default values."""
        track = AudioTrack()

        assert track.codec is None
        assert track.language is None
        assert track.channels is None


class TestMediaInfo:
    """Test MediaInfo dataclass."""

    def test_media_info_creation(self):
        """Test creating media info."""
        video_track = VideoTrack(codec="H264", width=1920, height=1080)
        audio_track = AudioTrack(codec="AAC", channels=2)

        info = MediaInfo(
            file_path=Path("video.mp4"),
            duration=3600.0,
            file_size=1024000,
            video_tracks=[video_track],
            audio_tracks=[audio_track],
        )

        assert info.file_path == Path("video.mp4")
        assert info.duration == 3600.0
        assert info.file_size == 1024000
        assert len(info.video_tracks) == 1
        assert len(info.audio_tracks) == 1

    def test_media_info_defaults(self):
        """Test media info with default values."""
        info = MediaInfo(file_path=Path("video.mp4"))

        assert info.file_path == Path("video.mp4")
        assert info.duration is None
        assert info.file_size is None
        assert info.video_tracks is None
        assert info.audio_tracks is None
