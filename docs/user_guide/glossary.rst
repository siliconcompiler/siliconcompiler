.. _glossary:

Glossary
===================================

The following set of terms represents fundamental SiliconCompiler definitions used throughout the documentation.

The first three sections cover vocabulary specific to SiliconCompiler -- its
objects, its execution model, and its schema. The remaining sections cover the
standard semiconductor vocabulary that appears throughout the documentation and
in tool output, grouped by where you meet it: general hardware design, the ASIC
and FPGA implementation flows, verification, and the file formats that move data
between tools.

SiliconCompiler concepts
------------------------

.. glossary::

    checklist
       A named set of requirements a :term:`design` must satisfy, each one
       either checked automatically against a recorded :term:`metric` or signed
       off by a person, with the evidence kept in the :term:`manifest`. Turns
       :term:`signoff` from a conversation into an auditable object. See
       :ref:`Checklists <checklists>`.

    dataroot
       A named data source that file paths are resolved against.
       A dataroot can be a local directory, a git repository, or a downloadable
       archive, and is registered with ``set_dataroot(name, path, tag=None)``.
       The optional ``tag`` is a version identifier for remote sources -- a git
       commit, branch, or tag.
       Storing files relative to a dataroot is what lets a :term:`design` be
       shared and rebuilt on another machine.

    design
       The hardware being compiled, described by a :class:`.Design` object: a
       top-level module name plus the :term:`filesets <fileset>` that hold its
       sources and constraints.
       A design is independent of any one technology; pairing it with a
       :term:`target` is what makes it buildable.

    fileset
       A named group of input files belonging to a :term:`design` or
       :term:`library`, such as ``rtl``, ``sdc``, or ``testbench``.
       Filesets let one design carry several alternative or complementary
       sets of sources and select among them per run.

    flow
       The sequence of compilation steps to run, expressed as a
       :term:`flowgraph`. ``asicflow``, ``synflow``, and ``signoffflow`` are
       examples. A flow describes *what to do*; a :term:`target` chooses which
       flow to use along with the technology to do it in.

    KPI
       Key Performance Indicator -- the handful of :term:`metrics <metric>` a
       run is actually judged on: area, power, timing :term:`slack`, and error
       counts. Every KPI is a metric, but a run records plenty of metrics that
       nobody is judging it by.

    library
       A reusable collection of design data added to a project as a dependency.
       A standard cell :term:`library` (:class:`.StdCellLibrary`) supplies the
       logic gates a synthesis tool maps to; other libraries package
       :term:`IP`, SRAMs, or I/O cells. Libraries are described with the same
       :term:`filesets <fileset>` and :term:`dataroots <dataroot>` as a
       :term:`design`.

    mainlib
       The primary standard cell :term:`library` for an :term:`ASIC` build, set
       with ``set_mainlib()``. Additional libraries added with ``add_asiclib()``
       supplement it during optimization.

    metric
       A quantitative result recorded by a :term:`task`, such as cell area,
       setup slack, or error count. Metrics are stored per
       :term:`flowgraph node`, which is why they are read with an explicit step
       and index. See :ref:`Working with Metrics <dev_metrics>`.

    PDK
       Process Design Kit -- the technology data a foundry supplies for a
       specific manufacturing process: layer definitions, design rules, device
       models, and the tool setup files that go with them.
       Open PDKs supported by SiliconCompiler are packaged in
       `lambdapdk <https://github.com/siliconcompiler/lambdapdk>`_.

    record
       Provenance data captured during a run -- tool versions, machine and user
       information, timestamps -- stored alongside :term:`metrics <metric>` so a
       build can be audited and reproduced. See :ref:`Execution Records <dev_records>`.

    target
       A function that configures a project for a particular technology in one
       call, selecting the :term:`PDK`, the standard cell
       :term:`libraries <library>`, the :term:`flows <flow>`, and the physical
       defaults that go with them. ``skywater130_demo`` is a target.

    uniquify
       To generate a separate, parameter-free copy of a parameterized module for
       each distinct set of parameter values it is instantiated with, so each
       copy can be hardened independently.
       Automated by :class:`.Uniquified`; see
       :ref:`Hardening parameterized modules <uniquify_modules>`.

Compilation model
-----------------

