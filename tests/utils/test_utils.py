import logging
import pytest

import os
import os.path
import psutil
import sys
import types

from unittest.mock import patch

from siliconcompiler import utils
from siliconcompiler.utils import \
    truncate_text, safecompare, get_cores, grep, \
    get_plugins, \
    default_sc_dir, default_credentials_file, default_cache_dir, \
    default_email_credentials_file, default_sc_path
from siliconcompiler.utils import (
    _load_pyproject_data,
    _installed_distribution_versions,
    _evaluate_requirement,
    _check_optional_group,
    _check_project_dependencies,
    _locate_pyproject_for_module,
    _find_editable_pyproject_paths,
    check_python_dependencies,
)


@pytest.mark.parametrize("text", (
    "testing-without-numbers", "testing-with-numbers0", "testing-with-numbers00"))
@pytest.mark.parametrize("length", (8, 10, 15))
def test_truncate_text_lengths(text, length):
    expect = min(len(text), length)

    assert len(truncate_text(text, length)) == expect


def test_truncate_text():
    text = "test"
    assert truncate_text(text, 8) == "test"
    assert truncate_text(text, 10) == "test"
    assert truncate_text(text, 15) == "test"

    text = "testing-without-numbers"
    assert truncate_text(text, 8) == "testi..."
    assert truncate_text(text, 10) == "testing..."
    assert truncate_text(text, 15) == "testing-with..."

    text = "testing-without-numbers0"
    assert truncate_text(text, 8) == "test...0"
    assert truncate_text(text, 10) == "testin...0"
    assert truncate_text(text, 15) == "testing-wit...0"

    text = "testing-without-numbers90"
    assert truncate_text(text, 8) == "tes...90"
    assert truncate_text(text, 10) == "testi...90"
    assert truncate_text(text, 15) == "testing-wi...90"

    text = "testing-without-numbers9123"
    assert truncate_text(text, 8) == "tes...23"
    assert truncate_text(text, 10) == "testi...23"
    assert truncate_text(text, 15) == "testing-wi...23"

    assert truncate_text("test", 1) == "test"
    assert truncate_text("testing-without-numbers", 1) == "te..."
    assert truncate_text("testing-without-numbers0", 1) == "t...0"
    assert truncate_text("testing-without-numbers9123", 1) == "...23"


@pytest.mark.parametrize("a,op,b,expect", [
    (1, ">", 2, False),
    (1, ">", 1, False),
    (2, ">", 1, True),
    (1, ">=", 2, False),
    (1, ">=", 1, True),
    (2, ">=", 1, True),
    (1, "<", 2, True),
    (1, "<", 1, False),
    (2, "<", 1, False),
    (1, "<=", 2, True),
    (1, "<=", 1, True),
    (2, "<=", 1, False),
    (1, "==", 2, False),
    (1, "==", 1, True),
    (2, "==", 1, False),
    (1, "!=", 2, True),
    (1, "!=", 1, False),
    (2, "!=", 1, True)
])
def test_safecompare(a, op, b, expect):
    assert safecompare(a, op, b) is expect


def test_safecompare_invalid_operator():
    with pytest.raises(ValueError, match=r"^Illegal comparison operation !$"):
        safecompare(1, "!", 2)


@pytest.fixture(autouse=True)
def disable_affinity(monkeypatch):
    """Give every get_cores() test a deterministic baseline by removing
    os.sched_getaffinity (as on macOS/Windows). Tests that exercise the
    affinity path re-add it explicitly with raising=False."""
    monkeypatch.delattr(os, 'sched_getaffinity', raising=False)


def test_get_cores_affinity(monkeypatch):
    # sched_getaffinity is preferred when available so cpuset/taskset limits
    # are honored, regardless of the machine's total core count.
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: {0, 1, 2, 3},
                        raising=False)
    monkeypatch.setattr(
        psutil, 'cpu_count',
        lambda logical: pytest.fail('affinity should be preferred'))
    assert get_cores() == 4


