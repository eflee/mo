"""Tests for configuration management."""

import configparser
from pathlib import Path

import pytest

from mo.config import Config
from mo.utils.errors import ConfigError


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory for config files."""
    return tmp_path


@pytest.fixture
def local_config_file(temp_config_dir):
    """Create a local config file."""
    config_path = temp_config_dir / ".mo.conf"
    config = configparser.ConfigParser()

    config["libraries"] = {
        "movies": "/media/Movies",
        "tv": "/media/TV",
    }

    config["library_types"] = {
        "movies": "movie",
        "tv": "show",
    }

    config["metadata"] = {
        "tmdb_api_key": "test_tmdb_key",
        "tvdb_api_key": "test_tvdb_key",
        "omdb_api_key": "test_omdb_key",
    }

    config["preferences"] = {
        "prefer_tvdb": "true",
        "include_provider_ids_in_paths": "false",
        "cache_ttl_hours": "24",
    }

    with open(config_path, "w") as f:
        config.write(f)

    return config_path


@pytest.fixture
def user_config_file(temp_config_dir):
    """Create a user config file."""
    config_path = temp_config_dir / "user_config"
    config = configparser.ConfigParser()

    config["metadata"] = {
        "tmdb_api_key": "user_tmdb_key",
    }

    with open(config_path, "w") as f:
        config.write(f)

    return config_path


class TestConfigLoading:
    """Test configuration loading."""

    def test_loads_local_config(self, local_config_file):
        """Test loading local config file."""
        cfg = Config(local_path=local_config_file)
        assert cfg.config_path == local_config_file
        assert cfg.get("metadata", "tmdb_api_key") == "test_tmdb_key"

    def test_loads_user_config_when_no_local(self, user_config_file, temp_config_dir):
        """Test loading user config when local doesn't exist."""
        local_path = temp_config_dir / ".mo.conf"
        cfg = Config(local_path=local_path, user_path=user_config_file)
        assert cfg.config_path == user_config_file
        assert cfg.get("metadata", "tmdb_api_key") == "user_tmdb_key"

    def test_prefers_local_over_user(self, local_config_file, user_config_file):
        """Test that local config takes precedence over user config."""
        cfg = Config(local_path=local_config_file, user_path=user_config_file)
        assert cfg.config_path == local_config_file
        assert cfg.get("metadata", "tmdb_api_key") == "test_tmdb_key"

    def test_raises_error_when_no_config_found(self, temp_config_dir):
        """Test error when no config file exists."""
        local_path = temp_config_dir / ".mo.conf"
        user_path = temp_config_dir / "user_config"

        with pytest.raises(ConfigError, match="No configuration file found"):
            Config(local_path=local_path, user_path=user_path)


class TestConfigGet:
    """Test getting configuration values."""

    def test_get_string_value(self, local_config_file):
        """Test getting string value."""
        cfg = Config(local_path=local_config_file)
        assert cfg.get("metadata", "tmdb_api_key") == "test_tmdb_key"

    def test_get_with_fallback(self, local_config_file):
        """Test getting value with fallback."""
        cfg = Config(local_path=local_config_file)
        assert cfg.get("metadata", "nonexistent", fallback="default") == "default"

    def test_get_bool_value(self, local_config_file):
        """Test getting boolean value."""
        cfg = Config(local_path=local_config_file)
        assert cfg.get_bool("preferences", "prefer_tvdb") is True
        assert cfg.get_bool("preferences", "include_provider_ids_in_paths") is False

    def test_get_bool_with_fallback(self, local_config_file):
        """Test getting boolean with fallback."""
        cfg = Config(local_path=local_config_file)
        assert cfg.get_bool("preferences", "nonexistent", fallback=True) is True

    def test_get_int_value(self, local_config_file):
        """Test getting integer value."""
        cfg = Config(local_path=local_config_file)
        assert cfg.get_int("preferences", "cache_ttl_hours") == 24

    def test_get_int_with_fallback(self, local_config_file):
        """Test getting integer with fallback."""
        cfg = Config(local_path=local_config_file)
        assert cfg.get_int("preferences", "nonexistent", fallback=100) == 100


