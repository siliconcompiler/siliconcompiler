ASIC design primer
===========================

Modern ASIC/SoC contain billions of switches embededed within a single device. The
combinatorics of designing and verifying such a device makes the construction
process inherently complex. In chip design, anything less than perfection operation
is considered a failure. There is no recompile option.

The complexity challenge of modern silicon machines is pervasive with significant
effort going into system desigbn, applications, O/S, tools, drivers, architecture,
design, design verification, physical design, testing, and productization.
If we really want to make a difference and reduce the cost and time of chip design
by orders of magnitude (100x), the industry will need to address all inefficiencies
in the process not just the major ones. (see Amdahl's Law).

The specific challenge area addressed by the SiliconCompiler project is automated
hardware compilation (ie. the concept of taking a high level description and
lowering it to some final low level form). In modern chip design, this is actually
an incredibly complex endeavor due to the enormous search space associated with
implementation commands and numerical parameters to specify to achieve correct and
optimal implementation. Selection of each one of the parameters and recipes
requires access to state of the art EDA tools and expert knowledge of tools, foundry
PDKs and physical design methodologies. The number of physical design concerns has
been steadily increasing with every CMOS process node advancement, starting at
180nm. To qualify production level silicon solutions at 22nm and below requires
sophisticated implementation and verification flows with expertise needed in:

* static timing analysis
* design for testability
* RC delay effects
* clock tree optimization
* power integrity and power delivery
* signal integrity
* multi-threshold low power synthesis
* power gating
* multi-voltage domains
* Advanced ESD and antenna design rules
* congestion avoidance
* self heating
* on chip variability
* statistical yield analysis
* multic-corner multi-mode analysis
* stress and proximity effects
* complex patterning density rules
* design for manufacturability
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
