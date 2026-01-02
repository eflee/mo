"""Tests for duration-based episode matching."""

import pytest

from mo.media.matcher import DurationMatcher, EpisodeMatch, MatchConfidence


class TestDurationMatcher:
    """Test duration matcher initialization."""

    def test_init_default(self):
        """Test matcher initialization with default tolerance."""
        matcher = DurationMatcher()
        assert matcher.tolerance == 300  # 5 minutes

    def test_init_custom_tolerance(self):
        """Test matcher initialization with custom tolerance."""
        matcher = DurationMatcher(tolerance=600)
        assert matcher.tolerance == 600


class TestMatchEpisode:
    """Test single episode matching."""

    @pytest.fixture
    def matcher(self):
        """Create a matcher for testing."""
        return DurationMatcher()

    def test_match_episode_exact(self, matcher):
        """Test exact duration match."""
        expected_durations = [1800.0, 2400.0, 1900.0]  # 30m, 40m, ~31m
        actual_duration = 2400.0  # Exactly 40 minutes

        match = matcher.match_episode(actual_duration, expected_durations)

        assert match is not None
        assert match.episode_number == 2
        assert match.expected_duration == 2400.0
        assert match.actual_duration == 2400.0
        assert match.confidence == MatchConfidence.EXACT
        assert match.duration_diff == 0.0

    def test_match_episode_within_tolerance(self, matcher):
        """Test match within tolerance threshold."""
        expected_durations = [2400.0]  # 40 minutes
        actual_duration = 2500.0  # 41:40 (100 seconds difference)

        match = matcher.match_episode(actual_duration, expected_durations)

        assert match is not None
        assert match.episode_number == 1
        assert match.confidence == MatchConfidence.HIGH
        assert match.duration_diff == 100.0

    def test_match_episode_outside_tolerance(self, matcher):
        """Test match outside tolerance threshold."""
        expected_durations = [2400.0]  # 40 minutes
        actual_duration = 3000.0  # 50 minutes (600 seconds difference)

        match = matcher.match_episode(actual_duration, expected_durations)

        assert match is not None
        assert match.episode_number == 1
        assert match.confidence == MatchConfidence.MEDIUM
        assert match.duration_diff == 600.0

    def test_match_episode_closest_match(self, matcher):
        """Test that closest match is selected."""
        expected_durations = [1800.0, 2400.0, 3000.0]  # 30m, 40m, 50m
        actual_duration = 2350.0  # ~39 minutes

        match = matcher.match_episode(actual_duration, expected_durations)

        assert match is not None
        assert match.episode_number == 2  # Closest to 40m
        assert match.expected_duration == 2400.0
        assert match.duration_diff == 50.0

    def test_match_episode_empty_list(self, matcher):
        """Test matching with empty expected durations."""
        match = matcher.match_episode(2400.0, [])

        assert match is None

    def test_match_episode_single_option(self, matcher):
        """Test matching with single expected duration."""
        expected_durations = [2400.0]
        actual_duration = 2200.0

        match = matcher.match_episode(actual_duration, expected_durations)

        assert match is not None
        assert match.episode_number == 1
        assert match.duration_diff == 200.0


class TestMatchEpisodes:
    """Test multiple episode matching."""

    @pytest.fixture
    def matcher(self):
        """Create a matcher for testing."""
        return DurationMatcher()

    def test_match_episodes_all_match(self, matcher):
        """Test matching multiple episodes successfully."""
        expected_durations = [1800.0, 2400.0, 1900.0]
        actual_durations = [1805.0, 2395.0, 1895.0]  # Close matches

        matches = matcher.match_episodes(actual_durations, expected_durations)

        assert len(matches) == 3
        assert all(m is not None for m in matches)
        assert matches[0].episode_number == 1
        assert matches[1].episode_number == 2
        assert matches[2].episode_number == 3

    def test_match_episodes_empty_actual(self, matcher):
        """Test matching with no actual durations."""
        expected_durations = [1800.0, 2400.0]
        actual_durations = []

        matches = matcher.match_episodes(actual_durations, expected_durations)

        assert matches == []

    def test_match_episodes_empty_expected(self, matcher):
        """Test matching with no expected durations."""
        actual_durations = [1800.0, 2400.0]
        expected_durations = []

        matches = matcher.match_episodes(actual_durations, expected_durations)

        assert len(matches) == 2
        assert all(m is None for m in matches)

    def test_match_episodes_different_lengths(self, matcher):
        """Test matching with different length lists."""
        expected_durations = [1800.0, 2400.0]
        actual_durations = [1805.0, 2395.0, 1895.0]  # One extra

        matches = matcher.match_episodes(actual_durations, expected_durations)

        # Should still get 3 matches (one for each actual)
        assert len(matches) == 3
        assert all(m is not None for m in matches)


