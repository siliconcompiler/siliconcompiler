# AGENTS.md

Orientation for coding agents working in this repository, and for anyone writing
SiliconCompiler build scripts. It is deliberately the same file humans read: a
separate AI-only document would rot.

Read this before generating SiliconCompiler code. Most of it is about avoiding
one specific failure -- confidently emitting an API that was removed in 2025 and
still dominates the training data, forum answers and search results.

## What SiliconCompiler is

A modular hardware build system -- "make for silicon". It compiles RTL to GDSII
(ASIC) or a bitstream (FPGA) by driving pluggable flows over open-source and
commercial EDA tools. Everything is configuration in a single, versioned schema;
the Python API is a typed surface over that schema.

## The API, in one working example

This is the current idiom. It is
[`examples/heartbeat/heartbeat.py`](examples/heartbeat/heartbeat.py), which runs.

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

The split matters: a **`Design`** describes source code and is reusable across
builds; a **project** describes one compilation of it.

**Use one of the named project classes -- `ASIC`, `FPGA`, `Lint`, `Sim` -- not
the bare `Project`.** Choosing the class is how you say what kind of build this
is, and each named class brings the schema, constraints and metrics for its
domain: `ASIC` carries the `asic,*` parameters and floorplan constraints, `Lint`
carries neither and needs no PDK. `Project` is the base class they extend. It is
the right choice only when writing code that must work across project types, and
the wrong choice for a build script -- a bare `Project` has no domain schema, so
the target and flow you want will not fit it.

Top-level exports, in full: `Design`, `Project`, `ASIC`, `FPGA`, `Lint`, `Sim`,
`PDK`, `StdCellLibrary`, `FPGADevice`, `Flowgraph`, `Checklist`, `Task`,
`TaskSkip`, `OpenTask`, `ShowTask`, `ScreenshotTask`, `NodeStatus`, `sc_open`.

## Five things generated code gets wrong

**1. `Chip` does not exist.** `Chip('design')`, `chip.set(...)`,
`chip.use(...)`, `chip.input(...)`, `chip.register_source(...)` and
`chip.load_target(...)` were removed in **v0.35.0** (August 2025) and replaced by
`Design` + `Project`. If you are about to write `Chip`, you are writing the old
API. See [Migrating from the Chip API](docs/user_guide/migration.rst) for the
old-to-new table.

**2. There is no `sc` command.** The entry points are `sc-dashboard`, `sc-issue`,
`sc-remote`, `sc-server`, `sc-show`, `sc-install` and `smake` -- that is the whole
list, from `[project.scripts]` in `pyproject.toml`. A bare `sc -target ...`
invocation is from the pre-0.35 CLI and will fail with `command not found`. To
run something from the shell, use a Python script, `smake`, or the demos:

```sh
python3 -m siliconcompiler.demos.asic_demo      # ASIC, remote by default
python3 -m siliconcompiler.demos.fpga_demo      # FPGA
```

**3. Prefer typed accessors over raw keypaths.** `project.option.add_fileset('rtl')`
and `project.get('option', 'fileset')` reach the same stored value, but the
accessor is the supported, self-documenting interface and is what the tutorials
and `examples/` use. Reach for a keypath only when no accessor exists -- most
often reading metrics and records, which are keyed per flowgraph node:

```python
project.get('metric', 'cellarea', step='synthesis', index='0')
```

Do not use a keypath for a parameter that has an accessor.

**4. Files go into filesets, not a flat list.** A `fileset` is a named group of
files with a role -- `rtl`, `sdc`, `xdc`, `testbench`. `Design.add_file` puts a
file in one; `Project.add_fileset` selects which ones this compilation uses. A
design can carry filesets it does not compile every time, which is the point.

**5. Paths are rooted at a `dataroot`, not the current directory.**
`design.set_dataroot("name", __file__)` anchors a design's files to the script
that defines them, so it works regardless of where it is run from. An
environment-variable dataroot (`set_dataroot("foundry", "$FOUNDRY_ROOT/...")`)
is how foundry data is referenced without committing it.

## Where new code goes

Answer this before writing a module -- the wrong destination is the most common
reason a contribution has to be restarted. Full table with links:
[docs/development_guide/contribution.rst](docs/development_guide/contribution.rst).

