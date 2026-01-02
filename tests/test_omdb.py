"""Tests for OMDb provider."""

from unittest.mock import Mock, patch

import pytest
import requests

from mo.providers.base import AuthenticationError, NotFoundError, ProviderError, RateLimitError
from mo.providers.omdb import OMDbProvider


class TestOMDbProvider:
    """Test OMDb provider initialization and authentication."""

    def test_init_requires_api_key(self):
        """Test that initialization requires an API key."""
        with pytest.raises(AuthenticationError, match="API key is required"):
            OMDbProvider(api_key=None)

    def test_init_with_api_key(self):
        """Test successful initialization with API key."""
        provider = OMDbProvider(api_key="test_key")
        assert provider.api_key == "test_key"


class TestOMDbMovieSearch:
    """Test OMDb movie search functionality."""

    @pytest.fixture
    def provider(self):
        """Create an OMDb provider for testing."""
        return OMDbProvider(api_key="test_key", cache_enabled=False)

    @pytest.fixture
    def mock_search_response(self):
        """Mock OMDb search response."""
        return {
            "Response": "True",
            "Search": [
                {
                    "Title": "Inception",
                    "Year": "2010",
                    "imdbID": "tt1375666",
                    "Type": "movie",
                    "Poster": "https://example.com/poster.jpg",
                },
                {
                    "Title": "Inception: The Cobol Job",
                    "Year": "2010",
                    "imdbID": "tt5295894",
                    "Type": "movie",
                    "Poster": "N/A",
                },
            ],
        }

    def test_search_movie_success(self, provider, mock_search_response):
        """Test successful movie search."""
        with patch.object(provider, "_request", return_value=mock_search_response):
            results = provider.search_movie("Inception")

        assert len(results) == 2
        assert results[0].provider == "omdb"
        assert results[0].id == "tt1375666"
        assert results[0].title == "Inception"
        assert results[0].year == 2010
        assert results[0].media_type == "movie"
        assert results[0].poster_url is not None
        assert results[1].poster_url is None  # "N/A" should be None

    def test_search_movie_no_results(self, provider):
        """Test movie search with no results."""
        with patch.object(provider, "_request", side_effect=NotFoundError("Not found")):
            results = provider.search_movie("NonexistentMovie123")

        assert results == []

    def test_search_movie_with_year(self, provider, mock_search_response):
        """Test movie search with year filter."""
        with patch.object(provider, "_request", return_value=mock_search_response) as mock:
            provider.search_movie("Inception", year=2010)

        call_args = mock.call_args
        assert call_args[0][0]["y"] == 2010


class TestOMDbTVSearch:
    """Test OMDb TV show search functionality."""

    @pytest.fixture
    def provider(self):
        """Create an OMDb provider for testing."""
        return OMDbProvider(api_key="test_key", cache_enabled=False)

    @pytest.fixture
    def mock_tv_response(self):
        """Mock OMDb TV search response."""
        return {
            "Response": "True",
            "Search": [
                {
                    "Title": "Breaking Bad",
                    "Year": "2008-2013",
                    "imdbID": "tt0903747",
                    "Type": "series",
                    "Poster": "https://example.com/bb.jpg",
                }
            ],
        }

    def test_search_tv_success(self, provider, mock_tv_response):
        """Test successful TV show search."""
        with patch.object(provider, "_request", return_value=mock_tv_response):
            results = provider.search_tv("Breaking Bad")

        assert len(results) == 1
        assert results[0].provider == "omdb"
        assert results[0].id == "tt0903747"
        assert results[0].title == "Breaking Bad"
        assert results[0].year == 2008  # Should parse first year from range
        assert results[0].media_type == "tv"


