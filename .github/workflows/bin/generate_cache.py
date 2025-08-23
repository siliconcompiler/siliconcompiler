import os
import sys
from pathlib import Path

# from siliconcompiler import Chip
# from siliconcompiler.package import path as sc_path
# import lambdapdk
# from logiklib.demo.K4_N8_6x6 import K4_N8_6x6
# from logiklib.demo.K6_N8_3x3 import K6_N8_3x3
# from logiklib.demo.K6_N8_12x12_BD import K6_N8_12x12_BD
# from logiklib.demo.K6_N8_28x28_BD import K6_N8_28x28_BD


if __name__ == "__main__":
    # chip = Chip('cache')

    # chip.use(lambdapdk)
    # chip.use(K4_N8_6x6)
    # chip.use(K6_N8_3x3)
    # chip.use(K6_N8_12x12_BD)
    # chip.use(K6_N8_28x28_BD)

    cwd = Path(os.getcwd())
    cwd.mkdir(exist_ok=True)
    # chip.set('option', 'cachedir', cwd / '.sc' / 'cache')

    # for package in chip.getkeys('package', 'source'):
    #     chip.logger.info(f"Fetching {package} data source")

    #     try:
    #         sc_path(chip, package)
    #     except Exception as e:
    #         chip.logger.info(f"Failed to generate cache for {package}: {e}")
    #         sys.exit(1)

    sys.exit(0)
