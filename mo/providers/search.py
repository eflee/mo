"""Interactive search interface for metadata providers.

Provides a user-friendly interface for searching metadata and selecting
the correct match from search results.
"""

from difflib import SequenceMatcher
from typing import List, Optional

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.table import Table

from mo.providers.base import SearchResult


class InteractiveSearch:
    """Interactive search interface with fuzzy matching and relevance scoring."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize interactive search.

        Args:
            console: Rich console for output (creates new one if not provided)
        """
        self.console = console or Console()

    def search_and_select(
        self,
        search_func,
        initial_title: str,
        year: Optional[int] = None,
        media_type: str = "movie",
    ) -> Optional[SearchResult]:
        """Interactive search with result selection.

        Args:
            search_func: Function to call for searching (takes title and year)
            initial_title: Initial search title
            year: Optional year for filtering
            media_type: Type of media ("movie" or "tv")

        Returns:
            SearchResult | None: Selected result or None if cancelled
        """
        current_title = initial_title
        current_year = year

        while True:
            # Perform search
            self.console.print(f"\n[bold]Searching for {media_type}: {current_title}[/bold]")
            if current_year:
                self.console.print(f"[dim]Year: {current_year}[/dim]")

            try:
                results = search_func(current_title, current_year)
            except Exception as e:
                self.console.print(f"[red]Search failed: {e}[/red]")
                return None

            if not results:
                self.console.print("[yellow]No results found.[/yellow]")

                # Ask to try a new search
                try:
                    choice = prompt(
                        "Enter new search term (or 'q' to quit): ",
                        default="",
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    return None

                if choice.lower() == "q" or not choice:
                    return None

                current_title = choice
                continue

            # Apply fuzzy matching and relevance scoring
            scored_results = self._score_results(results, current_title, current_year)

            # Display results
            selected = self._display_and_select(scored_results, current_title)

            if selected == "new":
                # User wants to search again
                try:
                    new_search = prompt(
                        "Enter new search term (or 'q' to quit): ",
                        default=current_title,
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    return None

                if new_search.lower() == "q" or not new_search:
                    return None

                current_title = new_search
                continue

            elif selected is None:
                # User cancelled
                return None

            else:
                # User selected a result
                return selected

    def _score_results(
        self, results: List[SearchResult], search_title: str, search_year: Optional[int]
    ) -> List[SearchResult]:
        """Apply relevance scoring to search results.

        Args:
            results: Search results to score
            search_title: Original search title
            search_year: Optional search year

        Returns:
            List[SearchResult]: Results with updated relevance scores, sorted by score
        """
        scored = []

        for result in results:
            # Start with provider's relevance score (if available)
            score = result.relevance_score

            # Add fuzzy matching score for title (0.0 to 1.0)
            title_similarity = SequenceMatcher(
                None, search_title.lower(), result.title.lower()
            ).ratio()
            score += title_similarity * 100  # Weight title match heavily

            # Boost score if year matches exactly
            if search_year and result.year == search_year:
                score += 50

            # Slight penalty if year is provided but doesn't match
            elif search_year and result.year and abs(result.year - search_year) > 0:
                score -= 10 * abs(result.year - search_year)

            # Create new result with updated score
            scored_result = SearchResult(
                provider=result.provider,
                id=result.id,
                title=result.title,
                year=result.year,
                plot=result.plot,
                rating=result.rating,
                poster_url=result.poster_url,
                media_type=result.media_type,
                relevance_score=score,
                raw_data=result.raw_data,
            )
            scored.append(scored_result)

        # Sort by relevance score (descending)
        scored.sort(key=lambda r: r.relevance_score, reverse=True)

        return scored

    def _display_and_select(
        self, results: List[SearchResult], search_title: str
    ) -> Optional[SearchResult] | str:
        """Display results and prompt user to select one.

        Args:
            results: Search results to display
            search_title: Original search title for context

        Returns:
            SearchResult | None | "new": Selected result, None if cancelled, or "new" for new search
        """
        # Create table
        table = Table(title=f"Search Results (sorted by relevance)")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Title", style="bold")
        table.add_column("Year", style="yellow", width=6)
        table.add_column("Rating", style="green", width=8)
        table.add_column("Plot", style="dim", max_width=50)

        # Add rows (limit to top 10 results)
        display_results = results[:10]
        for idx, result in enumerate(display_results, 1):
            year_str = str(result.year) if result.year else "N/A"
            rating_str = f"{result.rating:.1f}" if result.rating else "N/A"
            plot_str = result.plot[:47] + "..." if result.plot and len(result.plot) > 50 else (result.plot or "N/A")

            table.add_row(
                str(idx),
                result.title,
                year_str,
                rating_str,
                plot_str,
            )

        self.console.print(table)

        # Prompt for selection
        self.console.print("\n[bold]Options:[/bold]")
        self.console.print("  [cyan]1-10[/cyan]: Select a result")
        self.console.print("  [cyan]n[/cyan]: Enter new search term")
        self.console.print("  [cyan]q[/cyan]: Cancel and quit")

        try:
            choice = prompt("\nYour choice: ", default="1").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return None

        # Handle choice
        if choice == "q" or not choice:
            return None
        elif choice == "n":
            return "new"
        else:
            try:
                index = int(choice) - 1
                if 0 <= index < len(display_results):
                    return display_results[index]
                else:
                    self.console.print("[red]Invalid selection.[/red]")
                    return None
            except ValueError:
                self.console.print("[red]Invalid input.[/red]")
                return None

    def confirm_selection(self, result: SearchResult) -> bool:
        """Confirm a selected result with the user.

        Args:
            result: Result to confirm

        Returns:
            bool: True if confirmed, False otherwise
        """
        self.console.print("\n[bold green]Selected:[/bold green]")
        self.console.print(f"  Title: {result.title}")
        if result.year:
            self.console.print(f"  Year: {result.year}")
        if result.rating:
            self.console.print(f"  Rating: {result.rating:.1f}")
        if result.plot:
            plot = result.plot[:200] + "..." if len(result.plot) > 200 else result.plot
            self.console.print(f"  Plot: {plot}")

        try:
            confirm = prompt("\nConfirm this selection? [Y/n]: ", default="y").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return False

        return confirm in ("y", "yes", "")


def fuzzy_match_score(text1: str, text2: str) -> float:
    """Calculate fuzzy matching score between two strings.

    Args:
        text1: First string
        text2: Second string

    Returns:
        float: Similarity score (0.0 to 1.0)
    """
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
