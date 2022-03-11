import os
import subprocess
import shlex
import pytest

@pytest.mark.eda
def test_gcd_cli(scroot):
    '''Basic CLI test: build the GCD example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = f'{scroot}/examples/gcd'

    script = f'''sc {gcd_ex_dir}/gcd.v \
        -target freepdk45_demo \
        -clock_pin "core_clock clk" \
        -clock_period "core_clock 10" \
        -asic_diearea (0,0) \
        -asic_diearea (100.13,100.8) \
        -asic_corearea (10.07,11.2) \
        -asic_corearea (90.25,91) \
        -loglevel INFO \
        -quiet \
        -relax \
        -design gcd'''

    # Run the build command.
    subprocess.run(shlex.split(script), stdout = subprocess.DEVNULL)

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
