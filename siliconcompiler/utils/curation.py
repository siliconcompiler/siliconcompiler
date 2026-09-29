import shutil
import tarfile

import os.path

from typing import List, Optional, TYPE_CHECKING, Tuple

from siliconcompiler.schema import BaseSchema, Parameter
from siliconcompiler.schema.parametervalue import NodeListValue, NodeSetValue
from siliconcompiler.utils import FilterDirectories
from siliconcompiler.utils.paths import collectiondir, cwdir
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.flowgraph import RuntimeFlowgraph

if TYPE_CHECKING:
    from siliconcompiler.project import Project


CollectionKey = Tuple[Tuple[str, ...], Optional[str], Optional[str]]


def filter_collection_keys(keys: List[CollectionKey]) -> List[CollectionKey]:
    """Remove schema entries that must never be included in a collection."""
    filtered_keys = []
    for key, step, index in keys:
        if 'default' in key or key[0] == 'history':
            continue
        if key in (('option', 'builddir'), ('option', 'cachedir'),
                   ('option', 'credentials')):
            continue
        if (len(key) >= 5 and key[0] == 'tool' and key[2] == 'task'
                and key[4] in ('input', 'report', 'output')):
            continue
        filtered_keys.append((key, step, index))
    return filtered_keys


def _is_within(path: str, root: str) -> bool:
    """True if path is root or anything under it."""
    return path == root or path.startswith(root + os.sep)


