import contextlib
import logging
import os
import pytest
import shutil
import stat
import sys

import os.path

from pathlib import Path
from unittest.mock import patch

import siliconcompiler

from siliconcompiler.package import Resolver, RemoteResolver
from siliconcompiler.package import FileResolver, PythonPathResolver, KeyPathResolver
from siliconcompiler.package import InterProcessLock as dut_ipl

from siliconcompiler import Project, Design
from siliconcompiler.schema import BaseSchema


def test_init():
    resolver = Resolver("testpath", Project("testproj"), "source://this")

    assert resolver.name == "testpath"
    assert resolver.source == "source://this"
    assert resolver.reference is None
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)
    assert resolver.cache_id == "2e7ef7cca5512780f587a0f30afe2ff574bc1448"


def test_init_no_root():
    resolver = Resolver("testpath", None, "source://this")

    assert resolver.name == "testpath"
    assert resolver.source == "source://this"
    assert resolver.reference is None
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)
    assert resolver.cache_id == "2e7ef7cca5512780f587a0f30afe2ff574bc1448"


def test_init_with_ref():
    resolver = Resolver("testpath", Project("testproj"), "source://this", reference="ref")

    assert resolver.name == "testpath"
    assert resolver.source == "source://this"
    assert resolver.reference == "ref"
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)
    assert resolver.cache_id == "0b0f5cbd0aba45a46024a52b4dd543d56b09f5df"


def test_init_with_env(monkeypatch):
    resolver = Resolver("testpath", Project("testproj"), "source://${FILE_PATH}", reference="ref")

    monkeypatch.setenv("FILE_PATH", "this")

    assert resolver.name == "testpath"
    assert resolver.source == "source://${FILE_PATH}"
    assert resolver.reference == "ref"
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)
    assert resolver.cache_id == "44aae5e357af88c30de3ad29ee77f70bb8aa9b9d"


def test_init_with_env_project():
    project = Project("testproj")
    project.set("option", "env", "FILE_PATH", "this")
    resolver = Resolver("testpath", project, "source://${FILE_PATH}", reference="ref")

    assert resolver.name == "testpath"
    assert resolver.root is project
    assert resolver.source == "source://${FILE_PATH}"
    assert resolver.reference == "ref"
    assert resolver.urlscheme == "source"
    assert resolver.urlpath == "this"
    assert isinstance(resolver.logger, logging.Logger)


def test_resolve():
    resolver = Resolver("testpath", Project("testproj"), "source://this")
    with pytest.raises(NotImplementedError, match=r"^child class must implement this$"):
        resolver.resolve()


def test_display_name_with_schema():
    """Test display_name returns name when schema exists but has empty keypath."""
    project = Project("testproj")
    resolver = Resolver("mydata", project, "source://this")

    # For root-level schemas with empty keypath, display_name should be just the name
    display = resolver.display_name
    assert display == "mydata"


def test_display_name_without_schema():
    """Test display_name returns just the name when no schema is provided."""
    resolver = Resolver("mydata", None, "source://this")

    # display_name should be just the name without keypath
    assert resolver.display_name == "mydata"


def test_display_name_with_nested_schema():
    """Test display_name includes keypath when schema is nested."""
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.add_idir(".")

    project = Project(design)

    # Get a nested design schema from the project
    library_design = project.get("library", "testdesign", field="schema")
    resolver = Resolver("packagedata", library_design, "source://this")

    # display_name should include the keypath in brackets
    display = resolver.display_name
    assert display == "packagedata [library,testdesign]"


def test_display_name_consistency():
    """Test that display_name is consistent across multiple calls."""
    project = Project("testproj")
    resolver = Resolver("data", project, "source://path")

    # Multiple calls should return the same value
    display1 = resolver.display_name
    display2 = resolver.display_name
    assert display1 == display2


def test_display_name_format_with_keypath():
    """Test that display_name follows the expected format when keypath exists."""
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.add_idir(".")

    project = Project(design)
    library_design = project.get("library", "testdesign", field="schema")

    resolver = Resolver("myresolver", library_design, "source://this")

    # Format should be: "name [keypath,...]"
    display = resolver.display_name
    # Should have brackets and the name at the start
    assert display.startswith("myresolver [")
    assert display.endswith("]")


def test_find_resolver_not_found():
    with pytest.raises(ValueError,
                       match=r"^Source URI 'nosupport://help.me/file' is not supported$"):
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


def test_file_env_var():
    resolver = FileResolver("test", None, "$THIS_PATH/hello")
    assert resolver.source == "file://$THIS_PATH/hello"
    assert resolver.urlpath == "$THIS_PATH/hello"
    assert resolver.resolve() == "$THIS_PATH/hello"


def test_file_env_var_cwd(monkeypatch):
    class TestProject(Project):
        def valid(*_args, **_kwargs):
            return False

    project = TestProject()
    monkeypatch.setattr(project, "_Project__cwd", "thiscwd")

    resolver = FileResolver("test", project, "THIS_PATH/$hello")
    path = os.path.join("thiscwd", "THIS_PATH/$hello")
    assert resolver.source == f"file://{path}"
    assert resolver.urlpath == path


def test_file_source_rel_cwd(monkeypatch):
    class TestProject(Project):
        def valid(*_args, **_kwargs):
            return False

    project = TestProject()
    monkeypatch.setattr(project, "_Project__cwd", "thiscwd")

    resolver = FileResolver("test", project, "THIS_PATH/hello")
    path = os.path.join("thiscwd", "THIS_PATH/hello")
    assert resolver.source == f"file://{path}"
    assert resolver.urlpath == path


