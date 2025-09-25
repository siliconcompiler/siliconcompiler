.. _dev_flows:

Building a Flowgraph
====================

A flowgraph in SiliconCompiler defines the sequence of steps (or tasks) required to transform your hardware design from source code into a physical layout.
Think of it as a recipe for your project, where each step is a specific tool run (like synthesis or place-and-route).

Flowgraphs are highly flexible and allow you to create custom compilation flows tailored to your specific needs. You can build them in two primary ways:

1. **Instantiate Flowgraph**: For simple or dynamically generated flows, you can create an object directly from the :class:`.Flowgraph` class and configure it.
2. **Subclass Flowgraph**: For creating reusable, complex flows, you can define your own Python class that inherits from :class:`.Flowgraph`.

Once defined, you load your flowgraph into a project using the :meth:`.Project.set_flow()` method before starting a run. This tells SiliconCompiler which set of tasks to execute.

A complete set of supported builtin flows can be found in :ref:`flows <builtin_flows>`.

Key Concepts
------------

Before we build a flowgraph, let's define the core components:

* **Node**: A node represents a single task or step in the flow. Each node is typically an instance of a Task class, which wraps a specific EDA tool (e.g., Yosys for synthesis, OpenROAD for place-and-route).
* **Edge**: An edge defines a dependency between two nodes. If you create an edge from nodeA to nodeB, it means that nodeA must complete successfully before nodeB can begin. This creates the directed, acyclic graph that SiliconCompiler executes.

Example: A Basic Synthesis Flow
-------------------------------

Here's how to build a simple flow that elaborates Verilog, runs synthesis, and then performs a timing analysis.
This example demonstrates the fundamental :meth:`.node()` and :meth:`.edge()` API calls.

We'll create a new class called SynthesisFlow that inherits from :class:`.Flowgraph`.

.. code-block:: python

  # Import the base class and the specific tool tasks we need.
  from siliconcompiler import Flowgraph
  from siliconcompiler.tools.yosys import syn_asic
  from siliconcompiler.tools.opensta import timing
  from siliconcompiler.tools.slang import elaborate

  class SynthesisFlow(Flowgraph):
      """
      A simple synthesis flow that demonstrates the basic principles
      of creating a SiliconCompiler flowgraph.
      """
      def __init__(self):
          # It's important to call the parent constructor and give the flow a name.
          super().__init__("synthesis_flow")

          # Step 1: Create the nodes for our flow.
          # Each node is given a name (e.g., "elaborate") and is associated
          # with a Task object that knows how to run a specific tool.
          self.node("elaborate", elaborate.Elaborate())
          self.node("synthesis", syn_asic.ASICSynthesis())
          self.node("timing", timing.TimingTask())

          # Step 2: Create the edges to define the execution order.
          # This tells SiliconCompiler that 'elaborate' must run before 'synthesis',
          # and 'synthesis' must run before 'timing'.
          self.edge("elaborate", "synthesis")
          self.edge("synthesis", "timing")


To use this flow, you would instantiate it and set it in your project:

.. code-block:: python

  import siliconcompiler

  # Create a project
  project = siliconcompiler.Project()

  # Instantiate and set the flow
  flow = SynthesisFlow()
  project.set_flow(flow)

  # Now you can configure the rest of your project and run it.
  # project.run()


Useful APIs
-----------

The :class:`.Flowgraph` class provides a rich API for creating, modifying, and inspecting flowgraphs.

.. currentmodule:: siliconcompiler.Flowgraph

Create a Flowgraph
^^^^^^^^^^^^^^^^^^

These are the fundamental methods for building the graph structure.

.. autosummary::
    :nosignatures:

    node
    edge

Modifying a Flowgraph
^^^^^^^^^^^^^^^^^^^^^

These methods allow you to alter an existing flowgraph, which is useful for dynamically adjusting a pre-defined flow.

.. autosummary::
    :nosignatures:

    remove_node
    insert_node
    graph

Inspecting a Flowgraph
^^^^^^^^^^^^^^^^^^^^^^

These methods help you understand the structure and execution order of your flow.

.. autosummary::
    :nosignatures:

    get_nodes
    get_entry_nodes
    get_exit_nodes
    get_execution_order
    get_node_outputs
    validate
    get_task_module
    get_all_tasks
    write_flowgraph

Documentation
^^^^^^^^^^^^^

This method helps you generate documentation for your custom flow.

.. autosummary::
    :nosignatures:

    make_docs

Class Reference
---------------

For more detailed information, refer to the full API documentation for the primary classes involved in creating and managing flowgraphs.

.. scclassautosummary::
    :class: siliconcompiler/Flowgraph
    :noschema:

Supporting Classes
------------------

These classes are used internally by the flowgraph but can be useful to understand.

.. scclassautosummary::
    :class: siliconcompiler.flowgraph/FlowgraphNodeSchema
    :noschema:

.. scclassautosummary::
    :class: siliconcompiler.flowgraph/RuntimeFlowgraph
    :noschema:
