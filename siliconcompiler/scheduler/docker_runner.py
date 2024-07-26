import docker
import os
from siliconcompiler.package import get_cache_path
from siliconcompiler.package import _path as sc_path
from siliconcompiler.utils import default_email_credentials_file
from pathlib import Path
import sys


def get_image(chip, step, index):
    from siliconcompiler import __version__

    queue = chip.get('option', 'scheduler', 'queue', step=step, index=index)
    if queue:
        return queue

    return os.getenv(
        'SC_DOCKER_IMAGE',
        f'ghcr.io/siliconcompiler/sc_runner:v{__version__}')


def get_volumes_directories(chip, cache_dir, workdir, step, index):
    all_dirs = set()
    # Collect files
    for key in chip.allkeys():
        sc_type = chip.get(*key, field='type')

        if 'file' in sc_type or 'dir' in sc_type:
            cstep = step
            cindex = index

            if 'never' in chip.get(*key, field='pernode'):
                cstep = None
                cindex = None

            files = chip.find_files(*key, step=cstep, index=cindex, missing_ok=True)
            if files:
                if not isinstance(files, list):
                    files = [files]
                for path in files:
                    if path is None:
                        continue
                    if 'file' in sc_type:
                        all_dirs.add(os.path.dirname(path))
                    else:
                        all_dirs.add(path)

    # Collect caches
    for package in chip.getkeys('package', 'source'):
        all_dirs.add(sc_path(chip, package, None))

    all_dirs = [
        Path(cache_dir),
        Path(workdir),
        Path(chip.scroot),
        *[Path(path) for path in all_dirs]]

    pruned_dirs = all_dirs.copy()
    for base_path in all_dirs:
        if base_path not in pruned_dirs:
            continue

        new_pruned_dirs = [base_path]
        for check_path in pruned_dirs:
            if base_path == check_path:
                continue

            if base_path not in check_path.parents:
                new_pruned_dirs.append(check_path)
        pruned_dirs = new_pruned_dirs

    pruned_dirs = set(pruned_dirs)

    builddir = chip.find_files('option', 'builddir')

    rw_volumes = set()

    for path in pruned_dirs:
        for rw_allow in (Path(builddir), Path(workdir), Path(cache_dir)):
            if path == rw_allow or path in rw_allow.parents:
                rw_volumes.add(path)

    ro_volumes = pruned_dirs.difference(rw_volumes)

    return rw_volumes, ro_volumes


def init(chip):
    if sys.platform == 'win32':
        # this avoids the issue of different file system types
        chip.logger.error('Setting copy field to true for docker run on Windows')
        for key in chip.allkeys():
            if key[0] == 'history':
                continue
            sc_type = chip.get(*key, field='type')
            if 'dir' in sc_type or 'file' in sc_type:
                chip.set(*key, True, field='copy')
        chip.collect()


