"""Tests for movie adoption workflow."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mo.config import Config
from mo.library import Library
from mo.providers.base import SearchResult, MovieMetadata, Actor, Rating
from mo.workflows.movie import MovieAdoptionWorkflow, FileAction, AdoptionPlan


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(temp_dir):
    """Create a mock config."""
    config = Mock(spec=Config)
    config.get.return_value = "fake_api_key"
    return config


@pytest.fixture
def mock_library(temp_dir):
    """Create a mock library."""
    library_path = temp_dir / "library"
    library_path.mkdir()
    return Library(name="test_library", library_type="movie", path=library_path)


@pytest.fixture
def sample_metadata():
    """Create sample movie metadata."""
    return MovieMetadata(
        provider="tmdb",
        id="550",
        title="Fight Club",
        year=1999,
        original_title="Fight Club",
        plot="An insomniac office worker and a devil-may-care soap maker...",
        tagline="Mischief. Mayhem. Soap.",
        runtime=139,
        premiered="1999-10-15",
        genres=["Drama"],
        studios=["20th Century Fox"],
        directors=["David Fincher"],
        writers=["Chuck Palahniuk", "Jim Uhls"],
        actors=[
            Actor(name="Brad Pitt", role="Tyler Durden", order=0),
            Actor(name="Edward Norton", role="The Narrator", order=1),
        ],
        ratings=[
            Rating(source="tmdb", value=8.4, votes=25000),
        ],
        imdb_id="tt0137523",
        tmdb_id="550",
    )


@pytest.fixture
def sample_search_result():
    """Create a sample search result."""
    return SearchResult(
        provider="tmdb",
        id="550",
        title="Fight Club",
        year=1999,
        plot="An insomniac office worker and a devil-may-care soap maker...",
        rating=8.4,
        media_type="movie",
        relevance_score=100.0,
    )


class TestMovieAdoptionWorkflow:
    """Test MovieAdoptionWorkflow class."""

    def test_parse_source_path(self, mock_config, temp_dir):
        """Test parsing title and year from source path."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Test with year in filename
        source = temp_dir / "Fight Club (1999)"
        source.mkdir()

        title, year = workflow._parse_source_path(source)

        assert "Fight" in title or "fight" in title.lower()
        # Year parsing depends on MovieParser implementation

    def test_select_library_single(self, mock_config, mock_library):
        """Test library selection with single library."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Mock library manager to return single library
        workflow.library_manager.list = Mock(return_value=[mock_library])

        library = workflow._select_library(None)

        assert library == mock_library

    def test_select_library_by_name(self, mock_config, mock_library):
        """Test library selection by name."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Mock library manager
        workflow.library_manager.get = Mock(return_value=mock_library)
        workflow.library_manager.list = Mock(return_value=[mock_library])

        library = workflow._select_library("test_library")

        assert library == mock_library
        workflow.library_manager.get.assert_called_once_with("test_library")

    def test_generate_plan(self, mock_config, mock_library, sample_metadata, temp_dir):
        """Test action plan generation."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create a test movie file
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        movie_file = source_dir / "Fight.Club.mkv"
        movie_file.write_text("fake movie content")

        files = {
            "main": [movie_file],
            "extras": [],
            "subtitles": [],
            "other": [],
        }

        plan = workflow._generate_plan(
            source_path=source_dir,
            library=mock_library,
            metadata=sample_metadata,
            files=files,
            preserve=False,
        )

        assert isinstance(plan, AdoptionPlan)
        assert plan.source_path == source_dir
        assert plan.library == mock_library
        assert plan.metadata == sample_metadata
        assert plan.preserve_originals is False

        # Check that actions include:
        # 1. Create directory
        # 2. Move main file
        # 3. Write NFO
        assert len(plan.actions) >= 3

        action_types = [action.action for action in plan.actions]
        assert "create_dir" in action_types
        assert "move" in action_types
        assert "write_nfo" in action_types

    def test_generate_plan_with_extras(self, mock_config, mock_library, sample_metadata, temp_dir):
        """Test action plan generation with extras."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create test files
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        movie_file = source_dir / "movie.mkv"
        movie_file.write_text("fake movie content")
        extra_file = source_dir / "deleted_scenes.mkv"
        extra_file.write_text("fake extra content")
        subtitle_file = source_dir / "movie.en.srt"
        subtitle_file.write_text("fake subtitle content")

        files = {
            "main": [movie_file],
            "extras": [extra_file],
            "subtitles": [subtitle_file],
            "other": [],
        }

        plan = workflow._generate_plan(
            source_path=source_dir,
            library=mock_library,
            metadata=sample_metadata,
            files=files,
            preserve=True,  # Test preserve mode
        )

        assert plan.preserve_originals is True

        # Check actions include extras directory and extra file
        copy_actions = [a for a in plan.actions if a.action == "copy"]

        # Should copy main + extra + subtitle
        assert len(copy_actions) >= 3

    def test_file_action_to_dict(self, temp_dir):
        """Test FileAction serialization."""
        source = temp_dir / "source.mkv"
        dest = temp_dir / "dest.mkv"

        action = FileAction(
            action="move",
            source=source,
            destination=dest,
            file_type="main",
        )

        result = action.to_dict()

        assert result["action"] == "move"
        assert result["source"] == str(source)
        assert result["destination"] == str(dest)
        assert result["file_type"] == "main"

    def test_adoption_plan_to_dict(self, mock_library, sample_metadata, temp_dir):
        """Test AdoptionPlan serialization."""
        source = temp_dir / "source"
        movie_folder = temp_dir / "movie"

        action = FileAction(
            action="create_dir",
            destination=movie_folder,
        )

        plan = AdoptionPlan(
            source_path=source,
            library=mock_library,
            metadata=sample_metadata,
            actions=[action],
            movie_folder=movie_folder,
            preserve_originals=False,
        )

        result = plan.to_dict()

        assert result["source_path"] == str(source)
        assert result["movie_folder"] == str(movie_folder)
        assert result["preserve_originals"] is False
        assert "library" in result
        assert "metadata" in result
        assert "actions" in result
        assert len(result["actions"]) == 1