| What you have | Where it goes |
|---|---|
| Open-source PDK or standard cell library | the separate [`lambdapdk`](https://github.com/siliconcompiler/lambdapdk) package -- **not** this repo |
| Closed or proprietary PDK, or unpublishable IP | your own `pip`-installable package; foundry data referenced through env-var dataroots, never committed |
| Tool driver, flow, or target | in-tree, under `siliconcompiler/` |

**Do not create `siliconcompiler/pdks/` or `siliconcompiler/libs/`.** They do not
exist, and a stale guide told people to make them for years. In-tree module
directories are `siliconcompiler/tools/`, `flows/`, `targets/`, `checklists/`.

## Repo layout

| Path | Contents |
|---|---|
| `siliconcompiler/schema/` | the schema itself; `CHANGELOG.rst` records every parameter change under its own semver |
| `siliconcompiler/tools/` | one directory per EDA tool driver |
| `siliconcompiler/flows/`, `targets/` | pre-defined flowgraphs and target bundles |
| `siliconcompiler/apps/` | the seven CLI entry points |
| `siliconcompiler/toolscripts/` | per-OS tool install scripts, indexed by `_tools.json` |
| `examples/` | working, tested designs -- the entry script is `make.py` or `<dirname>.py` |
| `docs/` | Sphinx sources; `_ext/` holds build-time generators |
| `tests/` | pytest suite; `-m "not eda"` skips anything needing a tool |

Build output goes to
`build/<design>/<jobname>/<step>/<index>/{inputs,outputs,reports}/`. Manifests
are `.pkg.json` -- a `.cfg` path is from a much older era and is always stale.
Caches, credentials and system defaults live under `~/.sc/`. All of it is
documented in
[docs/user_guide/directories.rst](docs/user_guide/directories.rst).

Two independent version numbers: the **package** version (`0.38.x`) and the
**schema** version (`schemaversion`, `0.57.x`), which is what a manifest records
and what `siliconcompiler/schema/CHANGELOG.rst` tracks.

## Adding an example

`examples/` is enumerated at docs build time, so an example that does not
describe itself **fails the build**. Give the entry script -- `make.py`, or
`<dirname>.py` -- a module docstring whose first line is a one-line summary, and
end it with a `Requires:` line naming the tools it needs:

```python
"""Formal property checking with SymbiYosys.

Proves the SVA assertions carried by a small FIFO.

Requires: sby, yosys
"""
```

## Before you open a PR

Every PR is gated on **four** lint jobs plus the test suite and the docs build.
Agents fail these at the same rate humans do, and for the same reason: three of
the four are easy not to know about. Details in
[CONTRIBUTING.md](CONTRIBUTING.md).

```sh
pip install -e .[test,lint,docs]

flake8 --statistics .                              # 1. Python
tclfmt --check . && tclint .                       # 2. TCL
codespell                                          # 3. spelling -- prose included
pytest -m "not eda"                                # tests, no EDA tools needed
cd docs && make html                               # warnings are errors
```

The fourth gate is **Verilog**, and it is the sharpest edge: it needs
[Verible](https://github.com/chipsalliance/verible) (not a Python package), and
the format check *rewrites* files and then fails if anything changed. Run it
before committing and include whatever it reformats:

```sh
./.github/workflows/bin/format_verilog.sh > files.txt
git diff --exit-code
verible-verilog-lint --rules_config .github/workflows/config/verible.rules `cat files.txt`
```

Two rules that are not obvious from reading the tree:

- **The docs build treats warnings as errors** (`-W --keep-going`, plus
  `fail_on_warning` on Read the Docs). A broken cross-reference fails your PR.
- **`:lines:` is banned in `docs/`.** Address included code by name --
  `:pyobject:`, `:start-at:`/`:end-at:` -- because a line range silently shifts
  when the file above it changes, and the page then renders the wrong code with a
  green build. It has already happened. Conventions:
  [docs/README.md](docs/README.md).

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

If a claim in this file disagrees with the code, the code is right -- and the
disagreement is a bug worth fixing here. `tests/docs/test_agents_md.py` checks
the parts of it that can be checked mechanically.
