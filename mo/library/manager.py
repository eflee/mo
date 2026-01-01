"""Library management for media libraries.

Handles adding, removing, and querying media libraries.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional

from mo.config import Config
from mo.utils.errors import ValidationError

# Library type constants (DRY - single source of truth)
LibraryType = Literal["movie", "show"]
VALID_LIBRARY_TYPES = {"movie", "show"}


@dataclass
class Library:
    """
    Represents a media library.

    Single Responsibility: Data structure for library information.
    """

    name: str
    library_type: LibraryType
    path: Path

    def __post_init__(self):
        """Validate library after initialization."""
        if self.library_type not in VALID_LIBRARY_TYPES:
            raise ValidationError(
                f"Invalid library type '{self.library_type}'. "
                f"Must be one of: {', '.join(VALID_LIBRARY_TYPES)}"
            )

        if not isinstance(self.path, Path):
            self.path = Path(self.path)


class LibraryManager:
    """
    Manages media libraries.

    Single Responsibility: Handles library operations (add, remove, list, get).
    """

    def __init__(self, config: Config):
        """
        Initialize library manager.

        Args:
            config: Configuration instance
        """
        self._config = config

    def add(
        self, name: str, library_type: LibraryType, path: Path, save: bool = True
    ) -> Library:
        """
        Add a new library.

        Single Responsibility: Only handles adding a library.

        Args:
            name: Library name
            library_type: Type of library ('movie' or 'show')
            path: Root directory path for the library
            save: Whether to save to config immediately (default: True)

        Returns:
            Library: The created library

        Raises:
            ValidationError: If library is invalid or already exists
        """
        # Validate library type
        if library_type not in VALID_LIBRARY_TYPES:
            raise ValidationError(
                f"Invalid library type '{library_type}'. "
                f"Must be one of: {', '.join(VALID_LIBRARY_TYPES)}"
            )

        # Check for duplicate name
        if self._library_exists(name):
            raise ValidationError(
                f"Library '{name}' already exists. Use a different name."
            )

        # Validate path
        if not isinstance(path, Path):
            path = Path(path)

        if not path.exists():
            raise ValidationError(
                f"Library path does not exist: {path}\n"
                f"Please create the directory first."
            )

        if not path.is_dir():
            raise ValidationError(f"Library path must be a directory: {path}")

        # Create library
        library = Library(name=name, library_type=library_type, path=path)

        # Add to config
        self._config.set("libraries", name, str(path))
        self._config.set("library_types", name, library_type)

        if save:
            self._config.save()

        return library

    def remove(self, name: str, save: bool = True) -> None:
        """
        Remove a library.

        Single Responsibility: Only handles removing a library.

        Args:
            name: Library name to remove
            save: Whether to save to config immediately (default: True)

        Raises:
            ValidationError: If library doesn't exist
        """
        if not self._library_exists(name):
            raise ValidationError(f"Library '{name}' does not exist")

        self._config.remove_library(name)

        if save:
            self._config.save()

    def get(self, name: str) -> Library:
        """
        Get a library by name.

        Single Responsibility: Only retrieves a library.

        Args:
            name: Library name

        Returns:
            Library: The library

        Raises:
            ValidationError: If library doesn't exist
        """
        libraries = self._config.get_libraries()
        types = self._config.get_library_types()

        if name not in libraries:
            raise ValidationError(f"Library '{name}' does not exist")

        library_type = types.get(name)
        if not library_type:
            raise ValidationError(
                f"Library '{name}' is missing type configuration. "
                f"Please check your config file."
            )

        return Library(
            name=name, library_type=library_type, path=Path(libraries[name])
        )

    def list(self) -> List[Library]:
        """
        List all libraries.

        Single Responsibility: Only retrieves all libraries.

        Returns:
            List[Library]: List of all configured libraries
        """
        libraries = self._config.get_libraries()
        types = self._config.get_library_types()

        result = []
        for name, path in libraries.items():
            library_type = types.get(name)
            if library_type:  # Skip libraries with missing type
                result.append(
                    Library(name=name, library_type=library_type, path=Path(path))
                )

        return result

    def _library_exists(self, name: str) -> bool:
        """
        Check if a library exists.

        Single Responsibility: Only checks existence.

        Args:
            name: Library name

        Returns:
            bool: True if library exists
        """
        libraries = self._config.get_libraries()
        return name in libraries

    def get_library_info(self, name: str) -> Dict[str, str]:
        """
        Get detailed library information.

        Single Responsibility: Only formats library info for display.

        Args:
            name: Library name

        Returns:
            Dict[str, str]: Library information

        Raises:
            ValidationError: If library doesn't exist
        """
        library = self.get(name)

        info = {
            "Name": library.name,
            "Type": library.library_type,
            "Path": str(library.path),
            "Exists": "Yes" if library.path.exists() else "No",
        }

        # Add directory stats if path exists
        if library.path.exists():
            try:
                # Count immediate subdirectories (not recursive)
                subdirs = [
                    p for p in library.path.iterdir() if p.is_dir()
                ]
                info["Items"] = str(len(subdirs))
            except PermissionError:
                info["Items"] = "Permission denied"

        return info
