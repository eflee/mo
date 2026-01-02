"""TheTVDB API v4 client.

Implements TheTVDB API v4 for TV show and episode metadata retrieval.
Requires an API key from https://thetvdb.com/api-information
"""

import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from mo.providers.base import (
    AuthenticationError,
    EpisodeMetadata,
    NotFoundError,
    ProviderError,
    RateLimitError,
    SearchResult,
    TVShowMetadata,
)
from mo.providers.cache import get_cache


class TheTVDBProvider:
    """TheTVDB API v4 client for TV show metadata."""

    BASE_URL = "https://api4.thetvdb.com/v4/"

    # Rate limiting: Conservative limit for free tier
    MAX_REQUESTS_PER_SECOND = 10
    RATE_LIMIT_WINDOW = 1.0  # seconds

    def __init__(self, api_key: Optional[str] = None, cache_enabled: bool = True):
        """Initialize TheTVDB provider.

        Args:
            api_key: TheTVDB API key
            cache_enabled: Whether to enable response caching

        Raises:
            AuthenticationError: If API key is not provided
        """
        if not api_key:
            raise AuthenticationError("TheTVDB API key is required")

        self.api_key = api_key
        self.cache = get_cache(enabled=cache_enabled)
        self.session = self.cache.get_session()

        # Authentication
        self._token: Optional[str] = None
        self._token_expiry: float = 0

        # Rate limiting
        self._request_times: List[float] = []

    def _get_token(self) -> str:
        """Get or refresh JWT token.

        Returns:
            str: Valid JWT token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check if token is still valid (with 5 minute buffer)
        if self._token and time.time() < self._token_expiry - 300:
            return self._token

        # Request new token
        url = urljoin(self.BASE_URL, "login")
        try:
            response = requests.post(url, json={"apikey": self.api_key})
            response.raise_for_status()

            data = response.json()
            self._token = data["data"]["token"]

            # TheTVDB tokens expire after 1 month, but we'll refresh more frequently
            self._token_expiry = time.time() + (30 * 24 * 60 * 60)  # 30 days

            return self._token

        except requests.RequestException as e:
            raise AuthenticationError(f"TheTVDB authentication failed: {e}")
        except (KeyError, ValueError) as e:
            raise AuthenticationError(f"Invalid TheTVDB authentication response: {e}")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for TheTVDB API requests.

        Returns:
            dict: HTTP headers including authorization
        """
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _rate_limit(self) -> None:
        """Apply rate limiting to requests."""
        now = time.time()

        # Remove requests older than the window
        self._request_times = [
            t for t in self._request_times if now - t < self.RATE_LIMIT_WINDOW
        ]

        # Check if we're at the limit
        if len(self._request_times) >= self.MAX_REQUESTS_PER_SECOND:
            oldest = self._request_times[0]
            wait_time = self.RATE_LIMIT_WINDOW - (now - oldest)
            if wait_time > 0:
                time.sleep(wait_time)

        self._request_times.append(time.time())

    def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 3,
    ) -> Dict[str, Any]:
        """Make a request to TheTVDB API with retry logic.

        Args:
            endpoint: API endpoint (relative to BASE_URL)
            params: Query parameters
            retry_count: Number of retries on failure

        Returns:
            dict: JSON response

        Raises:
            ProviderError: If request fails
            RateLimitError: If rate limit exceeded
            NotFoundError: If resource not found
        """
        url = urljoin(self.BASE_URL, endpoint)

        self._rate_limit()

        for attempt in range(retry_count):
            try:
                response = self.session.get(
                    url, headers=self._get_headers(), params=params
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise NotFoundError(f"Resource not found: {endpoint}")
                elif response.status_code == 401:
                    # Token might be expired, try refreshing once
                    if attempt == 0:
                        self._token = None
                        continue
                    raise AuthenticationError("TheTVDB authentication failed")
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < retry_count - 1:
                        time.sleep(retry_after)
                        continue
                    raise RateLimitError(
                        "TheTVDB rate limit exceeded", retry_after=retry_after
                    )
                else:
                    response.raise_for_status()

            except requests.RequestException as e:
                if attempt == retry_count - 1:
                    raise ProviderError(f"TheTVDB API request failed: {e}")
                time.sleep(2 ** attempt)

        raise ProviderError("TheTVDB API request failed after retries")

    def search_tv(self, title: str, year: Optional[int] = None) -> List[SearchResult]:
        """Search for TV shows by title.

        Args:
            title: TV show title to search for
            year: Optional first air year for filtering

        Returns:
            List[SearchResult]: List of search results

        Raises:
            ProviderError: If search fails
        """
        params = {"query": title}
        if year:
            params["year"] = str(year)

        try:
            data = self._request("search", params=params)
            results = []

            for item in data.get("data", []):
                # TheTVDB search returns mixed results, filter for series
                if item.get("type") != "series":
                    continue

                # Extract year from first_air_time
                first_air = item.get("first_air_time")
                item_year = None
                if first_air:
                    try:
                        item_year = int(first_air.split("-")[0])
                    except (ValueError, IndexError):
                        pass

                # Apply year filter if specified
                if year and item_year and item_year != year:
                    continue

                results.append(
                    SearchResult(
                        provider="tvdb",
                        id=str(item["tvdb_id"]),
                        title=item.get("name", ""),
                        year=item_year,
                        plot=item.get("overview"),
                        rating=None,  # TheTVDB doesn't provide ratings in search
                        poster_url=item.get("image_url"),
                        media_type="tv",
                        relevance_score=0.0,  # TheTVDB doesn't provide relevance scores
                        raw_data=item,
                    )
                )

            return results

        except NotFoundError:
            return []

    def get_tv_show(self, show_id: str) -> TVShowMetadata:
        """Get detailed TV show metadata.

        Args:
            show_id: TheTVDB series ID

        Returns:
            TVShowMetadata: TV show metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If show not found
        """
        # Get basic series info
        data = self._request(f"series/{show_id}/extended")
        series = data.get("data", {})

        # Extract year from first aired
        year = None
        if series.get("firstAired"):
            try:
                year = int(series["firstAired"].split("-")[0])
            except (ValueError, IndexError):
                pass

        # Extract genres
        genres = None
        if series.get("genres"):
            genres = [g.get("name") for g in series["genres"] if g.get("name")]

        # Get artwork URL (prefer poster)
        poster_url = None
        if series.get("image"):
            poster_url = series["image"]

        # Extract IMDB ID from remote IDs
        imdb_id = None
        if series.get("remoteIds"):
            for remote_id in series["remoteIds"]:
                if remote_id.get("sourceName") == "IMDB":
                    imdb_id = remote_id.get("id")
                    break

        return TVShowMetadata(
            provider="tvdb",
            id=str(series["id"]),
            title=series.get("name", ""),
            year=year,
            plot=series.get("overview"),
            rating=None,  # TheTVDB v4 doesn't include ratings in extended data
            genres=genres,
            cast=None,  # Cast requires separate API call
            poster_url=poster_url,
            backdrop_url=None,
            imdb_id=imdb_id,
            tmdb_id=None,
            tvdb_id=str(series["id"]),
            seasons=len(series.get("seasons", [])),
            status=series.get("status", {}).get("name"),
            raw_data=series,
        )

    def get_episode(
        self, show_id: str, season_number: int, episode_number: int
    ) -> EpisodeMetadata:
        """Get detailed episode metadata.

        Args:
            show_id: TheTVDB series ID
            season_number: Season number
            episode_number: Episode number

        Returns:
            EpisodeMetadata: Episode metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If episode not found
        """
        # Get series episodes to find the specific episode
        params = {"season": str(season_number)}
        data = self._request(f"series/{show_id}/episodes/default", params=params)

        episodes = data.get("data", {}).get("episodes", [])

        # Find matching episode
        episode_data = None
        for ep in episodes:
            if ep.get("seasonNumber") == season_number and ep.get("number") == episode_number:
                episode_data = ep
                break

        if not episode_data:
            raise NotFoundError(
                f"Episode not found: S{season_number:02d}E{episode_number:02d}"
            )

        # Get detailed episode info
        episode_id = episode_data.get("id")
        if episode_id:
            try:
                detail_data = self._request(f"episodes/{episode_id}/extended")
                episode_data = detail_data.get("data", episode_data)
            except (ProviderError, NotFoundError):
                # Fall back to basic episode data
                pass

        return EpisodeMetadata(
            provider="tvdb",
            show_id=show_id,
            season_number=season_number,
            episode_number=episode_number,
            title=episode_data.get("name"),
            plot=episode_data.get("overview"),
            aired=episode_data.get("aired"),
            runtime=episode_data.get("runtime"),
            rating=None,
            still_url=episode_data.get("image"),
            raw_data=episode_data,
        )

    def search_movie(self, title: str, year: Optional[int] = None) -> List[SearchResult]:
        """Search for movies (not supported by TheTVDB).

        TheTVDB is primarily for TV shows. This method is included for
        interface compatibility but will always return an empty list.

        Args:
            title: Movie title (ignored)
            year: Movie year (ignored)

        Returns:
            List[SearchResult]: Empty list
        """
        return []
