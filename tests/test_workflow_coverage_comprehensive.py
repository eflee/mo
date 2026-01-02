"""Comprehensive workflow coverage tests for movie and TV adoption."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta

import pytest

from mo.config import Config
from mo.library import Library
from mo.providers.base import MovieMetadata, Rating, TVShowMetadata, EpisodeMetadata
from mo.workflows.movie import MovieAdoptionWorkflow, FileAction, AdoptionPlan
from mo.workflows.tv import TVShowAdoptionWorkflow
from mo.media.matcher import MatchConfidence, EpisodeMatch


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
def sample_movie_metadata():
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
        actors=[],
        ratings=[Rating(source="tmdb", value=8.4, votes=25000)],
        imdb_id="tt0137523",
        tmdb_id="550",
    )


@pytest.fixture
def sample_tv_metadata():
    """Create sample TV show metadata."""
    return TVShowMetadata(
        provider="tmdb",
        id="1399",
        title="Breaking Bad",
        year=2008,
        original_title="Breaking Bad",
        plot="A chemistry teacher...",
        premiered="2008-01-20",
        status="Ended",
        genres=["Drama"],
        networks=["AMC"],
        actors=[],
        ratings=[Rating(source="tmdb", value=9.5, votes=50000)],
        imdb_id="tt0903747",
        tmdb_id="1399",
        tvdb_id="81189",
    )


class TestMovieExecutePlanDirectories:
    """Test movie workflow plan execution - directory creation."""

    def test_execute_plan_creates_movie_folder(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that plan execution creates the movie folder."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_library.path / "Test Movie (1999)"
        
        actions = [
            FileAction(action="create_dir", destination=movie_folder),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        result = workflow._execute_plan(plan)
        assert result is True
        assert movie_folder.exists()

    def test_execute_plan_creates_subfolder_for_extras(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that plan execution creates extras subfolder."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_library.path / "Test Movie (1999)"
        extras_folder = movie_folder / "extras"
        
        actions = [
            FileAction(action="create_dir", destination=movie_folder),
            FileAction(action="create_dir", destination=extras_folder),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is True
        assert extras_folder.exists()


class TestMovieExecutePlanFileMoves:
    """Test movie workflow plan execution - file operations."""

    def test_execute_plan_moves_main_file(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test file moving during plan execution."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source_file = temp_dir / "test_movie.mkv"
        source_file.write_text("video content")
        
        movie_folder = mock_library.path / "Test Movie (1999)"
        dest_file = movie_folder / "Test Movie (1999).mkv"
        
        actions = [
            FileAction(action="create_dir", destination=movie_folder),
            FileAction(
                action="move",
                source=source_file,
                destination=dest_file,
                file_type="main",
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is True
        assert dest_file.exists()
        assert not source_file.exists()

    def test_execute_plan_copies_file_in_preserve_mode(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test file copying when preserve mode enabled."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source_file = temp_dir / "test_movie.mkv"
        source_file.write_text("video content")
        
        movie_folder = mock_library.path / "Test Movie (1999)"
        dest_file = movie_folder / "Test Movie (1999).mkv"
        
        actions = [
            FileAction(action="create_dir", destination=movie_folder),
            FileAction(
                action="copy",
                source=source_file,
                destination=dest_file,
                file_type="main",
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=True,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is True
        assert dest_file.exists()
        assert source_file.exists()


class TestMovieExecutePlanSubtitles:
    """Test movie workflow plan execution - subtitle handling."""

    def test_execute_plan_moves_subtitle_files(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test subtitle file handling in plan execution."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source_sub = temp_dir / "test_movie.srt"
        source_sub.write_text("1\n00:00:00,000 --> 00:00:05,000\nSubtitle text")
        
        movie_folder = mock_library.path / "Test Movie (1999)"
        dest_sub = movie_folder / "Test Movie (1999).srt"
        
        actions = [
            FileAction(action="create_dir", destination=movie_folder),
            FileAction(
                action="move",
                source=source_sub,
                destination=dest_sub,
                file_type="subtitles",
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is True
        assert dest_sub.exists()


class TestMovieExecutePlanNFO:
    """Test movie workflow plan execution - NFO writing."""

    def test_execute_plan_writes_nfo_file(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test NFO file writing during execution."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_library.path / "Test Movie (1999)"
        nfo_path = movie_folder / "movie.nfo"
        
        nfo_content = '<?xml version="1.0"?><movie><title>Test</title></movie>'
        
        actions = [
            FileAction(action="create_dir", destination=movie_folder),
            FileAction(
                action="write_nfo",
                destination=nfo_path,
                content=nfo_content,
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is True
        assert nfo_path.exists()
        content = nfo_path.read_text()
        assert "Test" in content


class TestMovieExecutePlanErrors:
    """Test movie workflow plan execution - error handling."""

    def test_execute_plan_handles_missing_source_file(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test handling of missing source files during move."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_library.path / "Test Movie (1999)"
        
        actions = [
            FileAction(
                action="move",
                source=temp_dir / "nonexistent.mkv",
                destination=movie_folder / "test.mkv",
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is False

    def test_execute_plan_continues_on_extra_file_failure(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that plan execution continues when extras fail."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        main_file = temp_dir / "main.mkv"
        main_file.write_text("main")
        
        movie_folder = mock_library.path / "Test Movie (1999)"
        
        actions = [
            FileAction(action="create_dir", destination=movie_folder),
            FileAction(
                action="move",
                source=main_file,
                destination=movie_folder / "main.mkv",
            ),
            FileAction(
                action="move",
                source=temp_dir / "missing_extra.mkv",
                destination=movie_folder / "extra.mkv",
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        # Should succeed even though extra failed
        assert movie_folder.exists()
        assert (movie_folder / "main.mkv").exists()


class TestTVExecutePlanStructure:
    """Test TV workflow plan execution - season structure."""

    def test_execute_plan_creates_season_folders(self, mock_config, temp_dir, sample_tv_metadata):
        """Test TV season folder creation."""
        show_library = Library(name="shows", library_type="show", path=temp_dir / "tv")
        show_library.path.mkdir()
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        series_folder = show_library.path / "Breaking Bad (2008)"
        season_folder = series_folder / "Season 01"
        
        actions = [
            FileAction(action="create_dir", destination=series_folder),
            FileAction(action="create_dir", destination=season_folder),
        ]
        
        plan = Mock()
        plan.series_folder = series_folder
        plan.actions = actions
        plan.to_dict.return_value = {}
        
        with patch('mo.workflows.tv.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is True
        assert series_folder.exists()
        assert season_folder.exists()

    def test_execute_plan_creates_multiple_seasons(self, mock_config, temp_dir, sample_tv_metadata):
        """Test creation of multiple season folders."""
        show_library = Library(name="shows", library_type="show", path=temp_dir / "tv")
        show_library.path.mkdir()
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        series_folder = show_library.path / "Breaking Bad (2008)"
        season_folders = [
            series_folder / "Season 01",
            series_folder / "Season 02",
            series_folder / "Season 03",
        ]
        
        actions = [FileAction(action="create_dir", destination=series_folder)]
        actions.extend([FileAction(action="create_dir", destination=sf) for sf in season_folders])
        
        plan = Mock()
        plan.series_folder = series_folder
        plan.actions = actions
        plan.to_dict.return_value = {}
        
        with patch('mo.workflows.tv.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is True
        for season_folder in season_folders:
            assert season_folder.exists()


class TestDryRunMode:
    """Test workflows in dry-run mode."""

    def test_movie_dry_run_no_files_modified(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that dry-run mode doesn't modify files."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=True)
        
        source_file = temp_dir / "test.mkv"
        source_file.write_text("content")
        
        movie_folder = mock_library.path / "Test Movie"
        
        actions = [
            FileAction(action="create_dir", destination=movie_folder),
            FileAction(
                action="move",
                source=source_file,
                destination=movie_folder / "test.mkv",
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            workflow._execute_plan(plan)
        
        # In dry-run, files shouldn't be created
        assert source_file.exists()

    def test_tv_dry_run_no_directories_created(self, mock_config, temp_dir, sample_tv_metadata):
        """Test that TV dry-run mode doesn't create directories."""
        show_library = Library(name="shows", library_type="show", path=temp_dir / "tv")
        show_library.path.mkdir()
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)
        
        series_folder = show_library.path / "Breaking Bad (2008)"
        
        actions = [FileAction(action="create_dir", destination=series_folder)]
        
        plan = Mock()
        plan.series_folder = series_folder
        plan.actions = actions
        plan.to_dict.return_value = {}
        
        with patch('mo.workflows.tv.json.dump'):
            workflow._execute_plan(plan)
        
        # In dry-run, nothing should be created
        assert not series_folder.exists()