def run(chip, step, index, replay):
    # Import here to avoid circular import
    from siliconcompiler.scheduler import _haltstep

    try:
        client = docker.from_env()
        client.version()
    except (docker.errors.DockerException, docker.errors.APIError) as e:
        chip.logger.error(f'Unable to connect to docker: {e}')
        _haltstep(chip, chip.get('option', 'flow'), step, index)

    is_windows = sys.platform == 'win32'

    workdir = chip.getworkdir()
    start_cwd = os.getcwd()

    # Remove handlers from logger
    chip.logger.handlers.clear()

    # Reinit logger
    chip._init_logger(step=step, index=index, in_run=True)

    # Change working directory since the run may delete this folder
    os.chdir(workdir)

    image_name = get_image(chip, step, index)

    # Pull image if needed
    try:
        image = client.images.get(image_name)
    except docker.errors.ImageNotFound:
        # Needs a lock to avoid downloading a bunch in parallel
        image_repo, image_tag = image_name.split(':')
        chip.logger.info(f'Pulling docker image {image_name}')
        try:
            image = client.images.pull(image_repo, tag=image_tag)
        except docker.errors.APIError as e:
            chip.logger.error(f'Unable to pull image: {e}')
            image_src = image_repo.split('/')[0]
            chip.logger.error(f"  if you are logged into {image_src} with expired credentials, "
                              f"please use 'docker logout {image_src}'")
            _haltstep(chip, chip.get('option', 'flow'), step, index)

    email_file = default_email_credentials_file()
    if is_windows:
        # Hack to get around manifest merging
        chip.set('option', 'cachedir', None)
        cache_dir = '/sc_cache'
        cwd = '/sc_docker'
        builddir = f'{cwd}/build'

        local_cfg = os.path.join(start_cwd, 'sc_docker.json')
        job = chip.get('option', 'jobname')
        cfg = f'{builddir}/{chip.design}/{job}/{step}/{index}/sc_docker.json'

        user = None

        volumes = [
            f"{chip.cwd}:{cwd}:rw",
            f"{get_cache_path(chip)}:{cache_dir}:rw"
        ]
        chip.logger.debug(f'Volumes: {volumes}')

        env = {}

        if os.path.exists(email_file):
            env["HOME"] = "/sc_home"

            volumes.append(f'{os.path.dirname(email_file)}:/sc_home/.sc:ro')
    else:
        cache_dir = get_cache_path(chip)
        cwd = chip.cwd
        builddir = chip.find_files('option', 'builddir')

        local_cfg = os.path.abspath('sc_docker.json')
        cfg = local_cfg

        user = os.getuid()

        rw_volumes, ro_volumes = get_volumes_directories(chip, cache_dir, workdir, step, index)
        volumes = [
            *[
                f'{path}:{path}:rw' for path in rw_volumes
            ],
            *[
                f'{path}:{path}:ro' for path in ro_volumes
            ]
        ]
        chip.logger.debug(f'Read write volumes: {rw_volumes}')
        chip.logger.debug(f'Read only volumes: {ro_volumes}')

        env = {}
        if os.path.exists(email_file):
            env["HOME"] = "/sc_home"

            volumes.append(f'{os.path.dirname(email_file)}:/sc_home/.sc:ro')

    container = None
    try:
        container = client.containers.run(
            image.id,
            volumes=volumes,
            labels=[
                "siliconcompiler",
                f"sc_node:{chip.design}:{step}{index}"
            ],
            user=user,
            detach=True,
            tty=True,
            auto_remove=True,
            environment=env)

        # Write manifest to make it available to the docker runner
        chip.write_manifest(local_cfg)

        cachemap = []
        for package in chip.getkeys('package', 'source'):
            cachemap.append(f'{package}:{sc_path(chip, package, None)}')

        chip.logger.info(f'Running in docker container: {container.name} ({container.short_id})')
        args = [
            '-cfg', cfg,
            '-cwd', cwd,
            '-builddir', builddir,
            '-cachedir', cache_dir,
            '-step', step,
            '-index', index,
            '-unset_scheduler'
        ]
        if not is_windows and cachemap:
            args.append('-cachemap')
            args.append(' '.join(cachemap))
        cmd = f'python3 -m siliconcompiler.scheduler.run_node {" ".join(args)}'
        exec_handle = client.api.exec_create(container.name, cmd)
        stream = client.api.exec_start(exec_handle, stream=True)

        # Print the log
        for chunk in stream:
            for line in chunk.decode().splitlines():
                print(line)

        if client.api.exec_inspect(exec_handle['Id']).get('ExitCode') != 0:
            _haltstep(chip, chip.get('option', 'flow'), step, index, log=False)
    finally:
        # Ensure we clean up containers
        if container:
            try:
                container.stop()
            except docker.errors.APIError:
                chip.logger.error('Failed to stop docker container')

    # Restore working directory
    os.chdir(start_cwd)
