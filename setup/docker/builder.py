#!/usr/bin/env python3
# Deprecated: the builder ships in the wheel as siliconcompiler.utils.toolimages.
# Kept for a docker_image.yml from before that, which runs this path in whatever
# checkout it is given -- scgallery's run-designs.yml calls it at @main against a
# pull request's code, so the two can be from either side of the move.

import sys
import warnings

from siliconcompiler.utils.toolimages import main


if __name__ == '__main__':
    warnings.warn("setup/docker/builder.py is deprecated, use "
                  "python3 -m siliconcompiler.utils.toolimages", DeprecationWarning, stacklevel=1)
    sys.exit(main())
