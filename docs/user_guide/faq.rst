FAQ
===================================

This is a list of Frequently Asked Questions about SiliconCompiler. Feel free to suggest new entries!

How do I...
-----------

... set up a new tool?

    See :ref:`Tools`

... set up a new flow?

    See :ref:`Flows`

... set up a new pdk?

    See :ref:`PDKs`

... set up a new library?

    See :ref:`Libraries`

... set up a new target?

    See :ref:`Targets`

... create a chip object?

   .. code-block:: python

      import siliconcompiler
      chip = siliconcompiler.Chip('<design>')

... run a compilation?

   .. code-block:: python

      chip.run()

... display my layout?

   .. code-block:: python

       chip.show()

... display a previous run from the command line?

    .. code-block:: bash

       sc-show -design <name>

... change the logger level?

    .. code-block:: python

        chip = siliconcompiler.Chip('<design>', loglevel=<INFO|DEBUG|WARNING|ERROR>)
        chip.set('option', 'loglevel', <level>)

... check my setup before running?

    .. code-block:: python

        chip.check_manifest()

... relax the parse constraints on import?

    .. code-block:: python

       chip.set('option', 'relax', True)

... change the build directory?

    .. code-block:: python

       chip.set('option', 'builddir', <dirpath>)

... use the setup json file from a previous run?

    .. code-block:: python

       chip.read_manifest(<filepath>)

... drive custom TCL code into the a target EDA flow?

    .. code-block:: python

       chip.set('tool', <tool>, 'task', <task>, 'prescript', <file>, step=<step>, index=<index>)
       chip.set('tool', <tool>, 'task', <task>, 'postscript', <file>, step=<step>, index=<index>)

... control the thread parallelism for a tool?

    .. code-block:: python

       chip.set('tool', <tool>, 'task', <task>, 'threads', <n>, step=<step>, index=<index>)

... start a fresh run?

    .. code-block:: python

       chip.set('option', 'clean', True)

... start a fresh run and keep the old one?

    .. code-block:: python

       chip.set('option', 'clean', True)
       chip.set('option', 'jobincr', True)

... print the description of a parameter?

    .. code-block:: python

       print(chip.help(keypath))