def test_get_cores_affinity_respects_cpuset(monkeypatch):
    # Even on a large machine, a narrow affinity mask caps the reported cores.
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: {2, 5},
                        raising=False)
    monkeypatch.setattr(psutil, 'cpu_count', lambda logical: 64)
    assert get_cores() == 2


def test_get_cores_affinity_physical(monkeypatch):
    # Physical count scales the affinity-limited logical count down by the
    # machine's hyperthreading ratio (2 threads/core here -> 6/2 == 3).
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: set(range(6)),
                        raising=False)

    def cpu_count(logical):
        return 16 if logical else 8

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores() == 6
    assert get_cores(physical=True) == 3


def test_get_cores_affinity_physical_single_logical_core(monkeypatch):
    # A tight affinity mask (single logical CPU) on a hyperthreaded machine
    # must still report at least one physical core rather than truncating to
    # 0 and falling through to the machine-wide fallback.
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: {0},
                        raising=False)

    def cpu_count(logical):
        return 16 if logical else 8

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores(physical=True) == 1


def test_get_cores_affinity_physical_no_hyperthreading(monkeypatch):
    # No hyperthreading -> physical count equals the affinity-limited count.
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: {0, 1, 2, 3},
                        raising=False)

    def cpu_count(logical):
        return 8

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores(physical=True) == 4


def test_get_cores_logical(monkeypatch):
    def cpu_count(logical):
        assert logical
        return 2

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores() == 2


def test_get_cores_physical(monkeypatch):
    def cpu_count(logical):
        assert not logical
        return 2

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores(physical=True) == 2


def test_get_cores_use_os(monkeypatch):
    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return 6

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores() == 6
    assert get_cores(physical=True) == 3


def test_get_cores_use_os_one_core(monkeypatch):
    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return 1

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores() == 1
    assert get_cores(physical=True) == 1


def test_get_cores_fallback(monkeypatch):
    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return None

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores() == 1
    assert get_cores(physical=True) == 1


def test_get_cores_empty_affinity_falls_back(monkeypatch):
    # An empty affinity set is treated as "unknown" and falls through to psutil.
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: set(),
                        raising=False)
    monkeypatch.setattr(psutil, 'cpu_count', lambda logical: 4)
    assert get_cores() == 4


def test_get_plugin():
    assert [] == get_plugins("nothingtofind")
    assert len(get_plugins("showtask")) > 0
    assert len(get_plugins("path_resolver")) > 0

    assert len(get_plugins("path_resolver", "https")) == 1


def test_default_sc_dir():
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_sc_dir() == os.path.join("this", ".sc")


def test_default_credentials_file():
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_credentials_file() == os.path.join("this", ".sc", "credentials")


def test_default_cache_dir():
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_cache_dir() == os.path.join("this", ".sc", "cache")


def test_default_email_credentials_file():
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_email_credentials_file() == os.path.join("this", ".sc", "email.json")


@pytest.mark.parametrize("path", ["test0", "that", "this", "works"])
def test_default_sc_path(path):
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_sc_path(path) == os.path.join("this", ".sc", path)


