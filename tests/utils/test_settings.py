import pytest
import errno
import os
import json
import logging
import stat
import threading
import time

import os.path

from unittest.mock import patch

from siliconcompiler.utils import settings as settings_module
from siliconcompiler.utils.multiprocessing import forking
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


def test_set_appends_new_keys_in_write_order(settings_file):
    """A category iterates in the order its keys were written."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('order', 'first', 1)
    manager.set('order', 'second', 2)
    manager.set('order', 'third', 3)

    assert list(manager.get_category('order')) == ['first', 'second', 'third']


def test_set_moves_rewritten_key_to_the_end(settings_file):
    """Re-writing a key moves it to the end of its category rather than updating it in place;
    callers such as OpenTask.register_task read position as precedence.
    """
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('order', 'first', 1)
    manager.set('order', 'second', 2)
    manager.set('order', 'third', 3)

    manager.set('order', 'first', 'rewritten')

    assert list(manager.get_category('order')) == ['second', 'third', 'first']
    assert manager.get('order', 'first') == 'rewritten'


def test_set_reorders_even_when_value_is_unchanged(settings_file):
    """Writing the same value still counts as a fresh write."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('order', 'a', 'x')
    manager.set('order', 'b', 'x')

    manager.set('order', 'a', 'x')

    assert list(manager.get_category('order')) == ['b', 'a']


def test_set_keep_does_not_reorder(settings_file):
    """keep=True skips the write entirely, position included."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('order', 'a', 1)
    manager.set('order', 'b', 2)

    manager.set('order', 'a', 99, keep=True)

    assert list(manager.get_category('order')) == ['a', 'b']
    assert manager.get('order', 'a') == 1


def test_set_ordering_is_per_category(settings_file):
    """Re-writing a key in one category leaves other categories alone."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('one', 'a', 1)
    manager.set('one', 'b', 2)
    manager.set('two', 'a', 1)
    manager.set('two', 'b', 2)

    manager.set('one', 'a', 3)

    assert list(manager.get_category('one')) == ['b', 'a']
    assert list(manager.get_category('two')) == ['a', 'b']


def test_set_ordering_survives_save_and_reload(settings_file):
    """The persisted file keeps the order, so a reload resolves the same way."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set('order', 'first', 1)
    manager.set('order', 'second', 2)
    manager.set('order', 'first', 3)
    manager.save()

    with open(settings_file, encoding='utf-8') as f:
        assert list(json.load(f)['order']) == ['second', 'first']

    reloaded = SettingsManager(settings_file, logging.getLogger())
    assert list(reloaded.get_category('order')) == ['second', 'first']


def test_set_ordering_with_system_layer(settings_file, system_file):
    """System keys lead get_category(); a re-written user key that shadows one keeps the system
    key's slot.
    """
    _write_json(system_file, {'order': {'sys_a': 1, 'sys_b': 2}})
    manager = SettingsManager(settings_file, logging.getLogger(),
                              system_filepath=system_file)

    manager.set('order', 'user_a', 3)
    manager.set('order', 'sys_a', 4)

    assert list(manager.get_category('order')) == ['sys_a', 'sys_b', 'user_a']
    assert manager.get('order', 'sys_a') == 4


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


def test_lock_category_blocks_other_threads(settings_file):
    """A category held open is not readable by another thread until released."""
    manager = SettingsManager(settings_file, logging.getLogger())

    holding = threading.Event()
    observed = []

    def reader():
        holding.wait(timeout=10)
        observed.append(manager.get_category("a"))

    thread = threading.Thread(target=reader)
    with manager.lock_category("a"):
        thread.start()
        manager.set("a", "first", 1)
        holding.set()
        # The reader is now blocked on the category; give it every chance to
        # slip in and read the half-built category before the second write.
        time.sleep(0.5)
        manager.set("a", "second", 2)

    thread.join(timeout=10)
    assert not thread.is_alive()
    assert observed == [{"first": 1, "second": 2}]


def test_lock_category_reentrant_for_holder(settings_file):
    """The holder can still read and write the category it is holding."""
    manager = SettingsManager(settings_file, logging.getLogger())

    with manager.lock_category("a"):
        manager.set("a", "key", 1)
        assert manager.get("a", "key") == 1
        assert manager.get_category("a") == {"key": 1}
        with manager.lock_category("a"):  # nesting is fine too
            manager.set("a", "key", 2)
        manager.delete("a", "key")
        assert manager.get_category("a") == {}


def test_lock_category_leaves_other_categories_alone(settings_file):
    """Holding one category does not block access to any other."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("b", "key", 1)

    done = threading.Event()

    def reader():
        assert manager.get("b", "key") == 1
        done.set()

    with manager.lock_category("a"):
        thread = threading.Thread(target=reader)
        thread.start()
        assert done.wait(timeout=10), "read of an unheld category blocked"
        thread.join(timeout=10)


