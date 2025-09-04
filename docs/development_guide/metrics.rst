Working with Metrics
====================

In SiliconCompiler, metrics are the key performance indicators (KPIs) that measure the quality of a compilation run.
They are numerical values—like area, power, timing, and error counts—that are tracked for each step of the flow.

Metrics serve three primary purposes:

* **Automated Optimization:** To automatically select the best compilation result from multiple runs.
* **Reporting:** To display a high-level summary of a run's performance.
* **Custom Scripting:** To allow you to build custom analysis and optimization loops.

1. Automated Optimization with Goals and Weights
------------------------------------------------

SiliconCompiler's minimum task uses metrics to find the optimal design result.
To guide this process, you can configure two parameters for any given metric in the flowgraph:

* ``goal:`` The target value for a metric. This defines a hard requirement.
* ``weight:`` A value that tells the optimizer how much to prioritize one metric over another.

The default ``asicflow`` provides a great example of a typical optimization strategy. Let's break it down:

.. code-block:: python

    # For critical metrics, set a high weight and a strict goal of 0.
    if metric in ('errors', 'warnings', 'drvs', 'holdwns', 'setupwns', 'holdtns', 'setuptns'):
        project.set('flowgraph', flow, step, index, 'weight', metric, 1.0)
        project.set('flowgraph', flow, step, index, 'goal', metric, 0)

    # For "soft" optimization metrics, set a high weight but no specific goal.
    elif metric in ('cellarea', 'peakpower', 'standbypower'):
        project.set('flowgraph', flow, step, index, 'weight', metric, 1.0)

This configuration establishes:

* **Hard Constraints:** Critical violations like errors, DRCs, and setup/hold time violations have a weight of 1.0 and a goal of 0. Any run that fails to meet this goal is considered a failure.
* **Soft Constraints:** Key optimization targets like area and power also have a high weight of 1.0. The optimizer will work to minimize these values, but there is no single pass/fail number.


2. Reporting and Analysis
-------------------------

Metrics are used by the :meth:`.Project.summary()` function to generate a dashboard view of the compilation results.
You can also access them directly with :meth:`.Project.get()` to create custom reports or to feed into your own analysis scripts.

.. code-block:: python

    # Example: Get the cell area after the 'place' step
    cell_area = proj.history("job0").get('metric', 'cellarea', step='place', index='0')
    print(f"Cell area after placement: {cell_area} um^2")

The Metric Lifecycle
--------------------

Metrics are populated automatically during a run. For each task (step and index):

1. All metric values in the schema are cleared.
2. The tool (e.g., OpenROAD, Yosys) is executed.
3. The tool's :meth:`.TaskSchema.post_process()` function runs, which parses the tool's log files and reports to extract the new metric values and save them to the schema.

If you are adding a new tool, you will need to implement a :meth:`.TaskSchema.post_process()` function to parse its outputs.

List of Available Metrics
-------------------------

The following table summarizes all metrics available in the SiliconCompiler schema.
For detailed descriptions of each, please refer to the `Schema<_schema>` section of the reference manual.
