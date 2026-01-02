"""Tests for TV show adoption workflow."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mo.config import Config
from mo.library import Library
from mo.providers.base import SearchResult, TVShowMetadata, EpisodeMetadata, Actor, Rating
from mo.workflows.tv import TVShowAdoptionWorkflow, FileAction, EpisodeFile, AdoptionPlan


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
        content_rating="TV-MA",
        genres=["Drama", "Crime", "Thriller"],
        networks=["AMC"],
        actors=[
            Actor(name="Bryan Cranston", role="Walter White", order=0),
            Actor(name="Aaron Paul", role="Jesse Pinkman", order=1),
        ],
        imdb_id="tt0903747",
        tmdb_id="1396",
        tvdb_id="81189",
        seasons=5,
        status="Ended",
    )


@pytest.fixture
def sample_episode_metadata():
    """Create sample episode metadata."""
    return EpisodeMetadata(
        provider="tmdb",
        show_id="1396",
        season_number=1,
        episode_number=1,
        title="Pilot",
        show_title="Breaking Bad",
        plot="A high school chemistry teacher is diagnosed with cancer...",
        aired="2008-01-20",
        runtime=58,
        rating=8.2,
        ratings=[Rating(source="tmdb", value=8.2, votes=5000)],
        directors=["Vince Gilligan"],
        writers=["Vince Gilligan"],
        tmdb_id="1396-1-1",
    )


class TestTVShowAdoptionWorkflow:
    """Test TVShowAdoptionWorkflow class."""

    def test_parse_source_path(self, mock_config, temp_dir):
        """Test parsing title and year from source path."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Test with year in folder name
        source = temp_dir / "Breaking Bad (2008)"
        source.mkdir()

        title, year = workflow._parse_source_path(source)

        assert "Breaking" in title or "bad" in title.lower()
        assert year == 2008

    def test_parse_source_path_no_year(self, mock_config, temp_dir):
        """Test parsing title without year."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        source = temp_dir / "Breaking Bad"
        source.mkdir()

        title, year = workflow._parse_source_path(source)

        assert "Breaking" in title or "bad" in title.lower()
        assert year is None

    def test_select_library_single(self, mock_config, mock_library):
        """Test library selection with single library."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Mock library manager to return single library
        workflow.library_manager.list = Mock(return_value=[mock_library])

        library = workflow._select_library(None)

        assert library == mock_library

    def test_select_library_by_name(self, mock_config, mock_library):
        """Test library selection by name."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Mock library manager
        workflow.library_manager.get = Mock(return_value=mock_library)
        workflow.library_manager.list = Mock(return_value=[mock_library])

        library = workflow._select_library("test_library")

        assert library == mock_library
        workflow.library_manager.get.assert_called_once_with("test_library")

    def test_file_action_to_dict(self, temp_dir):
        """Test FileAction serialization."""
        source = temp_dir / "source.mkv"
        dest = temp_dir / "dest.mkv"

        action = FileAction(
            action="move",
            source=source,
            destination=dest,
            file_type="episode",
        )

        result = action.to_dict()

        assert result["action"] == "move"
        assert result["source"] == str(source)
        assert result["destination"] == str(dest)
        assert result["file_type"] == "episode"

    def test_episode_file_creation(self, temp_dir):
        """Test EpisodeFile dataclass."""
        video_file = temp_dir / "Breaking.Bad.S01E01.mkv"
        video_file.write_text("fake content")

        episode_file = EpisodeFile(
            path=video_file,
            season=1,
            episode=1,
            duration=3600.0,
        )

        assert episode_file.season == 1
        assert episode_file.episode == 1
        assert episode_file.duration == 3600.0
        assert episode_file.episode_end is None

    def test_episode_file_multi_episode(self, temp_dir):
        """Test EpisodeFile with multi-episode file."""
        video_file = temp_dir / "Breaking.Bad.S01E01-E02.mkv"
        video_file.write_text("fake content")

        episode_file = EpisodeFile(
            path=video_file,
            season=1,
            episode=1,
            episode_end=2,
        )

        assert episode_file.episode == 1
        assert episode_file.episode_end == 2

    def test_adoption_plan_to_dict(self, mock_library, sample_show_metadata, temp_dir):
        """Test AdoptionPlan serialization."""
        source = temp_dir / "source"
        series_folder = temp_dir / "show"

        episode_file = EpisodeFile(
            path=temp_dir / "episode.mkv",
            season=1,
            episode=1,
        )

        action = FileAction(
            action="create_dir",
            destination=series_folder,
        )

        plan = AdoptionPlan(
            source_path=source,
            library=mock_library,
            show_metadata=sample_show_metadata,
            episodes_by_season={1: [episode_file]},
            actions=[action],
            series_folder=series_folder,
            preserve_originals=False,
        )

        result = plan.to_dict()

        assert result["source_path"] == str(source)
        assert result["series_folder"] == str(series_folder)
        assert result["preserve_originals"] is False
        assert "library" in result
        assert "show_metadata" in result
        assert "actions" in result
        assert result["episodes_count"] == 1
        assert result["seasons"] == [1]


class TestErrorHandling:
    """Test error handling in TVShowAdoptionWorkflow."""

    def test_missing_tmdb_api_key(self, temp_dir):
        """Test that workflow raises MoError when TMDB API key is not configured."""
        from mo.utils.errors import MoError

        config = Mock(spec=Config)
        config.get.return_value = None  # No API key configured

        with pytest.raises(MoError, match="TMDB API key not configured"):
            TVShowAdoptionWorkflow(config=config, dry_run=True)

    def test_provider_error_during_metadata_fetch(self, mock_config, temp_dir):
        """Test handling of ProviderError during metadata fetch."""
        from mo.providers.base import ProviderError

        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Mock the TMDB provider to raise ProviderError
        workflow.tmdb.get_tv_show = Mock(side_effect=ProviderError("API Error"))

        # Create a mock search result
        search_result = Mock()
        search_result.id = "1396"

        # Test that _get_full_show_metadata handles the error gracefully
        metadata = workflow._get_full_show_metadata(search_result)

        assert metadata is None

    def test_keyboard_interrupt_during_library_selection(self, mock_config, temp_dir):
        """Test handling of KeyboardInterrupt during library selection."""
        from mo.utils.errors import MoError

        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create multiple mock libraries to trigger selection prompt
        lib1 = Mock(spec=Library)
        lib1.name = "library1"
        lib1.library_type = "show"
        lib1.path = temp_dir / "lib1"

        lib2 = Mock(spec=Library)
        lib2.name = "library2"
        lib2.library_type = "show"
        lib2.path = temp_dir / "lib2"

        workflow.library_manager.list = Mock(return_value=[lib1, lib2])

        # Mock prompt to raise KeyboardInterrupt
        with patch("mo.workflows.tv.prompt", side_effect=KeyboardInterrupt):
            with pytest.raises(MoError, match="Library selection cancelled"):
                workflow._select_library(None)

    def test_no_video_files_found(self, mock_config, temp_dir):
        """Test handling when no video files are found."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create an empty directory
        source_dir = temp_dir / "show_dir"
        source_dir.mkdir()

        # Mock prompt to skip confirmation
        with patch("mo.workflows.tv.prompt", return_value="y"):
            result = workflow._identify_episodes(source_dir, None)

        assert result is None


