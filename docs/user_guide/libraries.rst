Libraries
=========

Efficient hardware and software development demands a robust eco-system of reusable high quality components. In SiliconCompiler, soft modules and physically hardened IP can be included in a design through the 'library' group of the schema.

The 'library' dictionary is general enough to serve as a central record for any module instantiated within a design. The library management philosophy is "write once, read often". All corners, all files, and all tools are set up once and then referenced by the designer on a per design basis.

In leading edge process nodes, it's not uncommon to have 10's to 100's of STA signoff corners, with each corner consuming gigabytes of disk space. The SiliconCompiler schema is designed to enable efficient setup of all library file pointers and to allow designers to easily select which libraries and which corners to use in any single run. The run time selection of corners, libraries, and timing enables an agile approach to design, wherein the designer can choose the level of accuracy and performance based on need. For example, early in the architecture exploration phase, speed matters and the right choice for synthesis may be to compile using a single stdcell library, using a NLDM model, at a single timing corner. As the design is fine tuned, and the team closes in on tapeout of a mass produced device, the compilation and signoff verification may use many VT libraries, CCS timing models, and hundreds of timing scenarios. Being able to make these trade-offs with a unified library setup and a couple of lines of designer Python settings, greatly reduces physical design speed and risk.

The following code snippet shows how library gds and lef files can be set up in the SC schema::

    chip.add('library','NangateOpenCellLibrary','lef','$FREEPDK45/lef/NangateOpenCellLibrary.lef')
    chip.add('library','NangateOpenCellLibrary','gds','$FREEPDK45/gds/NangateOpenCellLibrary.gds')

To enable simple 'target' based access, it is recommended that fundamental physical foundry sponsored IP (stdcells, GPIO, memory macros) are set up as part of the setup_pdk function.

SiliconCompiler also supports referencing soft libraroes (RTL, C-code, etc), in which case many of the physical IP parameters can be omitted.
