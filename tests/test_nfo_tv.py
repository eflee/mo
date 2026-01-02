"""Tests for TV show and episode NFO generation."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mo.nfo.tv import EpisodeNFOGenerator, TVShowNFOGenerator
from mo.providers.base import Actor, EpisodeMetadata, Rating, TVShowMetadata


class TestTVShowNFOGenerator:
    """Test TV show NFO generator."""

    @pytest.fixture
    def generator(self):
        """Create a generator for testing."""
        return TVShowNFOGenerator()

    @pytest.fixture
    def minimal_metadata(self):
        """Create minimal TV show metadata."""
        return TVShowMetadata(provider="test", id="test123", title="Test Show",
            year=2023,
        )

    @pytest.fixture
    def full_metadata(self):
        """Create full TV show metadata."""
        return TVShowMetadata(provider="test", id="test123", title="Test Show",
            original_title="Original Test Show",
            year=2023,
            plot="A test TV show.",
            premiered="2023-01-01",
            status="Continuing",
            content_rating="TV-14",
            imdb_id="tt7654321",
            tmdb_id="54321",
            tvdb_id="987654",
            genres=["Drama", "Comedy"],
            networks=["Test Network"],
            actors=[
                Actor(name="Main Actor", role="Lead", order=0),
            ],
            ratings=[
                Rating(source="tvdb", value=9.0, votes=5000),
            ],
        )

    def test_generate_minimal_nfo(self, generator, minimal_metadata):
        """Test generating minimal tvshow.nfo."""
        nfo = generator.generate(minimal_metadata)

        assert "<tvshow>" in nfo
        assert "<title>Test Show</title>" in nfo
        assert "<year>2023</year>" in nfo
        assert "<season>-1</season>" in nfo
        assert "<episode>-1</episode>" in nfo
        assert "</tvshow>" in nfo

    def test_generate_full_nfo(self, generator, full_metadata):
        """Test generating full tvshow.nfo."""
        nfo = generator.generate(full_metadata)

        assert "<title>Test Show</title>" in nfo
        assert "<originaltitle>Original Test Show</originaltitle>" in nfo
        assert "<plot>A test TV show.</plot>" in nfo
        assert "<status>Continuing</status>" in nfo
        assert "<mpaa>TV-14</mpaa>" in nfo

    def test_generate_with_unique_ids(self, generator, full_metadata):
        """Test unique IDs in tvshow.nfo."""
        nfo = generator.generate(full_metadata)

        assert 'type="tvdb"' in nfo
        assert 'type="imdb"' in nfo
        assert 'type="tmdb"' in nfo
        assert "987654" in nfo

    def test_generate_with_episodeguide(self, generator, full_metadata):
        """Test episodeguide element with TVDB URL."""
        nfo = generator.generate(full_metadata)

        assert "<episodeguide>" in nfo
        assert "thetvdb.com" in nfo
        assert "987654" in nfo
        assert 'cache="tvdb-en.xml"' in nfo

    def test_generate_placeholder_season_episode(self, generator, minimal_metadata):
        """Test that placeholder season/episode are included."""
        nfo = generator.generate(minimal_metadata)

        assert "<season>-1</season>" in nfo
        assert "<episode>-1</episode>" in nfo

    def test_generate_valid_xml(self, generator, full_metadata):
        """Test that generated XML is valid."""
        nfo = generator.generate(full_metadata)
        xml_lines = nfo.split('\n')
        xml_content = '\n'.join(xml_lines[1:])
        root = ET.fromstring(xml_content)
        assert root.tag == "tvshow"

    def test_generate_to_file(self, generator, minimal_metadata):
        """Test writing tvshow.nfo to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "tvshow.nfo"
            generator.generate_to_file(minimal_metadata, str(filepath))
            assert filepath.exists()
            content = filepath.read_text(encoding='utf-8')
            assert "<tvshow>" in content


