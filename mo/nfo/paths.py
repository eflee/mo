"""NFO file path determination logic for Jellyfin."""

from pathlib import Path

from mo.media.scanner import ContentType


class NFOPathResolver:
    """Resolve NFO file paths based on content type and folder structure."""

    @staticmethod
    def get_movie_nfo_path(
        video_file: Path,
        content_type: ContentType,
        is_dvd: bool = False,
        is_bluray: bool = False,
    ) -> Path:
        """Determine the NFO path for a movie.

        Args:
            video_file: Path to the main video file
            content_type: Content type (DEDICATED or MIXED)
            is_dvd: True if this is a DVD folder structure
            is_bluray: True if this is a Blu-ray folder structure

        Returns:
            Path: Path where the movie NFO should be written
        """
        # DVD structure: VIDEO_TS/VIDEO_TS.nfo
        if is_dvd:
            video_ts_dir = video_file.parent
            if video_ts_dir.name.upper() == "VIDEO_TS":
                return video_ts_dir / "VIDEO_TS.nfo"
            # If we're already in the parent of VIDEO_TS
            return video_ts_dir / "VIDEO_TS" / "VIDEO_TS.nfo"

        # Blu-ray structure: BDMV/bdmv.nfo (placeholder, not standard Jellyfin)
        if is_bluray:
            # Navigate up to find BDMV directory
            current = video_file.parent if video_file.is_file() else video_file
            while current and current.name:
                if current.name.upper() == "BDMV":
                    return current / "bdmv.nfo"
                current = current.parent
            # If BDMV not found in parents, assume we need to create it
            return video_file.parent / "BDMV" / "bdmv.nfo"

        # Dedicated folder: movie.nfo in the same directory as the video
        if content_type == ContentType.DEDICATED:
            return video_file.parent / "movie.nfo"

        # Mixed folder: <filename>.nfo
        return video_file.with_suffix(".nfo")

    @staticmethod
    def get_tvshow_nfo_path(series_root: Path) -> Path:
        """Determine the NFO path for a TV show.

        Args:
            series_root: Root directory of the TV series

        Returns:
            Path: Path where tvshow.nfo should be written
        """
        return series_root / "tvshow.nfo"

    @staticmethod
    def get_episode_nfo_path(video_file: Path) -> Path:
        """Determine the NFO path for an episode.

        Args:
            video_file: Path to the episode video file

        Returns:
            Path: Path where the episode NFO should be written
        """
        # Episode NFO always matches the video filename
        return video_file.with_suffix(".nfo")

    @staticmethod
    def is_dvd_structure(path: Path) -> bool:
        """Check if a path is part of a DVD structure.

        Args:
            path: Path to check

        Returns:
            bool: True if this is a DVD structure
        """
        # Check if path contains VIDEO_TS directory
        if path.is_file():
            path = path.parent

        # Check current directory
        if path.name.upper() == "VIDEO_TS":
            return True

        # Check subdirectories
        video_ts = path / "VIDEO_TS"
        return video_ts.exists() and video_ts.is_dir()

    @staticmethod
    def is_bluray_structure(path: Path) -> bool:
        """Check if a path is part of a Blu-ray structure.

        Args:
            path: Path to check

        Returns:
            bool: True if this is a Blu-ray structure
        """
        # Check if path contains BDMV directory
        if path.is_file():
            path = path.parent

        # Check current directory and parents
        current = path
        while current and current.name:
            if current.name.upper() == "BDMV":
                return True
            current = current.parent

        # Check subdirectories
        bdmv = path / "BDMV"
        return bdmv.exists() and bdmv.is_dir()
