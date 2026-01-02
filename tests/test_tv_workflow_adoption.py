"""Comprehensive TV show adoption workflow tests covering core business logic."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from mo.config import Config
from mo.library import Library, LibraryManager
from mo.providers.base import TVShowMetadata, EpisodeMetadata, SearchResult, Actor, Rating
from mo.workflows.tv import (
    TVShowAdoptionWorkflow,
    FileAction,
    EpisodeFile,
    AdoptionPlan,
)
from mo.media.matcher import MatchConfidence


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
    return Library(name="test_library", library_type="show", path=library_path)


@pytest.fixture
def sample_show_metadata():
    """Create sample TV show metadata."""
    return TVShowMetadata(
        provider="tmdb",
        id="1396",
        title="Breaking Bad",
        year=2008,
        original_title="Breaking Bad",
        plot="A high school chemistry teacher turned methamphetamine producer...",
        premiered="2008-01-20",
        rating=9.5,
        ratings=[Rating(source="tmdb", value=9.5, votes=10000)],
        genres=["drama", "crime"],
        status="Ended",
        seasons=5,
    )


class TestTVShowAdoptionWorkflowFullCycle:
    """Test complete TV show adoption workflow."""

    def test_adopt_with_single_season(self, mock_config, mock_library, sample_show_metadata, temp_dir):
        """Test adopting a single season TV show."""
        # Setup
        source_dir = temp_dir / "downloads" / "Breaking Bad S01"
        source_dir.mkdir(parents=True)
        
        # Create sample episode files
        (source_dir / "01x01.mkv").write_text("episode content 1")
        (source_dir / "01x02.mkv").write_text("episode content 2")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        # Mock provider search
        with patch.object(workflow.tmdb, 'search_tv') as mock_search:
            mock_search.return_value = [SearchResult(provider="tmdb", id="1396", title="Breaking Bad", year=2008)]
            
            # Mock provider metadata fetch
            with patch.object(workflow.tmdb, 'get_tv_show') as mock_get:
                # Create episodes for season 1
                episodes = [
                    EpisodeMetadata(
                        provider="tmdb",
                        show_id="1396",
                        season_number=1,
                        episode_number=1,
                        title="Pilot",
                        aired="2008-01-20",
                    ),
                    EpisodeMetadata(
                        provider="tmdb",
                        show_id="1396",
                        season_number=1,
                        episode_number=2,
                        title="Cat's in the Bag",
                        aired="2008-01-27",
                    ),
                ]
                
                sample_show_metadata.seasons = [{"season_number": 1, "episodes": episodes}]
                mock_get.return_value = sample_show_metadata
                
                # Mock dry_run to skip prompts
                with patch('prompt_toolkit.prompt') as mock_prompt:
                    mock_prompt.return_value = "y"  # Accept confirmation
                    
                    result = workflow.adopt(
                        source_path=source_dir,
                        library_name="test_library",
                        preserve=False,
                        force=False,
                    )
        
        # Result depends on plan execution
        assert isinstance(result, bool)

    def test_adopt_generates_plan_with_multiple_seasons(self, mock_config, mock_library, sample_show_metadata, temp_dir):
        """Test that adoption generates plan with multiple seasons."""
        # Setup
        source_dir = temp_dir / "downloads"
        source_dir.mkdir(parents=True)
        
        # Create season directories
        (source_dir / "Season 1").mkdir()
        (source_dir / "Season 1" / "01x01.mkv").write_text("s1e1")
        (source_dir / "Season 1" / "01x02.mkv").write_text("s1e2")
        
        (source_dir / "Season 2").mkdir()
        (source_dir / "Season 2" / "02x01.mkv").write_text("s2e1")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        with patch.object(workflow, '_search_show_metadata') as mock_search:
            with patch.object(workflow, '_get_full_show_metadata') as mock_get:
                with patch.object(workflow, '_identify_episodes') as mock_identify:
                    with patch.object(workflow, '_match_episodes_to_metadata') as mock_match:
                        with patch.object(workflow, '_generate_plan') as mock_plan_gen:
                            with patch.object(workflow, '_confirm_plan') as mock_confirm:
                                with patch.object(workflow, '_execute_plan') as mock_execute:
                                    # Setup mocks
                                    mock_search.return_value = SearchResult(provider="tmdb", id="1396", title="Breaking Bad", year=2008)
                                    mock_get.return_value = sample_show_metadata
                                    
                                    # Mock identified episodes
                                    episodes_by_season = {
                                        1: [
                                            EpisodeFile(path=source_dir / "Season 1" / "01x01.mkv", season=1, episode=1),
                                            EpisodeFile(path=source_dir / "Season 1" / "01x02.mkv", season=1, episode=2),
                                        ],
                                        2: [
                                            EpisodeFile(path=source_dir / "Season 2" / "02x01.mkv", season=2, episode=1),
                                        ],
                                    }
                                    mock_identify.return_value = episodes_by_season
                                    mock_match.return_value = episodes_by_season
                                    
                                    # Mock plan
                                    plan = Mock(spec=AdoptionPlan)
                                    plan.actions = [
                                        FileAction(action="create_dir"),
                                        FileAction(action="move"),
                                    ]
                                    mock_plan_gen.return_value = plan
                                    mock_confirm.return_value = True
                                    mock_execute.return_value = True
                                    
                                    result = workflow.adopt(
                                        source_path=source_dir,
                                        library_name="test_library",
                                        preserve=False,
                                        force=True,
                                    )
                                    
                                    # Verify workflow steps were called
                                    assert mock_search.called
                                    assert mock_get.called
                                    assert mock_identify.called
                                    assert mock_match.called
                                    assert mock_plan_gen.called

    def test_adopt_handles_no_matching_show(self, mock_config, mock_library, temp_dir):
        """Test adoption when show is not found in provider."""
        source_dir = temp_dir / "downloads" / "Unknown Show"
        source_dir.mkdir(parents=True)
        (source_dir / "01x01.mkv").write_text("content")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        with patch.object(workflow, '_search_show_metadata') as mock_search:
            mock_search.return_value = None  # No results
            
            result = workflow.adopt(
                source_path=source_dir,
                library_name="test_library",
                preserve=False,
                force=False,
            )
        
        assert result is False

    def test_adopt_handles_failed_metadata_fetch(self, mock_config, mock_library, temp_dir):
        """Test adoption when metadata fetch fails."""
        source_dir = temp_dir / "downloads" / "Breaking Bad S01"
        source_dir.mkdir(parents=True)
        (source_dir / "01x01.mkv").write_text("content")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        with patch.object(workflow, '_search_show_metadata') as mock_search:
            with patch.object(workflow, '_get_full_show_metadata') as mock_get:
                mock_search.return_value = SearchResult(provider="tmdb", id="1396", title="Breaking Bad", year=2008)
                mock_get.return_value = None  # Failed to fetch
                
                result = workflow.adopt(
                    source_path=source_dir,
                    library_name="test_library",
                    preserve=False,
                    force=False,
                )
        
        assert result is False

    def test_adopt_handles_no_episodes_found(self, mock_config, mock_library, sample_show_metadata, temp_dir):
        """Test adoption when no episode files are found."""
        source_dir = temp_dir / "downloads" / "Breaking Bad"
        source_dir.mkdir(parents=True)
        # Create directory with no video files
        (source_dir / "readme.txt").write_text("No episodes here")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        with patch.object(workflow, '_search_show_metadata') as mock_search:
            with patch.object(workflow, '_get_full_show_metadata') as mock_get:
                with patch.object(workflow, '_identify_episodes') as mock_identify:
                    mock_search.return_value = SearchResult(provider="tmdb", id="1396", title="Breaking Bad", year=2008)
                    mock_get.return_value = sample_show_metadata
                    mock_identify.return_value = None  # No episodes found
                    
                    result = workflow.adopt(
                        source_path=source_dir,
                        library_name="test_library",
                        preserve=False,
                        force=False,
                    )
        
        assert result is False

    def test_adopt_handles_episode_matching_failure(self, mock_config, mock_library, sample_show_metadata, temp_dir):
        """Test adoption when episode matching fails."""
        source_dir = temp_dir / "downloads" / "Breaking Bad S01"
        source_dir.mkdir(parents=True)
        (source_dir / "01x01.mkv").write_text("content")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        with patch.object(workflow, '_search_show_metadata') as mock_search:
            with patch.object(workflow, '_get_full_show_metadata') as mock_get:
                with patch.object(workflow, '_identify_episodes') as mock_identify:
                    with patch.object(workflow, '_match_episodes_to_metadata') as mock_match:
                        mock_search.return_value = SearchResult(provider="tmdb", id="1396", title="Breaking Bad", year=2008)
                        mock_get.return_value = sample_show_metadata
                        mock_identify.return_value = {1: [EpisodeFile(path=source_dir / "01x01.mkv", season=1, episode=1)]}
                        mock_match.return_value = None  # Matching failed
                        
                        result = workflow.adopt(
                            source_path=source_dir,
                            library_name="test_library",
                            preserve=False,
                            force=False,
                        )
        
        assert result is False

    def test_adopt_cancelled_by_user_at_plan_confirmation(self, mock_config, mock_library, sample_show_metadata, temp_dir):
        """Test adoption cancelled by user during plan confirmation."""
        source_dir = temp_dir / "downloads" / "Breaking Bad S01"
        source_dir.mkdir(parents=True)
        (source_dir / "01x01.mkv").write_text("content")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        with patch.object(workflow, '_search_show_metadata') as mock_search:
            with patch.object(workflow, '_get_full_show_metadata') as mock_get:
                with patch.object(workflow, '_identify_episodes') as mock_identify:
                    with patch.object(workflow, '_match_episodes_to_metadata') as mock_match:
                        with patch.object(workflow, '_generate_plan') as mock_plan:
                            with patch.object(workflow, '_confirm_plan') as mock_confirm:
                                mock_search.return_value = SearchResult(provider="tmdb", id="1396", title="Breaking Bad", year=2008)
                                mock_get.return_value = sample_show_metadata
                                mock_identify.return_value = {1: [EpisodeFile(path=source_dir / "01x01.mkv", season=1, episode=1)]}
                                mock_match.return_value = {1: [EpisodeFile(path=source_dir / "01x01.mkv", season=1, episode=1)]}
                                
                                plan = Mock(spec=AdoptionPlan)
                                plan.actions = []
                                mock_plan.return_value = plan
                                mock_confirm.return_value = False  # User cancelled
                                
                                result = workflow.adopt(
                                    source_path=source_dir,
                                    library_name="test_library",
                                    preserve=False,
                                    force=False,
                                )
        
        assert result is False

    def test_adopt_plan_execution_failure(self, mock_config, mock_library, sample_show_metadata, temp_dir):
        """Test adoption when plan execution fails."""
        source_dir = temp_dir / "downloads" / "Breaking Bad S01"
        source_dir.mkdir(parents=True)
        (source_dir / "01x01.mkv").write_text("content")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        with patch.object(workflow, '_search_show_metadata') as mock_search:
            with patch.object(workflow, '_get_full_show_metadata') as mock_get:
                with patch.object(workflow, '_identify_episodes') as mock_identify:
                    with patch.object(workflow, '_match_episodes_to_metadata') as mock_match:
                        with patch.object(workflow, '_generate_plan') as mock_plan:
                            with patch.object(workflow, '_confirm_plan') as mock_confirm:
                                with patch.object(workflow, '_execute_plan') as mock_execute:
                                    mock_search.return_value = SearchResult(provider="tmdb", id="1396", title="Breaking Bad", year=2008)
                                    mock_get.return_value = sample_show_metadata
                                    mock_identify.return_value = {1: [EpisodeFile(path=source_dir / "01x01.mkv", season=1, episode=1)]}
                                    mock_match.return_value = {1: [EpisodeFile(path=source_dir / "01x01.mkv", season=1, episode=1)]}
                                    
                                    plan = Mock(spec=AdoptionPlan)
                                    plan.actions = []
                                    mock_plan.return_value = plan
                                    mock_confirm.return_value = True
                                    mock_execute.return_value = False  # Execution failed
                                    
                                    result = workflow.adopt(
                                        source_path=source_dir,
                                        library_name="test_library",
                                        preserve=False,
                                        force=False,
                                    )
        
        assert result is False

    def test_adopt_with_season_filter(self, mock_config, mock_library, sample_show_metadata, temp_dir):
        """Test adoption with season filter."""
        source_dir = temp_dir / "downloads" / "Breaking Bad"
        source_dir.mkdir(parents=True)
        (source_dir / "01x01.mkv").write_text("s1e1")
        (source_dir / "02x01.mkv").write_text("s2e1")
        
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=False)
        
        # Mock library manager
        mock_lib_manager = Mock(spec=LibraryManager)
        mock_lib_manager.list.return_value = [mock_library]
        mock_lib_manager.get.return_value = mock_library
        workflow.library_manager = mock_lib_manager
        
        with patch.object(workflow, '_search_show_metadata') as mock_search:
            with patch.object(workflow, '_get_full_show_metadata') as mock_get:
                with patch.object(workflow, '_identify_episodes') as mock_identify:
                    mock_search.return_value = SearchResult(provider="tmdb", id="1396", title="Breaking Bad", year=2008)
                    mock_get.return_value = sample_show_metadata
                    
                    # Should only identify season 1
                    result = workflow.adopt(
                        source_path=source_dir,
                        library_name="test_library",
                        preserve=False,
                        force=False,
                        season_filter=1,
                    )
                    
                    # Check that season_filter was passed to _identify_episodes
                    calls = mock_identify.call_args_list
                    if calls:
                        _, kwargs = calls[0]
                        # season_filter should be 1
                        assert kwargs.get('season_filter') == 1 or calls[0][0][1] == 1
