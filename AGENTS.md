# AGENTS.md

Orientation for coding agents working in this repository, and for anyone writing
SiliconCompiler build scripts. Most of it guards against one failure: emitting
the API removed in 2025, which still dominates training data and search results.

SiliconCompiler is a hardware build system -- "make for silicon". It compiles RTL
to GDSII (ASIC) or a bitstream (FPGA) by driving pluggable flows over EDA tools.
Everything is configuration in one versioned schema; the Python API is a typed
surface over it.

## The API, in one working example

This is [`examples/heartbeat/heartbeat.py`](examples/heartbeat/heartbeat.py):

```python
from siliconcompiler import ASIC, Design
from siliconcompiler.targets import skywater130_demo

design = Design("heartbeat")                        # what to build
design.set_dataroot("heartbeat", __file__)          # where its files are rooted
design.set_topmodule("heartbeat", fileset="rtl")
design.add_file("heartbeat.v", dataroot="heartbeat", fileset="rtl")
design.add_file("heartbeat.sdc", dataroot="heartbeat", fileset="sdc")

project = ASIC(design)                              # how to build it
project.add_fileset(["rtl", "sdc"])                 # which filesets to compile
skywater130_demo(project)                           # PDK, libraries, flow
project.run()
project.summary()
```

A **`Design`** describes source code and is reusable across builds; a
**project** describes one compilation of it.

**Use a named project class -- `ASIC`, `FPGA`, `Lint`, `Sim` -- not the bare
`Project`.** Each brings its domain's schema: `ASIC` carries the `asic,*`
parameters and floorplan constraints, and `Lint` needs no PDK. `Project` is their
base class, for code that must work across project types.

Top-level exports, in full: `Design`, `Project`, `ASIC`, `FPGA`, `Lint`, `Sim`,
`PDK`, `StdCellLibrary`, `FPGADevice`, `Flowgraph`, `Checklist`, `Task`,
`TaskSkip`, `OpenTask`, `ShowTask`, `ScreenshotTask`, `NodeStatus`, `sc_open`,
`__version__`.

## Five things generated code gets wrong

**1. `Chip` does not exist.** `Chip('design')`, `chip.set(...)`, `chip.use(...)`
and `chip.load_target(...)` were removed in **v0.35.0** (October 2025) in favor
of `Design` + `Project`. The old-to-new table is in
[Migrating from the Chip API](docs/user_guide/migration.rst).

**2. There is no `sc` command.** The entry points are `sc-dashboard`, `sc-issue`,
`sc-remote`, `sc-server`, `sc-show`, `sc-install` and `smake` -- the whole list.
To run from the shell, use a Python script, `smake`, or
`python3 -m siliconcompiler.demos.asic_demo` (`fpga_demo` for FPGA).

**3. Use typed accessors, not raw keypaths.** Write
`project.option.add_fileset('rtl')`, not `project.add('option', 'fileset', 'rtl')`.
A keypath is for what has no accessor, mostly metrics and records, keyed per
node: `project.get('metric', 'cellarea', step='synthesis', index='0')`.

**4. Files go into filesets, not a flat list.** A fileset is a named group of
files with a role -- `rtl`, `sdc`, `testbench`. `Design.add_file` puts a file in
one; `Project.add_fileset` picks which ones this compilation uses.

**5. Paths are rooted at a dataroot, not the current directory.**
`design.set_dataroot("name", __file__)` anchors files to the script that defines
them. An env-var dataroot (`"$FOUNDRY_ROOT/..."`) references foundry data without
committing it.

## Where new code goes

