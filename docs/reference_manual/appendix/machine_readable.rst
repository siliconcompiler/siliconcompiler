.. _machine_readable:

.. index:: ! llms.txt, ! schema.json, ! machine-readable documentation

Machine-readable documentation
==============================

Three files are published alongside this site for programs rather than people:
editor tooling, validators, scripts, and code assistants answering questions about
SiliconCompiler. They hold the same content as the pages you are reading, in forms
that do not require parsing HTML.

.. list-table::
   :header-rows: 1
   :widths: 22 20 58

   * - File
     - Format
     - Contents
   * - `llms.txt <../../llms.txt>`_
     - Markdown
     - The current API, the names that no longer exist, where a new module
       belongs, and a linked index of every page on this site. Small enough to
       fetch speculatively. Follows the `llmstxt.org <https://llmstxt.org>`_
       convention.
   * - `llms-full.txt <../../llms-full.txt>`_
     - Markdown
     - The full text of every hand-written page on this site in one file, with
       cross-references resolved to absolute URLs. The generated reference is
       linked rather than included.
   * - `schema.json <../../schema.json>`_
     - JSON
     - Every parameter of every documented schema class, keyed by
       :term:`keypath`.

Versions
--------

The files are generated during each documentation build, so the copy served from
a version describes that version:

.. code-block:: text

   https://docs.siliconcompiler.com/en/stable/llms.txt     # current release
   https://docs.siliconcompiler.com/en/latest/llms.txt     # development branch
   https://docs.siliconcompiler.com/en/v0.38.3/llms.txt    # a specific release

This matters more for SiliconCompiler than it would for most projects: the API
changed substantially at v0.35.0, so a file describing "the current API" is only
meaningful next to a version. Prefer ``stable`` unless you specifically want
unreleased behaviour.

The schema dump
---------------

``schema.json`` is organised by class, then by keypath, with keypath segments
joined by commas -- the same notation as the :ref:`Schema Reference <schema>` and
as a ``get()`` call. ``default`` appears as a literal segment where the schema
accepts an arbitrary name:

.. code-block:: json

   {
     "sc_version": "0.38.3",
     "schemaversion": "0.57.1",
     "classes": {
       "ASIC": {
         "description": "The ASIC class extends the base Project class ...",
         "parameters": {
           "option,fileset": {
             "type": "[str]",
             "scope": "global",
             "pernode": "never",
             "shorthelp": "Option: Selected design filesets",
             "help": "List of filesets to use from the selected design library",
             "defvalue": []
           },
           "tool,default,task,default,warningoff": {"...": "..."}
         }
       }
     }
   }

The classes covered are the ones documented in the :ref:`Schema Reference
<schema>`, and the per-parameter fields are the ones defined at the top of that
page. The per-node value tree is omitted, because it describes one populated
project rather than the schema; ``defvalue`` carries the default.

Two version numbers appear at the top level, and they are independent:
``sc_version`` is the package release and ``schemaversion`` is the schema's own
semver, which is what a :term:`manifest` records. :ref:`Schema Changes
<schema_changelog>` tracks the latter.

.. note::
   These files are a convenience, not a stable API. The content tracks the
   documentation, so it changes when the documentation changes. If you are
   building something that depends on the schema long-term, pin a version in the
   URL and read :ref:`Schema Changes <schema_changelog>` before moving.
