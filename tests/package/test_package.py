import contextlib
import logging
import pytest

import os.path

from pathlib import Path
from unittest.mock import patch

import siliconcompiler

from siliconcompiler.package import Resolver, RemoteResolver
from siliconcompiler.package import FileResolver, PythonPathResolver, KeyPathResolver
from siliconcompiler.package import InterProcessLock as dut_ipl

from siliconcompiler import Chip


def test_init():
    resolver = Resolver("testpath", Chip("dummy"), "source://this")

    assert resolver.name == "testpath"
    assert resolver.source == "source://this"
    assert resolver.reference is None
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)


def test_init_no_root():
    resolver = Resolver("testpath", None, "source://this")

    assert resolver.name == "testpath"
    assert resolver.source == "source://this"
    assert resolver.reference is None
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)


def test_init_with_ref():
    resolver = Resolver("testpath", Chip("dummy"), "source://this", reference="ref")

    assert resolver.name == "testpath"
    assert resolver.source == "source://this"
    assert resolver.reference == "ref"
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)


def test_init_with_env(monkeypatch):
    resolver = Resolver("testpath", Chip("dummy"), "source://${FILE_PATH}", reference="ref")

    monkeypatch.setenv("FILE_PATH", "this")

    assert resolver.name == "testpath"
    assert resolver.source == "source://${FILE_PATH}"
    assert resolver.reference == "ref"
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)


def test_init_with_env_chip():
    chip = Chip("dummy")
    chip.set("option", "env", "FILE_PATH", "this")
    resolver = Resolver("testpath", chip, "source://${FILE_PATH}", reference="ref")

    assert resolver.name == "testpath"
    assert resolver.root is chip
    assert resolver.source == "source://${FILE_PATH}"
    assert resolver.reference == "ref"
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)


def test_resolve():
    resolver = Resolver("testpath", Chip("dummy"), "source://this")
    with pytest.raises(NotImplementedError, match="child class must implement this"):
        resolver.resolve()


def test_find_resolver_not_found():
    with pytest.raises(ValueError, match="nosupport://help.me/file is not supported"):
        Resolver.find_resolver("nosupport://help.me/file")


def test_find_resolver_key():
    assert Resolver.find_resolver("key://this") is KeyPathResolver


def test_find_resolver_file():
    assert Resolver.find_resolver("file://this") is FileResolver


def test_find_resolver_file_dot():
    assert Resolver.find_resolver(".") is FileResolver


def test_find_resolver_file_empty():
    assert Resolver.find_resolver("/this/path") is FileResolver


def test_find_resolver_python():
    assert Resolver.find_resolver("python://siliconcompiler") is PythonPathResolver


def test_get_path_new_data(caplog):
    class AlwaysNew(RemoteResolver):
        def check_cache(self):
            return False

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            pass

    os.makedirs("path", exist_ok=True)

    chip = Chip("dummy")
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    resolver = AlwaysNew("alwaysnew", chip, "notused", "notused")
    assert resolver.get_path() == os.path.abspath("path")

    assert "Saved alwaysnew data to " in caplog.text


def test_get_path_old_data(caplog):
    class AlwaysOld(RemoteResolver):
        def check_cache(self):
            return True

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            pass

    os.makedirs("path", exist_ok=True)

    chip = Chip("dummy")
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    resolver = AlwaysOld("alwaysold", chip, "notused", "notused")
    assert resolver.get_path() == os.path.abspath("path")

    assert "Found alwaysold data at " in caplog.text


def test_get_path_usecache(caplog):
    class AlwaysCache(RemoteResolver):
        def check_cache(self):
            return True

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            pass

    os.makedirs("path", exist_ok=True)

    chip = Chip("dummy")
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    resolver = AlwaysCache("alwayscache", chip, "notused", "notused")
    Resolver.set_cache(chip, "alwayscache", "path")
    assert resolver.get_path() == "path"

    assert caplog.text == ""


def test_get_path_not_found():
    class AlwaysOld(RemoteResolver):
        def check_cache(self):
            return True

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            pass

    chip = Chip("dummy")
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    resolver = AlwaysOld("alwaysmissing", chip, "notused", "notused")
    with pytest.raises(FileNotFoundError, match="Unable to locate alwaysmissing at .*path"):
        resolver.get_path()


