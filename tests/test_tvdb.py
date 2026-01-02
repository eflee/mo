"""Tests for TheTVDB provider."""

from unittest.mock import Mock, patch

import pytest
import requests

from mo.providers.base import AuthenticationError, NotFoundError, ProviderError
from mo.providers.tvdb import TheTVDBProvider


class TestTheTVDBProvider:
    """Test TheTVDB provider initialization and authentication."""

    def test_init_requires_api_key(self):
        """Test that initialization requires an API key."""
        with pytest.raises(AuthenticationError, match="API key is required"):
            TheTVDBProvider(api_key=None)

    def test_init_with_api_key(self):
        """Test successful initialization with API key."""
        provider = TheTVDBProvider(api_key="test_key")
        assert provider.api_key == "test_key"
        assert provider._token is None

    @patch("requests.post")
    def test_get_token_success(self, mock_post):
        """Test successful JWT token retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"token": "jwt_token_123"}}
        mock_post.return_value = mock_response

        provider = TheTVDBProvider(api_key="test_key", cache_enabled=False)
        token = provider._get_token()

        assert token == "jwt_token_123"
        assert provider._token == "jwt_token_123"
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_get_token_failure(self, mock_post):
        """Test JWT token retrieval failure."""
        mock_post.side_effect = requests.RequestException("Connection error")

        provider = TheTVDBProvider(api_key="test_key", cache_enabled=False)

        with pytest.raises(AuthenticationError, match="authentication failed"):
            provider._get_token()

    @patch("requests.post")
    def test_token_caching(self, mock_post):
        """Test that tokens are cached and reused."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"token": "jwt_token_123"}}
        mock_post.return_value = mock_response

        provider = TheTVDBProvider(api_key="test_key", cache_enabled=False)

        # First call should hit the API
        token1 = provider._get_token()
        assert mock_post.call_count == 1

        # Second call should use cached token
        token2 = provider._get_token()
        assert token1 == token2
        assert mock_post.call_count == 1  # Still only 1 call


class TestTheTVDBTVSearch:
    """Test TheTVDB TV show search functionality."""

    @pytest.fixture
    def provider(self):
        """Create a TheTVDB provider for testing."""
        provider = TheTVDBProvider(api_key="test_key", cache_enabled=False)
        provider._token = "test_jwt_token"  # Skip authentication
        provider._token_expiry = 9999999999.0
        return provider

    @pytest.fixture
    def mock_search_response(self):
        """Mock TheTVDB search response."""
        return {
            "data": [
                {
                    "tvdb_id": "81189",
                    "name": "Breaking Bad",
                    "type": "series",
                    "first_air_time": "2008-01-20",
                    "overview": "A high school chemistry teacher...",
                    "image_url": "https://artworks.thetvdb.com/banners/posters/81189-1.jpg",
                },
                {
                    "tvdb_id": "999999",
                    "name": "Breaking Bad: The Movie",
                    "type": "movie",
                    "first_air_time": "2019-10-11",
                    "overview": "A feature film...",
                    "image_url": "https://example.com/poster.jpg",
                },
            ]
        }

    def test_search_tv_success(self, provider, mock_search_response):
        """Test successful TV show search."""
        with patch.object(provider, "_request", return_value=mock_search_response):
            results = provider.search_tv("Breaking Bad")

        # Should only return series, not movies
        assert len(results) == 1
        assert results[0].provider == "tvdb"
        assert results[0].id == "81189"
        assert results[0].title == "Breaking Bad"
        assert results[0].year == 2008
        assert results[0].media_type == "tv"

    def test_search_tv_with_year_filter(self, provider, mock_search_response):
        """Test TV search with year filtering."""
        with patch.object(provider, "_request", return_value=mock_search_response):
            results = provider.search_tv("Breaking Bad", year=2008)

        # Should match year 2008
        assert len(results) == 1
        assert results[0].year == 2008

    def test_search_tv_no_results(self, provider):
        """Test TV search with no results."""
        with patch.object(provider, "_request", side_effect=NotFoundError("Not found")):
            results = provider.search_tv("NonexistentShow123")

        assert results == []

    def test_search_movie_returns_empty(self, provider):
        """Test that search_movie returns empty list (not supported)."""
        results = provider.search_movie("Some Movie")
        assert results == []


class TestTheTVDBShowMetadata:
    """Test TheTVDB show metadata retrieval."""

    @pytest.fixture
    def provider(self):
        """Create a TheTVDB provider for testing."""
        provider = TheTVDBProvider(api_key="test_key", cache_enabled=False)
        provider._token = "test_jwt_token"
        provider._token_expiry = 9999999999.0
        return provider

    @pytest.fixture
    def mock_show_response(self):
        """Mock TheTVDB extended series response."""
        return {
            "data": {
                "id": 81189,
                "name": "Breaking Bad",
                "overview": "A high school chemistry teacher...",
                "firstAired": "2008-01-20",
                "image": "https://artworks.thetvdb.com/banners/posters/81189-1.jpg",
                "genres": [{"name": "Drama"}, {"name": "Crime"}],
                "seasons": [
                    {"number": 1},
                    {"number": 2},
                    {"number": 3},
                    {"number": 4},
                    {"number": 5},
                ],
                "status": {"name": "Ended"},
                "remoteIds": [{"id": "tt0903747", "sourceName": "IMDB"}],
            }
        }

    def test_get_tv_show_success(self, provider, mock_show_response):
        """Test successful TV show metadata retrieval."""
        with patch.object(provider, "_request", return_value=mock_show_response):
            show = provider.get_tv_show("81189")

        assert show.provider == "tvdb"
        assert show.id == "81189"
        assert show.title == "Breaking Bad"
        assert show.year == 2008
        assert show.genres == ["Drama", "Crime"]
        assert show.tvdb_id == "81189"
        assert show.seasons == 5
        assert show.status == "Ended"

    def test_get_tv_show_not_found(self, provider):
        """Test TV show retrieval with non-existent ID."""
        with patch.object(provider, "_request", side_effect=NotFoundError("Not found")):
            with pytest.raises(NotFoundError):
                provider.get_tv_show("999999")


