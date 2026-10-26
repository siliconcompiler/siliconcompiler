'''``python -m siliconcompiler.remote.server``: serve the v1 API.'''

import argparse
import logging
import sys

from pathlib import Path
from typing import List, Optional

from siliconcompiler import __version__
from siliconcompiler.remote import banner


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m siliconcompiler.remote.server",
        description="SiliconCompiler remote job server (v1 API).")
    parser.add_argument("-port", type=int, default=8080, metavar="<int>",
                        help="port to serve on (default: %(default)s)")
    parser.add_argument("-datadir", default="./sc_server", metavar="<dir>",
                        help="directory holding the server's state (default: %(default)s)")
    parser.add_argument("-cluster", choices=("local", "slurm"), default="local",
                        metavar="<name>",
                        help="how a job is handed over to run: local or slurm "
                             "(default: %(default)s)")
    parser.add_argument("-version", action="version", version=__version__)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="| %(levelname)-8s | %(message)s")
    logger = logging.getLogger("sc-server")

    # Imported here so --help works without the "server" extra.
    try:
        from siliconcompiler.remote.server.app import create_app
    except ImportError as e:
        print(f'the server is unavailable: {e}. pip install "siliconcompiler[server]"',
              file=sys.stderr)
        return 1

    datadir = Path(args.datadir).resolve()
    app = create_app(datadir, cluster=args.cluster)

    for line in banner.strip("\n").splitlines():
        logger.info(line)
    logger.info(f"siliconcompiler {__version__}, serving the v1 API on port {args.port}")
    logger.info(f"data directory: {datadir}")
    logger.info("identity assurance: self_asserted -- this server does not verify "
                "who a caller is")

    app.run(host="0.0.0.0", port=args.port, threaded=True)       # noqa: S104
    return 0


if __name__ == "__main__":
    sys.exit(main())
