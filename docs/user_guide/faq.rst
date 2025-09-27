.. _faq:

FAQ
===

This is a list of Frequently Asked Questions about SiliconCompiler.
Feel free to suggest new entries!

How do I...
-----------

... set up a new tool?

    See :ref:`Tools <dev_tools>`

... set up a new flow?

    See :ref:`Flows <dev_flows>`

... set up a new pdk?

    See :ref:`PDKs <dev_pdks>`

... set up a new library?

    See :ref:`Libraries <dev_libraries>`

... set up a new target?

    See :ref:`Targets <dev_targets>`

... create a design object?

   .. code-block:: python

      from siliconcompiler import Design
      design = Design('<design>')

... create an asic project object?

   .. code-block:: python

      from siliconcompiler import ASICProject
      project = ASICProject(design)

... active filesets?

   .. code-block:: python

      project.add_fileset("rtl")

... run a compilation?

   .. code-block:: python

      project.run()

... display my layout?

   .. code-block:: python

       project.show()

... display a previous run from the command line?

    .. code-block:: bash

       sc-show -design <name>

... change the logger level?

    .. code-block:: python

        project.logger.setLevel(<INFO|DEBUG|WARNING|ERROR>)

... check my setup before running?

    .. code-block:: python

        project.check_manifest()

... change the build directory?

    .. code-block:: python

        project.set('option', 'builddir', <dirpath>)

... change the caching directory?

    .. code-block:: python

        project.set('option', 'cachedir', <dirpath>)

... use the setup json manifest file from a previous run?

    .. code-block:: python

        project = Project.from_manifest(<filepath>)

... control the thread parallelism for a task?

    .. code-block:: python

       project.set('tool', <tool>, 'task', <task>, 'threads', <n>, step=<step>, index=<index>)

... start a fresh run?

    .. code-block:: python

       project.set('option', 'clean', True)

... start a fresh run and keep the old one?

    .. code-block:: python

       project.set('option', 'clean', True)
       project.set('option', 'jobincr', True)

... start a fresh run using the previous run information?

    .. code-block:: python

       project.set('option', 'clean', True)
       project.set('option', 'jobincr', True)
       project.set('option', 'from', 'floorplan')

... register a new source of files?

    .. code-block:: python

       design.set_dataroot("<name>", "<path>", "<reference>")

... register a new source of files relative to my current file?

    .. code-block:: python

       design.set_dataroot('<name>', __file__)