def test_remote_init():
    resolver = RemoteResolver("thisname", Chip("dummy"), "https://filepath", "ref")

    assert resolver.name == "thisname"
    assert resolver.source == "https://filepath"
    assert resolver.reference == "ref"
    assert resolver.urlscheme == "https"
    assert resolver.urlpath == "filepath"
    assert isinstance(resolver.logger, logging.Logger)


def test_remote_init_no_ref():
    with pytest.raises(ValueError, match="Reference is required for cached data: thisname"):
        RemoteResolver("thisname", Chip("dummy"), "https://filepath")


def test_remote_child_impl():
    resolver = RemoteResolver("thisname", Chip("dummy"), "https://filepath", "ref")

    with pytest.raises(NotImplementedError, match="child class must implement this"):
        resolver.resolve_remote()

    with pytest.raises(NotImplementedError, match="child class must implement this"):
        resolver.check_cache()


def test_remote_cache_dir_default():
    resolver = RemoteResolver("thisname", Chip("dummy"), "https://filepath", "ref")
    assert resolver.cache_dir == Path.home() / ".sc" / "cache"


def test_remote_cache_dir_no_root():
    resolver = RemoteResolver("thisname", None, "https://filepath", "ref")
    assert resolver.cache_dir == Path.home() / ".sc" / "cache"


def test_remote_cache_dir_from_schema():
    chip = Chip("dummy")
    chip.set("option", "cachedir", os.path.abspath("."))
    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")
    assert resolver.cache_dir == Path(os.path.abspath("."))


def test_remote_cache_dir_from_schema_not_found():
    chip = Chip("dummy")
    chip.set("option", "cachedir", "thispath")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")
    assert resolver.cache_dir == Path(os.path.abspath("thispath"))


def test_remote_cache_name():
    resolver = RemoteResolver("thisname", Chip("dummy"), "https://filepath", "ref")
    assert resolver.cache_name == "thisname-ref"


def test_remote_cache_path():
    chip = Chip("dummy")
    chip.set("option", "cachedir", "thispath")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")
    with patch("os.makedirs") as mkdir:
        assert resolver.cache_path == Path(os.path.abspath("thispath/thisname-ref"))
        mkdir.assert_called_once()


def test_remote_cache_path_cache_exist():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")
    with patch("os.makedirs") as mkdir:
        assert resolver.cache_path == Path(os.path.abspath("thisname-ref"))
        mkdir.assert_not_called()


def test_remote_lock_file():
    chip = Chip("dummy")
    chip.set("option", "cachedir", "thispath")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")
    with patch("os.makedirs") as mkdir:
        assert resolver.lock_file == Path(os.path.abspath("thispath/thisname-ref.lock"))
        mkdir.assert_called_once()


def test_remote_sc_lock_file():
    chip = Chip("dummy")
    chip.set("option", "cachedir", "thispath")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")
    with patch("os.makedirs") as mkdir:
        assert resolver.sc_lock_file == Path(os.path.abspath("thispath/thisname-ref.sc_lock"))
        mkdir.assert_called_once()


def test_remote_resolve_cached():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")

    with patch("siliconcompiler.package.RemoteResolver.lock") as lock, \
         patch("siliconcompiler.package.RemoteResolver.check_cache") as check_cache, \
         patch("siliconcompiler.package.RemoteResolver.resolve_remote") as resolve_remote:
        check_cache.return_value = True
        assert resolver.resolve() == Path(os.path.abspath("thisname-ref"))
        lock.assert_called_once()
        check_cache.assert_called_once()
        resolve_remote.assert_not_called()


def test_remote_resolve():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")

    with patch("siliconcompiler.package.RemoteResolver.lock") as lock, \
         patch("siliconcompiler.package.RemoteResolver.check_cache") as check_cache, \
         patch("siliconcompiler.package.RemoteResolver.resolve_remote") as resolve_remote:
        check_cache.return_value = False
        assert resolver.resolve() == Path(os.path.abspath("thisname-ref"))
        lock.assert_called_once()
        check_cache.assert_called_once()
        resolve_remote.assert_called_once()


def test_remote_lock():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")

    with resolver.lock():
        assert os.path.exists(resolver.lock_file)
        assert not os.path.exists(resolver.sc_lock_file)

    assert os.path.exists(resolver.lock_file)
    assert not os.path.exists(resolver.sc_lock_file)


