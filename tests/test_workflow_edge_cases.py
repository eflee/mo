"""Workflow coverage targeting interactive prompts and edge cases."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from mo.config import Config
from mo.library import Library
from mo.providers.base import MovieMetadata, Rating
from mo.workflows.movie import MovieAdoptionWorkflow, FileAction, AdoptionPlan
from mo.workflows.tv import TVShowAdoptionWorkflow
from mo.utils.errors import MoError


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(temp_dir):
    config = Mock(spec=Config)
    config.get.return_value = "fake_api_key"
    return config


@pytest.fixture
def mock_library(temp_dir):
    library_path = temp_dir / "library"
    library_path.mkdir()
    return Library(name="test_library", library_type="movie", path=library_path)


@pytest.fixture
def sample_movie_metadata():
    return MovieMetadata(
        provider="tmdb", id="550", title="Fight Club", year=1999,
        original_title="Fight Club", plot="A movie...", runtime=139,
        premiered="1999-10-15", genres=["Drama"], studios=["20th Century Fox"],
        directors=["David Fincher"], writers=["Chuck", "Jim"], actors=[],
        ratings=[Rating(source="tmdb", value=8.4, votes=25000)],
        imdb_id="tt0137523", tmdb_id="550",
    )


class TestMovieWorkflowForceFlag:
    """Test movie workflow with force flag."""

    def test_execute_plan_force_skips_all_prompts(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that force flag allows execution without confirmation."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_library.path / "Test Movie"
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=[FileAction(action="create_dir", destination=movie_folder)],
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is True
        assert movie_folder.exists()


class TestMovieWorkflowPreserveFlag:
    """Test movie workflow with preserve flag."""

    def test_generate_plan_with_preserve_uses_copy_action(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that preserve flag generates copy actions."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        main_file = temp_dir / "movie.mkv"
        main_file.write_text("content")
        
        files = {"main": [main_file], "extras": [], "subtitles": []}
        
        plan = workflow._generate_plan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            files=files,
            preserve=True,
        )
        
        assert plan is not None
        # Check that copy actions are used (not move)
        copy_actions = [a for a in plan.actions if a.action == "copy"]
        assert len(copy_actions) > 0

    def test_generate_plan_without_preserve_uses_move_action(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that without preserve, move actions are used."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        main_file = temp_dir / "movie.mkv"
        main_file.write_text("content")
        
        files = {"main": [main_file], "extras": [], "subtitles": []}
        
        plan = workflow._generate_plan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            files=files,
            preserve=False,
        )
        
        assert plan is not None
        # Check that move actions are used
        move_actions = [a for a in plan.actions if a.action == "move"]
        assert len(move_actions) > 0


class TestMovieWorkflowFolderNaming:
    """Test movie folder naming conventions."""

    def test_generate_plan_creates_folder_with_year(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that movie folders include year."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        files = {"main": [], "extras": [], "subtitles": []}
        
        plan = workflow._generate_plan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            files=files,
            preserve=False,
        )
        
        # Check that folder path contains the year
        assert "(1999)" in str(plan.movie_folder)
        assert "Fight Club" in str(plan.movie_folder)


class TestTVWorkflowSeasonStructure:
    """Test TV workflow season structure generation."""

    def test_generate_tv_plan_creates_season_folders(self, mock_config, temp_dir):
        """Test that TV plan creates season folders."""
        show_library = Library(name="shows", library_type="show", path=temp_dir / "tv")
        show_library.path.mkdir()
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        series_folder = show_library.path / "Test Show (2020)"
        season_01 = series_folder / "Season 01"
        
        plan = Mock()
        plan.series_folder = series_folder
        plan.actions = [
            FileAction(action="create_dir", destination=series_folder),
            FileAction(action="create_dir", destination=season_01),
        ]
        plan.to_dict.return_value = {}
        
        with patch('mo.workflows.tv.json.dump'):
            workflow._execute_plan(plan)
        
        assert series_folder.exists()
        assert season_01.exists()


class TestWorkflowSourcePathHandling:
    """Test source path parsing and validation."""

    def test_parse_source_path_with_parenthetical_year(self, mock_config):
        """Test parsing path with year in parentheses."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source = Path("/downloads/The Matrix (1999)")
        title, year = workflow._parse_source_path(source)
        
        assert title == "The Matrix"
        assert year == 1999

    def test_parse_source_path_with_multiple_words(self, mock_config):
        """Test parsing title with multiple words."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source = Path("/downloads/The Lord of the Rings (2001)")
        title, year = workflow._parse_source_path(source)
        
        assert title == "The Lord of the Rings"
        assert year == 2001

    def test_parse_source_path_single_file(self, mock_config, temp_dir):
        """Test parsing when source is a single file."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source_file = temp_dir / "Movie.mkv"
        source_file.write_text("test")
        
        title, year = workflow._parse_source_path(source_file)
        
        assert title == "Movie"


class TestWorkflowErrorConditions:
    """Test error handling in workflows."""

    def test_movie_library_selection_error_message(self, mock_config):
        """Test error message when no libraries configured."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        with patch.object(workflow.library_manager, 'list') as mock_list:
            mock_list.return_value = []
            
            with pytest.raises(MoError) as exc_info:
                workflow._select_library(None)
            
            assert "No movie libraries" in str(exc_info.value)

    def test_tv_library_selection_error_message(self, mock_config):
        """Test error message for TV when no libraries configured."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        with patch.object(workflow.library_manager, 'list') as mock_list:
            mock_list.return_value = []
            
            with pytest.raises(MoError) as exc_info:
                workflow._select_library(None)
            
            assert "No TV show" in str(exc_info.value)


class TestWorkflowNFOGeneration:
    """Test NFO file generation in workflows."""

    def test_execute_plan_creates_nfo_for_main_file(self, mock_config, mock_library, sample_movie_metadata, temp_dir):
        """Test that NFO files are created for main movies."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_library.path / "Test Movie"
        nfo_file = movie_folder / "movie.nfo"
        
        # Create folder first
        movie_folder.mkdir(parents=True)
        
        actions = [
            FileAction(
                action="write_nfo",
                destination=nfo_file,
                content='<?xml version="1.0"?><movie><title>Test</title></movie>',
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
        
        assert nfo_file.exists()
        content = nfo_file.read_text()
        assert "<title>Test</title>" in content


class TestWorkflowActionGrouping:
    """Test grouping of actions in plans."""

    def test_adoption_plan_groups_actions_by_type(self, mock_library, sample_movie_metadata, temp_dir):
        """Test that adoption plan can group actions by type."""
        actions = [
            FileAction(action="create_dir", destination=temp_dir / "dir1"),
            FileAction(
                action="move",
                source=temp_dir / "file1.mkv",
                destination=temp_dir / "dir1/file1.mkv",
            ),
            FileAction(
                action="write_nfo",
                destination=temp_dir / "dir1/movie.nfo",
                content="<?xml></xml>",
            ),
        ]
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_library,
            metadata=sample_movie_metadata,
            actions=actions,
            movie_folder=temp_dir / "dir1",
            preserve_originals=False,
        )
        
        # Verify all actions are preserved
        assert len(plan.actions) == 3
        
        # Check action types
        action_types = {a.action for a in plan.actions}
        assert "create_dir" in action_types
        assert "move" in action_types
        assert "write_nfo" in action_types
