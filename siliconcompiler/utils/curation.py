import shutil
import tarfile

import os.path

from typing import List

from siliconcompiler.schema.parametervalue import NodeListValue, NodeSetValue
from siliconcompiler.utils import FilterDirectories
from siliconcompiler.utils.paths import collectiondir
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.flowgraph import RuntimeFlowgraph


def collect(project,
            directory: str = None,
            verbose: bool = True,
            whitelist: List[str] = None):
    '''
    Collects files and directories specified in the schema and places
    them in a collection directory. The function only copies items that have
    the 'copy' field set to True in their schema definition.

    Args:
        directory (str, optional): The output directory for collected files.
            Defaults to the path from :meth:`.collectiondir`.
        verbose (bool): If True, logs information about each collected file/directory.
            Defaults to True.
        whitelist (List[str], optional): A list of absolute paths that are
            allowed to be collected. If an item to be collected is not on this list,
            a `RuntimeError` is raised. Defaults to None.

    Raises:
        RuntimeError: If a file or directory to be collected is not in the `whitelist`.
        FileNotFoundError: If a specified file or directory cannot be found.
    '''
    from siliconcompiler import Project
    if not isinstance(project, Project):
        raise TypeError("project must be a Project")

    if not directory:
        directory = collectiondir(project)
    directory = os.path.abspath(directory)

    # Remove existing directory
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)

    if verbose:
        project.logger.info(f'Collecting files to: {directory}')

    dirs = {}
    files = {}

    for key in project.allkeys():
        if key[0] == 'history':
            # skip history
            continue

        # Skip runtime directories
        if key == ('option', 'builddir'):
            # skip builddir
            continue
        if key == ('option', 'cachedir'):
            # skip cache
            continue

        if key[0] == 'tool' and key[2] == 'task' and key[4] in ('input',
                                                                'report',
                                                                'output'):
            # skip flow files files from builds
            continue

        leaftype = project.get(*key, field='type')
        is_dir = "dir" in leaftype
        is_file = "file" in leaftype

        if not is_dir and not is_file:
            continue

        if not project.get(*key, field='copy'):
            continue

        for values, step, index in project.get(*key, field=None).getvalues(return_values=False):
            if not values.has_value:
                continue

            if isinstance(values, (NodeSetValue, NodeListValue)):
                values = values.values
            else:
                values = [values]

            if is_dir:
                dirs[(key, step, index)] = values
            else:
                files[(key, step, index)] = values

    path_filter = FilterDirectories(project)
    for key, step, index in sorted(dirs.keys()):
        abs_paths = project.find_files(*key, step=step, index=index)

        new_paths = set()

        if not isinstance(abs_paths, (list, tuple, set)):
            abs_paths = [abs_paths]

        abs_paths = zip(abs_paths, dirs[(key, step, index)])
        abs_paths = sorted(abs_paths, key=lambda p: p[0])

        for abs_path, value in abs_paths:
            if not abs_path:
                raise FileNotFoundError(f"{value.get()} could not be copied")

            if abs_path.startswith(directory):
                # File already imported in directory
                continue

            imported = False
            for new_path in new_paths:
                if abs_path.startwith(new_path):
                    imported = True
                    break
            if imported:
                continue

            new_paths.add(abs_path)

            import_path = os.path.join(directory, value.get_hashed_filename())
            if os.path.exists(import_path):
                continue

            if whitelist is not None and abs_path not in whitelist:
                raise RuntimeError(f'{abs_path} is not on the approved collection list.')

            if verbose:
                project.logger.info(f"  Collecting directory: {abs_path}")
            path_filter.abspath = abs_path
            shutil.copytree(abs_path, import_path, ignore=path_filter.filter)
            path_filter.abspath = None

    for key, step, index in sorted(files.keys()):
        abs_paths = project.find_files(*key, step=step, index=index)

        if not isinstance(abs_paths, (list, tuple, set)):
            abs_paths = [abs_paths]

        abs_paths = zip(abs_paths, files[(key, step, index)])
        abs_paths = sorted(abs_paths, key=lambda p: p[0])

        for abs_path, value in abs_paths:
            if not abs_path:
                raise FileNotFoundError(f"{value.get()} could not be copied")

            if abs_path.startswith(directory):
                # File already imported in directory
                continue

            import_path = os.path.join(directory, value.get_hashed_filename())
            if os.path.exists(import_path):
                continue

            if verbose:
                project.logger.info(f"  Collecting file: {abs_path}")
            shutil.copy2(abs_path, import_path)


def archive(project, jobname: str = None, include: List[str] = None, archive_name: str = None):
    '''Archive a job directory into a compressed tarball.

    Creates a single compressed archive (.tgz) based on the specified job.
    By default, only outputs, reports, log files, and the final manifest
    are archived.

    Args:
        jobname (str, optional): The job to archive. By default, archives the job specified
            in :keypath:`option,jobname`.
        include (List[str], optional): Overrides default inclusion rules. Accepts a list of glob
            patterns matched from the root of individual step/index directories.
            To capture all files, supply `["*"]`.
        archive_name (str, optional): The path to the output archive file. Defaults to
            `<design>_<jobname>.tgz`.
    '''
    from siliconcompiler import Project
    if not isinstance(project, Project):
        raise TypeError("project must be a Project")

    histories = project.getkeys("history")
    if not histories:
        raise ValueError("no history to archive")

    if jobname is None:
        jobname = project.get("option", "jobname")
    if jobname not in histories:
        org_job = jobname
        jobname = histories[0]
        project.logger.warning(f"{org_job} not found in history, picking {jobname}")

    history = project.history(jobname)

    flow = history.get('option', 'flow')
    flowgraph_nodes = RuntimeFlowgraph(
        history.get("flowgraph", flow, field='schema'),
        from_steps=history.get('option', 'from'),
        to_steps=history.get('option', 'to'),
        prune_nodes=history.get('option', 'prune')).get_nodes()

    if not archive_name:
        archive_name = f"{history.name}_{jobname}.tgz"

    project.logger.info(f'Creating archive {archive_name}...')

    with tarfile.open(archive_name, "w:gz") as tar:
        for step, index in flowgraph_nodes:
            SchedulerNode(history, step, index).archive(tar, include, True)