class TestConfidenceCalculation:
    """Test confidence calculation."""

    @pytest.fixture
    def matcher(self):
        """Create a matcher for testing."""
        return DurationMatcher(tolerance=300)

    def test_confidence_exact_match(self, matcher):
        """Test exact match confidence (≤1 second)."""
        confidence = matcher._calculate_confidence(0.0)
        assert confidence == MatchConfidence.EXACT

        confidence = matcher._calculate_confidence(1.0)
        assert confidence == MatchConfidence.EXACT

    def test_confidence_high_match(self, matcher):
        """Test high confidence match (within tolerance)."""
        confidence = matcher._calculate_confidence(150.0)
        assert confidence == MatchConfidence.HIGH

        confidence = matcher._calculate_confidence(300.0)
        assert confidence == MatchConfidence.HIGH

    def test_confidence_medium_match(self, matcher):
        """Test medium confidence match (outside tolerance)."""
        confidence = matcher._calculate_confidence(301.0)
        assert confidence == MatchConfidence.MEDIUM

        confidence = matcher._calculate_confidence(600.0)
        assert confidence == MatchConfidence.MEDIUM

    def test_is_confident_match(self, matcher):
        """Test confident match checking."""
        # Exact match
        exact_match = EpisodeMatch(
            episode_number=1,
            expected_duration=2400.0,
            actual_duration=2400.0,
            confidence=MatchConfidence.EXACT,
            duration_diff=0.0,
        )
        assert matcher.is_confident_match(exact_match) is True

        # High confidence match
        high_match = EpisodeMatch(
            episode_number=1,
            expected_duration=2400.0,
            actual_duration=2500.0,
            confidence=MatchConfidence.HIGH,
            duration_diff=100.0,
        )
        assert matcher.is_confident_match(high_match) is True

        # Medium confidence match
        medium_match = EpisodeMatch(
            episode_number=1,
            expected_duration=2400.0,
            actual_duration=3000.0,
            confidence=MatchConfidence.MEDIUM,
            duration_diff=600.0,
        )
        assert matcher.is_confident_match(medium_match) is False


class TestMatchConfidence:
    """Test MatchConfidence enum."""

    def test_confidence_values(self):
        """Test confidence enum values."""
        assert MatchConfidence.EXACT.value == 100
        assert MatchConfidence.HIGH.value == 80
        assert MatchConfidence.MEDIUM.value == 50

    def test_confidence_comparison(self):
        """Test confidence comparison."""
        # Can compare enum values
        assert MatchConfidence.EXACT.value > MatchConfidence.HIGH.value
        assert MatchConfidence.HIGH.value > MatchConfidence.MEDIUM.value


class TestEpisodeMatch:
    """Test EpisodeMatch dataclass."""

    def test_episode_match_creation(self):
        """Test creating an episode match."""
        match = EpisodeMatch(
            episode_number=5,
            expected_duration=2400.0,
            actual_duration=2450.0,
            confidence=MatchConfidence.HIGH,
            duration_diff=50.0,
        )

        assert match.episode_number == 5
        assert match.expected_duration == 2400.0
        assert match.actual_duration == 2450.0
        assert match.confidence == MatchConfidence.HIGH
        assert match.duration_diff == 50.0


class TestCustomTolerance:
    """Test custom tolerance values."""

    def test_tighter_tolerance(self):
        """Test with tighter tolerance (±1 minute)."""
        matcher = DurationMatcher(tolerance=60)

        expected_durations = [2400.0]
        actual_duration = 2450.0  # 50 seconds difference

        match = matcher.match_episode(actual_duration, expected_durations)

        assert match.confidence == MatchConfidence.HIGH

        # 100 seconds should be outside tolerance
        actual_duration = 2500.0
        match = matcher.match_episode(actual_duration, expected_durations)

        assert match.confidence == MatchConfidence.MEDIUM

    def test_looser_tolerance(self):
        """Test with looser tolerance (±10 minutes)."""
        matcher = DurationMatcher(tolerance=600)

        expected_durations = [2400.0]
        actual_duration = 2950.0  # ~9 minutes difference

        match = matcher.match_episode(actual_duration, expected_durations)

        assert match.confidence == MatchConfidence.HIGH

    def test_zero_tolerance(self):
        """Test with zero tolerance (exact matches only)."""
        matcher = DurationMatcher(tolerance=0)

        expected_durations = [2400.0]

        # Exact match (0 seconds)
        match = matcher.match_episode(2400.0, expected_durations)
        assert match.confidence == MatchConfidence.EXACT

        # Within 1 second is still EXACT (threshold is 1 second regardless of tolerance)
        match = matcher.match_episode(2401.0, expected_durations)
        assert match.confidence == MatchConfidence.EXACT

        # 2 seconds off is MEDIUM (exceeds both 1-second threshold and 0 tolerance)
        match = matcher.match_episode(2402.0, expected_durations)
        assert match.confidence == MatchConfidence.MEDIUM
