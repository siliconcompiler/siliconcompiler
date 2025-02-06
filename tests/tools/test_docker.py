from siliconcompiler import Chip, SiliconCompilerError
from siliconcompiler import __version__
import os
import glob
import docker
import pytest
import sys
from siliconcompiler.targets import asic_demo


@pytest.fixture
def docker_image(scroot):
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

    return image[0].id


@pytest.mark.docker
@pytest.mark.timeout(300)
@pytest.mark.quick
@pytest.mark.skipif(sys.platform != 'linux', reason='Not supported in testing')
def test_docker_run(docker_image, capfd):
    chip = Chip('test')
    chip.use(asic_demo)

    chip.set('option', 'scheduler', 'name', 'docker')
    chip.set('option', 'scheduler', 'queue', docker_image)
    chip.set('option', 'to', 'floorplan.init')

    assert chip.run()

    assert os.path.isfile(f'{chip.getworkdir()}/heartbeat.pkg.json')
    assert os.path.isfile(
        f'{chip.getworkdir(step="floorplan.init", index="0")}/outputs/heartbeat.odb')

    output = capfd.readouterr()
    assert "Running in docker container:" in output.out
    assert output.out.count("Running in docker container:") == 3


@pytest.mark.docker
@pytest.mark.timeout(600)
@pytest.mark.quick
@pytest.mark.skipif(sys.platform != 'linux', reason='Not supported in testing')
def test_docker_run_with_failure(docker_image, capfd):
    chip = Chip('test')
    chip.use(asic_demo)

    chip.set('option', 'scheduler', 'name', 'docker')
    chip.set('option', 'scheduler', 'queue', docker_image)
    chip.set('option', 'to', 'place.repair_design')
    chip.set('tool', 'openroad', 'task', 'global_placement', 'var', 'place_density', 'asdf',
             step='place.global', index='0')

    with pytest.raises(SiliconCompilerError):
        chip.run(raise_exception=True)

    assert not os.path.isfile(f'{chip.getworkdir()}/heartbeat.pkg.json')
    assert len(glob.glob(f'{chip.getworkdir()}/sc_issue*')) == 1
    assert os.path.isfile(
        f'{chip.getworkdir(step="floorplan.init", index="0")}/outputs/heartbeat.odb')
    assert not os.path.isfile(
        f'{chip.getworkdir(step="place.global", index="0")}/outputs/heartbeat.odb')

    output = capfd.readouterr()
    assert "Running in docker container:" in output.out
    assert output.out.count("Running in docker container:") == 8

    assert "| ERROR   | job0 | place.repair_design  | 0 | " not in output.out
