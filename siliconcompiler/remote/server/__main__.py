'''
``python -m siliconcompiler.remote.server``

A module entry point rather than a console script: it can be imported and driven
in-process, where a console script has to be installed and spawned.

Three flags. Everything else a deployment might want to say -- its limits, what
it advertises, how long a client waits -- has a working default and can be
overridden in ``<datadir>/config.json``, so the first run of a new server needs
no file and no arguments beyond where to keep its state.
'''

import argparse
import logging
import sys

from pathlib import Path
from typing import List, Optional

from siliconcompiler import __version__ as sc_version
from siliconcompiler.remote import banner


__all__ = ["main"]


CLUSTERS = ("local", "slurm", "docker")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m siliconcompiler.remote.server",
        description="SiliconCompiler remote job server (v1 API).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Policy -- limits, features, notices -- has defaults and can be\n"
            "overridden in <datadir>/config.json. Nothing there is required."))

    parser.add_argument(
        "-port", type=int, default=8080, metavar="<int>",
        help="port to serve on (default: %(default)s)")
    parser.add_argument(
        "-datadir", default="./sc_server", metavar="<dir>",
        help="directory holding the store, the artifacts and the build trees "
             "(default: %(default)s)")
    parser.add_argument(
        "-cluster", choices=CLUSTERS, default="local", metavar="<name>",
        help=f"how nodes are dispatched: {', '.join(CLUSTERS)} "
             "(default: %(default)s)")
    parser.add_argument(
        "-version", action="version", version=sc_version)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="| %(levelname)-8s | %(message)s")
    logger = logging.getLogger("sc-server")

    # Imported here rather than at module scope so that --help works with the
    # "server" extra missing, which is also what the docs build renders from.
    from siliconcompiler.remote.server.app import (
        create_app, missing_server_dependency)

    if missing_server_dependency:
        print(f"the server is unavailable: {missing_server_dependency} is not "
              'installed. pip install "siliconcompiler[server]"',
              file=sys.stderr)
        return 1

    datadir = Path(args.datadir).resolve()

    try:
        app = create_app(datadir, cluster=args.cluster)
    except Exception as e:                                       # noqa: BLE001
        # A bad config file or an unreadable store is a setup problem, and a
        # traceback buries the one line that says which.
        logger.error(str(e))
        return 1

    for line in banner.strip("\n").splitlines():
        logger.info(line)

    logger.info(f"siliconcompiler {sc_version}, serving the v1 API on "
                f"port {args.port}")
    logger.info(f"data directory: {datadir}")
    logger.info(f"cluster: {args.cluster}")
    # The honesty half, pairing with what GET /v1 publishes. Nothing here
    # verifies who a caller is; the key bound on first contact is the only real
    # control this mode has, and an operator should know that at startup rather
    # than from a document.
    logger.info(f"identity assurance: {app.config['SC_CONFIG']['identity_assurance']} "
                "-- this server does not verify who a caller is")

    app.run(host="0.0.0.0", port=args.port, threaded=True)       # noqa: S104
    return 0


if __name__ == "__main__":
    sys.exit(main())
