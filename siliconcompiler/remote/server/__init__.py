'''
The v1 remote job server.

Run it with ``python -m siliconcompiler.remote.server``. The pieces:

``schema.sql``  the 18-table store, whose shapes are the contract crucible
                implements
``store.py``    opening it, and the reads and writes every phase needs
``config.py``   what this deployment promises, defaults plus an optional
                ``<datadir>/config.json``
``errors.py``   the frozen 31-slug error registry and its RFC 9457 bodies
``app.py``      the Flask application factory
``routes/``     one module per group of endpoints
'''

from siliconcompiler.remote.server.app import create_app
from siliconcompiler.remote.server.config import Config
from siliconcompiler.remote.server.errors import ProblemError, problem
from siliconcompiler.remote.server.store import Store

__all__ = ["create_app", "Config", "ProblemError", "problem", "Store"]
