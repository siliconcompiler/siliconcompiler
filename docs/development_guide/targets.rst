.. _dev_targets:

Defining a Target
=================

A target in SiliconCompiler is a reusable "build configuration" for a specific type of chip. Think of it as a master recipe that bundles together everything needed to compile a design for a particular goal, such as creating a low-power IoT chip on the Skywater 130nm process or a high-performance block on FreePDK45.

Targets are implemented as simple Python functions that configure a Project object. They are loaded with a single call to :meth:`.Project.load_target()`, making it incredibly easy to set up a complex build.

A full list of built-in targets can be found on the :ref:`builtin_targets` page.

Why Create a Target?
--------------------

While you can configure a project's PDK, flow, and libraries manually, creating a target is the recommended approach for any serious project. The benefits include:

* **Encapsulation**: It bundles all technology-specific and flow-specific settings into one place.
* **Reusability**: The same target can be used across multiple designs, ensuring consistency.
* **Simplicity**: It reduces a complex setup process to a single line of code in your build script.

Anatomy of a Target Function
----------------------------

A target is a Python function that accepts a :class:`.Project` object as its first argument. Inside this function, you will typically perform the following actions:

1. **Load Core Components**: Set the fundamental building blocks of your compilation:

   * **PDK**: The process design kit for the manufacturing technology.
   * **Flow**: The sequence of EDA tool steps to run (e.g., synthesis, place-and-route).
   * **Libraries**: The standard cell libraries and/or macros to use.

2. **Set Default Constraints**: Define the default goals and physical constraints for the design.

   * **Timing Constraints**: Clock speeds, I/O delays, and other performance goals.
   * **Physical Constraints**: Desired die area, core utilization (density), and pin placement.

3. **Configure Tool Options**: Set default options for specific tools in the flow, such as the number of cores to use for a given step.

Example: A Target for a Simple ASIC
-----------------------------------

Let's create a target for a generic ASIC design. This function will load a standard ASIC flow, a fictional PDK and library, and set some common physical and timing constraints.

.. code-block:: python

  from siliconcompiler import ASICProject
  from siliconcompiler.flows import asicflow
  from siliconcompiler.tools.yosys import syn_asic

  # It's common practice to import the PDK and library schemas
  # that your target will use.
  from my_designs.pdks import my_freepdk45
  from my_designs.libs import my_nangate45

  def my_asic_target(project: ASICProject,
                     # Targets can be parameterized. Here, we allow the user
                     # to specify the number of cores for parallelizable steps.
                     place_np=1,
                     route_np=1):
      '''
      A simple target for a generic 45nm ASIC design.
      '''

      # 1. Load Core Components
      # The order is important: load libraries and PDK first, then the flow.
      project.set_mainlib(my_nangate45.Nangate45())
      project.set_pdk(my_freepdk45.FreePDK45())
      project.set_flow(asicflow.ASICFlow(place_np=place_np, route_np=route_np))

      # 2. Set Default Constraints

      # Timing Constraints: Define a "typical" corner for setup/hold analysis.
      # This sets the performance goals for the design.
      scenario = project.get_timingconstraints().make_scenario("typical")
      scenario.add_libcorner("typical")
      scenario.set_pexcorner("typical")
      scenario.add_check(["setup", "hold"])

      # Physical Constraints: Define the physical layout goals.
      # Here, we aim for 40% core utilization and a 1-micron margin.
      area = project.get_areaconstraints()
      area.set_density(40)
      area.set_coremargin(1)

      # 3. Configure Tool Options
      project.get_task(filter=syn_asic.ASICSynthesis).set_strategy("AREA3")


How to Use the Target
---------------------

Once the target function is defined, you can load it into your project like this:

.. code-block:: python

  import siliconcompiler

  # Create a project
  project = siliconcompiler.ASICProject()

  # Load the entire configuration by calling the target function.
  # We can also pass values for the parameterized arguments.
  project.load_target(my_asic_target, place_np=4, route_np=4)

  # Now the project is fully configured and ready to run!
  # project.run()

Next Steps
----------

A target is composed of other SiliconCompiler modules. To build effective targets, you will need to understand how to define these components:

* **PDKs**: Learn how to define a PDK in the :ref:`PDK<dev_pdks>` documentation.
* **Libraries**: Learn how to define a standard cell library in the :ref:`Library<dev_libraries>` documentation.
* **Flows**: Learn how to build a custom flow in the :ref:`Flow<dev_flows>` documentation.