def test_lock_category_released_on_exception(settings_file):
    """An exception inside the block still releases the category."""
    manager = SettingsManager(settings_file, logging.getLogger())

    with pytest.raises(RuntimeError, match="^boom$"):
        with manager.lock_category("a"):
            manager.set("a", "key", 1)
            raise RuntimeError("boom")

    released = threading.Event()

    def reader():
        manager.get_category("a")
        released.set()

    thread = threading.Thread(target=reader)
    thread.start()
    assert released.wait(timeout=10), "category still held after an exception"
    thread.join(timeout=10)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires fork")
def test_locks_reset_after_fork(settings_file, wait_for_child):
    """A child forked while a thread holds a category lock gets fresh locks instead of blocking."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "key", 1)

    holding = threading.Event()
    release = threading.Event()

    def holder():
        with manager.lock_category("a"):
            holding.set()
            release.wait(timeout=10)

    thread = threading.Thread(target=holder)
    thread.start()
    assert holding.wait(timeout=10)

    with forking():
        pid = os.fork()
    if pid == 0:
        try:
            manager.get_category("a")
            os._exit(0)
        except BaseException:
            os._exit(1)

    try:
        exited, read_ok = wait_for_child(pid)
    finally:
        release.set()
        thread.join(timeout=10)

    assert exited, "forked child blocked on a lock held by a thread it does not have"
    assert read_ok, "forked child failed to read the category"


# --- ATOMIC SAVES ---
posix_only = pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")


@pytest.fixture
def umask():
    """Set the process umask for one test, and put it back."""
    previous = []

    def set_umask(value):
        previous.append(os.umask(value))

    yield set_umask
    if previous:
        os.umask(previous[0])


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def _listing(path):
    return sorted(os.listdir(os.path.dirname(path)))


def _contents(path):
    with open(path, "rb") as f:
        return f.read()


@posix_only
def test_mode_applied_as_created(tmp_path, monkeypatch, umask):
    """The file, its lock and a new directory are private from the start."""
    umask(0o022)

    def no_chmod(*args, **kwargs):
        raise AssertionError("permissions changed after creation")

    monkeypatch.setattr(os, "chmod", no_chmod)
    monkeypatch.setattr(os, "fchmod", no_chmod)

    path = str(tmp_path / "auth" / "store.json")
    manager = SettingsManager(path, logging.getLogger(), mode=0o600)
    manager.set("a", "b", "c")
    manager.save()

    assert _mode(path) == 0o600
    assert _mode(path + ".lock") == 0o600
    assert _mode(tmp_path / "auth") == 0o700


@posix_only
def test_mode_none_new_file_gets_umask(settings_file, umask):
    umask(0o027)
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", "c")
    manager.save()

    assert _mode(settings_file) == 0o640


@posix_only
def test_mode_none_keeps_existing_permissions(settings_file, umask):
    """A file the user made private stays private: the replacement copies its bits."""
    umask(0o022)
    with open(settings_file, "w") as f:
        f.write("{}")
    os.chmod(settings_file, 0o600)

    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", "c")
    manager.save()

    assert _mode(settings_file) == 0o600


def test_save_unserializable_leaves_file(settings_file):
    """Today's truncate-then-write left an empty file behind for this."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", "c")
    manager.save()
    before = _contents(settings_file)
    listing = _listing(settings_file)

    manager.set("a", "b", object())
    with pytest.raises(TypeError):
        manager.save()

    assert _contents(settings_file) == before
    assert _listing(settings_file) == listing


