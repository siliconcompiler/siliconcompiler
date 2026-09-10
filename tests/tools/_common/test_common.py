# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import os.path
import pathlib

import pytest

from siliconcompiler import Task
from siliconcompiler.tools._common import distinct, CCache


# ============================================================================
# distinct
# ============================================================================


def test_distinct_empty():
    assert distinct([]) == []


def test_distinct_no_duplicates():
    # Order preserved, nothing removed.
    assert distinct(["a", "b", "c"]) == ["a", "b", "c"]


def test_distinct_removes_duplicates():
    assert distinct(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_distinct_preserves_first_seen_order():
    # 'c' first appears before 'a', so it must come first in the result.
    assert distinct(["c", "a", "c", "a", "b"]) == ["c", "a", "b"]


def test_distinct_all_duplicates():
    assert distinct(["x", "x", "x"]) == ["x"]


def test_distinct_does_not_mutate_input():
    values = ["a", "a", "b"]
    result = distinct(values)
    assert values == ["a", "a", "b"]
    assert result == ["a", "b"]
    assert result is not values


def test_distinct_returns_new_list_when_unique():
    values = ["a", "b"]
    result = distinct(values)
    assert result == values
    assert result is not values


def test_distinct_paths():
    # Typical frontend use case: the same include dir contributed by two filesets.
    idirs = ["/proj/rtl/include", "/proj/common/include", "/proj/rtl/include"]
    assert distinct(idirs) == ["/proj/rtl/include", "/proj/common/include"]


# ============================================================================
# CCache
# ============================================================================

class BaseTask(Task):
    '''Stands in for the rest of the task chain.

    :class:`CCache` post-processes whatever the classes below it return, and a
    bare :class:`.Task` cannot answer outside a run -- it reads the project. This
    returns a fixed environment instead, so each test below pins one branch of
    the mixin's decision rather than the whole runtime.
    '''
    #: A CCACHE_DIR arriving from [option,env] or the task's own env.
    preset = None

    def tool(self):
        return "thistool"

    def get_runtime_environmental_variables(self, include_path=True):
        envvars = {"PATH": "this:path"} if include_path else {}
        if self.preset is not None:
            envvars["CCACHE_DIR"] = self.preset
        return envvars


class CCacheTask(CCache, BaseTask):
    '''A task whose tool drives ccache, with the cache directory pinned.'''
    @property
    def cachedir(self):
        return "/cache/tools/thistool"


@pytest.fixture(autouse=True)
def no_ambient_ccache(monkeypatch):
    '''A developer's own CCACHE_DIR must not decide what these tests see.'''
    monkeypatch.delenv("CCACHE_DIR", raising=False)


def env(task, include_path=False):
    return task.get_runtime_environmental_variables(include_path=include_path)


def test_ccache_post_processes_the_chain():
    '''Listed ahead of the concrete task, the mixin's method is the one that
    resolves, so it sees the environment the rest of the chain assembled. Listed
    behind a class that overrides the same method, it would never run.'''
    assert CCacheTask.get_runtime_environmental_variables is \
        CCache.get_runtime_environmental_variables

    class Backwards(BaseTask, CCache):
        pass

    assert "CCACHE_DIR" not in env(Backwards())


def test_sets_the_tool_cache():
    assert env(CCacheTask())["CCACHE_DIR"] == "/cache/tools/thistool"


def test_leaves_the_rest_of_the_environment_alone():
    assert env(CCacheTask(), include_path=True) == {
        "PATH": "this:path",
        "CCACHE_DIR": "/cache/tools/thistool"
    }


def test_task_env_wins():
    '''[option,env] and the task's own env land in the environment before this.'''
    task = CCacheTask()
    task.preset = "/task/ccache"

    assert env(task)["CCACHE_DIR"] == "/task/ccache"


def test_ambient_environment_wins(monkeypatch):
    monkeypatch.setenv("CCACHE_DIR", "/user/ccache")

    assert env(CCacheTask()) == {}


def test_task_env_wins_over_the_ambient_environment(monkeypatch):
    monkeypatch.setenv("CCACHE_DIR", "/user/ccache")
    task = CCacheTask()
    task.preset = "/task/ccache"

    assert env(task)["CCACHE_DIR"] == "/task/ccache"


def test_an_empty_ambient_setting_is_not_a_setting(monkeypatch):
    '''CCACHE_DIR= names no directory, so ccache falls back to its own default.'''
    monkeypatch.setenv("CCACHE_DIR", "")

    assert env(CCacheTask())["CCACHE_DIR"] == "/cache/tools/thistool"


def test_an_empty_task_setting_is_not_a_setting():
    task = CCacheTask()
    task.preset = ""

    assert env(task)["CCACHE_DIR"] == "/cache/tools/thistool"


def test_survives_its_own_export(monkeypatch):
    '''The node exports these variables into its own environment and then asks
    again, to write the replay script. Testing for presence rather than value
    would see this mixin's own previous answer and drop the variable, and the
    replay would run without the cache the run itself used.
    '''
    task = CCacheTask()

    first = env(task)
    monkeypatch.setenv("CCACHE_DIR", first["CCACHE_DIR"])

    assert env(task)["CCACHE_DIR"] == first["CCACHE_DIR"]


def test_reads_the_task_cache_directory():
    '''The directory is Task.cachedir, not a path the mixin builds itself.'''
    class DefaultCacheTask(CCache, BaseTask):
        pass

    assert env(DefaultCacheTask())["CCACHE_DIR"] == \
        os.path.join(pathlib.Path.home(), ".sc", "cache", "tools", "thistool")
