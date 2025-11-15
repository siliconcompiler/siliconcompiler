.. _execution_options:

Execution Options
=================

SiliconCompiler uses a unified schema to manage all configuration settings for acompilation run.
This schema is hierarchical and accessible through the :class:`.Project` class.
Key parts of this schema control general behavior and job execution, primarily found under the :keypath:`option` and :keypath:`option,scheduler` keys.

General Options (['option'])
----------------------------

The :keypath:`option` part of the schema holds general-purpose settings that control the overall flow and setup.
This includes parameters like:

  * ``flow``: The name of the flowgraph to run (e.g., 'asicflow', 'fpgaflow').
  * ``target``: The name of the target technology module to load.
  * ``optmode``: The optimization level (0-3).
  * ``remote``: Boolean flag to enable remote processing.
  * ``quiet``: Suppress all non-error console output.

You can set these values in your script like so:

.. code-block:: python
  
  from siliconcompiler import Project
  project = Project()

  project.option.set_optmode(2)


Scheduler Options (['option,scheduler'])
----------------------------------------

The :keypath:`option,scheduler` part of the schema configures how individual tasks (steps in the flow) are executed.
This is crucial for distributing jobs on a compute cluster or running in isolated environments like Docker.
Key scheduler parameters include:

  * ``name``: The scheduler to use (e.g., 'local', 'slurm', 'docker').
  * ``queue``: The specific queue to submit to (for schedulers like Slurm).
  * ``cores``: The number of cores to request for a task.

Example of setting up the Slurm scheduler:

.. code-block:: python

  project.option.scheduler.set_name('slurm')
  project.option.scheduler.set_queue('long_jobs')
  project.option.scheduler.set_cores(8)

Saving Options as Defaults
--------------------------

Default settings for any schema parameter can be saved to disk so they areavailable for all future sessions,
eliminating the need to set them in everyscript.
When a Project object is initialized, it automatically searches for and loadssettings from a file at ``~/.sc/options.json``.
This file acts as a user-level set of defaults.
The data is recorded in ``~/.sc/options.json`` as a JSON object mapping schemakeys to their default values.
For example, a user who always wants to use the 'slurm' scheduler and a specific queue could have an ``options.json`` file that looks like this:

.. code-block:: json

  {
    [
      {
        "key": ["scheduler", "name"],
        "value": "slurm"
      },
      {
        "key": ["scheduler", "queue"],
        "value": "my_default_queue"
      },
      {
        "key": ["optmode"],
        "value": 1
      }
    ]
}

Loading Defaults
----------------

This file is loaded automatically when you instantiate a :class:`.Project`:

.. code-block:: python

    import siliconcompiler
    project = siliconcompiler.Project('my_design')
    # project.option.scheduler.get_name() will now return 'slurm' if set in the file

Settings loaded from this file are applied *before* any settings configured
in your script, so you can always override them:

.. code-block:: python

    # ~/.sc/options.json sets scheduler name to 'slurm'
    project = siliconcompiler.Project('my_design')

    # This value will be 'slurm'
    print(f"Default scheduler: {project.option.scheduler.get_name()}")

    # Override the default
    project.option.scheduler.set_name("local")

    # This value will now be 'local'
    print(f"Overridden scheduler: {project.option.scheduler.get_name()}")
    # The run will now use the 'local' scheduler

Writing Defaults
----------------

While you can edit the `~/.sc/options.json` file manually, you can also programmatically save the current project configuration as the new default.
The :meth:`.OptionSchema.write_defaults()` method can be used to write the current schema values.
To write to the user's default options file, you can do the following:

.. code-block:: python
  
  import os
  import siliconcompiler

  project = siliconcompiler.Project()

  # Set up the desired defaults
  project.option.scheduler.set_name("slurm")
  project.option.scheduler.set_queue("my_default_queue")
  project.option.set_optmode(1)

  # Write the current configuration as the new defaults
  # from the built-in defaults.
  project.option.write_defaults()

Any new :class:`Project` instance created in a new session will now load these values.
