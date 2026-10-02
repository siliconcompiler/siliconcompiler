.. _builtin_resolvers:

Data Sources
============

A :term:`dataroot` is registered with ``set_dataroot(name, path, tag=None)``, and
the scheme its path starts with picks what fetches it. These are the schemes
SiliconCompiler understands, and what each one takes.

.. code-block:: python

   design.set_dataroot("<name>", "<scheme>://<location>", tag="<version>")

Some rules hold for every source:

* A path with no scheme is a local directory, as with ``file://``.
* Environment variables (``$VAR`` or ``${VAR}``) and a leading ``~`` are expanded
  in any source when it is resolved. A value set in :keypath:`option,env` takes
  precedence over the process environment.
* Any scheme takes a ``+private`` marker, as in ``git+ssh+private://``. It says
  the source must never leave this machine: a :ref:`remote run
  <remote_processing>` does not upload it, so the server has to hold its own
  copy. A private repository does not need the marker, which is about where the
  data may go rather than how it is fetched; ``github+private://`` and
  ``gitlab+private://`` also skip their anonymous attempt.
* A remote source requires a ``tag`` and is fetched once into the
  :ref:`dataroot cache <dataroot_cache>`, then reused by every project.

.. _resolver_tokens:

Where a remote source reads a token from the environment, every variable it reads
also has a dataroot-specific form, ``<PREFIX>_<DATAROOT>_TOKEN``, which is read
before ``<PREFIX>_TOKEN``. ``<DATAROOT>`` is the dataroot's name in upper case,
with any of ``# $ & - = ! / .`` removed: a GitHub dataroot named ``my-pdk`` reads
``GITHUB_MYPDK_TOKEN`` before ``GITHUB_TOKEN``. That lets dataroots on one host
use different tokens.

A package can add a scheme of its own through the
``siliconcompiler.path_resolver`` :ref:`entry point <ext_lib_entry_points>`.

.. scresolvers::
