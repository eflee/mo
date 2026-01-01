"""OMDb (Open Movie Database) API client.

Implements OMDb API for movie metadata retrieval as a supplementary source.
Particularly useful for IMDb ratings and as a fallback source.
Requires an API key from https://www.omdbapi.com/apikey.aspx
"""

import time
from typing import Any, Dict, List, Optional

import requests

from mo.providers.base import (
    AuthenticationError,
    MovieMetadata,
    NotFoundError,
    ProviderError,
    RateLimitError,
    SearchResult,
)
from mo.providers.cache import get_cache


class OMDbProvider:
    """OMDb API client for movie metadata."""

    BASE_URL = "https://www.omdbapi.com/"

    # Rate limiting: Free tier allows 1000 requests per day
    MAX_REQUESTS_PER_DAY = 1000
    RATE_LIMIT_WINDOW = 24 * 60 * 60  # 24 hours in seconds

    def __init__(self, api_key: Optional[str] = None, cache_enabled: bool = True):
        """Initialize OMDb provider.

        Args:
            api_key: OMDb API key
            cache_enabled: Whether to enable response caching

        Raises:
            AuthenticationError: If API key is not provided
        """
        if not api_key:
            raise AuthenticationError("OMDb API key is required")

        self.api_key = api_key
        self.cache = get_cache(enabled=cache_enabled)
        self.session = self.cache.get_session()

        # Rate limiting
        self._request_times: List[float] = []

    def _rate_limit(self) -> None:
        """Apply rate limiting to requests."""
        now = time.time()

        # Remove requests older than 24 hours
        self._request_times = [
            t for t in self._request_times if now - t < self.RATE_LIMIT_WINDOW
        ]

        # Check if we're at the daily limit
        if len(self._request_times) >= self.MAX_REQUESTS_PER_DAY:
            oldest = self._request_times[0]
            wait_time = self.RATE_LIMIT_WINDOW - (now - oldest)
            raise RateLimitError(
                f"OMDb daily rate limit exceeded ({self.MAX_REQUESTS_PER_DAY} requests/day)",
                retry_after=int(wait_time),
            )

        self._request_times.append(time.time())

    def _request(
        self, params: Dict[str, Any], retry_count: int = 3
    ) -> Dict[str, Any]:
        """Make a request to OMDb API with retry logic.

        Args:
            params: Query parameters
            retry_count: Number of retries on failure

        Returns:
            dict: JSON response

        Raises:
            ProviderError: If request fails
            RateLimitError: If rate limit exceeded
            NotFoundError: If resource not found
        """
        params["apikey"] = self.api_key

        self._rate_limit()

        for attempt in range(retry_count):
            try:
                response = self.session.get(self.BASE_URL, params=params)
                response.raise_for_status()

                data = response.json()

                # OMDb returns error in response body
                if data.get("Response") == "False":
                    error = data.get("Error", "Unknown error")
                    if "not found" in error.lower():
                        raise NotFoundError(error)
                    elif "limit" in error.lower():
                        raise RateLimitError(error)
                    else:
                        raise ProviderError(f"OMDb error: {error}")

                return data

            except requests.RequestException as e:
                if attempt == retry_count - 1:
                    raise ProviderError(f"OMDb API request failed: {e}")
                time.sleep(2 ** attempt)

        raise ProviderError("OMDb API request failed after retries")

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
        params: Dict[str, Any] = {"s": title, "type": "movie", "page": page}
        if year:
            params["y"] = year

        try:
            data = self._request(params)
            results = []

            for item in data.get("Search", []):
                results.append(
                    SearchResult(
                        provider="omdb",
                        id=item.get("imdbID", ""),
                        title=item.get("Title", ""),
                        year=self._parse_year(item.get("Year")),
                        plot=None,  # Not available in search results
                        rating=None,  # Not available in search results
                        poster_url=item.get("Poster") if item.get("Poster") != "N/A" else None,
                        media_type="movie",
                        relevance_score=0.0,
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
        params: Dict[str, Any] = {"s": title, "type": "series", "page": page}
        if year:
            params["y"] = year

        try:
            data = self._request(params)
            results = []

            for item in data.get("Search", []):
                results.append(
                    SearchResult(
                        provider="omdb",
                        id=item.get("imdbID", ""),
                        title=item.get("Title", ""),
                        year=self._parse_year(item.get("Year")),
                        plot=None,
                        rating=None,
                        poster_url=item.get("Poster") if item.get("Poster") != "N/A" else None,
                        media_type="tv",
                        relevance_score=0.0,
                        raw_data=item,
                    )
                )

            return results

        except NotFoundError:
            return []

    def get_movie(self, movie_id: str) -> MovieMetadata:
        """Get detailed movie metadata by IMDb ID.

        Args:
            movie_id: IMDb ID (e.g., "tt1234567")

        Returns:
            MovieMetadata: Movie metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If movie not found
        """
        params = {"i": movie_id, "type": "movie", "plot": "full"}
        data = self._request(params)

        # Parse runtime (format: "142 min")
        runtime = None
        if data.get("Runtime") and data["Runtime"] != "N/A":
            try:
                runtime = int(data["Runtime"].split()[0])
            except (ValueError, IndexError):
                pass

        # Parse rating
        rating = None
        if data.get("imdbRating") and data["imdbRating"] != "N/A":
            try:
                rating = float(data["imdbRating"])
            except ValueError:
                pass

        # Parse genres
        genres = None
        if data.get("Genre") and data["Genre"] != "N/A":
            genres = [g.strip() for g in data["Genre"].split(",")]

        # Parse cast
        cast = None
        if data.get("Actors") and data["Actors"] != "N/A":
            cast = [a.strip() for a in data["Actors"].split(",")]

        # Parse crew
        crew = {}
        if data.get("Director") and data["Director"] != "N/A":
            crew["Director"] = [d.strip() for d in data["Director"].split(",")]
        if data.get("Writer") and data["Writer"] != "N/A":
            crew["Writer"] = [w.strip() for w in data["Writer"].split(",")]

        return MovieMetadata(
            provider="omdb",
            id=data.get("imdbID", ""),
            title=data.get("Title", ""),
            year=self._parse_year(data.get("Year")),
            plot=data.get("Plot") if data.get("Plot") != "N/A" else None,
            runtime=runtime,
            rating=rating,
            genres=genres,
            cast=cast,
            crew=crew if crew else None,
            poster_url=data.get("Poster") if data.get("Poster") != "N/A" else None,
            backdrop_url=None,  # OMDb doesn't provide backdrops
            imdb_id=data.get("imdbID"),
            tmdb_id=None,
            collection=None,
            raw_data=data,
        )

    def get_movie_by_title(
        self, title: str, year: Optional[int] = None
    ) -> MovieMetadata:
        """Get movie metadata by title (convenience method).

        Args:
            title: Movie title
            year: Optional release year

        Returns:
            MovieMetadata: Movie metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If movie not found
        """
        params: Dict[str, Any] = {"t": title, "type": "movie", "plot": "full"}
        if year:
            params["y"] = year

        data = self._request(params)

        # Reuse get_movie logic by passing the retrieved data
        imdb_id = data.get("imdbID")
        if not imdb_id:
            raise NotFoundError(f"Movie not found: {title}")

        # We already have the full data, so parse it directly
        runtime = None
        if data.get("Runtime") and data["Runtime"] != "N/A":
            try:
                runtime = int(data["Runtime"].split()[0])
            except (ValueError, IndexError):
                pass

        rating = None
        if data.get("imdbRating") and data["imdbRating"] != "N/A":
            try:
                rating = float(data["imdbRating"])
            except ValueError:
                pass

        genres = None
        if data.get("Genre") and data["Genre"] != "N/A":
            genres = [g.strip() for g in data["Genre"].split(",")]

        cast = None
        if data.get("Actors") and data["Actors"] != "N/A":
            cast = [a.strip() for a in data["Actors"].split(",")]

        crew = {}
        if data.get("Director") and data["Director"] != "N/A":
            crew["Director"] = [d.strip() for d in data["Director"].split(",")]
        if data.get("Writer") and data["Writer"] != "N/A":
            crew["Writer"] = [w.strip() for w in data["Writer"].split(",")]

        return MovieMetadata(
            provider="omdb",
            id=imdb_id,
            title=data.get("Title", ""),
            year=self._parse_year(data.get("Year")),
            plot=data.get("Plot") if data.get("Plot") != "N/A" else None,
            runtime=runtime,
            rating=rating,
            genres=genres,
            cast=cast,
            crew=crew if crew else None,
            poster_url=data.get("Poster") if data.get("Poster") != "N/A" else None,
            backdrop_url=None,
            imdb_id=imdb_id,
            tmdb_id=None,
            collection=None,
            raw_data=data,
        )

    def _parse_year(self, year_str: Optional[str]) -> Optional[int]:
        """Parse year from OMDb year string.

        OMDb returns years in various formats: "2010", "2010-2015", "2010-"

        Args:
            year_str: Year string from OMDb

        Returns:
            int | None: Year or None if invalid
        """
        if not year_str or year_str == "N/A":
            return None

        try:
            # Extract first year from range
            return int(year_str.split("-")[0].strip())
        except (ValueError, IndexError):
            return None