.. glossary::

    edge
       A directed connection between a tail node and head nodes in a flowgraph.

    flowgraph
       A directed acyclic graph specification of the hardware compilation.

    flowgraph node
       A **node** -- a single executable unit of a :term:`flowgraph`, identified
       by a (:term:`step`, :term:`index`) pair. Each node runs one :term:`task`
       with one :term:`tool`, in its own directory under the job directory, and
       carries its own :term:`metrics <metric>` and :term:`records <record>`.
       Nodes are connected by :term:`edges <edge>`.
       Not to be confused with the schema parameter field also called
       :term:`node`.

    index
       A variant of a :term:`step` operating on identical input data.
       Indices are what make a step run more than once in parallel -- to try
       several tool configurations, or to explore a parameter sweep -- and the
       results are compared to pick a winner.
       A step run only once has index ``0``.

    job
       Execution of complete or partial compilation flowgraph.

    manifest
       JSON file representation of the SiliconCompiler schema.
       See :ref:`Directory structures <directory_structures>` for where
       manifests are written during a run.

    program
       User specified program with one (or more) project instances.

    project
       Instance of SiliconCompiler Project class used to compile a design.

    step
       A discrete function in a flowgraph, such as synthesis, linting,
       placement, or routing.

    task
       The unit of work a :term:`flowgraph node` executes: a specific operation
       performed by one :term:`tool`, such as ``yosys/syn_asic`` or
       ``openroad/route``.

    tool
       Executable associated with a task in a flowgraph.

Schema
------

.. glossary::

    default
       Reserved SiliconCompiler schema key that can be replaced by any legal string.

    dictionary
       Associative array, ie. a collection of key-value pairs.

    keypath
       Ordered list of keys used to access schema parameters.

    keys
       Immutable strings used as index into dictionary.

    keywords
       Reserved strings that cannot be used as key names.

    list
       An ordered and mutable sequence of elements.

    parameter
       Schema leaf cell with a set of pre-defined key/value pairs.

    schema
       Nested dictionary of parameters.

Hardware design
---------------

Vocabulary that applies to any hardware compilation, whether the destination is
an :term:`ASIC` or an :term:`FPGA`.

