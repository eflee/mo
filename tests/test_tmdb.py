"""Tests for TMDB provider."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from mo.providers.base import (
    AuthenticationError,
    NotFoundError,
    ProviderError,
    RateLimitError,
)
from mo.providers.tmdb import TMDBProvider


class TestTMDBProvider:
    """Test TMDB provider initialization and authentication."""

    def test_init_requires_token(self):
        """Test that initialization requires an access token."""
        with pytest.raises(AuthenticationError, match="access token is required"):
            TMDBProvider(access_token=None)

    def test_init_with_token(self):
        """Test successful initialization with token."""
        provider = TMDBProvider(access_token="test_token")
        assert provider.access_token == "test_token"
        assert provider.language == "en-US"

    def test_init_with_custom_language(self):
        """Test initialization with custom language."""
        provider = TMDBProvider(access_token="test_token", language="fr-FR")
        assert provider.language == "fr-FR"

    def test_get_headers(self):
        """Test HTTP headers generation."""
        provider = TMDBProvider(access_token="test_token", cache_enabled=False)
        headers = provider._get_headers()
        assert headers["Authorization"] == "Bearer test_token"
        assert "Content-Type" in headers


class TestTMDBMovieSearch:
    """Test TMDB movie search functionality."""

    @pytest.fixture
    def provider(self):
        """Create a TMDB provider for testing."""
        return TMDBProvider(access_token="test_token", cache_enabled=False)

    @pytest.fixture
    def mock_search_response(self):
        """Mock TMDB movie search response."""
        return {
            "page": 1,
            "results": [
                {
                    "id": 27205,
                    "title": "Inception",
                    "release_date": "2010-07-16",
                    "overview": "A thief who steals corporate secrets...",
                    "vote_average": 8.4,
                    "poster_path": "/abc123.jpg",
                    "popularity": 123.45,
                },
                {
                    "id": 12345,
                    "title": "Inception: The Beginning",
                    "release_date": "2011-01-01",
                    "overview": "A documentary about...",
                    "vote_average": 6.5,
                    "poster_path": "/xyz789.jpg",
                    "popularity": 45.67,
                },
            ],
        }

    def test_search_movie_success(self, provider, mock_search_response):
        """Test successful movie search."""
        with patch.object(provider, "_request", return_value=mock_search_response):
            results = provider.search_movie("Inception", year=2010)

        assert len(results) == 2
        assert results[0].provider == "tmdb"
        assert results[0].id == "27205"
        assert results[0].title == "Inception"
        assert results[0].year == 2010
        assert results[0].rating == 8.4
        assert results[0].media_type == "movie"
        assert results[0].poster_url is not None

    def test_search_movie_no_results(self, provider):
        """Test movie search with no results."""
        with patch.object(provider, "_request", side_effect=NotFoundError("Not found")):
            results = provider.search_movie("NonexistentMovie123")

        assert results == []

    def test_search_movie_with_year(self, provider, mock_search_response):
        """Test movie search with year filter."""
        with patch.object(provider, "_request", return_value=mock_search_response) as mock:
            provider.search_movie("Inception", year=2010)

        mock.assert_called_once()
        call_args = mock.call_args
        assert call_args[1]["params"]["year"] == 2010

    def test_search_movie_pagination(self, provider, mock_search_response):
        """Test movie search with pagination."""
        with patch.object(provider, "_request", return_value=mock_search_response) as mock:
            provider.search_movie("Inception", page=2)

        call_args = mock.call_args
        assert call_args[1]["params"]["page"] == 2


class TestTMDBTVSearch:
    """Test TMDB TV show search functionality."""

    @pytest.fixture
    def provider(self):
        """Create a TMDB provider for testing."""
        return TMDBProvider(access_token="test_token", cache_enabled=False)

    @pytest.fixture
    def mock_tv_response(self):
        """Mock TMDB TV search response."""
        return {
            "page": 1,
            "results": [
                {
                    "id": 1396,
                    "name": "Breaking Bad",
                    "first_air_date": "2008-01-20",
                    "overview": "A high school chemistry teacher...",
                    "vote_average": 9.5,
                    "poster_path": "/bb123.jpg",
                    "popularity": 456.78,
                }
            ],
        }

    def test_search_tv_success(self, provider, mock_tv_response):
        """Test successful TV show search."""
        with patch.object(provider, "_request", return_value=mock_tv_response):
            results = provider.search_tv("Breaking Bad")

        assert len(results) == 1
        assert results[0].provider == "tmdb"
        assert results[0].id == "1396"
        assert results[0].title == "Breaking Bad"
        assert results[0].year == 2008
        assert results[0].media_type == "tv"

    def test_search_tv_with_year(self, provider, mock_tv_response):
        """Test TV search with year filter."""
        with patch.object(provider, "_request", return_value=mock_tv_response) as mock:
            provider.search_tv("Breaking Bad", year=2008)

        call_args = mock.call_args
        assert call_args[1]["params"]["first_air_date_year"] == 2008


class TestTMDBMovieMetadata:
    """Test TMDB movie metadata retrieval."""

    @pytest.fixture
    def provider(self):
        """Create a TMDB provider for testing."""
        return TMDBProvider(access_token="test_token", cache_enabled=False)

    @pytest.fixture
    def mock_movie_response(self):
        """Mock TMDB movie details response."""
        return {
            "id": 27205,
            "title": "Inception",
            "release_date": "2010-07-16",
            "overview": "A thief who steals corporate secrets...",
            "runtime": 148,
            "vote_average": 8.4,
            "genres": [{"id": 28, "name": "Action"}, {"id": 878, "name": "Science Fiction"}],
            "poster_path": "/abc123.jpg",
            "backdrop_path": "/backdrop.jpg",
            "belongs_to_collection": {"id": 1234, "name": "Inception Collection"},
            "credits": {
                "cast": [
                    {"name": "Leonardo DiCaprio", "character": "Cobb"},
                    {"name": "Ellen Page", "character": "Ariadne"},
                ],
                "crew": [
                    {"name": "Christopher Nolan", "job": "Director"},
                    {"name": "Hans Zimmer", "job": "Composer"},
                ],
            },
            "external_ids": {"imdb_id": "tt1375666"},
        }

    def test_get_movie_success(self, provider, mock_movie_response):
        """Test successful movie metadata retrieval."""
        with patch.object(provider, "_request", return_value=mock_movie_response):
            movie = provider.get_movie("27205")

        assert movie.provider == "tmdb"
        assert movie.id == "27205"
        assert movie.title == "Inception"
        assert movie.year == 2010
        assert movie.runtime == 148
        assert movie.rating == 8.4
        assert movie.genres == ["Action", "Science Fiction"]
        assert len(movie.cast) == 2
        assert "Christopher Nolan" in movie.crew["Director"]
        assert movie.imdb_id == "tt1375666"
        assert movie.tmdb_id == "27205"
        assert movie.collection == "Inception Collection"

    def test_get_movie_not_found(self, provider):
        """Test movie metadata retrieval with non-existent ID."""
        with patch.object(provider, "_request", side_effect=NotFoundError("Not found")):
            with pytest.raises(NotFoundError):
                provider.get_movie("999999")


class TestTMDBTVMetadata:
    """Test TMDB TV show metadata retrieval."""

    @pytest.fixture
    def provider(self):
        """Create a TMDB provider for testing."""
        return TMDBProvider(access_token="test_token", cache_enabled=False)

    @pytest.fixture
    def mock_tv_response(self):
        """Mock TMDB TV show details response."""
        return {
            "id": 1396,
            "name": "Breaking Bad",
            "first_air_date": "2008-01-20",
            "overview": "A high school chemistry teacher...",
            "vote_average": 9.5,
            "genres": [{"id": 18, "name": "Drama"}, {"id": 80, "name": "Crime"}],
            "poster_path": "/bb123.jpg",
            "backdrop_path": "/bb_backdrop.jpg",
            "number_of_seasons": 5,
            "status": "Ended",
            "credits": {
                "cast": [
                    {"name": "Bryan Cranston", "character": "Walter White"},
                    {"name": "Aaron Paul", "character": "Jesse Pinkman"},
                ]
            },
            "external_ids": {"imdb_id": "tt0903747", "tvdb_id": 81189},
        }

    def test_get_tv_show_success(self, provider, mock_tv_response):
        """Test successful TV show metadata retrieval."""
        with patch.object(provider, "_request", return_value=mock_tv_response):
            show = provider.get_tv_show("1396")

        assert show.provider == "tmdb"
        assert show.id == "1396"
        assert show.title == "Breaking Bad"
        assert show.year == 2008
        assert show.genres == ["Drama", "Crime"]
        assert show.imdb_id == "tt0903747"
        assert show.tvdb_id == "81189"
        assert show.seasons == 5
        assert show.status == "Ended"


class TestTMDBEpisodeMetadata:
    """Test TMDB episode metadata retrieval."""

    @pytest.fixture
    def provider(self):
        """Create a TMDB provider for testing."""
        return TMDBProvider(access_token="test_token", cache_enabled=False)

    @pytest.fixture
    def mock_episode_response(self):
        """Mock TMDB episode details response."""
        return {
            "id": 62085,
            "name": "Pilot",
            "overview": "When an unassuming high school chemistry teacher...",
            "air_date": "2008-01-20",
            "runtime": 58,
            "vote_average": 8.5,
            "still_path": "/still123.jpg",
            "season_number": 1,
            "episode_number": 1,
        }

    def test_get_episode_success(self, provider, mock_episode_response):
        """Test successful episode metadata retrieval."""
        with patch.object(provider, "_request", return_value=mock_episode_response):
            episode = provider.get_episode("1396", season_number=1, episode_number=1)

        assert episode.provider == "tmdb"
        assert episode.show_id == "1396"
        assert episode.season_number == 1
        assert episode.episode_number == 1
        assert episode.title == "Pilot"
        assert episode.air_date == "2008-01-20"
        assert episode.runtime == 58
        assert episode.rating == 8.5


class TestTMDBRateLimiting:
    """Test TMDB rate limiting."""

    @pytest.fixture
    def provider(self):
        """Create a TMDB provider for testing."""
        return TMDBProvider(access_token="test_token", cache_enabled=False)

    def test_rate_limit_tracking(self, provider):
        """Test that rate limiting tracks requests."""
        provider._rate_limit()
        assert len(provider._request_times) == 1

        provider._rate_limit()
        assert len(provider._request_times) == 2


class TestTMDBErrorHandling:
    """Test TMDB error handling."""

    @pytest.fixture
    def provider(self):
        """Create a TMDB provider for testing."""
        return TMDBProvider(access_token="test_token", cache_enabled=False)

    def test_handles_401_error(self, provider):
        """Test handling of authentication errors."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"status_message": "Invalid token"}

        with patch.object(provider.session, "get", return_value=mock_response):
            with pytest.raises(AuthenticationError, match="Invalid TMDB access token"):
                provider._request("test/endpoint")

    def test_handles_404_error(self, provider):
        """Test handling of not found errors."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(provider.session, "get", return_value=mock_response):
            with pytest.raises(NotFoundError):
                provider._request("test/endpoint")

    def test_handles_429_rate_limit(self, provider):
        """Test handling of rate limit errors."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(provider.session, "get", return_value=mock_response):
            with pytest.raises(RateLimitError) as exc_info:
                provider._request("test/endpoint", retry_count=1)

        assert exc_info.value.retry_after == 60

    def test_retry_logic(self, provider):
        """Test request retry logic."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError()

        with patch.object(provider.session, "get", return_value=mock_response):
            with pytest.raises(ProviderError, match="failed"):
                provider._request("test/endpoint", retry_count=2)


class TestTMDBHelpers:
    """Test TMDB helper methods."""

    @pytest.fixture
    def provider(self):
        """Create a TMDB provider for testing."""
        return TMDBProvider(access_token="test_token", cache_enabled=False)

    def test_parse_year_valid(self, provider):
        """Test year parsing from valid date."""
        assert provider._parse_year("2010-07-16") == 2010
        assert provider._parse_year("2023-01-01") == 2023

    def test_parse_year_invalid(self, provider):
        """Test year parsing from invalid date."""
        assert provider._parse_year(None) is None
        assert provider._parse_year("") is None
        assert provider._parse_year("invalid") is None

    def test_get_image_url(self, provider):
        """Test image URL generation."""
        url = provider._get_image_url("/abc123.jpg")
        assert url == "https://image.tmdb.org/t/p/w500/abc123.jpg"

    def test_get_image_url_custom_size(self, provider):
        """Test image URL with custom size."""
        url = provider._get_image_url("/abc123.jpg", size="original")
        assert url == "https://image.tmdb.org/t/p/original/abc123.jpg"

    def test_get_image_url_none(self, provider):
        """Test image URL with None path."""
        assert provider._get_image_url(None) is None
