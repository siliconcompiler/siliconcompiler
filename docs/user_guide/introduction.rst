Introduction
===================================

SiliconCompiler (SC") is an end-to-end Python based open source platform for
hardware compilation. It supports a comprehensive, flexible ecosystem of
tools, hardware targets, and community resources that lowers the barrier to physical ASIC prototyping and high accuracy HW/SW codesign. 

Highlights
----------------
* Configurable, extensible, and automated ASIC and FPGA compilation flows
* Easy to use Python based interface
* Command line application with full configuration access
* Plain text single file JSON compilation record
* Zero-install client/server execution model
* Simple name based target technology mapping
* Python based technology agnostic ASIC floor-planning API  

.. list-table::
   :widths: 20 15 15 20
   :header-rows: 1
		 
   * - Feature
     - SiliconCompiler
     - Previous
     - Value Proposition
   * - User API interface
     - Python
     - TCL
     - Python 1000x more popular
   * - Open Command API
     - Yes
     - No
     - Workforce development
   * - PDK agnostic APR setup 
     - Yes
     - No
     - Porting costs
   * - Library agnostic setup
     - Yes
     - Not usually
     - Porting costs
   * - Unified ASIC/FPGA API
     - Yes
     - No
     - Porting costs
   * - Unified DV/APR sourcelist
     - Yes
     - No
     - Security, quality
   * - Client/server architecture
     - Yes
     - No
     - On-ramp friction
   * - Cloud scale automation
     - Python
     - Proprietary
     - Portable infrastructure
   * - Single line app support
     - Yes
     - No
     - On-ramp friction
   * - Provenance tracking
     - Automated
     - Manual
     - Security, quality
   * - Single file manifest/record
     - Yes
     - No
     - Security, quality
   * - Automated Tapeout archiving
     - Automated
     - Manual
     - Security, quality
 
       
History
----------------

A silicon compiler is a piece of software that reads a high level specification
and automatically translates it into a complete layout of an integrated circuit
(IC). The term was coined in 1979 at a conference at Caltech at the height of
the 1st VLSI revolution led by Carver Mead and Lynn Conway. Mead and Conway
created abstractions and design methodologies that enabled a community of
engineers without a background in solid state device physics to design
circuits. 


The initial idea behind the early “silicon compilers” was one where chips
would be specified as a series of parameterized building blocks and the
silicon compiler would automatically stitch them together to create the final
set of photmasks containing all the layers needed to create transistors and
interconnect. In today’s terminology, we would probably call these early
"silicon compilers" by a different name: generators. The initial silicon
compilers had a compelling vision, but were not fully automated and proved too
limited for the rapidly evolving VLSI community. For the industry, what
eventually won out was a new kind of silicon compiler where a standardized high
level hardware description language (Verilog/VHDL) is automatically translated
to a physical layout using a series of automated transformations
(synthesis-->placement-->cts-->routing-->dfm-->...)

This new “RTL to GDS” silicon compiler approach has been used in every
System-On-Chip designed in the last 20 years, but challenges remain:

* Silicon compilation technology is inaccessible for most
* Silicon compilation is still not fully automated
* Silicon compilation is still not PDK agnostic
* Silicon design abstractions are leaking PDK data


Challenges
----------------

One of the main challenges with current EDA physical design tools come from the
enormous search space associated with implementation commands and numerical
parameters  to specify to achieve correct and optimal implementation of SoCs
in SOTA nodes. Selection of each one of the parameters and recipes requires
intimate knowledge of the EDA tools, foundry constraints and rules, physical
design methodologies.

Physical implementation of complex SoCs at SOTA process nodes is a daunting
engineering undertaking with expertise needed across a broad set of domains.
The number of physical design concerns has been steadily increasing with every
CMOS process node advancement, starting at 180nm. To qualify production level
silicon solutions at 22nm and below requires sophisticated implementation and
verification flows with expertise needed in:

* static timing analysis
* congestion avoidance
* power delivery and power integrity analysis
* wire delay effects
* self heating
* on chip variability
* statistical yield analysis
* multic-corner multi-mode analysis
* signal integrity
* stress and proximity effects
* design for testability
* electrostatic discharnge design rules
* complex patterning density rules
* multi-voltage domains
* power gating
* multi-threshold low power synthesis
* design for manufacturability
* antenna rules
* double and triple pattern lithography considerations
* current density limitations
* advanced packaging
* reliability and device fatique

To address the ever expanding set of physical design concerns, EDA companies
are continuously adding new tool features and automation capabilities to
commercial physical design tools. Despite these efforts, design
automation progress has not kept pace with the exponential rate of Moore’s Law
(2x more transistors per chip every 2 years), resulting in a productivity gap
that has made physical design of complex SoCs in SOTA process nodes impractical
for small design teams.

Large semiconductor companies with many design groups and numerous products
and prototypes in the pipeline minimize EDA, IP, and PDK project startup costs
through establishment of internal CAD teams that provide infrastructure and
enablement for all of the company’s product design teams. The key services
provided by internal CAD teams generally include:

* Setup and management of large on-premises and cloud based server farms
* EDA and IP procurement for the company
* EDA and IP license management for the company
* Installation of EDA tools, foundry PDKs, and foundational physical IP
* Version tracking and archiving of all versions of EDA, IP, PDKs
* Design/tapeout archiving
* Establishment of qualified reference physical design flows for the company
* Direct interfacing with EDA, IP, and foundry suppliers
* Reference flow support of internal design teams

**The SiliconCompiler project aims to provides open source design enablement
infrastucture to enable anyone to design SoCs without the benefit of a large
internal CAD team**

Architecture
-------------

The SiliconCompiler relies on a central unified python dictionary (“schema”)
that tracks all files and accesses and actions taken from RTL to GDS. During
design execution, the schema is dynamically accessed by translation scripts at
runtime to generate configuration files for each EDA tool accessed. Metrics are
collected at each design step and fed back into the centralized dictionary
maintained by the Python management program. JSON files are written to disk
after each step for verification purposes. Most importantly, a single
automatically generated unified JSON manifest can be coupled to every GDS sent
to foundry to ensure provenance and traceability.

The configuration schema is accessed through a Python API that enables a safe
and secure interface to the configuration schema and manages the silicon
compilation pipeline.

The SiliconCompiler project is based on a number of key design decisions:

* Leverage the incredible open source Python ecosystem to reduce cost and risk
  of the development.
* Leverage powerful nested structures in the Python language to create data
  structures that mimic the natural PDK and IP patterns for setup that enables
  independent setup on a per IP and per process basis. Maximum efficiency is
  reached when each setup owner can work independently and the designer can
  simply point to the resources to be used (library, EDA tool, process).
* Create a set of known good targets that hard code appropriate defaults for
  all configuration parameters within the compiler for an easy out of the box
  experience, with the ability to override each parameter dynamically at run
  time.
* Leverage the looping and control features of the Python language to enable
  single file configuration (“manifest”) of a process node PDK and/or IP
  library.
* Use YAML/TCL/JSON configuration writers to interfaces with external tools.
* A single golden trackable configuration manifest that keeps a complete record
  and hashes of all files and tool versions and configurations used to produce
  the GDSII.
* Don’t fight the tools or the foundries. SC will conform to existing
  interfaces provided if available (TCL/YAML). When non-existent, as in the
  case of PDKs and IP libraries, SC native setup files will be created with
  translators to EDA reference methodologies
* Build generators not instances. The architecture schema is built to enable
  auto-generation of command line options and API access, enabling SC to
  scale gracefully from a single command line argument all the way up to the
  most complicated SoCs within a single platform without burdening the novice
  with steep ramp up costs or restricting advanced developers.
