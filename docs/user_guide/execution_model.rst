.. _execution_model:

###################
Compilation Process
###################

The complete SiliconCompiler compilation is handled by a single call to the :meth:`.Project.run()` function.
Within that function call, a static data :term:`flowgraph`, consisting of :term:`nodes <flowgraph node>` and :term:`edges <edge>` is traversed and "executed."

The static flowgraph approach was chosen for a number reasons:

* Performance scalability ("cloud-scale")
* High abstraction level (not locked into one language and/or shared memory model)
* Deterministic execution
* Ease of implementation (synchronization is hard)

The Flowgraph
-------------

Nodes and Edges
^^^^^^^^^^^^^^^

A SiliconCompiler flowgraph consists of a set of connected nodes and edges, where:

* A :term:`node <flowgraph node>` is an executable :term:`tool` performing some (":term:`task`"), and
* An :term:`edge` is the connection between those tasks, specifying execution order.

.. graphviz:: _images/concepts/flowgraph.dot
   :align: center

Tasks
^^^^^
SiliconCompiler breaks down a "task" into an atomic combination of a step and an index, where:

1. A :term:`step` is defined as discrete function performed within compilation flow such as synthesis, linting, placement, routing, etc, and
2. An :term:`index` is defined as variant of a step operating on identical data.

An example of this might be two parallel synthesis runs with different settings after elaboration.
The two synthesis "tasks" might be called ``syn/0`` and ``syn/1``, where:

.. graphviz:: _images/concepts/step_index.dot
   :align: center

See :ref:`using index for optimization <using_index_for_opt>` for more information on why using indices to build your flowgraph are helpful.

Execution
^^^^^^^^^

Flowgraph execution is done through the :meth:`.Project.run()` function which checks the flowgraph for correctness and then executes all tasks in the flowgraph from start to finish.

Flowgraph Examples
------------------

The flowgraph, used in the :ref:`asic demo <asic_demo>`, is a built-in compilation flow, called :ref:`asicflow <schema-siliconcompiler-flows-asicflow-asicflow>`. This compilation flow is a pre-defined flowgraph customized for an ASIC build flow, and is called through the :meth:`.Project.add_dep()` function, which calls a :ref:`pre-defined PDK module <builtin_pdks>` that :ref:`uses the asicflow flowgraph <schema-siliconcompiler-flows-asicflow-asicflow>`.

You can design your own project compilation build flows by easily creating custom flowgraphs through:

* :meth:`.Flowgraph.node()` / :meth:`.Flowgraph.edge()` methods

The user is free to construct a flowgraph by defining any reasonable combination of steps and indices based on available tools and PDKs.


A Two-Node Flowgraph
^^^^^^^^^^^^^^^^^^^^

The example below shows a snippet which creates a simple two-step (import + synthesis) compilation pipeline.

.. The built in functions are important to minimize data movement in remote processing workflows, where intermediate results may not be accessible.


.. literalinclude:: examples/heartbeat_flowgraph.py
   :caption: Snippet from `examples/heartbeat_flowgraph.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/docs/user_guide/examples/heartbeat_flowgraph.py>`_
   :start-after: start of flowgraph setup
   :end-before: end of flowgraph setup


At this point, you can visually examine your flowgraph by using :meth:`.Flowgraph.write_flowgraph()`. This function is very useful in debugging graph definitions. ::

  flow.write_flowgraph("flowgraph.svg", landscape=True)

.. scflowgraph:: examples/heartbeat_flowgraph.py
   :landscape:
   :align: center

.. _using_index_for_opt:

Using Index for Optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The previous example did not include any mention of :term:`index`, so the index defaults to ``0``.

While not essential to basic execution, the ':term:`index`' is fundamental to searching and optimizing tool and design options.

One example use case for the index feature would be to run a design through synthesis with a range of settings and then selecting the optimal settings based on power, performance, and area.
The snippet below shows how a massively parallel optimization flow can be programmed using the SiliconCompiler Python API.

.. literalinclude:: examples/flowgraph_doe.py
   :caption: Snippet from `examples/flowgraph_doe.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/docs/user_guide/examples/flowgraph_doe.py>`_ that sets up parallel synthesis runs for optimization
   :start-after: # create node for optimized (or minimum in this case) metric
   :end-before: if __name__

.. scflowgraph:: examples/flowgraph_doe.py
   :align: center

.. seealso::
   :ref:`Parallel Job Execution <parallel_execution>` runs this pattern as a
   worked example and compares it against the two other ways of parallelizing a
   sweep, and :ref:`Multi-Job Flows <multi_job_sweep>` covers reading the
   resulting metrics back out to drive a decision.
