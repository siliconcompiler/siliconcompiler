PDK configuration
===================================

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
