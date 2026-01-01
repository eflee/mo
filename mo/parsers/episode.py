"""Episode filename parser compatible with Jellyfin.

Based on Jellyfin's EpisodePathParser.cs logic.
Supports multiple episode numbering patterns including standard (S##E##),
alternate (s##x##), multi-episode, date-based, and absolute numbering.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class EpisodeInfo:
    """
    Parsed episode information from a filename.

    Single Responsibility: Data structure for episode metadata.
    """

    series_name: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    ending_episode_number: Optional[int] = None
    is_daily: bool = False
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None


# Compiled regex patterns for performance (DRY - compile once)
# Based on Jellyfin's EpisodePathParser.cs

# Standard patterns: S01E02, s01x02, 1x02
_STANDARD_PATTERN = re.compile(
    r"""
    (?:s|season\s*)?              # Optional 's' or 'season '
    (?P<season>\d{1,4})           # Season number (1-4 digits)
    \s*[ex]\s*                    # Separator: 'e', 'x', or spaces
    (?P<episode>\d{1,3})          # Episode number (1-3 digits)
    (?:                           # Optional ending episodes
        \s*[-xeE]\s*              # Separator
        (?:e)?                    # Optional 'e'
        (?P<ending>\d{1,3})       # Ending episode number
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Multi-episode pattern: S01E01-E02-E03 or S01E01xE02xE03
_MULTI_EPISODE_PATTERN = re.compile(
    r"""
    (?:s|season\s*)?              # Optional 's' or 'season '
    (?P<season>\d{1,4})           # Season number
    \s*[ex]\s*                    # Separator
    (?P<episode>\d{1,3})          # Starting episode
    (?:                           # Additional episodes
        \s*[-xeE]\s*
        (?:e)?
        \d{1,3}
    )+
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Date-based pattern: 2023-01-15, 2023.01.15, 2023_01_15
_DATE_PATTERN = re.compile(
    r"""
    (?P<year>\d{4})               # Year (4 digits)
    [-._\s]                       # Separator
    (?P<month>\d{1,2})            # Month (1-2 digits)
    [-._\s]                       # Separator
    (?P<day>\d{1,2})              # Day (1-2 digits)
    """,
    re.VERBOSE,
)

# Absolute numbering pattern: Show 001.mkv, Show - 001.mkv
_ABSOLUTE_PATTERN = re.compile(
    r"""
    (?P<series>.+?)               # Series name (non-greedy)
    \s*[-_.\s]\s*                 # Separator
    (?P<episode>\d{1,3})          # Episode number
    \s*$                          # End of string (before extension)
    """,
    re.VERBOSE,
)

# Invalid season ranges (to avoid false positives with resolutions)
# Jellyfin invalidates seasons 200-1927 and >2500
_INVALID_SEASON_MIN = 200
_INVALID_SEASON_MAX = 1927
_INVALID_SEASON_THRESHOLD = 2500

# Common video resolutions to avoid treating as episode numbers
_COMMON_RESOLUTIONS = {480, 576, 720, 1080, 2160, 4320}


def _is_valid_season(season: int) -> bool:
    """
    Check if a season number is valid (not a resolution false positive).

    Args:
        season: Season number to validate

    Returns:
        bool: True if valid season number
    """
    if _INVALID_SEASON_MIN <= season <= _INVALID_SEASON_MAX:
        return False
    if season > _INVALID_SEASON_THRESHOLD:
        return False
    return True


def _is_valid_ending_episode(episode: int) -> bool:
    """
    Check if an ending episode number is valid (not a resolution).

    Args:
        episode: Episode number to validate

    Returns:
        bool: True if valid episode number
    """
    return episode not in _COMMON_RESOLUTIONS


def _clean_series_name(name: str) -> str:
    """
    Clean series name by trimming special characters.

    Jellyfin trims _, ., and - from series names extracted from filenames.

    Args:
        name: Raw series name

    Returns:
        str: Cleaned series name
    """
    if not name:
        return ""

    # Replace underscores, dots, and dashes with spaces
    cleaned = name.replace("_", " ").replace(".", " ").replace("-", " ")

    # Replace multiple spaces with single space
    cleaned = " ".join(cleaned.split())

    # Trim whitespace
    cleaned = cleaned.strip()

    return cleaned


def parse_episode_filename(filename: str) -> Optional[EpisodeInfo]:
    """
    Parse episode information from a filename.

    Single Responsibility: Only parses filename patterns.

    This function attempts to extract episode information using multiple
    patterns in order of specificity:
    1. Standard patterns (S##E##, s##x##)
    2. Multi-episode patterns
    3. Date-based patterns
    4. Absolute numbering patterns

    Args:
        filename: Episode filename (can include path)

    Returns:
        EpisodeInfo | None: Parsed episode info, or None if no match

    Examples:
        >>> parse_episode_filename("Show.S01E05.mkv")
        EpisodeInfo(series_name="Show", season_number=1, episode_number=5)

        >>> parse_episode_filename("Show.2x03.avi")
        EpisodeInfo(series_name=None, season_number=2, episode_number=3)

        >>> parse_episode_filename("Show.S01E01-E02.mkv")
        EpisodeInfo(season_number=1, episode_number=1, ending_episode_number=2)
    """
    # Extract filename without path and extension
    path = Path(filename)
    name = path.stem

    # Try multi-episode pattern FIRST (more specific than standard pattern)
    match = _MULTI_EPISODE_PATTERN.search(name)
    if match:
        season = int(match.group("season"))
        episode = int(match.group("episode"))

        # Validate season
        if not _is_valid_season(season):
            pass
        else:
            # Extract all episode numbers from the multi-episode pattern
            # Find all additional episode numbers (excluding the first one)
            full_match = match.group(0)
            # Find the position after the first episode number
            first_ep_match = re.search(r"[ex](\d{1,3})", full_match, re.IGNORECASE)
            if first_ep_match:
                after_first = full_match[first_ep_match.end():]
                # Extract subsequent episode numbers
                additional_episodes = re.findall(r"(?:[ex-]|e)(\d{1,3})", after_first, re.IGNORECASE)
                all_episodes = [episode] + [int(e) for e in additional_episodes]
            else:
                all_episodes = [episode]

            # Filter out invalid episode numbers (resolutions)
            valid_episodes = [e for e in all_episodes if _is_valid_ending_episode(e)]

            ending_num = valid_episodes[-1] if len(valid_episodes) > 1 else None

            series_name = name[: match.start()].strip()
            series_name = _clean_series_name(series_name) if series_name else None

            return EpisodeInfo(
                series_name=series_name,
                season_number=season,
                episode_number=episode,
                ending_episode_number=ending_num,
            )

    # Try standard pattern (S##E##, s##x##)
    match = _STANDARD_PATTERN.search(name)
    if match:
        season = int(match.group("season"))
        episode = int(match.group("episode"))
        ending = match.group("ending")

        # Validate season number
        if not _is_valid_season(season):
            # Continue to next pattern
            pass
        else:
            # Validate ending episode if present
            ending_num = None
            if ending:
                ending_val = int(ending)
                if _is_valid_ending_episode(ending_val):
                    ending_num = ending_val

            # Extract series name (everything before the match)
            series_name = name[: match.start()].strip()
            series_name = _clean_series_name(series_name) if series_name else None

            return EpisodeInfo(
                series_name=series_name,
                season_number=season,
                episode_number=episode,
                ending_episode_number=ending_num,
            )

    # Try date-based pattern
    match = _DATE_PATTERN.search(name)
    if match:
        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))

        # Validate date
        try:
            datetime(year, month, day)
        except ValueError:
            # Invalid date, skip
            pass
        else:
            series_name = name[: match.start()].strip()
            series_name = _clean_series_name(series_name) if series_name else None

            return EpisodeInfo(
                series_name=series_name,
                is_daily=True,
                year=year,
                month=month,
                day=day,
            )

    # Try absolute numbering (least specific, try last)
    match = _ABSOLUTE_PATTERN.match(name)
    if match:
        series = match.group("series")
        episode = int(match.group("episode"))

        series_name = _clean_series_name(series)

        # Only return if we have a valid series name
        if series_name:
            return EpisodeInfo(
                series_name=series_name,
                episode_number=episode,
                # Season is not determined from absolute numbering
                season_number=None,
            )

    # No pattern matched
    return None


def extract_all_episode_numbers(filename: str) -> List[int]:
    """
    Extract all episode numbers from a multi-episode filename.

    Single Responsibility: Only extracts episode number list.

    Args:
        filename: Episode filename

    Returns:
        List[int]: List of all episode numbers (e.g., [1, 2, 3] for S01E01-E02-E03)

    Examples:
        >>> extract_all_episode_numbers("Show.S01E01-E02-E03.mkv")
        [1, 2, 3]

        >>> extract_all_episode_numbers("Show.S01E05.mkv")
        [5]
    """
    path = Path(filename)
    name = path.stem

    # Try multi-episode pattern first
    match = _MULTI_EPISODE_PATTERN.search(name)
    if match:
        season = int(match.group("season"))
        episode = int(match.group("episode"))

        if _is_valid_season(season):
            # Extract all episode numbers
            full_match = match.group(0)
            # Find the position after the first episode number
            first_ep_match = re.search(r"[ex](\d{1,3})", full_match, re.IGNORECASE)
            if first_ep_match:
                after_first = full_match[first_ep_match.end():]
                # Extract subsequent episode numbers
                additional_episodes = re.findall(r"(?:[ex-]|e)(\d{1,3})", after_first, re.IGNORECASE)
                episode_nums = [episode] + [int(e) for e in additional_episodes]

                # Check if this is a range (only 2 episodes with dash separator)
                if len(episode_nums) == 2 and '-' in full_match:
                    # Generate range
                    all_episodes = list(range(episode_nums[0], episode_nums[1] + 1))
                else:
                    all_episodes = episode_nums
            else:
                all_episodes = [episode]

            # Filter out invalid episode numbers (resolutions)
            return [e for e in all_episodes if _is_valid_ending_episode(e)]

    # Try standard pattern
    match = _STANDARD_PATTERN.search(name)
    if match:
        season = int(match.group("season"))
        episode = int(match.group("episode"))
        ending = match.group("ending")

        if _is_valid_season(season):
            if ending:
                ending_val = int(ending)
                if _is_valid_ending_episode(ending_val):
                    return list(range(episode, ending_val + 1))
            return [episode]

    # Single episode or no match
    info = parse_episode_filename(filename)
    if info and info.episode_number:
        return [info.episode_number]

    return []
