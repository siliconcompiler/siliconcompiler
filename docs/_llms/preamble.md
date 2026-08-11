# SiliconCompiler

> A modular hardware build system -- "make for silicon". It compiles RTL to GDSII
> (ASIC) or a bitstream (FPGA) by driving pluggable flows over open-source and
> commercial EDA tools. Everything is configuration in a single versioned schema,
> and the Python API is a typed surface over that schema.

This file follows the [llms.txt](https://llmstxt.org) convention. It exists
because most of the material written about SiliconCompiler describes an API that
was removed in 2025, so an assistant answering from memory will usually be
wrong. The sections below state what is current; the index that follows links
every page on the documentation site.

## The current API

Import from `siliconcompiler`. A **`Design`** describes source code and is
reusable; a **project** describes one compilation of it.

Use one of the named project classes -- **`ASIC`, `FPGA`, `Lint` or `Sim`** --
rather than the bare `Project`. Choosing the class is how you say what kind of
build this is, and each named class carries the schema, constraints and metrics
for its domain. `Project` is only the base class they extend; a build script
written against it has no domain schema and will not fit the target or flow you
want.

```python
from siliconcompiler import ASIC, Design
from siliconcompiler.targets import skywater130_demo

design = Design("heartbeat")
design.set_dataroot("heartbeat", __file__)          # the root for files below
design.set_topmodule("heartbeat", fileset="rtl")
design.add_file("heartbeat.v", dataroot="heartbeat", fileset="rtl")
design.add_file("heartbeat.sdc", dataroot="heartbeat", fileset="sdc")

project = ASIC(design)
project.add_fileset(["rtl", "sdc"])                 # which filesets to compile
skywater130_demo(project)                           # PDK, libraries and flow
project.run()
project.summary()
```

Four conventions this example encodes:

- **Files live in named filesets** (`rtl`, `sdc`, `xdc`, `testbench`) rather than
  one flat list. `Design.add_file` assigns one; `Project.add_fileset` selects
  which the run uses.
- **Paths are rooted at a dataroot**, not the working directory. Passing
  `__file__` roots them at the directory holding the script -- a file path is
  accepted and its parent directory used -- so the build works from anywhere. An
  environment variable dataroot (`set_dataroot("foundry", "$FOUNDRY_ROOT/...")`)
  is how foundry data is referenced without committing it.
- **Prefer typed accessors to raw keypaths.** `project.option.set_remote(True)`
  and `project.set('option', 'remote', True)` reach the same value; the accessor
  is the supported interface. Use a keypath when no accessor exists, which mostly
  means reading metrics and records: `project.get('metric', 'cellarea',
  step='synthesis', index='0')`.
- **A target is a function you call** with the project. Flows, tool tasks,
  libraries and PDKs are classes you subclass.

Top-level exports, in full: `Design`, `Project`, `ASIC`, `FPGA`, `Lint`, `Sim`,
`PDK`, `StdCellLibrary`, `FPGADevice`, `Flowgraph`, `Checklist`, `Task`,
`TaskSkip`, `OpenTask`, `ShowTask`, `ScreenshotTask`, `NodeStatus`, `sc_open`,
`__version__`.

## What no longer exists

This section is the reason the file is worth fetching.

- **There is no `Chip` class.** `Chip('design')`, `chip.set(...)`,
  `chip.input(...)`, `chip.use(...)`, `chip.register_source(...)` and
  `chip.load_target(...)` were removed in **v0.35.0** (October 2025). They are
  what most training data contains. The replacement is `Design` + a project
  class; every old name is mapped in the migration guide linked below.
- **There is no `sc` command.** The console scripts are `sc-dashboard`,
  `sc-issue`, `sc-remote`, `sc-server`, `sc-show`, `sc-install` and `smake` --
  that is the complete list. A `sc -target asic_demo` invocation is from the
  pre-0.35 CLI and fails with `command not found`. To run something from a
  shell, use a Python script, `smake`, or
  `python3 -m siliconcompiler.demos.asic_demo`.
- **`FPGA` changed meaning.** It used to be the FPGA device class; it is now the
  FPGA *project* class. The device is `FPGADevice`.
- **Manifests are `.pkg.json`**, not `.cfg`. The `.cfg` extension predates
  v0.20 and any script or command using it is stale.
- **`package=` is now `dataroot=`** on every path parameter (schema 0.52.0).
- **The `option,mode` parameter is gone** -- pick the project class instead.

## Where new code goes

A frequent request is "add a PDK to SiliconCompiler", and the answer is usually
that it does not go in this repository:

- **Open-source PDKs and standard cell libraries** go in the separate
  [`lambdapdk`](https://github.com/siliconcompiler/lambdapdk) package.
- **Closed or proprietary PDKs and IP** go in your own pip-installable package,
  with foundry data referenced through environment-variable dataroots and never
  committed.
- **Tool drivers, flows and targets** go in-tree, under `siliconcompiler/`.

`siliconcompiler/pdks/` and `siliconcompiler/libs/` do not exist and should not
be created. In-tree module directories are `tools/`, `flows/`, `targets/` and
`checklists/`.

## Two version numbers

The package version and the schema version are independent. The schema version
(`schemaversion`) is recorded in every manifest and has its own changelog, which
is the authoritative record of what was added, renamed or removed at each
version -- see "Schema Changes" in the index below.

## Machine-readable schema

`schema.json` at the root of this site is a generated dump of the schema for each
project class: every parameter with its keypath, type, default, scope and help
text. Prefer it over scraping the HTML reference.

## Repository

Source, issues and discussions:
<https://github.com/siliconcompiler/siliconcompiler>. The repository root carries
an `AGENTS.md` with the same orientation aimed at editing the code rather than
using it. Working, tested designs are under `examples/`.