class TestEpisodeNFOGenerator:
    """Test episode NFO generator."""

    @pytest.fixture
    def generator(self):
        """Create a generator for testing."""
        return EpisodeNFOGenerator()

    @pytest.fixture
    def minimal_metadata(self):
        """Create minimal episode metadata."""
        return EpisodeMetadata(provider="test", show_id="show123", title="Pilot", season_number=1,
            episode_number=1,
        )

    @pytest.fixture
    def full_metadata(self):
        """Create full episode metadata."""
        return EpisodeMetadata(provider="test", show_id="show123", title="The Test Episode", show_title="Test Show",
            season_number=1,
            episode_number=5,
            plot="An episode plot.",
            aired="2023-02-15",
            runtime=42,
            imdb_id="tt1111111",
            tmdb_id="22222",
            tvdb_id="33333",
            directors=["Episode Director"],
            writers=["Episode Writer"],
            actors=[
                Actor(name="Guest Star", role="Guest", order=5),
            ],
            ratings=[
                Rating(source="imdb", value=8.8),
            ],
        )

    def test_generate_minimal_nfo(self, generator, minimal_metadata):
        """Test generating minimal episode NFO."""
        nfo = generator.generate(minimal_metadata)

        assert "<episodedetails>" in nfo
        assert "<title>Pilot</title>" in nfo
        assert "<season>1</season>" in nfo
        assert "<episode>1</episode>" in nfo
        assert "</episodedetails>" in nfo

    def test_generate_full_nfo(self, generator, full_metadata):
        """Test generating full episode NFO."""
        nfo = generator.generate(full_metadata)

        assert "<showtitle>Test Show</showtitle>" in nfo
        assert "<title>The Test Episode</title>" in nfo
        assert "<season>1</season>" in nfo
        assert "<episode>5</episode>" in nfo
        assert "<plot>An episode plot.</plot>" in nfo
        assert "<aired>2023-02-15</aired>" in nfo
        assert "<runtime>42</runtime>" in nfo

    def test_generate_with_multi_episode_end(self, generator):
        """Test multi-episode with episodenumberend."""
        metadata = EpisodeMetadata(provider="test", show_id="show123", title="Double Episode", season_number=1,
            episode_number=3,
            episode_number_end=4,
        )
        nfo = generator.generate(metadata)

        assert "<episode>3</episode>" in nfo
        assert "<episodenumberend>4</episodenumberend>" in nfo

    def test_generate_valid_xml(self, generator, full_metadata):
        """Test that generated XML is valid."""
        nfo = generator.generate(full_metadata)
        xml_lines = nfo.split('\n')
        xml_content = '\n'.join(xml_lines[1:])
        root = ET.fromstring(xml_content)
        assert root.tag == "episodedetails"

    def test_generate_season_zero_special_fields(self, generator):
        """Test special fields for Season 0 episodes."""
        metadata = EpisodeMetadata(provider="test", show_id="show123", title="Special Episode", season_number=0,
            episode_number=1,
            airs_after_season=1,
            airs_before_season=2,
            airs_before_episode=1,
            display_season=1,
            display_episode=13,
        )
        nfo = generator.generate(metadata)

        assert "<season>0</season>" in nfo
        assert "<airsafter_season>1</airsafter_season>" in nfo
        assert "<airsbefore_season>2</airsbefore_season>" in nfo
        assert "<airsbefore_episode>1</airsbefore_episode>" in nfo
        assert "<displayseason>1</displayseason>" in nfo
        assert "<displayepisode>13</displayepisode>" in nfo

    def test_generate_no_special_fields_for_regular_episode(self, generator):
        """Test that special fields are not added for regular episodes."""
        metadata = EpisodeMetadata(provider="test", show_id="show123", title="Regular Episode", season_number=1,
            episode_number=1,
        )
        nfo = generator.generate(metadata)

        assert "<airsafter_season>" not in nfo
        assert "<airsbefore_season>" not in nfo

    def test_generate_to_file(self, generator, minimal_metadata):
        """Test writing episode NFO to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "episode.nfo"
            generator.generate_to_file(minimal_metadata, str(filepath))
            assert filepath.exists()
            content = filepath.read_text(encoding='utf-8')
            assert "<episodedetails>" in content


class TestMultiEpisodeNFO:
    """Test multi-episode NFO generation."""

    @pytest.fixture
    def generator(self):
        """Create a generator for testing."""
        return EpisodeNFOGenerator()

    @pytest.fixture
    def episode_list(self):
        """Create a list of episodes."""
        return [
            EpisodeMetadata(provider="test", show_id="show123", title="Episode 1", season_number=1,
                episode_number=1,
            ),
            EpisodeMetadata(provider="test", show_id="show123", title="Episode 2", season_number=1,
                episode_number=2,
            ),
        ]

    def test_generate_multi_episode(self, generator, episode_list):
        """Test generating multi-episode NFO."""
        nfo = generator.generate_multi_episode(episode_list)

        # Should contain both episodes
        assert nfo.count("<episodedetails>") == 2
        assert "<title>Episode 1</title>" in nfo
        assert "<title>Episode 2</title>" in nfo
        assert "<episode>1</episode>" in nfo
        assert "<episode>2</episode>" in nfo

    def test_generate_multi_episode_to_file(self, generator, episode_list):
        """Test writing multi-episode NFO to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "multi.nfo"
            generator.generate_multi_episode_to_file(episode_list, str(filepath))

            content = filepath.read_text(encoding='utf-8')
            assert content.count("<episodedetails>") == 2


class TestTVNFOSkipsNoneValues:
    """Test that None values are properly skipped."""

    @pytest.fixture
    def show_generator(self):
        """Create a show generator."""
        return TVShowNFOGenerator()

    @pytest.fixture
    def episode_generator(self):
        """Create an episode generator."""
        return EpisodeNFOGenerator()

    def test_show_skips_none_plot(self, show_generator):
        """Test that None plot is skipped in show NFO."""
        metadata = TVShowMetadata(provider="test", id="test123", title="Test", year=2023, plot=None)
        nfo = show_generator.generate(metadata)
        assert "<plot>" not in nfo

    def test_episode_skips_none_aired(self, episode_generator):
        """Test that None aired date is skipped."""
        metadata = EpisodeMetadata(provider="test", show_id="show123", title="Test", season_number=1,
            episode_number=1,
            aired=None,
        )
        nfo = episode_generator.generate(metadata)
        assert "<aired>" not in nfo

    def test_show_skips_original_title_if_same(self, show_generator):
        """Test that original_title is skipped if same as title."""
        metadata = TVShowMetadata(provider="test", id="test123", title="Test Show",
            original_title="Test Show",
            year=2023,
        )
        nfo = show_generator.generate(metadata)
        assert "<originaltitle>" not in nfo
