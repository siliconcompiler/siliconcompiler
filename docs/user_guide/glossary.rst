.. _glossary:

Glossary
===================================

The following set of terms represents fundamental SiliconCompiler definitions used throughout the documentation.

SiliconCompiler concepts
------------------------

.. glossary::

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

    flowgraph node
       A single executable unit of a :term:`flowgraph`, identified by a
       (:term:`step`, :term:`index`) pair. Each node runs one :term:`task` with
       one :term:`tool`, in its own directory under the job directory.
       Not to be confused with the schema parameter field also called
       :term:`node`.

    hardened macro
       A block that has been compiled all the way to a physical implementation
       and is reused as a fixed, pre-built component -- an abstract layout view
       plus timing models -- rather than being resynthesized with the parent.
       Hardening gives predictable timing and area at the cost of flexibility: a
       hardened macro is a concrete netlist and therefore has no parameters.
       See :ref:`Instantiating a hardened module <hardened_modules>`.

    library
       A reusable collection of design data added to a project as a dependency.
       A standard cell :term:`library` (:class:`.StdCellLibrary`) supplies the
       logic gates a synthesis tool maps to; other libraries package IP, SRAMs,
       or I/O cells. Libraries are described with the same
       :term:`filesets <fileset>` and :term:`dataroots <dataroot>` as a
       :term:`design`.

    mainlib
       The primary standard cell :term:`library` for an ASIC build, set with
       ``set_mainlib()``. Additional libraries added with ``add_asiclib()``
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

Hardware design vocabulary
--------------------------

These terms are standard in the semiconductor industry rather than specific to
SiliconCompiler, but they appear throughout the documentation and in tool
output.

.. glossary::

    bitstream
       The configuration file loaded onto an :term:`FPGA` to make it behave as
       your design. It is the FPGA flow's final output, in the role
       :term:`GDSII` plays for an ASIC -- with the difference that you can
       produce one, load it, and change your mind, which is why FPGA builds are
       measured in minutes rather than months.

    DEF
       Design Exchange Format -- a text format describing the physical
       implementation of a design: component placement, routing, and pin
       locations. Paired with :term:`LEF`, which describes the cells being
       placed.

    DRC
       Design Rule Check -- verification that a layout obeys the geometric
       rules the foundry requires for manufacturability.

    formal verification
       Reasoning mathematically about a model of the design under stated
       assumptions, rather than exercising it with the stimulus a
       :term:`testbench` happens to apply. Covers bounded model checking (is
       this true for the first N cycles?), unbounded proof (is it true in every
       reachable state?) and equivalence checking such as :term:`LEC`.
       Complements simulation instead of replacing it: simulation finds the bugs
       you thought to look for, formal finds the ones you did not -- within
       whatever the assumptions and the bound allow.

    FPGA
       Field-Programmable Gate Array -- a chip whose logic is configured after
       manufacture by loading a :term:`bitstream`, rather than fixed at tapeout.
       The compilation flow is the same shape as an ASIC's, but targets a
       specific device instead of a :term:`PDK`.

    GDSII
       The standard binary layout format, and the usual final output of an ASIC
       flow: the file sent to the foundry for manufacturing.
       (OASIS is a more modern alternative with the same role.)

    LUT
       Look-Up Table -- the small programmable truth table that is an
       :term:`FPGA`'s basic logic element, in the role a :term:`standard cell`
       plays in an ASIC. FPGA resource reports are counted in LUTs, and a design
       "fits" when it needs no more than the device has.

    LEC
       Logical Equivalence Check -- formal proof that two representations of a
       design, typically the :term:`RTL` and a synthesized :term:`netlist`,
       implement identical logic. Catches the class of bug where an
       optimization silently changed behavior.

    LEF
       Library Exchange Format -- a text format describing the abstract physical
       view of cells and macros: outline, pin positions, and blockages, without
       the full internal layout. Enough for a placer and router to work with.

    LVS
       Layout Versus Schematic -- verification that the manufactured layout is
       electrically identical to the netlist it was built from.

    netlist
       A description of a circuit as instantiated components and the
       connections between them, as opposed to the behavioral description in
       :term:`RTL`.

    PEX
       Parasitic Extraction -- computing the resistance and capacitance
       introduced by the physical wiring, so that timing analysis can account
       for real interconnect delay rather than estimates.

    RTL
       Register Transfer Level -- a description of hardware in terms of a
       clocked flow of data between registers, written in a language such as 
       Verilog, VHDL, or SystemVerilog. The usual starting point of a compilation.

    SDC
       Synopsys Design Constraints -- the de facto standard format for
       specifying timing constraints: clock definitions, I/O delays, and
       exceptions.

    standard cell
       A pre-designed, pre-characterized logic gate or flip-flop with a fixed
       height, drawn from a standard cell :term:`library`. Synthesis maps a
       design onto these cells, and placement arranges them in rows.

    STA
       Static Timing Analysis -- verifying that a design meets its timing
       constraints by analyzing every path, without simulating any vectors.

    testbench
       Code that drives a design under simulation and checks what comes back.
       In SiliconCompiler it lives in its own :term:`fileset` beside the
       :term:`RTL`, so the same :term:`design` can carry several -- one per
       simulator, or one per scenario -- and a run selects among them.

    VCD
       Value Change Dump -- the standard waveform format, a record of every
       signal transition in a simulation. Useful twice: for looking at what the
       design did, and as switching activity for power analysis, which is far
       more accurate than the default assumptions.
