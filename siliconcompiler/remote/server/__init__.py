'''
The v1 remote job server, run with ``python -m siliconcompiler.remote.server``.

``app.py``        the Flask application, and the checks it starts with
``config.py``     what this deployment promises, and its defaults
``errors.py``     the frozen error registry; ``errorpages/`` a page per type
``jobs/``         the job, create to delete: the one service routes and portal use
``routes/``       the v1 endpoints, one module per group
``portal/``       the web UI
``state/``        the store's rows and the storage's bytes
``identity/``     sessions, accounts and devices
``staging/``      opening the upload, reading the manifest, fetching sources
``packages/``     a job's Python packages, installed while it stages
``software/``     the software and images this deployment offers
``running/``      handing a run to a scheduler, and the process that runs it
``outputs/``      what a run leaves behind, served and taken back

🔴 Importing a part does not import Flask: the run's process and the manifest's
read load modules from here, so the names below load when first asked for.
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