def test_file_source_abs():
    abspath = os.path.abspath("abs")
    resolver = FileResolver("test", None, abspath)
    assert resolver.source == f"file://{abspath}"
    assert resolver.urlpath == abspath


def test_file_env_var_with_scheme():
    resolver = FileResolver("test", None, "file://$THIS_PATH/hello")
    assert resolver.source == "file://$THIS_PATH/hello"
    assert resolver.urlpath == "$THIS_PATH/hello"


def test_file_env_var_start_with_root():
    class Project(BaseSchema):
        __cwd = "thiscwd"

        def valid(*_args, **_kwargs):  # keep interface, silence linters
            return False

    resolver = FileResolver("test", Project(), "$THIS_PATH/hello")
    assert resolver.source == "file://$THIS_PATH/hello"
    assert resolver.urlpath == "$THIS_PATH/hello"
    assert resolver.resolve() == "$THIS_PATH/hello"


def test_file_env_var_brace_form():
    resolver = FileResolver("test", None, "${THIS_PATH}/hello")
    assert resolver.source == "file://${THIS_PATH}/hello"
    assert resolver.urlpath == "${THIS_PATH}/hello"


def test_cache_id_different_name():
    res0 = Resolver("testpath0", Project("testproj"), "file://.", reference="ref")
    res1 = Resolver("testpath1", Project("testproj"), "file://.", reference="ref")

    assert res0.cache_id == res1.cache_id


def test_cache_id_different_ref():
    res0 = Resolver("testpath0", Project("testproj"), "file://.", reference="ref0")
    res1 = Resolver("testpath1", Project("testproj"), "file://.", reference="ref1")

    assert res0.cache_id != res1.cache_id


def test_cache_id_different_source():
    res0 = Resolver("testpath0", Project("testproj"), "file://test0", reference="ref")
    res1 = Resolver("testpath1", Project("testproj"), "file://test1", reference="ref")

    assert res0.cache_id != res1.cache_id


def test_get_path_new_data(monkeypatch, caplog):
    class AlwaysNew(RemoteResolver):
        def check_cache(self):
            return False

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            pass

    os.makedirs("path", exist_ok=True)

    proj = Project("testproj")
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    resolver = AlwaysNew("alwaysnew", proj, "notused", "notused")
    assert resolver.get_path() == os.path.abspath("path")

    assert "Saved alwaysnew data to " in caplog.text


@pytest.mark.parametrize("errorcls", (KeyboardInterrupt, IOError, SystemExit))
def test_get_path_new_data_error(errorcls):
    class AlwaysNew(RemoteResolver):
        def check_cache(self):
            return False

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            raise errorcls("Match me")

    os.makedirs("path", exist_ok=True)

    proj = Project("testproj")

    resolver = AlwaysNew("alwaysnew", proj, "notused", "notused")
    with patch("shutil.rmtree") as rmtree:
        with pytest.raises(errorcls, match=r"^Match me$"):
            resolver.get_path()
        rmtree.assert_called_once_with(os.path.abspath("path"))


@pytest.mark.parametrize("errorcls", (KeyboardInterrupt, IOError, SystemExit))
def test_get_path_new_data_error_failed_to_clean(errorcls, monkeypatch, caplog):
    class AlwaysNew(RemoteResolver):
        def check_cache(self):
            return False

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            raise KeyboardInterrupt("Match me")

    os.makedirs("path", exist_ok=True)

    proj = Project("testproj")
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    def dummy_rm(tree):
        raise errorcls("this error")

    resolver = AlwaysNew("alwaysnew", proj, "notused", "notused")
    with patch("shutil.rmtree") as rmtree:
        rmtree.side_effect = dummy_rm
        with pytest.raises(KeyboardInterrupt, match=r"^Match me$"):
            resolver.get_path()
        rmtree.assert_called_once_with(os.path.abspath("path"))

    assert f"Exception occurred during cleanup: this error ({errorcls.__name__})" in caplog.text


def test_get_path_old_data(monkeypatch, caplog):
    class AlwaysOld(RemoteResolver):
        def check_cache(self):
            return True

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            pass

    os.makedirs("path", exist_ok=True)

    proj = Project("testproj")
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    resolver = AlwaysOld("alwaysold", proj, "notused", "notused")
    assert resolver.get_path() == os.path.abspath("path")

    assert "Found alwaysold data at " in caplog.text


def test_get_path_usecache(monkeypatch, caplog):
    class AlwaysCache(RemoteResolver):
        def check_cache(self):
            return True

        @property
        def cache_path(self):
            return os.path.abspath("path")

        def resolve_remote(self):
            pass

    os.makedirs("path", exist_ok=True)

    proj = Project("testproj")
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    resolver = AlwaysCache("alwayscache", proj, "notused", "notused")
    Resolver.set_cache(proj, resolver.cache_id, "path")
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

    proj = Project("testproj")

    resolver = AlwaysOld("alwaysmissing", proj, "notused", "notused")
    with pytest.raises(FileNotFoundError, match=r"^Unable to locate 'alwaysmissing' at .*path$"):
        resolver.get_path()


def test_remote_init():
    resolver = RemoteResolver("thisname", Project("testproj"), "https://filepath", "ref")

    assert resolver.name == "thisname"
    assert resolver.source == "https://filepath"
    assert resolver.reference == "ref"
    assert resolver.urlscheme == "https"
    assert resolver.urlpath == "filepath"
    assert isinstance(resolver.logger, logging.Logger)


