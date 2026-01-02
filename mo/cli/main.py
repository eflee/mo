"""Main CLI entry point for mo.

Implements git-like command structure:
- mo library (add|remove|info)
- mo adopt (movie|show)
- mo config (set|list)
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from mo.config import Config
from mo.library import LibraryManager
from mo.utils.errors import ConfigError, MoError

console = Console()


def get_config() -> Optional[Config]:
    """
    Get configuration instance with error handling.


    Returns:
        Config | None: Config instance or None if error
    """
    try:
        return Config()
    except ConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        return None


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making changes",
)
@click.option(
    "--preserve",
    "-p",
    is_flag=True,
    help="Preserve original files (copy instead of move)",
)
@click.pass_context
def cli(ctx, verbose: bool, dry_run: bool, preserve: bool):
    """mo.py - Media Organizer for Jellyfin-compatible media libraries."""
    # Store global options in context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["dry_run"] = dry_run
    ctx.obj["preserve"] = preserve


# ============================================================================
# Library Commands
# ============================================================================


@cli.group()
def library():
    """Manage media libraries."""
    pass


@library.command()
@click.argument("name")
@click.argument("type", type=click.Choice(["movie", "show"]))
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def add(ctx, name: str, type: str, path: Path):
    """
    Add a new library.

    NAME: Library name
    TYPE: Library type (movie or show)
    PATH: Root directory path
    """
    config = get_config()
    if config is None:
        sys.exit(1)

    manager = LibraryManager(config)

    try:
        if ctx.obj.get("dry_run"):
            console.print(f"[yellow]Dry run:[/yellow] Would add library '{name}'")
            console.print(f"  Type: {type}")
            console.print(f"  Path: {path}")
        else:
            library = manager.add(name, type, path)
            console.print(f"[green]✓[/green] Added library '{library.name}'")
            console.print(f"  Type: {library.library_type}")
            console.print(f"  Path: {library.path}")

    except MoError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@library.command()
@click.argument("name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def remove(ctx, name: str, force: bool):
    """
    Remove a library.

    NAME: Library name to remove
    """
    config = get_config()
    if config is None:
        sys.exit(1)

    manager = LibraryManager(config)

    try:
        # Get library info before removal
        lib = manager.get(name)

        # Confirm removal unless --force
        if not force and not ctx.obj.get("dry_run"):
            console.print(f"[yellow]Warning:[/yellow] About to remove library '{name}'")
            console.print(f"  Type: {lib.library_type}")
            console.print(f"  Path: {lib.path}")

            if not click.confirm("Are you sure?"):
                console.print("Cancelled.")
                sys.exit(0)

        if ctx.obj.get("dry_run"):
            console.print(f"[yellow]Dry run:[/yellow] Would remove library '{name}'")
        else:
            manager.remove(name)
            console.print(f"[green]✓[/green] Removed library '{name}'")

    except MoError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@library.command()
@click.argument("name", required=False)
def info(name: Optional[str]):
    """
    Display library information.

    NAME: Library name (optional). If not provided, lists all libraries.
    """
    config = get_config()
    if config is None:
        sys.exit(1)

    manager = LibraryManager(config)

    try:
        if name:
            # Show single library info
            info_dict = manager.get_library_info(name)

            table = Table(title=f"Library: {name}", show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            for key, value in info_dict.items():
                table.add_row(key, value)

            console.print(table)

        else:
            # List all libraries
            libraries = manager.list()

            if not libraries:
                console.print("[yellow]No libraries configured.[/yellow]")
                console.print("Use 'mo library add' to add a library.")
                sys.exit(0)

            table = Table(title="Configured Libraries")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Path")

            for lib in libraries:
                table.add_row(lib.name, lib.library_type, str(lib.path))

            console.print(table)

    except MoError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


# ============================================================================
# Config Commands
# ============================================================================


@cli.group()
def config():
    """Manage configuration."""
    pass


@config.command()
@click.argument("key")
@click.argument("value")
@click.option(
    "--target",
    type=click.Choice(["local", "user"]),
    help="Target config location (local or user)",
)
@click.pass_context
def set(ctx, key: str, value: str, target: Optional[str]):
    """
    Set a configuration value.

    KEY: Configuration key in format 'section.key'
    VALUE: Value to set
    """
    cfg = get_config()
    if cfg is None:
        sys.exit(1)

    try:
        # Parse section.key format
        if "." not in key:
            console.print(
                "[red]Error:[/red] Key must be in format 'section.key' "
                "(e.g., 'metadata.tmdb_api_key')"
            )
            sys.exit(1)

        section, key_name = key.rsplit(".", 1)

        if ctx.obj.get("dry_run"):
            console.print(f"[yellow]Dry run:[/yellow] Would set {section}.{key_name} = {value}")
        else:
            cfg.set(section, key_name, value)
            cfg.save(target=target)
            console.print(f"[green]✓[/green] Set {section}.{key_name} = {value}")

    except MoError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@config.command("list")
@click.option(
    "--section",
    "-s",
    help="Show only specific section",
)
def list_config(section: Optional[str]):
    """Display configuration values."""
    cfg = get_config()
    if cfg is None:
        sys.exit(1)

    try:
        SENSITIVE_KEYS = {"api_key", "password", "token", "secret"}

        if section:
            # Show specific section
            items = cfg.get_all(section)

            if not items:
                console.print(f"[yellow]Section '{section}' is empty or does not exist.[/yellow]")
                sys.exit(0)

            table = Table(title=f"Configuration: {section}")
            table.add_column("Key", style="cyan")
            table.add_column("Value")

            for key, value in items.items():
                # Redact sensitive values
                if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
                    value = "********"
                table.add_row(key, value)

            console.print(table)

        else:
            # Show all sections
            sections = cfg.get_sections()

            if not sections:
                console.print("[yellow]Configuration is empty.[/yellow]")
                sys.exit(0)

            for sec in sections:
                items = cfg.get_all(sec)

                table = Table(title=f"[{sec}]")
                table.add_column("Key", style="cyan")
                table.add_column("Value")

                for key, value in items.items():
                    # Redact sensitive values
                    if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
                        value = "********"
                    table.add_row(key, value)

                console.print(table)
                console.print()  # Blank line between sections

    except MoError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


# ============================================================================
# Adopt Commands
# ============================================================================


@cli.group()
def adopt():
    """Adopt media files into libraries."""
    pass


@adopt.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "--library",
    "-l",
    help="Library name (auto-selects if only one movie library exists)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompts",
)
@click.pass_context
def movie(ctx, directory: Optional[Path], library: Optional[str], force: bool):
    """
    Adopt a movie file or directory.

    DIRECTORY: Path to movie file or directory (defaults to current directory)
    """
    from mo.workflows import MovieAdoptionWorkflow

    # Use current directory if not specified
    source_path = directory or Path.cwd()

    config = get_config()
    if config is None:
        sys.exit(1)

    try:
        workflow = MovieAdoptionWorkflow(
            config=config,
            console=console,
            verbose=ctx.obj.get("verbose", False),
            dry_run=ctx.obj.get("dry_run", False),
        )

        success = workflow.adopt(
            source_path=source_path,
            library_name=library,
            preserve=ctx.obj.get("preserve", False),
            force=force,
        )

        sys.exit(0 if success else 1)

    except MoError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@adopt.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "--library",
    "-l",
    help="Library name (auto-selects if only one show library exists)",
)
@click.option(
    "--season",
    "-s",
    type=int,
    help="Season number (for adopting a single season)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompts",
)
@click.pass_context
def show(ctx, directory: Optional[Path], library: Optional[str], season: Optional[int], force: bool):
    """
    Adopt a TV show directory.

    DIRECTORY: Path to TV show directory (defaults to current directory)
    """
    from mo.workflows import TVShowAdoptionWorkflow

    # Use current directory if not specified
    source_path = directory or Path.cwd()

    config = get_config()
    if config is None:
        sys.exit(1)

    try:
        workflow = TVShowAdoptionWorkflow(
            config=config,
            console=console,
            verbose=ctx.obj.get("verbose", False),
            dry_run=ctx.obj.get("dry_run", False),
        )

        success = workflow.adopt(
            source_path=source_path,
            library_name=library,
            preserve=ctx.obj.get("preserve", False),
            force=force,
            season_filter=season,
        )

        sys.exit(0 if success else 1)

    except MoError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
