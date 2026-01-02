"""Media metadata extraction using pymediainfo."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from pymediainfo import MediaInfo as PyMediaInfo
except ImportError:
    PyMediaInfo = None


@dataclass
class VideoTrack:
    """Video track information."""

    codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None  # seconds
    frame_rate: Optional[float] = None


@dataclass
class AudioTrack:
    """Audio track information."""

    codec: Optional[str] = None
    language: Optional[str] = None
    channels: Optional[int] = None


@dataclass
class MediaInfo:
    """Complete media file information."""

    file_path: Path
    duration: Optional[float] = None  # seconds
    file_size: Optional[int] = None  # bytes
    video_tracks: Optional[List[VideoTrack]] = None
    audio_tracks: Optional[List[AudioTrack]] = None


class MediaMetadataExtractor:
    """Extract metadata from media files using pymediainfo."""

    def __init__(self):
        """Initialize metadata extractor.

        Raises:
            ImportError: If pymediainfo is not installed
        """
        if PyMediaInfo is None:
            raise ImportError(
                "pymediainfo is required for metadata extraction. "
                "Install it with: pip install pymediainfo"
            )

    def extract(self, file_path: Path) -> Optional[MediaInfo]:
        """Extract metadata from a media file.

        Args:
            file_path: Path to media file

        Returns:
            MediaInfo | None: Extracted metadata, or None if extraction fails
        """
        if not file_path.is_file():
            return None

        try:
            # Get file size
            file_size = file_path.stat().st_size

            # Parse media info
            media_info = PyMediaInfo.parse(str(file_path))

            # Extract duration (use general track if available, otherwise video track)
            duration = None
            for track in media_info.tracks:
                if track.track_type == "General" and track.duration:
                    duration = track.duration / 1000.0  # Convert ms to seconds
                    break

            # Extract video tracks
            video_tracks = []
            for track in media_info.tracks:
                if track.track_type == "Video":
                    video_track = VideoTrack(
                        codec=track.codec_id or track.format,
                        width=track.width,
                        height=track.height,
                        duration=track.duration / 1000.0 if track.duration else None,
                        frame_rate=float(track.frame_rate) if track.frame_rate else None,
                    )
                    video_tracks.append(video_track)

                    # Use video duration if general duration not found
                    if duration is None and track.duration:
                        duration = track.duration / 1000.0

            # Extract audio tracks
            audio_tracks = []
            for track in media_info.tracks:
                if track.track_type == "Audio":
                    audio_track = AudioTrack(
                        codec=track.codec_id or track.format,
                        language=track.language,
                        channels=track.channel_s,
                    )
                    audio_tracks.append(audio_track)

            return MediaInfo(
                file_path=file_path,
                duration=duration,
                file_size=file_size,
                video_tracks=video_tracks if video_tracks else None,
                audio_tracks=audio_tracks if audio_tracks else None,
            )

        except (OSError, PermissionError, Exception):
            # Handle corrupted or inaccessible files gracefully
            return None

    def get_duration(self, file_path: Path) -> Optional[float]:
        """Get duration of a media file (convenience method).

        Args:
            file_path: Path to media file

        Returns:
            float | None: Duration in seconds, or None if extraction fails
        """
        media_info = self.extract(file_path)
        return media_info.duration if media_info else None
