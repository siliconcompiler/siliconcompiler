# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import sys

from siliconcompiler.remote.server import Server


###############################################
# Main method to run the sc-server application.
###############################################
def main():
    progname = "sc-server"
    description = """
-----------------------------------------------------------
Silicon Compiler Collection Remote Job Server (sc-server)
-----------------------------------------------------------
"""

    server = Server()

    try:
        server.create_cmdline(
            progname,
            description=description)
    except ValueError as e:
        server.logger.error(f'{e}')
        return 1

    try:
        server.run()
    except Exception as e:
        server.logger.error(f'{e}')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
