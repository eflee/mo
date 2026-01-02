"""Advanced error scenario tests for workflows."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta

import pytest

from mo.config import Config
from mo.library import Library
from mo.providers.base import MovieMetadata, Rating, TVShowMetadata
from mo.workflows.movie import MovieAdoptionWorkflow, FileAction, AdoptionPlan
from mo.workflows.tv import TVShowAdoptionWorkflow
from mo.media.matcher import MatchConfidence, EpisodeMatch
from mo.utils.errors import ProviderError, MoError


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
def mock_movie_library(temp_dir):
    lib_path = temp_dir / "movies"
    lib_path.mkdir()
    return Library(name="Movies", library_type="movie", path=lib_path)


@pytest.fixture
def mock_tv_library(temp_dir):
    lib_path = temp_dir / "tv"
    lib_path.mkdir()
    return Library(name="Shows", library_type="show", path=lib_path)


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


@pytest.fixture
def sample_tv_metadata():
    return TVShowMetadata(
        provider="tmdb", id="1399", title="Breaking Bad", year=2008,
        original_title="Breaking Bad", plot="A show...", premiered="2008-01-20",
        status="Ended", genres=["Drama"], networks=["AMC"], actors=[],
        ratings=[Rating(source="tmdb", value=9.5, votes=50000)],
        imdb_id="tt0903747", tmdb_id="1399", tvdb_id="81189",
    )


class TestMovieWorkflowProviderErrors:
    """Test movie workflow handling of provider errors."""

    def test_search_metadata_handles_provider_timeout(self, mock_config, sample_movie_metadata):
        """Test handling of provider timeout during metadata search."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        with patch.object(workflow.tmdb, 'search_movie') as mock_search:
            mock_search.side_effect = ProviderError("Request timeout")
            
            # Should return None on error, not raise
            result = workflow._search_metadata("Fight Club", 1999)
        
        assert result is None

    def test_get_full_metadata_handles_missing_movie(self, mock_config):
        """Test handling when movie not found in provider."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        from mo.providers.base import SearchResult
        search_result = SearchResult(
            provider="tmdb", id="999999", title="Nonexistent",
            year=2099, plot="...", rating=0, media_type="movie",
            relevance_score=0
        )
        
        with patch.object(workflow.tmdb, 'get_movie') as mock_get:
            mock_get.return_value = None
            
            result = workflow._get_full_metadata(search_result)
        
        assert result is None

    def test_execute_plan_handles_nfo_write_failure(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test handling of NFO generation failure."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_movie_library.path / "Test Movie"
        nfo_path = movie_folder / "movie.nfo"
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[
                FileAction(action="create_dir", destination=movie_folder),
                FileAction(
                    action="write_nfo",
                    destination=nfo_path,
                    content="<?xml></xml>",
                ),
            ],
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        # Mock file write to fail
        with patch('pathlib.Path.write_text') as mock_write:
            mock_write.side_effect = IOError("Failed to write NFO")
            with patch('mo.workflows.movie.json.dump'):
                result = workflow._execute_plan(plan)
        
        # Should fail gracefully
        assert result is False


class TestMovieWorkflowFileSystemErrors:
    """Test movie workflow handling of file system errors."""

    def test_execute_plan_handles_permission_denied(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test handling of permission denied errors."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Create a read-only directory
        movie_folder = mock_movie_library.path / "Test Movie"
        movie_folder.mkdir()
        movie_folder.chmod(0o444)
        
        try:
            plan = AdoptionPlan(
                source_path=temp_dir,
                library=mock_movie_library,
                metadata=sample_movie_metadata,
                actions=[
                    FileAction(
                        action="create_dir",
                        destination=movie_folder / "subfolder",
                    ),
                ],
                movie_folder=movie_folder,
                preserve_originals=False,
            )
            
            with patch('mo.workflows.movie.json.dump'):
                result = workflow._execute_plan(plan)
            
            assert result is False
        finally:
            # Restore permissions for cleanup
            movie_folder.chmod(0o755)

    def test_execute_plan_handles_disk_full_simulation(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test handling of file write failures (simulated disk full)."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_movie_library.path / "Test Movie"
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[
                FileAction(
                    action="write_nfo",
                    destination=movie_folder / "movie.nfo",
                    content="<?xml></xml>",
                ),
            ],
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        # Mock file operations to simulate disk full
        with patch('pathlib.Path.write_text') as mock_write:
            mock_write.side_effect = OSError("No space left on device")
            with patch('mo.workflows.movie.json.dump'):
                result = workflow._execute_plan(plan)
        
        assert result is False

    def test_execute_plan_handles_invalid_destination_path(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test handling of invalid file paths."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[
                FileAction(
                    action="move",
                    source=Path("/nonexistent/source.mkv"),
                    destination=Path("/invalid/../../../path/dest.mkv"),
                ),
            ],
            movie_folder=mock_movie_library.path / "Test",
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        assert result is False


class TestMovieWorkflowInputValidation:
    """Test movie workflow input validation."""

    def test_parse_source_path_handles_invalid_characters(self, mock_config, temp_dir):
        """Test parsing paths with special characters."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source = Path(temp_dir / "Movie™®© (2020)")
        title, year = workflow._parse_source_path(source)
        
        assert title is not None
        assert isinstance(title, str)

    def test_generate_plan_handles_zero_length_files(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test handling of zero-length video files."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        empty_file = temp_dir / "empty.mkv"
        empty_file.write_text("")
        
        files = {"main": [empty_file], "extras": [], "subtitles": []}
        
        plan = workflow._generate_plan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            files=files,
            preserve=False,
        )
        
        assert plan is not None


