import pytest
import os
import json
import logging

import os.path

from unittest.mock import patch

from siliconcompiler.utils.settings import SettingsManager


@pytest.fixture
def settings_file(tmp_path):
    """Fixture to provide a clean temporary file path for each test."""
    return str(tmp_path / "config.json")


def test_load_non_existent_file(settings_file):
    """Test loading when file doesn't exist (should start empty)."""
    manager = SettingsManager(settings_file, logging.getLogger())
    assert manager._SettingsManager__settings == {}


def test_basic_set_get_save_load(settings_file):
    """Test setting values, saving, and reloading."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('showtools', 'enabled', True)
    manager.set('slurmconfig', 'nodes', 4)
    manager.save()

    # Create new instance to simulate app restart
    new_manager = SettingsManager(settings_file, logging.getLogger())
    assert new_manager.get('showtools', 'enabled') is True
    assert new_manager.get('slurmconfig', 'nodes') == 4


def test_set_keep_flag(settings_file):
    """Test the keep flag behavior in set()."""
    manager = SettingsManager(settings_file, logging.getLogger())

    # Initial set
    manager.set('test', 'key', 'initial')
    assert manager.get('test', 'key') == 'initial'

    # Try to overwrite with keep=True (should fail to overwrite)
    manager.set('test', 'key', 'new', keep=True)
    assert manager.get('test', 'key') == 'initial'

    # Try to overwrite with keep=False (default) (should overwrite)
    manager.set('test', 'key', 'new')
    assert manager.get('test', 'key') == 'new'


def test_get_defaults(settings_file):
    """Test getting missing keys returns default values."""
    manager = SettingsManager(settings_file, logging.getLogger())
    assert manager.get('nonexistent', 'key', default='fallback') == 'fallback'

    manager.set('existing', 'key1', 'value')
    assert manager.get('existing', 'key2', default='fallback_inner') == 'fallback_inner'


def test_malformed_json_file(settings_file, caplog):
    """Test loading a file with broken JSON."""
    with open(settings_file, 'w') as f:
        f.write("{ this is not json }")

    manager = SettingsManager(settings_file, logging.getLogger())
    assert manager._SettingsManager__settings == {}
    assert "is malformed" in caplog.text

    # Verify we can save over it
    manager.set('new', 'key', 1)
    manager.save()

    # Verify it fixed the file
    with open(settings_file, 'r') as f:
        data = json.load(f)
    assert data['new']['key'] == 1


def test_valid_json_but_not_dict(settings_file, caplog):
    """Test loading a JSON file that is a list, not a dict."""
    with open(settings_file, 'w') as f:
        f.write("[1, 2, 3]")

    manager = SettingsManager(settings_file, logging.getLogger())
    assert manager._SettingsManager__settings == {}
    assert "did not contain a JSON object" in caplog.text


def test_get_category(settings_file):
    """Test retrieving entire category."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('options', 'theme', 'dark')

    assert manager.get_category('options') == {'theme': 'dark'}
    assert manager.get_category('missing') == {}


def test_delete_setting(settings_file):
    """Test deleting settings and cleaning up empty categories."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('misc', 'temp', 1)
    manager.set('misc', 'keep', 2)

    # Delete one key
    manager.delete('misc', 'temp')
    assert manager.get('misc', 'temp') is None
    assert manager.get('misc', 'keep') == 2

    # Delete last key, category should be removed
    manager.delete('misc', 'keep')
    assert 'misc' not in manager._SettingsManager__settings


def test_delete_setting_category(settings_file):
    """Test deleting categories."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('misc', 'temp', 1)
    manager.set('misc', 'keep', 2)

    # Delete category
    manager.delete('misc')

    assert 'misc' not in manager._SettingsManager__settings


def test_save_creates_directories(tmp_path):
    """Test that save() creates missing subdirectories."""
    nested_path = str(tmp_path / 'subdir' / 'deep' / 'conf.json')
    manager = SettingsManager(nested_path, logging.getLogger())
    manager.set('a', 'b', 'c')
    manager.save()

    assert os.path.exists(nested_path)


def test_save_permission_error(settings_file, monkeypatch, caplog):
    """Test error handling when saving fails using a simulated permission error."""
    manager = SettingsManager(settings_file, logging.getLogger())

    # Mock open() to raise PermissionError
    def mock_open(*args, **kwargs):
        raise PermissionError("Simulated permission denied")

    # monkeypatch is a standard pytest fixture
    with monkeypatch.context() as m:
        m.setattr("builtins.open", mock_open)
        with pytest.raises(PermissionError):
            manager.save()

    assert "Failed to save settings" in caplog.text