def test_remote_init_no_ref():
    with pytest.raises(ValueError,
                       match=r"^A reference \(e.g., version, commit\) is required for thisname$"):
        RemoteResolver("thisname", Project("testproj"), "https://filepath")


def test_remote_child_impl():
    resolver = RemoteResolver("thisname", Project("testproj"), "https://filepath", "ref")

    with pytest.raises(NotImplementedError, match=r"^child class must implement this$"):
        resolver.resolve_remote()

    with pytest.raises(NotImplementedError, match=r"^child class must implement this$"):
        resolver.check_cache()


@pytest.mark.nocache
def test_remote_cache_dir_default():
    resolver = RemoteResolver("thisname", Project("testproj"), "https://filepath", "ref")
    assert resolver.cache_dir == Path.home() / ".sc" / "cache"


def test_remote_cache_dir_no_root():
    resolver = RemoteResolver("thisname", None, "https://filepath", "ref")
    assert resolver.cache_dir == Path.home() / ".sc" / "cache"


def test_remote_cache_dir_from_schema():
    project = Project("testproj")
    project.option.set_cachedir(os.path.abspath("."))
    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")
    assert resolver.cache_dir == Path(os.path.abspath("."))


def test_remote_cache_dir_from_schema_not_found():
    project = Project("testproj")
    project.option.set_cachedir("thispath")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")
    assert resolver.cache_dir == Path(os.path.abspath("thispath"))


def test_remote_cache_name():
    resolver = RemoteResolver("thisname", Project("testproj"), "https://filepath", "ref")
    assert resolver.cache_name == "thisname-ref-c7a4a1c3dfc3975e"


def test_remote_cache_path():
    project = Project("testproj")
    project.option.set_cachedir("thispath")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")
    with patch("os.makedirs") as mkdir:
        assert resolver.cache_path == \
            Path(os.path.abspath("thispath/thisname-ref-c7a4a1c3dfc3975e"))
        mkdir.assert_called_once()


def test_remote_cache_path_cache_exist():
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")
    with patch("os.makedirs") as mkdir:
        assert resolver.cache_path == Path(os.path.abspath("thisname-ref-c7a4a1c3dfc3975e"))
        mkdir.assert_not_called()


def test_remote_lock_file():
    project = Project("testproj")
    project.option.set_cachedir("thispath")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")
    with patch("os.makedirs") as mkdir:
        assert resolver.lock_file == \
            Path(os.path.abspath("thispath/thisname-ref-c7a4a1c3dfc3975e.lock"))
        mkdir.assert_called_once()


def test_remote_sc_lock_file():
    project = Project("testproj")
    project.option.set_cachedir("thispath")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")
    with patch("os.makedirs") as mkdir:
        assert resolver.sc_lock_file == \
            Path(os.path.abspath("thispath/thisname-ref-c7a4a1c3dfc3975e.sc_lock"))
        mkdir.assert_called_once()


def test_remote_resolve_cached():
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")

    with patch("siliconcompiler.package.RemoteResolver.lock") as lock, \
         patch("siliconcompiler.package.RemoteResolver.check_cache") as check_cache, \
         patch("siliconcompiler.package.RemoteResolver.resolve_remote") as resolve_remote:
        check_cache.return_value = True
        assert resolver.resolve() == Path(os.path.abspath("thisname-ref-c7a4a1c3dfc3975e"))
        lock.assert_called_once()
        check_cache.assert_called_once()
        resolve_remote.assert_not_called()


def test_remote_resolve():
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")

    with patch("siliconcompiler.package.RemoteResolver.lock") as lock, \
         patch("siliconcompiler.package.RemoteResolver.check_cache") as check_cache, \
         patch("siliconcompiler.package.RemoteResolver.resolve_remote") as resolve_remote:
        check_cache.return_value = False
        assert resolver.resolve() == Path(os.path.abspath("thisname-ref-c7a4a1c3dfc3975e"))
        lock.assert_called_once()
        check_cache.assert_called_once()
        resolve_remote.assert_called_once()


def test_remote_resolve_cached_different_name():
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")

    with patch("siliconcompiler.package.RemoteResolver.lock") as lock, \
         patch("siliconcompiler.package.RemoteResolver.check_cache") as check_cache, \
         patch("siliconcompiler.package.RemoteResolver.resolve_remote") as resolve_remote:
        check_cache.return_value = False
        assert resolver.resolve() == Path(os.path.abspath("thisname-ref-c7a4a1c3dfc3975e"))
        Path(os.path.abspath("thisname-ref-c7a4a1c3dfc3975e")).mkdir(exist_ok=True)
        lock.assert_called_once()
        check_cache.assert_called_once()
        resolve_remote.assert_called_once()
        assert resolver.get_path() == os.path.abspath("thisname-ref-c7a4a1c3dfc3975e")

    resolver = RemoteResolver("thisname1", project, "https://filepath", "ref")
    with patch("siliconcompiler.package.RemoteResolver.lock") as lock, \
         patch("siliconcompiler.package.RemoteResolver.check_cache") as check_cache, \
         patch("siliconcompiler.package.RemoteResolver.resolve_remote") as resolve_remote:
        check_cache.return_value = False
        # This will use the same of the other resolver despite the name change
        assert resolver.get_path() == os.path.abspath("thisname-ref-c7a4a1c3dfc3975e")
        lock.assert_not_called()
        check_cache.assert_not_called()
        resolve_remote.assert_not_called()


def test_remote_lock():
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")

    with resolver.lock():
        assert os.path.exists(resolver.lock_file)
        assert not os.path.exists(resolver.sc_lock_file)

    assert os.path.exists(resolver.lock_file)
    assert not os.path.exists(resolver.sc_lock_file)


