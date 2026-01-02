"""TV show and episode NFO generation for Jellyfin."""

from typing import List

from mo.nfo.builder import NFOBuilder
from mo.providers.base import EpisodeMetadata, TVShowMetadata


class TVShowNFOGenerator:
    """Generate tvshow.nfo files for Jellyfin."""

    def generate(self, metadata: TVShowMetadata) -> str:
        """Generate a TV show NFO from metadata.

        Args:
            metadata: TV show metadata from provider

        Returns:
            str: XML string for the tvshow.nfo file
        """
        builder = NFOBuilder("tvshow")

        # Title
        builder.add_element("title", metadata.title)
        if metadata.original_title and metadata.original_title != metadata.title:
            builder.add_element("originaltitle", metadata.original_title)

        # Year
        if metadata.year:
            builder.add_element("year", metadata.year)

        # Plot
        if metadata.plot:
            builder.add_element("plot", metadata.plot)

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

        # Unique IDs
        if metadata.imdb_id or metadata.tmdb_id or metadata.tvdb_id:
            uniqueid_added = False
            if metadata.tvdb_id:
                builder.add_element(
                    "uniqueid", metadata.tvdb_id, type="tvdb", default="true"
                )
                uniqueid_added = True
            if metadata.imdb_id:
                builder.add_element(
                    "uniqueid",
                    metadata.imdb_id,
                    type="imdb",
                    default="false" if uniqueid_added else "true",
                )
                uniqueid_added = True
            if metadata.tmdb_id:
                builder.add_element(
                    "uniqueid",
                    metadata.tmdb_id,
                    type="tmdb",
                    default="false" if uniqueid_added else "true",
                )

        # Genres
        if metadata.genres:
            builder.add_elements("genre", metadata.genres)

        # Studios/Networks
        if metadata.networks:
            builder.add_elements("studio", metadata.networks)

        # Premiered date
        if metadata.premiered:
            builder.add_element("premiered", metadata.premiered)

        # Status
        if metadata.status:
            builder.add_element("status", metadata.status)

        # Episode guide (TVDB URL)
        if metadata.tvdb_id:
            episodeguide_elem = builder.add_element("episodeguide")
            url = f"https://thetvdb.com/?tab=series&id={metadata.tvdb_id}&lid=7"
            builder.add_element("url", url, parent=episodeguide_elem, cache="tvdb-en.xml")

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

        # Placeholder season and episode (Jellyfin convention)
        builder.add_element("season", "-1")
        builder.add_element("episode", "-1")

        return builder.to_string()

    def generate_to_file(self, metadata: TVShowMetadata, filepath: str) -> None:
        """Generate a TV show NFO and write it to a file.

        Args:
            metadata: TV show metadata from provider
            filepath: Path to output tvshow.nfo file
        """
        nfo_content = self.generate(metadata)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(nfo_content)


class EpisodeNFOGenerator:
    """Generate episode NFO files for Jellyfin."""

    def generate(
        self,
        metadata: EpisodeMetadata,
    ) -> str:
        """Generate an episode NFO from metadata.

        Args:
            metadata: Episode metadata from provider

        Returns:
            str: XML string for the episode NFO file
        """
        builder = NFOBuilder("episodedetails")

        # Show title
        if metadata.show_title:
            builder.add_element("showtitle", metadata.show_title)

        # Season and episode numbers
        if metadata.season_number is not None:
            builder.add_element("season", metadata.season_number)
        if metadata.episode_number is not None:
            builder.add_element("episode", metadata.episode_number)

        # Multi-episode end number
        if metadata.episode_number_end is not None:
            builder.add_element("episodenumberend", metadata.episode_number_end)

        # Episode title
        if metadata.title:
            builder.add_element("title", metadata.title)

        # Plot
        if metadata.plot:
            builder.add_element("plot", metadata.plot)

        # Air date
        if metadata.aired:
            builder.add_element("aired", metadata.aired)

        # Runtime
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

        # Unique IDs
        if metadata.imdb_id or metadata.tmdb_id or metadata.tvdb_id:
            uniqueid_added = False
            if metadata.tvdb_id:
                builder.add_element(
                    "uniqueid", metadata.tvdb_id, type="tvdb", default="true"
                )
                uniqueid_added = True
            if metadata.imdb_id:
                builder.add_element(
                    "uniqueid",
                    metadata.imdb_id,
                    type="imdb",
                    default="false" if uniqueid_added else "true",
                )
                uniqueid_added = True
            if metadata.tmdb_id:
                builder.add_element(
                    "uniqueid",
                    metadata.tmdb_id,
                    type="tmdb",
                    default="false" if uniqueid_added else "true",
                )

        # Credits
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

        # Special episode fields (Season 0 specials)
        if metadata.season_number == 0:
            if metadata.airs_after_season is not None:
                builder.add_element("airsafter_season", metadata.airs_after_season)
            if metadata.airs_before_season is not None:
                builder.add_element("airsbefore_season", metadata.airs_before_season)
            if metadata.airs_before_episode is not None:
                builder.add_element("airsbefore_episode", metadata.airs_before_episode)
            if metadata.display_season is not None:
                builder.add_element("displayseason", metadata.display_season)
            if metadata.display_episode is not None:
                builder.add_element("displayepisode", metadata.display_episode)

        return builder.to_string()

    def generate_multi_episode(self, episodes: List[EpisodeMetadata]) -> str:
        """Generate a multi-episode NFO file.

        Args:
            episodes: List of episode metadata

        Returns:
            str: XML string with multiple episodedetails blocks
        """
        # For multi-episode files, we need multiple <episodedetails> root elements
        # This is handled by concatenating multiple NFO outputs
        nfo_parts = []
        for episode in episodes:
            nfo_parts.append(self.generate(episode))

        # Join with newline
        return '\n'.join(nfo_parts)

    def generate_to_file(
        self,
        metadata: EpisodeMetadata,
        filepath: str,
    ) -> None:
        """Generate an episode NFO and write it to a file.

        Args:
            metadata: Episode metadata from provider
            filepath: Path to output episode NFO file
        """
        nfo_content = self.generate(metadata)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(nfo_content)

    def generate_multi_episode_to_file(
        self,
        episodes: List[EpisodeMetadata],
        filepath: str,
    ) -> None:
        """Generate a multi-episode NFO and write it to a file.

        Args:
            episodes: List of episode metadata
            filepath: Path to output episode NFO file
        """
        nfo_content = self.generate_multi_episode(episodes)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
