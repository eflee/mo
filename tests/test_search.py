"""Tests for interactive search interface."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from mo.providers.base import SearchResult
from mo.providers.search import InteractiveSearch, fuzzy_match_score


class TestFuzzyMatching:
    """Test fuzzy matching functionality."""

    def test_exact_match(self):
        """Test fuzzy match with exact strings."""
        score = fuzzy_match_score("Inception", "Inception")
        assert score == 1.0

    def test_case_insensitive(self):
        """Test fuzzy match is case insensitive."""
        score = fuzzy_match_score("INCEPTION", "inception")
        assert score == 1.0

    def test_partial_match(self):
        """Test fuzzy match with partial match."""
        score = fuzzy_match_score("Inception", "Inception 2")
        assert 0.5 < score < 1.0

    def test_no_match(self):
        """Test fuzzy match with completely different strings."""
        score = fuzzy_match_score("Inception", "Breaking Bad")
        assert score < 0.5


class TestInteractiveSearch:
    """Test interactive search interface."""

    @pytest.fixture
    def search_interface(self):
        """Create interactive search instance."""
        return InteractiveSearch()

    @pytest.fixture
    def mock_results(self):
        """Create mock search results."""
        return [
            SearchResult(
                provider="tmdb",
                id="1",
                title="Inception",
                year=2010,
                plot="A thief who steals corporate secrets...",
                rating=8.8,
                poster_url="https://example.com/inception.jpg",
                media_type="movie",
                relevance_score=100.0,
            ),
            SearchResult(
                provider="tmdb",
                id="2",
                title="Inception: The Beginning",
                year=2011,
                plot="A documentary...",
                rating=6.5,
                poster_url=None,
                media_type="movie",
                relevance_score=50.0,
            ),
        ]

    def test_score_results_exact_match(self, search_interface, mock_results):
        """Test result scoring with exact title match."""
        scored = search_interface._score_results(mock_results, "Inception", None)

        assert len(scored) == 2
        assert scored[0].title == "Inception"  # Should be first (better match)

    def test_score_results_with_year_match(self, search_interface, mock_results):
        """Test result scoring with year matching."""
        scored = search_interface._score_results(mock_results, "Inception", 2010)

        # Result with matching year should score higher
        assert scored[0].year == 2010

    def test_score_results_year_penalty(self, search_interface, mock_results):
        """Test result scoring with year mismatch penalty."""
        scored = search_interface._score_results(mock_results, "Inception", 2015)

        # Results should still be scored, but with year penalty
        assert len(scored) == 2

    def test_score_results_sorted(self, search_interface, mock_results):
        """Test that results are sorted by relevance score."""
        scored = search_interface._score_results(mock_results, "Inception", 2010)

        # Results should be in descending order by score
        for i in range(len(scored) - 1):
            assert scored[i].relevance_score >= scored[i + 1].relevance_score

    @patch("mo.providers.search.prompt")
    def test_display_and_select_valid_choice(self, mock_prompt, search_interface, mock_results):
        """Test display and selection with valid choice."""
        mock_prompt.return_value = "1"

        result = search_interface._display_and_select(mock_results, "Inception")

        assert result == mock_results[0]

    @patch("mo.providers.search.prompt")
    def test_display_and_select_new_search(self, mock_prompt, search_interface, mock_results):
        """Test display and selection choosing new search."""
        mock_prompt.return_value = "n"

        result = search_interface._display_and_select(mock_results, "Inception")

        assert result == "new"

    @patch("mo.providers.search.prompt")
    def test_display_and_select_quit(self, mock_prompt, search_interface, mock_results):
        """Test display and selection with quit choice."""
        mock_prompt.return_value = "q"

        result = search_interface._display_and_select(mock_results, "Inception")

        assert result is None

    @patch("mo.providers.search.prompt")
    def test_display_and_select_invalid_choice(self, mock_prompt, search_interface, mock_results):
        """Test display and selection with invalid choice."""
        mock_prompt.return_value = "99"

        result = search_interface._display_and_select(mock_results, "Inception")

        assert result is None

    @patch("mo.providers.search.prompt")
    def test_display_and_select_keyboard_interrupt(self, mock_prompt, search_interface, mock_results):
        """Test display and selection with keyboard interrupt."""
        mock_prompt.side_effect = KeyboardInterrupt()

        result = search_interface._display_and_select(mock_results, "Inception")

        assert result is None

    @patch("mo.providers.search.prompt")
    def test_confirm_selection_yes(self, mock_prompt, search_interface, mock_results):
        """Test confirming selection with yes."""
        mock_prompt.return_value = "y"

        confirmed = search_interface.confirm_selection(mock_results[0])

        assert confirmed is True

    @patch("mo.providers.search.prompt")
    def test_confirm_selection_no(self, mock_prompt, search_interface, mock_results):
        """Test confirming selection with no."""
        mock_prompt.return_value = "n"

        confirmed = search_interface.confirm_selection(mock_results[0])

        assert confirmed is False

    @patch("mo.providers.search.prompt")
    def test_confirm_selection_default_yes(self, mock_prompt, search_interface, mock_results):
        """Test confirming selection with default (yes)."""
        mock_prompt.return_value = ""

        confirmed = search_interface.confirm_selection(mock_results[0])

        assert confirmed is True

    @patch("mo.providers.search.prompt")
    def test_search_and_select_first_result(self, mock_prompt, search_interface, mock_results):
        """Test full search and select flow selecting first result."""
        mock_search = Mock(return_value=mock_results)
        mock_prompt.return_value = "1"

        result = search_interface.search_and_select(
            mock_search, "Inception", year=2010, media_type="movie"
        )

        assert result.title == "Inception"
        mock_search.assert_called_once_with("Inception", 2010)

    @patch("mo.providers.search.prompt")
    def test_search_and_select_no_results_quit(self, mock_prompt, search_interface):
        """Test search and select with no results and quit."""
        mock_search = Mock(return_value=[])
        mock_prompt.return_value = "q"

        result = search_interface.search_and_select(
            mock_search, "NonexistentMovie", media_type="movie"
        )

        assert result is None

    @patch("mo.providers.search.prompt")
    def test_search_and_select_no_results_new_search(self, mock_prompt, search_interface, mock_results):
        """Test search and select with no results then new search."""
        mock_search = Mock(side_effect=[[], mock_results])
        mock_prompt.side_effect = ["New Query", "1"]

        result = search_interface.search_and_select(
            mock_search, "Typo", media_type="movie"
        )

        assert result.title == "Inception"
        assert mock_search.call_count == 2

    @patch("mo.providers.search.prompt")
    def test_search_and_select_new_search_from_results(self, mock_prompt, search_interface, mock_results):
        """Test search and select choosing new search from results."""
        mock_results_2 = [
            SearchResult(
                provider="tmdb",
                id="3",
                title="The Matrix",
                year=1999,
                plot="A computer hacker...",
                rating=8.7,
                poster_url=None,
                media_type="movie",
                relevance_score=100.0,
            )
        ]

        mock_search = Mock(side_effect=[mock_results, mock_results_2])
        mock_prompt.side_effect = ["n", "The Matrix", "1"]

        result = search_interface.search_and_select(
            mock_search, "Inception", media_type="movie"
        )

        assert result.title == "The Matrix"
        assert mock_search.call_count == 2

    @patch("mo.providers.search.prompt")
    def test_search_and_select_keyboard_interrupt(self, mock_prompt, search_interface):
        """Test search and select with keyboard interrupt."""
        mock_search = Mock(return_value=[])
        mock_prompt.side_effect = KeyboardInterrupt()

        result = search_interface.search_and_select(
            mock_search, "Inception", media_type="movie"
        )

        assert result is None

    @patch("mo.providers.search.prompt")
    def test_search_and_select_search_error(self, mock_prompt, search_interface):
        """Test search and select when search function raises error."""
        mock_search = Mock(side_effect=Exception("API Error"))

        result = search_interface.search_and_select(
            mock_search, "Inception", media_type="movie"
        )

        assert result is None


class TestSearchResultDisplay:
    """Test search result display functionality."""

    @pytest.fixture
    def search_interface(self):
        """Create interactive search instance."""
        return InteractiveSearch()

    @pytest.fixture
    def mock_results_with_none_values(self):
        """Create mock search results with None values."""
        return [
            SearchResult(
                provider="tmdb",
                id="1",
                title="Incomplete Movie",
                year=None,
                plot=None,
                rating=None,
                poster_url=None,
                media_type="movie",
                relevance_score=50.0,
            )
        ]

    @patch("mo.providers.search.prompt")
    def test_display_handles_none_values(self, mock_prompt, search_interface, mock_results_with_none_values):
        """Test that display handles None values gracefully."""
        mock_prompt.return_value = "1"

        result = search_interface._display_and_select(
            mock_results_with_none_values, "Incomplete"
        )

        assert result is not None

    @pytest.fixture
    def mock_results_long_plot(self):
        """Create mock search results with long plot."""
        long_plot = "A" * 100  # 100 character plot
        return [
            SearchResult(
                provider="tmdb",
                id="1",
                title="Movie",
                year=2020,
                plot=long_plot,
                rating=7.0,
                poster_url=None,
                media_type="movie",
                relevance_score=50.0,
            )
        ]

    @patch("mo.providers.search.prompt")
    def test_display_truncates_long_plot(self, mock_prompt, search_interface, mock_results_long_plot):
        """Test that display truncates long plots."""
        mock_prompt.return_value = "1"

        # Should not raise any errors with long plot
        result = search_interface._display_and_select(
            mock_results_long_plot, "Movie"
        )

        assert result is not None