def test_remote_lock_after_lock():
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")

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
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver0 = RemoteResolver("thisname", project, "https://filepath", "ref")
    resolver1 = RemoteResolver("thisname", project, "https://filepath", "ref")

    # change second resolver to wait 1 second
    resolver1.set_timeout(1)
    assert resolver1.timeout == 1

    with resolver0.lock():
        assert os.path.exists(resolver0.lock_file)
        assert not os.path.exists(resolver0.sc_lock_file)

        with pytest.raises(RuntimeError, match=r"^Failed to access .*\. "
                                               r"Another thread is currently holding the lock\.$"):
            with resolver1.lock():
                assert False, "should not get here"

    assert os.path.exists(resolver0.lock_file)
    assert not os.path.exists(resolver0.sc_lock_file)


def test_remote_lock_within_lock_thread_multiple_tries(monkeypatch):
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver0 = RemoteResolver("thisname", project, "https://filepath", "ref")
    resolver1 = RemoteResolver("thisname", project, "https://filepath", "ref")

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
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver0 = RemoteResolver("thisname", project, "https://filepath", "ref")
    resolver1 = RemoteResolver("thisname", project, "https://filepath", "ref")

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
        with pytest.raises(RuntimeError, match=r"^Failed to access .*\. .*\.lock is still locked. "
                           r"If this is a mistake, please delete the lock file\.$"):
            with resolver1.lock():
                pass

    assert os.path.exists(resolver0.lock_file)
    assert not os.path.exists(resolver0.sc_lock_file)


def test_remote_lock_exception():
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")

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
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")
    resolver.set_timeout(1)

    with patch("fasteners.InterProcessLock.acquire") as acquire:
        acquire.return_value = False
        with pytest.raises(RuntimeError,
                           match=r"^Failed to access .*\. .*\.lock is still locked\. "
                           r"If this is a mistake, please delete the lock file\.$"):
            with resolver.lock():
                assert False, "Should not gain lock"
            acquire.assert_called_once()

    assert not os.path.exists(resolver.lock_file)
    assert not os.path.exists(resolver.sc_lock_file)


def test_remote_lock_revert_to_file():
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")

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
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = RemoteResolver("thisname", project, "https://filepath", "ref")

    with patch("fasteners.InterProcessLock.acquire") as acquire, \
         patch("time.sleep") as sleep:
        def fail_lock(*args, **kwargs):
            raise RuntimeError
        acquire.side_effect = fail_lock

        # Generate lock
        resolver.sc_lock_file.touch()

        with pytest.raises(RuntimeError,
                           match=r"^Failed to access .*\. Lock .* still exists\.$"):
            with resolver.lock():
                pass

        assert sleep.call_count == 600

    assert not os.path.exists(resolver.lock_file)
    assert os.path.exists(resolver.sc_lock_file)


def test_file_resolver_abs_path():
    resolver = FileResolver("thisname", Project("testproj"), os.path.abspath("test"))
    assert resolver.resolve() == os.path.abspath("test")


def test_file_resolver_with_file():
    resolver = FileResolver("thisname", Project("testproj"), "file://test")
    assert resolver.resolve() == os.path.abspath("test")


def test_file_resolver_with_abspath():
    resolver = FileResolver("thisname", Project("testproj"), f"file://{os.path.abspath('../test')}")
    assert resolver.resolve() == os.path.abspath("../test")


def test_file_resolver_with_relpath():
    resolver = FileResolver("thisname", Project("testproj"), "file://test")
    assert resolver.resolve() == os.path.abspath("test")


def test_python_path_resolver():
    resolver = PythonPathResolver("thisname", Project("testproj"), "python://siliconcompiler")
    assert resolver.resolve() == os.path.dirname(siliconcompiler.__file__)


def test_python_path_resolver_with_urlpath():
    """Test that PythonPathResolver correctly extracts module name from source."""
    resolver = PythonPathResolver("test_module", None, "python://json")
    assert resolver.urlpath == "json"
    assert resolver.resolve() is not None


def test_python_path_resolver_with_nested_module():
    """Test PythonPathResolver with nested module."""
    resolver = PythonPathResolver("test_nested", None, "python://xml.etree")
    resolved = resolver.resolve()
    assert resolved is not None
    assert os.path.exists(resolved)


def test_python_path_resolver_reference_ignored():
    """Test that PythonPathResolver ignores the reference parameter."""
    resolver = PythonPathResolver("thisname", None, "python://siliconcompiler", reference="v1.0")
    # Reference should be ignored for Python modules
    assert resolver.reference is None
    assert resolver.resolve() == os.path.dirname(siliconcompiler.__file__)


def test_python_path_resolver_not_found():
    """Test that PythonPathResolver raises error for non-existent module."""
    resolver = PythonPathResolver("test_missing", None, "python://nonexistent_module_xyz")
    with pytest.raises(ModuleNotFoundError):
        resolver.resolve()


def test_python_path_resolver_absolute_path():
    """Test that resolved path is absolute."""
    resolver = PythonPathResolver("thisname", None, "python://siliconcompiler")
    resolved = resolver.resolve()
    assert os.path.isabs(resolved)


def test_python_path_resolver_get_python_module_mapping():
    """Test get_python_module_mapping returns a valid dictionary."""
    mapping = PythonPathResolver.get_python_module_mapping()
    assert isinstance(mapping, dict)
    # Should contain some common modules or siliconcompiler
    assert len(mapping) > 0
    # Each key should be a module name, each value should be a list of distribution names
    for module_name, dist_names in mapping.items():
        assert isinstance(module_name, str)
        assert isinstance(dist_names, list)
        assert all(isinstance(dn, str) for dn in dist_names)


