"""Metadata provider integrations for TMDB, TheTVDB, and OMDb.

This module provides API clients for fetching movie and TV show metadata
from various providers. Each provider implements a common interface for
searching and retrieving metadata, with built-in caching and error handling.
"""

from mo.providers.base import (
    AuthenticationError,
    EpisodeMetadata,
    MetadataProvider,
    MovieMetadata,
    NotFoundError,
    ProviderError,
    RateLimitError,
    SearchResult,
    TVShowMetadata,
)
from mo.providers.cache import MetadataCache, clear_cache, get_cache
from mo.providers.omdb import OMDbProvider
from mo.providers.search import InteractiveSearch, fuzzy_match_score
from mo.providers.tmdb import TMDBProvider
from mo.providers.tvdb import TheTVDBProvider

__all__ = [
    "AuthenticationError",
    "EpisodeMetadata",
    "InteractiveSearch",
    "MetadataCache",
    "MetadataProvider",
    "MovieMetadata",
    "NotFoundError",
    "OMDbProvider",
    "ProviderError",
    "RateLimitError",
    "SearchResult",
    "TMDBProvider",
    "TVShowMetadata",
    "TheTVDBProvider",
    "clear_cache",
    "fuzzy_match_score",
    "get_cache",
]
