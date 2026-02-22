import docker
import os
import shlex
import sys

import docker.errors

from pathlib import Path

import siliconcompiler

from siliconcompiler.package import RemoteResolver
from siliconcompiler.utils import default_email_credentials_file
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.utils.logging import SCBlankLoggerFormatter


def get_image(project, step, index) -> str:
    """Determines the Docker image to use for a given node.

    The image is selected based on the following priority:
    1. The value of ['option', 'scheduler', 'queue'] specific to the step/index.
    2. The value of the 'SC_DOCKER_IMAGE' environment variable.
    3. A default image name constructed as 'ghcr.io/siliconcompiler/sc_runner:v<version>'.

    Args:
        project (Project): The project object.
        step (str): The step name of the node.
        index (str): The index of the node.

    Returns:
        str: The name of the Docker image to use.
    """
    from siliconcompiler import __version__

    queue = project.option.scheduler.get_queue(step=step, index=index)
    if queue:
        return queue

    return os.getenv(
        'SC_DOCKER_IMAGE',
        f'ghcr.io/siliconcompiler/sc_runner:v{__version__}')


def get_volumes_directories(project, cache_dir, workdir, step, index):
    """
    Identifies and categorizes all host directories that need to be mounted
    into the Docker container.

    This function scans the project schema for all file and directory paths,
    collects them, and then prunes the list to a minimal set of parent
    directories to mount. It then separates these directories into read-write
    (RW) and read-only (RO) sets.

    Args:
        project (Project): The project object.
        cache_dir (str): The path to the cache directory.
        workdir (str): The path to the node's working directory.
        step (str): The step name of the current node.
        index (str): The index of the current node.

    Returns:
        tuple: A tuple containing two sets: (rw_volumes, ro_volumes).
            `rw_volumes` is a set of Path objects for read-write directories.
            `ro_volumes` is a set of Path objects for read-only directories.
    """
    all_dirs = set()
    # Collect files
    for key in project.allkeys():
        sc_type = project.get(*key, field='type')

        if 'file' in sc_type or 'dir' in sc_type:
            cstep = step
            cindex = index

            if project.get(*key, field='pernode').is_never():
                cstep = None
                cindex = None

            files = project.find_files(*key, step=cstep, index=cindex, missing_ok=True)
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
    # for resolver in project.get('package', field="schema").get_resolvers().values():
    #     all_dirs.add(resolver())

    all_dirs = [
        Path(cache_dir),
        Path(workdir),
        Path(siliconcompiler.__file__).parent,
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

    builddir = project.find_files('option', 'builddir')

    rw_volumes = set()

    for path in pruned_dirs:
        for rw_allow in (Path(builddir), Path(workdir), Path(cache_dir)):
            if path == rw_allow or path in rw_allow.parents:
                rw_volumes.add(path)

    ro_volumes = pruned_dirs.difference(rw_volumes)

    return rw_volumes, ro_volumes


class DockerSchedulerNode(SchedulerNode):
    """A SchedulerNode implementation for running tasks in a Docker container.

    This class extends the base SchedulerNode to handle the specifics of
    running a compilation step inside a Docker container. It uses the `docker-py`
    library to manage the container lifecycle, including pulling the image,

    mounting volumes, and executing the command.
    """

    def __init__(self, project, step, index, replay=False):
        """Initializes a DockerSchedulerNode.

        Args:
            project (Project): The parent Project object.
            step (str): The step name in the flowgraph.
            index (str): The index for the step.
            replay (bool): If True, sets up the node to replay a previous run.
        """
        super().__init__(project, step, index, replay=replay)

        self.__queue = get_image(self.project, self.step, self.index)

    @property
    def queue(self):
        """str: The Docker image name to be used for the container."""
        return self.__queue

    @staticmethod
    def init(project):
        """
        A static pre-processing hook for the Docker scheduler.

        Args:
            project (Project): The project object to perform pre-processing on.
        """
        try:
            client = docker.from_env()
            client.version()
        except (docker.errors.DockerException, docker.errors.APIError):
            raise RuntimeError('docker is not available or installed on this machine')

    def mark_copy(self) -> bool:
        if sys.platform != 'win32':
            return False

        do_collect = False
        for key in self.get_required_path_keys():
            self.project.set(*key, True, field='copy')
            do_collect = True
        return do_collect

    def run(self):
        """
        Runs the node's task inside a Docker container.

        This method orchestrates the entire process:
        1. Connects to the Docker daemon.
        2. Pulls the required Docker image if it's not present locally.
        3. Determines and prepares all necessary volume mounts.
        4. Creates and starts a detached Docker container.
        5. Writes the current manifest to a file accessible by the container.
        6. Executes the `sc-node` command inside the container.
        7. Streams the container's log output to the console.
        8. Halts on error and ensures the container is stopped upon completion.
        """
        self._init_run_logger()

        client = docker.from_env()

        is_windows = sys.platform == 'win32'

        workdir = self.jobworkdir
        start_cwd = os.getcwd()

        # Change working directory since the run may delete this folder
        os.makedirs(workdir, exist_ok=True)
        os.chdir(workdir)

        image_name = get_image(self.project, self.step, self.index)

        # Pull image if needed
        try:
            image = client.images.get(image_name)
        except docker.errors.ImageNotFound:
            # Needs a lock to avoid downloading a bunch in parallel
            image_repo, image_tag = image_name.split(':')
            self.logger.info(f'Pulling docker image {image_name}')
            try:
                image = client.images.pull(image_repo, tag=image_tag)
            except docker.errors.APIError as e:
                self.logger.error(f'Unable to pull image: {e}')
                image_src = image_repo.split('/')[0]
                self.logger.error(f"  if you are logged into {image_src} with expired credentials, "
                                  f"please use 'docker logout {image_src}'")
                self.halt()

        email_file = default_email_credentials_file()
        if is_windows:
            # Hack to get around manifest merging
            self.project.option.set_cachedir(None)
            cache_dir = '/sc_cache'
            cwd = '/sc_docker'
            builddir = f'{cwd}/build'

            local_cfg = os.path.join(start_cwd, 'sc_docker.json')
            cfg = f'{builddir}/{self.name}/{self.jobname}/{self.step}/{self.index}/sc_docker.json'

            user = None

            volumes = [
                f"{self.project_cwd}:{cwd}:rw",
                f"{RemoteResolver.determine_cache_dir(self.project)}:{cache_dir}:rw"
            ]
            self.logger.debug(f'Volumes: {volumes}')

            env = {}

            if os.path.exists(email_file):
                env["HOME"] = "/sc_home"

                volumes.append(f'{os.path.dirname(email_file)}:/sc_home/.sc:ro')
        else:
            cache_dir = RemoteResolver.determine_cache_dir(self.project)
            cwd = self.project_cwd
            builddir = self.project.find_files('option', 'builddir')

            local_cfg = os.path.abspath('sc_docker.json')
            cfg = local_cfg

            user = os.getuid()

            rw_volumes, ro_volumes = get_volumes_directories(
                self.project, cache_dir, workdir, self.step, self.index)
            volumes = [
                *[
                    f'{path}:{path}:rw' for path in rw_volumes
                ],
                *[
                    f'{path}:{path}:ro' for path in ro_volumes
                ]
            ]
            self.logger.debug(f'Read write volumes: {rw_volumes}')
            self.logger.debug(f'Read only volumes: {ro_volumes}')

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
                    f"sc_node:{self.name}:{self.step}:{self.index}"
                ],
                user=user,
                detach=True,
                tty=True,
                auto_remove=True,
                environment=env)

            # Write manifest to make it available to the docker runner
            self.project.write_manifest(local_cfg)

            cachemap = []
            # for package, resolver in self.project.get(
            #         'package', field="schema").get_resolvers().items():
            #     cachemap.append(f'{package}:{resolver()}')

            self.logger.info('Running in docker container: '
                             f'{container.name} ({container.short_id})')
            args = [
                '-cfg', cfg,
                '-cwd', cwd,
                '-builddir', str(builddir),
                '-cachedir', str(cache_dir),
                '-step', self.step,
                '-index', self.index,
                '-unset_scheduler'
            ]
            if not is_windows and cachemap:
                args.append('-cachemap')
                args.extend(cachemap)
            cmd = f'python3 -m siliconcompiler.scheduler.run_node {shlex.join(args)}'
            exec_handle = client.api.exec_create(container.name, cmd)
            stream = client.api.exec_start(exec_handle, stream=True)

            # Print the log
            org_formatter = self.project._logger_console.formatter
            try:
                self.project._logger_console.setFormatter(SCBlankLoggerFormatter())
                for chunk in stream:
                    for line in chunk.decode().splitlines():
                        self.logger.info(line)
            finally:
                self.project._logger_console.setFormatter(org_formatter)

            if client.api.exec_inspect(exec_handle['Id']).get('ExitCode') != 0:
                self.halt()
        finally:
            # Ensure we clean up containers
            if container:
                try:
                    container.stop()
                except docker.errors.APIError:
                    self.logger.error(f'Failed to stop docker container: {container.name}')

        # Restore working directory
        os.chdir(start_cwd)

    def check_required_paths(self) -> bool:
        return True