class TestOMDbMovieMetadata:
    """Test OMDb movie metadata retrieval."""

    @pytest.fixture
    def provider(self):
        """Create an OMDb provider for testing."""
        return OMDbProvider(api_key="test_key", cache_enabled=False)

    @pytest.fixture
    def mock_movie_response(self):
        """Mock OMDb movie details response."""
        return {
            "Response": "True",
            "Title": "Inception",
            "Year": "2010",
            "Runtime": "148 min",
            "Genre": "Action, Sci-Fi, Thriller",
            "Director": "Christopher Nolan",
            "Writer": "Christopher Nolan",
            "Actors": "Leonardo DiCaprio, Joseph Gordon-Levitt, Ellen Page",
            "Plot": "A thief who steals corporate secrets...",
            "Poster": "https://example.com/inception.jpg",
            "imdbRating": "8.8",
            "imdbID": "tt1375666",
            "Type": "movie",
        }

    def test_get_movie_success(self, provider, mock_movie_response):
        """Test successful movie metadata retrieval."""
        with patch.object(provider, "_request", return_value=mock_movie_response):
            movie = provider.get_movie("tt1375666")

        assert movie.provider == "omdb"
        assert movie.id == "tt1375666"
        assert movie.title == "Inception"
        assert movie.year == 2010
        assert movie.runtime == 148
        assert movie.rating == 8.8
        assert movie.genres == ["Action", "Sci-Fi", "Thriller"]
        assert len(movie.cast) == 3
        assert "Leonardo DiCaprio" in movie.cast
        assert "Christopher Nolan" in movie.crew["Director"]

    def test_get_movie_by_title(self, provider, mock_movie_response):
        """Test movie retrieval by title."""
        with patch.object(provider, "_request", return_value=mock_movie_response):
            movie = provider.get_movie_by_title("Inception", year=2010)

        assert movie.title == "Inception"
        assert movie.year == 2010

    def test_get_movie_handles_na_values(self, provider):
        """Test handling of N/A values in OMDb response."""
        response = {
            "Response": "True",
            "Title": "Test Movie",
            "Year": "2020",
            "Runtime": "N/A",
            "Genre": "N/A",
            "Director": "N/A",
            "Plot": "N/A",
            "Poster": "N/A",
            "imdbRating": "N/A",
            "imdbID": "tt1234567",
        }

        with patch.object(provider, "_request", return_value=response):
            movie = provider.get_movie("tt1234567")

        assert movie.runtime is None
        assert movie.genres is None
        assert movie.plot is None
        assert movie.poster_url is None
        assert movie.rating is None


class TestOMDbErrorHandling:
    """Test OMDb error handling."""

    @pytest.fixture
    def provider(self):
        """Create an OMDb provider for testing."""
        return OMDbProvider(api_key="test_key", cache_enabled=False)

    def test_handles_not_found_error(self, provider):
        """Test handling of not found errors."""
        response = {"Response": "False", "Error": "Movie not found!"}

        with patch.object(provider.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response
            mock_get.return_value = mock_response

            with pytest.raises(NotFoundError, match="not found"):
                provider._request({})

    def test_handles_rate_limit_error(self, provider):
        """Test handling of rate limit errors."""
        response = {"Response": "False", "Error": "Request limit reached!"}

        with patch.object(provider.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response
            mock_get.return_value = mock_response

            with pytest.raises(RateLimitError, match="limit"):
                provider._request({})

    def test_handles_generic_error(self, provider):
        """Test handling of generic errors."""
        response = {"Response": "False", "Error": "Some error occurred"}

        with patch.object(provider.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response
            mock_get.return_value = mock_response

            with pytest.raises(ProviderError, match="error"):
                provider._request({})

    def test_retry_logic(self, provider):
        """Test request retry logic."""
        with patch.object(provider.session, "get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection error")

            with pytest.raises(ProviderError, match="failed"):
                provider._request({}, retry_count=2)

            assert mock_get.call_count == 2


class TestOMDbRateLimiting:
    """Test OMDb rate limiting."""

    @pytest.fixture
    def provider(self):
        """Create an OMDb provider for testing."""
        return OMDbProvider(api_key="test_key", cache_enabled=False)

    def test_rate_limit_tracking(self, provider):
        """Test that rate limiting tracks requests."""
        provider._rate_limit()
        assert len(provider._request_times) == 1

        provider._rate_limit()
        assert len(provider._request_times) == 2

    def test_rate_limit_exceeded(self, provider):
        """Test rate limit enforcement."""
        import time

        # Simulate hitting daily limit with recent timestamps
        current_time = time.time()
        provider._request_times = [current_time] * provider.MAX_REQUESTS_PER_DAY

        with pytest.raises(RateLimitError, match="daily rate limit"):
            provider._rate_limit()


class TestOMDbHelpers:
    """Test OMDb helper methods."""

    @pytest.fixture
    def provider(self):
        """Create an OMDb provider for testing."""
        return OMDbProvider(api_key="test_key", cache_enabled=False)

    def test_parse_year_single(self, provider):
        """Test year parsing from single year."""
        assert provider._parse_year("2010") == 2010

    def test_parse_year_range(self, provider):
        """Test year parsing from year range."""
        assert provider._parse_year("2008-2013") == 2008
        assert provider._parse_year("2010-") == 2010

    def test_parse_year_na(self, provider):
        """Test year parsing with N/A."""
        assert provider._parse_year("N/A") is None
        assert provider._parse_year(None) is None

    def test_parse_year_invalid(self, provider):
        """Test year parsing with invalid input."""
        assert provider._parse_year("invalid") is None
