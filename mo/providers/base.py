"""Base metadata provider interface and exceptions."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


class ProviderError(Exception):
    """Base exception for metadata provider errors."""

    pass


class RateLimitError(ProviderError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying (if known)
        """
        super().__init__(message)
        self.retry_after = retry_after


class AuthenticationError(ProviderError):
    """Raised when API authentication fails."""

    pass


class NotFoundError(ProviderError):
    """Raised when requested resource is not found."""

    pass


@dataclass
class SearchResult:
    """Generic search result from a metadata provider."""

    provider: str
    id: str
    title: str
    year: Optional[int] = None
    plot: Optional[str] = None
    rating: Optional[float] = None
    poster_url: Optional[str] = None
    media_type: Optional[str] = None  # "movie" or "tv"
    relevance_score: float = 0.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class MovieMetadata:
    """Movie metadata from a provider."""

    provider: str
    id: str
    title: str
    year: Optional[int] = None
    plot: Optional[str] = None
    runtime: Optional[int] = None  # minutes
    rating: Optional[float] = None
    genres: Optional[List[str]] = None
    cast: Optional[List[str]] = None
    crew: Optional[Dict[str, List[str]]] = None  # role -> names
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    collection: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class TVShowMetadata:
    """TV show metadata from a provider."""

    provider: str
    id: str
    title: str
    year: Optional[int] = None
    plot: Optional[str] = None
    rating: Optional[float] = None
    genres: Optional[List[str]] = None
    cast: Optional[List[str]] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    seasons: Optional[int] = None
    status: Optional[str] = None  # "Continuing", "Ended", etc.
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class EpisodeMetadata:
    """TV episode metadata from a provider."""

    provider: str
    show_id: str
    season_number: int
    episode_number: int
    title: Optional[str] = None
    plot: Optional[str] = None
    air_date: Optional[str] = None  # ISO format YYYY-MM-DD
    runtime: Optional[int] = None  # minutes
    rating: Optional[float] = None
    still_url: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class MetadataProvider(Protocol):
    """Protocol for metadata providers.

    Providers should implement this interface to be compatible with the
    metadata fetching system. All methods should raise ProviderError or
    its subclasses on failure.
    """

    def search_movie(self, title: str, year: Optional[int] = None) -> List[SearchResult]:
        """Search for movies by title and optional year.

        Args:
            title: Movie title to search for
            year: Optional release year for filtering

        Returns:
            List[SearchResult]: List of search results

        Raises:
            ProviderError: If search fails
            RateLimitError: If rate limit exceeded
        """
        ...

    def search_tv(self, title: str, year: Optional[int] = None) -> List[SearchResult]:
        """Search for TV shows by title and optional year.

        Args:
            title: TV show title to search for
            year: Optional first air year for filtering

        Returns:
            List[SearchResult]: List of search results

        Raises:
            ProviderError: If search fails
            RateLimitError: If rate limit exceeded
        """
        ...

    def get_movie(self, movie_id: str) -> MovieMetadata:
        """Get detailed movie metadata.

        Args:
            movie_id: Provider-specific movie ID

        Returns:
            MovieMetadata: Movie metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If movie not found
            RateLimitError: If rate limit exceeded
        """
        ...

    def get_tv_show(self, show_id: str) -> TVShowMetadata:
        """Get detailed TV show metadata.

        Args:
            show_id: Provider-specific show ID

        Returns:
            TVShowMetadata: TV show metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If show not found
            RateLimitError: If rate limit exceeded
        """
        ...

    def get_episode(
        self, show_id: str, season_number: int, episode_number: int
    ) -> EpisodeMetadata:
        """Get detailed episode metadata.

        Args:
            show_id: Provider-specific show ID
            season_number: Season number
            episode_number: Episode number

        Returns:
            EpisodeMetadata: Episode metadata

        Raises:
            ProviderError: If retrieval fails
            NotFoundError: If episode not found
            RateLimitError: If rate limit exceeded
        """
        ...
