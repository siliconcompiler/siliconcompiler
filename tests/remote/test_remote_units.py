'''Numbers as a person reads them.

The wire carries base units and always will; this is the one place that
decides how they are shown, so that the CLI and the portal cannot disagree.
'''

import pytest

from siliconcompiler.remote.units import duration, size


@pytest.mark.parametrize("value,shown", [
    (None, "—"),
    (0, "0 B"),
    (12, "12 B"),
    (1023, "1023 B"),
    (1024, "1.0 KiB"),
    (1536, "1.5 KiB"),
    # 🔴 Every byte ceiling this deployment publishes is an exact power of
    # 1024, and binary is what renders them as the round numbers they are.
    # Decimal would show these three as 104.9 MB, 1.07 GB and 10.74 GB, on the
    # page where an operator checks the limit they set.
    (104857600, "100 MiB"),
    (1073741824, "1.0 GiB"),
    (10737418240, "10.0 GiB"),
    # Three significant figures is enough at this magnitude: 1004.7 MiB is
    # harder to read than 1005 MiB.
    (1053818880, "1005 MiB"),
])
def test_a_size_reads_as_a_size(value, shown):
    assert size(value) == shown


def test_a_size_that_is_not_a_number_is_not_a_crash():
    '''It renders a dash on a page, which is what a missing number is.'''
    assert size("nonsense") == "—"


@pytest.mark.parametrize("value,shown", [
    (None, "—"),
    (0, "0s"),
    (42, "42s"),
    (60, "1m 00s"),
    (432, "7m 12s"),
    (11100, "3h 05m"),
    (194400, "2d 06h"),
])
def test_a_duration_reads_as_a_duration(value, shown):
    '''Two units, never three: the third is never what the question was.'''
    assert duration(value) == shown


@pytest.mark.parametrize("name,member", [("JobStatus", "TIMEOUT"), ("NodeStatus", "UPLOADED")])
def test_the_old_protocols_status_names_still_work_and_say_why_not(name, member):
    '''Released, and read by nothing since v1: kept working, with a warning
    pointing at what replaced them (AGENTS.md, *Renaming or removing public
    API*).'''
    import siliconcompiler.remote as remote

    with pytest.warns(DeprecationWarning, match=f"remote.{name} is deprecated"):
        found = getattr(remote, name)
    assert hasattr(found, member)
    assert name not in remote.__all__


def test_the_client_never_imports_the_server():
    '''🔴 The client runs without the server extra, and importing anything
    under `siliconcompiler.remote.server` loads that package. So no module a
    client run reaches imports from it -- at the top or inside a function.'''
    import ast
    import os

    import siliconcompiler.remote as remote

    root = os.path.dirname(remote.__file__)
    reached = [os.path.join(root, name) for name in os.listdir(root) if name.endswith(".py")]
    for folder, _, files in os.walk(os.path.join(root, "client")):
        reached += [os.path.join(folder, name) for name in files if name.endswith(".py")]

    found = []
    for path in reached:
        for node in ast.walk(ast.parse(open(path).read())):
            names = [node.module or ""] if isinstance(node, ast.ImportFrom) else \
                [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            found += [f"{os.path.relpath(path, root)}:{node.lineno} {name}" for name in names
                      if name.startswith("siliconcompiler.remote.server")]
    assert found == []


def test_a_part_of_the_server_loads_without_flask():
    '''The run's own process and the manifest's read load modules from the
    server, and neither has a web server to import.'''
    import subprocess
    import sys

    script = (
        "import sys, importlib.abc\n"
        "class NoFlask(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name.split('.')[0] in ('flask', 'werkzeug', 'jinja2'):\n"
        "            raise ImportError(name)\n"
        "sys.meta_path.insert(0, NoFlask())\n"
        "import siliconcompiler.remote.server.running.runner\n"
        "import siliconcompiler.remote.server.staging.manifestread\n"
        "import siliconcompiler.remote.client.run\n")
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    assert done.returncode == 0, done.stderr
