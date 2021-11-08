Introduction
===================================

SiliconCompiler Overview
------------------------

SiliconCompiler ("SC") is a open source compiler infrastructure project that
aims to lower the barrier to hardware specialization through a simple
distributed programming model and standardized tool configurations.

Fundamental challenges to an open and agile hardware compilation system
include:

1. The N-squared translation problem.
2. Low productivity of physical design flow development.
3. Long compile cycles (limited by `Amdahl's law. <https://en.wikipedia.org/wiki/Amdahl%27s_law>`_).
4. NDA restrictions blocking feedback loop (see `Network Effect <https://en.wikipedia.org/wiki/Network_effect>`_).


The N-squared translation problem is a well known challenge involving
communication between N sources and N destinations, each speaking separate
languages. A brute force implementation for all to all communication would
require N^2 separate translators from all sources to all destinations. A more
efficient efficient solution relies on constructing an intermediate
representation "IR" that enables all sources to be translated to all
destinations using N source to IR translators and 2 IR to destination
translators. The IR approach has served as the guiding principle for a number
of successful software projects, including `LLVM <https://llvm.org/>`_ and
`Pandoc <chttps://pandoc.org/>`_.

Ideally, it should be possible to compile a hardware design for a specific
PDK the same way it's possible to compile a software program for a specific
architecture:

.. code-block:: bash

    $ clang --target=aarch64-linux-gnu hello.c -o hello

Modern hardware compilation involves translating 1000's of designs to
10's of PDKs using 10's of individual tool executables, resulting in 1000's of
separate configurations and translators and high per design efforts.

.. image:: _images/challenge_nsquared.png

Our software inspired IR approach relies on a single plain text :ref:`Schema`
nested dictionary for tracking all design, tool, and PDK related information
transforming the O(N^2) complexity translation problem to an O(N)
problem..

.. image:: _images/siliconcompiler_ir.png

The second challenge addressed by the SiliconCompiler project is
the low productivity of physical design flow development.  The vast
majority of ASIC and FPGA tools are still programmed using proprietary
TCl based APIs. For large commercial organizations with dedicated in
house CAD teams and TCL experts, this is a workable system as demonstrated
by the thousands of silicon miracles taped out every year, but for
smaller teams and students new to the field, the current situation
leaves much to be desired.

Fortunately, there is no theoretical barrier standing in the way of
creating a hardware compilation community similar to the thriving
communities seen in LLVM and machine learning. The Python language
has millions of developers world wide and over 335,000 packages on
PyPi, so for us it was the obvious platform of choice for a compilation
framework built to serve a diverse set of users and tools.

The SiliconCompiler programming model is based on a simple and open
Python :ref:`core API` model where compilation parameters are set up
by the user and arbitrary static compilation passes are executed by
a SiliconCompiler runtime.

.. literalinclude:: examples/heartbeat.py

The SiliconCompiler :ref:`core API` interfaces with the :ref:`Schema`,
decoupling the user from the tool configurations and PDKs, and paving
the way for extensive derivative package development and knowledge
sharing using `Python package manager <https://pypi.org>`_. We are
hopeful to one day see foundry PDK setup files and EDA tool
configuration files being shared in a manner similar to how Python
and JavaScript packages are shared today through PyPI and npm.

.. image:: ../_images/sc_stack.svg

To address the long compilation times of physical design steps, an
abstracted asynchronous flowgraph programming model was developed that
enables transparent execution on local machines or in warehouse scale
data centers.

.. literalinclude:: examples/pattern_forkjoin.py

.. image:: _images/pattern_forkjoin.png


To solve the challenge of restrictive NDAs prevalent in the semiconductor
industry, SiliconCompiler has been designed from ground up for cloud and
client/server execution. The architecture allows proprietary PDKs
to be decoupled from the designer as much as possible using intermediate
proxies and information fire walling. By definition, a compilation cycle
must feed back some information to the programmer (at least 1
bit) to be useful, but through use of a intermediate proxy, the feedback
can be carefully controlled.

.. image:: _images/siliconcompiler_proxy.png


Project philosophy
-------------------

* Modern hardware compilation is a high performance computing (HPC) problem and
  compilation must make optimal use of the underlying computing platform whether
  we run on a laptop, powerful, workstation, or in a warehouse scale data center.
* Computing platform details should be abstracted from the user.
* Adoption is maximized by prioritizing developer community size (Python).
* Adoption is maximized by serving all client platforms (Windows, macOS, Linux).
* Accept things we cannot change. Legacy tools with TCL interfaces will not
  (should not) be converted to Python. Leading edge tools and PDKs will remain
  closed source and proprietary for the foreseeable future.
* Use standardized ASCII text file formats for data exchange whenever possible.
  (JSON, YAML, DEF, Verilog).
* Build generators, not instances. (sw, hw, docs,...)
* Design for the lowest common denominator. Some brilliant EEs are terrible
  programmers and some brilliant programmers are bad engineers.
  Tools and frameworks should lower the bar for all. Create enough
  abstraction layers to serve the novice user and expert user effectively.

Features
-------------------

.. list-table::
   :widths: 20 15 15 20
   :header-rows: 1

   * - Feature
     - SiliconCompiler
     - Status Quo
     - Why it's important
   * - User API interface
     - Python
     - TCL
     - Python is 1000x more popular
   * - Open API
     - Yes
     - No
     - Network effect
   * - PDK agnostic APR setup
     - Yes
     - No
     - Startup time
   * - Library agnostic setup
     - Yes
     - Not usually
     - Startup time
   * - Common ASIC/FPGA design API
     - Yes
     - No
     - Startup time
   * - Remote processing
     - Yes
     - No
     - Startup time
   * - Provenance tracking
     - Automated
     - Manual
     - Security, quality
   * - Single file manifest/record
     - Yes
     - No
     - Security, quality
   * - Tapeout archiving
     - Automated
     - Manual
     - Security, quality


Historical perspective
------------------------

The term "Silicon Compiler" dates back to the first VLSI revolution in the late
1970's. The term was initially defined as a software system that that reads a high
level specification and translates it into a complete layout of an integrated
circuit (IC). The initial idea behind early Silicon Compilers was one where chips
would be specified as a series of parameterized building blocks and the silicon
compiler would automatically stitch them together to create the final set of
photomasks containing all the layers needed to create transistors and interconnect.

The initial silicon compilers had a compelling vision, but were not fully automated
and proved too limited for the rapidly evolving VLSI community. Instead, the
methodology that won was based on standardized high level hardware description
language (Verilog/VHDL) and a standard library based abstraction where the design is
automatically translated/lowered to a physical layout using a series of automated
transformations (synthesis --> placement --> cts--> routing- -> dfm-->etc) and a
standard cell lib This “RTL to GDS” silicon compiler approach was rarely 100%
automated, but it was good enough for the industry for over 30 years. Still,
significant issues remain:

* Silicon compilation technology is too expensive ('not free as in beer')
* Silicon compilation is not fully automated
* Silicon compilation is not PDK agnostic
* Silicon design abstractions are now leaking

Moore's law as we know it is ending and the only way we can continue to advance the
state of the art in performance, cost, and energy efficiency in the future is
through extreme circuit specialization. Unfortunately, this post-Moore
era vision will never materialize at the current chip design costs which range from
$50-500M at advanced manufacturing nodes.

.. image:: ../_images/cost.png

Observing the positive impact that silicon and Moore's Law on the world over the
last 50 years it is a social imperative that we extend the current exponential
trend for as long possible. The time for a 2nd VLSI revolution has arrived!
