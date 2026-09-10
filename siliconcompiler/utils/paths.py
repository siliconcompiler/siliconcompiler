import os.path

from typing import Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from siliconcompiler.project import Project
    from siliconcompiler.schema import BaseSchema


def cwdir(project: "Project") -> str:
    from siliconcompiler import Project
    if not isinstance(project, Project):
        raise TypeError("project must be a Project type")
    return project._Project__cwd


def cwdirsafe(project: "Project") -> str:
    """
    Returns the current working directory for the project, with safe fallback.

    This function attempts to retrieve the project's current working directory.
    If the provided object is not a valid Project instance, it falls back to
    the system's current working directory.

    Args:
        project (Project): The SiliconCompiler project object.

    Returns:
        str: The absolute path to the project's working directory, or the
        system's current working directory if the project is invalid.
    """
    try:
        return cwdir(project)
    except TypeError:
        return os.getcwd()


def builddir(project: "Project") -> str:
    """
    Returns the absolute path to the project's build directory.

    This directory is the root for all intermediate and final compilation
    artifacts. If a relative path is configured, it is resolved relative to the
    project's current working directory.

    Args:
        project (Project): The SiliconCompiler project object.

    Returns:
        str: The absolute path to the build directory.

    Raises:
        TypeError: If the provided project is not a valid Project object.
    """
    from siliconcompiler import Project
    if not isinstance(project, Project):
        raise TypeError("project must be a Project type")

    builddir: str = project.option.get_builddir()
    if os.path.isabs(builddir):
        return builddir

    return os.path.join(cwdir(project), builddir)


def jobdir(project: "Project") -> str:
    """
    Returns the absolute path to the current job directory.

    The directory structure is typically:
    `<build_dir>/<design_name>/<job_name>/`

    Args:
        project (Project): The SiliconCompiler project object.

    Returns:
        str: The absolute path to the job directory.

    Raises:
        TypeError: If the provided project is not a valid Project object.
        ValueError: If the project name has not been set.
    """
    from siliconcompiler import Project
    if not isinstance(project, Project):
        raise TypeError("project must be a Project type")

    if not project.name:
        raise ValueError("name has not been set")

    jobname: str = project.option.get_jobname()

    return os.path.join(builddir(project), project.name, jobname)


def workdir(project: "Project",
            step: Optional[str] = None,
            index: Optional[Union[int, str]] = None,
            relpath: Optional[bool] = False) -> str:
    """
    Returns path to the working directory for a given step and index.

    The directory structure is typically:
    `<build_dir>/<design_name>/<job_name>/<step>/<index>/`

    If `step` and `index` are not provided, this function returns the job
    directory. If `step` is provided but `index` is not, index '0' is assumed.

    Args:
        project (Project): The SiliconCompiler project object.
        step (str, optional): The name of the flowgraph step (e.g., 'syn',
            'place'). Defaults to None.
        index (Union[int, str], optional): The index of the task within the
            step. Defaults to '0' if step is specified.
        relpath (bool, optional): If True, returns a path relative to the
            project's current working directory. Otherwise, returns an absolute
            path. Defaults to False.

    Returns:
        str: The path to the specified working directory.

    Raises:
        TypeError: If the provided project is not a valid Project object.
        ValueError: If the project name has not been set.
    """

    dirlist = []
    if step is not None:
        dirlist.append(step)

        if index is None:
            index = '0'

        dirlist.append(str(index))

    path = os.path.join(jobdir(project), *dirlist)
    if relpath:
        return os.path.relpath(path, cwdir(project))

    return path


def collectiondir(project: "Project") -> Union[None, str]:
    """
    Returns the absolute path to the file collection directory.

    This directory is located within the job directory and is used to
    consolidate files marked for collection.

    Args:
        project (Project): The SiliconCompiler project object.

    Returns:
        str or None: The absolute path to the collected files directory, or
        None if the path cannot be resolved.
    """
    try:
        return os.path.join(jobdir(project), "sc_collected_files")
    except TypeError:
        return None


def cachedir(project: Optional[Union["Project", "BaseSchema"]]) -> str:
    """
    Returns the absolute path to the cache directory.

    This is the root of everything SiliconCompiler caches between runs, and it
    holds one subdirectory per kind of cached data: :func:`datarootdir` for
    resolved data sources and :func:`toolcachedir` for the caches tools keep for
    themselves. Cached data goes in those, never in the root itself.

    The location comes from :keypath:`option,cachedir` when it is set, and
    otherwise from ``~/.sc/cache``.

    Unlike the rest of this module, this accepts any schema and not only a
    :class:`.Project`: a data source resolves against whichever schema declared
    it, which is often a library rather than the project using it.

    Args:
        project (Project): The SiliconCompiler project object, or None to get
            the default location.

    Returns:
        str: The absolute path to the cache directory.
    """
    # siliconcompiler.utils imports this module, so this one cannot import it back
    # at module scope.
    from siliconcompiler.utils import default_cache_dir

    default_path = default_cache_dir()
    if not project:
        return default_path

    path = None
    if project.valid('option', 'cachedir'):
        path = project.get('option', 'cachedir')
        if path:
            path = project.find_files('option', 'cachedir', missing_ok=True)
            if not path:
                path = os.path.join(cwdirsafe(project), project.get('option', 'cachedir'))
    if not path:
        path = default_path

    return str(path)


def datarootdir(project: Optional[Union["Project", "BaseSchema"]]) -> str:
    """
    Returns the absolute path to the cached data source directory.

    Every :term:`dataroot` fetched from a git repository or a downloadable
    archive is extracted here, one directory per source and version. This is the
    area :mod:`siliconcompiler.package.cleanup` collects.

    Args:
        project (Project): The SiliconCompiler project object, or None to get
            the default location.

    Returns:
        str: The absolute path to the data source cache directory.
    """
    return os.path.join(cachedir(project), "dataroot")


def toolcachedir(project: Optional[Union["Project", "BaseSchema"]]) -> str:
    """
    Returns the absolute path to the tool cache directory.

    This is where a tool keeps whatever it carries from one run to the next --
    a compiler cache, an incremental build directory -- one subdirectory per
    tool, addressed by :attr:`.Task.cachedir`. It lives under
    :func:`cachedir` so that it inherits :keypath:`option,cachedir`, and so that
    it is inside the directory a task container gets mounted read-write.

    Nothing collects this directory: a tool that keeps a cache is expected to
    cap it itself, the way ccache does.

    Args:
        project (Project): The SiliconCompiler project object, or None to get
            the default location.

    Returns:
        str: The absolute path to the tool cache directory.
    """
    return os.path.join(cachedir(project), "tools")