def test_python_path_resolver_get_python_module_mapping_cached():
    """Test that get_python_module_mapping uses LRU cache."""
    # Call it twice and ensure it returns the same object (cached)
    mapping1 = PythonPathResolver.get_python_module_mapping()
    mapping2 = PythonPathResolver.get_python_module_mapping()
    assert mapping1 is mapping2


def test_python_path_resolver_is_module_editable_not_found():
    """Test is_python_module_editable returns False for non-existent module."""
    result = PythonPathResolver.is_python_module_editable("nonexistent_module_xyz_123")
    assert result is False


def test_python_path_resolver_is_module_editable_standard_lib():
    """Test is_python_module_editable with standard library modules."""
    # Standard library modules should not be editable
    result = PythonPathResolver.is_python_module_editable("json")
    # json is a standard library module, so should be False
    # It might not be in the distribution mapping at all
    assert result is False


def test_python_path_resolver_is_module_editable_installed():
    """Test is_python_module_editable with installed package."""
    # pytest should be installed
    result = PythonPathResolver.is_python_module_editable("pytest")
    # pytest is typically not installed in editable mode
    assert result is False


def test_python_path_resolver_is_module_editable_siliconcompiler():
    """Test is_python_module_editable with siliconcompiler."""
    result = PythonPathResolver.is_python_module_editable("siliconcompiler")
    assert isinstance(result, bool)
    # siliconcompiler could be editable during development, or not


def test_python_path_resolver_set_dataroot_editable_module():
    """Test set_dataroot with an editable module."""
    from siliconcompiler.schema_support.pathschema import PathSchema

    schema = PathSchema()

    # Mock is_python_module_editable to return True
    with patch.object(PythonPathResolver, "is_python_module_editable", return_value=True):
        PythonPathResolver.set_dataroot(
            schema,
            "test_data",
            "siliconcompiler",
            "fallback/path",
            "v1.0"
        )

        # Check that dataroot was set with python:// source
        assert schema.get("dataroot", "test_data", "path") == "python://siliconcompiler"
        assert schema.get("dataroot", "test_data", "tag") is None


def test_python_path_resolver_set_dataroot_non_editable_module():
    """Test set_dataroot with a non-editable module."""
    from siliconcompiler.schema_support.pathschema import PathSchema

    schema = PathSchema()

    # Mock is_python_module_editable to return False
    with patch.object(PythonPathResolver, "is_python_module_editable", return_value=False):
        PythonPathResolver.set_dataroot(
            schema,
            "test_data",
            "some_module",
            "fallback/path",
            "v1.0"
        )

        # Check that dataroot was set with fallback path
        assert schema.get("dataroot", "test_data", "path") == "fallback/path"
        assert schema.get("dataroot", "test_data", "tag") == "v1.0"


def test_python_path_resolver_set_dataroot_with_path_append():
    """Test set_dataroot with path appending for editable module."""
    from siliconcompiler.schema_support.pathschema import PathSchema

    schema = PathSchema()

    # Mock is_python_module_editable to return True
    with patch.object(PythonPathResolver, "is_python_module_editable", return_value=True):
        with patch.object(PythonPathResolver, "__init__", return_value=None):
            # We need to mock the constructor and resolve separately
            with patch("siliconcompiler.package.PythonPathResolver.resolve") as mock_resolve:
                # Mock the resolve method to return a test path
                mock_resolve.return_value = "/path/to/module"

                PythonPathResolver.set_dataroot(
                    schema,
                    "test_data",
                    "siliconcompiler",
                    "fallback/path",
                    python_module_path_append="subdir"
                )

                # Check that path was appended correctly
                expected_path = os.path.abspath(os.path.join("/path/to/module", "subdir"))
                assert schema.get("dataroot", "test_data", "path") == expected_path


def test_python_path_resolver_set_dataroot_no_path_append():
    """Test set_dataroot with editable module but no path appending."""
    from siliconcompiler.schema_support.pathschema import PathSchema

    schema = PathSchema()

    # Mock is_python_module_editable to return True
    with patch.object(PythonPathResolver, "is_python_module_editable", return_value=True):
        PythonPathResolver.set_dataroot(
            schema,
            "test_data",
            "siliconcompiler",
            "fallback/path",
            python_module_path_append=None
        )

        # Check that dataroot was set with python:// source
        assert schema.get("dataroot", "test_data", "path") == "python://siliconcompiler"


def test_python_path_resolver_get_path_integration():
    """Test the full get_path flow for PythonPathResolver."""
    resolver = PythonPathResolver("test_module", None, "python://siliconcompiler")
    path = resolver.get_path()

    assert isinstance(path, str)
    assert os.path.exists(path)
    assert os.path.isabs(path)
    assert path == os.path.dirname(siliconcompiler.__file__)


def test_python_path_resolver_cache_id():
    """Test that cache IDs are consistent and different for different sources."""
    resolver1 = PythonPathResolver("test1", None, "python://siliconcompiler")
    resolver2 = PythonPathResolver("test2", None, "python://siliconcompiler")
    resolver3 = PythonPathResolver("test3", None, "python://json")

    # Same source should have same cache ID (regardless of name)
    assert resolver1.cache_id == resolver2.cache_id
    # Different sources should have different cache IDs
    assert resolver1.cache_id != resolver3.cache_id


def test_keypath_resolver():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.add_idir(".")

    proj = Project(design)

    resolver = KeyPathResolver("thisname", proj, "key://library,testdesign,fileset,rtl,idir")
    assert resolver.resolve() == os.path.abspath(".")


