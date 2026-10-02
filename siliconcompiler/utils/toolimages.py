"""
The tools sc-install builds, and their docker images.

The tools are SiliconCompiler's own, plus those installed packages add through a
``toolscripts`` entry point in the ``siliconcompiler.install`` group.

Every tool gets an image of its own, built on a shared builder image and tagged by a
hash of everything that goes into it, so an image is rebuilt only when one of its
inputs moves. sc_tools gathers them into the image the CI runs in.

SiliconCompiler's CI runs this as ``python3 -m siliconcompiler.utils.toolimages``.
A package that adds tools runs it with ``--image_prefix``: tags are then computed
over the manifest merged with the installed packages', every image whose tag
matches SiliconCompiler's is reused from SiliconCompiler's registry, and the rest
are built under the prefix.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import sys

from pathlib import Path
from typing import Dict, Optional, Tuple

from siliconcompiler import __version__
from siliconcompiler import utils
from siliconcompiler.utils import get_plugins


_docker_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'data', 'docker')
# docker-extra-files in _tools.json are relative to this
_data_path = os.path.dirname(_docker_path)
# The images are built on this OS, so its install scripts are the ones they run
_os_name = 'ubuntu24'
# Sourced by every install script, so it has to travel into the image with them
# and feed the tool image tag the same way the install script itself does.
_prereqs_script = '_prereqs.sh'

_registry = 'ghcr.io'
_sc_prefix = 'siliconcompiler/sc_'

# The per-image exceptions to the build-only sweep, declared by the tool that
# knows them. A tool built FROM another tool's image prunes and sweeps that
# tool's files as well as its own, so the base's exceptions have to travel with
# it -- the whole chain is unioned here rather than repeated by hand in every
# dependent's entry.
_SWEEP_FIELDS = ('docker-keep-pkgs', 'docker-drop-pkgs', 'docker-prune-dirs')


def get_tool_script_dir() -> Path:
    return Path(__file__).parent.parent / "toolscripts"


def get_install_tools(osname: Optional[str], tools_root: Optional[Path] = None) -> Dict[str, str]:
    if tools_root is None:
        tools_root = get_tool_script_dir()

    script_dir = None
    if osname:
        script_dir = tools_root / osname
        if not script_dir.exists():
            script_dir = None

    tools = {}
    if script_dir:
        for script in glob.glob(str(script_dir / "install-*.sh")):
            tool = re.match(r"install-(.*)\.sh", os.path.basename(script).lower())
            if tool:
                tools[tool.group(1)] = script

    return tools


def get_package_tools(osname: Optional[str]) -> Tuple[Dict[str, dict], Dict[str, str]]:
    """
    Collect the pins and install scripts from the ``toolscripts`` directories packages
    register, each laid out like SiliconCompiler's own: ``_tools.json`` beside one
    directory of ``install-<tool>.sh`` per OS.

    Parameters:
        osname (Optional[str]): OS identifier whose install scripts are collected.

    Returns:
        tuple: The packages' ``_tools.json`` entries, and their install scripts by tool.

    Raises:
        ValueError: if an entry point returns something that is not a directory, a
            ``_tools.json`` does not parse, or two packages supply the same tool.
    """
    pins = {}
    scripts = {}
    owners = {}
    for plugin in get_plugins("install", name="toolscripts"):
        root = Path(plugin())
        if not root.is_dir():
            raise ValueError(f"toolscripts entry point returned {root}, which is not a directory")

        package_pins = {}
        manifest = root / "_tools.json"
        if manifest.exists():
            try:
                with open(manifest) as f:
                    package_pins = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"{manifest} is not valid JSON: {e}") from e
        package_scripts = get_install_tools(osname, root)

        for tool in sorted({*package_pins, *package_scripts}):
            if tool in owners:
                raise ValueError(f"{tool} is supplied by both {owners[tool]} and {root}")
            owners[tool] = root

        pins.update(package_pins)
        scripts.update(package_scripts)

    return pins, scripts


def get_tools_manifest(osname: Optional[str]) -> Dict[str, dict]:
    """
    SiliconCompiler's ``_tools.json`` with the packages' entries applied on top. An
    entry for a tool SiliconCompiler pins changes only the fields it names.

    Parameters:
        osname (Optional[str]): OS identifier whose package install scripts are
            checked for conflicts, see :func:`get_package_tools`.
    """
    with open(get_tool_script_dir() / "_tools.json") as f:
        manifest = json.load(f)

    pins, _ = get_package_tools(osname)
    for tool, fields in pins.items():
        manifest[tool] = {**manifest.get(tool, {}), **fields}
    return manifest


def get_file_hash(f):
    '''
    Returns the sha1 hex digest for the content of the input file (f)
    '''
    with open(f, 'r') as f:
        hash = hashlib.sha1(f.read().encode('utf-8'))
        return hash.hexdigest()
    raise FileExistsError(f'Unable to process {f}')


def check_image(image_name):
    '''
    Check if image is available

    Only a registry that says the image is not there counts as absent. Anything else
    -- a 401 from credentials that cannot read it, a registry that is down -- is
    raised, since reading it as absent would start a rebuild of everything.
    '''
    # Imported here rather than at module scope, so sc-install reading the manifest
    # does not load the docker SDK.
    import docker

    client = docker.from_env()
    try:
        client.images.get_registry_data(image_name)
        return True
    except docker.errors.NotFound:
        pass
    except docker.errors.NullResource:
        pass

    try:
        client.images.get(image_name)
        return True
    except docker.errors.ImageNotFound:
        pass

    return False


def base_image_details():
    '''
    Details about the base builder image
    '''
    docker_file = os.path.join(_docker_path, 'toolbase.docker')
    return 'sc_tool_builder', get_file_hash(docker_file), docker_file


def assemble_docker_file(name, tag, template, options, output_dir, copy_files=None):
    '''
    Generate a Dockerfile based on the provided template, and return its directory
    '''

    print(f'Generating: {name}:{tag}')
    tool_template = utils.get_file_template(os.path.abspath(template))

    if not tool_template:
        raise FileNotFoundError('Template file is missing')

    docker_dir = os.path.join(output_dir, name)
    shutil.rmtree(docker_dir, ignore_errors=True)
    os.makedirs(docker_dir, exist_ok=True)

    with open(os.path.join(docker_dir, 'Dockerfile'), 'w') as f:
        f.write(tool_template.render(options))

    if copy_files:
        for cp_file in copy_files:
            if os.path.isdir(cp_file):
                shutil.copytree(cp_file, os.path.join(docker_dir, os.path.basename(cp_file)))
            else:
                shutil.copy2(cp_file, docker_dir)

    return docker_dir


class ToolImages:
    '''
    The images of one manifest's tools.

    Args:
        manifest (dict): the _tools.json to build from.
        scripts (dict): the install script of each tool.
        registry (str): registry holding the images.
        prefix (str): namespace and name prefix of the tool images,
            ``siliconcompiler/sc_`` for SiliconCompiler's own.
        tools_filter (list): tools to include in sc_tools, default is all.
        base (ToolImages): SiliconCompiler's images, reused for every tool whose
            image would be built here exactly as it is there.
    '''

    def __init__(self, manifest, scripts, registry=_registry, prefix=_sc_prefix,
                 tools_filter=None, base=None):
        self.manifest = manifest
        self.scripts = scripts
        self.registry = registry
        self.namespace, self.name_prefix = prefix.rsplit('/', 1)
        self.tools_filter = tools_filter or []
        self.base = base

    def get_field(self, tool, field):
        return self.manifest[tool].get(field)

    def get_tools(self):
        return list(self.manifest.keys())

    def get_image_name(self, name, tag, is_check_image, namespace=None):
        '''
        Returns the image name with tag
        '''
        if is_check_image:
            tag = f"sc-check-{tag}"

        image_name = f'{namespace or self.namespace}/{name}:{tag}'
        if self.registry:
            image_name = f'{self.registry}/{image_name}'
        return image_name

    def builder_image(self, is_check_image):
        '''
        The builder image, which is always SiliconCompiler's
        '''
        if self.base:
            return self.base.builder_image(is_check_image)
        name, tag, _ = base_image_details()
        return self.get_image_name(name, tag, is_check_image, namespace='siliconcompiler')

    def tool_image_details(self, tool):
        '''
        Details about the tool builder image
        '''
        docker_file = os.path.join(_docker_path, 'tool.docker')

        tag = self.get_field(tool, 'git-commit')
        if not tag:
            tag = self.get_field(tool, 'version')
        if not tag:
            raise ValueError(f'{tool} does not have a valid tag')

        return f'{self.name_prefix}{tool}', tag, docker_file

    def is_reused(self, tool):
        '''
        True when SiliconCompiler builds this tool's image exactly as it would be built
        here, so its image is taken from SiliconCompiler's registry.
        '''
        if not self.base or tool not in self.base.manifest or tool not in self.base.scripts:
            return False
        return self.base.get_tool_image_check_tag(tool) == self.get_tool_image_check_tag(tool)

    def tool_image(self, tool, is_check_image):
        '''
        Returns the image name of a tool, with its version or its hash as the tag
        '''
        if self.is_reused(tool):
            return self.base.tool_image(tool, is_check_image)

        name, version, _ = self.tool_image_details(tool)
        if is_check_image:
            return self.get_image_name(name, self.get_tool_image_check_tag(tool), True)
        return self.get_image_name(name, version, False)

    def tools_image_details(self, tools, tools_versions):
        '''
        Details about the sc_tools image, which contains all the tools
        '''
        docker_file = os.path.join(_docker_path, 'sc_tools.docker')

        hash = hashlib.sha1()
        for tool in sorted(tools):
            hash.update(tool.encode('utf-8'))
        for tool, version in tools_versions:
            hash.update(version.encode('utf-8'))
        hash.update(get_file_hash(docker_file).encode('utf-8'))
        # sc_tools.docker copies _prereqs.sh in and runs the docker-skip install
        # scripts that source it, so it is a build input of this image too.
        prereqs_file = os.path.join(get_tool_script_dir(), _prereqs_script)
        if os.path.exists(prereqs_file):
            hash.update(get_file_hash(prereqs_file).encode('utf-8'))

        return f'{self.name_prefix}tools', hash.hexdigest(), docker_file

    def _get_sweep_field(self, tool, field):
        values = []
        for name in [tool] + self._get_docker_depends(tool):
            entries = self.get_field(name, field)
            if entries:
                values.extend(entries)

        # Deduplicated, order preserved: the same package can be named by a tool and
        # by the tool it is built on.
        return list(dict.fromkeys(values))

    def _get_docker_depends(self, tool):
        depends = self.get_field(tool, 'docker-depends')
        if not depends:
            return []
        if isinstance(depends, str):
            depends = [depends]

        chain = []
        for depend in depends:
            chain.append(depend)
            chain.extend(self._get_docker_depends(depend))
        return chain

    def _write_manifest(self, docker_dir):
        # The install scripts read their pins through the _tools.py next to this, so it
        # is the merged manifest that travels, overrides included.
        with open(os.path.join(docker_dir, '_tools.json'), 'w') as f:
            f.write(json.dumps(self.manifest, indent=2))

    def make_tool_docker(self, tool, output_dir):
        '''
        Generate the tool builder dockerfile
        '''
        name, tag, docker_file = self.tool_image_details(tool)

        extracmds = self.get_field(tool, 'docker-cmds')
        if extracmds:
            extracmds = '\n'.join(extracmds)
        else:
            extracmds = ''

        depends = self.get_field(tool, 'docker-depends')
        if not depends:
            depends = []
        if isinstance(depends, str):
            depends = [depends]

        template_opts = {
            'tool': tool,
            'base_build_image': self.builder_image(False),
            'install_script': f'install-{tool}.sh',
            'extra_commands': extracmds,
            'depends_tools': [self.tool_image(depend, True) for depend in depends],
            # Another tool builds against this prefix, so leave its symbols alone.
            # The dependent copies this prefix in and strips it there, which is what
            # reaches sc_tools, so nothing ships unstripped either way.
            'strip_symbols': not self._is_build_input(tool),
            'keep_pkgs': ' '.join(self._get_sweep_field(tool, 'docker-keep-pkgs')),
            'drop_pkgs': ' '.join(self._get_sweep_field(tool, 'docker-drop-pkgs')),
            'prune_dirs': ' '.join(self._get_sweep_field(tool, 'docker-prune-dirs'))
        }

        copy_files = []
        docker_extra_files = self.get_field(tool, 'docker-extra-files')
        if docker_extra_files:
            for extra_file in docker_extra_files:
                copy_files.append(os.path.join(_data_path, extra_file))

        copy_files.extend([
            os.path.join(get_tool_script_dir(), '_tools.py'),
            os.path.join(get_tool_script_dir(), _prereqs_script),
            self.scripts[tool]])
        docker_dir = assemble_docker_file(name, tag, docker_file, template_opts, output_dir,
                                          copy_files=copy_files)
        self._write_manifest(docker_dir)

    def overrides_sc_tool(self):
        '''
        True when the pin or the recipe of one of SiliconCompiler's tools is changed
        here. The old version's files would then survive underneath anything layered
        over sc_tools, so the image of every tool is assembled the way sc_tools is.
        '''
        if not self.base:
            return False
        return any(self.manifest.get(tool) != fields or
                   self.scripts.get(tool) != self.base.scripts.get(tool)
                   for tool, fields in self.base.manifest.items())

    def _layers_on_sc_tools(self):
        return self.base is not None and not self.overrides_sc_tool()

    def _get_layered_images(self):
        return [self.tool_image(tool, True) for tool, _ in self.get_built_tools()]

    def _tools_image_details(self):
        if self._layers_on_sc_tools():
            docker_file = os.path.join(_docker_path, 'tools_extend.docker')
            hash = hashlib.sha1()
            hash.update(self.base.tools_image(False).encode('utf-8'))
            for image in sorted(self._get_layered_images()):
                hash.update(image.encode('utf-8'))
            hash.update(get_file_hash(docker_file).encode('utf-8'))
            return f'{self.name_prefix}tools', hash.hexdigest(), docker_file

        return self.tools_image_details(self._get_tool_images(), self._get_tool_versions())

    def tools_image(self, is_check_image):
        '''
        Returns the image name of the image holding every tool.

        SiliconCompiler's is sc_tools. A package's is sc_tools itself when it builds
        nothing, sc_tools with the package's images layered on when it only adds
        tools, and otherwise assembled from every tool's image as sc_tools is.
        '''
        if self._layers_on_sc_tools() and not self.get_built_tools():
            return self.base.tools_image(is_check_image)

        name, tag, _ = self._tools_image_details()
        return self.get_image_name(name, tag, is_check_image)

    def make_tools_docker(self, output_dir):
        '''
        Generate the dockerfile of the image holding every tool, when there is one
        to build here
        '''
        if self._layers_on_sc_tools():
            if self.get_built_tools():
                name, tag, docker_file = self._tools_image_details()
                template_opts = {
                    'sc_tools_image': self.base.tools_image(False),
                    'tools': self._get_layered_images()
                }
                assemble_docker_file(name, tag, docker_file, template_opts, output_dir)
            return

        tools = self._get_tool_images()
        name, tag, docker_file = self.tools_image_details(tools, self._get_tool_versions())

        skip_build = []
        for tool in self.get_tools():
            if self.tools_filter and tool not in self.tools_filter:
                continue
            if self.get_field(tool, 'docker-skip'):
                skip_build.append(tool)

        template_opts = {
            'tools': tools,
            'skip_build': skip_build
        }

        if not self.tools_filter or "slurm" in self.tools_filter:
            template_opts['slurm_version'] = self.get_field('slurm', 'version')

        copy_files = [
            os.path.join(get_tool_script_dir(), '_tools.py'),
            os.path.join(get_tool_script_dir(), _prereqs_script)]
        for tool in skip_build:
            copy_files.append(self.scripts[tool])

        docker_dir = assemble_docker_file(name, tag, docker_file, template_opts, output_dir,
                                          copy_files=copy_files)
        self._write_manifest(docker_dir)

    def make_sc_runner_docker(self, output_dir):
        '''
        Generate sc_runner dockerfile, which is sc_tools with SiliconCompiler installed
        '''
        _, sc_tools_tag, _ = self.tools_image_details(self._get_tool_images(),
                                                      self._get_tool_versions())
        template_opts = {
            'release_version': f'v{__version__}',
            'sc_tools_build_image': self.get_image_name('sc_tools', sc_tools_tag, False),
        }

        docker_file = os.path.join(_docker_path, 'sc_runner.docker')
        assemble_docker_file('sc_runner', f'v{__version__}', docker_file, template_opts,
                             output_dir)

    def _get_tools(self, allow_skip=False):
        '''
        Helper function to provide a list of tools
        '''
        tools = []
        for tool in self.get_tools():
            if self.tools_filter and tool not in self.tools_filter:
                continue
            if tool not in self.scripts:
                continue
            if allow_skip or not self.get_field(tool, 'docker-skip'):
                tools.append((tool, self.get_field(tool, 'docker-depends')))
        return tools

    def get_built_tools(self):
        '''
        The tools whose images are built here rather than taken from SiliconCompiler
        '''
        return [(tool, depends) for tool, depends in self._get_tools()
                if not self.is_reused(tool)]

    def _is_build_input(self, tool):
        '''
        True when another tool declares this one in docker-depends, which makes this
        image a build input rather than only a shipping artifact.

        Deliberately independent of --include_tools: whether an image is safe to
        strip is a property of the tool graph, not of which subset is being built,
        and making it vary with the filter would let a filtered build produce a
        differently-stripped image under the same tag.
        '''
        for other in self.get_tools():
            depends = self.get_field(other, 'docker-depends')
            if not depends:
                continue
            if isinstance(depends, str):
                depends = [depends]
            if tool in depends:
                return True

        return False

    def _get_subsumed_tools(self):
        '''
        Tools whose install prefix is already carried by another tool's image, and
        which therefore do not need copying into sc_tools on their own.

        tool.docker copies a dependency's whole $SC_PREFIX into the dependent before
        building it, and installs the dependency's apt.txt there too, so sc_soda's
        image contains everything sc_mlir installed and sc_nextpnr's contains
        icepack -- prefix and packages both.

        Copying the dependency into sc_tools as well is not merely redundant. COPY
        never deletes at the destination, so if a dependent prunes what it inherited
        (soda drops the LLVM/MLIR dev tree once soda-opt has linked against it) an
        unpruned copy of the dependency landing first would survive underneath the
        pruned one and the prune would save nothing.

        A dependency is only subsumed when a dependent is actually being copied.
        Under --include_tools the dependent may be filtered out, and then the
        dependency has to carry itself.
        '''
        copied = {tool for tool, _ in self._get_tools()}

        subsumed = set()
        for _, depends in self._get_tools():
            if not depends:
                continue
            if isinstance(depends, str):
                depends = [depends]
            for depend in depends:
                if depend in copied:
                    subsumed.add(depend)

        return subsumed

    def _get_tool_images(self):
        '''
        Returns the image names that sc_tools needs to copy, which excludes any tool
        already carried by a dependent's image.
        '''
        subsumed = self._get_subsumed_tools()
        return [self.tool_image(tool, True) for tool, _ in self._get_tools()
                if tool not in subsumed]

    def _get_tool_versions(self):
        '''
        Returns the version of every tool, the docker-skip ones included
        '''
        tool_versions = []
        for tool_name, _ in self._get_tools(allow_skip=True):
            version = self.get_field(tool_name, 'git-commit')
            if not version:
                version = self.get_field(tool_name, 'version')
            if not version:
                continue
            tool_versions.append((tool_name, version))

        return tool_versions

    def get_tool_image_check_tag(self, tool):
        _, builder_tag, _ = base_image_details()

        _, tool_tag, tools_file = self.tool_image_details(tool)
        hash = hashlib.sha1()
        hash.update(builder_tag.encode('utf-8'))
        hash.update(get_file_hash(tools_file).encode('utf-8'))
        hash.update(tool_tag.encode('utf-8'))
        if tool in self.scripts:
            hash.update(get_file_hash(self.scripts[tool]).encode('utf-8'))
        prereqs_file = os.path.join(get_tool_script_dir(), _prereqs_script)
        if os.path.exists(prereqs_file):
            hash.update(get_file_hash(prereqs_file).encode('utf-8'))
        cmds = self.get_field(tool, 'docker-cmds')
        if cmds:
            for cmd in cmds:
                hash.update(cmd.encode('utf-8'))

        # Only this tool's own entries: the dependency chain's are folded in by the
        # depends_hash at the end, which already covers everything a base tool
        # contributes to this image.
        for field in _SWEEP_FIELDS:
            entries = self.get_field(tool, field)
            if entries:
                for entry in entries:
                    hash.update(f'{field}:{entry}'.encode('utf-8'))

        # Whether this image gets stripped depends on the tool graph around it, not
        # only on this tool's own inputs, so a tool gaining or losing a dependent
        # has to invalidate its image.
        hash.update(str(self._is_build_input(tool)).encode('utf-8'))

        extra_files = self.get_field(tool, 'docker-extra-files')
        if extra_files:
            for extra_file in extra_files:
                path = os.path.join(_data_path, extra_file)
                files = []
                if os.path.isdir(path):
                    for file in os.listdir(path):
                        file = os.path.join(path, file)
                        if os.path.isfile(file):
                            files.append(file)
                else:
                    files = [path]

                for file in sorted(files):
                    hash.update(get_file_hash(file).encode('utf-8'))

        depends_on = self.get_field(tool, 'docker-depends')
        if depends_on:
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            for depend in depends_on:
                depends_hash = self.get_tool_image_check_tag(depend)
                hash.update(depends_hash.encode('utf-8'))

        return hash.hexdigest()

    def images(self):
        '''
        The builder, tool, sc_tools and sc_runner images, by name
        '''
        builder_name, _, _ = base_image_details()
        images = {
            "builder": {
                'tool': "builder",
                'name': self.builder_image(False),
                'check_name': self.builder_image(True),
                'builder_name': None
            }
        }

        for tool, _ in self._get_tools():
            images[tool] = {
                'tool': tool,
                'name': self.tool_image(tool, False),
                'check_name': self.tool_image(tool, True),
                'builder_name': builder_name
            }

        images['tools'] = {
            'tool': "tools",
            'name': self.tools_image(False),
            'check_name': self.tools_image(True),
            'builder_name': None
        }
        images['runner'] = {
            'tool': "runner",
            'name': self.get_image_name('sc_runner', f'v{__version__}', False),
            'check_name': self.get_image_name('sc_runner', f'v{__version__}', True),
            'builder_name': None
        }
        return images


def _load_manifest():
    with open(os.path.join(get_tool_script_dir(), '_tools.json')) as f:
        return json.load(f)


def get_tool_images(registry=_registry, prefix=None, tools_filter=None):
    '''
    Returns SiliconCompiler's tool images, or with a prefix those of the manifest
    merged with the installed packages', built under that prefix in the given registry
    wherever they cannot be taken from SiliconCompiler's, which stay in its own.
    '''
    scripts = get_install_tools(_os_name)
    sc_images = ToolImages(_load_manifest(), scripts,
                           registry=_registry if prefix else registry,
                           tools_filter=None if prefix else tools_filter)
    if not prefix:
        return sc_images

    _, package_scripts = get_package_tools(_os_name)
    return ToolImages(get_tools_manifest(_os_name),
                      {**scripts, **package_scripts},
                      registry=registry, prefix=prefix, tools_filter=tools_filter,
                      base=sc_images)


def main():
    parser = argparse.ArgumentParser('SC Docker Builder')
    parser.add_argument('--registry',
                        default=_registry,
                        metavar='registry',
                        help='Registry holding the docker images; with --image_prefix, '
                             'the one the built images go to, while SiliconCompiler\'s are '
                             f'still taken from {_registry}')

    parser.add_argument('--image_prefix',
                        metavar='prefix',
                        help='Build the tools installed packages add or override, as images '
                             'named <registry>/<prefix><tool>; every other image is '
                             'SiliconCompiler\'s')

    parser.add_argument('--check_image',
                        metavar='image_name',
                        help='Check if a particular image is available')

    parser.add_argument('--tool',
                        metavar='tool_name',
                        help='Image name for a particular tool')
    parser.add_argument('--tool_as_hash_name',
                        action='store_true',
                        help='Return the image name with the hash instead of version')

    parser.add_argument('--all_tool_images',
                        action='store_true',
                        help='Return the image names for all the tools, separated by spaces, '
                             'regardless of build state')

    parser.add_argument('--include_tools',
                        nargs='+',
                        metavar='<tool>',
                        help='Tools to include in the final sc_tools image, default is all')

    parser.add_argument('--json_tools',
                        action='store_true',
                        help='Generate a JSON string with the tools that need to be built')
    parser.add_argument('--reportall',
                        action='store_true',
                        help='Report all images regardless of build state')
    parser.add_argument('--with_dependencies',
                        action='store_true',
                        help='Include tools which depend on other tools')

    parser.add_argument('--plan',
                        action='store_true',
                        help='List the images that are built, the images of '
                             'SiliconCompiler\'s they are built from, and the image of '
                             'every tool')

    parser.add_argument('--generate_files',
                        action='store_true',
                        help='Generate all available Dockerfiles')
    parser.add_argument('--output_dir',
                        default='docker',
                        metavar='dir',
                        help='Output directory to write the dockerfiles to')

    args = parser.parse_args()

    images = get_tool_images(registry=args.registry, prefix=args.image_prefix,
                             tools_filter=args.include_tools)
    if args.include_tools:
        all_tools = images.get_tools()
        for tool in args.include_tools:
            if tool not in all_tools:
                print(f'{tool} is not a valid tool. Valid tools are: {", ".join(all_tools)}')
                return 1

    # A package builds only the images it changes, and the image of every tool
    # from them; sc_runner stays SiliconCompiler's.
    built_tools = images.get_built_tools()
    if args.image_prefix and (args.all_tool_images or args.tool == 'runner'):
        print('sc_runner is only built for SiliconCompiler itself')
        return 1

    if args.json_tools:
        image_info = images.images()
        json_tools = {'include': []}
        for tool, depends in built_tools:
            if (not depends and not args.with_dependencies) or (depends and args.with_dependencies):
                tool_info = image_info[tool]
                if args.reportall or not check_image(tool_info['check_name']):
                    json_tools['include'].append(tool_info)
        if len(json_tools['include']) == 0:
            print(json.dumps({}))
        else:
            print(json.dumps(json_tools))
        return 0

    if args.all_tool_images:
        print(' '.join([images.tool_image(tool, False) for tool, _ in images._get_tools()]))
        return 0

    if args.check_image:
        if check_image(args.check_image):
            print('true')
        else:
            print('false')
        return 0

    if args.tool:
        image_info = images.images()
        if args.tool not in image_info:
            print(f'{args.tool} has no image')
            return 1
        key = 'check_name' if args.tool_as_hash_name else 'name'
        print(image_info[args.tool][key])
        return 0

    if args.plan:
        reused = []
        for tool, depends in built_tools:
            print(f'build  {tool:<16} {images.tool_image(tool, True)}')
            for depend in images._get_docker_depends(tool):
                if images.is_reused(depend) and depend not in reused:
                    reused.append(depend)
        for tool in reused:
            print(f'reuse  {tool:<16} {images.tool_image(tool, True)}')

        if not args.image_prefix or images.overrides_sc_tool():
            how = 'assembled'
        elif built_tools:
            how = 'layered'
        else:
            how = 'sc_tools'
        print(f'tools  {how:<16} {images.tools_image(False)}')
        return 0

    if args.generate_files:
        if not args.image_prefix:
            name, tag, docker_file = base_image_details()
            assemble_docker_file(name, tag, docker_file, {}, args.output_dir)

        for tool, _ in built_tools:
            images.make_tool_docker(tool, args.output_dir)

        images.make_tools_docker(args.output_dir)
        if not args.image_prefix and not args.include_tools:
            images.make_sc_runner_docker(args.output_dir)
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
