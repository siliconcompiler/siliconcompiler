.. _dev_libraries:

Defining a Library
==================

In hardware design, a library is a collection of reusable components.
SiliconCompiler generalizes this concept with the :class:`.DesignSchema` object, which acts as a standardized "manifest" for any piece of IP (Intellectual Property) you want to include in your design.

This could be a hard macro with pre-defined physical layouts (GDS, LEF), a standard cell library from a foundry, or a soft IP delivered as RTL source code (Verilog, VHDL).

By packaging IP into a :class:`.DesignSchema`, you make it easy to manage, version, and reuse across different projects.
Libraries are loaded into a project using the :meth:`.Project.add_dep()` method.

Types of Libraries
------------------

There are two primary categories of libraries you can define:

* **Hard Libraries (StdCellLibrarySchema)**: These represent foundational, physical IP. This includes standard cell libraries, I/O cells, or hard macros (like SRAMs or SERDES) that have fixed layouts. They are defined using the specialized :class:`.StdCellLibrarySchema` class, which has extra features for handling physical and timing models.
* **Soft Libraries (DesignSchema)**: These represent synthesizable IP delivered as source code. This is common for digital IP cores that you want to integrate into your design before synthesis. They are defined using the base :class:`.DesignSchema` class.

Example 1: Hard IP Library
--------------------------

This example demonstrates how to define a library for a hard macro. This macro is a pre-designed block with its own physical layout (LEF, GDS) and timing models (.lib).
We will use the :class:`.StdCellLibrarySchema` because it is a physical, foundational component.

.. code-block:: python

  from pathlib import Path
  from siliconcompiler import StdCellLibrarySchema
  from my_pdk import FakePDK # Assuming a PDK is defined elsewhere

  class FakeHardIPLibrary(StdCellLibrarySchema):
      def __init__(self):
          # 1. Call the parent constructor with a unique name for the library.
          super().__init__("fakeip")

          # 2. Associate this library with a specific PDK.
          # This tells SiliconCompiler that this IP is designed for this technology.
          self.add_asic_pdk(FakePDK())

          # 3. Define the location of the library's source files.
          # Here, we point to a local directory.
          path_base = Path("fakeip")
          self.set_dataroot("fakedata", "python://fakedata_module")

          # 4. Organize the library's files into standardized filesets.
          with self.active_dataroot("fakedata"):
              # Define the physical view files (LEF and GDS).
              with self.active_fileset("models.physical"):
                  self.add_file(path_base / "lef" / "fakeip.lef")
                  self.add_file(path_base / "gds" / "fakeip.gds")
                  # Helper function to add standard APR tech files.
                  self.add_asic_aprfileset()

              # Define the timing models. This library provides an NLDM model
              # for the "typical" corner.
              with self.active_fileset("models.timing.nldm"):
                  self.add_file(path_base / "nldm" / "fakeip.lib")
                  # Helper to associate the file with a specific corner.
                  self.add_asic_libcornerfileset("typical", "nldm")

Using the Library
^^^^^^^^^^^^^^^^^

To use either of these libraries in your design, you would instantiate the class and add it as a dependency to your project.

.. code-block:: python

  import siliconcompiler

  project = siliconcompiler.ASICProject()

  # Instantiate and add the soft IP library.
  soft_ip_lib = FakeHardIPLibrary()
  project.add_asiclib(soft_ip_lib)

  # Now, the 'fakeip' will be included during compilation.
  # project.run()

Example 2: Soft IP Library
--------------------------

This example shows how to define a library for a soft IP core, which is just a reusable block of RTL code. Since there are no physical or timing views, we use the :class:`.DesignSchema`.

.. code-block:: python

  from siliconcompiler import DesignSchema

  class FakeSoftIP(DesignSchema):
      def __init__(self):
          # 1. Call the parent constructor with a unique name.
          super().__init__("fakesoftip")

          # 2. Set metadata for the library.
          self.set_version("v1.0")

          # 3. Define the location of the source files.
          self.set_dataroot("fakedata", "python://fakedata_module")

          # 4. Add the RTL source code to the 'rtl' fileset.
          # When this library is included in a project, this Verilog file
          # will be passed to the synthesis tool.
          with self.active_dataroot("fakedata"), self.active_fileset("rtl"):
                  self.add_file("rtl/fakeip.v")

Using the Library
^^^^^^^^^^^^^^^^^

To use either of these libraries in your design, you would instantiate the class and add it as a dependency to your project.

.. code-block:: python

  import siliconcompiler

  project = siliconcompiler.Project()

  # Instantiate and add the soft IP library.
  soft_ip_lib = FakeSoftIP()
  project.add_dep(soft_ip_lib)

  # Now, the 'fakeip.v' source file will be included during compilation.
  # project.run()

Useful APIs
-----------

Core Configuration
^^^^^^^^^^^^^^^^^^^

.. currentmodule:: siliconcompiler.Design

.. autosummary::
    :nosignatures:

    add_file
    set_dataroot

PDK and Physical Views
^^^^^^^^^^^^^^^^^^^^^^

.. currentmodule:: siliconcompiler.StdCellLibrary

.. autosummary::
    :nosignatures:

    add_file
    set_dataroot
    add_asic_pdk
    add_asic_aprfileset
    add_asic_libcornerfileset

Class Reference
---------------
For a complete list of all available methods, please see the full class documentation.

.. autoclass:: siliconcompiler.Design
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.StdCellLibrary
    :members:
    :show-inheritance:
    :inherited-members:
