from siliconcompiler import Chip
from siliconcompiler import __version__
import os
import docker
import pytest
import sys


@pytest.mark.docker
@pytest.mark.timeout(300)
@pytest.mark.skipif(sys.platform != 'linux', reason='Not supported yet')
def test_docker_run(monkeypatch, scroot, capfd):
    # Build image for test
    buildargs = {
        'SC_VERSION': __version__
    }
    scimage = os.getenv('SC_IMAGE', None)
    if scimage:
        buildargs['SC_IMAGE'] = scimage

    client = docker.from_env()
    image = client.images.build(
        path=scroot,
        buildargs=buildargs,
        dockerfile=f'{scroot}/setup/docker/sc_local_runner.docker')

    monkeypatch.setenv('SC_DOCKER_IMAGE', image[0].id)

    chip = Chip('test')
    chip.load_target('asic_demo')

    chip.set('option', 'scheduler', 'name', 'docker')
    chip.set('option', 'to', 'floorplan')

    chip.run()

    assert os.path.isfile(f'{chip._getworkdir()}/heartbeat.pkg.json')
    assert os.path.isfile(f'{chip._getworkdir(step="floorplan", index="0")}/outputs/heartbeat.odb')

    output = capfd.readouterr()
    assert "Running in docker container:" in output.out
    assert output.out.count("Running in docker container:") == 3