def test_load_generic_exception(tmp_path, caplog):
    """Test the generic exception catcher in _load."""
    # Point to a directory instead of a file to force an OS error (IsADirectoryError)
    bad_path = str(tmp_path / 'folder_conflict_load')
    os.makedirs(bad_path)

    manager = SettingsManager(bad_path, logging.getLogger())
    # Should catch the error and init empty
    assert manager._SettingsManager__settings == {}
    assert "Unexpected error loading settings" in caplog.text


# --- LOCKING TESTS ---
def test_lock_file_exists(settings_file):
    """Test that the .lock file exists after saving."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('test', 'lock', True)
    manager.save()

    lock_path = settings_file + ".lock"
    assert os.path.exists(lock_path)


def test_timeout_during_load(settings_file, caplog):
    """Test that init logs error and starts empty if lock exists too long."""
    settings = SettingsManager(settings_file, logging.getLogger())
    settings.set("test", "test", True)
    settings.save()
    assert os.path.exists(settings_file)

    with patch("fasteners.InterProcessLock.acquire") as acq:
        acq.return_value = False
        manager = SettingsManager(settings_file, logging.getLogger(), timeout=0.1)

    assert manager._SettingsManager__settings == {}
    assert "Timeout acquiring lock" in caplog.text


def test_filepath_none():
    """Test behavior when filepath is None (in-memory only)."""
    manager = SettingsManager(None, logging.getLogger())

    # Should start empty
    assert manager._SettingsManager__settings == {}

    # Set/Get should work in memory
    manager.set('memory', 'test', 123)
    assert manager.get('memory', 'test') == 123


# ---------------------------------------------------------------------------
# System settings layer (defaults + system priority)
# ---------------------------------------------------------------------------


@pytest.fixture
def system_file(tmp_path):
    """Fixture to provide a path for a system settings file."""
    return str(tmp_path / "system.json")


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def test_backward_compat_no_system_layer(settings_file):
    """Old settings.json files behave exactly as before when no system file."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("schema-options", "remote", True)
    manager.save()

    reloaded = SettingsManager(settings_file, logging.getLogger())
    assert reloaded.get("schema-options", "remote") is True
    assert reloaded.get("schema-options", "missing", default="d") == "d"
    assert reloaded.get_category("schema-options") == {"remote": True}


def test_backward_compat_missing_system_file(settings_file, system_file):
    """A non-existent system file is a no-op, not an error."""
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    assert manager.get("any", "key", default="d") == "d"
    assert manager._SettingsManager__system_settings == {}
    assert manager._SettingsManager__priority == {}


def test_backward_compat_user_priority_wrapper_is_plain(settings_file):
    """A priority-wrapper shape in a USER file is treated as an ordinary value."""
    _write_json(settings_file, {"record": {"region": {"value": "eu", "system_priority": True}}})
    manager = SettingsManager(settings_file, logging.getLogger())
    # Priority flags are only honored in the system file; the user file is untouched.
    assert manager._SettingsManager__priority == {}
    assert manager.get("record", "region") == {"value": "eu", "system_priority": True}
    manager.set("record", "region", "us")
    assert manager.get("record", "region") == "us"


def test_system_default_used_when_user_absent(settings_file, system_file):
    """System values act as defaults when the user has not set them."""
    _write_json(system_file, {"record": {"region": "us-east-1"}})
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    assert manager.get("record", "region") == "us-east-1"


def test_user_overrides_plain_system_default(settings_file, system_file):
    """Plain (non-priority) system values are overridable by the user."""
    _write_json(system_file, {"record": {"region": "us-east-1"}})
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    manager.set("record", "region", "eu-west-1")
    assert manager.get("record", "region") == "eu-west-1"


def test_system_priority_wins(settings_file, system_file, caplog):
    """A system-priority key always returns the system value and ignores user writes."""
    _write_json(system_file, {
        "record": {"region": {"value": "us-east-1", "system_priority": True}},
    })
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)

    with caplog.at_level(logging.WARNING):
        manager.set("record", "region", "eu-west-1")
    assert "system priority" in caplog.text

    assert manager.get("record", "region") == "us-east-1"
    # The write did not land in the user layer.
    assert "record" not in manager._SettingsManager__settings


