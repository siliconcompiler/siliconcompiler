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


... create a chip object?
   .. code-block:: python

      import siliconcompiler
      chip = siliconcompiler.Chip()

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

        chip = siliconcompiler.Chip(loglevel=<INFO|ERROR|DEBUG>)

... check my setup before running?
    .. code-block:: python

        chip.check()

... relax the parse contraints on import?
    .. code-block:: python

       chip.set('relax', True)

... change the build directory?
    .. code-block:: python

       chip.set('option', 'builddir', <dirpath>)

... use the setup json file from a previous run?
    .. code-block:: python

       chip.read_manifest(<filepath>)

... drive custom TCL code into the a target EDA flow?
    .. code-block:: python

       chip.set('eda', <tool>, <step>, <index>, 'prescript', <file>)
       chip.set('eda', <tool>, <step>, <index>, 'postscript', <file>)

... control the thread parallelism for a tool?
    .. code-block:: python

       chip.set('eda', <tool>, <step>, <index>, 'threads', <n>)

... print the description of a parameter?
    .. code-block:: python

       print(chip.help(keypath))