def test_save_failed_write_leaves_file(settings_file, monkeypatch):
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", "c")
    manager.save()
    before = _contents(settings_file)
    listing = _listing(settings_file)

    def fail(*args, **kwargs):
        raise OSError("disk full")

    manager.set("a", "b", "d")
    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match=r"^disk full$"):
        manager.save()

    assert _contents(settings_file) == before
    assert _listing(settings_file) == listing


def test_save_follows_symlink(tmp_path):
    target = tmp_path / "dotfiles" / "settings.json"
    target.parent.mkdir()
    target.write_text("{}")
    link = tmp_path / "settings.json"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create a symlink here")

    manager = SettingsManager(str(link), logging.getLogger())
    manager.set("a", "b", "c")
    manager.save()

    assert os.path.islink(link)
    assert json.loads(target.read_text()) == {"a": {"b": "c"}}


def test_save_retries_refused_replace(settings_file, monkeypatch):
    """Windows refuses a replace while another program has the file open."""
    real_replace = os.replace
    refusals = []

    def refuse_twice(src, dst):
        if len(refusals) < 2:
            refusals.append(dst)
            raise PermissionError("in use")
        real_replace(src, dst)

    monkeypatch.setattr(settings_module, "_REPLACE_RETRY", 5.0)
    monkeypatch.setattr(os, "replace", refuse_twice)

    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", "c")
    manager.save()

    assert len(refusals) == 2
    with open(settings_file) as f:
        assert json.load(f) == {"a": {"b": "c"}}


def test_save_does_not_retry_on_posix(settings_file, monkeypatch):
    def refuse(src, dst):
        raise PermissionError("in use")

    monkeypatch.setattr(settings_module, "_REPLACE_RETRY", 0.0)
    monkeypatch.setattr(os, "replace", refuse)

    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", "c")
    with pytest.raises(PermissionError, match=r"^in use$"):
        manager.save()
    assert _listing(settings_file) == ["config.json.lock"]


def test_save_times_out(settings_file, other_process_lock):
    """save() used to wait on the lock forever."""
    manager = SettingsManager(settings_file, logging.getLogger(), timeout=0.2)
    manager.set("a", "b", "c")

    with other_process_lock.hold(settings_file + ".lock"):
        with pytest.raises(TimeoutError, match=r": another process holds it$"):
            manager.save()

    assert not os.path.exists(settings_file)


def test_save_times_out_on_a_leftover_marker(settings_file, caplog):
    """
    Where files cannot be locked, a marker a killed process left behind makes
    save() fail naming it, rather than poll for ever.
    """
    manager = SettingsManager(settings_file, logging.getLogger(), timeout=0.2)
    manager.set("a", "b", "c")
    with open(settings_file + ".sc_lock", "w"):
        pass

    start = time.monotonic()
    with patch("fasteners.InterProcessLock.acquire", side_effect=RuntimeError("ENOLCK")):
        with pytest.raises(TimeoutError, match=r"config\.json\.sc_lock exists\."):
            manager.save()
    assert time.monotonic() - start < 5
    assert "Failed to save settings" in caplog.text


def test_save_refused_after_load_timeout(settings_file, caplog):
    """The empty copy a timed-out load starts from must not replace the file."""
    settings = SettingsManager(settings_file, logging.getLogger())
    settings.set("keep", "this", True)
    settings.save()
    before = _contents(settings_file)

    with patch("fasteners.InterProcessLock.acquire") as acq:
        acq.return_value = False
        manager = SettingsManager(settings_file, logging.getLogger(), timeout=0.1)

    manager.set("new", "key", 1)
    with pytest.raises(RuntimeError, match=r"was not loaded \(its lock was not had in time\)"):
        manager.save()

    assert _contents(settings_file) == before
    assert "Failed to save settings" in caplog.text


def test_transaction_lifts_save_refusal(settings_file):
    settings = SettingsManager(settings_file, logging.getLogger())
    settings.set("keep", "this", True)
    settings.save()

    with patch("fasteners.InterProcessLock.acquire") as acq:
        acq.return_value = False
        manager = SettingsManager(settings_file, logging.getLogger(), timeout=0.1)

    with manager.transaction():
        manager.set("new", "key", 1)
    manager.save()

    with open(settings_file) as f:
        assert json.load(f) == {"keep": {"this": True}, "new": {"key": 1}}