| What you have | Where it goes |
|---|---|
| Open-source PDK or standard cell library | the separate [`lambdapdk`](https://github.com/siliconcompiler/lambdapdk) package -- **not** this repo |
| Closed or proprietary PDK, or unpublishable IP | your own `pip`-installable package; foundry data through env-var dataroots, never committed |
| Tool driver, flow, or target | in-tree, under `siliconcompiler/` |

**Do not create `siliconcompiler/pdks/` or `siliconcompiler/libs/`.** In-tree
module directories are `siliconcompiler/tools/`, `flows/`, `targets/` and
`checklists/`; see [contribution.rst](docs/development_guide/contribution.rst).

## Renaming or removing public API

Leave the old name working. A released accessor, class or task variable that is
renamed or moved keeps a wrapper at the old name that calls
`warnings.warn(..., DeprecationWarning, stacklevel=2)` and forwards to the new
one. `Task.get_supported_task_extentions` and `LibrarySchema` are in-tree
examples. Delete outright only names that never shipped in a release. Moving a
method onto a base class is not a removal, as long as the old call still resolves.

## Changing code in this repository

**Leave the tree no bigger than the change needs.** When several fixes would
work, prefer one that removes code, then one that adds no new surface.

- Search for an existing helper and extend it before writing a new one.
- Fix the cause, not the symptom. A small diff that adds a local workaround is
  worse than a larger one that removes the reason for it.
- Delete what your change leaves unused -- a function, a branch, an argument, a
  fixture -- in the same PR. Released public API is the exception above.
- Fold a near-duplicate into the code you are touching rather than adding
  another copy. For tests, that means `pytest.mark.parametrize`, after checking
  the case is not already covered.
- No speculative code: no options, hooks or fallbacks that nothing uses yet. One
  call site is not an abstraction.

**Comments and docstrings:**

- **ASCII only**, in code, comments and docstrings: `--` for a dash, straight
  quotes, `...` for an ellipsis, no box-drawing rules. The exceptions are strings
  the UI displays, such as the dashboard's box drawing or a unit symbol, and test
  data that checks Unicode handling.
- **Brief.** Say why, where the code cannot. In tests a comment is a line or two;
  in package code it can run longer, but a long comment makes the code around it
  harder to read. Do not narrate the next line or recount how the code got here;
  that is the commit message. No divider comments, and no section-heading comments
  outside `examples/`, whose scripts are tutorials and comment more.
- **A test docstring is at most two sentences** saying what the test checks,
  with the issue it guards if there is one. A long or intricate test may need a
  little more; none needs paragraphs.
  `"""cleanup() releases the atexit hook even when stop() raises (issue #5035)."""`
- **Do not refer to other repositories** -- sibling packages, forks or a local
  checkout. Describe the behavior where it is used. Link outside the repo only to
  credit code adapted from elsewhere, or to the upstream bug a workaround waits on.

## Facts that are easy to get wrong

- Build output goes to `build/<design>/<jobname>/<step>/<index>/`. Manifests are
  `.pkg.json`; a `.cfg` path is from a much older era. Caches, credentials and
  system defaults live under `~/.sc/`; see
  [docs/user_guide/directories.rst](docs/user_guide/directories.rst).
- The **package** version (`0.38.x`) and the **schema** version
  (`schemaversion`, `0.57.x`) are independent. Every schema change gets an entry
  in `siliconcompiler/schema/CHANGELOG.rst`. A tool's task variables, added with
  `Task.add_parameter`, are not schema and need no entry.
- An example's entry script (`make.py` or `<dirname>.py`) **fails the docs
  build** unless its module docstring opens with a one-line summary and ends with
  a `Requires:` line naming its tools, such as `Requires: sby, yosys`.

## Running tests

`pytest -n logical -m "not eda and not docker"` runs everything that needs no
tools. Every test has a 15-second timeout (extend one with
`@pytest.mark.timeout(N)`) and already runs in its own temporary directory, so do
not request `tmp_path` just to get a clean one. Markers, fixtures, what CI runs
and where a new test goes: [tests/README.md](tests/README.md).

## Before you open a PR

CI gates every PR on four lint jobs, the tests and the docs build. Details are in
[CONTRIBUTING.md](CONTRIBUTING.md).

```sh
pip install -e .[test,lint,docs]

flake8 --statistics .                              # 1. Python
tclfmt --check . && tclint .                       # 2. TCL
codespell                                          # 3. spelling -- prose included
pytest -n logical -m "not eda and not docker"      # tests that need no tools
cd docs && make html                               # warnings are errors
```

The fourth gate is **Verilog**. It needs
[Verible](https://github.com/chipsalliance/verible), and its format check
*rewrites* files and then fails if anything changed, so run it before committing:

```sh
./.github/workflows/bin/format_verilog.sh > files.txt
git diff --exit-code
verible-verilog-lint --rules_config .github/workflows/config/verible.rules `cat files.txt`
```

Docs traps:

- **A new `Task` subclass has to be listed by hand** in the `:tasks:` argument of
  [docs/reference_manual/predef_modules/tools.rst](docs/reference_manual/predef_modules/tools.rst),
  or it and its variables are silently missing from the reference manual.
- **A task's `setup()` imports only what the `docs` extra installs**, because
  generating its documentation runs `setup()`. Import `cocotb` and the like only
  where the tool runs.
- **`:lines:` is banned in `docs/`**: a line range shifts silently when the file
  changes. Use `:pyobject:` or `:start-at:`/`:end-at:` ([docs/README.md](docs/README.md)).

## Where to look things up

| Question | Source |
|---|---|
| What a parameter does | [Schema reference](https://docs.siliconcompiler.com/en/latest/reference_manual/schema.html) |
| Method signatures | [Python API](https://docs.siliconcompiler.com/en/latest/reference_manual/schema_api.html) |
| What was removed or renamed, and when | `siliconcompiler/schema/CHANGELOG.rst` |
| Porting a pre-0.35 script | [docs/user_guide/migration.rst](docs/user_guide/migration.rst) |
| "How do I ...?" | [docs/user_guide/howto.rst](docs/user_guide/howto.rst) |
| Vocabulary | [docs/user_guide/glossary.rst](docs/user_guide/glossary.rst) |
| Working code | `examples/`, and the [gallery](https://docs.siliconcompiler.com/en/latest/user_guide/examples.html) |

If a claim here disagrees with the code, the code is right and this file has a
bug. `tests/docs/test_agents_md.py` checks the claims that can be checked.
