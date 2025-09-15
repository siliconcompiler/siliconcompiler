.. _dev_pdks:

Defining a Process Design Kit (PDK)
===================================

In semiconductor design, a Process Design Kit (PDK) contains all the technology-specific data—such as transistor models, layout rules, and standard cell libraries—required to manufacture a chip on a particular process node.
These kits are often complex and vary significantly between foundries.

SiliconCompiler simplifies this by providing a standardized Python object, the :class:`.PDKSchema`, to define and package a PDK.
This object acts as a structured "manifest" that describes the PDK's properties and points to all the necessary files.
Once defined, a PDK can be easily reused and loaded into any project with a single command: :meth:`.ASICProject.set_pdk()`.

Key Concepts
------------

A :class:`.PDKSchema` is built around two main concepts:

* **Metadata**: High-level information that describes the manufacturing process, such as the foundry, process node (e.g., 28nm), and metal stackup. This data is essential for design tools and for calculating manufacturing metrics.
* **Filesets**: A "fileset" is a named group of files that serve a specific purpose. For example, a views.lef fileset contains all the LEF files needed for abstract layout views, while a models.spice fileset would contain SPICE models for simulation. This organization ensures that each tool gets exactly the files it needs.

Example: Defining a Virtual PDK
-------------------------------

The following example demonstrates how to create a basic PDK definition by subclassing :class:`.PDKSchema`. We will define a fictional 28nm process.

.. code-block:: python

  from pathlib import Path
  from siliconcompiler import PDKSchema

  class ExamplePDK(PDKSchema):
      """
      A demonstration PDKSchema for a fictional 28nm process.
      """
      def __init__(self):
          super().__init__()

          # 1. Give the PDK a unique name.
          self.set_name("examplepdk")

          # Assume the PDK files are in a local directory named "examplepdk/"
          pdk_path = Path("examplepdk")

          # 2. Define the high-level process metadata.
          self.set_foundry("virtual")
          self.set_version("v1.0")
          self.set_node(28)  # Process node in nanometers
          self.set_stackup("12M") # Number of metal layers
          self.set_wafersize(300) # Wafer diameter in millimeters

          # Define manufacturing and cost parameters.
          self.set_scribewidth(0.1, 0.1)
          self.set_edgemargin(2)
          self.set_defectdensity(1.25)

          # 3. Define the data source for the PDK files.
          # Here, we point to a fictional Git repository.
          self.set_dataroot("pdksource", "git+https://data.com/source.tar.gz")

          # 4. Organize the PDK files into filesets.
          # The 'with self.active_dataroot(...)' block tells SiliconCompiler
          # that all files added inside this block are relative to this data source.
          with self.active_dataroot("pdksource"):
              # The 'with self.active_fileset(...)' block groups related files.
              # Here, we are defining the LEF files for the abstract view.
              with self.active_fileset("views.lef"):
                  self.add_file(pdk_path / "apr" / "examplepdk.lef")
                  # This helper function automatically adds technology LEF files
                  # for common open-source tools.
                  for tool in ('openroad', 'klayout', 'magic'):
                      self.add_aprtechfileset(tool)

              # Define which metal layers are available for routing.
              self.set_aprroutinglayers(min="metal2", max="metal7")


To use this PDK, you would instantiate it and pass it to your project:

.. code-block:: python

  import siliconcompiler

  # Create a project
  project = siliconcompiler.ASICProject()

  # Instantiate and set the PDK
  pdk = ExamplePDK()
  project.set_pdk(pdk)

  # Now, when project.run() is called, the tools in the flow
  # will be able to find and use the files defined in the PDK.

Useful APIs
-----------

The PDKSchema class provides a comprehensive API for defining all aspects of a PDK.

.. currentmodule:: siliconcompiler.PDK

Setting Process Metadata
^^^^^^^^^^^^^^^^^^^^^^^^

These methods define the core physical and manufacturing properties of the process.

.. autosummary::
    :nosignatures:

    set_foundry
    set_node
    set_stackup
    set_wafersize
    set_unitcost
    set_defectdensity
    set_scribewidth
    set_edgemargin
    set_aprroutinglayers

Organizing Filesets
^^^^^^^^^^^^^^^^^^^

These methods are used to group files for different tools and design views.

.. autosummary::
    :nosignatures:

    add_aprtechfileset
    add_displayfileset
    add_devmodelfileset
    add_pexmodelfileset
    add_runsetfileset
    add_waiverfileset

Manufacturing Calculations
^^^^^^^^^^^^^^^^^^^^^^^^^^

These methods use the defined metadata to compute key manufacturing metrics.

.. autosummary::
    :nosignatures:

    calc_yield
    calc_dpw

Class Reference
---------------

.. autoclass:: siliconcompiler.PDK
    :no-index:
    :members:
    :show-inheritance:
    :inherited-members:
