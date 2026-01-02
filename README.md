# mo.py - Media Organizer

An interactive command-line tool for organizing movie and TV show files into the proper directory structure and filenames with nfo metadata. `mo.py` migrates files from a landing directory into a configured library directories. It's intended to be a filesystem based solution for media organization for peopel who live in the terminal and are pedantic about organization. 

## Overview

`mo.py` helps you transform messy media files into properly organized, metadata-rich file systems based libraries. It's intended to work adopts the same organzation strucutre as Jellyfin for compatability. 
I wrote this as a way to agnostically organize media using online metadata sources to name, match,sort and organize files easily. 
It handles the complexity and interactively works with the user to pull files into evergreen libraries.

## Key Features

- **Interactive metadata search**: Point mo at a directory and adopt that directory into a library by interactively searching for the correct movie or TV show.
- **Intelligent file matching**: Uses filename patterns and media file duration to match episodes with files
- **Jellyfin-compatible output**: Creates proper folder structures and file naming conventions
- **NFO metadata generation**: Writes complete NFO files with metadata from online sources
- **Handles edge cases**: Interactive prompts help you deal with bonus content, extras, and mismatched files
- **Partial TV seasons**: Works with incomplete TV show collections

## How It Works

mo.py uses an **interactive, multi-step workflow** where you confirm each decision before any files are modified. At the end, you review and approve the complete action plan before execution.

### For Movies

**Step 1: Metadata Search**
- mo.py analyzes the filename/folder name and searches metadata providers
- Displays search results with title, year, and plot summary
- You select the correct match OR provide a new search term
- Repeat until you confirm the correct movie

**Step 2: File Identification**
- mo.py scans all files in the directory
- For each file, you confirm its role:
  - Main movie file
  - Extras (behind-the-scenes, deleted scenes, etc.)
  - Subtitles
  - Other supporting files
- You decide which files to adopt and which to leave behind

**Step 3: Final Plan Review**
- mo.py presents a compact action plan showing:
  - Directory structure to be created
  - All file moves and renames
  - NFO files to be generated
  - Any conflicts/overwrites (requires explicit confirmation)
- You approve or cancel the entire operation
- If approved, all actions are executed and logged

**Result:**
```
Movie Name (Year)/
├── Movie Name (Year).mkv
├── movie.nfo
└── extras/
    └── Behind the Scenes.mkv
```

### For TV Shows

**Step 1: Show Metadata Search**
- mo.py analyzes the folder name and searches metadata providers
- Displays search results with title, year, and summary
- You select the correct match OR provide a new search term
- Repeat until you confirm the correct show

**Step 2: Season Identification**
- mo.py identifies seasons by:
  - Subdirectory names (e.g., `Season 01/`, `S01/`)
  - Filename prefixes (e.g., `S01E01`, `S02E03`)
- For each detected season, you confirm:
  - Season number is correct
  - Files belong to this season
- You can override or manually specify season numbers