@pytest.mark.parametrize("args,line,expected", [
    # T1: Basic Match
    ("hello", "this is a hello world", "this is a hello world"),
    # T2: Basic No Match
    ("goodbye", "this is a hello world", None),
    # T3: Input Line None
    ("hello", None, None),
    # T4: Empty Pattern
    ("", "line", None),
    # T5: Invert Match (-v, Match found -> returns None)
    ("-v hello", "contains hello", None),
    # T6: Invert No Match (-v, No match -> returns Line)
    ("-v goodbye", "contains hello", "contains hello"),
    # T7: Ignore Case (-i, No Match without flag)
    ("hello", "HELLO world", None),
    # T8: Ignore Case (-i, Match with flag)
    ("-i hello", "HELLO world", "HELLO world"),
    # T9: Whole Word (-w, Substring match -> fail)
    ("-w cat", "The catalog is big.", None),
    # T10: Whole Word (-w, Word match -> success)
    ("-w cat", "The cat sat.", "The cat sat."),
    # T11: Exact Line (-x, Partial match -> fail)
    ("-x hello", "hello world", None),
    # T12: Exact Line (-x, Exact match -> success)
    ("-x hello", "hello", "hello"),
    # T13: Only Match (-o)
    ("-o hello", "Hello hello world", "hello"),
    # T14: Combined (-vi, Invert + Ignore Case)
    ("-vi HELLO", "This is hello world", None),
    # T15: Combined (-o -i)
    ("-o -i world", "Hello WORLD", "WORLD"),
    # T16: Combined (-xw, Exact + Word)
    ("-xw test", "test", "test"),
    # T17: Combined (-xw, Partial Fail)
    ("-xw testing", "testing is hard", None),
    # T20: Pattern with -e (Treats -hello as pattern)
    ("-e -hello world", "-hello world is great", "-hello world is great"),
])
def test_grep_logic(args, line, expected):
    """Tests the core logic and return values of the grep function."""
    assert grep(logging.getLogger(), args, line) == expected


def test_unknown_switch_error(caplog):
    # T18: Unknown Switch Error
    grep(logging.getLogger(), "-q hello", "test")
    assert "Unknown switch: -q" in caplog.text


def test_concatenated_unknown_switch_error(caplog):
    # T19: Concatenated Unknown Switch
    grep(logging.getLogger(), "-vq hello", "test")
    assert "Unknown switch: -q" in caplog.text


def test_invalid_regex_error(caplog):
    # T21: Invalid Regex Pattern
    grep(logging.getLogger(), "*", "test")
    # Check that we logged an error starting with our specific message
    assert "Invalid regex pattern" in caplog.text


# ---------------------------------------------------------------------------
# check_python_dependencies (pre-run informative dependency check)
# ---------------------------------------------------------------------------

@pytest.fixture
def logger():
    return logging.getLogger("test-python-deps")


class FakeDist:
    """Minimal stand-in for an importlib.metadata Distribution."""

    def __init__(self, name, version, raise_meta=False):
        self._name = name
        self.version = version
        self._raise = raise_meta

    @property
    def metadata(self):
        if self._raise:
            raise RuntimeError("metadata unavailable")
        return {"Name": self._name}


class FakeSpec:
    def __init__(self, origin=None, locations=None):
        self.origin = origin
        self.submodule_search_locations = locations


# ---------------------------------------------------------------------------
# _import_toml / _load_pyproject_data
# ---------------------------------------------------------------------------


