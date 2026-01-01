"""Tests for library management."""

import configparser
from pathlib import Path

import pytest

from mo.config import Config
from mo.library import Library, LibraryManager
from mo.utils.errors import ValidationError


@pytest.fixture
def config_file(tmp_path):
    """Create a basic config file."""
    config_path = tmp_path / ".mo.conf"
    config = configparser.ConfigParser()

    config["metadata"] = {
        "tmdb_api_key": "test_key",
    }

    with open(config_path, "w") as f:
        config.write(f)

    return config_path


@pytest.fixture
def config(config_file):
    """Create a Config instance."""
    return Config(local_path=config_file)


@pytest.fixture
def library_manager(config):
    """Create a LibraryManager instance."""
    return LibraryManager(config)


@pytest.fixture
def media_dir(tmp_path):
    """Create a media directory."""
    media = tmp_path / "media"
    media.mkdir()
    return media


class TestLibrary:
    """Test Library dataclass."""

    def test_create_library(self):
        """Test creating a library."""
        lib = Library(name="movies", library_type="movie", path=Path("/media/Movies"))
        assert lib.name == "movies"
        assert lib.library_type == "movie"
        assert lib.path == Path("/media/Movies")

    def test_invalid_library_type_raises_error(self):
        """Test error for invalid library type."""
        with pytest.raises(ValidationError, match="Invalid library type"):
            Library(name="test", library_type="invalid", path=Path("/media"))

    def test_path_conversion(self):
        """Test that string paths are converted to Path."""
        lib = Library(name="movies", library_type="movie", path="/media/Movies")
        assert isinstance(lib.path, Path)


class TestLibraryManagerAdd:
    """Test adding libraries."""

    def test_add_library(self, library_manager, media_dir):
        """Test adding a valid library."""
        lib = library_manager.add("movies", "movie", media_dir, save=False)

        assert lib.name == "movies"
        assert lib.library_type == "movie"
        assert lib.path == media_dir

    def test_add_library_saves_to_config(self, library_manager, media_dir, config):
        """Test that adding library saves to config."""
        library_manager.add("movies", "movie", media_dir)

        libraries = config.get_libraries()
        types = config.get_library_types()

        assert "movies" in libraries
        assert libraries["movies"] == str(media_dir)
        assert types["movies"] == "movie"

    def test_add_duplicate_library_raises_error(self, library_manager, media_dir):
        """Test error when adding duplicate library."""
        library_manager.add("movies", "movie", media_dir, save=False)

        with pytest.raises(ValidationError, match="already exists"):
            library_manager.add("movies", "show", media_dir, save=False)

    def test_add_library_with_nonexistent_path_raises_error(
        self, library_manager, tmp_path
    ):
        """Test error for nonexistent path."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ValidationError, match="does not exist"):
            library_manager.add("movies", "movie", nonexistent, save=False)

    def test_add_library_with_file_path_raises_error(self, library_manager, tmp_path):
        """Test error when path is a file."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(ValidationError, match="must be a directory"):
            library_manager.add("movies", "movie", file_path, save=False)

    def test_add_library_with_invalid_type_raises_error(
        self, library_manager, media_dir
    ):
        """Test error for invalid library type."""
        with pytest.raises(ValidationError, match="Invalid library type"):
            library_manager.add("movies", "invalid", media_dir, save=False)

    def test_add_multiple_libraries(self, library_manager, tmp_path):
        """Test adding multiple libraries."""
        movies_dir = tmp_path / "movies"
        tv_dir = tmp_path / "tv"
        movies_dir.mkdir()
        tv_dir.mkdir()

        library_manager.add("movies", "movie", movies_dir, save=False)
        library_manager.add("tv", "show", tv_dir, save=False)

        libraries = library_manager.list()
        assert len(libraries) == 2


