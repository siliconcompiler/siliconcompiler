# SiliconCompiler tests

The pytest suite. Install it with `pip install -e .[test]`.

## Running tests

```sh
pytest -n logical -m "not eda and not docker"   # everything that needs no tools
pytest tests/schema/test_baseschema.py          # one file
pytest tests/schema/test_baseschema.py::test_copy
pytest -k topmodule                             # every test whose name matches
```

What CI runs:

| When | Markers | Needs |
|---|---|---|
| every push and PR | `-m "not eda and not docker"` | nothing |
| every push and PR | `-m "eda and quick"` | EDA tools |
| every push and PR | `-m "docker and quick"` | Docker |
| nightly | `-m "not docker"` | EDA tools |

Useful options:

- `-n logical` runs tests in parallel.
- `-s` shows a test's output instead of capturing it.
- `--cwd` runs tests in the current directory instead of a temporary one.
- `--clean` deletes each test's temporary directory when it finishes.

To run `eda` tests locally, set `SCTESTCACHE=<dir>` so every test shares one
download cache, as CI does.

## What every test gets

These are autouse fixtures in `conftest.py`, so a test does not ask for them:

- **Its own temporary working directory.** Do not request `tmp_path` just to get
  a clean working directory.
- **A private home directory.** `HOME` points into pytest's temporary root, so
  `~/.sc` is never the developer's own, and `SC_SYSTEM_SETTINGS` is unset.
- **A 15-second timeout**, from `pyproject.toml`. Use
  `@pytest.mark.timeout(N)` for a test that needs longer.
- **`SCTESTCACHE` as the cache directory**, when it is set.
- **For `eda` tests:** at most two CPU cores, and OpenROAD image generation off.

## Markers

| Marker | Meaning |
|---|---|
| `eda` | needs EDA tools; runs nightly |
| `quick` | with `eda` or `docker`, also runs on every push |
| `docker` | needs Docker |
| `slurm` | needs slurm; skipped automatically without it |
| `nocpulimit` | an `eda` test that may use every core |
| `nocache` | do not apply `SCTESTCACHE` |
| `isolated_manager` | gets its own MPManager server, for tests of the manager's lifecycle |

`pytest --markers` lists them with pytest's built-in ones.

## Writing tests

- **Where it goes:** the layout mirrors the package. A test for
  `siliconcompiler/<pkg>/<module>.py` goes in `tests/<pkg>/test_<module>.py`, and
  one for a top-level module such as `project.py` in `tests/test_project.py`. Tool
  drivers are tested in `tests/tools/test_<tool>.py`, and examples in
  `tests/examples/`.
- **Data:** a directory's own data lives in its `data/` folder, reached with the
  `datadir` fixture. Data shared across directories lives in `tests/data/`, under
  the `scroot` fixture.
- **Ready-made projects:** `heartbeat_design`, `gcd_design` and their ASIC
  projects `asic_heartbeat` and `asic_gcd`. `pytest --fixtures tests/conftest.py`
  lists every fixture.
- **Markers:** a test that runs a tool is `eda`. Add `quick` only if it has to
  run on every push.
- **Docstrings and comments** follow the rules in
  [AGENTS.md](../AGENTS.md#changing-code-in-this-repository).