def test_load_pyproject_data_valid(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\ndependencies = ["foo"]\n')
    data = _load_pyproject_data(str(pyproject))
    assert data["project"]["name"] == "demo"


def test_load_pyproject_data_missing_file(tmp_path):
    assert _load_pyproject_data(str(tmp_path / "does_not_exist.toml")) is None


def test_load_pyproject_data_malformed(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("this is = not valid toml =====")
    assert _load_pyproject_data(str(pyproject)) is None


def test_load_pyproject_data_no_toml_parser(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n')

    # Simulate an interpreter where neither tomllib nor tomli is available.
    monkeypatch.setattr(utils, "tomllib", None)
    assert _load_pyproject_data(str(pyproject)) is None


# ---------------------------------------------------------------------------
# _installed_distribution_versions
# ---------------------------------------------------------------------------


def test_installed_distribution_versions(monkeypatch):
    dists = [
        FakeDist("Foo_Bar", "1.2.3"),
        FakeDist("", "0.0.0"),                 # empty name -> skipped
        FakeDist("broken", "9.9", raise_meta=True),  # metadata raises -> skipped
        FakeDist("Foo-Bar", "2.0.0"),          # duplicate canonical -> first wins
    ]
    monkeypatch.setattr(utils, "distributions", lambda: iter(dists))

    installed = _installed_distribution_versions()
    assert installed == {"foo-bar": "1.2.3"}


# ---------------------------------------------------------------------------
# _evaluate_requirement
# ---------------------------------------------------------------------------


def test_evaluate_requirement_unparsable():
    assert _evaluate_requirement("git+https://example.com/x.git", {}) == \
        ("skip", None, None)


def test_evaluate_requirement_marker_excluded():
    # Marker that never applies on any supported interpreter.
    assert _evaluate_requirement("foo; python_version < '3.0'", {}) == \
        ("skip", None, None)


def test_evaluate_requirement_missing():
    assert _evaluate_requirement("foo >= 1.0", {}) == ("missing", "foo", None)


def test_evaluate_requirement_incompatible():
    result = _evaluate_requirement("foo >= 2.0", {"foo": "1.0"})
    assert result == ("incompatible", "foo", "1.0")


def test_evaluate_requirement_ok():
    assert _evaluate_requirement("foo >= 1.0", {"foo": "2.0"}) == ("ok", "foo", "2.0")


def test_evaluate_requirement_ok_no_specifier():
    assert _evaluate_requirement("foo", {"foo": "2.0"}) == ("ok", "foo", "2.0")


def test_evaluate_requirement_specifier_contains_raises(monkeypatch):
    # An installed version that cannot be compared against the specifier -> skip.
    class BadSpecifier:
        def __bool__(self):
            return True

        def contains(self, *args, **kwargs):
            raise RuntimeError("uncomparable version")

    class FakeReq:
        def __init__(self, _):
            self.marker = None
            self.name = "foo"
            self.specifier = BadSpecifier()

    monkeypatch.setattr(utils, "Requirement", FakeReq)
    assert _evaluate_requirement("foo", {"foo": "weird"}) == ("skip", "foo", "weird")


def test_evaluate_requirement_marker_evaluate_raises(monkeypatch):
    class BadMarker:
        def evaluate(self):
            raise RuntimeError("bad marker")

    class FakeReq:
        def __init__(self, _):
            self.marker = BadMarker()
            self.name = "foo"
            self.specifier = None

    monkeypatch.setattr(utils, "Requirement", FakeReq)
    assert _evaluate_requirement("foo", {}) == ("skip", None, None)


# ---------------------------------------------------------------------------
# _check_optional_group
# ---------------------------------------------------------------------------


def test_check_optional_group_non_string_and_all_skipped(logger, caplog):
    with caplog.at_level(logging.WARNING):
        # None entry is skipped; marker-excluded entry is skipped -> nothing applicable.
        issues = _check_optional_group(
            "docs", [None, "foo; python_version < '3.0'"], {}, "demo", logger)
    assert issues == 0
    assert caplog.records == []


def test_check_optional_group_active_reports_missing(logger, caplog):
    # Two members, one installed -> all-but-one -> active -> report the missing one.
    with caplog.at_level(logging.WARNING):
        issues = _check_optional_group(
            "docs", ["present", "absent"], {"present": "1.0"}, "demo", logger)
    assert issues == 1
    assert caplog.messages == [
        "optional group 'docs' in demo appears installed, but 'absent' is missing "
        "(declared as 'absent')",
    ]


def test_check_optional_group_inactive_stays_silent(logger, caplog):
    # Three members, only one installed -> not active -> no missing warnings.
    with caplog.at_level(logging.WARNING):
        issues = _check_optional_group(
            "docs", ["a", "b", "c"], {"a": "1.0"}, "demo", logger)
    assert issues == 0
    assert caplog.records == []


def test_check_optional_group_incompatible_always_reported(logger, caplog):
    # Not active (too few installed), but an installed member conflicts -> reported.
    with caplog.at_level(logging.WARNING):
        issues = _check_optional_group(
            "docs", ["a >= 2.0", "b", "c"], {"a": "1.0"}, "demo", logger)
    assert issues == 1
    assert caplog.messages == [
        "installed 'a' (1.0) does not satisfy 'a >= 2.0' from optional group "
        "'docs' in demo",
    ]


def test_check_optional_group_fully_installed_silent(logger, caplog):
    with caplog.at_level(logging.WARNING):
        issues = _check_optional_group(
            "docs", ["a >= 1.0", "b"], {"a": "1.0", "b": "1.0"}, "demo", logger)
    assert issues == 0
    assert caplog.records == []


# ---------------------------------------------------------------------------
# _check_project_dependencies
# ---------------------------------------------------------------------------


def test_check_project_dependencies_not_a_dict(logger):
    assert _check_project_dependencies("nope", {}, logger) == 0


def test_check_project_dependencies_no_project_table(logger):
    assert _check_project_dependencies({"build-system": {}}, {}, logger) == 0


def test_check_project_dependencies_project_not_dict(logger):
    assert _check_project_dependencies({"project": "oops"}, {}, logger) == 0


def test_check_project_dependencies_core_missing_and_conflict(logger, caplog):
    data = {
        "project": {
            "name": "demo",
            "dependencies": [
                "missingpkg >= 1.0",
                "oldpkg >= 2.0",
                None,                         # non-string -> skipped
                "okpkg",                      # satisfied -> silent
            ],
        }
    }
    installed = {"oldpkg": "1.0", "okpkg": "1.0"}
    with caplog.at_level(logging.WARNING):
        issues = _check_project_dependencies(data, installed, logger)

    assert issues == 2
    # Core-only drift -> plain reinstall, no extras suffix.
    assert caplog.messages == [
        "required dependency 'missingpkg' is declared in demo's pyproject.toml "
        "but is not installed",
        "installed 'oldpkg' (1.0) does not satisfy 'oldpkg >= 2.0' declared in "
        "demo's pyproject.toml",
        "demo environment is out of sync with pyproject.toml; "
        "run 'pip install -e .' to update",
    ]


def test_check_project_dependencies_default_name(logger, caplog):
    data = {"project": {"dependencies": ["missingpkg"]}}
    with caplog.at_level(logging.WARNING):
        issues = _check_project_dependencies(data, {}, logger)
    assert issues == 1
    assert caplog.messages == [
        "required dependency 'missingpkg' is declared in this project's "
        "pyproject.toml but is not installed",
        "this project environment is out of sync with pyproject.toml; "
        "run 'pip install -e .' to update",
    ]


def test_check_project_dependencies_non_list_sections(logger, caplog):
    data = {
        "project": {
            "name": "demo",
            "dependencies": "not-a-list",
            "optional-dependencies": {
                "good": ["missingextra", "present"],
                "bad": "not-a-list",           # skipped
            },
        }
    }
    installed = {"present": "1.0"}
    with caplog.at_level(logging.WARNING):
        issues = _check_project_dependencies(data, installed, logger)
    # Only the "good" group is active (all-but-one) and reports its missing member;
    # the affected optional group is named in the reinstall hint.
    assert issues == 1
    assert caplog.messages == [
        "optional group 'good' in demo appears installed, but 'missingextra' is "
        "missing (declared as 'missingextra')",
        "demo environment is out of sync with pyproject.toml; "
        "run 'pip install -e .[good]' to update",
    ]


def test_check_project_dependencies_hint_lists_multiple_groups(logger, caplog):
    data = {
        "project": {
            "name": "demo",
            "dependencies": ["coremissing"],
            "optional-dependencies": {
                "gui": ["presentgui", "missinggui"],     # active -> missing reported
                "remote": ["presentremote >= 2.0"],      # installed but conflicting
                "quiet": ["a", "b", "c"],                # inactive -> silent
            },
        }
    }
    installed = {"presentgui": "1.0", "presentremote": "1.0"}
    with caplog.at_level(logging.WARNING):
        issues = _check_project_dependencies(data, installed, logger)

    assert issues == 3  # 1 core + 1 gui-missing + 1 remote-conflict
    assert caplog.messages == [
        "required dependency 'coremissing' is declared in demo's pyproject.toml "
        "but is not installed",
        "optional group 'gui' in demo appears installed, but 'missinggui' is "
        "missing (declared as 'missinggui')",
        "installed 'presentremote' (1.0) does not satisfy 'presentremote >= 2.0' "
        "from optional group 'remote' in demo",
        "demo environment is out of sync with pyproject.toml; "
        "run 'pip install -e .[gui,remote]' to update",
    ]


def test_check_project_dependencies_ignores_dev_groups(logger, caplog):
    # Development/testing groups are skipped even when active and out of sync.
    data = {
        "project": {
            "name": "demo",
            "optional-dependencies": {
                "test": ["presenttest", "missingtest"],   # active drift, but ignored
                "Lint": ["oldlint >= 2.0"],               # conflict, but ignored (case)
                "docs": ["missingdoc", "presentdoc"],     # active drift, but ignored
            },
        }
    }
    installed = {"presenttest": "1.0", "oldlint": "1.0", "presentdoc": "1.0"}
    with caplog.at_level(logging.WARNING):
        issues = _check_project_dependencies(data, installed, logger)

    assert issues == 0
    assert caplog.records == []


def test_check_project_dependencies_optional_not_dict(logger):
    data = {"project": {"name": "demo", "optional-dependencies": "nope"}}
    assert _check_project_dependencies(data, {}, logger) == 0


def test_check_project_dependencies_clean_no_hint(logger, caplog):
    data = {"project": {"name": "demo", "dependencies": ["okpkg >= 1.0"]}}
    with caplog.at_level(logging.WARNING):
        issues = _check_project_dependencies(data, {"okpkg": "2.0"}, logger)
    assert issues == 0
    assert caplog.records == []


# ---------------------------------------------------------------------------
# _locate_pyproject_for_module
# ---------------------------------------------------------------------------


def test_locate_pyproject_find_spec_raises(monkeypatch):
    def _boom(_):
        raise ValueError("bad module")

    monkeypatch.setattr("importlib.util.find_spec", _boom)
    assert _locate_pyproject_for_module("whatever") is None


def test_locate_pyproject_spec_none(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda _: None)
    assert _locate_pyproject_for_module("whatever") is None


def test_locate_pyproject_from_origin(tmp_path, monkeypatch):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    origin = str(pkg / "__init__.py")
    monkeypatch.setattr("importlib.util.find_spec", lambda _: FakeSpec(origin=origin))

    found = _locate_pyproject_for_module("pkg")
    assert found == str(tmp_path / "pyproject.toml")


def test_locate_pyproject_not_found_within_limit(tmp_path, monkeypatch):
    # Deeply nested with no pyproject.toml anywhere within the walk limit.
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    origin = str(deep / "__init__.py")
    monkeypatch.setattr("importlib.util.find_spec", lambda _: FakeSpec(origin=origin))
    assert _locate_pyproject_for_module("pkg") is None


def test_locate_pyproject_namespace_package(tmp_path, monkeypatch):
    pkg = tmp_path / "nspkg"
    pkg.mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda _: FakeSpec(origin="namespace", locations=[str(pkg)]))

    assert _locate_pyproject_for_module("nspkg") == str(tmp_path / "pyproject.toml")


def test_locate_pyproject_namespace_no_locations(monkeypatch):
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda _: FakeSpec(origin=None, locations=None))
    assert _locate_pyproject_for_module("nspkg") is None


def test_locate_pyproject_walk_stops_at_root(monkeypatch, tmp_path):
    # Origin directly at a directory whose parent is itself (simulate fs root).
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda _: FakeSpec(origin="/__init__.py"))
    assert _locate_pyproject_for_module("pkg") is None