.. glossary::

    elaboration
       Turning a design's sources into a resolved design hierarchy: reading
       every file, binding each module instance to its definition, and
       substituting parameter values. Runs ahead of :term:`synthesis`, and is where missing
       files, unresolved modules and parameter mistakes surface -- which is why
       ``elaborationflow`` exists as a flow on its own.

    HDL
       Hardware Description Language -- a language for describing hardware
       rather than a program's behavior over time. :term:`Verilog`,
       :term:`SystemVerilog` and :term:`VHDL` are the three in wide use, and a
       :term:`design` names its sources by :term:`fileset` regardless of which
       it uses. Higher-level frontends such as Chisel, Amaranth and Bluespec
       generate one of them rather than replacing it; see
       :ref:`Hardware Frontends <hw_frontends>`.

    HLS
    high-level synthesis
       Compiling a description of *what* to compute -- C, or a machine learning
       kernel -- into :term:`RTL`, with the tool deciding the datapath, the state
       machine and the schedule rather than the author writing them. What is
       gained is that an algorithm becomes hardware without being rewritten;
       what is given up is direct control over the microarchitecture, so results
       depend heavily on how the input was optimized beforehand. SiliconCompiler
       drives Bambu (see :ref:`the C HLS frontend <c_hls_frontend>`) and, through
       :term:`MLIR`, SODA Synthesizer (:ref:`the SODA tutorial
       <soda_tutorial>`).

    IP
       Intellectual Property -- a reusable design block. Delivered either as
       *soft* IP (:term:`RTL` you synthesize yourself) or *hard* IP (a
       :term:`hardened macro` with fixed layout and timing views). Packaged in
       SiliconCompiler as a :term:`library`.

    MLIR
       A compiler infrastructure, part of the LLVM project, built around
       reusable *dialects* -- self-contained sets of operations and types -- and
       progressive lowering between them. A machine learning model enters as a
       high-level dialect such as TOSA and is rewritten step by step down to
       something a backend can consume, which is what makes it the substrate for
       :term:`HLS` front ends like ``soda-opt``. See
       :ref:`the SODA tutorial <soda_tutorial>`.

    netlist
       A description of a circuit as instantiated components and the
       connections between them, as opposed to the behavioral description in
       :term:`RTL`.

    place-and-route
    P&R
    PnR
    PNR
       :term:`Placement` and :term:`routing` taken together, and normally run by
       a single tool, because the two decisions constrain each other: a
       placement is only a good one if what it implies can actually be routed.
       Abbreviated P&R, PnR or PNR interchangeably -- tool documentation is not
       consistent about which spelling it uses.

    placement
       Deciding where each cell in the :term:`netlist` physically sits: inside
       the :term:`floorplan` for an :term:`ASIC`, or on the fabric's fixed logic
       sites for an :term:`FPGA`. Runs after :term:`synthesis` and before
       :term:`routing`, and largely fixes the wire lengths every later step has
       to live with.

    routing
       Connecting placed cells -- drawing metal wires layer by layer within the
       :term:`PDK`'s spacing rules on an :term:`ASIC`, or configuring the
       fabric's prefabricated interconnect on an :term:`FPGA`. The last major
       implementation step; on an ASIC its output is what :term:`DRC` and
       :term:`LVS` check and what :term:`PEX` measures.

    RTL
       Register Transfer Level -- a description of hardware in terms of a
       clocked flow of data between registers, written in an :term:`HDL` such as
       :term:`Verilog`, :term:`VHDL`, or :term:`SystemVerilog`. The usual
       starting point of a compilation.

    SoC
       System on Chip -- a single chip carrying a whole system rather than one
       function: one or more processors, memory, and the peripherals and
       interconnect that tie them together. Built by integrating :term:`IP`,
       which is why an SoC :term:`design` typically depends on several
       :term:`libraries <library>` and instantiates
       :term:`hardened macros <hardened macro>` such as
       :term:`SRAMs <SRAM>`. See :ref:`Building an SoC <picorv32_example>`.

    SystemVerilog
       An extension of :term:`Verilog` adding stronger typing, interfaces,
       classes, and the constrained-random and :term:`assertion` constructs
       most verification is written in today. Accepted anywhere Verilog is,
       though tool support for the verification subset varies more than for
       the synthesizable one.

    synthesis
       Translating :term:`RTL` into a :term:`netlist` of concrete cells --
       :term:`standard cells <standard cell>` for an :term:`ASIC`,
       :term:`LUTs <LUT>` and hard blocks for an :term:`FPGA` -- while
       optimizing for area, timing and power. The point at which a design stops
       being technology-independent.

    Verilog
       The most widely used :term:`HDL`, and the lingua franca of the
       open-source tool flow: the language SiliconCompiler's built-in
       :term:`flows <flow>` assume unless told otherwise, and the output format
       most higher-level frontends generate. Extended by
       :term:`SystemVerilog`.

    VHDL
       An :term:`HDL` with a stricter type system than :term:`Verilog`, common
       in European and aerospace/defense design. Supported by SiliconCompiler
       where the underlying tool supports it -- fewer open-source tools do than
       for Verilog, so a VHDL design may need a different :term:`flow`.

ASIC design
-----------