class TestLibraryManagerRemove:
    """Test removing libraries."""

    def test_remove_library(self, library_manager, media_dir):
        """Test removing a library."""
        library_manager.add("movies", "movie", media_dir, save=False)
        library_manager.remove("movies", save=False)

        with pytest.raises(ValidationError, match="does not exist"):
            library_manager.get("movies")

    def test_remove_nonexistent_library_raises_error(self, library_manager):
        """Test error when removing nonexistent library."""
        with pytest.raises(ValidationError, match="does not exist"):
            library_manager.remove("nonexistent", save=False)

    def test_remove_library_saves_to_config(self, library_manager, media_dir, config):
        """Test that removing library saves to config."""
        library_manager.add("movies", "movie", media_dir)
        library_manager.remove("movies")

        libraries = config.get_libraries()
        assert "movies" not in libraries


class TestLibraryManagerGet:
    """Test getting libraries."""

    def test_get_library(self, library_manager, media_dir):
        """Test getting a library by name."""
        library_manager.add("movies", "movie", media_dir, save=False)
        lib = library_manager.get("movies")

        assert lib.name == "movies"
        assert lib.library_type == "movie"
        assert lib.path == media_dir

    def test_get_nonexistent_library_raises_error(self, library_manager):
        """Test error when getting nonexistent library."""
        with pytest.raises(ValidationError, match="does not exist"):
            library_manager.get("nonexistent")

    def test_get_library_with_missing_type_raises_error(
        self, library_manager, media_dir, config
    ):
        """Test error when library is missing type configuration."""
        # Manually add library without type
        config.set("libraries", "broken", str(media_dir))

        with pytest.raises(ValidationError, match="missing type configuration"):
            library_manager.get("broken")


class TestLibraryManagerList:
    """Test listing libraries."""

    def test_list_empty(self, library_manager):
        """Test listing when no libraries exist."""
        libraries = library_manager.list()
        assert libraries == []

    def test_list_libraries(self, library_manager, tmp_path):
        """Test listing libraries."""
        movies_dir = tmp_path / "movies"
        tv_dir = tmp_path / "tv"
        movies_dir.mkdir()
        tv_dir.mkdir()

        library_manager.add("movies", "movie", movies_dir, save=False)
        library_manager.add("tv", "show", tv_dir, save=False)

        libraries = library_manager.list()
        assert len(libraries) == 2

        names = {lib.name for lib in libraries}
        assert names == {"movies", "tv"}

    def test_list_skips_libraries_with_missing_type(
        self, library_manager, media_dir, config
    ):
        """Test that list skips libraries with missing type."""
        library_manager.add("movies", "movie", media_dir, save=False)

        # Add broken library without type
        config.set("libraries", "broken", str(media_dir))

        libraries = library_manager.list()
        assert len(libraries) == 1
        assert libraries[0].name == "movies"


class TestLibraryManagerInfo:
    """Test getting library info."""

    def test_get_library_info(self, library_manager, media_dir):
        """Test getting library information."""
        library_manager.add("movies", "movie", media_dir, save=False)
        info = library_manager.get_library_info("movies")

        assert info["Name"] == "movies"
        assert info["Type"] == "movie"
        assert info["Path"] == str(media_dir)
        assert info["Exists"] == "Yes"

    def test_get_library_info_counts_items(self, library_manager, tmp_path):
        """Test that info includes item count."""
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        # Create some subdirectories
        (media_dir / "Movie 1").mkdir()
        (media_dir / "Movie 2").mkdir()
        (media_dir / "Movie 3").mkdir()

        library_manager.add("movies", "movie", media_dir, save=False)
        info = library_manager.get_library_info("movies")

        assert info["Items"] == "3"

    def test_get_library_info_nonexistent_path(self, library_manager, tmp_path):
        """Test info for library with nonexistent path."""
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        library_manager.add("movies", "movie", media_dir, save=False)

        # Remove the directory
        media_dir.rmdir()

        info = library_manager.get_library_info("movies")
        assert info["Exists"] == "No"
        assert "Items" not in info

    def test_get_library_info_permission_denied(
        self, library_manager, tmp_path, monkeypatch
    ):
        """Test info when permission denied."""
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        library_manager.add("movies", "movie", media_dir, save=False)

        # Mock iterdir to raise PermissionError
        def mock_iterdir(self):
            raise PermissionError("Access denied")

        monkeypatch.setattr(Path, "iterdir", mock_iterdir)

        info = library_manager.get_library_info("movies")
        assert info["Items"] == "Permission denied"
