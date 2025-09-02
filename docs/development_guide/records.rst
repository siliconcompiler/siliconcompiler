Execution Records and Provenance
================================

To support hardware provenance and ensure reproducibility, SiliconCompiler automatically records key information during every compilation run.
This creates a detailed history, or "provenance," for your design, which is crucial for tracking a complete and unbroken chain of custody from source code to final layout.

What Information is Recorded?
-----------------------------

Tracking is broken into two categories to protect potentially sensitive information by default.

Default Tracking (Always On)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For every run, SiliconCompiler will automatically record the following without any special configuration:

* **SiliconCompiler Version:** The exact version of the framework used.
* **Tool Details:** The version of each tool executed (e.g., Yosys, OpenROAD) and the specific command-line options used.
* **Timestamps:** The start and end times for each task.

Optional Full Tracking
^^^^^^^^^^^^^^^^^^^^^^

You can enable a more detailed level of tracking that also records environmental information.

* **User:** The username of the person who initiated the run.
* **Machine:** The hostname of the machine where the run was executed.

.. note::
  Please be aware that user and machine information can be considered sensitive.
  Use caution and ensure you are complying with your organization's privacy policies before enabling this feature, especially if you plan to share the results.


Enabling Full Tracking
----------------------

To capture all available provenance data, you must explicitly enable the :keypath:`option,track` parameter on your project object:

.. code-block:: python

  import siliconcompiler

  # Create a project object
  proj = siliconcompiler.Project('my_design')

  # Enable full tracking to record user and machine information
  proj.set('option', 'track', True)

  # ... continue with your compilation setup

How Records Are Stored
----------------------

Records are captured for each individual task (defined by its step and index) in the flowgraph.
This granular approach ensures that every action performed on the design is documented, leaving no gaps in the history of the compilation process.
