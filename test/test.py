import argparse
import os
import shutil
import siliconcompiler
import subprocess
import sys

from multiprocessing import Process

###########################
def gcd_test():
    '''Basic CLI test: build the GCD example by running `sc` as a command-line app.
    '''

    # Use subprocess to test running the `sc` scripts as a command-line program.
    # Pipe stdout to /dev/null to avoid printing to the terminal.
    gcd_ex_dir = os.path.abspath('../examples/gcd/')
    subprocess.run(['sc',
                    gcd_ex_dir + '/gcd.v',
                    '-design', 'gcd',
                    '-target', 'freepdk45',
                    '-asic_diesize', '0 0 100.13 100.8',
                    '-asic_coresize', '10.07 11.2 90.25 91',
                    '-constraint', gcd_ex_dir + '/constraint.sdc',
                    '-loglevel', 'NOTSET'],
                   stdout = subprocess.DEVNULL)

    # Verify that a GDS file was generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')

###########################
def gcd_perm_test():
    # TODO: Permutations test.
    return True

###########################
def gcd_server_test():
    # TODO: Local server test.
    return True

###########################
def gcd_server_perm_test():
    # TODO: Local server test with permutations.
    return True

###########################
def gcd_py_test():
    '''Basic Python API test: build the GCD example using only Python code.
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    # Inserting value into configuration
    chip.add('source', 'examples/gcd/gcd.v')
    chip.add('design', 'gcd')
    chip.add('clock', 'clock_name', 'pin', 'clk')
    chip.add('constraint', "examples/gcd/constraint.sdc")
    chip.set('target', "freepdk45")
    chip.set('asic', 'diesize', "0 0 100.13 100.8")
    chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
    chip.set_jobid()

    chip.target()

    chip.set('stop', 'export')
    chip.set('quiet', 'true')

    new_proc = Process(target=chip.run)
    new_proc.start()
    new_proc.join()

    # (Printing the summary makes it harder to see other test case results.)
    #chip.summary()

    # Verify that a GDS file was generated.
    assert os.path.isfile('build/gcd/job1/export/outputs/gcd.gds')

###############################
# Core test runner logic
###############################

tests = {
    'gcd': gcd_test,
    'gcd_permutations': gcd_perm_test,
    'gcd_server': gcd_server_test,
    'gcd_server_permutations': gcd_server_perm_test,
    'gcd_py': gcd_py_test,
}

def run_tests():
    # Read command-line options:
    #   -list:  List supported tests.
    #   -tests: Comma-separated list of tests to run (default: all).
    parser = argparse.ArgumentParser()
    parser.add_argument('-list',
                        action='store_true',
                        help='List available tests.')
    parser.add_argument('-tests',
                        type=str,
                        help='Optional comma-separated list of tests to run.')

    cmdargs = vars(parser.parse_args())

    if cmdargs['list']:
        print('Available tests:')
        for test_name in tests.keys():
            print('  * ' + test_name)
        # Don't run the actual tests when '-list' is specified.
        sys.exit(1)

    # Get a list of tests to run (all tests if none are specified).
    if cmdargs['tests']:
        tests_to_run = cmdargs['tests'].strip().split(',')
        # Verify that all test names are valid.
        for test_name in tests_to_run:
            if not test_name in tests.keys():
                print('Error: Invalid test name: ' + test_name)
                sys.exit(1)
    else:
        tests_to_run = list(tests.keys())

    # Run each test individually.
    print('Running tests: ' + str(tests_to_run))
    topdir = os.getcwd()
    for test_name in tests_to_run:
        # Create and enter a local build directory.
        os.mkdir(test_name)
        os.chdir(topdir + '/' + test_name)

        # Run the test.
        try:
            tests[test_name]()
            print('  * ' + test_name + ': PASS')
        except:
            print('  * ' + test_name + ': FAIL')

        # Exit and remove the local build directory.
        os.chdir(topdir)
        shutil.rmtree(test_name)

# Run the 'run_tests()' method when this file is run.
if __name__ == "__main__":
    run_tests()
