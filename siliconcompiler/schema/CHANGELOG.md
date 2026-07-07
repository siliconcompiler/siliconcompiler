# Schema Changelog

All notable changes to the SiliconCompiler **schema version** (`schemaversion`)
are documented here. The schema version follows [semver](https://semver.org).

The current version is defined in [`_metadata.py`](_metadata.py). It lived in
`schema_cfg.py` (as `SCHEMA_VERSION`) prior to 0.52.0, and moved to
`schema/_metadata.py` during the 0.51.5 → 0.52.0 transition.

Entries describe the actual schema/parameter changes for each version (derived
from the code diffs, not the commit messages). Dates are the git commit dates of
the version bump. Version numbering was not strictly linear during early
development, so a few dates are non-monotonic relative to the semver ordering.

## 0.56.0 — 2026-07-07
- Added value ranges/limits to numeric schema types via a new `NodeRangeType`
  and `int<...>`/`float<...>` type syntax (e.g. `int<0..100>`, `float<0.0..1.0>`,
  open-ended `int<0..>`); `str<...>` is treated as an enum. Ranges are validated
  on set and encoded into the serialized type string.

## 0.55.0 — 2026-07-01
- Changed the global-value key from `'global'` to `'*'` to avoid name conflicts,
  with legacy read support for older manifests.

## 0.54.0 — 2026-01-09
- Removed the standalone library schema; `LibrarySchema`/`ToolLibrarySchema` now
  derive from `Design` — everything is a design.

## 0.53.1 — 2026-01-06
- Added the `physicalonly` cell type to ASIC library cells to better support
  LVS/LEC netlist generation.

## 0.53.0 — 2025-12-01
- Separated timing **mode** information from **scenario** information in the
  constraints schema to make multi-mode timing easier to work with.

## 0.52.1 — 2025-10-31
- Moved libraries into a separate class to avoid extra dependency evaluations.

## 0.52.0 — 2025-10-01
- Renamed the `package` field to `dataroot` throughout path parameters and the
  `find_files`/`check_filepaths` APIs.
- Version definition moved from `schema_cfg.py` to `schema/_metadata.py`.

## 0.51.5 — 2025-08-29
- Removed the legacy `schema_cfg.py` setup and updated the schema version flag;
  no substantive parameter change.

## 0.51.4 — 2025-06-02
- Switched the tool schema import to a temporary placeholder (`ToolSchemaTmp`)
  during the class migration; records now capture microsecond-resolution
  start/end times.

## 0.51.3 — 2025-05-16
- Replaced inline FPGA and PDK parameter definitions with insertion of the
  separate `FPGASchema` and `PDKSchema` modules; simplified the schematic/fpga
  section signatures.

## 0.51.2 — 2025-05-13
- Removed the `schema_task()` function and all task-related definitions; tool
  task definitions moved to a dedicated `ToolSchema` class, with scope fixes.

## 0.51.1 — 2025-05-09
- Removed all PDK-related definitions from `schema_cfg.py` (migrated to the
  separate `PDKSchema` module); fixed flowgraph scope.

## 0.51.0 — 2025-05-05
- Major architecture refactor: moved from the flat `scparam` dictionary model to
  a `Parameter`-based object model with `EditableSchema`, `Scope`, and `PerNode`
  enums. PDK, FPGA, and tool definitions began migrating out to separate schema
  modules.

## 0.50.0 — 2025-02-21
- Reduced `constraint,pin` dimensions from three (width, length, height) to two
  (width, height) — a pin sits on a 2D surface.
- Renamed `constraint,component` `height` to `zheight`; made component
  `rotation` per-node; simplified the `substrate` reference.

## 0.49.0 — 2025-02-10
- Advanced-packaging update: `datasheet,package,<name>,footprint` changed from
  string to `file`; added a `3dmodel` file parameter.
- Added `constraint,component,<name>,substrate` and `side`
  (enum: left/right/front/back/top/bottom); renamed component `height` to
  `zheight`.
- Reworked package pin metrics (e.g. `pitch` → `pinpitch`) and pin signal
  mapping.

## 0.48.6 — 2024-12-20
- Added the `quiet` value to the `option,loglevel` enum.

## 0.48.5 — 2024-12-09
- Added `record,pythonversion` and `record,pythonpackage` (list of installed
  packages); made `record,remoteid` non-per-node.

## 0.48.4 — 2024-11-05
- Added metrics `macroarea`, `padcellarea`, and `stdcellarea`.

## 0.48.3 — 2024-11-05
- Added back the `datasheet,package,<name>,footprint` parameter (as a `file`).
- Corrected version numbering: adding schema parameters only bumps the patch
  digit (`0.0.X`). This reverted an erroneous 0.49.0 bump made on 2024-11-04.

## 0.48.2 — 2024-09-18
- Added `defvalue='R0'` to the component rotation parameter and reorganized its
  enum, with expanded documentation.

## 0.48.1 — 2024-09-17
- Added `unit='nm'` to `pdk,<name>,node`; changed
  `datasheet,package,pin,<pinnumber>,loc` unit from `mm` to `um`; used keypaths
  to cross-link keys in the docs.

## 0.48.0 — 2024-09-15
- Restructured the schematic parameters into a hierarchical form.
- Changed `constraint,component,<name>,rotation` from float to an 18-value enum
  (R0/R90/R180/R270 plus mirror variants); removed the separate `flip`
  parameter; moved origin handling to `datasheet,package,<name>,anchor`.

## 0.47.0 — 2024-09-06
- Added a schematic/netlist section: `component,<name>,model`, `pin,<name>,dir`,
  `net,<name>,connect`, plus `hierchar` and `buschar`.

## 0.46.0 — 2024-09-06
- Added `constraint,component,<name>,origin`, default `(0.0, 0.0)` — supports
  changing the default origin from center to the lower-left corner for packaging
  and board design.

## 0.45.1 — 2024-09-05
- Cleaned up short-help strings and capitalization (no substantive parameter
  change).

## 0.45.0 — 2024-09-04
- Restructured datasheet package pins into a hierarchical
  `pin,<pinnumber>,{shape,width,length,loc,name}` form, replacing the flat
  `pinshape`/`pinwidth`/`pinlength`/`pinloc`/`netname`/`portname` keys.

## 0.44.5 — 2024-09-03
- Changed `constraint,component,<name>,placement` and
  `constraint,pin,<name>,placement` from `(float,float,float)` to
  `(float,float)`.

## 0.44.4 — 2024-08-27
- Removed the `option,target` parameter (targets now loaded by the app).

## 0.44.3 — 2024-08-09
- Added `datasheet,package,<name>,portname` (net name is not always the port
  name); added `copy=True` to file/dir parameters (tool task file/dir/scripts
  and `option` file/dir/idir/ydir/vlib).

## 0.44.2 — 2024-07-29
- Lowercased the `option,loglevel` enum
  (`info/warning/error/critical/debug`, default `info`), separating it from
  Python logger levels.

## 0.44.1 — 2024-07-26
- Added `record,toolexitcode` (per-node int); removed `option,copyall`.

## 0.44.0 — 2024-07-25
- Renamed `record,exitstatus` to `record,status` and expanded its enum with
  `queued`, `running`, and `timeout` states.

## 0.43.1 — 2024-07-23
- Removed `option,frontend`; made `option,entrypoint` per-node optional.

## 0.43.0 — 2024-07-22
- Moved runtime info into the record: removed flowgraph `status`/`select`; added
  `record,exitstatus` (enum) and `record,inputnode` (`[(str,str)]`, per-node).

## 0.42.7 — 2024-07-19
- Changed the `require` default from `None` to `False` across parameters and
  dropped the mode-specific `require` markers (`'all'`/`'asic'`/`'fpga'`);
  removed `option,mode`.

## 0.42.6 — 2024-07-09
- Help-text/shorthelp refinements for datasheet package pin parameters (no
  substantive parameter change).

## 0.42.5 — 2024-07-08
- Added `output` to the task `stdout`/`stderr` destination enum
  (`log/output/none`); removed the `jobinput` key.

## 0.42.4 — 2024-07-08
- Removed FPGA resource/board parameters and several PDK parameters
  (`thickness`, `density`); combined `hscribe`/`vscribe` into `scribe`
  (`(float,float)`); renamed PDK `directory` → `dir`; restructured PDK `doc` by
  `doctype`; removed several option/task flags; removed ASIC cell types
  `delay`/`clkdelay`/`clkinv`/`clkicg`.

## 0.42.3 — 2024-07-08
- Changed `option,scheduler,msgevent` from a string to an enum list
  (`all/summary/begin/end/timeout/fail`).

## 0.42.2 — 2024-07-08
- Removed the task `keep` parameter and `option,resume`; changed `option,clean`
  semantics to "start a job from the beginning".

## 0.42.1 — 2024-07-07
- Removed `option,showtool,<filetype>`.

## 0.42.0 — 2024-07-07
- Breaking cleanup: removed the `unit,*` section, `pdk,<name>,lambda`,
  `option,uselambda`, flowgraph `timeout`, and assorted FPGA/PDK/option
  parameters; renamed `option,cache` → `option,cachedir` and PDK `directory` →
  `dir`.

## 0.41.1 — 2024-07-05
- Added metrics `drcs`, `holdskew`, `setupskew`, and `inverters` (split from
  `buffers`); removed `dozepower`, `idlepower`, and `sleeppower`.

## 0.41.0 — 2024-07-03
- Restructured `datasheet,package` to be indexed by package `name`, merging the
  standard and generation parameters and folding per-pin package data under the
  package hierarchy.

## 0.40.8 — 2024-07-03
- Merged the datasheet standard and generation parameters; removed
  `datasheet,partnumber`, `datasheet,abstraction`, and `datasheet,io,<name>,gen`;
  refined the IO `arch` enum.

## 0.40.7 — 2024-07-02
- Added `docker` to the `option,scheduler,name` enum (docker-based running).

## 0.40.6 — 2024-05-30
- Renamed `option,scheduler,maxconcurrency` → `option,scheduler,maxnodes`; added
  directory-hash (`filehash`) support.

## 0.40.5 — 2024-05-28
- Added `option,scheduler,maxconcurrency` (max concurrent local jobs).

## 0.40.4 — 2024-04-21
- Added the `metric,logicdepth` parameter.

## 0.40.3 — 2024-03-14
- Added FPGA resource parameters `fpga,<partname>,resources,{registers,dsps,brams}`.

## 0.40.2 — 2024-03-05
- Added `option,library` (per-node list) for soft libraries.

## 0.40.1 — 2024-02-28
- Added datasheet top-level parameters (`partnumber`, `type`, `series`,
  `manufacturer`, `grade`, `qual`, `trl`, `status`, `fmax`, `ops`, `iobw`,
  `iocount`, `ram`, `peakpower`, etc.); corrected several switch help strings.

## 0.40.0 — 2023-12-18
- First standardized datasheet metrics: restructured `datasheet` into
  hierarchical `processor,<name>,*`, `io,<name>,*`, `fpga,<name>,*`, and
  `package,<name>,*` (with `pincount`, `drawing`) namespaces.

## 0.39.0 — 2023-11-17
- Added `option,cache`; removed `option,scpath`; reworked the package parameters
  (`package,version/description/keyword/license/organization`, `package,doc,*`,
  contact fields).

## 0.38.0 — 2023-11-02
- Added a `dependency,<dep>,{path,commitid,name}` section (later reconciled with
  the package schema).

## 0.37.2 — 2023-11-02
- Removed `option,registry` and the entire `package,*` section (name, version,
  description, keyword, doc, license, organization, contact, …).

## 0.37.1 — 2023-10-26
- Removed the flowgraph node `valid` flag; added `option,prune` (`[(str,str)]`).

## 0.37.0 — 2023-09-20
- Replaced `option,steplist`/`option,skipstep`/`option,indexlist` with
  `option,from` and `option,to`.

## 0.36.0 — 2023-08-30
- Moved job IDs into the core schema and removed the `skipstep` option;
  restructured FPGA `<partname>` (added `file,*`/`var,*`) and datasheet
  package/pin parameters.

## 0.35.0 — 2023-08-03
- Cosmetic/FPGA-prep changes: removed `fpga,arch`; added `fpga,<family>,lutsize`;
  moved FPGA `vendor` under `<partname>`; added `record,remoteid`.

## 0.34.7 — 2023-08-09
- Reworked datasheet pin/mechanical parameters: renamed
  `datasheet,pin,*,signal` ↔ `interface`, changed `map` to be indexed by `<bump>`
  as `(float,float)` in `um`.

## 0.34.6 — 2023-08-08
- Fixed examples in the record portion of the schema (no substantive parameter
  change).

## 0.34.5 — 2023-07-29
- Fixed a typo in a switch flag (no substantive parameter change).

## 0.34.4 — 2023-07-27
- Fixed typos in schema help strings (no substantive parameter change).

## 0.34.3 — 2023-06-13
- Fixed a `constraint,net,<name>,shield` switch-name typo (documentation only).

## 0.34.2 — 2023-06-09
- Changed `tool,<tool>,format` to an enum (`json`/`tcl`/`yaml`).

## 0.34.1 — 2023-06-09
- Fixed CLI switch quoting (no substantive parameter change).

## 0.34.0 — 2023-05-19
- Restructured node value storage (nested `default,default,value`); added
  file-node metadata (`date`, `author`, `filehash`); changed timing `voltage`
  to per-pin (`constraint,timing,<scenario>,voltage,<pin>`); changed
  `option,credentials` from `[file]` to `file`.

## 0.33.0 — 2023-05-17
- Added `tool,task,dir` (user-supplied directories mapped to keys); added pin
  voltage support to constraints; made the credentials file a single file.

## 0.32.0 — 2023-04-12
- Whitespace/formatting cleanup (no substantive parameter change).

## 0.31.0 — 2023-04-01
- Added SBOM traceability and made scheduler options
  (`cores/memory/queue/defer/options/msgevent/msgcontact`) per-node optional.

## 0.30.0 — 2023-04-07
- Added a copy flag to directory parameters.

## 0.29.0 — 2023-03-30
- Added task-module support; improved switch handling and help strings.

## 0.28.0 — 2023-03-06
- Added the `metric,fmax` parameter.

## 0.27.0 — 2023-02-24
- Removed the `signature` field from parameter metadata; renamed `nodefield` to
  `node`.

## 0.26.0 — 2023-02-21
- Put the global value into the same dict as per-node values: removed the
  separate `value`/`set`/`filehash`/`date`/`author` fields, renamed `nodevalue`
  to `nodefield`.

## 0.25.0 — 2023-02-20
- Added `option,strict`; made many scheduler/constraint parameters per-node
  optional.

## 0.24.0 — 2023-02-13
- Added back the `option,dir` parameter.

## 0.23.0 — 2023-02-10
- Removed step/index from task parameters (warningoff, continue, regex, option,
  var, env, file, input, output, stdout, stderr, require, report, refdir,
  script, prescript, postscript, keep); made `tool` path/version/licenseserver
  per-node optional.

## 0.22.0 — 2023-02-02
- Flattened metrics from `metric,<step>,<index>,<item>` to `metric,<item>` with
  `pernode='required'`; removed `arg,pdk` and `arg,flow`.

## 0.21.0 — 2023-01-31
- Renamed `option,bkpt` to `option,breakpoint`.

## 0.20.0 — 2023-01-27
- Replaced `option,jobscheduler`/`msgevent`/`msgcontact` with an
  `option,scheduler,*` subgroup (`name/cores/memory/queue/defer/options/
  msgevent/msgcontact`); added `option,timeout`.

## 0.19.0 — 2023-01-27
- Added `option,nice`, `option,var,<key>`, `option,file,<key>`; removed the
  per-tool `asic,{file,dir,var}` parameters.

## 0.18.0 — 2023-01-26
- Removed the `server,*` section (cores, memory, queue, nice, timeout,
  interactive, defer).

## 0.17.0 — 2023-01-25
- Added job-scheduler management via a `server,*` section
  (cores/memory/queue/nice/timeout/interactive/defer); removed `option,nice`.

## 0.16.1 — 2023-01-21
- Removed the PDK layer `grid` section and `asic` layer/footprint parameters
  (`rclayer`, `vpinlayer`, `hpinlayer`, `pgmetal`, footprint alias/symmetry/size);
  added `asic,site,<libarch>` and `option,nice`.

## 0.15.0 — 2023-01-25
- Added the `enum` type and switched mode/loglevel/status to enums; added
  `pdk,<name>,{minlayer,maxlayer},<stackup>`, `option,uselambda`,
  `constraint,pin,<name>,{side,order}`, and several
  `constraint,net,<name>,*` parameters.

## 0.14.0 — 2023-01-22
- Moved ASIC constraints into the common `constraint` group (renaming
  `diearea` → `outline`, adding `corearea`/`coremargin`/`density`/`aspectratio`);
  made net `maxlayer`/`minlayer` per-net.

## 0.13.0 — 2023-01-22
- Moved `lambda` from top-level into `pdk,<name>,lambda`; removed duplicate
  `asic,pdk`/`asic,stackup` and assorted `asic` max* parameters; moved stackup to
  options.

## 0.12.0 — 2023-01-18
- Added `datasheet,<design>,footprint` and `flowgraph,<flow>,<step>,<index>,task`.

## 0.11.0 — 2023-01-15
- Added the tool/task split (`schema_task()` hierarchy); reworked input/output
  parameters to `[item, fileset, filetype]`; removed the early
  `lambda`/`schematic`/`layout` sections.

## 0.10.0 — 2023-01-01
- Added an initial unified layout/schematic structure (`schematic,*` and
  `layout,*` groups covering components, pins, nets, outline, footprint) plus a
  top-level `lambda`.

## 0.9.0 — 2022-08-31
- Initial schema object.