class TestConfigSet:
    """Test setting configuration values."""

    def test_set_value_in_existing_section(self, local_config_file):
        """Test setting value in existing section."""
        cfg = Config(local_path=local_config_file)
        cfg.set("metadata", "new_key", "new_value")
        assert cfg.get("metadata", "new_key") == "new_value"

    def test_set_value_creates_section(self, local_config_file):
        """Test that setting value creates section if needed."""
        cfg = Config(local_path=local_config_file)
        cfg.set("new_section", "key", "value")
        assert cfg.get("new_section", "key") == "value"

    def test_set_overwrites_existing_value(self, local_config_file):
        """Test that set overwrites existing value."""
        cfg = Config(local_path=local_config_file)
        original = cfg.get("metadata", "tmdb_api_key")
        cfg.set("metadata", "tmdb_api_key", "new_key")
        assert cfg.get("metadata", "tmdb_api_key") == "new_key"
        assert cfg.get("metadata", "tmdb_api_key") != original


class TestConfigSave:
    """Test saving configuration."""

    def test_save_to_active_config(self, local_config_file):
        """Test saving to active config file."""
        cfg = Config(local_path=local_config_file)
        cfg.set("metadata", "new_key", "new_value")
        cfg.save()

        # Reload and verify
        cfg2 = Config(local_path=local_config_file)
        assert cfg2.get("metadata", "new_key") == "new_value"

    def test_save_to_local(self, local_config_file, temp_config_dir):
        """Test saving to local config."""
        cfg = Config(local_path=local_config_file)
        cfg.set("test", "key", "value")

        new_local = temp_config_dir / "new_local.conf"
        cfg._local_path = new_local
        cfg.save(target="local")

        assert new_local.exists()
        cfg2 = Config(local_path=new_local)
        assert cfg2.get("test", "key") == "value"

    def test_save_to_user(self, local_config_file, temp_config_dir):
        """Test saving to user config."""
        cfg = Config(local_path=local_config_file)
        cfg.set("test", "key", "value")

        user_path = temp_config_dir / "user.conf"
        cfg._user_path = user_path
        cfg.save(target="user")

        assert user_path.exists()

    def test_save_creates_parent_directory(self, local_config_file, temp_config_dir):
        """Test that save creates parent directory if needed."""
        cfg = Config(local_path=local_config_file)
        cfg.set("test", "key", "value")

        nested_path = temp_config_dir / "nested" / "dir" / "config"
        cfg._local_path = nested_path
        cfg.save(target="local")

        assert nested_path.exists()

    def test_save_invalid_target_raises_error(self, local_config_file):
        """Test error for invalid save target."""
        cfg = Config(local_path=local_config_file)
        with pytest.raises(ConfigError, match="Invalid target"):
            cfg.save(target="invalid")


class TestConfigLibraries:
    """Test library-specific methods."""

    def test_get_libraries(self, local_config_file):
        """Test getting all libraries."""
        cfg = Config(local_path=local_config_file)
        libraries = cfg.get_libraries()
        assert libraries == {
            "movies": "/media/Movies",
            "tv": "/media/TV",
        }

    def test_get_library_types(self, local_config_file):
        """Test getting library types."""
        cfg = Config(local_path=local_config_file)
        types = cfg.get_library_types()
        assert types == {
            "movies": "movie",
            "tv": "show",
        }

    def test_get_libraries_empty_when_no_section(self, user_config_file):
        """Test getting libraries returns empty dict when section missing."""
        cfg = Config(local_path=user_config_file)
        assert cfg.get_libraries() == {}

    def test_remove_library(self, local_config_file):
        """Test removing a library."""
        cfg = Config(local_path=local_config_file)
        cfg.remove_library("movies")

        libraries = cfg.get_libraries()
        assert "movies" not in libraries

        types = cfg.get_library_types()
        assert "movies" not in types


class TestConfigHelpers:
    """Test helper methods."""

    def test_get_sections(self, local_config_file):
        """Test getting all sections."""
        cfg = Config(local_path=local_config_file)
        sections = cfg.get_sections()
        assert "libraries" in sections
        assert "metadata" in sections
        assert "preferences" in sections

    def test_get_all(self, local_config_file):
        """Test getting all values in a section."""
        cfg = Config(local_path=local_config_file)
        metadata = cfg.get_all("metadata")
        assert metadata["tmdb_api_key"] == "test_tmdb_key"
        assert metadata["tvdb_api_key"] == "test_tvdb_key"

    def test_get_all_empty_for_nonexistent_section(self, local_config_file):
        """Test get_all returns empty dict for nonexistent section."""
        cfg = Config(local_path=local_config_file)
        assert cfg.get_all("nonexistent") == {}

    def test_repr(self, local_config_file):
        """Test string representation."""
        cfg = Config(local_path=local_config_file)
        repr_str = repr(cfg)
        assert "Config" in repr_str
        assert str(local_config_file) in repr_str
