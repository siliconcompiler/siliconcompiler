"""
A collection of utility functions for discovering and selecting the correct
SiliconCompiler manifest file (`.pkg.json`) within a project directory.

This module provides logic to automatically find manifests based on a standard
build directory structure, and then select the most appropriate one based on
the project's configuration (design, jobname, step, index) or other clues.
"""
import os
import os.path

from typing import List, Dict, Optional

from siliconcompiler import Project


def manifest_switches() -> List[str]:
    """
    Returns a list of command-line switches used to identify a manifest.

    These switches correspond to project parameters that can specify a unique
    run or node within a project.

    Returns:
        list[str]: A list of command-line switch names.
    """
    return ['-design',
            '-cfg',
            '-arg_step',
            '-arg_index',
            '-jobname']


def _get_manifests(cwd: str) -> Dict:
    """
    Scans a directory tree to find all SiliconCompiler manifest files.

    This function walks through a standard SC build structure
    (`<builddir>/<design>/<jobname>/<step>/<index>`) to locate all
    `.pkg.json` files. It organizes them into a nested dictionary for
    easy lookup.

    Args:
        cwd (str): The current working directory to start the scan from.

    Returns:
        dict: A nested dictionary mapping:
              `{design: {jobname: {(step, index): /path/to/manifest.pkg.json}}}`.
              Top-level manifests are stored with a (None, None) key for the node.
    """
    manifests = {}

    def get_dirs(path):
        """Helper to get all subdirectories of a given path."""
        dirs = []
        if not os.path.isdir(path):
            return dirs
        for dirname in os.listdir(path):
            fullpath = os.path.join(path, dirname)
            if os.path.isdir(fullpath):
                dirs.append((dirname, fullpath))
        return dirs

    # Expected structure: <cwd>/<builddir>/<design>/<jobname>/<step>/<index>
    for _, buildpath in get_dirs(cwd):
        for design, designdir in get_dirs(buildpath):
            for jobname, jobdir in get_dirs(designdir):
                # Check for top-level manifest
                manifest = os.path.join(jobdir, f'{design}.pkg.json')
                if os.path.isfile(manifest):
                    manifests[(design, jobname, None, None)] = manifest
                # Check for node-level manifests
                for step, stepdir in get_dirs(jobdir):
                    for index, indexdir in get_dirs(stepdir):
                        # Check outputs first, then inputs
                        manifest = os.path.join(indexdir, 'outputs', f'{design}.pkg.json')
                        if os.path.isfile(manifest):
                            manifests[(design, jobname, step, index)] = manifest
                        else:
                            manifest = os.path.join(indexdir, 'inputs', f'{design}.pkg.json')
                            if os.path.isfile(manifest):
                                manifests[(design, jobname, step, index)] = manifest

    # Reorganize the flat list into a nested dictionary for easier access.
    organized_manifest = {}
    for (design, job, step, index), manifest in manifests.items():
        jobs = organized_manifest.setdefault(design, {})
        jobs.setdefault(job, {})[step, index] = os.path.abspath(manifest)

    return organized_manifest


def pick_manifest_from_file(cliproject: Project, src_file: Optional[str], all_manifests: Dict) \
        -> Optional[str]:
    """
    Tries to find a manifest located in the same directory as a given source file.

    This is useful for applications like a GUI where a user might open a single
    file from a larger project, and we need to infer the associated manifest.

    Args:
        cliproject (Project): The SiliconCompiler project object, used for logging.
        src_file (str): The path to the source file provided by the user.
        all_manifests (dict): A dictionary of all discovered manifests, typically
            from an internal discovery function like `_get_manifests`.

    Returns:
        str or None: The path to the found manifest, or None if no manifest
                     is found in the same directory.
    """
    if src_file is None:
        return None

    if not os.path.exists(src_file):
        cliproject.logger.error(f'{src_file} cannot be found.')
        return None

    src_dir = os.path.abspath(os.path.dirname(src_file))
    # Iterate through all discovered manifests to find one in the same directory.
    for _, jobs in all_manifests.items():
        for _, nodes in jobs.items():
            for manifest in nodes.values():
                if src_dir == os.path.dirname(manifest):
                    return manifest

    return None


def pick_manifest(cliproject: Project, src_file: Optional[str] = None) -> Optional[str]:
    """
    Selects the most appropriate manifest based on the project's configuration.

    This function implements the selection logic in the following order of priority:
    1. Find a manifest in the same directory as `src_file`, if provided.
    2. If the design is not set, try to infer it (only works if there is exactly one design).
    3. If the jobname is not set, try to infer it (only works if there is one job for the design).
    4. If step/index are specified, return the manifest for that specific node.
    5. If no node is specified, return the top-level manifest for the job.
    6. As a last resort, return the most recently modified manifest for the job.

    Args:
        cliproject (Project): The SiliconCompiler project object containing the configuration.
        src_file (str, optional): A path to a source file to help locate the
            manifest. Defaults to None.

    Returns:
        str or None: The absolute path to the selected manifest, or None if a
                     suitable manifest cannot be determined.
    """
    all_manifests = _get_manifests(os.getcwd())

    # 1. Try to find based on source file location.
    manifest = pick_manifest_from_file(cliproject, src_file, all_manifests)
    if manifest:
        return manifest

    # 2. Infer design if unset and only one option exists.
    if not cliproject.get("option", "design"):
        if len(all_manifests) == 1:
            cliproject.set("option", "design", list(all_manifests.keys())[0])
        else:
            cliproject.logger.error('Design name is not set and could not be inferred.')
            return None

    design = cliproject.get("option", "design")

    if design not in all_manifests:
        cliproject.logger.error(f'Could not find any manifests for design "{design}".')
        return None

    # 3. Infer jobname if unset and only one option exists for the design.
    jobname = cliproject.get('option', 'jobname')
    if jobname not in all_manifests[design] and \
            len(all_manifests[design]) != 1:
        cliproject.logger.error(f'Could not determine jobname for {design}')
        return None

    if jobname not in all_manifests[design]:
        jobname = list(all_manifests[design].keys())[0]

    # 4. Find specific node manifest if step/index are provided.
    step, index = cliproject.get('arg', 'step'), cliproject.get('arg', 'index')
    # Auto-complete index if only step is provided and a unique match is found.
    if step and not index:
        all_nodes = list(all_manifests[design][jobname].keys())
        try:
            all_nodes.remove((None, None))  # Exclude top-level manifest from search
        except ValueError:
            pass  # Top-level manifest might not exist
        for found_step, found_index in sorted(all_nodes):
            if found_step == step:
                index = found_index
                break  # Take the first matching index
        if index is None:
            index = '0'  # Default to '0' if no match is found

    if step and index:
        if (step, index) in all_manifests[design][jobname]:
            return all_manifests[design][jobname][(step, index)]
        else:
            cliproject.logger.error(f'Node "{step}/{index}" is not a valid node.')
            return None

    # 5. Return top-level job manifest if it exists.
    if (None, None) in all_manifests[design][jobname]:
        return all_manifests[design][jobname][(None, None)]

    # 6. Fallback: return the most recently modified manifest in the job.
    return list(sorted(all_manifests[design][jobname].values(),
                       key=lambda file: os.stat(file).st_ctime))[-1]