def test_remote_lock_after_lock():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")

    with resolver.lock():
        assert os.path.exists(resolver.lock_file)
        assert not os.path.exists(resolver.sc_lock_file)

    assert os.path.exists(resolver.lock_file)
    assert not os.path.exists(resolver.sc_lock_file)

    with resolver.lock():
        assert os.path.exists(resolver.lock_file)
        assert not os.path.exists(resolver.sc_lock_file)

    assert os.path.exists(resolver.lock_file)
    assert not os.path.exists(resolver.sc_lock_file)


def test_remote_lock_within_lock_thread():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver0 = RemoteResolver("thisname", chip, "https://filepath", "ref")
    resolver1 = RemoteResolver("thisname", chip, "https://filepath", "ref")

    # change second resolver to wait 1 second
    resolver1.set_timeout(1)
    assert resolver1.timeout == 1

    with resolver0.lock():
        assert os.path.exists(resolver0.lock_file)
        assert not os.path.exists(resolver0.sc_lock_file)

        with pytest.raises(RuntimeError, match="Failed to access .*. "
                                               "Another thread is currently holding the lock."):
            with resolver1.lock():
                assert False, "should not get here"

    assert os.path.exists(resolver0.lock_file)
    assert not os.path.exists(resolver0.sc_lock_file)


def test_remote_lock_within_lock_thread_multiple_tries(monkeypatch):
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver0 = RemoteResolver("thisname", chip, "https://filepath", "ref")
    resolver1 = RemoteResolver("thisname", chip, "https://filepath", "ref")

    # change second resolver to wait 10 second
    resolver1.set_timeout(10)
    assert resolver1.timeout == 10

    # Allow filelock to pass
    @contextlib.contextmanager
    def dummy_lock():
        yield
    monkeypatch.setattr(resolver0, "_RemoteResolver__file_lock", dummy_lock)

    with resolver0.lock():
        class DummyLock:
            def __init__(self):
                self.calls = 0
                pass

            def acquire_lock(self, timeout=None):
                self.calls += 1
                if self.calls == 1:
                    return False
                return True

            def locked(self):
                return False

        lock = DummyLock()

        def gen_dummy_lock(*args, **kwargs):
            return lock

        monkeypatch.setattr(RemoteResolver, "thread_lock", gen_dummy_lock)
        with resolver1.lock():
            assert lock.calls == 2
        assert lock.calls == 2

    assert os.path.exists(resolver0.lock_file)
    assert not os.path.exists(resolver0.sc_lock_file)


def test_remote_lock_within_lock_file(monkeypatch):
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver0 = RemoteResolver("thisname", chip, "https://filepath", "ref")
    resolver1 = RemoteResolver("thisname", chip, "https://filepath", "ref")

    # change second resolver to wait 1 second
    resolver1.set_timeout(1)
    assert resolver1.timeout == 1

    # Allow threadlock to pass
    @contextlib.contextmanager
    def dummy_lock():
        yield
    monkeypatch.setattr(resolver0, "_RemoteResolver__thread_lock", dummy_lock)

    with resolver0.lock():
        assert os.path.exists(resolver0.lock_file)
        assert not os.path.exists(resolver0.sc_lock_file)

        def dummy_lock(*args, **kwargs):
            return False
        monkeypatch.setattr(dut_ipl, "acquire", dummy_lock)
        with pytest.raises(RuntimeError, match="Failed to access .*. .* is still locked, "
                                               "if this is a mistake, please delete it."):
            with resolver1.lock():
                pass

    assert os.path.exists(resolver0.lock_file)
    assert not os.path.exists(resolver0.sc_lock_file)


def test_remote_lock_exception():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")

    with pytest.raises(ValueError):
        with resolver.lock():
            assert os.path.exists(resolver.lock_file)
            assert not os.path.exists(resolver.sc_lock_file)
            raise ValueError

    assert os.path.exists(resolver.lock_file)
    assert not os.path.exists(resolver.sc_lock_file)

    # try lock again
    with pytest.raises(ValueError):
        with resolver.lock():
            assert os.path.exists(resolver.lock_file)
            assert not os.path.exists(resolver.sc_lock_file)
            raise ValueError


def test_remote_lock_failed():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")
    resolver.set_timeout(1)

    with patch("fasteners.InterProcessLock.acquire") as acquire:
        acquire.return_value = False
        with pytest.raises(RuntimeError,
                           match="Failed to access .*.lock is still locked, if this is a mistake, "
                                 "please delete it"):
            with resolver.lock():
                assert False, "Should not gain lock"
            acquire.assert_called_once()

    assert not os.path.exists(resolver.lock_file)
    assert not os.path.exists(resolver.sc_lock_file)


