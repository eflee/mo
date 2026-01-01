"""Tests for CLI commands."""

import configparser
from pathlib import Path

import pytest
from click.testing import CliRunner

from mo.cli.main import cli


@pytest.fixture
def runner():
    """Create Click CLI runner."""
    return CliRunner()


@pytest.fixture
def config_file(tmp_path):
    """Create a basic config file."""
    config_path = tmp_path / ".mo.conf"
    config = configparser.ConfigParser()

    config["metadata"] = {
        "tmdb_api_key": "test_key",
    }

    with open(config_path, "w") as f:
        config.write(f)

    return config_path


@pytest.fixture
def media_dir(tmp_path):
    """Create a media directory."""
    media = tmp_path / "media"
    media.mkdir()
    return media


class TestLibraryCommands:
    """Test library CLI commands."""

    def test_library_add(self, runner, tmp_path, media_dir):
        """Test adding a library."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            # Create minimal config in the isolated filesystem
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(
                cli, ["library", "add", "movies", "movie", str(media_dir)]
            )

            assert result.exit_code == 0
            assert "Added library 'movies'" in result.output

    def test_library_add_nonexistent_path(self, runner, tmp_path):
        """Test error for nonexistent path."""
        config_file = tmp_path / ".mo.conf"

        config = configparser.ConfigParser()
        config["metadata"] = {"tmdb_api_key": "test"}
        with open(config_file, "w") as f:
            config.write(f)

        nonexistent = tmp_path / "nonexistent"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["library", "add", "movies", "movie", str(nonexistent)]
            )

            assert result.exit_code == 2  # Click validation error

    def test_library_add_dry_run(self, runner, tmp_path, media_dir):
        """Test dry run mode."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(
                cli, ["--dry-run", "library", "add", "movies", "movie", str(media_dir)]
            )

            assert result.exit_code == 0
            assert "Dry run" in result.output
            assert "Would add library 'movies'" in result.output

    def test_library_remove(self, runner, tmp_path, media_dir):
        """Test removing a library."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            config["libraries"] = {"movies": str(media_dir)}
            config["library_types"] = {"movies": "movie"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(
                cli, ["library", "remove", "movies", "--force"], input="y\n"
            )

            assert result.exit_code == 0
            assert "Removed library 'movies'" in result.output

    def test_library_remove_with_confirmation(self, runner, tmp_path, media_dir):
        """Test removal with confirmation prompt."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            config["libraries"] = {"movies": str(media_dir)}
            config["library_types"] = {"movies": "movie"}
            with open(config_file, "w") as f:
                config.write(f)

            # Cancel removal
            result = runner.invoke(cli, ["library", "remove", "movies"], input="n\n")
            assert "Cancelled" in result.output

    def test_library_info_single(self, runner, tmp_path, media_dir):
        """Test displaying single library info."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            config["libraries"] = {"movies": str(media_dir)}
            config["library_types"] = {"movies": "movie"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(cli, ["library", "info", "movies"])

            assert result.exit_code == 0
            assert "movies" in result.output
            assert "movie" in result.output

    def test_library_info_list_all(self, runner, tmp_path, media_dir):
        """Test listing all libraries."""
        tv_dir = tmp_path / "tv"
        tv_dir.mkdir()

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            config["libraries"] = {
                "movies": str(media_dir),
                "tv": str(tv_dir),
            }
            config["library_types"] = {
                "movies": "movie",
                "tv": "show",
            }
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(cli, ["library", "info"])

            assert result.exit_code == 0
            assert "movies" in result.output
            assert "tv" in result.output

    def test_library_info_no_libraries(self, runner, tmp_path):
        """Test info when no libraries configured."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(cli, ["library", "info"])

            assert result.exit_code == 0
            assert "No libraries configured" in result.output


class TestConfigCommands:
    """Test config CLI commands."""

    def test_config_set(self, runner, tmp_path):
        """Test setting config value."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(
                cli, ["config", "set", "metadata.new_key", "new_value"]
            )

            assert result.exit_code == 0
            assert "Set metadata.new_key = new_value" in result.output

    def test_config_set_invalid_key_format(self, runner, tmp_path):
        """Test error for invalid key format."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(cli, ["config", "set", "invalidkey", "value"])

            assert result.exit_code == 1
            assert "must be in format 'section.key'" in result.output

    def test_config_set_dry_run(self, runner, tmp_path):
        """Test config set in dry run mode."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(
                cli, ["--dry-run", "config", "set", "metadata.key", "value"]
            )

            assert result.exit_code == 0
            assert "Dry run" in result.output

    def test_config_list(self, runner, tmp_path):
        """Test listing config."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {
                "tmdb_api_key": "secret_key",
                "other_setting": "value",
            }
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(cli, ["config", "list"])

            assert result.exit_code == 0
            # Check for the config keys in output
            assert "tmdb_api_key" in result.output
            assert "other_setting" in result.output
            # API key should be redacted
            assert "********" in result.output
            assert "secret_key" not in result.output
            # Other settings should be visible
            assert "value" in result.output

    def test_config_list_section(self, runner, tmp_path):
        """Test listing specific section."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            config_file = Path(td) / ".mo.conf"
            config = configparser.ConfigParser()
            config["metadata"] = {"tmdb_api_key": "test"}
            config["preferences"] = {"prefer_tvdb": "true"}
            with open(config_file, "w") as f:
                config.write(f)

            result = runner.invoke(cli, ["config", "list", "--section", "preferences"])

            assert result.exit_code == 0
            assert "preferences" in result.output
            assert "prefer_tvdb" in result.output


class TestAdoptCommands:
    """Test adopt CLI commands (placeholders)."""

    def test_adopt_movie_placeholder(self, runner, tmp_path):
        """Test movie adoption placeholder."""
        movie_file = tmp_path / "movie.mkv"
        movie_file.touch()

        result = runner.invoke(cli, ["adopt", "movie", str(movie_file)])

        assert result.exit_code == 0
        assert "not yet implemented" in result.output

    def test_adopt_show_placeholder(self, runner, tmp_path):
        """Test show adoption placeholder."""
        show_file = tmp_path / "show.mkv"
        show_file.touch()

        result = runner.invoke(cli, ["adopt", "show", str(show_file)])

        assert result.exit_code == 0
        assert "not yet implemented" in result.output


class TestNoConfig:
    """Test CLI behavior without config file."""

    def test_library_add_without_config(self, runner, tmp_path):
        """Test that commands fail gracefully without config."""
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["library", "add", "movies", "movie", str(media_dir)]
            )

            assert result.exit_code == 1
            assert "No configuration file found" in result.output
