"""Movie NFO generation for Jellyfin."""

from mo.nfo.builder import NFOBuilder
from mo.providers.base import MovieMetadata


class MovieNFOGenerator:
    """Generate movie.nfo files for Jellyfin."""

    def generate(self, metadata: MovieMetadata, include_legacy_id: bool = True) -> str:
        """Generate a movie NFO from metadata.

        Args:
            metadata: Movie metadata from provider
            include_legacy_id: Include legacy <id> element for backwards compatibility

        Returns:
            str: XML string for the NFO file
        """
        builder = NFOBuilder("movie")

        # Title fields
        builder.add_element("title", metadata.title)
        if metadata.original_title and metadata.original_title != metadata.title:
            builder.add_element("originaltitle", metadata.original_title)
        if metadata.sort_title:
            builder.add_element("sorttitle", metadata.sort_title)

        # Year and dates
        if metadata.year:
            builder.add_element("year", metadata.year)
        if metadata.premiered:
            builder.add_element("premiered", metadata.premiered)

        # Plot and tagline
        if metadata.plot:
            builder.add_element("plot", metadata.plot)
        if metadata.tagline:
            builder.add_element("tagline", metadata.tagline)

        # Runtime (in minutes)
        if metadata.runtime:
            builder.add_element("runtime", metadata.runtime)

        # Ratings
        if metadata.ratings:
            ratings_elem = builder.add_element("ratings")
            for rating in metadata.ratings:
                rating_elem = builder.add_element("rating", parent=ratings_elem, name=rating.source)
                builder.add_element("value", rating.value, parent=rating_elem)
                if rating.votes:
                    builder.add_element("votes", rating.votes, parent=rating_elem)

        # Content rating (MPAA)
        if metadata.content_rating:
            builder.add_element("mpaa", metadata.content_rating)

        # Unique IDs (modern format)
        if metadata.imdb_id or metadata.tmdb_id:
            uniqueid_added = False
            if metadata.imdb_id:
                builder.add_element(
                    "uniqueid", metadata.imdb_id, type="imdb", default="true"
                )
                uniqueid_added = True
            if metadata.tmdb_id:
                builder.add_element(
                    "uniqueid",
                    metadata.tmdb_id,
                    type="tmdb",
                    default="false" if uniqueid_added else "true",
                )

        # Legacy ID (for backwards compatibility with older Jellyfin versions)
        if include_legacy_id and metadata.imdb_id:
            builder.add_element("id", metadata.imdb_id)

        # Genres
        if metadata.genres:
            builder.add_elements("genre", metadata.genres)

        # Studios
        if metadata.studios:
            builder.add_elements("studio", metadata.studios)

        # Collection (set)
        if metadata.collection:
            set_elem = builder.add_element("set")
            builder.add_element("name", metadata.collection, parent=set_elem)
            # Add tmdbcolid if we have tmdb_id (collection ID would need to be in metadata)
            # This is a placeholder for future enhancement

        # Credits (director, writer)
        if metadata.directors:
            builder.add_elements("director", metadata.directors)
        if metadata.writers:
            builder.add_elements("writer", metadata.writers)

        # Actors
        if metadata.actors:
            for actor in metadata.actors:
                actor_elem = builder.add_element("actor")
                builder.add_element("name", actor.name, parent=actor_elem)
                if actor.role:
                    builder.add_element("role", actor.role, parent=actor_elem)
                if actor.order is not None:
                    builder.add_element("order", actor.order, parent=actor_elem)
                if actor.thumb:
                    builder.add_element("thumb", actor.thumb, parent=actor_elem)

        return builder.to_string()

    def generate_to_file(
        self,
        metadata: MovieMetadata,
        filepath: str,
        include_legacy_id: bool = True,
    ) -> None:
        """Generate a movie NFO and write it to a file.

        Args:
            metadata: Movie metadata from provider
            filepath: Path to output NFO file
            include_legacy_id: Include legacy <id> element for backwards compatibility
        """
        nfo_content = self.generate(metadata, include_legacy_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
