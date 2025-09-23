import os.path

from typing import Union


def builddir(project) -> str:
    """
    Returns the absolute path to the project's build directory.

    This directory is the root for all intermediate and final compilation
    artifacts.

    Returns:
        str: The absolute path to the build directory.
    """
    from siliconcompiler import Project
    if not isinstance(project, Project):
        raise TypeError("project must be a Project type")

    builddir = project.get('option', 'builddir')
    if os.path.isabs(builddir):
        return builddir

    return os.path.join(project._Project__cwd, builddir)


def jobdir(project) -> str:
    """
    Returns the absolute path to the job directory.

    The directory structure is typically:
    `<build_dir>/<design_name>/<job_name>/`
    """
    from siliconcompiler import Project
    if not isinstance(project, Project):
        raise TypeError("project must be a Project type")

    if not project.name:
        raise ValueError("name has not been set")

    return os.path.join(
        builddir(project),
        project.name,
        project.get('option', 'jobname'))


def workdir(project, step: str = None, index: Union[int, str] = None, relpath: bool = False) -> str:
    """
    Returns the absolute path to the working directory for a given
    step and index within the project's job structure.

    The directory structure is typically:
    `<build_dir>/<design_name>/<job_name>/<step>/<index>/`

    If `step` and `index` are not provided, the job directory is returned.
    If `step` is provided but `index` is not, index '0' is assumed.

    Args:
        step (str, optional): The name of the flowgraph step (e.g., 'syn', 'place').
                                Defaults to None.
        index (Union[int, str], optional): The index of the task within the step.
                                            Defaults to None (implies '0' if step is set).

    Returns:
        str: The absolute path to the specified working directory.

    Raises:
        ValueError: If the design name is not set in the project.
    """

    dirlist = []
    if step is not None:
        dirlist.append(step)

        if index is None:
            index = '0'

        dirlist.append(str(index))

    path = os.path.join(jobdir(project), *dirlist)
    if relpath:
        return os.path.relpath(path, project._Project__cwd)

    return path


def collectiondir(project) -> str:
    """
    Returns the absolute path to the directory where collected files are stored.

    This directory is typically located within the project's working directory
    and is used to consolidate files marked for collection.

    Returns:
        str: The absolute path to the collected files directory.
    """
    try:
        return os.path.join(jobdir(project), "sc_collected_files")
    except TypeError:
        return None