def collect(project: "Project",
            keys: List[CollectionKey],
            directory: Optional[str] = None,
            verbose: bool = True,
            whitelist: Optional[List[str]] = None) -> None:
    '''
    Collects the specified files and directories into a collection directory.

    Each file or directory is stored once. A value naming one the collection
    already holds, directly or inside a directory, gets a link to that copy at its
    own collected path: a symbolic link, or where one cannot be made, a hard link
    or a copy.

    Args:
        keys (List[Tuple[Tuple[str, ...], Optional[str], Optional[str]]]):
            Path parameter keypaths and their flowgraph step and index to collect.
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
    if not directory:
        raise ValueError("unable to determine collection directory")

    directory = os.path.abspath(directory)

    # Move existing directory
    prev_dir = None
    if os.path.exists(directory):
        prev_dir = os.path.join(os.path.dirname(directory), "sc_previous_collection")
        os.rename(directory, prev_dir)
    os.makedirs(directory)

    if verbose:
        project.logger.info(f'Collecting files to: {directory}')

    cwd = cwdir(project)

    def find_files(*key, step: Optional[str] = None, index: Optional[str] = None):
        """
        Find the files in the filesystem, otherwise look in previous collection
        """
        e = None
        try:
            return BaseSchema._find_files(project, *key, step=step, index=index,
                                          cwd=cwd,
                                          collection_dir=directory)
        except FileNotFoundError as err:
            e = err
        if prev_dir:
            # Try previous location next
            return BaseSchema._find_files(project, *key, step=step, index=index,
                                          cwd=cwd,
                                          collection_dir=prev_dir)
        if e:
            raise e

    dirs = {}
    files = {}

    for key, step, index in keys:
        param: Parameter = project.get(*key, field=None)

        if not param.is_path:
            continue

        values = None
        for candidate, candidate_step, candidate_index in param.getvalues(return_values=False):
            if candidate_step == step and candidate_index == index:
                values = candidate
                break
        if values is None or not values.has_value:
            continue

        if isinstance(values, (NodeSetValue, NodeListValue)):
            values = values.values
        else:
            values = [values]

        if param.is_directory:
            dirs[(key, step, index)] = values
        else:
            files[(key, step, index)] = values

    def resolve(params):
        """
        Pair each value with the real path of what it names, in path order, so a
        directory comes before anything inside it
        """
        found = []
        for key, step, index in sorted(params.keys()):
            abs_paths = find_files(*key, step=step, index=index)

            if not isinstance(abs_paths, (list, tuple, set)):
                abs_paths = [abs_paths]

            for abs_path, value in zip(abs_paths, params[(key, step, index)]):
                if not abs_path:
                    raise FileNotFoundError(f"{value.get()} could not be copied")
                found.append((os.path.realpath(abs_path), abs_path, value))
        return sorted(found, key=lambda f: f[0])

    def found_in_collection(value) -> bool:
        """
        True if the value already resolves in the collection by its own path
        """
        try:
            path = value.resolve_path(search=[], collection_dir=directory)
        except FileNotFoundError:
            return False
        return path is not None and _is_within(path, directory)

    # Real path of each file or directory copied in -> where its copy is
    stored = {}

    def find_stored(real_path: str) -> Optional[str]:
        """
        Where the collection already holds real_path, as itself or inside a
        directory it holds
        """
        if real_path in stored:
            return stored[real_path]
        source = real_path
        while os.path.dirname(source) != source:
            source = os.path.dirname(source)
            if source in stored:
                copy = os.path.join(stored[source], os.path.relpath(real_path, source))
                if os.path.exists(copy):
                    return copy
        return None

    symlinks = True

    def link(copy: str, import_path: str) -> None:
        """
        Name copy, already in the collection, at import_path too
        """
        nonlocal symlinks
        os.makedirs(os.path.dirname(import_path), exist_ok=True)
        is_dir = os.path.isdir(copy)
        if symlinks:
            try:
                os.symlink(os.path.relpath(copy, os.path.dirname(import_path)), import_path,
                           target_is_directory=is_dir)
                return
            except OSError:
                # Windows needs a privilege most users lack to make one
                symlinks = False
        if is_dir:
            shutil.copytree(copy, import_path)
            return
        try:
            os.link(copy, import_path)
        except OSError:
            shutil.copy2(copy, import_path)

    try:
        path_filter = FilterDirectories(project)
        # Directories first, so that a file inside one is found there
        for is_dir, params in ((True, dirs), (False, files)):
            for real_path, abs_path, value in resolve(params):
                if _is_within(abs_path, directory) or found_in_collection(value):
                    continue

                import_path = os.path.join(
                    directory,
                    value.generate_hashed_collection_path(value.get(), value.get('dataroot')))

                copy = find_stored(real_path)
                if copy:
                    link(copy, import_path)
                    continue

                if is_dir:
                    if whitelist is not None and abs_path not in whitelist:
                        raise RuntimeError(
                            f'{abs_path} is not on the approved collection list.')

                    if verbose:
                        project.logger.info(f"  Collecting directory: {abs_path}")
                    path_filter.abspath = abs_path
                    os.makedirs(os.path.dirname(import_path), exist_ok=True)
                    shutil.copytree(abs_path, import_path, ignore=path_filter.filter)
                    path_filter.abspath = None
                else:
                    if verbose:
                        project.logger.info(f"  Collecting file: {abs_path}")
                    os.makedirs(os.path.dirname(import_path), exist_ok=True)
                    shutil.copy2(abs_path, import_path)
                stored[real_path] = import_path
    finally:
        if prev_dir:
            # Delete existing directory
            shutil.rmtree(prev_dir)


def archive(project: "Project",
            jobname: Optional[str] = None,
            include: Optional[List[str]] = None,
            archive_name: Optional[str] = None) -> None:
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
        jobname = project.option.get_jobname()
    if jobname not in histories:
        org_job = jobname
        jobname = histories[0]
        project.logger.warning(f"{org_job} not found in history, picking {jobname}")

    history = project.history(jobname)

    flow = None
    try:
        flow = history.get_flow()
    except KeyError:
        pass

    if flow:
        flowgraph_nodes = RuntimeFlowgraph(
            flow,
            from_steps=history.option.get_from(),
            to_steps=history.option.get_to(),
            prune_nodes=history.option.get_prune()).get_nodes()
    else:
        flowgraph_nodes = []

    if not archive_name:
        archive_name = f"{history.name}_{jobname}.tgz"

    project.logger.info(f'Creating archive {archive_name}...')

    with tarfile.open(archive_name, "w:gz") as tar:
        for step, index in flowgraph_nodes:
            SchedulerNode(history, step, index).archive(tar, include, True)