# ---------------------------------------------------------------------------
# _find_editable_pyproject_paths
# ---------------------------------------------------------------------------


def _install_fake_resolver(monkeypatch, mapping, editable, locate):
    import siliconcompiler.package as package

    monkeypatch.setattr(
        package.PythonPathResolver, "get_python_module_mapping",
        staticmethod(lambda: mapping))
    monkeypatch.setattr(
        package.PythonPathResolver, "is_python_module_editable",
        staticmethod(editable))
    monkeypatch.setattr(utils, "_locate_pyproject_for_module", locate)


def test_find_editable_pyproject_paths_happy(monkeypatch):
    mapping = {"a": ["A"], "b": ["B"], "c": ["C"], "d": ["D"], "e": ["E"]}

    def editable(module):
        if module == "e":
            raise RuntimeError("cannot determine")
        return module in ("a", "b", "d")

    def locate(module):
        return {
            "a": "/proj1/pyproject.toml",
            "b": "/proj1/pyproject.toml",   # duplicate -> deduped
            "d": None,                        # editable but no pyproject -> skipped
        }[module]

    _install_fake_resolver(monkeypatch, mapping, editable, locate)
    assert _find_editable_pyproject_paths() == ["/proj1/pyproject.toml"]


def test_find_editable_pyproject_paths_import_fails(monkeypatch):
    broken = types.ModuleType("siliconcompiler.package")
    monkeypatch.setitem(sys.modules, "siliconcompiler.package", broken)
    assert _find_editable_pyproject_paths() == []