# --- TRANSACTIONS ---
def test_transaction_keeps_another_managers_write(settings_file):
    """The lost update: both managers loaded before either wrote."""
    first = SettingsManager(settings_file, logging.getLogger())
    second = SettingsManager(settings_file, logging.getLogger())

    with first.transaction():
        first.set("a", "first", 1)
    with second.transaction():
        second.set("a", "second", 2)

    with open(settings_file) as f:
        assert json.load(f) == {"a": {"first": 1, "second": 2}}


def test_transaction_threads_on_two_managers(settings_file):
    """
    Read-modify-write from many threads over two managers loses nothing, which
    needs the lock to be shared by every manager on the file.
    """
    managers = [SettingsManager(settings_file, logging.getLogger(), timeout=30)
                for _ in range(2)]
    errors = []

    def bump(manager):
        try:
            for _ in range(10):
                with manager.transaction():
                    manager.set("count", "n", manager.get("count", "n", 0) + 1)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=bump, args=(managers[i % 2],)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    with open(settings_file) as f:
        assert json.load(f) == {"count": {"n": 40}}


def test_save_waits_for_another_threads_transaction(settings_file):
    """A plain save() used to walk straight into a running transaction."""
    manager = SettingsManager(settings_file, logging.getLogger(), timeout=10)
    inside = threading.Event()
    leave = threading.Event()
    order = []
    errors = []

    def transact():
        try:
            with manager.transaction():
                manager.set("a", "b", 1)
                inside.set()
                leave.wait(timeout=10)
                order.append("transaction")
        except BaseException as e:
            errors.append(e)

    def save():
        manager.save()
        order.append("save")

    first = threading.Thread(target=transact)
    first.start()
    assert inside.wait(timeout=10)

    second = threading.Thread(target=save)
    second.start()
    second.join(timeout=0.3)
    assert second.is_alive(), "save() did not wait for the transaction"

    leave.set()
    first.join(timeout=10)
    second.join(timeout=10)

    assert errors == []
    assert order == ["transaction", "save"]


def test_save_inside_transaction_keeps_the_lock(settings_file, other_process_lock):
    manager = SettingsManager(settings_file, logging.getLogger())
    lockfile = settings_file + ".lock"

    with manager.transaction():
        manager.set("a", "b", 1)
        manager.save()
        assert not other_process_lock.can_take(lockfile)
        manager.set("a", "c", 2)

    assert other_process_lock.can_take(lockfile)
    with open(settings_file) as f:
        assert json.load(f) == {"a": {"b": 1, "c": 2}}


def test_transaction_lock_held_by_another_process(settings_file, other_process_lock):
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", 1)
    manager.save()
    before = _contents(settings_file)

    with other_process_lock.hold(settings_file + ".lock"):
        with pytest.raises(TimeoutError, match=r": another process holds it$"):
            with manager.transaction(timeout=0.2):
                pytest.fail("should not get here")

    assert _contents(settings_file) == before


def test_transaction_where_files_cannot_be_locked(settings_file):
    """As on an NFS home without lock support: the fallback marker holds it."""
    manager = SettingsManager(settings_file, logging.getLogger())
    marker = settings_file + ".sc_lock"

    with patch("fasteners.InterProcessLock.acquire", side_effect=RuntimeError("ENOLCK")):
        with manager.transaction():
            assert os.path.exists(marker)
            manager.set("a", "b", 1)
        assert not os.path.exists(marker)

        # A marker a killed process left behind is named, not broken
        with open(marker, "w"):
            pass
        with pytest.raises(TimeoutError, match=r"config\.json\.sc_lock exists\."):
            with manager.transaction(timeout=0.2):
                pytest.fail("should not get here")

    with open(settings_file) as f:
        assert json.load(f) == {"a": {"b": 1}}