def test_remote_lock_revert_to_file():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")

    with patch("fasteners.InterProcessLock.acquire") as acquire:
        def fail_lock(*args, **kwargs):
            raise RuntimeError
        acquire.side_effect = fail_lock

        with resolver.lock():
            assert not os.path.exists(resolver.lock_file)
            assert os.path.exists(resolver.sc_lock_file)

    assert not os.path.exists(resolver.lock_file)
    assert not os.path.exists(resolver.sc_lock_file)


def test_remote_lock_revert_to_file_failed():
    chip = Chip("dummy")
    chip.set("option", "cachedir", ".")

    resolver = RemoteResolver("thisname", chip, "https://filepath", "ref")

    with patch("fasteners.InterProcessLock.acquire") as acquire, \
         patch("time.sleep") as sleep:
        def fail_lock(*args, **kwargs):
            raise RuntimeError
        acquire.side_effect = fail_lock

        # Generate lock
        resolver.sc_lock_file.touch()

        with pytest.raises(RuntimeError,
                           match="Failed to access .*. Lock .* still exists"):
            with resolver.lock():
                pass

        assert sleep.call_count == 600

    assert not os.path.exists(resolver.lock_file)
    assert os.path.exists(resolver.sc_lock_file)


def test_file_resolver_abs_path():
    resolver = FileResolver("thisname", Chip("dummy"), os.path.abspath("test"))
    assert resolver.resolve() == os.path.abspath("test")


def test_file_resolver_with_file():
    resolver = FileResolver("thisname", Chip("dummy"), "file://test")
    assert resolver.resolve() == os.path.abspath("test")


def test_file_resolver_with_abspath():
    resolver = FileResolver("thisname", Chip("dummy"), f"file://{os.path.abspath('../test')}")
    assert resolver.resolve() == os.path.abspath("../test")


def test_file_resolver_with_relpath():
    resolver = FileResolver("thisname", Chip("dummy"), "file://test")
    assert resolver.resolve() == os.path.abspath("test")


def test_python_path_resolver():
    resolver = PythonPathResolver("thisname", Chip("dummy"), "python://siliconcompiler")
    assert resolver.resolve() == os.path.dirname(siliconcompiler.__file__)


def test_keypath_resolver():
    chip = Chip("dummy")
    chip.set("option", "dir", "testdir", ".")

    resolver = KeyPathResolver("thisname", chip, "key://option,dir,testdir")
    assert resolver.resolve() == os.path.abspath(".")


def test_keypath_resolver_no_root():
    resolver = KeyPathResolver("thisname", None, "key://option,dir,testdir")
    with pytest.raises(RuntimeError, match="Root schema has not be defined for thisname"):
        resolver.resolve()


def test_get_cache():
    chip = Chip("dummy")
    assert Resolver.get_cache(chip) == {}


def test_set_cache():
    chip = Chip("dummy")
    assert Resolver.get_cache(chip) == {}
    Resolver.set_cache(chip, "test", "path")
    assert Resolver.get_cache(chip) == {
        "test": "path"
    }
    Resolver.set_cache(chip, "test0", "path0")
    assert Resolver.get_cache(chip) == {
        "test": "path",
        "test0": "path0",
    }


def test_set_cache_different_chips():
    chip0 = Chip("dummy")
    chip1 = Chip("dummy")

    assert Resolver.get_cache(chip0) == {}
    assert Resolver.get_cache(chip1) == {}

    Resolver.set_cache(chip0, "test", "path")
    assert Resolver.get_cache(chip0) == {
        "test": "path"
    }
    assert Resolver.get_cache(chip1) == {}

    Resolver.set_cache(chip1, "test0", "path0")
    assert Resolver.get_cache(chip0) == {
        "test": "path"
    }
    assert Resolver.get_cache(chip1) == {
        "test0": "path0",
    }


def test_reset_cache():
    chip = Chip("dummy")

    assert Resolver.get_cache(chip) == {}

    Resolver.set_cache(chip, "test", "path")
    assert Resolver.get_cache(chip) == {
        "test": "path"
    }

    Resolver.reset_cache(chip)
    assert Resolver.get_cache(chip) == {}
