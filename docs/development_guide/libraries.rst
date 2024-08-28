Libraries
=========

Efficient hardware and software development demands a robust ecosystem of reusable high quality components. In SiliconCompiler, you can add new IP to your design by creating a :class:`siliconcompiler.Library` object which can be passed into the :meth:`.use()` function. The :class:`siliconcompiler.Library` class contains its own Schema dictionary, which can describe a macro block or standard cell library.

The general flow to create and import a library is to instantiate a :class:`siliconcompiler.Library` object, set up any required sources (in the case of a soft library), or models and outputs (in case of a hardened library), and then import it into a parent design :class:`siliconcompiler.Chip` object.

To select which standard cell libraries to use during compilation, add their names to the :keypath:`asic, logiclib` parameter, and to select macro libraries, add their names to the :keypath:`asic, macrolib` parameter.

Here's an example of setting up and importing a macro block as a :class:`siliconcompiler.Library` object::

  chip = siliconcompiler.Chip('mydesign')
  chip.add('input', 'verilog', 'mydesign.v')

  lib = siliconcompiler.Library('mymacro')
  lib.add('output', stackup, 'lef', 'mymacro.lef')
  lib.add('output', stackup, 'gds', 'mymacro.gds')
  # ... add more library sources

  chip.use(lib)
  chip.add('asic', 'macrolib', 'mymacro')
  chip.set('constraint', 'component', 'macro_instance1', 'placement', (20.0, 20.0, 0.0))
  chip.set('constraint', 'component', 'macro_instance2', 'placement', (40.0, 20.0, 0.0))
  chip.set('constraint', 'component', 'macro_instance2', 'rotation', 180)
  # ... perform more build configuration

  chip.run()

This example assumes that the theoretical `mydesign.v` file contains at least two instances of a block named `mymacro`, named `macro_instance1` and `macro_instance2`. The physical design flow will be able to find the library's LEF and GDS files during the build process, and the macro placements for the named instances will be fixed.

The same approach is used to configure standard cell libraries, which are primarily defined using :keypath:`output` settings. In leading edge process nodes, it's not uncommon to have 10's to 100's of STA signoff corners, with each corner consuming gigabytes of disk space. The SiliconCompiler schema is designed to enable efficient setup of all library file pointers and to allow designers to easily select which libraries and which corners to use in any single run. The run time selection of corners, libraries, and timing enables an agile approach to design, wherein the designer can choose the level of accuracy and performance based on need. For example, early in the architecture exploration phase, speed matters and the right choice for synthesis may be to compile using a single stdcell library, using a NLDM model, at a single timing corner. As the design is fine tuned, and the team closes in on tapeout of a mass produced device, the compilation and signoff verification may use many Vt libraries, CCS timing models, and hundreds of timing scenarios. Being able to make these trade-offs with a unified library setup and a couple of lines of designer Python settings, greatly reduces physical design speed and risk.

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
     - Args
     - Returns
     - Used by
     - Required

   * - **setup**
     - Library setup function
     - :class:`.Chip`
     - :class:`siliconcompiler.Library`
     - :meth:`.use()`
     - yes

   * - **make_docs**
     - Doc generator
     - :class:`.Chip`
     - :class:`siliconcompiler.Library`
     - sphinx
     - no

A complete set of supported standard cell libraries for SC's included open PDKs can be found in the `libraries <libraries>`.