class TestEpisodeIdentification:
    """Test episode identification logic."""

    def test_identify_single_season(self, mock_config, temp_dir):
        """Test identification of episodes in a single season."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create season directory with episodes
        show_dir = temp_dir / "Breaking Bad"
        show_dir.mkdir()
        season_dir = show_dir / "Season 01"
        season_dir.mkdir()

        # Create episode files
        (season_dir / "Breaking.Bad.S01E01.mkv").write_bytes(b"0" * 1000000)
        (season_dir / "Breaking.Bad.S01E02.mkv").write_bytes(b"0" * 1000000)

        # Mock the prompt to auto-confirm
        with patch("mo.workflows.tv.prompt", return_value="y"):
            episodes = workflow._identify_episodes(show_dir, None)

        assert episodes is not None
        assert 1 in episodes
        assert len(episodes[1]) == 2
        assert episodes[1][0].episode == 1
        assert episodes[1][1].episode == 2

    def test_identify_multiple_seasons(self, mock_config, temp_dir):
        """Test identification of episodes across multiple seasons."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create show directory with multiple seasons
        show_dir = temp_dir / "Breaking Bad"
        show_dir.mkdir()

        season1_dir = show_dir / "Season 01"
        season1_dir.mkdir()
        (season1_dir / "Breaking.Bad.S01E01.mkv").write_bytes(b"0" * 1000000)

        season2_dir = show_dir / "Season 02"
        season2_dir.mkdir()
        (season2_dir / "Breaking.Bad.S02E01.mkv").write_bytes(b"0" * 1000000)

        # Mock the prompt to auto-confirm
        with patch("mo.workflows.tv.prompt", return_value="y"):
            episodes = workflow._identify_episodes(show_dir, None)

        assert episodes is not None
        assert 1 in episodes
        assert 2 in episodes
        assert len(episodes[1]) == 1
        assert len(episodes[2]) == 1

    def test_season_filter(self, mock_config, temp_dir):
        """Test season filtering."""
        workflow = TVShowAdoptionWorkflow(config=mock_config, dry_run=True)

        # Create show directory with multiple seasons
        show_dir = temp_dir / "Breaking Bad"
        show_dir.mkdir()

        season1_dir = show_dir / "Season 01"
        season1_dir.mkdir()
        (season1_dir / "Breaking.Bad.S01E01.mkv").write_bytes(b"0" * 1000000)

        season2_dir = show_dir / "Season 02"
        season2_dir.mkdir()
        (season2_dir / "Breaking.Bad.S02E01.mkv").write_bytes(b"0" * 1000000)

        # Mock the prompt to auto-confirm
        with patch("mo.workflows.tv.prompt", return_value="y"):
            episodes = workflow._identify_episodes(show_dir, season_filter=1)

        assert episodes is not None
        assert 1 in episodes
        assert 2 not in episodes  # Season 2 should be filtered out
        assert len(episodes[1]) == 1
