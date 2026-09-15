# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys

from siliconcompiler.remote import Server


###############################################
# Main method to run the sc-server application.
###############################################
def main():
    progname = "sc-server"
    description = """
---------------------------------------------------------
Silicon Compiler Collection Remote Job Server (sc-server)
---------------------------------------------------------
"""

    server = Server.create_cmdline(
        progname,
        description=description,
        use_cfg=True,
        use_sources=False)

    try:
        server.run()
    except ModuleNotFoundError as e:
        # A missing optional dependency is a setup problem rather than a
        # crash, so it gets a message instead of a traceback.
        print(f"{progname} is unavailable: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        server.logger.exception(e)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