def test_transaction_lock_held_by_another_thread(settings_file):
    """The timeout bounds the wait on this process's threads too."""
    manager = SettingsManager(settings_file, logging.getLogger())
    holding = threading.Event()
    release = threading.Event()

    def holder():
        with manager.transaction():
            holding.set()
            release.wait(timeout=10)

    thread = threading.Thread(target=holder)
    thread.start()
    try:
        assert holding.wait(timeout=10)
        start = time.monotonic()
        with pytest.raises(TimeoutError, match=r"another thread of this process holds it$"):
            with manager.transaction(timeout=0.2):
                pytest.fail("should not get here")
        assert time.monotonic() - start < 5
    finally:
        release.set()
        thread.join(timeout=10)


def test_transaction_accessors(settings_file):
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "gone", 0)
    manager.save()

    reached = threading.Event()
    read = []

    def reader():
        reached.set()
        read.append(manager.get_category("a"))

    with manager.transaction():
        manager.set("a", "b", 1)
        assert manager.get("a", "b") == 1
        manager.delete("a", "gone")
        assert manager.get_category("a") == {"b": 1}

        with manager.lock_category("a"):
            manager.set("a", "c", 2)
            thread = threading.Thread(target=reader)
            thread.start()
            assert reached.wait(timeout=10)
            thread.join(timeout=0.2)
            assert thread.is_alive(), "lock_category did not hold the other thread"
            manager.set("a", "d", 3)
        thread.join(timeout=10)

    assert read == [{"b": 1, "c": 2, "d": 3}]
    with open(settings_file) as f:
        assert json.load(f) == {"a": {"b": 1, "c": 2, "d": 3}}


def test_transaction_exception_saves_nothing(settings_file):
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "x", 1)
    manager.save()
    before = _contents(settings_file)

    with pytest.raises(ValueError, match=r"^boom$"):
        with manager.transaction():
            manager.set("a", "y", 2)
            raise ValueError("boom")

    assert _contents(settings_file) == before
    assert manager.get_category("a") == {"x": 1}

    # Nothing left held
    with manager.transaction(timeout=0.2):
        pass


def test_transaction_unserializable_saves_nothing(settings_file):
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "x", 1)
    manager.save()
    before = _contents(settings_file)

    with pytest.raises(TypeError):
        with manager.transaction():
            manager.set("a", "y", object())

    assert _contents(settings_file) == before
    assert manager.get_category("a") == {"x": 1}


@pytest.mark.parametrize("contents,message", [
    ("{ this is not json }", r"is malformed"),
    ("[1, 2, 3]", r"does not hold a JSON object"),
])
def test_transaction_refuses_unreadable_file(settings_file, contents, message):
    with open(settings_file, "w") as f:
        f.write(contents)

    manager = SettingsManager(settings_file, logging.getLogger())
    with pytest.raises(ValueError, match=message):
        with manager.transaction():
            manager.set("a", "b", 1)

    with open(settings_file) as f:
        assert f.read() == contents


def test_transaction_unchanged_writes_nothing(settings_file):
    manager = SettingsManager(settings_file, logging.getLogger())
    with manager.transaction():
        assert manager.get("a", "b") is None
    assert not os.path.exists(settings_file)

    manager.set("a", "b", 1)
    manager.save()
    inode = os.stat(settings_file).st_ino

    with manager.transaction():
        manager.set("a", "b", 1)

    assert os.stat(settings_file).st_ino == inode


