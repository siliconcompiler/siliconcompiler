import json
import os
import pytest
import subprocess
import sys
import time

from unittest.mock import Mock

# Run as a daily test, because this takes a long time to build.
@pytest.mark.eda
@pytest.mark.timeout(900)
def test_picorv32_sram(setup_example_test):
    setup_example_test('picorv32_ram')

    import picorv32_ram
    chip = picorv32_ram.build_top()
    chip.run()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/picorv32_top/job0/export/0/outputs/picorv32_top.gds')

# Run remotely, using the minimal development server.
# TODO: Until we merge in some client.py changes to use GDS/LEF files which get copied into the build
# directory, this "remote" test will only work on localhost.
# It is still useful to test for failures which can only occur in the remote flow, however.
@pytest.mark.eda
@pytest.mark.timeout(900)
@pytest.mark.skip(reason='Long runtime, possibly causing transient failures')
def test_picorv32_sram_remote(setup_example_test):
    setup_example_test('picorv32_ram')

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-port', '8090',
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'])
    time.sleep(3)

    # Create a Chip object to run the example build.
    import picorv32_ram
    chip = picorv32_ram.build_top(remote=True)

    # Mock the _runstep method.
    old__runtask = chip._runtask
    def mocked_runtask(*args, **kwargs):
        if args[0] == 'import':
            old__runtask(*args)
        else:
            chip.logger.error('Non-import step run locally in remote job!')
    chip._runtask = Mock()
    chip._runtask.side_effect = mocked_runtask

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    os.environ['DISPLAY'] = ''

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost', 'port': 8090}))
    chip.set('option', 'remote', True)
    chip.set('option', 'credentials', os.path.abspath(tmp_creds))

    # Run the test remotely.
    chip.run()

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/picorv32_top/job0/export/0/outputs/picorv32_top.gds')