def test_keypath_resolver_no_root():
    resolver = KeyPathResolver("thisname", None, "key://option,dir,testdir")
    with pytest.raises(RuntimeError,
                       match=r"^A root schema has not been defined for 'thisname'$"):
        resolver.resolve()


def test_get_cache():
    project = Project("testproj")
    assert Resolver.get_cache(project) == {}
    assert getattr(project, "__Resolver_cache_id")


def test_get_cache_none():
    with patch("siliconcompiler.package.Resolver._Resolver__get_root_id") as root:
        assert Resolver.get_cache(None) is None
        root.assert_not_called()


def test_set_cache():
    project = Project("testproj")
    assert Resolver.get_cache(project) == {}
    assert getattr(project, "__Resolver_cache_id")

    Resolver.set_cache(project, "test", "path")
    assert Resolver.get_cache(project) == {
        "test": "path"
    }
    Resolver.set_cache(project, "test0", "path0")
    assert Resolver.get_cache(project) == {
        "test": "path",
        "test0": "path0",
    }


def test_set_cache_none():
    with patch("siliconcompiler.package.Resolver._Resolver__get_root_id") as root:
        Resolver.set_cache(None, "test", "path")
        root.assert_not_called()


def test_set_cache_different_projects():
    project0 = Project("testproj")
    project1 = Project("testproj")

    assert Resolver.get_cache(project0) == {}
    assert Resolver.get_cache(project1) == {}

    assert getattr(project0, "__Resolver_cache_id")
    assert getattr(project1, "__Resolver_cache_id")

    Resolver.set_cache(project0, "test", "path")
    assert Resolver.get_cache(project0) == {
        "test": "path"
    }
    assert Resolver.get_cache(project1) == {}

    Resolver.set_cache(project1, "test0", "path0")
    assert Resolver.get_cache(project0) == {
        "test": "path"
    }
    assert Resolver.get_cache(project1) == {
        "test0": "path0",
    }


def test_reset_cache():
    project = Project("testproj")

    assert Resolver.get_cache(project) == {}

    Resolver.set_cache(project, "test", "path")
    assert Resolver.get_cache(project) == {
        "test": "path"
    }

    assert getattr(project, "__Resolver_cache_id")

    Resolver.reset_cache(project)
    assert Resolver.get_cache(project) == {}


def test_reset_cache_none():
    with patch("siliconcompiler.package.Resolver._Resolver__get_root_id") as root:
        Resolver.reset_cache(None)
        root.assert_not_called()


# ============================================================================
# Tests for _make_readonly() method
# ============================================================================

def test_make_readonly_single_file(tmp_path):
    """Test making a single file read-only."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    # Set explicit initial permissions (0o644) to avoid umask variability
    os.chmod(test_file, 0o644)

    # Verify it has write permission bit initially
    mode_before = os.stat(test_file).st_mode
    assert mode_before & stat.S_IWUSR

    # Make it read-only
    project = Project("testproj_single_file")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(test_file)

    # Verify it's read-only by checking permission bits
    assert os.access(test_file, os.R_OK)

    # Check exact permissions (444)
    mode = os.stat(test_file).st_mode
    assert mode & stat.S_IRUSR
    assert mode & stat.S_IRGRP
    assert mode & stat.S_IROTH
    assert not (mode & stat.S_IWUSR)
    assert not (mode & stat.S_IWGRP)
    assert not (mode & stat.S_IWOTH)


def test_make_readonly_single_file_path_object(tmp_path):
    """Test making a single file read-only using Path object."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    # Make it read-only using Path object
    project = Project("testproj_path_object")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(Path(test_file))

    # Check exact permissions
    mode = os.stat(test_file).st_mode
    assert not (mode & stat.S_IWUSR)
    assert not (mode & stat.S_IWGRP)
    assert not (mode & stat.S_IWOTH)


def test_make_readonly_directory_simple(tmp_path):
    """Test making a directory with files read-only."""
    # Create a directory with files
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "file1.txt").write_text("content1")
    (cache_dir / "file2.txt").write_text("content2")

    # Make directory and contents read-only
    project = Project("testproj_dir_simple")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(cache_dir)

    # Verify all files have write bits removed
    for fpath in [cache_dir / "file1.txt", cache_dir / "file2.txt"]:
        mode = os.stat(fpath).st_mode
        assert not (mode & stat.S_IWUSR)
        assert not (mode & stat.S_IWGRP)
        assert not (mode & stat.S_IWOTH)

    # Verify we can still read files
    assert os.access(cache_dir / "file1.txt", os.R_OK)
    assert os.access(cache_dir / "file2.txt", os.R_OK)

    # Verify we can still traverse the directory
    assert os.access(cache_dir, os.X_OK)


def test_make_readonly_nested_directories(tmp_path):
    """Test making nested directories with files read-only."""
    # Create nested directory structure
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "file1.txt").write_text("root")

    subdir1 = cache_dir / "subdir1"
    subdir1.mkdir()
    (subdir1 / "file2.txt").write_text("sub1")

    subdir2 = subdir1 / "subdir2"
    subdir2.mkdir()
    (subdir2 / "file3.txt").write_text("sub2")

    subdir3 = subdir2 / "subdir3"
    subdir3.mkdir()
    (subdir3 / "file4.txt").write_text("sub3")

    # Make entire tree read-only
    project = Project("testproj_nested")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(cache_dir)

    # Verify all files are read-only by checking permission bits
    for fpath in cache_dir.rglob("*.txt"):
        mode = os.stat(fpath).st_mode
        assert not (mode & stat.S_IWUSR), f"{fpath} should have write bit removed"
        assert not (mode & stat.S_IWGRP), f"{fpath} should have group write bit removed"
        assert not (mode & stat.S_IWOTH), f"{fpath} should have other write bit removed"

    # Verify all directories are readable and traversable
    for dpath in [cache_dir, subdir1, subdir2, subdir3]:
        assert os.access(dpath, os.R_OK), f"{dpath} should be readable"
        assert os.access(dpath, os.X_OK), f"{dpath} should be traversable"


