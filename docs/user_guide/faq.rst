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

      from siliconcompiler import ASIC
      project = ASIC(design)

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

        project.option.set_builddir(<dirpath>)

... change the caching directory?

    .. code-block:: python

        project.option.set_cachedir(<dirpath>)

... use the setup json manifest file from a previous run?

    .. code-block:: python

        project = Project.from_manifest(<filepath>)

... control the thread parallelism for a task?

    .. code-block:: python

       <task class>.find_task(project).set_threads(<n>, step=<step>, index=<index>)

... start a fresh run?

    .. code-block:: python

       project.option.set_clean(True)

... start a fresh run and keep the old one?

    .. code-block:: python

       project.option.set_clean(True)
       project.option.set_jobincr(True)

... start a fresh run using the previous run information?

    .. code-block:: python

       project.option.set_clean(True)
       project.option.set_jobincr(True)
       project.option.add_from('floorplan')

... register a new source of files?

    .. code-block:: python

       design.set_dataroot("<name>", "<path>", "<reference>")

... register a new source of files relative to my current file?

    .. code-block:: python

       design.set_dataroot('<name>', __file__)

... preserve options, like scheduler information, :ref:`across sessions <user_settings>`?

    .. code-block:: python

       project.option.write_defaults()

... avoid rebuilding an expensive object (such as a PDK) many times?

    If a schema object is a pure function of its construction arguments, base it
    on ``CachedSchema``. Instances are built once per unique (hashable) set of
    arguments, and the shared, frozen instance is returned on subsequent
    constructions. This is useful for heavy objects, like PDKs, that would
    otherwise be re-created dozens of times while loading a target.

    .. code-block:: python

       from siliconcompiler import PDK
       from siliconcompiler.schema import CachedSchema

       class MyPDK(PDK, CachedSchema):
           def __init__(self):
               super().__init__("mypdk")
               # ... expensive schema population ...

       MyPDK() is MyPDK()   # True -- same shared instance, built only once

    The shared instance is *frozen*: calling ``set``, ``add``, ``unset``,
    ``remove``, or using ``EditableSchema`` on it raises a
    ``SchemaFrozenError``. This protects the shared object from accidental
    modification.

... get a modifiable version of a frozen (cached) object?

    Use ``copy()``. A copy is always mutable and fully independent of the shared
    instance, so you are free to modify it. Objects reloaded from a manifest
    (for example, inside a run) are likewise mutable.

    .. code-block:: python

       my_pdk = MyPDK()          # frozen, shared
       local = my_pdk.copy()     # mutable, independent
       local.set("pdk", "foundry", "virtual")

    To modify a frozen object in place (for example, to write resolved file
    paths or hashes back into a shared object during a run), use the ``_thaw``
    context manager, which restores the frozen state on exit:

    .. code-block:: python

       with my_pdk._thaw():
           my_pdk.set(*keypath, hashes, field="filehash")

... harden a parameterized module so I can reuse it as a macro?

    A hardened macro has no parameters, so a parameterized module cannot be
    hardened directly. Use :class:`.Uniquified`, which generates a parameter-free
    variant per used parameter combination plus a wrapper that dispatches to
    them. See the :ref:`uniquify tutorial <uniquify_modules>` and the
    :ref:`Uniquify API <uniquify_api>`.

    .. code-block:: python

       from siliconcompiler.tools.slang.utils.macro import Uniquified

       uq = Uniquified(parent_design, ["mymodule"])
       uq.build(target=freepdk45_demo)   # harden every used parameterization
       uq.wireup(project)                # alias wrappers + inject macros

... find out which parameter values my module is actually instantiated with?

    Construct :class:`.Uniquified` (construction only elaborates and generates in
    memory -- no disk writes, no tools) and read its state:

    .. code-block:: python

       uq = Uniquified(parent_design, ["mymodule"])
       print(uq.variants)   # {'mymodule': ['mymodule__N8', 'mymodule__N16']}

... rebuild only some hardened variants?

    Pass ``macros`` to :meth:`.Uniquified.build` as a variant name, a module
    name, or a glob; add ``rebuild=True`` to force a rebuild even if a cached
    macro exists.

    .. code-block:: python

       uq.build(target=freepdk45_demo, macros="mymodule__N8", rebuild=True)