**Step 3: Episode Matching (per season)**
- mo.py analyzes each season's files using:
  - Filename patterns (S##E## notation)
  - Media file duration compared to episode runtime
  - Confidence scoring
- Displays proposed matches for the season:
  - File → Episode mapping with confidence level
  - Episode title, number, and air date
- For each season, you can:
  - Accept all matches
  - Override individual matches
  - Manually map ambiguous files
  - Mark extraneous files to leave behind (extras, samples, etc.)

**Step 4: Final Plan Review**
- mo.py presents a compact action plan showing:
  - Directory structure to be created
  - All file moves and renames (grouped by season)
  - NFO files to be generated (series + all episodes)
  - Any conflicts/overwrites (requires explicit confirmation)
- You approve or cancel the entire operation
- If approved, all actions are executed and logged

**Result:**
```
Show Name (Year)/
├── tvshow.nfo
├── Season 01/
│   ├── Show Name S01E01.mkv
│   ├── Show Name S01E01.nfo
│   ├── Show Name S01E02.mkv
│   └── Show Name S01E02.nfo
└── Season 02/
    ├── Show Name S02E01.mkv
    └── Show Name S02E01.nfo
```

### Action Logging

Every adoption operation:
- Creates a timestamped log file in the **current working directory** (e.g., `.mo_action_log_20260101_143022.json`)
- Records all actions taken:
  - Original file paths
  - Destination paths
  - Directories created
  - NFO files written
  - Timestamps
  - Operation mode (move or copy)
- Log can be used to manually reverse operations if needed

## Jellyfin Compatibility

### Folder Structure

mo.py follows Jellyfin's naming conventions ([Movies Documentation](https://jellyfin.org/docs/general/server/media/movies/), [TV Shows Documentation](https://jellyfin.org/docs/general/server/media/shows/)):

**Movies:**
- Format: `Movie Name (Year)/Movie Name (Year).ext`
- Optional: External IDs like `[imdbid-tt1234567]` or `[tmdbid-12345]`
- Each movie in its own folder with matching filename

**TV Shows:**
- Series: `Show Name (Year)/`
- Seasons: `Season 01/`, `Season 02/` (zero-padded, no abbreviations like "S01")
- Episodes: `Show Name S01E01 Episode Title.ext`

### NFO Files

mo.py generates Kodi/Jellyfin-compatible NFO files ([NFO Documentation](https://jellyfin.org/docs/general/server/metadata/nfo/)) containing:

**Common Fields:**
- `title` / `name`: Title of the media
- `originaltitle`: Original title if different
- `sorttitle`: Sort/forced sort name
- `year`: Production year
- `plot` / `overview`: Synopsis/description
- `tagline`: Tagline
- `mpaa`: Content rating (e.g., PG-13, TV-MA)
- `genre`: Genres (can have multiple)
- `studio`: Production studios
- `runtime`: Runtime in minutes
- `aired` / `premiered` / `releasedate`: Release/air date
- `director`, `writer`, `credits`: Crew members
- `actor`: Cast members with role information
- `rating` / `ratings`: User/critic ratings
- `uniqueid`: Provider IDs with type attribute (e.g., `<uniqueid type="imdb">tt1234567</uniqueid>`)

**Movie-Specific Fields:**
- Root element: `<movie>` (or `<musicvideo>`)
- `id`: IMDb ID (legacy, prefer `uniqueid`)
- `set`: Collection information with `<name>` subelement
- `tmdbcolid` attribute on `set` element for TMDB collection ID

**TV Show-Specific Fields (tvshow.nfo):**
- Root element: `<tvshow>`
- `id`: TVDB ID (legacy)
- `episodeguide`: TVDB API endpoint with language
- `status`: Series status (Continuing, Ended, etc.)
- `season`: -1 (placeholder)
- `episode`: -1 (placeholder)

**Episode-Specific Fields:**
- Root element: `<episodedetails>`
- `showtitle`: Series name
- `season`: Season number
- `episode`: Episode number
- `episodenumberend`: Ending episode for multi-episode files
- `aired`: Air date
- Special episode fields for Season 0:
  - `airsafter_season`: Season it airs after
  - `airsbefore_season`: Season it airs before
  - `airsbefore_episode`: Episode it airs before
  - `displayseason`: Display season override
  - `displayepisode`: Display episode override

**NFO File Naming:**
- Movies: `movie.nfo` (in movie folder) OR `<filename>.nfo` (same name as video file)
- TV Shows: `tvshow.nfo` (in series root folder)
- Episodes: `<episode_filename>.nfo` (same name as episode file)
- Seasons: `season.nfo` (optional, in season folder)
- VIDEO_TS: `VIDEO_TS.nfo` (for DVD folders)

### Metadata Sources

mo.py retrieves metadata from the following online sources:

- **[TheMovieDB (TMDB)](https://www.themoviedb.org/)**: Primary source for movies and TV shows
  - Free for non-commercial use
  - Requires [API key registration](https://developer.themoviedb.org/docs/getting-started)
  - Access token obtained from account settings

- **[TheTVDB](https://thetvdb.com/)**: TV show episode data
  - Requires [API key via v4 Dashboard](https://support.thetvdb.com/kb/faq.php?id=81)
  - Free tier available with user subscription model ($12/year per user)
  - Commercial licenses available for larger projects

- **[OMDb API](https://www.omdbapi.com/)**: Supplementary movie data
  - Free tier: [1,000 API calls per day](https://www.omdbapi.com/apikey.aspx)
  - Requires simple registration for API key
  - Rate limits can be removed with optional donation

## Commands

mo.py is organized around a set of commands and subcommands, similar to git.

### Library Management

Libraries are destination repositories where adopted media files are organized. Each library has three components:
- **Name**: A unique identifier for the library
- **Type**: Either `movie` or `show`
- **Root Directory**: The filesystem path where media will be organized

```bash
# Add a new library with name, type, and root directory
mo.py library add <library_name> <movie|show> <root_directory>

# Remove a library
mo.py library remove <library_name>

# Show library information
mo.py library info <library_name>
```

### Adopting Media

The `adopt` command processes media files from a source directory and integrates them into a configured library with proper Jellyfin structure and metadata. The command behavior varies based on the media type:

#### `adopt movie [directory]`
Assumes the target is either:
- A single media file, OR
- A directory containing a single movie (which may include multiple files like extras, behind-the-scenes, etc.)

Uses current directory if `[directory]` is not specified.

#### `adopt show [directory]`
Assumes the target is a directory storing all or part of a TV show. The directory may be:
- Divided into season-based subdirectories (e.g., `Season 01/`, `Season 02/`)
- Organized with season prefixes in filenames (e.g., `S01E01`, `S02E03`)
- A mix of organizational patterns

mo.py intelligently assigns individual media files as episodes using:
- **Duration-based matching**: Compares file length with expected episode runtime
- **Filename hints**: Parses season/episode patterns from filenames

Uses current directory if `[directory]` is not specified.

#### `adopt show --season <n> [directory]`
Assumes the target is a directory storing all or part of a specific season (number provided as `<n>`). This is essentially a partial operation of adopting an entire show, scoped to a single season.

Uses current directory if `[directory]` is not specified.

#### Global Flags

mo.py supports the following global flags for all commands:

- **`--verbose` / `-v`**: Enable verbose output for detailed logging
- **`--dry-run`**: Preview actions without making any changes (shows what would be done)
- **`--preserve` / `-p`**: Preserve original files by copying instead of moving
  - Default behavior: Files are **moved** from source to library
  - With `--preserve`: Files are **copied**, leaving originals intact
  - Action log records the operation mode used

#### Safety and Confirmation

- **Always prompts before overwriting** unless `--force` flag is provided
- **Shows action plan**: `mo.py adopt` always outputs the complete set of actions it will take and confirms with the user before proceeding
- **Operation mode**: By default, files are moved. Use `--preserve` to copy instead

**Examples:**

```bash
# Add a movies library
mo.py library add MyMovies movie ~/movies/

# Adopt a movie from current directory (interactive search and confirmation)
cd /downloads/Inception.2010
mo.py adopt movie

# Adopt a TV show from specified directory
mo.py adopt show /downloads/Breaking.Bad/

# Adopt only season 2 of a show
mo.py adopt show --season 2 /downloads/The.Wire.Season.2

# Force adoption without prompting (use with caution)
mo.py adopt movie --force /downloads/SomeMovie/

# Preserve original files (copy instead of move)
mo.py --preserve adopt movie /downloads/Inception.2010

# Combine flags: verbose output and preserve mode
mo.py -v --preserve adopt show /downloads/Breaking.Bad/

# Dry run to preview actions without making changes
mo.py --dry-run adopt movie /downloads/SomeMovie/
```

## Configuration

mo.py uses a hierarchical configuration system:

1. **Local config** (`.mo.conf` in current directory) - checked first
2. **User config** (`~/.config/mo/config` or platform-specific location) - merged with local config

If neither configuration file exists, mo.py will error and prompt you to create a configuration using the `library` command.

### Configuration Management

```bash
# Configure metadata API keys
mo.py config set tmdb_api_key <your_key>
mo.py config set tvdb_api_key <your_key>
mo.py config set omdb_api_key <your_key>

# View current configuration
mo.py config list

# Set preferences
mo.py config set prefer_tvdb true
```

The configuration file stores:
- Defined libraries (name, type, root directory)
- Metadata provider API keys
- Provider preferences
- File handling preferences

**Example configuration:**

```ini
[libraries]
MyMovies = /media/jellyfin/Movies
MyShows = /media/jellyfin/TV Shows

[library_types]
MyMovies = movie
MyShows = show

[metadata]
tmdb_api_key = your_tmdb_key_here
tvdb_api_key = your_tvdb_key_here
omdb_api_key = your_omdb_key_here
prefer_tvdb = true
```

### Setting Up API Keys

To use mo.py, you'll need to obtain API keys from the metadata providers:

1. **TMDB**: Register at [TMDB Developer Portal](https://developer.themoviedb.org/docs/getting-started) and get your API Read Access Token
2. **TheTVDB**: Create an API key via [TheTVDB v4 Dashboard](https://support.thetvdb.com/kb/faq.php?id=81) (requires account and subscription)
3. **OMDb**: Register at [OMDb API](https://www.omdbapi.com/apikey.aspx) for free tier access

Then configure mo.py with your keys:
```bash
mo.py config set tmdb_api_key <your_key>
mo.py config set tvdb_api_key <your_key>
mo.py config set omdb_api_key <your_key>
```

## Requirements

- Python 3.8+
- Internet connection (for metadata lookup)
- Media files in common formats (MP4, MKV, AVI, etc.)

## Installation

```bash
git clone https://github.com/yourusername/mo.git
cd mo
pip install -r requirements.txt
```

## Migration from Proprietary Format (Temporary)

I have have existing media organized with custom `metadata.json` files, mo.py can:
- Read existing metadata
- Match it with current online sources
- Convert to Jellyfin-compatible NFO format
- Reorganize files into proper structure

This functionality will be temporary until I have fully adopted my library into the new format.

## Reserved Characters

The following characters cannot be used in filenames and will be sanitized:
`< > : " / \ | ? *`

## Additional Jellyfin Compatibility Notes

Based on analysis of the Jellyfin source code, the following additional requirements ensure full compatibility:

### Episode Filename Parsing

Jellyfin uses complex regex patterns to parse episode information from filenames. Key patterns mo.py should support:

- Standard: `S##E##` (e.g., `S01E01`, `S04E11`)
- Alternate: `s##x##` (e.g., `s01x01`)
- Multi-episode: `S01E01-E02-E03` or `S01E01xE02xE03`
- Date-based: For shows organized by air date
- Absolute numbering: For anime (e.g., `Show Name 001.mkv`)

**Important parsing rules from Jellyfin:**
- Seasons 200-1927 and >2500 are invalidated to avoid false positives (e.g., `1920x1080` resolution)
- Series names extracted from filenames are trimmed of `_`, `.`, and `-` characters
- Multi-episode files can use formats like `02x03-04-15` or `S01E23-E24-E26`
- Ending episode numbers are validated to avoid false matches with resolution specs (e.g., `1080p`)

### Season Folder Recognition

Jellyfin recognizes season folders by:
- Exact match: `Season ##` (with optional leading zeros)
- Not abbreviated: `S01` is NOT recognized as a season folder
- Special handling: Season 0 for specials
- If a folder contains episode files with season numbers, it's treated as episodes, not a season folder

### NFO File Location Priority

For movies, Jellyfin checks NFO files in this order:
1. `VIDEO_TS/VIDEO_TS.nfo` (for DVD structures)
2. `movie.nfo` (in movie folder, only for Movie type items)
3. `<foldername>.nfo` (for DVD/BluRay folders)
4. `<filename>.nfo` (same name as video file)

For episodes:
- Only `<filename>.nfo` (must match episode file exactly)

For series:
- Only `tvshow.nfo` in series root directory

### Multi-Episode File Support

Jellyfin supports multiple `<episodedetails>` blocks in a single NFO file for multi-episode files:
- Each episode gets its own `<episodedetails>` block
- Episode names, overviews, and original titles are concatenated with ` / ` separator
- `IndexNumberEnd` is set to the highest episode number

### Provider ID Formats

Jellyfin accepts provider IDs in multiple formats:
- Modern: `<uniqueid type="imdb">tt1234567</uniqueid>`
- Legacy: `<imdb>tt1234567</imdb>` or `<imdbid>tt1234567</imdbid>`
- Aliases: `tmdbid`, `tvdbid`, `imdb_id`, `tmdbcol`, `tmdbcolid`, `collectionnumber`
- Attribute format: `<id IMDB="tt1234567" TMDB="12345">content</id>`

**mo.py should write modern `uniqueid` format but be aware of legacy formats for migration.**

### Special Episode Handling

Season 0 (Specials) episodes require additional metadata:
- Use `airsafter_season`, `airsbefore_season`, `airsbefore_episode` to specify placement
- `displayseason` and `displayepisode` override the display numbering
- These fields help Jellyfin correctly order specials relative to regular episodes

### Path-Based Provider ID Detection

Jellyfin can extract provider IDs directly from folder and filenames using bracket notation. mo.py should optionally support this format:

**Supported Provider IDs in Paths:**
- Movies: `[imdbid-tt1234567]`, `[tmdbid-12345]`
- TV Shows: `[imdbid-tt...]`, `[tvdbid-...]`, `[tmdbid-...]`, `[anidbid-...]`, `[anilistid-...]`, `[anisearchid-...]`

**Examples:**
- `Inception (2010) [imdbid-tt1627792]/Inception (2010).mkv`
- `Breaking Bad (2008) [tvdbid-81189]/tvshow.nfo`

This metadata is extracted using `GetAttributeValue()` during library scanning, so including provider IDs in paths provides a fallback if NFO files are missing or incomplete.

### Content Type Detection

Jellyfin uses several methods to distinguish between movies and TV shows:

**Series Detection:**
- Presence of `tvshow.nfo` in root directory
- Presence of season folders matching `Season ##` pattern
- Presence of episode files with season/episode numbers (S##E##)
- Provider IDs in folder name (imdbid, tvdbid, etc.)

**Movie Detection:**
- Absence of `tvshow.nfo`
- DVD/BluRay folder structure (`VIDEO_TS/`, `BDMV/`)
- Single video file or mixed folder with multiple videos
- Provider IDs in folder/filename (imdbid, tmdbid)

**Sample File Filtering:**
- Files matching regex `\bsample\b` (case-insensitive) are ignored
- mo.py should warn users about sample files and offer to skip them

### Mixed vs Dedicated Folder Logic

Jellyfin's behavior changes based on folder structure:

**Dedicated Movie Folder:**
- Single video file in its own folder
- Movie name uses folder name
- NFO can be `movie.nfo` in folder

**Mixed Folder:**
- Multiple video files in same directory
- Each movie name uses filename (not folder name)
- NFO must be `<filename>.nfo` (not `movie.nfo`)
- mo.py should default to dedicated folders for better organization

### Episode Resolution Context

Jellyfin resolves episodes within a parent context:

**Episode Parent Priority:**
1. If within a `Season ##/` folder → use that season number
2. If directly under series folder → attempt to parse season from filename
3. If season cannot be determined → **default to Season 1**

**mo.py Implications:**
- Always organize episodes into explicit `Season ##/` folders to avoid ambiguity
- Never rely on filename-only season detection
- Warn users if episodes lack clear season information

## Development Setup & Architecture

This section outlines the project structure, dependencies, development tools, and architectural decisions required before starting implementation.

### Project Structure

```
mo/
├── mo.py                      # Main entry point (CLI)
├── README.md                  # This file
├── LICENSE                    # License file
├── requirements.txt           # Python dependencies
├── requirements-dev.txt       # Development dependencies (testing, linting)
├── setup.py                   # Package setup for installation
├── .gitignore                 # Git ignore file
├── pyproject.toml            # Modern Python project config (PEP 518)
├── pytest.ini                # Pytest configuration
├── .mo.conf.example          # Example local config file
│
├── mo/                       # Main package directory
│   ├── __init__.py
│   ├── __main__.py           # Enable `python -m mo`
│   │
│   ├── cli/                  # CLI interface
│   │   ├── __init__.py
│   │   ├── parser.py         # Argument parsing
│   │   ├── commands.py       # Command routing and execution
│   │   └── ui.py             # Interactive prompts, menus, progress indicators
│   │
│   ├── config/               # Configuration management
│   │   ├── __init__.py
│   │   ├── loader.py         # Hierarchical config loading
│   │   ├── manager.py        # Config operations (get, set, list)
│   │   └── schema.py         # Config validation schema
│   │
│   ├── library/              # Library management
│   │   ├── __init__.py
│   │   ├── manager.py        # Library add/remove/info
│   │   └── models.py         # Library data structures
│   │
│   ├── providers/            # Metadata provider integrations
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract base provider
│   │   ├── tmdb.py           # TMDB API client
│   │   ├── tvdb.py           # TheTVDB API client
│   │   ├── omdb.py           # OMDb API client
│   │   ├── cache.py          # Metadata caching layer
│   │   └── search.py         # Unified search interface
│   │
│   ├── parsers/              # Filename and path parsing
│   │   ├── __init__.py
│   │   ├── episode.py        # Episode filename parser (Jellyfin-compatible)
│   │   ├── season.py         # Season folder detection
│   │   ├── movie.py          # Movie filename parser
│   │   ├── provider_id.py    # Provider ID extraction from paths
│   │   └── sanitize.py       # Filename sanitization
│   │
│   ├── media/                # Media file analysis
│   │   ├── __init__.py
│   │   ├── scanner.py        # Directory scanning, file detection
│   │   ├── analyzer.py       # Media metadata extraction (ffprobe)
│   │   └── matcher.py        # Episode matching (duration + filename)
│   │
│   ├── nfo/                  # NFO generation
│   │   ├── __init__.py
│   │   ├── builder.py        # XML builder utilities
│   │   ├── movie.py          # Movie NFO generator
│   │   ├── tvshow.py         # TV show NFO generator
│   │   ├── episode.py        # Episode NFO generator
│   │   └── templates.py      # NFO field templates
│   │
│   ├── workflows/            # Adoption workflows
│   │   ├── __init__.py
│   │   ├── base.py           # Base workflow class
│   │   ├── movie.py          # Movie adoption workflow
│   │   ├── tvshow.py         # TV show adoption workflow
│   │   ├── planner.py        # Action plan generation
│   │   └── executor.py       # File operations and logging
│   │
│   ├── migration/            # Proprietary format migration (temporary)
│   │   ├── __init__.py
│   │   ├── parser.py         # metadata.json parser
│   │   └── converter.py      # Convert to NFO format
│   │
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── logging.py        # Logging configuration
│       ├── validation.py     # Input validation
│       ├── platform.py       # Platform-specific helpers
│       └── errors.py         # Custom exception classes
│
└── tests/                    # Test suite
    ├── __init__.py
    ├── conftest.py           # Pytest fixtures
    │
    ├── unit/                 # Unit tests (mirror package structure)
    │   ├── __init__.py
    │   ├── test_config/
    │   ├── test_parsers/
    │   ├── test_providers/
    │   ├── test_media/
    │   ├── test_nfo/
    │   └── test_utils/
    │
    ├── integration/          # Integration tests
    │   ├── __init__.py
    │   ├── test_movie_workflow.py
    │   ├── test_tvshow_workflow.py
    │   └── test_migration.py
    │
    └── fixtures/             # Test data
        ├── configs/          # Sample config files
        ├── media/            # Sample video files (small test files)
        ├── nfo/              # Expected NFO outputs
        └── responses/        # Mock API responses (JSON)
```

### Core Dependencies

**Runtime Dependencies** (`requirements.txt`):
```
# CLI and UI
click>=8.0.0                  # Modern CLI framework with decorators
rich>=13.0.0                  # Rich terminal output (colors, progress bars, tables)
prompt-toolkit>=3.0.0         # Interactive prompts and menus

# HTTP and API clients
requests>=2.28.0              # HTTP library
requests-cache>=1.0.0         # HTTP caching
httpx>=0.24.0                 # Async HTTP client (future enhancement)

# Media file analysis
pymediainfo>=6.0.0            # Media file metadata extraction
# Alternative: ffmpeg-python>=0.2.0

# XML processing
lxml>=4.9.0                   # Fast XML parsing and generation
xmltodict>=0.13.0             # XML to dict conversion (for NFO parsing)

# Configuration
tomli>=2.0.0; python_version < "3.11"  # TOML parsing (built-in for 3.11+)
platformdirs>=3.0.0           # Cross-platform config directory paths

# Data validation
pydantic>=2.0.0               # Data validation and settings management
python-dotenv>=1.0.0          # .env file support (optional API key storage)

# Utilities
python-dateutil>=2.8.0        # Date parsing and formatting
tqdm>=4.65.0                  # Progress bars (alternative to rich)
```

**Development Dependencies** (`requirements-dev.txt`):
```
# Testing
pytest>=7.4.0                 # Test framework
pytest-cov>=4.1.0             # Code coverage
pytest-mock>=3.11.0           # Mocking utilities
pytest-asyncio>=0.21.0        # Async test support
responses>=0.23.0             # HTTP response mocking

# Code quality
black>=23.7.0                 # Code formatter
isort>=5.12.0                 # Import sorter
flake8>=6.1.0                 # Linter
mypy>=1.5.0                   # Type checker
pylint>=2.17.0                # Additional linting

# Documentation
sphinx>=7.0.0                 # Documentation generator
sphinx-rtd-theme>=1.3.0       # Read the Docs theme

# Development tools
ipython>=8.14.0               # Enhanced Python shell
pre-commit>=3.3.0             # Git pre-commit hooks
```

### System Dependencies

**Required:**
- Python 3.8 or higher
- `ffprobe` (from FFmpeg) - for media file metadata extraction
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

**Optional:**
- `mediainfo` - alternative to ffprobe for media analysis
  - macOS: `brew install mediainfo`
  - Ubuntu/Debian: `sudo apt install mediainfo`

### Architectural Decisions

#### 1. CLI Framework: Click
**Why Click over argparse:**
- Decorator-based command definition (cleaner code)
- Automatic help generation
- Built-in support for subcommands (git-like interface)
- Type conversion and validation
- Better testing support
- Wide community adoption

**Example:**
```python
@click.group()
def cli():
    """mo.py - Media Organizer"""
    pass

@cli.group()
def library():
    """Manage media libraries"""
    pass

@library.command()
@click.argument('name')
@click.argument('type', type=click.Choice(['movie', 'show']))
@click.argument('path', type=click.Path(exists=True))
def add(name, type, path):
    """Add a new library"""
    pass
```

#### 2. Configuration Format: INI
**Why INI over TOML/YAML:**
- Simple, human-readable format
- No external dependencies (configparser is built-in for Python 3.8+)
- Sufficient for our flat configuration structure
- Easy to edit manually
- Widely understood by users

**Note:** Use `platformdirs` for cross-platform config paths:
- Linux: `~/.config/mo/config`
- macOS: `~/Library/Application Support/mo/config`
- Windows: `%APPDATA%\mo\config`

#### 3. Media Analysis: pymediainfo vs ffprobe
**Decision: Use pymediainfo with ffprobe fallback**
- `pymediainfo` provides a Python API (cleaner integration)
- `ffprobe` as fallback if mediainfo not available
- Both extract: duration, resolution, codec, bitrate
- Handle errors gracefully if neither is available

#### 4. HTTP Client: requests + requests-cache
**Why:**
- `requests` is industry standard, simple API
- `requests-cache` provides transparent caching (reduces API calls)
- Cache metadata during interactive sessions
- TTL-based expiration (e.g., 24 hours for search results)

#### 5. XML Generation: lxml
**Why lxml over xml.etree:**
- Faster performance
- Better Unicode handling
- Pretty-printing support (readable NFO files)
- XPath support (useful for migration/validation)

#### 6. Data Validation: Pydantic
**Why Pydantic:**
- Runtime type checking and validation
- Clear error messages for invalid data
- IDE autocomplete support
- Easy serialization/deserialization
- Used for: config schemas, API response models, NFO data structures

**Example:**
```python
from pydantic import BaseModel, Field, validator

class MovieMetadata(BaseModel):
    title: str
    year: int = Field(ge=1800, le=2100)
    imdb_id: str | None = None
    tmdb_id: int | None = None

    @validator('imdb_id')
    def validate_imdb_id(cls, v):
        if v and not v.startswith('tt'):
            raise ValueError('IMDb ID must start with "tt"')
        return v
```

#### 7. Testing Strategy
**Unit Tests:**
- Mock all external dependencies (APIs, file I/O)
- Test each module in isolation
- Use `pytest-mock` for mocking
- Use `responses` for HTTP mocking
- Aim for >80% code coverage

**Integration Tests:**
- Use temporary directories (pytest `tmp_path` fixture)
- Mock API calls but use real file operations
- Test full workflows end-to-end
- Validate actual NFO output against Jellyfin specs

**Test Data:**
- Minimal test video files (1-2 seconds, small size)
- Pre-recorded API responses (JSON fixtures)
- Expected NFO outputs for validation

#### 8. Logging Strategy
**Approach:**
- Use Python's built-in `logging` module
- Rich handler for colored console output
- File handler for debug logs (`~/.cache/mo/mo.log`)
- Structured logging with context (JSON format for file logs)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `--verbose` flag sets level to DEBUG

#### 9. Error Handling Philosophy
**Principles:**
- Never silent failure - always inform the user
- Provide actionable error messages with fix suggestions
- Graceful degradation when possible (e.g., one provider fails, try another)
- Use custom exception hierarchy for different error types:
  - `ConfigError` - configuration issues
  - `ProviderError` - API failures
  - `ValidationError` - invalid input
  - `FileSystemError` - file operation failures

#### 10. Interactive UI with Rich
**Why Rich:**
- Beautiful terminal output with colors and formatting
- Built-in progress bars and spinners
- Tables for displaying search results
- Syntax highlighting for plans/logs
- Tree views for directory structures
- Plays well with Click

**Example:**
```python
from rich.console import Console
from rich.table import Table

console = Console()

table = Table(title="Search Results")
table.add_column("No.", style="cyan")
table.add_column("Title", style="green")
table.add_column("Year", style="yellow")
table.add_column("Rating", style="magenta")

for i, result in enumerate(results, 1):
    table.add_row(str(i), result.title, str(result.year), str(result.rating))

console.print(table)
```

### Development Workflow

1. **Setup Development Environment:**
   ```bash
   git clone https://github.com/yourusername/mo.git
   cd mo
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -e ".[dev]"   # Editable install with dev dependencies
   pre-commit install        # Install git hooks
   ```

2. **Run Tests:**
   ```bash
   pytest                          # Run all tests
   pytest tests/unit/              # Run unit tests only
   pytest --cov=mo --cov-report=html  # Generate coverage report
   ```

3. **Code Quality:**
   ```bash
   black mo/ tests/                # Format code
   isort mo/ tests/                # Sort imports
   flake8 mo/ tests/               # Lint
   mypy mo/                        # Type check
   ```

4. **Run mo.py in Development:**
   ```bash
   python -m mo --help             # Run as module
   python mo.py --help             # Run as script
   ```

### Configuration Files

**`.mo.conf.example`** (local config example):
```ini
[libraries]
movies = /media/jellyfin/Movies
tv = /media/jellyfin/TV Shows

[library_types]
movies = movie
tv = show

[metadata]
tmdb_api_key = YOUR_TMDB_KEY_HERE
tvdb_api_key = YOUR_TVDB_KEY_HERE
omdb_api_key = YOUR_OMDB_KEY_HERE

[preferences]
prefer_tvdb = true
include_provider_ids_in_paths = false
cache_ttl_hours = 24
```

**`pyproject.toml`** (modern Python project config):
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mo"
version = "1.0.0"
description = "Media Organizer - Jellyfin-compatible media library management"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "your.email@example.com"}]
keywords = ["jellyfin", "media", "organizer", "nfo", "metadata"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]

[project.scripts]
mo = "mo.__main__:main"

[tool.black]
line-length = 100
target-version = ["py38"]

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --strict-markers"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
```

**`.gitignore`**:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
*.log

# Config (don't commit API keys)
.mo.conf
config

# OS
.DS_Store
Thumbs.db
```

### API Key Setup for Development

**TMDB:**
1. Create account at [themoviedb.org](https://www.themoviedb.org/)
2. Go to Settings → API
3. Request API key (free)
4. Copy "API Read Access Token" (v4 auth)

**TheTVDB:**
1. Create account at [thetvdb.com](https://thetvdb.com/)
2. Subscribe ($12/year for personal use)
3. Go to [API v4 Dashboard](https://thetvdb.com/dashboard/account/apikeys)
4. Create new API key

**OMDb:**
1. Register at [omdbapi.com](http://www.omdbapi.com/apikey.aspx)
2. Verify email
3. Copy API key (1000 free requests/day)

**Store in config:**
```bash
python -m mo config set tmdb_api_key YOUR_KEY
python -m mo config set tvdb_api_key YOUR_KEY
python -m mo config set omdb_api_key YOUR_KEY
```

### Performance Considerations

1. **API Rate Limiting:**
   - TMDB: 40 requests per 10 seconds
   - TheTVDB: Rate limits vary by subscription tier
   - OMDb: 1000 requests/day (free tier)
   - Implementation: exponential backoff, request queuing

2. **Caching Strategy:**
   - Cache search results: 24 hours
   - Cache episode metadata: 7 days
   - Cache movie metadata: 30 days
   - Use `requests-cache` with SQLite backend

3. **File Operations:**
   - Use `shutil.move()` for same-filesystem moves (instant)
   - Use `shutil.copy2()` + `os.remove()` for cross-filesystem (preserve metadata)
   - Verify checksums for large files (optional)
   - Batch operations to minimize I/O

4. **Memory Usage:**
   - Stream large files (don't load into memory)
   - Process episodes one season at a time
   - Limit concurrent API requests

### Security Considerations

1. **API Key Storage:**
   - Store in config files with restricted permissions (0600)
   - Redact when displaying config (`config list`)
   - Optionally support `.env` files

2. **File Operations:**
   - Validate all paths (prevent directory traversal)
   - Check available disk space before operations
   - Preserve file permissions and ownership
   - Never follow symlinks without user confirmation

3. **Input Validation:**
   - Sanitize all user input
   - Validate provider IDs match expected formats
   - Reject suspiciously long paths/filenames

## v1.0 Implementation Plan

All features listed below are required for v1.0 release. Each phase includes comprehensive unit testing to ensure reliability and Jellyfin compatibility.

### Phase 1: Core Infrastructure & Filename Utilities ✅
**Goal:** Build foundational components for configuration, library management, and Jellyfin-compatible filename handling.

- [x] **Filename sanitization and validation**
  - [x] Reserved character replacement (`< > : " / \ | ? *`)
  - [x] Path length validation (OS-specific limits)
  - [x] Unicode normalization
  - [x] **Unit tests:** Test all reserved characters, path length edge cases, Unicode handling
- [x] **Provider ID utilities**
  - [x] Extract provider IDs from paths using bracket notation `[imdbid-...]`, `[tmdbid-...]`
  - [x] Generate Jellyfin-compatible folder names with optional provider IDs
  - [x] Validate provider ID formats (IMDb: tt + digits, TMDB: digits, TVDB: digits)
  - [x] **Unit tests:** Parse various bracket formats, validate ID formats, handle malformed input
- [x] **Configuration system**
  - [x] Hierarchical config loading (local `.mo.conf` → user `~/.config/mo/config`)
  - [x] INI format parser with validation
  - [x] `config set <key> <value>` command
  - [x] `config list` command with redacted API keys
  - [x] Platform-specific user config paths (XDG on Linux, AppData on Windows, etc.)
  - [x] Error handling for missing config with helpful messages
  - [x] **Unit tests:** Config file parsing, hierarchical merging, platform path detection, invalid config handling
- [x] **Library management**
  - [x] Library data structure (name, type: movie|show, root directory)
  - [x] `library add <name> <movie|show> <path>` with validation
  - [x] `library remove <name>` with confirmation
  - [x] `library info <name>` display
  - [x] Directory existence validation
  - [x] Duplicate library name detection
  - [x] Persistence to config file
  - [x] **Unit tests:** Add/remove/info operations, validation rules, persistence, duplicate detection
- [x] **CLI framework**
  - [x] Argument parser for commands and subcommands (Click)
  - [x] Command routing (library, adopt, config)
  - [x] Help system and usage documentation
  - [x] `--force`, `--verbose`, `--dry-run`, `--preserve` global flags
  - [x] **Unit tests:** Argument parsing, command routing, flag handling

### Phase 2: Jellyfin Filename Parsing ✅
**Goal:** Implement Jellyfin-compatible episode and movie filename parsing with full validation.

- [x] **Episode filename parser**
  - [x] Regex-based parsing matching Jellyfin's `EpisodePathParser.cs` logic
  - [x] Standard formats: `S##E##`, `s##x##`, `##x##`
  - [x] Multi-episode: `S01E01-E02`, `S01E01xE02xE03`, `02x03-04-15`
  - [x] Absolute numbering for anime (e.g., `Show 001.mkv`)
  - [x] Date-based episodes (e.g., `2023-01-15`)
  - [x] Season validation: reject seasons 200-1927 and >2500 (avoid resolution false positives)
  - [x] Ending episode validation: reject if looks like resolution (1080, 720, etc.)
  - [x] Series name extraction with trimming of `_`, `.`, `-`
  - [x] **Unit tests:** All Jellyfin test cases from `EpisodePathParserTest.cs`, edge cases, invalid formats
- [x] **Season folder detection**
  - [x] Recognize `Season ##` format (with or without leading zeros)
  - [x] Reject abbreviated formats like `S01`
  - [x] Special handling for Season 0 (Specials)
  - [x] **Unit tests:** Valid season folders, invalid formats, Season 0 handling
- [x] **Movie filename parser**
  - [x] Extract title and year from filenames/folders
  - [x] Provider ID extraction from paths
  - [x] DVD/BluRay structure detection (`VIDEO_TS/`, `BDMV/`)
  - [x] **Unit tests:** Title/year extraction, provider ID parsing, DVD/BluRay detection
- [x] **Sample file detection**
  - [x] Regex matching `\bsample\b` (case-insensitive)
  - [x] Flag files for user confirmation
  - [x] **Unit tests:** Sample detection, false positive avoidance

### Phase 3: Metadata Provider Integration ✅
**Goal:** Integrate TMDB, TheTVDB, and OMDb APIs with caching and error handling.

- [x] **TMDB integration**
  - [x] API client with access token authentication
  - [x] Movie search by title/year with pagination
  - [x] TV show search by title/year
  - [x] Episode metadata retrieval (season/episode)
  - [x] Cast, crew, ratings, and genre data
  - [x] Collection information for movies
  - [x] Rate limiting and retry logic
  - [x] **Unit tests:** API client (mocked), search parsing, error handling, rate limiting
- [x] **TheTVDB integration**
  - [x] v4 API client with JWT authentication
  - [x] TV show search with multiple result handling
  - [x] Season and episode data retrieval
  - [x] Episode runtime information
  - [x] Air dates and special episode metadata
  - [x] Rate limiting and retry logic
  - [x] **Unit tests:** API client (mocked), authentication, search/episode retrieval, error handling
- [x] **OMDb integration**
  - [x] API client with key authentication
  - [x] Movie metadata as supplementary/fallback source
  - [x] IMDb rating integration
  - [x] Rate limiting (1000 calls/day free tier)
  - [x] **Unit tests:** API client (mocked), fallback logic, rate limiting
- [x] **Metadata caching**
  - [x] Local cache for API responses (TTL-based)
  - [x] Reduce redundant API calls during interactive sessions
  - [x] **Unit tests:** Cache hit/miss, TTL expiration, cache invalidation
- [x] **Interactive search interface**
  - [x] Display search results (title, year, plot summary, ratings)
  - [x] Numbered selection menu
  - [x] Option to enter new search term
  - [x] Loop until user confirms match
  - [x] Fuzzy matching and relevance scoring
  - [x] **Unit tests:** Result display formatting, user input handling (mocked)

### Phase 4: File Analysis and Media Detection ✅
**Goal:** Scan directories, identify media files, and extract metadata (duration, codecs).

- [x] **Media file detection**
  - [x] Scan directories for video extensions (mp4, mkv, avi, m4v, mov, wmv, flv, webm)
  - [x] Handle single files vs directories
  - [x] Recursive directory traversal with depth limits
  - [x] Subtitle file detection (srt, sub, ass, ssa, vtt)
  - [x] Ignore hidden files and system files
  - [x] **Unit tests:** File scanning, extension matching, recursion, subtitle detection
- [x] **Media file metadata extraction**
  - [x] Use ffprobe or pymediainfo to extract duration
  - [x] Extract resolution, codec information (for logging/debugging)
  - [x] Handle corrupted or inaccessible files gracefully
  - [x] **Unit tests:** Duration extraction (mocked ffprobe), error handling for corrupted files
- [x] **Duration-based episode matching**
  - [x] Compare file duration with expected episode runtime from TVDB/TMDB
  - [x] Tolerance threshold (e.g., ±5 minutes)
  - [x] Confidence scoring: exact match (100%), close match (80%), poor match (50%)
  - [x] Combine with filename hints for final confidence score
  - [x] **Unit tests:** Duration comparison, confidence scoring, tolerance thresholds
- [x] **Content type detection (mixed vs dedicated folders)**
  - [x] Detect dedicated movie folders (single video file)
  - [x] Detect mixed folders (multiple video files)
  - [x] Determine appropriate NFO naming strategy
  - [x] **Unit tests:** Folder type detection, edge cases with extras/samples

### Phase 5: NFO Generation Engine ✅
**Goal:** Generate Jellyfin-compatible NFO XML files for movies, TV shows, and episodes.

- [x] **NFO XML builder**
  - [x] XML generation with proper encoding (UTF-8)
  - [x] Pretty-printing with indentation
  - [x] Element ordering matching Jellyfin's savers
  - [x] **Unit tests:** XML structure, encoding, element ordering
- [x] **Movie NFO generation**
  - [x] Root element: `<movie>` or `<musicvideo>`
  - [x] Common fields: title, originaltitle, sorttitle, year, plot, tagline, mpaa, genre, studio, runtime, premiered, director, writer, actor, ratings
  - [x] Modern `<uniqueid type="imdb">` format for provider IDs
  - [x] Legacy `<id>` for IMDb (backwards compatibility)
  - [x] Collection support with `<set><name>` and optional `tmdbcolid` attribute
  - [x] Actor elements with role, thumb, order
  - [x] Multiple genre and studio elements
  - [x] **Unit tests:** Complete NFO generation, field validation, XML validity, legacy format support
- [x] **TV show NFO generation (tvshow.nfo)**
  - [x] Root element: `<tvshow>`
  - [x] Common fields: title, year, plot, genre, studio, mpaa, actor, ratings
  - [x] `<episodeguide>` with TVDB URL and language
  - [x] `<status>` (Continuing, Ended)
  - [x] Placeholder `<season>-1</season>` and `<episode>-1</episode>`
  - [x] **Unit tests:** Complete tvshow.nfo generation, episodeguide URL format, field validation
- [x] **Episode NFO generation**
  - [x] Root element: `<episodedetails>`
  - [x] Episode-specific fields: showtitle, season, episode, episodenumberend, aired
  - [x] Common fields: title, plot, director, writer, actor, ratings
  - [x] Multi-episode support: multiple `<episodedetails>` blocks in one file
  - [x] Special episode fields for Season 0: airsafter_season, airsbefore_season, airsbefore_episode, displayseason, displayepisode
  - [x] **Unit tests:** Episode NFO generation, multi-episode files, Season 0 specials, field validation
- [x] **NFO file path determination**
  - [x] Movies: `movie.nfo` (dedicated folder) or `<filename>.nfo` (mixed folder)
  - [x] Movies (DVD): `VIDEO_TS/VIDEO_TS.nfo`
  - [x] TV shows: `tvshow.nfo` in series root
  - [x] Episodes: `<filename>.nfo` matching episode file
  - [x] **Unit tests:** Path selection logic for all content types

### Phase 6: Movie Adoption Workflow
**Goal:** Implement end-to-end movie adoption with interactive steps and NFO generation.

- [ ] **Step 1: Movie metadata search**
  - [ ] Parse source folder/filename for title and year hints
  - [ ] Query TMDB and OMDb
  - [ ] Display results to user with plot summaries
  - [ ] User selects match or enters new search
  - [ ] Retry loop until confirmation
  - [ ] **Unit tests:** Search hint extraction, user interaction flow (mocked)
- [ ] **Step 2: File identification**
  - [ ] Scan directory for all files
  - [ ] Identify main movie file (largest video file)
  - [ ] Identify extras (behind-the-scenes, deleted scenes, interviews)
  - [ ] Identify subtitles
  - [ ] User confirms role of each file
  - [ ] User marks files to adopt vs skip
  - [ ] **Unit tests:** File role detection, user confirmation flow (mocked)
- [ ] **Step 3: Jellyfin structure planning**
  - [ ] Generate `Movie Name (Year)/` folder name
  - [ ] Optional provider ID injection: `[imdbid-tt1234567]`
  - [ ] Sanitize filename (reserved characters)
  - [ ] Determine NFO path (movie.nfo vs filename.nfo based on folder type)
  - [ ] Plan extras subdirectory if needed
  - [ ] **Unit tests:** Folder name generation, provider ID injection, sanitization
- [ ] **Step 4: Final plan review**
  - [ ] Display complete action plan (directories, file moves, NFO files)
  - [ ] Highlight conflicts/overwrites
  - [ ] Request final yes/no confirmation
  - [ ] Cancel aborts without changes
  - [ ] **Unit tests:** Plan generation, conflict detection
- [ ] **Step 5: Execution**
  - [ ] Create timestamped action log (JSON format) in source directory
  - [ ] Create target directory structure
  - [ ] Move/copy files to library with proper naming
  - [ ] Write movie.nfo with complete metadata
  - [ ] Move subtitles and extras
  - [ ] Preserve file permissions
  - [ ] Log all actions with timestamps
  - [ ] Handle partial failures with rollback or skip
  - [ ] Overwrite protection (require `--force` flag)
  - [ ] **Unit tests:** File operations, logging, error handling, rollback

### Phase 7: TV Show Adoption Workflow
**Goal:** Implement end-to-end TV show adoption with season/episode matching and NFO generation.

- [ ] **Step 1: Show metadata search**
  - [ ] Parse source folder for show title and year hints
  - [ ] Query TMDB and TheTVDB
  - [ ] Display results with show summaries and season counts
  - [ ] User selects match or enters new search
  - [ ] Retry loop until confirmation
  - [ ] **Unit tests:** Search hint extraction, user interaction flow (mocked)
- [ ] **Step 2: Season identification**
  - [ ] Detect seasons by subdirectory names (`Season 01/`, `Season 02/`)
  - [ ] Detect seasons by filename prefixes (S01E01, S02E03)
  - [ ] Default to Season 1 if season cannot be determined (Jellyfin behavior)
  - [ ] Warn user if episodes lack clear season information
  - [ ] Present detected seasons to user for confirmation
  - [ ] User can override/manually assign season numbers
  - [ ] Handle `--season <n>` flag for partial adoption
  - [ ] Special handling for Season 0 (Specials)
  - [ ] **Unit tests:** Season detection from folders, season detection from filenames, default behavior, user override
- [ ] **Step 3: Episode matching per season**
  - [ ] For each season, analyze all files
  - [ ] Parse filenames using Jellyfin-compatible parser
  - [ ] Extract file duration
  - [ ] Fetch episode list from TVDB/TMDB (titles, air dates, runtime)
  - [ ] Match files to episodes using filename hints + duration comparison
  - [ ] Calculate confidence scores
  - [ ] Handle multi-episode files (S01E01-E02)
  - [ ] Detect sample files and flag for user
  - [ ] Display file → episode mappings with confidence
  - [ ] User can: accept all, override individual matches, manually map, skip files
  - [ ] Batch confirmation for high-confidence matches
  - [ ] **Unit tests:** Episode matching algorithm, multi-episode detection, confidence scoring, sample detection
- [ ] **Step 4: Jellyfin structure planning**
  - [ ] Generate `Show Name (Year)/` series folder
  - [ ] Generate `Season 01/`, `Season 02/` subfolders (zero-padded, no "S01" abbreviation)
  - [ ] Generate episode filenames: `Show Name S01E01 Episode Title.ext`
  - [ ] Sanitize all filenames
  - [ ] Optional provider ID injection in series folder name
  - [ ] Plan tvshow.nfo + all episode NFO files
  - [ ] **Unit tests:** Folder structure generation, filename generation, sanitization
- [ ] **Step 5: Final plan review**
  - [ ] Display complete action plan (directories, file moves grouped by season, NFO files)
  - [ ] Highlight conflicts/overwrites
  - [ ] Request final yes/no confirmation
  - [ ] Cancel aborts without changes
  - [ ] **Unit tests:** Plan generation, conflict detection
- [ ] **Step 6: Execution**
  - [ ] Create timestamped action log (JSON format) in source directory
  - [ ] Create series directory structure (series root + season folders)
  - [ ] Write tvshow.nfo in series root
  - [ ] Move/copy episode files to season folders with proper naming
  - [ ] Write episode NFO for each episode
  - [ ] Handle multi-episode NFO files (multiple `<episodedetails>` blocks)
  - [ ] Move subtitles matching episode files
  - [ ] Preserve file permissions
  - [ ] Log all actions with timestamps
  - [ ] Handle partial failures with skip or rollback
  - [ ] Overwrite protection (require `--force` flag)
  - [ ] **Unit tests:** File operations, NFO generation, logging, error handling, multi-episode NFOs

### Phase 8: Migration from Proprietary Format (Temporary)
**Goal:** Convert existing proprietary `metadata.json` format to Jellyfin NFO format.

- [ ] **metadata.json parser**
  - [ ] Read existing proprietary metadata structure
  - [ ] Extract title, year, episode mappings, provider IDs
  - [ ] Handle malformed or incomplete metadata
  - [ ] **Unit tests:** JSON parsing, field extraction, error handling
- [ ] **Metadata reconciliation**
  - [ ] Match proprietary data with TMDB/TVDB by provider ID or title/year
  - [ ] Display matches to user for confirmation
  - [ ] Handle mismatches or missing metadata
  - [ ] **Unit tests:** Matching logic, user confirmation flow (mocked)
- [ ] **Conversion workflow**
  - [ ] Transform proprietary format to NFO XML
  - [ ] Reorganize files into Jellyfin structure
  - [ ] Preserve existing organization where possible
  - [ ] Generate conversion report
  - [ ] **Unit tests:** Conversion accuracy, file reorganization, report generation

### Phase 9: Polish, Error Handling, and Edge Cases
**Goal:** Ensure robustness, user-friendly error messages, and comprehensive testing.

- [ ] **Error handling**
  - [ ] Network errors: retry logic with exponential backoff, fallback to cached data
  - [ ] File system errors: permissions, disk space checks, path too long
  - [ ] Invalid configuration: helpful error messages with fix suggestions
  - [ ] Missing API keys: detect and prompt user with setup instructions
  - [ ] API rate limits: detect and pause with user notification
  - [ ] Graceful degradation: partial results when some providers fail
  - [ ] **Unit tests:** All error scenarios, retry logic, error message formatting
- [ ] **Logging and output**
  - [ ] Progress indicators for long operations (spinner, percentage)
  - [ ] `--verbose` flag for detailed logging
  - [ ] `--dry-run` flag to preview actions without execution
  - [ ] Colored output for errors, warnings, success (optional, detect TTY)
  - [ ] Structured logging to file for debugging
  - [ ] **Unit tests:** dry-run mode
- [ ] **Edge cases**
  - [ ] Empty directories: detect and warn user
  - [ ] Duplicate files (same content hash): detect and offer deduplication
  - [ ] Special characters in filenames: sanitize properly
  - [ ] Very long filenames: truncate intelligently with hash suffix
  - [ ] Path length limits (Windows 260 char limit): detect and error with guidance
  - [ ] Symbolic links: detect and handle (follow or warn)
  - [ ] Files without extensions: detect using magic bytes or skip
  - [ ] Zero-byte files: detect and warn
  - [ ] **Unit tests:** All edge cases, boundary conditions
- [ ] **Integration testing**
  - [ ] End-to-end movie adoption workflow
  - [ ] End-to-end TV show adoption workflow (full series)
  - [ ] Partial TV show adoption (single season)
  - [ ] Migration from proprietary format
  - [ ] Multi-provider fallback scenarios
  - [ ] Test data sets: sample movies and TV shows with various naming patterns
  - [ ] **Integration tests:** Full workflows with mocked APIs and temporary file systems
- [ ] **Documentation**
  - [ ] Inline code documentation (docstrings)
  - [ ] API documentation for key modules
  - [ ] Troubleshooting guide
  - [ ] FAQ section in README
  - [ ] Example configurations


## License

See [LICENSE](LICENSE) file for details.
