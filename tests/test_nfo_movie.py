"""Tests for movie NFO generation."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mo.nfo.movie import MovieNFOGenerator
from mo.providers.base import Actor, MovieMetadata, Rating


class TestMovieNFOGenerator:
    """Test movie NFO generator initialization."""

    def test_init(self):
        """Test generator initialization."""
        generator = MovieNFOGenerator()
        assert generator is not None


class TestGenerateMovieNFO:
    """Test movie NFO generation."""

    @pytest.fixture
    def generator(self):
        """Create a generator for testing."""
        return MovieNFOGenerator()

    @pytest.fixture
    def minimal_metadata(self):
        """Create minimal movie metadata."""
        return MovieMetadata(provider="test", id="test123", title="Test Movie",
            year=2023,
        )

    @pytest.fixture
    def full_metadata(self):
        """Create full movie metadata."""
        return MovieMetadata(provider="test", id="test123", title="Test Movie",
            original_title="Original Test Movie",
            sort_title="Test Movie, The",
            year=2023,
            premiered="2023-01-15",
            plot="A test movie plot.",
            tagline="The ultimate test",
            runtime=120,
            content_rating="PG-13",
            imdb_id="tt1234567",
            tmdb_id="12345",
            genres=["Action", "Thriller"],
            studios=["Test Studios", "Another Studio"],
            collection="Test Collection",
            directors=["John Director"],
            writers=["Jane Writer", "Bob Writer"],
            actors=[
                Actor(name="Lead Actor", role="Hero", order=0),
                Actor(name="Supporting Actor", role="Sidekick", order=1),
            ],
            ratings=[
                Rating(source="imdb", value=8.5, votes=10000),
                Rating(source="tmdb", value=8.0),
            ],
        )

    def test_generate_minimal_nfo(self, generator, minimal_metadata):
        """Test generating NFO with minimal metadata."""
        nfo = generator.generate(minimal_metadata)

        assert '<?xml version="1.0" encoding="UTF-8"' in nfo
        assert "<movie>" in nfo
        assert "<title>Test Movie</title>" in nfo
        assert "<year>2023</year>" in nfo
        assert "</movie>" in nfo

    def test_generate_full_nfo(self, generator, full_metadata):
        """Test generating NFO with full metadata."""
        nfo = generator.generate(full_metadata)

        # Check all major elements
        assert "<title>Test Movie</title>" in nfo
        assert "<originaltitle>Original Test Movie</originaltitle>" in nfo
        assert "<sorttitle>Test Movie, The</sorttitle>" in nfo
        assert "<year>2023</year>" in nfo
        assert "<plot>A test movie plot.</plot>" in nfo
        assert "<tagline>The ultimate test</tagline>" in nfo
        assert "<runtime>120</runtime>" in nfo
        assert "<mpaa>PG-13</mpaa>" in nfo

    def test_generate_with_unique_ids(self, generator, full_metadata):
        """Test unique ID generation."""
        nfo = generator.generate(full_metadata)

        assert 'type="imdb"' in nfo
        assert 'type="tmdb"' in nfo
        assert "tt1234567" in nfo
        assert "12345" in nfo

    def test_generate_with_legacy_id(self, generator, full_metadata):
        """Test legacy ID element."""
        nfo = generator.generate(full_metadata, include_legacy_id=True)
        assert "<id>tt1234567</id>" in nfo

    def test_generate_without_legacy_id(self, generator, full_metadata):
        """Test without legacy ID element."""
        nfo = generator.generate(full_metadata, include_legacy_id=False)
        # Should not have standalone <id> (only <uniqueid>)
        assert "<id>tt1234567</id>" not in nfo
        assert "<uniqueid" in nfo

    def test_generate_with_genres(self, generator, full_metadata):
        """Test genre elements."""
        nfo = generator.generate(full_metadata)
        assert "<genre>Action</genre>" in nfo
        assert "<genre>Thriller</genre>" in nfo

    def test_generate_with_studios(self, generator, full_metadata):
        """Test studio elements."""
        nfo = generator.generate(full_metadata)
        assert "<studio>Test Studios</studio>" in nfo
        assert "<studio>Another Studio</studio>" in nfo

    def test_generate_with_collection(self, generator, full_metadata):
        """Test collection/set element."""
        nfo = generator.generate(full_metadata)
        assert "<set>" in nfo
        assert "<name>Test Collection</name>" in nfo

    def test_generate_with_credits(self, generator, full_metadata):
        """Test director and writer elements."""
        nfo = generator.generate(full_metadata)
        assert "<director>John Director</director>" in nfo
        assert "<writer>Jane Writer</writer>" in nfo
        assert "<writer>Bob Writer</writer>" in nfo

    def test_generate_with_actors(self, generator, full_metadata):
        """Test actor elements."""
        nfo = generator.generate(full_metadata)
        assert "<actor>" in nfo
        assert "<name>Lead Actor</name>" in nfo
        assert "<role>Hero</role>" in nfo
        assert "<order>0</order>" in nfo

    def test_generate_with_ratings(self, generator, full_metadata):
        """Test ratings elements."""
        nfo = generator.generate(full_metadata)
        assert "<ratings>" in nfo
        assert 'name="imdb"' in nfo
        assert "<value>8.5</value>" in nfo
        assert "<votes>10000</votes>" in nfo

    def test_generate_valid_xml(self, generator, full_metadata):
        """Test that generated XML is valid."""
        nfo = generator.generate(full_metadata)
        # Parse to verify it's valid XML
        xml_lines = nfo.split('\n')
        xml_content = '\n'.join(xml_lines[1:])  # Skip declaration
        root = ET.fromstring(xml_content)
        assert root.tag == "movie"

    def test_generate_skips_none_values(self, generator):
        """Test that None values are skipped."""
        metadata = MovieMetadata(provider="test", id="test123", title="Test",
            year=2023,
            plot=None,
            tagline=None,
        )
        nfo = generator.generate(metadata)
        assert "<plot>" not in nfo
        assert "<tagline>" not in nfo

    def test_generate_skips_original_title_if_same(self, generator):
        """Test that original_title is skipped if same as title."""
        metadata = MovieMetadata(provider="test", id="test123", title="Test Movie",
            original_title="Test Movie",
            year=2023,
        )
        nfo = generator.generate(metadata)
        assert "<originaltitle>" not in nfo


class TestGenerateToFile:
    """Test generating NFO to file."""

    @pytest.fixture
    def generator(self):
        """Create a generator for testing."""
        return MovieNFOGenerator()

    @pytest.fixture
    def metadata(self):
        """Create test metadata."""
        return MovieMetadata(provider="test", id="test123", title="Test Movie",
            year=2023,
            imdb_id="tt1234567",
        )

    def test_generate_to_file_creates_file(self, generator, metadata):
        """Test that generate_to_file creates a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "movie.nfo"
            generator.generate_to_file(metadata, str(filepath))
            assert filepath.exists()

    def test_generate_to_file_content(self, generator, metadata):
        """Test file content matches generated NFO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "movie.nfo"
            generator.generate_to_file(metadata, str(filepath))

            content = filepath.read_text(encoding='utf-8')
            expected = generator.generate(metadata)
            assert content == expected

    def test_generate_to_file_utf8_encoding(self, generator):
        """Test UTF-8 encoding with special characters."""
        metadata = MovieMetadata(provider="test", id="test123", title="Test Café",
            year=2023,
            plot="Plot with émojis 🎬",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "movie.nfo"
            generator.generate_to_file(metadata, str(filepath))

            content = filepath.read_text(encoding='utf-8')
            assert "Café" in content or "Caf" in content


class TestElementOrdering:
    """Test that elements appear in the correct order."""

    @pytest.fixture
    def generator(self):
        """Create a generator for testing."""
        return MovieNFOGenerator()

    def test_title_before_plot(self, generator):
        """Test that title appears before plot."""
        metadata = MovieMetadata(provider="test", id="test123", title="Test", year=2023, plot="Plot")
        nfo = generator.generate(metadata)
        title_pos = nfo.index("<title>")
        plot_pos = nfo.index("<plot>")
        assert title_pos < plot_pos

    def test_year_before_plot(self, generator):
        """Test that year appears before plot."""
        metadata = MovieMetadata(provider="test", id="test123", title="Test", year=2023, plot="Plot")
        nfo = generator.generate(metadata)
        year_pos = nfo.index("<year>")
        plot_pos = nfo.index("<plot>")
        assert year_pos < plot_pos

    def test_uniqueid_before_genres(self, generator):
        """Test that uniqueid appears before genres."""
        metadata = MovieMetadata(provider="test", id="test123", title="Test",
            year=2023,
            imdb_id="tt123",
            genres=["Action"],
        )
        nfo = generator.generate(metadata)
        uniqueid_pos = nfo.index("<uniqueid")
        genre_pos = nfo.index("<genre>")
        assert uniqueid_pos < genre_pos