def test_make_readonly_empty_directory(tmp_path):
    """Test making an empty directory read-only."""
    # Create an empty directory
    cache_dir = tmp_path / "empty_cache"
    cache_dir.mkdir()

    # Make it read-only
    project = Project("testproj_empty_dir")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(cache_dir)

    # Verify directory is readable and still traversable
    assert os.access(cache_dir, os.R_OK)
    assert os.access(cache_dir, os.X_OK)

    # Verify it's not writable by checking stat mode bits
    mode = os.stat(cache_dir).st_mode
    assert not (mode & stat.S_IWUSR)


def test_make_readonly_preserves_read_access(tmp_path):
    """Test that making read-only only removes write permissions, preserving others."""
    # Create a file with restrictive permissions initially
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    # Make it only readable by owner (400)
    test_file.chmod(stat.S_IRUSR)

    # Make it read-only (this should only remove write bits, not add read bits)
    project = Project("testproj_preserves_read")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(test_file)

    # Verify owner can still read
    mode = os.stat(test_file).st_mode
    assert mode & stat.S_IRUSR
    # Verify none can write (since the original file had no write bits anyway)
    assert not (mode & stat.S_IWUSR)
    assert not (mode & stat.S_IWGRP)
    assert not (mode & stat.S_IWOTH)


def test_make_readonly_preserves_executable_bit_file(tmp_path):
    """Test that making read-only preserves the executable bit on files (Unix only)."""
    # Create an executable file
    test_file = tmp_path / "script.sh"
    test_file.write_text("#!/bin/bash\necho hello")
    test_file.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                    stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)  # 755

    # Make it read-only
    project = Project("testproj_exec_bit")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(test_file)

    # Verify core behavior: write bits removed
    mode = os.stat(test_file).st_mode
    assert not (mode & stat.S_IWUSR)
    assert not (mode & stat.S_IWGRP)
    assert not (mode & stat.S_IWOTH)

    # Unix-specific: verify execute bits preserved
    if sys.platform != "win32":
        assert os.access(test_file, os.X_OK)
        # Check exact permissions
        assert mode & stat.S_IRUSR
        assert mode & stat.S_IXUSR
        assert mode & stat.S_IRGRP
        assert mode & stat.S_IXGRP
        assert mode & stat.S_IROTH
        assert mode & stat.S_IXOTH
        assert not (mode & stat.S_IWUSR)
        assert not (mode & stat.S_IWGRP)
        assert not (mode & stat.S_IWOTH)


def test_make_readonly_removes_write_preserves_exec(tmp_path):
    """Test that making read-only removes write but preserves read and execute."""
    # Create a file with write permission (644)
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    test_file.chmod(stat.S_IRUSR | stat.S_IWUSR |
                    stat.S_IRGRP |
                    stat.S_IROTH)  # 644

    # Make it read-only
    project = Project("testproj_remove_write")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(test_file)

    # Verify permissions changed from 644 to 444
    mode = os.stat(test_file).st_mode
    assert mode & stat.S_IRUSR
    assert mode & stat.S_IRGRP
    assert mode & stat.S_IROTH
    assert not (mode & stat.S_IWUSR)
    assert not (mode & stat.S_IWGRP)
    assert not (mode & stat.S_IWOTH)
    # Verify no execute bit
    assert not (mode & stat.S_IXUSR)
    assert not (mode & stat.S_IXGRP)
    assert not (mode & stat.S_IXOTH)


def test_make_readonly_directory_with_mixed_permissions(tmp_path):
    """Test making directory read-only removes write permissions while preserving read/exec."""
    # Create a directory with files having different permissions
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    file1 = cache_dir / "file1.txt"
    file1.write_text("content1")
    file1.chmod(stat.S_IRUSR | stat.S_IWUSR)  # rw- --- ---

    file2 = cache_dir / "file2.txt"
    file2.write_text("content2")
    file2.chmod(stat.S_IRUSR | stat.S_IRGRP)  # r-- r-- ---

    # Make directory and contents read-only
    project = Project("testproj_mixed_perms")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(cache_dir)

    # Verify all files have write permissions removed
    for fpath in [file1, file2]:
        mode = os.stat(fpath).st_mode
        assert not (mode & stat.S_IWUSR), f"{fpath}: owner should not be able to write"
        assert not (mode & stat.S_IWGRP), f"{fpath}: group should not be able to write"
        assert not (mode & stat.S_IWOTH), f"{fpath}: others should not be able to write"

    # Verify file1 preserved its original read permission (owner only)
    mode1 = os.stat(file1).st_mode
    assert mode1 & stat.S_IRUSR, "file1: owner should be able to read"

    # Verify file2 preserved its original read permissions (owner and group)
    mode2 = os.stat(file2).st_mode
    assert mode2 & stat.S_IRUSR, "file2: owner should be able to read"
    assert mode2 & stat.S_IRGRP, "file2: group should be able to read"


