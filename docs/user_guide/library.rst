Library management
===================================

A core need for efficient hardware and software development is a robust eco-system of reusable high quality components. In SiliconCompiler, soft modules and physically hardened IP can be included in a design through the 'library' group of the schema.

The 'library' dictionary is general enough to serves as central record for any module instantiated within a design. The SC library management philosophy is "write once, read often". All corners, all files, and all tools are set up once and then referenced by the designer on a per design basis.

In leading edge process nodes, it's not uncommon to have 10's to 100's of STA signoff corners, with each corner consuming gigabytes of disk space. The SiliconCompiler schema is designed to enable efficient setup of all library file pointers and to allow designers to easily select which libraries and which corners to use in any single run. The run time selection of corners, libraries, and timing enables an agile approach to design, wherein the designer can choose the level of accuracy and performance based on need. For example, early in the architecture explopration phase, speed matters and the right chice for synthesis may be to compile using a single stdcell library, using a NLDM model, at a single timing corner. As the design is fine tuned, and the team closes in on tapeout of a mass produced device, the compilation and signoff verification may use many VT libraries, CCS timing models, and hudnredes of timing scenarios. Being able to make these tradeoffs with a unified library setup and a couple of lines of designer Python settings, greatly reduces physical design speed and risk.

The 'library' dictionary is grouped by name and include parameters for the following files and properties:

  * library type (soft/hard)
  * source file list
  * testbench file list
  * library dependency (fir hierarchincal design/packing)
  * process pdk requirement
  * metal stackup requirement
  * version number
  * place of origin
  * license file
  * document file list
  * datasheet file list
  * standard cell architecture/type
  * nldm timing model file list
  * ccs timing model file list
  * scm timing model file list
  * aocv timing model file list
  * lef file list
  * gds file list
  * netlist file list
  * spice file list
  * hdl file list
  * atpg file list
  * pgmetal layer
  * library tag/label
  * default drive cell
  * site name
  * binary layoutdb (per vendor)
  * cell definions (ignore, tie1/tie0, etc)


The following code snippet shows how library gds and lef files can be set up in the SC schema::

    chip.add('library','NangateOpenCellLibrary','lef','$FREEPDK45/lef/NangateOpenCellLibrary.lef')
    chip.add('library','NangateOpenCellLibrary','gds','$FREEPDK45/gds/NangateOpenCellLibrary.gds')

To enable simple 'target' based access, it is reocommened that fundemental physical foundry sponsored IP (stdcells, GPIO, memory macros) are bundled together as part of a single PDK target.

See the freepdk45 setup file for a complete example: `verilator.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/foundries/freepdk45.py>`_

See the schema manual for a full description of all ‘library’ parameters supported by the SC schema.
