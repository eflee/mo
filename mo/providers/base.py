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
class Actor:
    """Actor information for NFO generation."""

    name: str
    role: Optional[str] = None
    order: Optional[int] = None
    thumb: Optional[str] = None  # URL to actor photo


@dataclass
class Rating:
    """Rating information from a provider."""

    source: str  # e.g., "imdb", "tmdb", "tvdb"
    value: float  # Rating value (e.g., 8.5)
    votes: Optional[int] = None  # Number of votes


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
    original_title: Optional[str] = None
    sort_title: Optional[str] = None
    plot: Optional[str] = None
    tagline: Optional[str] = None
    runtime: Optional[int] = None  # minutes
    premiered: Optional[str] = None  # ISO format YYYY-MM-DD
    rating: Optional[float] = None
    ratings: Optional[List[Rating]] = None  # Multiple rating sources
    content_rating: Optional[str] = None  # MPAA rating (e.g., "PG-13")
    genres: Optional[List[str]] = None
    studios: Optional[List[str]] = None
    collection: Optional[str] = None
    directors: Optional[List[str]] = None
    writers: Optional[List[str]] = None
    actors: Optional[List[Actor]] = None
    cast: Optional[List[str]] = None  # Legacy simple cast list
    crew: Optional[Dict[str, List[str]]] = None  # role -> names
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class TVShowMetadata:
    """TV show metadata from a provider."""

    provider: str
    id: str
    title: str
    year: Optional[int] = None
    original_title: Optional[str] = None
    plot: Optional[str] = None
    premiered: Optional[str] = None  # ISO format YYYY-MM-DD
    rating: Optional[float] = None
    ratings: Optional[List[Rating]] = None
    content_rating: Optional[str] = None
    genres: Optional[List[str]] = None
    networks: Optional[List[str]] = None  # Studios/Networks
    actors: Optional[List[Actor]] = None
    cast: Optional[List[str]] = None  # Legacy simple cast list
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
    show_title: Optional[str] = None
    plot: Optional[str] = None
    aired: Optional[str] = None  # ISO format YYYY-MM-DD (renamed from air_date)
    runtime: Optional[int] = None  # minutes
    rating: Optional[float] = None
    ratings: Optional[List[Rating]] = None
    directors: Optional[List[str]] = None
    writers: Optional[List[str]] = None
    actors: Optional[List[Actor]] = None
    still_url: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    episode_number_end: Optional[int] = None  # For multi-episode files
    # Special episode fields (Season 0 specials)
    airs_after_season: Optional[int] = None
    airs_before_season: Optional[int] = None
    airs_before_episode: Optional[int] = None
    display_season: Optional[int] = None
    display_episode: Optional[int] = None
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