def test_transaction_saves_a_reorder(settings_file):
    """Key order carries meaning, so moving a key is a change."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "first", 1)
    manager.set("a", "second", 2)
    manager.save()

    with manager.transaction():
        manager.set("a", "first", 1)

    with open(settings_file) as f:
        assert list(json.load(f)["a"]) == ["second", "first"]


def test_transaction_nested(settings_file):
    manager = SettingsManager(settings_file, logging.getLogger())

    with manager.transaction():
        manager.set("a", "outer", 1)
        with manager.transaction():
            manager.set("a", "inner", 2)
        assert not os.path.exists(settings_file), "the inner transaction saved"

    with open(settings_file) as f:
        assert json.load(f) == {"a": {"outer": 1, "inner": 2}}


def test_transaction_discards_unsaved_changes(settings_file):
    """Documented: a transaction starts from the file."""
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "unsaved", 1)

    with manager.transaction():
        assert manager.get("a", "unsaved") is None


def test_transaction_without_file():
    manager = SettingsManager(None, logging.getLogger())
    holding = threading.Event()
    release = threading.Event()

    def holder():
        with manager.transaction():
            holding.set()
            release.wait(timeout=10)

    thread = threading.Thread(target=holder)
    thread.start()
    try:
        assert holding.wait(timeout=10)
        with pytest.raises(TimeoutError, match=r"another thread of this process holds it$"):
            with manager.transaction(timeout=0.2):
                pytest.fail("should not get here")
    finally:
        release.set()
        thread.join(timeout=10)

    with manager.transaction():
        manager.set("a", "b", 1)
    assert manager.get("a", "b") == 1


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires fork")
def test_transaction_locks_reset_after_fork(settings_file, wait_for_child):
    """
    A child forked while a thread is in a transaction does not wait on that
    thread: a file-less transaction runs, and a file transaction waits on the
    parent process, which still holds the file.
    """
    manager = SettingsManager(settings_file, logging.getLogger())
    memory = SettingsManager(None, logging.getLogger())

    holding = threading.Event()
    release = threading.Event()

    def holder():
        with manager.transaction(), memory.transaction():
            holding.set()
            release.wait(timeout=10)

    thread = threading.Thread(target=holder)
    thread.start()
    assert holding.wait(timeout=10)

    with forking():
        pid = os.fork()
    if pid == 0:
        try:
            with memory.transaction(timeout=5):
                pass
            try:
                with manager.transaction(timeout=0.2):
                    os._exit(2)
            except TimeoutError as e:
                os._exit(0 if str(e).endswith(": another process holds it") else 3)
        except BaseException:
            os._exit(1)

    try:
        exited, as_expected = wait_for_child(pid)
    finally:
        release.set()
        thread.join(timeout=10)

    assert exited, "forked child blocked on a lock held by a thread it does not have"
    assert as_expected, "forked child did not run its own transaction or wait on its parent"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires fork")
def test_transaction_does_not_commit_in_a_forked_child(settings_file, wait_for_child,
                                                       other_process_lock):
    """
    A child forked by the thread inside a transaction inherits the block, and
    used to commit it on the way out -- writing the file while its parent held
    the lock. It raises instead, and writes nothing.
    """
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "before", 1)
    manager.save()

    pid = None
    try:
        with manager.transaction():
            manager.set("a", "parent", 1)
            with forking():
                pid = os.fork()
            if pid == 0:
                manager.set("a", "child", 1)
            else:
                exited, clean = wait_for_child(pid)
                held = not other_process_lock.can_take(settings_file + ".lock")
                with open(settings_file) as f:
                    while_held = json.load(f)
    except RuntimeError as e:
        if pid == 0:
            os._exit(0 if "forked" in str(e) else 2)
        raise
    except BaseException:
        if pid == 0:
            os._exit(3)
        raise
    if pid == 0:
        os._exit(4)

    assert exited and clean, "the child committed its parent's transaction"
    assert held, "the child released its parent's lock"
    assert while_held == {"a": {"before": 1}}, "the child wrote the file"
    with open(settings_file) as f:
        assert json.load(f) == {"a": {"before": 1, "parent": 1}}


@posix_only
def test_save_syncs_the_directory(settings_file, monkeypatch):
    """The rename reaches the disk before save() returns, not only the contents."""
    synced = []
    real_fsync = os.fsync

    def fsync(fd):
        synced.append(stat.S_ISDIR(os.fstat(fd).st_mode))
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", "c")
    manager.save()

    # The temporary file, then the directory it was renamed in
    assert synced == [False, True]


@posix_only
def test_save_where_the_directory_cannot_be_synced(settings_file, monkeypatch):
    """Some filesystems refuse to sync a directory; the rename has still happened."""
    real_fsync = os.fsync

    def fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "not supported")
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    manager = SettingsManager(settings_file, logging.getLogger())
    manager.set("a", "b", "c")
    manager.save()

    with open(settings_file) as f:
        assert json.load(f) == {"a": {"b": "c"}}