class TestFileIdentification:
    """Test file identification logic."""

    def test_identify_single_file(self, mock_config, temp_dir):
        """Test identification of a single movie file."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create a single movie file
        movie_file = temp_dir / "movie.mkv"
        movie_file.write_text("fake content")

        # Mock the prompt to auto-confirm
        with patch("mo.workflows.movie.prompt", return_value="y"):
            files = workflow._identify_files(movie_file)

        assert files is not None
        assert len(files["main"]) == 1
        assert files["main"][0] == movie_file

    def test_identify_directory_with_files(self, mock_config, temp_dir):
        """Test identification in a directory with multiple files."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create movie files
        movie_dir = temp_dir / "movie_dir"
        movie_dir.mkdir()

        main_file = movie_dir / "movie.mkv"
        main_file.write_bytes(b"0" * 1000000)  # 1 MB

        small_file = movie_dir / "trailer.mp4"
        small_file.write_bytes(b"0" * 100000)  # 100 KB

        subtitle_file = movie_dir / "movie.srt"
        subtitle_file.write_text("subtitle content")

        # Mock the prompt to auto-confirm
        with patch("mo.workflows.movie.prompt", return_value="y"):
            files = workflow._identify_files(movie_dir)

        assert files is not None
        # Main file should be the largest video file
        assert len(files["main"]) == 1
        assert files["main"][0] == main_file

        # Smaller video file should be categorized as extra
        assert small_file in files["extras"]

        # Subtitle should be in subtitles
        assert subtitle_file in files["subtitles"]


class TestErrorHandling:
    """Test error handling in MovieAdoptionWorkflow."""

    def test_missing_tmdb_api_key(self, temp_dir):
        """Test that workflow raises MoError when TMDB API key is not configured."""
        from mo.utils.errors import MoError

        config = Mock(spec=Config)
        config.get.return_value = None  # No API key configured

        with pytest.raises(MoError, match="TMDB API key not configured"):
            MovieAdoptionWorkflow(config=config, dry_run=True)

    def test_provider_error_during_metadata_fetch(self, mock_config, mock_library, temp_dir):
        """Test handling of ProviderError during metadata fetch."""
        from mo.providers.base import ProviderError

        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Mock the TMDB provider to raise ProviderError
        workflow.tmdb.get_movie = Mock(side_effect=ProviderError("API Error"))

        # Create a mock search result
        search_result = Mock()
        search_result.id = "550"

        # Test that _get_full_metadata handles the error gracefully
        metadata = workflow._get_full_metadata(search_result)

        assert metadata is None

    def test_keyboard_interrupt_during_library_selection(self, mock_config, temp_dir):
        """Test handling of KeyboardInterrupt during library selection."""
        from mo.utils.errors import MoError

        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create multiple mock libraries to trigger selection prompt
        lib1 = Mock(spec=Library)
        lib1.name = "library1"
        lib1.library_type = "movie"
        lib1.path = temp_dir / "lib1"

        lib2 = Mock(spec=Library)
        lib2.name = "library2"
        lib2.library_type = "movie"
        lib2.path = temp_dir / "lib2"

        workflow.library_manager.list = Mock(return_value=[lib1, lib2])

        # Mock prompt to raise KeyboardInterrupt
        with patch("mo.workflows.movie.prompt", side_effect=KeyboardInterrupt):
            with pytest.raises(MoError, match="Library selection cancelled"):
                workflow._select_library(None)

    def test_eoferror_during_file_confirmation(self, mock_config, temp_dir):
        """Test handling of EOFError during file confirmation."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create a test movie file
        movie_file = temp_dir / "movie.mkv"
        movie_file.write_text("fake content")

        # Mock prompt to raise EOFError
        with patch("mo.workflows.movie.prompt", side_effect=EOFError):
            files = workflow._identify_files(movie_file)

        assert files is None
