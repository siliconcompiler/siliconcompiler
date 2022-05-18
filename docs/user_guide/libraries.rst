Libraries
=========

Efficient hardware and software development demands a robust eco-system of reusable high quality components. In SiliconCompiler, IP can be reused by importing a Chip configuration dictionary into a parent Chip object under the 'library' schema.

The general flow to create and import a library is to instantiate a library :class:`.Chip` object, set up any required sources (in the case of a soft library), or models and outputs (in case of a hardened library), and then import it into a parent design :class:`.Chip` object. To select which standard cell libraries to use during compilation, add their names to the :keypath:`asic, logiclib` parameter, and to select macro libraries, add their names to the :keypath:`asic, macrolib` parameter.
Here's an example of setting up and importing a library object::

  lib = siliconcompiler.Chip('mylibrary')
  lib.add('model', 'layout', 'lef', 'mylibrary.lef')
  # ... add more library sources

  chip = siliconcompiler.Chip('mydesign')
  chip.add('input', 'verilog', 'mydesign.v')
  chip.import_library(lib)
  chip.add('macrolib', 'mylibrary')
  # ... perform more build configuration

  run()

The same approach is used to configure standard cell libraries, which are primarily defined using :keypath:`model` settings. In leading edge process nodes, it's not uncommon to have 10's to 100's of STA signoff corners, with each corner consuming gigabytes of disk space. The SiliconCompiler schema is designed to enable efficient setup of all library file pointers and to allow designers to easily select which libraries and which corners to use in any single run. The run time selection of corners, libraries, and timing enables an agile approach to design, wherein the designer can choose the level of accuracy and performance based on need. For example, early in the architecture exploration phase, speed matters and the right choice for synthesis may be to compile using a single stdcell library, using a NLDM model, at a single timing corner. As the design is fine tuned, and the team closes in on tapeout of a mass produced device, the compilation and signoff verification may use many VT libraries, CCS timing models, and hundreds of timing scenarios. Being able to make these trade-offs with a unified library setup and a couple of lines of designer Python settings, greatly reduces physical design speed and risk.

The following code snippet shows how library gds and lef files can be set up in the SC schema::

    lib.add('model','layout','lef','$FREEPDK45/lef/NangateOpenCellLibrary.lef')
    lib.add('model','layout','gds','$FREEPDK45/gds/NangateOpenCellLibrary.gds')

SiliconCompiler also supports referencing soft libraries (RTL, C-code, etc), in which case many of the physical IP parameters can be omitted.

Library Modules
----------------
To enable simple 'target' based access, it is recommended that fundamental physical foundry sponsored IP (stdcells, GPIO, memory macros) are set up as part of reusable library modules.

Similarly to :ref:`PDKs<PDKs>`, library modules must implement the following functions.

.. list-table::
   :widths: 10 10 10 10 10 10
   :header-rows: 1

   * - Function
     - Description
     - Arg
     - Returns
     - Used by
     - Required

   * - **setup**
     - Library setup function
     - chip
     - chip
     - :meth:`.load_lib()`
     - yes

   * - **make_docs**
     - Doc generator
     - None
     - chip
     - sphinx
     - yes

A complete set of supported standard cell libraries for SC's included open PDKs can be found in the :ref:`Libraries Directory`.