def test_find_editable_pyproject_paths_mapping_raises(monkeypatch):
    import siliconcompiler.package as package

    def _boom():
        raise RuntimeError("mapping failed")

    monkeypatch.setattr(
        package.PythonPathResolver, "get_python_module_mapping",
        staticmethod(_boom))
    assert _find_editable_pyproject_paths() == []


# ---------------------------------------------------------------------------
# check_python_dependencies (orchestrator)
# ---------------------------------------------------------------------------


def test_check_python_dependencies_happy(monkeypatch, tmp_path, logger, caplog):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo"\ndependencies = ["missingpkg >= 1.0"]\n')

    monkeypatch.setattr(
        utils, "_find_editable_pyproject_paths", lambda: [str(pyproject)])
    monkeypatch.setattr(
        utils, "_installed_distribution_versions", lambda: {})

    with caplog.at_level(logging.WARNING):
        check_python_dependencies(logger)
    assert caplog.messages == [
        "required dependency 'missingpkg' is declared in demo's pyproject.toml "
        "but is not installed",
        "demo environment is out of sync with pyproject.toml; "
        "run 'pip install -e .' to update",
    ]


def test_check_python_dependencies_skips_unparseable_pyproject(
        monkeypatch, tmp_path, logger, caplog):
    bad = tmp_path / "pyproject.toml"
    bad.write_text("== not valid ==")

    monkeypatch.setattr(utils, "_find_editable_pyproject_paths", lambda: [str(bad)])
    monkeypatch.setattr(utils, "_installed_distribution_versions", lambda: {})

    with caplog.at_level(logging.WARNING):
        check_python_dependencies(logger)
    assert caplog.records == []