.. glossary::

    ASIC
       Application-Specific Integrated Circuit -- a chip whose logic is fixed at
       manufacture. The counterpart to an :term:`FPGA`: far better area, power
       and speed, paid for with a months-long manufacturing cycle and a mask set
       that cannot be changed afterwards. An ASIC build is driven by the
       :class:`.ASIC` project class, which pairs a :term:`design` with a
       :term:`PDK` and a :term:`mainlib`.

    blackbox
       Telling a tool to treat a module as an opaque interface with no contents,
       so it is neither elaborated nor synthesized. This is how a
       :term:`hardened macro` is wired into a parent design: the parent sees
       only the ports, and the physical implementation comes from the macro's
       own views. See :ref:`Instantiating a hardened module <hardened_modules>`.

    clock tree synthesis
    CTS
       Building the buffered network that distributes a clock to every register,
       balancing arrival times so skew stays inside what :term:`STA` will
       accept. Runs between :term:`placement` and :term:`routing`.

    corner
       A named combination of process, voltage and temperature at which a design
       is analyzed. A cell that is fast in one corner is slow in another, so
       timing is checked in several -- typically a slow corner for setup and a
       fast one for hold. A :term:`library` ships one :term:`Liberty` file per
       corner.

    delay model
       How a :term:`Liberty` file expresses cell delay: ``nldm`` (lookup tables)
       or ``ccs`` (current source models -- slower to read, more accurate).
       A :term:`library` groups its timing :term:`filesets <fileset>` by
       ``(corner, delaymodel)`` and a :term:`target` selects one with
       ``set_asic_delaymodel()``. See
       :ref:`Timing models and the delay model <lib_delaymodel>`.

    DFM
       Design for Manufacturability -- layout changes that raise yield beyond
       what the :term:`DRC` rules strictly demand: extra spacing where there is
       room, redundant vias, fill for uniform metal density. Passing DRC says a
       layout is legal; DFM is about how many of the manufactured die work.

    DFT
       Design for Test -- logic added so manufactured parts can be tested: scan
       chains that stitch registers into a shift register, compression logic,
       and built-in self-test for memories. Costs area and some timing, and is
       what makes it possible to tell a good die from a bad one after
       :term:`tapeout`.

    DRC
       Design Rule Check -- verification that a layout obeys the geometric
       rules the foundry requires for manufacturability.

    floorplan
       The physical plan of a block before detailed implementation: die and core
       area, where :term:`macros <macro>` and I/O sit, and the power grid.
       Set through the project's area constraints, and settled early because
       :term:`placement` and :term:`routing` both have to work inside it.

    hardened macro
    hard macro
       A block that has been compiled all the way to a physical implementation
       and is reused as a fixed, pre-built component -- an abstract layout view
       plus timing models -- rather than being resynthesized with the parent.
       Hardening gives predictable timing and area at the cost of flexibility: a
       hardened macro is a concrete netlist and therefore has no parameters.
       See :ref:`Instantiating a hardened module <hardened_modules>`.

    LVS
       Layout Versus Schematic -- verification that the manufactured layout is
       electrically identical to the netlist it was built from.

    macro
       A block placed in the :term:`floorplan` as a unit rather than synthesized
       along with its parent -- an SRAM, a PLL, an analog block, or a
       :term:`hardened macro` of your own. Macros are placed before
       :term:`standard cells <standard cell>`, because everything else has to
       fit around them.

    PEX
       Parasitic Extraction -- computing the resistance and capacitance
       introduced by the physical wiring, so that timing analysis can account
       for real interconnect delay rather than estimates. Its output is a
       :term:`SPEF` file.

    scenario
       A named timing analysis condition: which library :term:`corner` to
       analyze at, which parasitic corner to use, and which checks (setup,
       hold) to run. A :term:`target` defines one or more with
       ``constraint.timing.make_scenario()``, and :term:`STA` runs against all
       of them.

    signoff
       The final verification pass a design must clear before :term:`tapeout` --
       :term:`DRC`, :term:`LVS`, :term:`STA` at every :term:`corner`, and
       whatever else the foundry demands -- run with signoff-quality tools and
       decks rather than the faster in-flow approximations. ``signoffflow`` is
       the built-in signoff :term:`flow`; see
       :ref:`Checklists <checklists>` for recording the results.

    slack
       How much time a path has to spare against its constraint: positive means
       it meets timing, negative means it misses by that much. :term:`STA`
       reports it as worst (WNS) and total (TNS) negative slack, recorded as
       :term:`metrics <metric>` such as ``setupwns`` and ``holdtns``.

    SRAM
       Static Random Access Memory -- on-chip memory built from a dense,
       specially drawn bit cell rather than from :term:`standard cells
       <standard cell>`. Too regular and too area-critical to synthesize, so an
       SRAM arrives as a :term:`hardened macro` from a memory compiler or the
       :term:`PDK` and is placed in the :term:`floorplan` as a
       :term:`macro`. See :ref:`Building an SoC with a memory <picorv32_example>`.

    stackup
       The set of metal layers a process offers for :term:`routing`, named by
       how many there are and how they are built -- ``"12M"`` for a twelve-metal
       stack. Set on the :term:`PDK` with ``set_stackup()``. Every
       :term:`library` used in a build has to be characterized for the same
       stackup, since the abstract views in :term:`LEF` are drawn on those
       layers.

    standard cell
       A pre-designed, pre-characterized logic gate or flip-flop with a fixed
       height, drawn from a standard cell :term:`library`. Synthesis maps a
       design onto these cells, and placement arranges them in rows.

    STA
       Static Timing Analysis -- verifying that a design meets its timing
       constraints by analyzing every path, without simulating any vectors.

    tapeout
       Sending the final layout database -- usually :term:`GDSII`, sometimes
       OASIS -- to the foundry, the point after which nothing can change
       without a new mask set. What :term:`signoff` and the
       :ref:`checklist <checklists>` machinery exist to gate.

    utilization
       How much of the core area the cells actually occupy, as a percentage --
       also called *density*, and set with ``constraint.area.set_density()``.
       The central floorplanning trade-off: pack too tightly and there is no
       room left to :term:`route <routing>`; leave too much slack and the die is larger
       and more expensive than it needs to be. Typical starting points are
       40--70%, lower for congested designs.