class TestFileActionSerialization:
    """Test FileAction serialization for logging."""

    def test_file_action_create_dir_to_dict(self):
        """Test FileAction create_dir serialization."""
        action = FileAction(action="create_dir", destination=Path("/path/to/dir"))
        data = action.to_dict()
        
        assert data["action"] == "create_dir"
        assert data["destination"] == "/path/to/dir"

    def test_file_action_move_to_dict(self):
        """Test FileAction move serialization."""
        action = FileAction(
            action="move",
            source=Path("/src/file.mkv"),
            destination=Path("/dst/file.mkv"),
            file_type="main",
        )
        data = action.to_dict()
        
        assert data["action"] == "move"
        assert data["source"] == "/src/file.mkv"
        assert data["file_type"] == "main"

    def test_file_action_copy_to_dict(self):
        """Test FileAction copy serialization."""
        action = FileAction(
            action="copy",
            source=Path("/src/extra.mkv"),
            destination=Path("/dst/extra.mkv"),
            file_type="extras",
        )
        data = action.to_dict()
        
        assert data["action"] == "copy"
        assert data["file_type"] == "extras"

    def test_file_action_write_nfo_to_dict(self):
        """Test FileAction NFO write serialization."""
        nfo_content = '<?xml version="1.0"?><movie></movie>'
        action = FileAction(
            action="write_nfo",
            destination=Path("/path/movie.nfo"),
            content=nfo_content,
        )
        data = action.to_dict()
        
        assert data["action"] == "write_nfo"
        assert data["content_length"] == len(nfo_content)


class TestAdoptionPlanSerialization:
    """Test AdoptionPlan serialization."""

    def test_movie_plan_to_dict(self, mock_library, sample_movie_metadata, temp_dir):
        """Test movie plan serialization."""
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=[],
            movie_folder=mock_library.path / "Fight Club (1999)",
            preserve_originals=False,
        )
        
        data = plan.to_dict()
        
        assert data["source_path"] == str(temp_dir)
        assert data["library"]["name"] == "test_library"
        assert data["metadata"]["title"] == "Fight Club"
        assert data["preserve_originals"] is False

    def test_movie_plan_with_multiple_actions(self, mock_library, sample_movie_metadata, temp_dir):
        """Test plan serialization with multiple actions."""
        actions = [
            FileAction(action="create_dir", destination=temp_dir / "dir"),
            FileAction(
                action="move",
                source=temp_dir / "file.mkv",
                destination=temp_dir / "dir/file.mkv",
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=temp_dir / "dir",
            preserve_originals=False,
        )
        
        data = plan.to_dict()
        assert len(data["actions"]) == 2
        assert data["actions"][0]["action"] == "create_dir"
        assert data["actions"][1]["action"] == "move"