def test_system_priority_without_value_returns_default(settings_file, system_file):
    """A priority wrapper with no value returns default and ignores the user."""
    _write_json(system_file, {"record": {"region": {"system_priority": True}}})
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    manager.set("record", "region", "eu-west-1")
    assert manager.get("record", "region", default="local") == "local"


def test_explicit_non_priority_wrapper(settings_file, system_file):
    """A wrapper with system_priority=false is an ordinary, overridable default."""
    _write_json(system_file, {
        "record": {"region": {"value": "us-east-1", "system_priority": False}},
    })
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    assert manager.get("record", "region") == "us-east-1"
    manager.set("record", "region", "eu-west-1")
    assert manager.get("record", "region") == "eu-west-1"


def test_get_category_merges_layers(settings_file, system_file):
    """get_category merges system defaults with user overrides, respecting priority."""
    _write_json(system_file, {
        "showtask": {
            "gds": {"value": "klayout", "system_priority": True},
            "def": "openroad",
        },
    })
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    manager.set("showtask", "def", "innovus")   # override plain default
    manager.set("showtask", "vcd", "gtkwave")    # new user-only key
    manager.set("showtask", "gds", "magic")      # attempt to override priority -> ignored

    assert manager.get_category("showtask") == {
        "gds": "klayout",     # system priority -> system wins
        "def": "innovus",     # user override
        "vcd": "gtkwave",     # user only
    }


def test_delete_system_priority_key_ignored(settings_file, system_file, caplog):
    """System-priority settings cannot be deleted."""
    _write_json(system_file, {
        "record": {"region": {"value": "us-east-1", "system_priority": True}},
    })
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    with caplog.at_level(logging.WARNING):
        manager.delete("record", "region")
    assert "system priority" in caplog.text
    assert manager.get("record", "region") == "us-east-1"


def test_save_never_persists_system_layer(settings_file, system_file):
    """Saving only writes the user layer; system defaults/priorities are not copied in."""
    _write_json(system_file, {
        "record": {"region": {"value": "us-east-1", "system_priority": True}},
    })
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    manager.set("showtask", "vcd", "gtkwave")
    manager.save()

    with open(settings_file, encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk == {"showtask": {"vcd": "gtkwave"}}
    assert "record" not in on_disk


def test_malformed_system_file_ignored(settings_file, system_file, caplog):
    """A malformed system file is ignored, and the user layer still works."""
    with open(system_file, "w", encoding="utf-8") as f:
        f.write("{ not valid json")
    with caplog.at_level(logging.ERROR):
        manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    assert "malformed" in caplog.text
    assert manager._SettingsManager__system_settings == {}
    manager.set("record", "region", "eu")
    assert manager.get("record", "region") == "eu"


def test_system_file_not_a_dict_ignored(settings_file, system_file, caplog):
    """A system file that is valid JSON but not an object is ignored."""
    _write_json(system_file, ["not", "a", "dict"])
    with caplog.at_level(logging.WARNING):
        manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    assert "did not contain" in caplog.text
    assert manager._SettingsManager__system_settings == {}


def test_non_dict_category_ignored(settings_file, system_file, caplog):
    """A system category that is not a JSON object is skipped, others still load."""
    _write_json(system_file, {
        "bogus": "not-an-object",
        "record": {"region": "us-east-1"},
    })
    with caplog.at_level(logging.WARNING):
        manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    assert "bogus" in caplog.text
    assert "bogus" not in manager._SettingsManager__system_settings
    assert manager.get("record", "region") == "us-east-1"


def test_mixed_priority_and_plain_in_category(settings_file, system_file):
    """A category may mix priority wrappers, plain wrappers, and bare values."""
    _write_json(system_file, {
        "a": {
            "priority_key": {"value": 1, "system_priority": True},
            "plain_key": {"value": 2, "system_priority": False},
            "bare_key": 3,
        },
    })
    manager = SettingsManager(settings_file, logging.getLogger(), system_filepath=system_file)
    manager.set("a", "priority_key", 99)
    manager.set("a", "plain_key", 99)
    manager.set("a", "bare_key", 99)
    assert manager.get("a", "priority_key") == 1   # system priority -> system wins
    assert manager.get("a", "plain_key") == 99     # overridable
    assert manager.get("a", "bare_key") == 99      # overridable
    assert manager._SettingsManager__priority == {"a": {"priority_key"}}

    # Save should be a safe no-op
    manager.save()
