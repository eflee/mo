"""Duration-based episode matching with confidence scoring."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class MatchConfidence(Enum):
    """Confidence level for episode matches."""

    EXACT = 100  # Exact duration match
    HIGH = 80  # Close match (within tolerance)
    MEDIUM = 50  # Poor match (outside tolerance but closest)


@dataclass
class EpisodeMatch:
    """Represents a matched episode."""

    episode_number: int
    expected_duration: float  # seconds
    actual_duration: float  # seconds
    confidence: MatchConfidence
    duration_diff: float  # absolute difference in seconds


class DurationMatcher:
    """Match episodes based on duration with tolerance threshold."""

    DEFAULT_TOLERANCE = 300  # ±5 minutes (300 seconds)

    def __init__(self, tolerance: float = DEFAULT_TOLERANCE):
        """Initialize duration matcher.

        Args:
            tolerance: Tolerance threshold in seconds (default: ±5 minutes)
        """
        self.tolerance = tolerance

    def match_episode(
        self,
        actual_duration: float,
        expected_durations: List[float],
    ) -> Optional[EpisodeMatch]:
        """Match an episode based on duration.

        Args:
            actual_duration: Actual file duration in seconds
            expected_durations: List of expected episode durations (indexed by episode number - 1)

        Returns:
            EpisodeMatch | None: Best match, or None if no episodes provided
        """
        if not expected_durations:
            return None

        best_match: Optional[EpisodeMatch] = None
        best_diff = float("inf")

        for episode_num, expected_duration in enumerate(expected_durations, start=1):
            diff = abs(actual_duration - expected_duration)

            if diff < best_diff:
                best_diff = diff
                confidence = self._calculate_confidence(diff)

                best_match = EpisodeMatch(
                    episode_number=episode_num,
                    expected_duration=expected_duration,
                    actual_duration=actual_duration,
                    confidence=confidence,
                    duration_diff=diff,
                )

        return best_match

    def match_episodes(
        self,
        actual_durations: List[float],
        expected_durations: List[float],
    ) -> List[Optional[EpisodeMatch]]:
        """Match multiple episodes based on durations.

        Args:
            actual_durations: List of actual file durations in seconds
            expected_durations: List of expected episode durations

        Returns:
            List[EpisodeMatch | None]: Matches for each file (in order), None if no match
        """
        matches: List[Optional[EpisodeMatch]] = []

        for actual_duration in actual_durations:
            match = self.match_episode(actual_duration, expected_durations)
            matches.append(match)

        return matches

    def _calculate_confidence(self, duration_diff: float) -> MatchConfidence:
        """Calculate confidence based on duration difference.

        Args:
            duration_diff: Absolute duration difference in seconds

        Returns:
            MatchConfidence: Confidence level
        """
        # Exact match (within 1 second)
        if duration_diff <= 1.0:
            return MatchConfidence.EXACT

        # Close match (within tolerance threshold)
        if duration_diff <= self.tolerance:
            return MatchConfidence.HIGH

        # Poor match (outside tolerance)
        return MatchConfidence.MEDIUM

    def is_confident_match(self, match: EpisodeMatch) -> bool:
        """Check if a match has sufficient confidence.

        Args:
            match: Episode match to check

        Returns:
            bool: True if confidence is EXACT or HIGH
        """
        return match.confidence in (MatchConfidence.EXACT, MatchConfidence.HIGH)