def test_make_readonly_directory_preserves_execute_bit(tmp_path):
    """Test that making directories read-only preserves execute bit (Unix only)."""
    # Create a directory structure
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    subdir = cache_dir / "subdir"
    subdir.mkdir()
    (cache_dir / "test.txt").write_text("content")

    # Set directory with specific permissions (755)
    subdir.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)

    # Make read-only
    project = Project("testproj_dir_exec_bit")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(cache_dir)

    # Core behavior: verify write bits removed
    mode = os.stat(subdir).st_mode
    assert not (mode & stat.S_IWUSR)
    assert not (mode & stat.S_IWGRP)
    assert not (mode & stat.S_IWOTH)

    # Unix-specific: verify execute bits preserved (555 instead of 755)
    if sys.platform != "win32":
        assert os.access(subdir, os.X_OK)
        assert mode & stat.S_IXUSR
        assert mode & stat.S_IXGRP
        assert mode & stat.S_IXOTH


def test_make_readonly_string_path(tmp_path):
    """Test making files read-only using string path instead of Path object."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    # Make it read-only using string path
    project = Project("testproj_string_path")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(str(test_file))

    # Verify it's read-only
    mode = os.stat(test_file).st_mode
    assert not (mode & stat.S_IWUSR)


def test_make_readonly_error_handling(tmp_path, monkeypatch, caplog):
    """Test error handling when chmod fails in resolve() flow."""
    import logging

    # Create a mock remote resolver that succeeds initially
    class TestResolver(RemoteResolver):
        def check_cache(self):
            return False  # Cache is invalid, will fetch

        def resolve_remote(self):
            # Create a test file to simulate successful download
            (Path(self.cache_path) / "test.txt").parent.mkdir(parents=True, exist_ok=True)
            (Path(self.cache_path) / "test.txt").write_text("content")

    # Create project with logging
    project = Project("testproj")
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.WARNING)
    caplog.set_level(logging.WARNING)

    resolver = TestResolver("test", project, "https://example.com", "v1.0")

    # Mock os.chmod to simulate permission error
    def mock_chmod(path, mode, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("os.chmod", mock_chmod)

    # resolve() should catch the chmod error and log warning
    # (the cache won't be made read-only, but resolve succeeds)
    result = resolver.resolve()

    # Verify that the cache path exists (resolve succeeded)
    assert Path(result).exists()
    # Verify that warning was logged about chmod failure
    assert "Could not make cache read-only" in caplog.text


# ============================================================================
# Tests for _make_writable() method (for cache cleanup/deletion)
# ============================================================================

def test_make_writable_single_file(tmp_path):
    """Test making a read-only file writable."""
    # Create a read-only file
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    test_file.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 444

    # Verify it doesn't have write permission bit
    mode_before = os.stat(test_file).st_mode
    assert not (mode_before & stat.S_IWUSR)

    # Make it writable
    project = Project("testproj_writable_single")
    project.option.set_cachedir(str(tmp_path))
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_writable(test_file)

    # Verify owner write permission bit is now set
    mode_after = os.stat(test_file).st_mode
    assert mode_after & stat.S_IWUSR


def test_make_writable_directory(tmp_path):
    """Test making a read-only directory writable."""
    # Create a directory with read-only files
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    file1 = cache_dir / "file1.txt"
    file1.write_text("content1")

    # Make everything read-only
    project = Project("testproj")
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(cache_dir)

    # Verify it's read-only via stat mode
    mode_file = os.stat(file1).st_mode
    mode_dir = os.stat(cache_dir).st_mode
    assert not (mode_file & stat.S_IWUSR)
    assert not (mode_dir & stat.S_IWUSR)

    # Make writable
    resolver._make_writable(cache_dir)

    # Verify owner can write via stat mode
    mode_file = os.stat(file1).st_mode
    mode_dir = os.stat(cache_dir).st_mode
    assert mode_file & stat.S_IWUSR
    assert mode_dir & stat.S_IWUSR


def test_make_readonly_then_delete(tmp_path):
    """Test that we can delete a read-only cache after making it writable."""
    # Create a read-only cache directory
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "file1.txt").write_text("content1")
    (cache_dir / "subdir").mkdir()
    (cache_dir / "subdir" / "file2.txt").write_text("content2")

    # Make it read-only
    project = Project("testproj")
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_readonly(cache_dir)

    # Verify it's read-only via stat mode
    mode_file1 = os.stat(cache_dir / "file1.txt").st_mode
    mode_subdir = os.stat(cache_dir / "subdir").st_mode
    assert not (mode_file1 & stat.S_IWUSR)
    assert not (mode_subdir & stat.S_IWUSR)

    # Make writable and delete (should not raise)
    resolver._make_writable(cache_dir)
    shutil.rmtree(cache_dir)

    # Verify deletion succeeded
    assert not cache_dir.exists()


def test_make_writable_preserves_read_and_exec(tmp_path):
    """Test that making writable preserves existing read and execute permissions."""
    # Create an executable file that's read-only
    exec_file = tmp_path / "script.sh"
    exec_file.write_text("#!/bin/bash\necho hello")
    exec_file.chmod(stat.S_IRUSR | stat.S_IXUSR)  # r-x --- --- (500)

    # Make writable
    project = Project("testproj")
    resolver = RemoteResolver("test", project, "https://example.com", "v1.0")
    resolver._make_writable(exec_file)

    # Verify it's still executable
    assert os.access(exec_file, os.X_OK)
    # Verify owner write permission bit is now set
    mode_after = os.stat(exec_file).st_mode
    assert mode_after & stat.S_IWUSR
    # Verify it's still readable
    assert os.access(exec_file, os.R_OK)
