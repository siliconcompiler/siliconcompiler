'''
The v1 remote job server.

Run it with ``python -m siliconcompiler.remote.server``. At the top, what every
part leans on; below it, one folder per part of a job's life:

``app.py``        the Flask application, and the checks it starts with
``config.py``     what this deployment promises: defaults, then an optional
                  ``<datadir>/config.json``
``errors.py``     the frozen error registry and its RFC 9457 bodies;
                  ``errorpages/`` holds a page for each type
``jobs.py``       the job, from create to delete: the one service every route
                  and the portal go through
``routes/``       the v1 endpoints, one module per group
``portal/``       the web UI, through the same service as the API

``state/``        the store's rows and the storage's bytes
``identity/``     sessions, accounts and devices
``staging/``      opening the upload, reading the manifest, fetching sources
``packages/``     a job's Python packages, installed while it stages
``software/``     the software and images this deployment offers
``running/``      handing a run to a scheduler, and the process that runs it
``outputs/``      what a run leaves behind, served and taken back

🔴 **Importing a part does not import Flask.** The run's own process and the
manifest's read load modules from here, and neither needs a web server; so the
names below are loaded when first asked for.
'''

__all__ = ["create_app", "Config", "ProblemError", "problem", "Store"]

_WHERE = {"create_app": "siliconcompiler.remote.server.app",
          "Config": "siliconcompiler.remote.server.config",
          "ProblemError": "siliconcompiler.remote.server.errors",
          "problem": "siliconcompiler.remote.server.errors",
          "Store": "siliconcompiler.remote.server.state.store"}


def __getattr__(name):
    if name in _WHERE:
        import importlib

        return getattr(importlib.import_module(_WHERE[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
