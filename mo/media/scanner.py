"""Media file scanning and detection."""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set


class ContentType(Enum):
    """Content type for a directory."""

    DEDICATED = "dedicated"  # Single media item (movie or TV show)
    MIXED = "mixed"  # Multiple media items


@dataclass
class MediaFile:
    """Represents a detected media file."""

    path: Path
    file_type: str  # "video" or "subtitle"
    extension: str
    size: int  # bytes


@dataclass
class ScanResult:
    """Result of a directory scan."""

    root_path: Path
    video_files: List[MediaFile]
    subtitle_files: List[MediaFile]
    content_type: ContentType


class MediaScanner:
    """Scanner for media files in directories."""

    # Video file extensions (Jellyfin compatible)
    VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".m4v", ".mov", ".wmv", ".flv", ".webm"}

    # Subtitle file extensions
    SUBTITLE_EXTENSIONS = {".srt", ".sub", ".ass", ".ssa", ".vtt"}

    # Files and directories to ignore
    IGNORE_PATTERNS = {
        # System files
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        # Hidden directories
        ".git",
        ".svn",
        "__pycache__",
        # Sample files
        "sample",
        "Sample",
        "SAMPLE",
    }

    def __init__(self, max_depth: Optional[int] = None):
        """Initialize media scanner.

        Args:
            max_depth: Maximum directory depth to scan (None for unlimited)
        """
        self.max_depth = max_depth

    def scan_directory(self, path: Path) -> ScanResult:
        """Scan a directory for media files.

        Args:
            path: Directory path to scan

        Returns:
            ScanResult: Scan results including detected files and content type

        Raises:
            ValueError: If path is not a directory
        """
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        video_files: List[MediaFile] = []
        subtitle_files: List[MediaFile] = []

        # Scan for media files
        self._scan_recursive(path, path, video_files, subtitle_files, depth=0)

        # Detect content type
        content_type = self._detect_content_type(path, video_files)

        return ScanResult(
            root_path=path,
            video_files=video_files,
            subtitle_files=subtitle_files,
            content_type=content_type,
        )

    def _scan_recursive(
        self,
        root: Path,
        current: Path,
        video_files: List[MediaFile],
        subtitle_files: List[MediaFile],
        depth: int,
    ) -> None:
        """Recursively scan directory for media files.

        Args:
            root: Root directory being scanned
            current: Current directory
            video_files: List to append video files to
            subtitle_files: List to append subtitle files to
            depth: Current recursion depth
        """
        # Check depth limit
        if self.max_depth is not None and depth > self.max_depth:
            return

        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            # Skip inaccessible directories
            return

        for entry in entries:
            # Skip hidden files and ignore patterns
            if self._should_ignore(entry):
                continue

            if entry.is_file():
                # Check if it's a media file
                media_file = self._check_media_file(entry)
                if media_file:
                    if media_file.file_type == "video":
                        video_files.append(media_file)
                    elif media_file.file_type == "subtitle":
                        subtitle_files.append(media_file)

            elif entry.is_dir():
                # Recursively scan subdirectory
                self._scan_recursive(root, entry, video_files, subtitle_files, depth + 1)

    def _should_ignore(self, path: Path) -> bool:
        """Check if a file or directory should be ignored.

        Args:
            path: Path to check

        Returns:
            bool: True if should be ignored
        """
        # Check if hidden (starts with .)
        if path.name.startswith("."):
            return True

        # Check ignore patterns
        if path.name in self.IGNORE_PATTERNS:
            return True

        # Check if path contains sample pattern
        if "sample" in path.name.lower():
            return True

        return False

    def _check_media_file(self, path: Path) -> Optional[MediaFile]:
        """Check if a file is a media file.

        Args:
            path: File path to check

        Returns:
            MediaFile | None: MediaFile if valid, None otherwise
        """
        extension = path.suffix.lower()

        # Check for video file
        if extension in self.VIDEO_EXTENSIONS:
            try:
                size = path.stat().st_size
                return MediaFile(
                    path=path,
                    file_type="video",
                    extension=extension,
                    size=size,
                )
            except (OSError, PermissionError):
                # Skip inaccessible files
                return None

        # Check for subtitle file
        elif extension in self.SUBTITLE_EXTENSIONS:
            try:
                size = path.stat().st_size
                return MediaFile(
                    path=path,
                    file_type="subtitle",
                    extension=extension,
                    size=size,
                )
            except (OSError, PermissionError):
                # Skip inaccessible files
                return None

        return None

    def _detect_content_type(self, root: Path, video_files: List[MediaFile]) -> ContentType:
        """Detect content type based on directory structure and files.

        A directory is considered DEDICATED if:
        - It contains a single video file, OR
        - All video files are in the same immediate subdirectory (e.g., Season folders)

        Otherwise, it's MIXED.

        Args:
            root: Root directory path
            video_files: List of video files found

        Returns:
            ContentType: Detected content type
        """
        if len(video_files) <= 1:
            return ContentType.DEDICATED

        # Get unique parent directories of video files (relative to root)
        parent_dirs: Set[Path] = set()
        for video in video_files:
            # Get parent relative to root
            try:
                relative = video.path.parent.relative_to(root)
                parent_dirs.add(relative)
            except ValueError:
                # File is not under root (shouldn't happen)
                pass

        # If all videos are in subdirectories (not root directly)
        if len(parent_dirs) > 0 and all(parent != Path(".") for parent in parent_dirs):
            # Check if they're all in season-like subdirectories
            # This would be DEDICATED (TV show with seasons)
            parent_names = {p.name.lower() for p in parent_dirs}
            if all("season" in name or name.startswith("s") for name in parent_names):
                return ContentType.DEDICATED

        # If videos are spread across multiple directories at root level, it's MIXED
        if len(parent_dirs) > 1:
            return ContentType.MIXED

        # Single directory with multiple videos - likely DEDICATED (TV season)
        return ContentType.DEDICATED