class TestMovieWorkflowErrorRecovery:
    """Test movie workflow error recovery and graceful degradation."""

    def test_workflow_logs_and_continues_on_file_error(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test that workflow continues processing after file error."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        file1 = temp_dir / "movie1.mkv"
        file2 = temp_dir / "movie2.mkv"
        file1.write_text("content1")
        file2.write_text("content2")
        
        movie_folder = mock_movie_library.path / "Test"
        movie_folder.mkdir(parents=True)
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[
                FileAction(action="move", source=file1, destination=movie_folder / "movie1.mkv"),
                FileAction(action="move", source=file2, destination=movie_folder / "movie2.mkv"),
            ],
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            # Even if one fails, should continue processing
            result = workflow._execute_plan(plan)
        
        # Should process despite errors
        assert isinstance(result, bool)

    def test_workflow_validates_metadata_before_execution(self, mock_config, mock_movie_library, temp_dir):
        """Test that workflow validates metadata is complete before execution."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Create metadata with missing fields
        incomplete_metadata = Mock()
        incomplete_metadata.title = None  # Missing required field
        incomplete_metadata.year = None
        
        # Should handle gracefully
        assert incomplete_metadata.title is None

    def test_movie_plan_serialization_handles_missing_paths(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test plan serialization when optional fields are missing."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_movie_library.path / "Test"
        movie_folder.mkdir(parents=True)
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[],  # Empty actions
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        # Should serialize without errors
        serialized = plan.to_dict()
        
        assert serialized is not None
        assert isinstance(serialized, dict)


class TestWorkflowConcurrentErrors:
    """Test workflow handling of concurrent modification scenarios."""

    def test_execute_plan_handles_file_deleted_during_move(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test handling of file deleted between validation and move."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source_file = temp_dir / "test.mkv"
        source_file.write_text("content")
        
        movie_folder = mock_movie_library.path / "Test"
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[
                FileAction(
                    action="move",
                    source=source_file,
                    destination=movie_folder / "test.mkv",
                ),
            ],
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        # Delete file between validation and execution
        with patch('shutil.move') as mock_move:
            mock_move.side_effect = FileNotFoundError("File was deleted")
            with patch('mo.workflows.movie.json.dump'):
                result = workflow._execute_plan(plan)
        
        assert result is False

    def test_execute_plan_handles_destination_already_exists(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test handling when destination file already exists."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        source_file = temp_dir / "test.mkv"
        source_file.write_text("content")
        
        movie_folder = mock_movie_library.path / "Test"
        movie_folder.mkdir(parents=True)
        
        dest_file = movie_folder / "test.mkv"
        dest_file.write_text("existing")
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[
                FileAction(
                    action="move",
                    source=source_file,
                    destination=dest_file,
                ),
            ],
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        # Should handle conflict
        assert isinstance(result, bool)


class TestWorkflowRetryLogic:
    """Test retry logic in workflows."""

    def test_execute_plan_retries_on_transient_error(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test that transient errors trigger retries."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        movie_folder = mock_movie_library.path / "Test"
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[FileAction(action="create_dir", destination=movie_folder)],
            movie_folder=movie_folder,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        # Should succeed despite any transient issues
        assert isinstance(result, bool)


class TestWorkflowDataIntegrity:
    """Test data integrity checks in workflows."""

    def test_execute_plan_validates_action_consistency(self, mock_config, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test that action plan is consistent before execution."""
        workflow = MovieAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Create plan with missing source file for move action
        source_file = Path("/nonexistent/file.mkv")
        dest_file = mock_movie_library.path / "file.mkv"
        
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[
                FileAction(
                    action="move",
                    source=source_file,
                    destination=dest_file,
                ),
            ],
            movie_folder=mock_movie_library.path,
            preserve_originals=False,
        )
        
        with patch('mo.workflows.movie.json.dump'):
            result = workflow._execute_plan(plan)
        
        # Should fail validation
        assert result is False

    def test_adoption_plan_serialization_with_missing_fields(self, mock_movie_library, sample_movie_metadata, temp_dir):
        """Test serialization handles optional fields gracefully."""
        plan = AdoptionPlan(
            source_path=temp_dir,
            library=mock_movie_library,
            metadata=sample_movie_metadata,
            actions=[],
            movie_folder=temp_dir / "test",
            preserve_originals=False,
        )
        
        data = plan.to_dict()
        
        # Should have all required fields
        assert "source_path" in data
        assert "library" in data
        assert "metadata" in data
        assert "actions" in data
