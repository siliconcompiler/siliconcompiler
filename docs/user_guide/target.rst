Compiler targets
===================================

Every parameter in the SiliconCompiler schema is directly accessible through the
core API, but given the large number of parameters needed to set up a complex PDK
and flow, the startup barrier can be imposing for new users. To faciliate grouping
and encapsulation of schema parameters, SC implements a target() function that
operates on string based names similar to `LLVM <https://clang.llvm.org/docs/CrossCompilation.html>`_.

The SC target() function searches the 'scpath' parameter for Python modules based on a
target string using underscore ('_') as a target delimeter. The order of search for target
loading is:

  1. Installation path of the SiliconCompiler Python package
  2. Current working directory at start of compilation
  3. Parameter 'scpath' list provided by user

Different types of setup targets are located based in searching for the
following setup modules using the above search order.

  * flows/<flowname>.py
  * pdks/<pdkname>.py
  * projects/<projectname>.py
  * tools/<toolname>/<toolname>.py

The tool modules are used called in the run()function and required for all
compilations, while PDKs, projects, and flows used solely by the target()
function.

To enable automated document generation, all target modules must include
a function called make_docs(). The make_docs module should create a chip
instance and call the appropriate setup function. The resulting
manifest can the be leverage to auto-generate manuaslf for the target::

  def make_docs():
     '''
     A one line desription of the model

     A paragraph of module content description
     '''

     chip = siliconcompiler.Chip()
     setup_flow(chip)

     return chip

The purpose of the project, pdk, and flow modules are different and
somewhat orthogonal and have different setup function names. The
code snippets below outline the type of functionality that would
typically go into each module.

**flow**


**pdk**

Process design kits (PDKs) for leading process nodes are shipped with hundreds of
files, documents, and configuration parameters, resulting in significant startup
times in porting a design to a new node. SC aims to minimize the design and EDA
porting effort by standardizing the parameters associated with PDK setup.

The standardized SC 'pdk' parameters form a data exchange contract between the foundry, eda developers, and designers, simplifying the process of creating a PDK agnostic
compilation flow.


* Foundries set PDK parameters based on the the SC standard schema
* Designers and EDA developers read PDK parameters based on the standard SC schema

PDk parameters are grouped within the 'pdk' schema dictionary and include the
following major sub-groups.

  * **models**: Device models and wire models for simulation
  * **rules**: Design rules for custom design
  * **apr**: Setup rules for automated place and route tools

Full freepdk45 setup: `verilator.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/foundries/freepdk45.py>`_

See the schema manual for a full description of all 'pdk' parameters supported by the SC schema.

The purpose of the PDK module is to encapsulate all the settings that would be associated with a PDK.
The example below shows PDK setup template::

  def setup_pdk(chip):
     '''
     A one line desription of the process PDK.

     A paragraph of module content description
     '''


**pdk**



The supported target combinations include:

  * <project>
  * <flow>
  * <flow>_<pdk>
  * <tool>
  * <tool>_<pdk>
  * <pdk>