FPGA design
-----------

.. glossary::

    bitstream
       The configuration file loaded onto an :term:`FPGA` to make it behave as
       your design. It is the FPGA flow's final output, in the role
       :term:`GDSII` plays for an ASIC -- with the difference that you can
       produce one, load it, and change your mind, which is why FPGA builds are
       measured in minutes rather than months.

    FPGA
       Field-Programmable Gate Array -- a chip whose logic is configured after
       manufacture by loading a :term:`bitstream`, rather than fixed at tapeout.
       The compilation flow is the same shape as an ASIC's, but targets a
       specific device instead of a :term:`PDK`.

    LUT
       Look-Up Table -- the small programmable truth table that is an
       :term:`FPGA`'s basic logic element, in the role a :term:`standard cell`
       plays in an ASIC. FPGA resource reports are counted in LUTs, and a design
       "fits" when it needs no more than the device has.

Simulation and verification
---------------------------

.. glossary::

    assertion
       A property that must always hold, written alongside the design or in the
       :term:`testbench` -- typically in SystemVerilog Assertions (SVA).
       Checked continuously during simulation, and provable outright by
       :term:`formal verification`.

    formal verification
       Reasoning mathematically about a model of the design under stated
       assumptions, rather than exercising it with the stimulus a
       :term:`testbench` happens to apply. Covers bounded model checking (is
       this true for the first N cycles?), unbounded proof (is it true in every
       reachable state?) and equivalence checking such as :term:`LEC`.
       Complements simulation instead of replacing it: simulation finds the bugs
       you thought to look for, formal finds the ones you did not -- within
       whatever the assumptions and the bound allow.

    LEC
       Logical Equivalence Check -- formal proof that two representations of a
       design, typically the :term:`RTL` and a synthesized :term:`netlist`,
       implement identical logic. Catches the class of bug where an
       optimization silently changed behavior.

    lint
       Static analysis of :term:`RTL` for mistakes a compiler will accept but a
       designer did not intend -- width mismatches, undriven or unused signals,
       incomplete sensitivity lists. Needs no technology data and no EDA tool
       beyond the linter itself, which makes it the cheapest check to run first.
       ``lintflow`` is the built-in :term:`flow`.

    testbench
       Code that drives a design under simulation and checks what comes back.
       In SiliconCompiler it lives in its own :term:`fileset` beside the
       :term:`RTL`, so the same :term:`design` can carry several -- one per
       simulator, or one per scenario -- and a run selects among them.

    waveform
       The recorded history of every signal in a simulation, written as a
       :term:`VCD` or FST file and read in a viewer such as Surfer or GTKWave.

File formats
------------

.. glossary::

    DEF
       Design Exchange Format -- a text format describing the physical
       implementation of a design: component placement, routing, and pin
       locations. Paired with :term:`LEF`, which describes the cells being
       placed.

    GDSII
    GDS
       The standard binary layout format, and the usual final output of an ASIC
       flow: the file sent to the foundry for manufacturing.
       (OASIS is a more modern alternative with the same role.)

    LEF
       Library Exchange Format -- a text format describing the abstract physical
       view of cells and macros: outline, pin positions, and blockages, without
       the full internal layout. Enough for a placer and router to work with.

    Liberty
       The ``.lib`` timing and power format for a :term:`standard cell`
       :term:`library`: per-cell delay, transition, setup/hold and power tables,
       characterized for one :term:`corner` and one :term:`delay model`. What
       :term:`synthesis` and :term:`STA` read to know how fast a cell is.

    SDC
       Synopsys Design Constraints -- the de facto standard format for
       specifying timing constraints: clock definitions, I/O delays, and
       exceptions.

    SDF
       Standard Delay Format -- per-instance delays written out after
       implementation and back-annotated onto a gate-level simulation, so the
       simulator models real timing instead of unit delays. The bridge between
       :term:`STA` and simulation-based timing verification.

    SPEF
       Standard Parasitic Exchange Format -- the text format carrying the
       resistance and capacitance values :term:`PEX` extracts, read back by
       :term:`STA` so timing reflects real interconnect. See
       :ref:`pex_calibration` for calibrating a pre-route estimate against a
       golden SPEF.

    VCD
       Value Change Dump -- the standard waveform format, a record of every
       signal transition in a simulation. Useful twice: for looking at what the
       design did, and as switching activity for power analysis, which is far
       more accurate than the default assumptions.
