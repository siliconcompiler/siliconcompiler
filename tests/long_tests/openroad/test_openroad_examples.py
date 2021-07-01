import os
import siliconcompiler
from tests.fixtures import test_wrapper

# Find the OpenROAD examples directory under `third_party/`.
or_ex_dir = os.path.abspath(__file__)
or_ex_dir = or_ex_dir[:or_ex_dir.rfind('/tests/long_tests')]
or_ex_dir += '/third_party/openroad/examples'

##################################
def gen_chip(sources, target, design, constraint, clk_sig, diesize, coresize):
    '''Helper method to generate a Chip object for a test design.
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    # Inserting value into configuration
    for source in sources:
        chip.add('source', source)
    chip.add('design', design)
    chip.add('clock', 'clock_name', 'pin', clk_sig)
    chip.add('constraint', constraint)
    chip.set('target', target)
    chip.set('asic', 'diesize', diesize)
    chip.set('asic', 'coresize', coresize)
    chip.set_jobid()

    # Apply target PDK settings.
    chip.target()

    # Set a few last options.
    chip.set('stop', 'export')
    chip.set('quiet', 'true')

    # Return the generated Chip object.
    return chip

##################################
def run_chip_job(chip):
    '''Helper method to run a test job on a Chip object, and ensure success.
    '''

    # Run the job.
    chip.run()

    # Verify that GDS and SVG files were generated.
    top = chip.get('design')[-1]
    assert os.path.isfile('build/' + top + '/job1/export/outputs/' + top + '.gds')
    assert os.path.isfile('build/' + top + '/job1/export/outputs/' + top + '.svg')

##################################
def test_gcd_sky130hd():
    '''Basic CLI test: build the GCD example by running `sc` as a command-line app.
    '''

    # Create the Chip object which represents the design configuration.
    chip = gen_chip([or_ex_dir + '/gcd/gcd.v'], 'sky130',
                    'gcd', or_ex_dir + '/gcd/sky130hd.sdc', 'clk',
                    '0 0 279.96 280.128', '9.996 10.08 269.964 270.048')

    # Set verilator option to support this design's nonstandard metacomments.
    chip.cfg['flow']['import']['option']['value'].append('-Wfuture-')

    # Run the design through the workflow, and assert success.
    run_chip_job(chip)

##################################
def test_gcd_freepdk45():
    '''Basic CLI test: build the GCD example by running `sc` as a command-line app.
    '''

    # Create the Chip object which represents the design configuration.
    chip = gen_chip([or_ex_dir + '/gcd/gcd.v'], 'freepdk45',
                    'gcd', or_ex_dir + '/gcd/freepdk45.sdc', 'clk',
                    '0 0 100.13 100.8', '10.07 9.8 90.25 91')

    # Set verilator option to support this design's nonstandard metacomments.
    chip.cfg['flow']['import']['option']['value'].append('-Wfuture-')

    # Run the design through the workflow, and assert success.
    run_chip_job(chip)

##################################
def test_aes_freepdk45():
    '''Basic CLI test: build the AES example by running `sc` through its Python API.
    '''

    # Create the Chip object which represents the design configuration.
    chip = gen_chip([or_ex_dir + '/aes/aes_cipher_top.v'], 'freepdk45',
                    'aes_cipher_top', or_ex_dir + '/aes/freepdk45.sdc', 'clk',
                    '0 0 500.65 504', '10.07 9.8 490.77 494.2')

    # Run the design through the workflow, and assert success.
    run_chip_job(chip)

##################################
def test_aes_sky130hd():
    '''Basic CLI test: build the AES example by running `sc` through its Python API.
    '''

    # Create the Chip object which represents the design configuration.
    chip = gen_chip([or_ex_dir + '/aes/aes_cipher_top.v'], 'sky130',
                    'aes_cipher_top', or_ex_dir + '/aes/sky130hd.sdc', 'clk',
                    '0 0 1117.77 1019.2', '10.07 9.8 1107.7 1009.4')

    # Run the design through the workflow, and assert success.
    run_chip_job(chip)
