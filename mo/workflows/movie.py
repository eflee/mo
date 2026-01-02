"""Movie adoption workflow with interactive steps."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import shutil

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from prompt_toolkit import prompt

from mo.config import Config
from mo.library import LibraryManager, Library
from mo.media.scanner import ContentType, MediaScanner
from mo.nfo.movie import MovieNFOGenerator
from mo.nfo.paths import NFOPathResolver
from mo.parsers.movie import parse_movie_filename
from mo.parsers.sanitize import sanitize_filename
from mo.providers.base import SearchResult, MovieMetadata, ProviderError
from mo.providers.search import InteractiveSearch
from mo.providers.tmdb import TMDBProvider
from mo.utils.errors import MoError


@dataclass
class FileAction:
    """Represents a file operation to be performed."""

    action: str  # "move", "copy", "create_dir", "write_nfo"
    source: Optional[Path] = None
    destination: Optional[Path] = None
    content: Optional[str] = None  # For NFO files
    file_type: Optional[str] = None  # "main", "extra", "subtitle", etc.

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
class AdoptionPlan:
    """Complete plan for adopting a movie."""

    source_path: Path
    library: Library
    metadata: MovieMetadata
    actions: List[FileAction]
    movie_folder: Path
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
            "metadata": {
                "title": self.metadata.title,
                "year": self.metadata.year,
                "imdb_id": self.metadata.imdb_id,
                "tmdb_id": self.metadata.tmdb_id,
            },
            "movie_folder": str(self.movie_folder),
            "preserve_originals": self.preserve_originals,
            "actions": [action.to_dict() for action in self.actions],
        }


class MovieAdoptionWorkflow:
    """Interactive workflow for adopting movie files into a library."""

    def __init__(
        self,
        config: Config,
        console: Optional[Console] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize movie adoption workflow.

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
        self.nfo_generator = MovieNFOGenerator()

        # Initialize TMDB provider
        tmdb_api_key = config.get("metadata", "tmdb_api_key")
        if not tmdb_api_key:
            raise MoError(
                "TMDB API key not configured. "
                "Run: mo config set metadata.tmdb_api_key <your_key>"
            )
        self.tmdb = TMDBProvider(access_token=tmdb_api_key)

    def adopt(
        self,
        source_path: Path,
        library_name: Optional[str] = None,
        preserve: bool = False,
        force: bool = False,
    ) -> bool:
        """Run the complete movie adoption workflow.

        Args:
            source_path: Path to movie file or directory
            library_name: Optional library name (auto-selects if only one movie library)
            preserve: Copy files instead of moving them
            force: Skip confirmation prompts

        Returns:
            bool: True if adoption succeeded, False otherwise
        """
        try:
            # Step 1: Select library
            library = self._select_library(library_name)

            # Step 2: Parse title/year from source path
            title_hint, year_hint = self._parse_source_path(source_path)

            # Step 3: Search for metadata
            search_result = self._search_metadata(title_hint, year_hint)
            if not search_result:
                self.console.print("[yellow]Search cancelled.[/yellow]")
                return False

            # Step 4: Get full metadata
            metadata = self._get_full_metadata(search_result)
            if not metadata:
                return False

            # Step 5: Identify and categorize files
            files = self._identify_files(source_path)
            if not files:
                return False

            # Step 6: Generate action plan
            plan = self._generate_plan(
                source_path=source_path,
                library=library,
                metadata=metadata,
                files=files,
                preserve=preserve,
            )

            # Step 7: Display plan and confirm
            if not self._confirm_plan(plan, force):
                self.console.print("[yellow]Adoption cancelled.[/yellow]")
                return False

            # Step 8: Execute plan
            success = self._execute_plan(plan)

            if success:
                self.console.print("\n[bold green]✓ Movie adopted successfully![/bold green]")
                self.console.print(f"Location: {plan.movie_folder}")

            return success

        except ProviderError as e:
            self.console.print(f"[red]Metadata provider error:[/red] {e}")
            return False
        except MoError as e:
            self.console.print(f"[red]Error:[/red] {e}")
            return False
        except Exception as e:
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
        movie_libraries = [
            lib for lib in self.library_manager.list()
            if lib.library_type == "movie"
        ]

        if not movie_libraries:
            raise MoError(
                "No movie libraries configured. "
                "Run: mo library add <name> movie <path>"
            )

        if library_name:
            # Use specified library
            return self.library_manager.get(library_name)

        if len(movie_libraries) == 1:
            # Auto-select single library
            lib = movie_libraries[0]
            if self.verbose:
                self.console.print(f"[dim]Using library: {lib.name}[/dim]")
            return lib

        # Multiple libraries - need to prompt
        self.console.print("\n[bold]Multiple movie libraries found:[/bold]")
        table = Table()
        table.add_column("#", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Path")

        for idx, lib in enumerate(movie_libraries, 1):
            table.add_row(str(idx), lib.name, str(lib.path))

        self.console.print(table)

        try:
            choice = prompt("\nSelect library (number): ", default="1").strip()
            index = int(choice) - 1
            if 0 <= index < len(movie_libraries):
                return movie_libraries[index]
            else:
                raise MoError("Invalid library selection")
        except (ValueError, KeyboardInterrupt, EOFError):
            raise MoError("Library selection cancelled")

    def _parse_source_path(self, source_path: Path) -> tuple[str, Optional[int]]:
        """Extract title and year hints from source path.

        Args:
            source_path: Path to parse

        Returns:
            tuple[str, Optional[int]]: (title, year)
        """
        # Try parsing the directory name or filename
        name = source_path.name if source_path.is_file() else source_path.name

        result = parse_movie_filename(name)
        title = result.title if result else name
        year = result.year if result else None

        if self.verbose:
            self.console.print(f"[dim]Parsed from path - Title: {title}, Year: {year}[/dim]")

        return title, year

    def _search_metadata(
        self, title: str, year: Optional[int]
    ) -> Optional[SearchResult]:
        """Interactive metadata search.

        Args:
            title: Title hint
            year: Optional year hint

        Returns:
            SearchResult | None: Selected result or None if cancelled
        """
        self.console.print("\n[bold cyan]Step 1: Search for Movie Metadata[/bold cyan]")

        result = self.search.search_and_select(
            search_func=self.tmdb.search_movie,
            initial_title=title,
            year=year,
            media_type="movie",
        )

        if result and not self.search.confirm_selection(result):
            return None

        return result

    def _get_full_metadata(self, search_result: SearchResult) -> Optional[MovieMetadata]:
        """Fetch complete metadata for selected movie.

        Args:
            search_result: Search result to get metadata for

        Returns:
            MovieMetadata | None: Full metadata or None on error
        """
        self.console.print("\n[dim]Fetching complete metadata...[/dim]")

        try:
            metadata = self.tmdb.get_movie(search_result.id)

            if self.verbose:
                self.console.print(f"[dim]Fetched metadata for: {metadata.title} ({metadata.year})[/dim]")
                self.console.print(f"[dim]Runtime: {metadata.runtime} min[/dim]")
                self.console.print(f"[dim]Genres: {', '.join(metadata.genres or [])}[/dim]")

            return metadata

        except ProviderError as e:
            self.console.print(f"[red]Failed to fetch metadata:[/red] {e}")
            return None

    def _identify_files(self, source_path: Path) -> Optional[Dict[str, List[Path]]]:
        """Identify and categorize files in source directory.

        Args:
            source_path: Source path to scan

        Returns:
            dict[str, list[Path]] | None: Categorized files or None if cancelled
        """
        self.console.print("\n[bold cyan]Step 2: Identify Files[/bold cyan]")

        if source_path.is_file():
            # Single file - treat as main movie file
            files = {"main": [source_path], "extras": [], "subtitles": [], "other": []}
        else:
            # Directory - scan for files
            all_files = list(source_path.rglob("*"))
            all_files = [f for f in all_files if f.is_file()]

            # Categorize files
            scan_result = self.scanner.scan_directory(source_path)

            # Find main video file (largest)
            video_files = [vf.path for vf in scan_result.video_files]
            main_file = max(video_files, key=lambda f: f.stat().st_size) if video_files else None

            # Categorize
            files = {
                "main": [main_file] if main_file else [],
                "extras": [],
                "subtitles": [],
                "other": [],
            }

            for file in all_files:
                if file == main_file:
                    continue

                # Check file type
                suffix = file.suffix.lower()
                if suffix in [".srt", ".sub", ".idx", ".ass", ".ssa"]:
                    files["subtitles"].append(file)
                elif suffix in [".mkv", ".mp4", ".avi", ".m4v", ".mov"]:
                    # Additional video files - likely extras
                    files["extras"].append(file)
                elif suffix in [".nfo", ".jpg", ".png", ".txt"]:
                    # Metadata/art files - include as "other"
                    files["other"].append(file)

        # Display identified files
        table = Table(title="Identified Files")
        table.add_column("Type", style="cyan")
        table.add_column("File", style="bold")
        table.add_column("Size")

        for file_type, file_list in files.items():
            for file in file_list:
                size = file.stat().st_size / (1024 * 1024)  # MB
                table.add_row(
                    file_type.capitalize(),
                    file.name,
                    f"{size:.1f} MB",
                )

        self.console.print(table)

        # Confirm main file
        if not files["main"]:
            self.console.print("[red]No main video file found![/red]")
            return None

        try:
            confirm = prompt(
                f"\nConfirm '{files['main'][0].name}' as main movie file? [Y/n]: ",
                default="y"
            ).strip().lower()

            if confirm not in ("y", "yes", ""):
                self.console.print("[yellow]File identification cancelled.[/yellow]")
                return None

        except (KeyboardInterrupt, EOFError):
            return None

        return files

    def _generate_plan(
        self,
        source_path: Path,
        library: Library,
        metadata: MovieMetadata,
        files: Dict[str, List[Path]],
        preserve: bool,
    ) -> AdoptionPlan:
        """Generate action plan for adoption.

        Args:
            source_path: Source path
            library: Target library
            metadata: Movie metadata
            files: Categorized files
            preserve: Whether to preserve originals

        Returns:
            AdoptionPlan: Complete action plan
        """
        self.console.print("\n[bold cyan]Step 3: Generate Action Plan[/bold cyan]")

        # Determine movie folder name
        title = sanitize_filename(metadata.title)
        year = metadata.year or ""
        folder_name = f"{title} ({year})" if year else title
        movie_folder = library.path / folder_name

        # Collect actions
        actions: List[FileAction] = []

        # Create movie directory
        actions.append(FileAction(
            action="create_dir",
            destination=movie_folder,
        ))

        # Main movie file
        if files["main"]:
            main_file = files["main"][0]
            main_extension = main_file.suffix
            main_dest = movie_folder / f"{folder_name}{main_extension}"

            actions.append(FileAction(
                action="copy" if preserve else "move",
                source=main_file,
                destination=main_dest,
                file_type="main",
            ))

        # Generate NFO
        nfo_content = self.nfo_generator.generate(metadata)
        nfo_path = movie_folder / "movie.nfo"

        actions.append(FileAction(
            action="write_nfo",
            destination=nfo_path,
            content=nfo_content,
        ))

        # Extras (if any)
        if files["extras"]:
            extras_dir = movie_folder / "extras"
            actions.append(FileAction(
                action="create_dir",
                destination=extras_dir,
            ))

            for extra_file in files["extras"]:
                extra_dest = extras_dir / extra_file.name
                actions.append(FileAction(
                    action="copy" if preserve else "move",
                    source=extra_file,
                    destination=extra_dest,
                    file_type="extra",
                ))

        # Subtitles
        if files["subtitles"]:
            for sub_file in files["subtitles"]:
                sub_dest = movie_folder / sub_file.name
                actions.append(FileAction(
                    action="copy" if preserve else "move",
                    source=sub_file,
                    destination=sub_dest,
                    file_type="subtitle",
                ))

        return AdoptionPlan(
            source_path=source_path,
            library=library,
            metadata=metadata,
            actions=actions,
            movie_folder=movie_folder,
            preserve_originals=preserve,
        )

    def _confirm_plan(self, plan: AdoptionPlan, force: bool) -> bool:
        """Display action plan and get confirmation.

        Args:
            plan: Action plan to confirm
            force: Skip confirmation if True

        Returns:
            bool: True if confirmed, False otherwise
        """
        self.console.print("\n[bold cyan]Action Plan[/bold cyan]")

        # Display destination
        self.console.print(f"\n[bold]Destination:[/bold] {plan.movie_folder}")
        self.console.print(f"[bold]Library:[/bold] {plan.library.name}")
        self.console.print(f"[bold]Mode:[/bold] {'Copy' if plan.preserve_originals else 'Move'}")

        # Build tree view of actions
        tree = Tree("[bold]Actions:[/bold]")

        for action in plan.actions:
            if action.action == "create_dir":
                tree.add(f"[cyan]Create directory:[/cyan] {action.destination.name}")
            elif action.action in ("move", "copy"):
                action_verb = "Copy" if action.action == "copy" else "Move"
                tree.add(
                    f"[yellow]{action_verb}:[/yellow] {action.source.name} → {action.destination.name}"
                )
            elif action.action == "write_nfo":
                tree.add(f"[green]Write NFO:[/green] {action.destination.name}")

        self.console.print(tree)

        # Check for conflicts
        if plan.movie_folder.exists():
            self.console.print(f"\n[yellow]Warning:[/yellow] Destination folder already exists!")
            if not force:
                try:
                    overwrite = prompt("Overwrite existing files? [y/N]: ", default="n").strip().lower()
                    if overwrite not in ("y", "yes"):
                        return False
                except (KeyboardInterrupt, EOFError):
                    return False

        # Final confirmation
        if force or self.dry_run:
            return True

        try:
            confirm = prompt("\nProceed with adoption? [Y/n]: ", default="y").strip().lower()
            return confirm in ("y", "yes", "")
        except (KeyboardInterrupt, EOFError):
            return False

    def _execute_plan(self, plan: AdoptionPlan) -> bool:
        """Execute the action plan.

        Args:
            plan: Action plan to execute

        Returns:
            bool: True if successful, False otherwise
        """
        if self.dry_run:
            self.console.print("\n[yellow]Dry run - no actions performed[/yellow]")
            return True

        self.console.print("\n[bold cyan]Executing Plan...[/bold cyan]")

        # Create action log
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "movie_adoption",
            "plan": plan.to_dict(),
            "results": [],
        }

        try:
            for action in plan.actions:
                if action.action == "create_dir":
                    action.destination.mkdir(parents=True, exist_ok=True)
                    log_entry["results"].append({
                        "action": "create_dir",
                        "path": str(action.destination),
                        "status": "success",
                    })
                    if self.verbose:
                        self.console.print(f"[dim]Created: {action.destination}[/dim]")

                elif action.action == "move":
                    # Move file
                    action.destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(action.source), str(action.destination))
                    log_entry["results"].append({
                        "action": "move",
                        "source": str(action.source),
                        "destination": str(action.destination),
                        "status": "success",
                    })
                    if self.verbose:
                        self.console.print(f"[dim]Moved: {action.source.name} → {action.destination}[/dim]")

                elif action.action == "copy":
                    # Copy file
                    action.destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(action.source), str(action.destination))
                    log_entry["results"].append({
                        "action": "copy",
                        "source": str(action.source),
                        "destination": str(action.destination),
                        "status": "success",
                    })
                    if self.verbose:
                        self.console.print(f"[dim]Copied: {action.source.name} → {action.destination}[/dim]")

                elif action.action == "write_nfo":
                    # Write NFO file
                    action.destination.parent.mkdir(parents=True, exist_ok=True)
                    action.destination.write_text(action.content, encoding="utf-8")
                    log_entry["results"].append({
                        "action": "write_nfo",
                        "path": str(action.destination),
                        "status": "success",
                    })
                    if self.verbose:
                        self.console.print(f"[dim]Wrote NFO: {action.destination.name}[/dim]")

            # Write log file
            log_filename = f".mo_action_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            log_path = Path.cwd() / log_filename

            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_entry, f, indent=2)

            self.console.print(f"\n[dim]Action log: {log_path}[/dim]")

            return True

        except Exception as e:
            self.console.print(f"\n[red]Error during execution:[/red] {e}")
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
                pass

            return False
