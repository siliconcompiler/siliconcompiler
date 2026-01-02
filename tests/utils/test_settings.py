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

    # Save should be a safe no-op
    manager.save()
