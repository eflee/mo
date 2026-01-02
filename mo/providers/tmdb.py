"""TMDB (The Movie Database) API client.

Implements the TMDB API v3 for movie and TV show metadata retrieval.
Requires an API access token from https://www.themoviedb.org/settings/api
"""

import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from mo.providers.base import (
    AuthenticationError,
    EpisodeMetadata,
    MovieMetadata,
    NotFoundError,
    ProviderError,
    RateLimitError,
    SearchResult,
    TVShowMetadata,
)
from mo.providers.cache import get_cache


class TMDBProvider:
    """TMDB API client for movie and TV show metadata."""

    BASE_URL = "https://api.themoviedb.org/3/"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

    # Rate limiting: TMDB allows 50 requests per second
    MAX_REQUESTS_PER_SECOND = 50
    RATE_LIMIT_WINDOW = 1.0  # seconds

    def __init__(
        self,
        access_token: Optional[str] = None,
        cache_enabled: bool = True,
        language: str = "en-US",
    ):
        """Initialize TMDB provider.

        Args:
            access_token: TMDB API access token (Bearer token)
            cache_enabled: Whether to enable response caching
            language: Language for metadata (ISO 639-1 code)

        Raises:
            AuthenticationError: If access token is not provided
        """
        if not access_token:
            raise AuthenticationError("TMDB access token is required")

        self.access_token = access_token
        self.language = language
        self.cache = get_cache(enabled=cache_enabled)
        self.session = self.cache.get_session()

        # Rate limiting
        self._request_times: List[float] = []

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for TMDB API requests.

        Returns:
            dict: HTTP headers including authorization
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json;charset=utf-8",
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
            # Calculate wait time
            oldest = self._request_times[0]
            wait_time = self.RATE_LIMIT_WINDOW - (now - oldest)
            if wait_time > 0:
                time.sleep(wait_time)

        # Record this request
        self._request_times.append(time.time())

    def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 3,
    ) -> Dict[str, Any]:
        """Make a request to the TMDB API with retry logic.

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
        params = params or {}
        params.setdefault("language", self.language)

        self._rate_limit()

        for attempt in range(retry_count):
            try:
                response = self.session.get(url, headers=self._get_headers(), params=params)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise NotFoundError(f"Resource not found: {endpoint}")
                elif response.status_code == 401:
                    raise AuthenticationError("Invalid TMDB access token")
                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < retry_count - 1:
                        time.sleep(retry_after)
                        continue
                    raise RateLimitError(
                        "TMDB rate limit exceeded", retry_after=retry_after
                    )
                else:
                    response.raise_for_status()

            except requests.RequestException as e:
                if attempt == retry_count - 1:
                    raise ProviderError(f"TMDB API request failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

        raise ProviderError("TMDB API request failed after retries")

    def search_movie(
        self, title: str, year: Optional[int] = None, page: int = 1
    ) -> List[SearchResult]:
        """Search for movies by title.

        Args:
            title: Movie title to search for
            year: Optional release year for filtering
            page: Results page number (1-indexed)

        Returns:
            List[SearchResult]: List of search results

        Raises:
            ProviderError: If search fails
        """
        params: Dict[str, Any] = {"query": title, "page": page}
        if year:
            params["year"] = year

        try:
            data = self._request("search/movie", params=params)
            results = []

            for item in data.get("results", []):
                results.append(
                    SearchResult(
                        provider="tmdb",
                        id=str(item["id"]),
                        title=item.get("title", ""),
                        year=self._parse_year(item.get("release_date")),
                        plot=item.get("overview"),
                        rating=item.get("vote_average"),
                        poster_url=self._get_image_url(item.get("poster_path")),
                        media_type="movie",
                        relevance_score=item.get("popularity", 0.0),
                        raw_data=item,
                    )
                )

            return results

        except NotFoundError:
            return []

    def search_tv(
        self, title: str, year: Optional[int] = None, page: int = 1
    ) -> List[SearchResult]:
        """Search for TV shows by title.

        Args:
            title: TV show title to search for
            year: Optional first air year for filtering
            page: Results page number (1-indexed)

        Returns:
            List[SearchResult]: List of search results

        Raises:
            ProviderError: If search fails
        """
        params: Dict[str, Any] = {"query": title, "page": page}
        if year:
            params["first_air_date_year"] = year

        try:
            data = self._request("search/tv", params=params)
            results = []

            for item in data.get("results", []):
                results.append(
                    SearchResult(
                        provider="tmdb",
                        id=str(item["id"]),
                        title=item.get("name", ""),
                        year=self._parse_year(item.get("first_air_date")),
                        plot=item.get("overview"),
                        rating=item.get("vote_average"),
                        poster_url=self._get_image_url(item.get("poster_path")),
                        media_type="tv",
                        relevance_score=item.get("popularity", 0.0),
                        raw_data=item,
                    )
                )

            return results

        except NotFoundError:
            return []

    def get_movie(self, movie_id: str) -> MovieMetadata:
        """Get detailed movie metadata.

        Args:
            movie_id: TMDB movie ID

        Returns:
            MovieMetadata: Movie metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If movie not found
        """
        params = {"append_to_response": "credits,external_ids"}
        data = self._request(f"movie/{movie_id}", params=params)

        # Extract cast and crew
        credits = data.get("credits", {})
        cast = [c["name"] for c in credits.get("cast", [])[:15]]  # Top 15 cast
        crew_dict: Dict[str, List[str]] = {}

        for person in credits.get("crew", []):
            job = person.get("job", "Unknown")
            name = person.get("name", "")
            if job in ["Director", "Writer", "Producer"]:
                crew_dict.setdefault(job, []).append(name)

        # Extract external IDs
        external_ids = data.get("external_ids", {})

        # Collection info
        collection = None
        if data.get("belongs_to_collection"):
            collection = data["belongs_to_collection"].get("name")

        return MovieMetadata(
            provider="tmdb",
            id=str(data["id"]),
            title=data.get("title", ""),
            year=self._parse_year(data.get("release_date")),
            plot=data.get("overview"),
            runtime=data.get("runtime"),
            rating=data.get("vote_average"),
            genres=[g["name"] for g in data.get("genres", [])],
            cast=cast if cast else None,
            crew=crew_dict if crew_dict else None,
            poster_url=self._get_image_url(data.get("poster_path")),
            backdrop_url=self._get_image_url(data.get("backdrop_path"), size="original"),
            imdb_id=external_ids.get("imdb_id"),
            tmdb_id=str(data["id"]),
            collection=collection,
            raw_data=data,
        )

    def get_tv_show(self, show_id: str) -> TVShowMetadata:
        """Get detailed TV show metadata.

        Args:
            show_id: TMDB TV show ID

        Returns:
            TVShowMetadata: TV show metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If show not found
        """
        params = {"append_to_response": "credits,external_ids"}
        data = self._request(f"tv/{show_id}", params=params)

        # Extract cast
        credits = data.get("credits", {})
        cast = [c["name"] for c in credits.get("cast", [])[:15]]

        # Extract external IDs
        external_ids = data.get("external_ids", {})

        return TVShowMetadata(
            provider="tmdb",
            id=str(data["id"]),
            title=data.get("name", ""),
            year=self._parse_year(data.get("first_air_date")),
            plot=data.get("overview"),
            rating=data.get("vote_average"),
            genres=[g["name"] for g in data.get("genres", [])],
            cast=cast if cast else None,
            poster_url=self._get_image_url(data.get("poster_path")),
            backdrop_url=self._get_image_url(data.get("backdrop_path"), size="original"),
            imdb_id=external_ids.get("imdb_id"),
            tmdb_id=str(data["id"]),
            tvdb_id=str(external_ids["tvdb_id"]) if external_ids.get("tvdb_id") else None,
            seasons=data.get("number_of_seasons"),
            status=data.get("status"),
            raw_data=data,
        )

    def get_episode(
        self, show_id: str, season_number: int, episode_number: int
    ) -> EpisodeMetadata:
        """Get detailed episode metadata.

        Args:
            show_id: TMDB TV show ID
            season_number: Season number
            episode_number: Episode number

        Returns:
            EpisodeMetadata: Episode metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If episode not found
        """
        endpoint = f"tv/{show_id}/season/{season_number}/episode/{episode_number}"
        data = self._request(endpoint)

        return EpisodeMetadata(
            provider="tmdb",
            show_id=show_id,
            season_number=season_number,
            episode_number=episode_number,
            title=data.get("name"),
            plot=data.get("overview"),
            air_date=data.get("air_date"),
            runtime=data.get("runtime"),
            rating=data.get("vote_average"),
            still_url=self._get_image_url(data.get("still_path")),
            raw_data=data,
        )

    def _parse_year(self, date_str: Optional[str]) -> Optional[int]:
        """Parse year from ISO date string.

        Args:
            date_str: ISO date string (YYYY-MM-DD)

        Returns:
            int | None: Year or None if invalid
        """
        if not date_str:
            return None
        try:
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return None

    def _get_image_url(
        self, path: Optional[str], size: str = "w500"
    ) -> Optional[str]:
        """Build full image URL from TMDB path.

        Args:
            path: TMDB image path (e.g., "/abc123.jpg")
            size: Image size (w92, w154, w185, w342, w500, w780, original)

        Returns:
            str | None: Full image URL or None if no path
        """
        if not path:
            return None
        return urljoin(self.IMAGE_BASE_URL, f"{size}{path}")
