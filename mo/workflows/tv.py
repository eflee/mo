"""TV show adoption workflow with interactive steps."""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import shutil

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from prompt_toolkit import prompt

from mo.config import Config
from mo.library import LibraryManager, Library
from mo.media.scanner import MediaScanner
from mo.media.metadata import MediaMetadataExtractor
from mo.media.matcher import MatchConfidence
from mo.nfo.tv import TVShowNFOGenerator, EpisodeNFOGenerator
from mo.parsers.episode import parse_episode_filename
from mo.parsers.season import format_season_folder_name, detect_season_from_path
from mo.parsers.sanitize import sanitize_filename
from mo.providers.base import SearchResult, TVShowMetadata, EpisodeMetadata, ProviderError
from mo.providers.search import InteractiveSearch
from mo.providers.tmdb import TMDBProvider
from mo.providers.tvdb import TheTVDBProvider
from mo.utils.errors import MoError

# Configure logging
logger = logging.getLogger(__name__)


# Constants
EXTRA_EPISODES_BUFFER = 10  # Number of extra episodes to fetch beyond expected count


@dataclass
class FileAction:
    """Represents a file operation to be performed."""

    action: str  # "move", "copy", "create_dir", "write_nfo"
    source: Optional[Path] = None
    destination: Optional[Path] = None
    content: Optional[str] = None  # For NFO files
    file_type: Optional[str] = None  # "episode", "subtitle", etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "action": self.action,
            "source": str(self.source) if self.source else None,
            "destination": str(self.destination) if self.destination else None,
            "file_type": self.file_type,
            "content_length": len(self.content) if self.content else None,
        }


@dataclass
class EpisodeFile:
    """Represents an episode file with parsed metadata."""

    path: Path
    season: int
    episode: int
    episode_end: Optional[int] = None  # For multi-episode files
    duration: Optional[float] = None  # seconds
    matched_episode: Optional[EpisodeMetadata] = None
    confidence: Optional[MatchConfidence] = None


@dataclass
class AdoptionPlan:
    """Complete plan for adopting a TV show."""

    source_path: Path
    library: Library
    show_metadata: TVShowMetadata
    episodes_by_season: Dict[int, List[EpisodeFile]]
    actions: List[FileAction]
    series_folder: Path
    preserve_originals: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "source_path": str(self.source_path),
            "library": {
                "name": self.library.name,
                "type": self.library.library_type,
                "path": str(self.library.path),
            },
            "show_metadata": {
                "title": self.show_metadata.title,
                "year": self.show_metadata.year,
                "imdb_id": self.show_metadata.imdb_id,
                "tmdb_id": self.show_metadata.tmdb_id,
                "tvdb_id": self.show_metadata.tvdb_id,
            },
            "series_folder": str(self.series_folder),
            "preserve_originals": self.preserve_originals,
            "episodes_count": sum(len(eps) for eps in self.episodes_by_season.values()),
            "seasons": list(self.episodes_by_season.keys()),
            "actions": [action.to_dict() for action in self.actions],
        }