def test_check_python_dependencies_never_raises(monkeypatch, logger, caplog):
    def _boom():
        raise RuntimeError("catastrophe")

    monkeypatch.setattr(utils, "_installed_distribution_versions", _boom)
    with caplog.at_level(logging.DEBUG):
        check_python_dependencies(logger)  # must not raise
    assert caplog.messages == ["python dependency check skipped: catastrophe"]


def test_check_python_dependencies_isolates_per_project(
        monkeypatch, tmp_path, logger, caplog):
    # A failure checking one project must not prevent the others being checked.
    good = tmp_path / "good_pyproject.toml"
    good.write_text('[project]\nname = "good"\ndependencies = ["missingpkg"]\n')

    def fake_load(path):
        if path == "/bad/pyproject.toml":
            raise RuntimeError("boom")
        return _load_pyproject_data(path)

    monkeypatch.setattr(
        utils, "_find_editable_pyproject_paths",
        lambda: ["/bad/pyproject.toml", str(good)])
    monkeypatch.setattr(utils, "_installed_distribution_versions", lambda: {})
    monkeypatch.setattr(utils, "_load_pyproject_data", fake_load)

    with caplog.at_level(logging.DEBUG):
        check_python_dependencies(logger)

    assert caplog.messages == [
        "python dependency check skipped for /bad/pyproject.toml: boom",
        "required dependency 'missingpkg' is declared in good's pyproject.toml "
        "but is not installed",
        "good environment is out of sync with pyproject.toml; "
        "run 'pip install -e .' to update",
    ]
