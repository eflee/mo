"""Tests for NFO XML builder."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mo.nfo.builder import NFOBuilder


class TestNFOBuilder:
    """Test NFO builder initialization."""

    def test_init_creates_root(self):
        """Test that initialization creates a root element."""
        builder = NFOBuilder("movie")
        assert builder.root.tag == "movie"

    def test_init_with_different_tags(self):
        """Test initialization with different root tags."""
        for tag in ["movie", "tvshow", "episodedetails"]:
            builder = NFOBuilder(tag)
            assert builder.root.tag == tag


class TestAddElement:
    """Test adding elements to NFO."""

    @pytest.fixture
    def builder(self):
        """Create a builder for testing."""
        return NFOBuilder("movie")

    def test_add_element_with_text(self, builder):
        """Test adding an element with text content."""
        elem = builder.add_element("title", "Test Movie")
        assert elem.tag == "title"
        assert elem.text == "Test Movie"

    def test_add_element_without_text(self, builder):
        """Test adding an element without text."""
        elem = builder.add_element("ratings")
        assert elem.tag == "ratings"
        assert elem.text is None

    def test_add_element_with_attributes(self, builder):
        """Test adding an element with attributes."""
        elem = builder.add_element("uniqueid", "tt1234567", type="imdb", default="true")
        assert elem.get("type") == "imdb"
        assert elem.get("default") == "true"
        assert elem.text == "tt1234567"

    def test_add_element_to_parent(self, builder):
        """Test adding an element to a specific parent."""
        parent = builder.add_element("ratings")
        child = builder.add_element("rating", "8.5", parent=parent)
        assert child in list(parent)

    def test_add_element_converts_to_string(self, builder):
        """Test that numeric values are converted to strings."""
        elem = builder.add_element("year", 2023)
        assert elem.text == "2023"

    def test_add_element_skips_none_text(self, builder):
        """Test that None text is handled properly."""
        elem = builder.add_element("tagline", None)
        assert elem.text is None


class TestAddElements:
    """Test adding multiple elements."""

    @pytest.fixture
    def builder(self):
        """Create a builder for testing."""
        return NFOBuilder("movie")

    def test_add_elements_creates_multiple(self, builder):
        """Test adding multiple elements."""
        genres = ["Action", "Thriller", "Drama"]
        elements = builder.add_elements("genre", genres)
        assert len(elements) == 3
        assert elements[0].text == "Action"
        assert elements[1].text == "Thriller"
        assert elements[2].text == "Drama"

    def test_add_elements_skips_none(self, builder):
        """Test that None values are skipped."""
        values = ["Action", None, "Drama"]
        elements = builder.add_elements("genre", values)
        assert len(elements) == 2
        assert elements[0].text == "Action"
        assert elements[1].text == "Drama"

    def test_add_elements_empty_list(self, builder):
        """Test adding elements from an empty list."""
        elements = builder.add_elements("genre", [])
        assert len(elements) == 0


class TestToString:
    """Test XML string generation."""

    @pytest.fixture
    def builder(self):
        """Create a builder with some content."""
        builder = NFOBuilder("movie")
        builder.add_element("title", "Test Movie")
        builder.add_element("year", 2023)
        return builder

    def test_to_string_contains_xml_declaration(self, builder):
        """Test that output contains XML declaration."""
        xml = builder.to_string()
        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"')

    def test_to_string_contains_content(self, builder):
        """Test that output contains the elements."""
        xml = builder.to_string()
        assert "<title>Test Movie</title>" in xml
        assert "<year>2023</year>" in xml

    def test_to_string_pretty_formatting(self, builder):
        """Test pretty-printed formatting."""
        xml = builder.to_string(pretty=True)
        # Should have indentation
        assert "  <title>" in xml or "\n  <" in xml

    def test_to_string_compact_formatting(self, builder):
        """Test compact formatting without pretty-printing."""
        xml = builder.to_string(pretty=False)
        # Should not have extra whitespace between tags
        assert xml.count('\n') <= 1  # Only the declaration line

    def test_to_string_valid_xml(self, builder):
        """Test that generated XML is valid and parseable."""
        xml = builder.to_string()
        # Remove XML declaration for ET parsing
        xml_content = '\n'.join(xml.split('\n')[1:])
        root = ET.fromstring(xml_content)
        assert root.tag == "movie"
        assert root.find("title").text == "Test Movie"

    def test_to_string_utf8_encoding(self, builder):
        """Test UTF-8 encoding with special characters."""
        builder.add_element("plot", "Test with émojis 🎬 and spëcial chars")
        xml = builder.to_string()
        assert "émojis" in xml or "&#" in xml  # Either literal or encoded


class TestWrite:
    """Test writing NFO to file."""

    @pytest.fixture
    def builder(self):
        """Create a builder with content."""
        builder = NFOBuilder("movie")
        builder.add_element("title", "Test Movie")
        return builder

    def test_write_creates_file(self, builder):
        """Test that write creates a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.nfo"
            builder.write(str(filepath))
            assert filepath.exists()

    def test_write_utf8_encoding(self, builder):
        """Test that file is written with UTF-8 encoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.nfo"
            builder.write(str(filepath))
            # Read and verify encoding
            content = filepath.read_text(encoding='utf-8')
            assert "UTF-8" in content

    def test_write_content_matches_to_string(self, builder):
        """Test that written content matches to_string output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.nfo"
            builder.write(str(filepath))
            file_content = filepath.read_text(encoding='utf-8')
            string_content = builder.to_string()
            assert file_content == string_content


class TestComplexStructure:
    """Test building complex XML structures."""

    def test_nested_elements(self):
        """Test creating nested element structures."""
        builder = NFOBuilder("movie")
        ratings = builder.add_element("ratings")
        rating = builder.add_element("rating", parent=ratings, name="imdb")
        builder.add_element("value", "8.5", parent=rating)
        builder.add_element("votes", "100000", parent=rating)

        xml = builder.to_string()
        assert "<ratings>" in xml
        assert "<rating" in xml
        assert "<value>8.5</value>" in xml

    def test_multiple_actor_elements(self):
        """Test creating multiple actor elements with nested structure."""
        builder = NFOBuilder("movie")

        # First actor
        actor1 = builder.add_element("actor")
        builder.add_element("name", "John Doe", parent=actor1)
        builder.add_element("role", "Hero", parent=actor1)

        # Second actor
        actor2 = builder.add_element("actor")
        builder.add_element("name", "Jane Smith", parent=actor2)
        builder.add_element("role", "Villain", parent=actor2)

        xml = builder.to_string()
        assert xml.count("<actor>") == 2
        assert "John Doe" in xml
        assert "Jane Smith" in xml
