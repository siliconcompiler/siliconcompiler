'''
``python -m siliconcompiler.remote.server``

A module entry point, not a console script, so it can be driven in-process.
Everything beyond the flags has a default in ``config.py``, overridable in
``<datadir>/config.json``.
'''

import argparse
import logging
import sys

from pathlib import Path
from typing import List, Optional

from siliconcompiler import __version__ as sc_version
from siliconcompiler.remote import banner
from siliconcompiler.remote.server.config import TEST_MODES


__all__ = ["main"]


# One batch job per run, not one dispatch per node. No `docker`: under batch
# submission the container is the cluster's business.
CLUSTERS = ("local", "slurm")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m siliconcompiler.remote.server",
        description="SiliconCompiler remote job server (v1 API), alpha: the v1 client, "
                    "this server and its portal may still change.",
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
        help=f"how a job is handed over to run: {', '.join(CLUSTERS)} "
             "(default: %(default)s)")
    parser.add_argument(
        "-test-mode", type=int, choices=sorted(TEST_MODES), default=None,
        metavar="<n>",
        help="FOR TESTING: serve one of the preset deployments: what this "
             "server does by default (1), up to the most it withholds (3), or "
             "one that can fetch nothing (4). config.json still applies on top")
    parser.add_argument(
        "-version", action="version", version=sc_version)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    # 🔴 `python -m` puts the working directory on sys.path, and the server is
    # usually started in its data directory, among every job's extracted
    # archive (contract §1): it comes off before anything else.
    import os

    here = os.path.realpath(os.getcwd())
    sys.path[:] = [entry for entry in sys.path
                   if entry and os.path.realpath(entry) != here]

    args = _parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="| %(levelname)-8s | %(message)s")
    logger = logging.getLogger("sc-server")

    # Imported here so --help works without the "server" extra, as the docs
    # build needs.
    from siliconcompiler.remote.server.app import (
        create_app, missing_server_dependency)

    if missing_server_dependency:
        print(f"the server is unavailable: {missing_server_dependency} is not "
              'installed. pip install "siliconcompiler[server]"',
              file=sys.stderr)
        return 1

    datadir = Path(args.datadir).resolve()

    # This host's own names on this port, where config.json names none.
    import socket
    here_names = dict.fromkeys(
        name for name in ("localhost", "127.0.0.1", socket.gethostname(),
                          socket.getfqdn()) if name)
    origins = [f"http://{name}:{args.port}" for name in here_names]

    try:
        app = create_app(datadir, cluster=args.cluster, test_mode=args.test_mode,
                         public_origins=origins)
    except Exception as e:                                       # noqa: BLE001
        # A setup problem: a traceback would bury the one line that says which.
        logger.error(str(e))
        return 1

    for line in banner.strip("\n").splitlines():
        logger.info(line)

    logger.info(f"siliconcompiler {sc_version}, serving the v1 API on "
                f"port {args.port} (alpha)")
    logger.info(f"data directory: {datadir}")
    logger.info(f"error type pages: http://localhost:{args.port}/server-errors/ "
                "-- and each refusal names its page with a Link header")
    logger.info(f"cluster: {args.cluster}")
    logger.info(f"reached at: {', '.join(app.config['SC_PUBLIC_ORIGINS'])} "
                "-- a client addressing it any other way is refused; set "
                "public_origins in config.json behind a proxy")
    if args.test_mode is not None:
        # Loud: a deployment left in it serves less than its operator thinks.
        config = app.config["SC_CONFIG"]
        logger.warning(f"TEST MODE {args.test_mode}: features "
                       f"{config['features'] or 'none'}, API hands over "
                       f"{config['api_fetchable_kinds'] or 'every kind'}, "
                       f"denied {config['denied_resources'] or 'nothing'}"
                       + (", every fetch fails" if config["fetch_fails"] else ""))
    # Nothing here verifies who a caller is, and an operator should hear so at
    # startup.
    logger.info(f"identity assurance: {app.config['SC_CONFIG']['identity_assurance']} "
                "-- this server does not verify who a caller is")

    app.run(host="0.0.0.0", port=args.port, threaded=True)       # noqa: S104
    return 0


if __name__ == "__main__":
    sys.exit(main())