class TVShowAdoptionWorkflow:
    """Interactive workflow for adopting TV show files into a library."""

    def __init__(
        self,
        config: Config,
        console: Optional[Console] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize TV show adoption workflow.

        Args:
            config: Configuration instance
            console: Rich console for output
            verbose: Enable verbose output
            dry_run: Preview actions without executing
        """
        self.config = config
        self.console = console or Console()
        self.verbose = verbose
        self.dry_run = dry_run

        self.library_manager = LibraryManager(config)
        self.scanner = MediaScanner()
        self.search = InteractiveSearch(console=self.console)
        self.tvshow_nfo_generator = TVShowNFOGenerator()
        self.episode_nfo_generator = EpisodeNFOGenerator()
        self.metadata_extractor = MediaMetadataExtractor()

        # Initialize TMDB provider
        tmdb_api_key = config.get("metadata", "tmdb_api_key")
        if not tmdb_api_key:
            raise MoError(
                "TMDB API key not configured. "
                "Run: mo config set metadata.tmdb_api_key <your_key>"
            )
        self.tmdb = TMDBProvider(access_token=tmdb_api_key)

        # Initialize TheTVDB provider if configured (for future use as fallback/supplement to TMDB)
        # Currently not used in workflow, but available for future enhancement
        tvdb_api_key = config.get("metadata", "tvdb_api_key")
        self.tvdb = TheTVDBProvider(api_key=tvdb_api_key) if tvdb_api_key else None

    def adopt(
        self,
        source_path: Path,
        library_name: Optional[str] = None,
        preserve: bool = False,
        force: bool = False,
        season_filter: Optional[int] = None,
    ) -> bool:
        """Run the complete TV show adoption workflow.

        Args:
            source_path: Path to TV show directory
            library_name: Optional library name (auto-selects if only one show library)
            preserve: Copy files instead of moving them
            force: Skip confirmation prompts
            season_filter: Only adopt specific season number

        Returns:
            bool: True if adoption succeeded, False otherwise
        """
        logger.info(f"Starting TV show adoption workflow for: {source_path}")
        logger.debug(f"Options: preserve={preserve}, force={force}, library={library_name}, season_filter={season_filter}")
        
        try:
            # Step 1: Select library
            library = self._select_library(library_name)
            logger.info(f"Selected library: {library.name} at {library.path}")

            # Step 2: Parse title/year from source path
            title_hint, year_hint = self._parse_source_path(source_path)
            logger.debug(f"Parsed from source: title={title_hint}, year={year_hint}")

            # Step 3: Search for show metadata
            search_result = self._search_show_metadata(title_hint, year_hint)
            if not search_result:
                logger.warning("TV show metadata search cancelled by user")
                self.console.print("[yellow]Search cancelled.[/yellow]")
                return False

            # Step 4: Get full show metadata
            show_metadata = self._get_full_show_metadata(search_result)
            if not show_metadata:
                logger.warning("Failed to fetch full show metadata")
                return False
            
            logger.info(f"Fetched show metadata: {show_metadata.title} ({show_metadata.year})")

            # Step 5: Scan and categorize episode files by season
            episodes_by_season = self._identify_episodes(source_path, season_filter)
            if not episodes_by_season:
                logger.warning("No episodes identified for adoption")
                return False
            
            total_episodes = sum(len(eps) for eps in episodes_by_season.values())
            logger.info(f"Identified {total_episodes} episodes across {len(episodes_by_season)} seasons")

            # Step 6: Match episodes to metadata for each season
            matched_episodes = self._match_episodes_to_metadata(
                show_metadata, episodes_by_season
            )
            if not matched_episodes:
                logger.warning("Episode matching failed")
                return False

            # Step 7: Generate action plan
            plan = self._generate_plan(
                source_path=source_path,
                library=library,
                show_metadata=show_metadata,
                episodes_by_season=matched_episodes,
                preserve=preserve,
            )
            logger.info(f"Generated adoption plan with {len(plan.actions)} actions")

            # Step 8: Display plan and confirm
            if not self._confirm_plan(plan, force):
                logger.info("Adoption cancelled by user")
                self.console.print("[yellow]Adoption cancelled.[/yellow]")
                return False

            # Step 9: Execute plan
            success = self._execute_plan(plan)

            if success:
                logger.info(f"TV show successfully adopted: {plan.series_folder}")
                self.console.print("\n[bold green]✓ TV show adopted successfully![/bold green]")
                self.console.print(f"Location: {plan.series_folder}")
            else:
                logger.error("Plan execution failed")

            return success

        except ProviderError as e:
            logger.error(f"Metadata provider error: {e}", exc_info=True)
            self.console.print(f"[red]Metadata provider error:[/red] {e}")
            return False
        except MoError as e:
            logger.error(f"Error: {e}", exc_info=True)
            self.console.print(f"[red]Error:[/red] {e}")
            return False
        except Exception as e:
            logger.exception("Unexpected error during TV show adoption")
            self.console.print(f"[red]Unexpected error:[/red] {e}")
            if self.verbose:
                import traceback
                self.console.print(traceback.format_exc())
            return False

    def _select_library(self, library_name: Optional[str]) -> Library:
        """Select which library to use for adoption.

        Args:
            library_name: Optional library name

        Returns:
            Library: Selected library

        Raises:
            MoError: If no library found or multiple libraries without selection
        """
        show_libraries = [
            lib for lib in self.library_manager.list()
            if lib.library_type == "show"
        ]

        if not show_libraries:
            raise MoError(
                "No TV show libraries configured. "
                "Run: mo library add <name> show <path>"
            )

        if library_name:
            # Use specified library
            return self.library_manager.get(library_name)

        if len(show_libraries) == 1:
            # Auto-select single library
            lib = show_libraries[0]
            if self.verbose:
                self.console.print(f"[dim]Using library: {lib.name}[/dim]")
            return lib

        # Multiple libraries - need to prompt
        self.console.print("\n[bold]Multiple TV show libraries found:[/bold]")
        table = Table()
        table.add_column("#", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Path")

        for idx, lib in enumerate(show_libraries, 1):
            table.add_row(str(idx), lib.name, str(lib.path))

        self.console.print(table)

        try:
            choice = prompt("\nSelect library (number): ", default="1").strip()
            index = int(choice) - 1
            if 0 <= index < len(show_libraries):
                return show_libraries[index]
            else:
                raise MoError("Invalid library selection")
        except ValueError:
            raise MoError(
                f"Invalid library selection: {choice!r}. "
                f"Please enter a number between 1 and {len(show_libraries)}."
            )
        except (KeyboardInterrupt, EOFError):
            raise MoError("Library selection cancelled")

    def _parse_source_path(self, source_path: Path) -> Tuple[str, Optional[int]]:
        """Extract title and year hints from source path.

        Args:
            source_path: Path to parse

        Returns:
            Tuple[str, Optional[int]]: (title, year)
        """
        # Try parsing the directory name
        name = source_path.name

        # Try to extract year from path (e.g., "Show Name (2020)")
        import re
        year_match = re.search(r'\((\d{4})\)', name)
        year = int(year_match.group(1)) if year_match else None

        # Remove year and clean title
        title = re.sub(r'\s*\(\d{4}\)', '', name)
        title = re.sub(r'[._-]+', ' ', title).strip()

        if self.verbose:
            self.console.print(f"[dim]Parsed from path - Title: {title}, Year: {year}[/dim]")

        return title, year

    def _search_show_metadata(
        self, title: str, year: Optional[int]
    ) -> Optional[SearchResult]:
        """Interactive show metadata search.

        Args:
            title: Title hint
            year: Optional year hint

        Returns:
            SearchResult | None: Selected result or None if cancelled
        """
        self.console.print("\n[bold cyan]Step 1: Search for TV Show Metadata[/bold cyan]")

        result = self.search.search_and_select(
            search_func=self.tmdb.search_tv,
            initial_title=title,
            year=year,
            media_type="tv",
        )

        if result and not self.search.confirm_selection(result):
            return None

        return result

    def _get_full_show_metadata(self, search_result: SearchResult) -> Optional[TVShowMetadata]:
        """Fetch complete metadata for selected show.

        Args:
            search_result: Search result to get metadata for

        Returns:
            TVShowMetadata | None: Full metadata or None on error
        """
        self.console.print("\n[dim]Fetching complete show metadata...[/dim]")

        try:
            metadata = self.tmdb.get_tv_show(search_result.id)

            if self.verbose:
                self.console.print(f"[dim]Fetched metadata for: {metadata.title} ({metadata.year})[/dim]")
                self.console.print(f"[dim]Seasons: {metadata.seasons}[/dim]")
                self.console.print(f"[dim]Status: {metadata.status}[/dim]")

            return metadata

        except ProviderError as e:
            self.console.print(f"[red]Failed to fetch metadata:[/red] {e}")
            return None

    def _identify_episodes(
        self, source_path: Path, season_filter: Optional[int]
    ) -> Optional[Dict[int, List[EpisodeFile]]]:
        """Identify and categorize episode files by season.

        Args:
            source_path: Source path to scan
            season_filter: Only include specific season

        Returns:
            Dict[int, List[EpisodeFile]] | None: Episodes grouped by season, or None if cancelled
        """
        self.console.print("\n[bold cyan]Step 2: Identify Episode Files[/bold cyan]")

        # Scan directory for video files
        scan_result = self.scanner.scan_directory(source_path)
        video_files = [vf.path for vf in scan_result.video_files]

        if not video_files:
            self.console.print("[red]No video files found![/red]")
            return None

        # Parse episode information from filenames
        episodes_by_season: Dict[int, List[EpisodeFile]] = defaultdict(list)

        for video_file in video_files:
            # Try to detect season from path first
            season_from_path = detect_season_from_path(video_file)

            # Parse episode filename
            parsed = parse_episode_filename(video_file.name)

            if not parsed:
                if self.verbose:
                    self.console.print(f"[yellow]Warning: Could not parse {video_file.name}[/yellow]")
                continue

            # Determine season number
            season = parsed.season_number if parsed.season_number is not None else season_from_path
            if season is None:
                season = 1  # Default to season 1 per Jellyfin behavior
                if self.verbose:
                    self.console.print(
                        f"[yellow]Warning: No season detected for {video_file.name}, "
                        f"defaulting to Season 1[/yellow]"
                    )

            # Skip if season filter is active and doesn't match
            if season_filter is not None and season != season_filter:
                continue

            # Create episode file entry
            episode_file = EpisodeFile(
                path=video_file,
                season=season,
                episode=parsed.episode_number,
                episode_end=parsed.ending_episode_number,
            )

            episodes_by_season[season].append(episode_file)

        if not episodes_by_season:
            self.console.print("[red]No episodes found matching criteria![/red]")
            return None

        # Sort episodes within each season
        for season in episodes_by_season:
            episodes_by_season[season].sort(key=lambda e: e.episode)

        # Display identified episodes
        self._display_identified_episodes(episodes_by_season)

        # Confirm with user
        try:
            confirm = prompt(
                f"\nFound {sum(len(eps) for eps in episodes_by_season.values())} episodes "
                f"across {len(episodes_by_season)} season(s). Continue? [Y/n]: ",
                default="y"
            ).strip().lower()

            if confirm not in ("y", "yes", ""):
                self.console.print("[yellow]Episode identification cancelled.[/yellow]")
                return None

        except (KeyboardInterrupt, EOFError):
            return None

        return dict(episodes_by_season)

    def _display_identified_episodes(self, episodes_by_season: Dict[int, List[EpisodeFile]]) -> None:
        """Display identified episodes in a table.

        Args:
            episodes_by_season: Episodes grouped by season
        """
        table = Table(title="Identified Episodes")
        table.add_column("Season", style="cyan")
        table.add_column("Episode", style="bold")
        table.add_column("File", style="dim")

        for season in sorted(episodes_by_season.keys()):
            for ep in episodes_by_season[season]:
                episode_str = f"E{ep.episode:02d}"
                if ep.episode_end:
                    episode_str += f"-E{ep.episode_end:02d}"

                table.add_row(
                    f"Season {season:02d}" if season > 0 else "Specials",
                    episode_str,
                    ep.path.name
                )

        self.console.print(table)

    def _match_episodes_to_metadata(
        self,
        show_metadata: TVShowMetadata,
        episodes_by_season: Dict[int, List[EpisodeFile]],
    ) -> Optional[Dict[int, List[EpisodeFile]]]:
        """Match episode files to metadata from providers.

        Args:
            show_metadata: Show metadata
            episodes_by_season: Episodes grouped by season

        Returns:
            Dict[int, List[EpisodeFile]] | None: Matched episodes or None if cancelled
        """
        self.console.print("\n[bold cyan]Step 3: Match Episodes to Metadata[/bold cyan]")

        # Process each season
        for season_num in sorted(episodes_by_season.keys()):
            self.console.print(f"\n[bold]Processing Season {season_num}...[/bold]")

            season_episodes = episodes_by_season[season_num]

            # Extract durations for matching
            for episode_file in season_episodes:
                duration = self.metadata_extractor.get_duration(episode_file.path)
                episode_file.duration = duration

            # Fetch episode metadata for this season
            try:
                episode_metadata_list = self._fetch_season_metadata(
                    show_metadata, season_num, len(season_episodes)
                )
            except ProviderError as e:
                self.console.print(f"[yellow]Warning: Could not fetch metadata for season {season_num}: {e}[/yellow]")
                episode_metadata_list = []

            # Match episodes using filename hints
            self._match_season_episodes(season_episodes, episode_metadata_list)

            # Display matches for review
            self._display_episode_matches(season_num, season_episodes)

        # Confirm matches
        try:
            confirm = prompt("\nAccept episode matches? [Y/n]: ", default="y").strip().lower()

            if confirm not in ("y", "yes", ""):
                self.console.print("[yellow]Episode matching cancelled.[/yellow]")
                return None

        except (KeyboardInterrupt, EOFError):
            return None

        return episodes_by_season

    def _fetch_season_metadata(
        self, show_metadata: TVShowMetadata, season_num: int, expected_episodes: int
    ) -> List[EpisodeMetadata]:
        """Fetch episode metadata for a season.

        Args:
            show_metadata: Show metadata
            season_num: Season number
            expected_episodes: Expected number of episodes

        Returns:
            List[EpisodeMetadata]: Episode metadata list
        """
        episodes = []

        # Fetch from TMDB
        for ep_num in range(1, expected_episodes + EXTRA_EPISODES_BUFFER):
            try:
                ep_metadata = self.tmdb.get_episode(show_metadata.tmdb_id, season_num, ep_num)
                if ep_metadata:
                    episodes.append(ep_metadata)
            except ProviderError:
                # Stop when we hit missing episodes
                break

        return episodes

    def _match_season_episodes(
        self, season_episodes: List[EpisodeFile], metadata_list: List[EpisodeMetadata]
    ) -> None:
        """Match episode files to metadata.

        Args:
            season_episodes: Episode files for season
            metadata_list: Episode metadata from provider
        """
        # Create mapping of episode number to metadata
        metadata_by_episode = {ep.episode_number: ep for ep in metadata_list}

        for episode_file in season_episodes:
            # Try exact episode number match first
            if episode_file.episode in metadata_by_episode:
                episode_file.matched_episode = metadata_by_episode[episode_file.episode]
                episode_file.confidence = MatchConfidence.HIGH
            else:
                # No metadata found for this episode number
                episode_file.confidence = MatchConfidence.MEDIUM

    def _display_episode_matches(self, season_num: int, episodes: List[EpisodeFile]) -> None:
        """Display episode matching results.

        Args:
            season_num: Season number
            episodes: Episode files with matches
        """
        table = Table(title=f"Season {season_num} Matches")
        table.add_column("Episode", style="cyan")
        table.add_column("File", style="dim")
        table.add_column("Matched Title", style="bold")
        table.add_column("Confidence", style="green")

        for ep in episodes:
            ep_str = f"S{season_num:02d}E{ep.episode:02d}"
            if ep.episode_end:
                ep_str += f"-E{ep.episode_end:02d}"

            matched_title = ep.matched_episode.title if ep.matched_episode else "[No Match]"
            confidence = ep.confidence.name if ep.confidence else "UNKNOWN"

            table.add_row(
                ep_str,
                ep.path.name[:40] + "..." if len(ep.path.name) > 40 else ep.path.name,
                matched_title,
                confidence
            )

        self.console.print(table)

    def _generate_plan(
        self,
        source_path: Path,
        library: Library,
        show_metadata: TVShowMetadata,
        episodes_by_season: Dict[int, List[EpisodeFile]],
        preserve: bool,
    ) -> AdoptionPlan:
        """Generate action plan for adoption.

        Args:
            source_path: Source path
            library: Target library
            show_metadata: Show metadata
            episodes_by_season: Episodes by season
            preserve: Whether to preserve originals

        Returns:
            AdoptionPlan: Complete action plan
        """
        self.console.print("\n[bold cyan]Step 4: Generate Action Plan[/bold cyan]")

        # Determine series folder name
        title = sanitize_filename(show_metadata.title)
        year = show_metadata.year or ""
        folder_name = f"{title} ({year})" if year else title
        series_folder = library.path / folder_name

        # Collect actions
        actions: List[FileAction] = []

        # Create series directory
        actions.append(FileAction(
            action="create_dir",
            destination=series_folder,
        ))

        # Generate and write tvshow.nfo
        tvshow_nfo_content = self.tvshow_nfo_generator.generate(show_metadata)
        tvshow_nfo_path = series_folder / "tvshow.nfo"
        actions.append(FileAction(
            action="write_nfo",
            destination=tvshow_nfo_path,
            content=tvshow_nfo_content,
        ))

        # Process each season
        for season_num in sorted(episodes_by_season.keys()):
            # Create season folder
            season_folder_name = format_season_folder_name(season_num)
            season_folder = series_folder / season_folder_name

            actions.append(FileAction(
                action="create_dir",
                destination=season_folder,
            ))

            # Process episodes in season
            for episode_file in episodes_by_season[season_num]:
                # Generate episode filename
                episode_str = f"S{season_num:02d}E{episode_file.episode:02d}"
                if episode_file.episode_end:
                    episode_str += f"-E{episode_file.episode_end:02d}"

                episode_title = ""
                if episode_file.matched_episode:
                    episode_title = f" {sanitize_filename(episode_file.matched_episode.title)}"

                episode_filename = f"{title} {episode_str}{episode_title}{episode_file.path.suffix}"
                episode_dest = season_folder / episode_filename

                # Move/copy episode file
                actions.append(FileAction(
                    action="copy" if preserve else "move",
                    source=episode_file.path,
                    destination=episode_dest,
                    file_type="episode",
                ))

                # Write episode NFO
                if episode_file.matched_episode:
                    if episode_file.episode_end:
                        # Multi-episode NFO - fetch metadata for all episodes in range
                        episodes_metadata = []
                        for ep_num in range(episode_file.episode, episode_file.episode_end + 1):
                            try:
                                ep_metadata = self.tmdb.get_episode(
                                    show_metadata.tmdb_id, season_num, ep_num
                                )
                                if ep_metadata:
                                    episodes_metadata.append(ep_metadata)
                            except ProviderError:
                                # If we can't fetch an episode, skip it
                                if self.verbose:
                                    self.console.print(
                                        f"[yellow]Warning: Could not fetch metadata for "
                                        f"S{season_num:02d}E{ep_num:02d}[/yellow]"
                                    )

                        if episodes_metadata:
                            nfo_content = self.episode_nfo_generator.generate_multi_episode(episodes_metadata)
                        else:
                            # Fallback to single episode if we couldn't fetch multi-episode data
                            nfo_content = self.episode_nfo_generator.generate(episode_file.matched_episode)
                    else:
                        nfo_content = self.episode_nfo_generator.generate(episode_file.matched_episode)

                    nfo_path = episode_dest.with_suffix('.nfo')
                    actions.append(FileAction(
                        action="write_nfo",
                        destination=nfo_path,
                        content=nfo_content,
                    ))

        return AdoptionPlan(
            source_path=source_path,
            library=library,
            show_metadata=show_metadata,
            episodes_by_season=episodes_by_season,
            actions=actions,
            series_folder=series_folder,
            preserve_originals=preserve,
        )

    def _confirm_plan(self, plan: AdoptionPlan, force: bool) -> bool:
        """Display plan and request confirmation.

        Args:
            plan: Adoption plan
            force: Skip confirmation if True

        Returns:
            bool: True if confirmed, False otherwise
        """
        self.console.print("\n[bold cyan]Step 5: Review Action Plan[/bold cyan]")

        # Display plan tree
        tree = Tree(f"[bold]{plan.show_metadata.title}[/bold]")

        # Count actions by type
        action_counts = defaultdict(int)
        for action in plan.actions:
            action_counts[action.action] += 1

        tree.add(f"Series Folder: {plan.series_folder}")
        tree.add(f"Episodes: {sum(len(eps) for eps in plan.episodes_by_season.values())}")
        tree.add(f"Seasons: {len(plan.episodes_by_season)}")

        actions_node = tree.add("Actions:")
        for action_type, count in sorted(action_counts.items()):
            actions_node.add(f"{action_type}: {count}")

        self.console.print(tree)

        # Check for conflicts
        if plan.series_folder.exists():
            self.console.print(
                f"\n[yellow]Warning: Series folder already exists: {plan.series_folder}[/yellow]"
            )

        if self.dry_run:
            self.console.print("\n[yellow]DRY RUN - No changes will be made[/yellow]")
            return True

        if force:
            return True

        # Request confirmation
        try:
            confirm = prompt("\nProceed with adoption? [y/N]: ", default="n").strip().lower()
            return confirm in ("y", "yes")
        except (KeyboardInterrupt, EOFError):
            return False

    def _execute_plan(self, plan: AdoptionPlan) -> bool:
        """Execute the adoption plan.

        Args:
            plan: Adoption plan

        Returns:
            bool: True if successful, False otherwise
        """
        self.console.print("\n[bold cyan]Step 6: Executing Plan[/bold cyan]")

        if self.dry_run:
            self.console.print("[yellow]Dry run - skipping execution[/yellow]")
            return True

        # Create action log
        log_entry = {
            "type": "tv_adoption",
            "timestamp": datetime.now().isoformat(),
            "plan": plan.to_dict(),
            "results": [],
        }

        try:
            with self.console.status("[bold green]Executing actions...") as status:
                for i, action in enumerate(plan.actions, 1):
                    status.update(f"[bold green]Executing action {i}/{len(plan.actions)}...")

                    try:
                        if action.action == "create_dir":
                            action.destination.mkdir(parents=True, exist_ok=True)
                        elif action.action == "move":
                            if action.destination is not None:
                                action.destination.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(action.source), str(action.destination))
                        elif action.action == "copy":
                            if action.destination is not None:
                                action.destination.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(action.source), str(action.destination))
                        elif action.action == "write_nfo":
                            if action.destination is not None:
                                action.destination.parent.mkdir(parents=True, exist_ok=True)
                            action.destination.write_text(action.content, encoding="utf-8")

                        log_entry["results"].append({
                            "action": action.to_dict(),
                            "status": "success",
                        })

                    except Exception as e:
                        log_entry["results"].append({
                            "action": action.to_dict(),
                            "status": "failed",
                            "error": str(e),
                        })
                        raise

            # Write success log
            log_filename = f".mo_action_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            log_path = Path.cwd() / log_filename
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_entry, f, indent=2)

            return True

        except Exception as e:
            self.console.print(f"\n[red]Execution failed:[/red] {e}")

            log_entry["results"].append({
                "action": "error",
                "error": str(e),
                "status": "failed",
            })

            # Still try to write log
            try:
                log_filename = f".mo_action_log_FAILED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                log_path = Path.cwd() / log_filename
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(log_entry, f, indent=2)
            except Exception:
                # If writing the failure log also fails, ignore it to avoid masking the original error
                pass

            return False
