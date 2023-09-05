import siliconcompiler

import os
import pytest
import subprocess


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
                 step='place', index='0')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None
    assert gcd_chip.find_result('gds', step='export') is None

    # Fix place step and re-run
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.40',
                 step='place', index='0')
    gcd_chip.set('option', 'resume', True)
    gcd_chip.run()

    # Ensure floorplan did not get re-run
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) == old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is not None
    assert gcd_chip.find_result('gds', step='export') is not None

@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume_remote(gcd_chip, unused_tcp_port):
    '''Test that jobs can be resumed on a remote server.
    '''

    # Start running an sc-server instance.
    os.mkdir('local_server_work')
    srv_proc = subprocess.Popen(['sc-server',
                                 '-port', str(unused_tcp_port),
                                 '-nfs_mount', './local_server_work',
                                 '-cluster', 'local'])

    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
                 step='place', index='0')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None
    assert gcd_chip.find_result('gds', step='export') is None

    # Fix place step and re-run remotely.
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.40',
                 step='place', index='0')
    gcd_chip.set('option', 'remote', True)
    gcd_chip.set('option', 'resume', True)
    gcd_chip.run()

    # Kill the server process.
    srv_proc.kill()

    # Ensure flow finished successfully
    assert os.path.isfile('build/gcd/job0/place/0/outputs/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.pkg.json')