class TestTheTVDBEpisodeMetadata:
    """Test TheTVDB episode metadata retrieval."""

    @pytest.fixture
    def provider(self):
        """Create a TheTVDB provider for testing."""
        provider = TheTVDBProvider(api_key="test_key", cache_enabled=False)
        provider._token = "test_jwt_token"
        provider._token_expiry = 9999999999.0
        return provider

    @pytest.fixture
    def mock_episodes_response(self):
        """Mock TheTVDB episodes response."""
        return {
            "data": {
                "episodes": [
                    {
                        "id": 349232,
                        "seasonNumber": 1,
                        "number": 1,
                        "name": "Pilot",
                        "overview": "When an unassuming high school chemistry teacher...",
                        "aired": "2008-01-20",
                        "runtime": 58,
                        "image": "https://artworks.thetvdb.com/banners/episodes/81189/349232.jpg",
                    },
                    {
                        "id": 349233,
                        "seasonNumber": 1,
                        "number": 2,
                        "name": "Cat's in the Bag...",
                        "overview": "Walt and Jesse attempt to tie up loose ends...",
                        "aired": "2008-01-27",
                        "runtime": 48,
                        "image": None,
                    },
                ]
            }
        }

    @pytest.fixture
    def mock_episode_detail_response(self):
        """Mock TheTVDB episode detail response."""
        return {
            "data": {
                "id": 349232,
                "seasonNumber": 1,
                "number": 1,
                "name": "Pilot",
                "overview": "When an unassuming high school chemistry teacher...",
                "aired": "2008-01-20",
                "runtime": 58,
                "image": "https://artworks.thetvdb.com/banners/episodes/81189/349232.jpg",
            }
        }

    def test_get_episode_success(self, provider, mock_episodes_response, mock_episode_detail_response):
        """Test successful episode metadata retrieval."""
        with patch.object(provider, "_request") as mock_request:
            # First call returns episodes list, second call returns episode details
            mock_request.side_effect = [mock_episodes_response, mock_episode_detail_response]

            episode = provider.get_episode("81189", season_number=1, episode_number=1)

        assert episode.provider == "tvdb"
        assert episode.show_id == "81189"
        assert episode.season_number == 1
        assert episode.episode_number == 1
        assert episode.title == "Pilot"
        assert episode.aired == "2008-01-20"
        assert episode.runtime == 58

    def test_get_episode_not_found(self, provider, mock_episodes_response):
        """Test episode retrieval when episode doesn't exist."""
        with patch.object(provider, "_request", return_value=mock_episodes_response):
            with pytest.raises(NotFoundError, match="Episode not found"):
                provider.get_episode("81189", season_number=1, episode_number=99)

    def test_get_episode_without_detail(self, provider, mock_episodes_response):
        """Test episode retrieval when detail endpoint fails."""
        with patch.object(provider, "_request") as mock_request:
            # First call returns episodes, second call fails
            mock_request.side_effect = [
                mock_episodes_response,
                ProviderError("Detail fetch failed"),
            ]

            episode = provider.get_episode("81189", season_number=1, episode_number=1)

        # Should fall back to basic episode data
        assert episode.title == "Pilot"
        assert episode.season_number == 1


class TestTheTVDBErrorHandling:
    """Test TheTVDB error handling."""

    @pytest.fixture
    def provider(self):
        """Create a TheTVDB provider for testing."""
        provider = TheTVDBProvider(api_key="test_key", cache_enabled=False)
        provider._token = "test_jwt_token"
        provider._token_expiry = 9999999999.0
        return provider

    def test_handles_401_error_with_retry(self, provider):
        """Test handling of 401 errors with token refresh."""
        mock_response_401 = Mock()
        mock_response_401.status_code = 401

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"data": []}

        with patch.object(provider.session, "get") as mock_get:
            with patch.object(provider, "_get_token", return_value="new_token"):
                mock_get.side_effect = [mock_response_401, mock_response_200]

                result = provider._request("test/endpoint")

        assert mock_get.call_count == 2  # Retry after 401

    def test_handles_404_error(self, provider):
        """Test handling of 404 errors."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(provider.session, "get", return_value=mock_response):
            with pytest.raises(NotFoundError):
                provider._request("test/endpoint")

    def test_retry_logic(self, provider):
        """Test request retry logic."""
        with patch.object(provider.session, "get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection error")

            with pytest.raises(ProviderError, match="failed"):
                provider._request("test/endpoint", retry_count=2)

            assert mock_get.call_count == 2


class TestTheTVDBRateLimiting:
    """Test TheTVDB rate limiting."""

    @pytest.fixture
    def provider(self):
        """Create a TheTVDB provider for testing."""
        provider = TheTVDBProvider(api_key="test_key", cache_enabled=False)
        provider._token = "test_jwt_token"
        provider._token_expiry = 9999999999.0
        return provider

    def test_rate_limit_tracking(self, provider):
        """Test that rate limiting tracks requests."""
        provider._rate_limit()
        assert len(provider._request_times) == 1

        provider._rate_limit()
        assert len(provider._request_times) == 2
