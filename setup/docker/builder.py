#!/usr/bin/env python3

import os

import argparse
import docker
import hashlib
import json
import shutil
import requests
from siliconcompiler import __version__
from siliconcompiler import utils
# Import tools which contains all the version information
from siliconcompiler.toolscripts import _tools


_file_path = os.path.dirname(__file__)
_builder_path = os.path.abspath(os.path.join(_file_path, '..'))
_tools_path = os.path.abspath(
    os.path.join(_file_path, '..', '..', 'siliconcompiler', 'toolscripts'))
_install_script_path = os.path.join(_tools_path, 'ubuntu20')


_registry = 'ghcr.io'
_images = {}
_tools_filter = []


# Image information methods
def base_image_details():
    '''
    Details about the base builder image
    '''
    docker_file = os.path.join(_file_path, 'toolbase.docker')
    return 'sc_tool_builder', get_file_hash(docker_file), docker_file


def tool_image_details(tool):
    '''
    Details about the tool builder image
    '''
    docker_file = os.path.join(_file_path, 'tool.docker')

    tag = _tools.get_field(tool, 'git-commit')
    if not tag:
        tag = _tools.get_field(tool, 'version')
    if not tag:
        raise ValueError(f'{tool} does not have a valid tag')

    return f'sc_{tool}', tag, docker_file


def tools_image_details(tools, tools_versions):
    '''
    Details about the sc_tools image, which contains all the tools
    '''
    docker_file = os.path.join(_file_path, 'sc_tools.docker')

    hash = hashlib.sha1()
    for tool in sorted(tools):
        hash.update(tool.encode('utf-8'))
    for tool, version in tools_versions:
        hash.update(version.encode('utf-8'))
    hash.update(get_file_hash(docker_file).encode('utf-8'))

    return 'sc_tools', hash.hexdigest(), docker_file


def check_image(image_name):
    '''
    Check if image is available
    '''
    client = docker.from_env()
    try:
        client.images.get_registry_data(image_name)
        return True
    except docker.errors.NotFound:
        pass
    except docker.errors.NullResource:
        pass
    except requests.exceptions.HTTPError:
        pass

    try:
        docker.from_env().images.get(image_name)
        return True
    except docker.errors.ImageNotFound:
        pass

    return False


def get_file_hash(f):
    '''
    Returns the sha1 hex digest for the content of the input file (f)
    '''
    with open(f, 'r') as f:
        hash = hashlib.sha1(f.read().encode('utf-8'))
        return hash.hexdigest()
    raise FileExistsError(f'Unable to process {f}')


def get_image_name(name, tag, is_check_image):
    '''
    Returns the image name with tag
    '''
    if is_check_image:
        tag = f"sc-check-{tag}"

    image_name = f'siliconcompiler/{name}:{tag}'
    if _registry:
        image_name = f'{_registry}/{image_name}'
    return image_name


def assemble_docker_file(name, tag, template, options, output_dir, copy_files=None):
    '''
    Generate a Dockerfile based on the provided template
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


def make_base_tool_docker(output_dir):
    '''
    Generate the base tool builder dockerfile
    '''
    name, tag, docker_file = base_image_details()
    assemble_docker_file(name, tag, docker_file, {}, output_dir)


def make_tool_docker(tool, output_dir, reference_tool=None):
    '''
    Generate the tool builder dockerfile
    '''
    if not _tools.has_tool(tool):
        print(f'{tool} not supported')
        return

    base_name, base_tag, _ = base_image_details()
    is_check = False
    if reference_tool:
        base_name, _, _ = tool_image_details(reference_tool)
        base_tag = _get_tool_image_check_tag(reference_tool)
        is_check = True

    name, tag, docker_file = tool_image_details(tool)

    extracmds = _tools.get_field(tool, 'docker-cmds')
    if extracmds:
        extracmds = '\n'.join(extracmds)
    else:
        extracmds = ''
    template_opts = {
        'tool': tool,
        'base_build_image': get_image_name(base_name, base_tag, is_check),
        'install_script': f'install-{tool}.sh',
        'extra_commands': extracmds
    }

    docker_extra_files = _tools.get_field(tool, 'docker-extra-files')
    copy_files = []
    if docker_extra_files:
        for extra_file in docker_extra_files:
            copy_files.append(os.path.join(_builder_path, extra_file))

    for f in (os.path.join(_tools_path, '_tools.json'),
              os.path.join(_tools_path, '_tools.py'),
              os.path.join(_install_script_path, template_opts['install_script'])):
        copy_files.append(os.path.join(_tools_path, f))
    assemble_docker_file(name, tag, docker_file, template_opts, output_dir, copy_files=copy_files)


def make_sc_tools_docker(tools, tools_version, output_dir):
    '''
    Generate sc_tools dockerfile which contains all the tools
    '''

    name, tag, docker_file = tools_image_details(tools, tools_version)

    skip_build = []
    for tool in _tools.get_tools():
        if _tools_filter and tool not in _tools_filter:
            continue
        if _tools.get_field(tool, 'docker-skip'):
            skip_build.append(tool)

    template_opts = {
        'tools': tools,
        'skip_build': skip_build
    }

    if not _tools_filter or (_tools_filter and "slurm" in _tools_filter):
        template_opts['slurm_version'] = _tools.get_field('slurm', 'version')

    copy_files = [
        os.path.join(_tools_path, '_tools.json'),
        os.path.join(_tools_path, '_tools.py')]
    for tool in skip_build:
        copy_files.append(os.path.join(_install_script_path, f'install-{tool}.sh'))
    cp_files = []
    for f in copy_files:
        cp_files.append(os.path.join(_tools_path, f))

    assemble_docker_file(name, tag, docker_file, template_opts, output_dir, copy_files=cp_files)


def make_sc_runner_docker(sc_tools_version, output_dir):
    '''
    Generate sc_tools dockerfile which contains all the tools
    '''

    template_opts = {
        'release_version': f'v{__version__}',
        'sc_tools_build_image': get_image_name('sc_tools', sc_tools_version, False),
    }

    docker_file = os.path.join(_file_path, 'sc_runner.docker')
    assemble_docker_file('sc_runner', f'v{__version__}', docker_file, template_opts, output_dir)


def build_docker(docker_file, image_name):
    '''
    Helper function to build the input docker image
    '''
    container_limits = {'cpusetcpus': '0'}
    cpus = int(os.cpu_count() / 2) - 1
    if cpus > 1:
        container_limits = {'cpusetcpus': f'0-{cpus}'}

    client = docker.from_env()
    try:
        client.images.build(path=os.path.dirname(docker_file),
                            tag=image_name,
                            dockerfile=os.path.basename(docker_file),
                            container_limits=container_limits)
    except Exception as e:
        print(f'Failed to build {image_name}: {e}')


def _get_tools(allow_skip=False):
    '''
    Helper function to provide a list of tools
    '''
    tools = []
    for tool in _tools.get_tools():
        if _tools_filter and tool not in _tools_filter:
            continue
        if not os.path.exists(os.path.join(_install_script_path, f'install-{tool}.sh')):
            continue
        if allow_skip or not _tools.get_field(tool, 'docker-skip'):
            tools.append((tool, _tools.get_field(tool, 'docker-depends')))
    return tools


def _get_tool_images(tool=None):
    '''
    Returns the image name for a tool.
    If tool is not provided, return all image names in a dict
    '''
    tool_images = {}
    for tool_name, _ in _get_tools():
        tool_images[tool_name] = _images[tool_name]['check_name']

    if tool:
        return tool_images[tool]
    else:
        return [tool_images[tool] for tool, _ in _get_tools()]


def _get_tool_versions():
    '''
    Returns the image name for a tool.
    If tool is not provided, return all image names in a dict
    '''
    tool_versions = []
    for tool_name, _ in _get_tools(allow_skip=True):
        version = _tools.get_field(tool_name, 'git-commit')
        if not version:
            version = _tools.get_field(tool_name, 'version')
        if not version:
            continue
        tool_versions.append((tool_name, version))

    return tool_versions


def _get_tool_image_check_tag(tool):
    _, builder_tag, _ = base_image_details()

    _, tool_tag, tools_file = tool_image_details(tool)
    hash = hashlib.sha1()
    hash.update(builder_tag.encode('utf-8'))
    hash.update(get_file_hash(tools_file).encode('utf-8'))
    hash.update(tool_tag.encode('utf-8'))
    build_file = os.path.join(_install_script_path, f'install-{tool}.sh')
    if os.path.exists(build_file):
        hash.update(get_file_hash(build_file).encode('utf-8'))
    cmds = _tools.get_field(tool, 'docker-cmds')
    if cmds:
        for cmd in cmds:
            hash.update(cmd.encode('utf-8'))

    extra_files = _tools.get_field(tool, 'docker-extra-files')
    if extra_files:
        for extra_file in extra_files:
            path = os.path.join(_builder_path, extra_file)
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

    depends_on = _tools.get_field(tool, 'docker-depends')
    if depends_on:
        depends_hash = _get_tool_image_check_tag(depends_on)
        hash.update(depends_hash.encode('utf-8'))

    return hash.hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser('SC Docker Builder')
    parser.add_argument('--registry',
                        default=_registry,
                        metavar='registry',
                        help='Registry holding the docker images')

    parser.add_argument('--check_image',
                        metavar='image_name',
                        help='Check if a particular image is available')

    parser.add_argument('--tool',
                        metavar='tool_name',
                        help='Image name for a particular tool')
    parser.add_argument('--tool_as_hash_name',
                        action='store_true',
                        help='Return the image name with the hash instead of version')

    parser.add_argument('--include_tools',
                        nargs='+',
                        metavar='<tool>',
                        help='Tools to include in the final sc_tools image, default is all')

    parser.add_argument('--json_tools',
                        action='store_true',
                        help='Generate a JSON string with the tools that need to be built')
    parser.add_argument('--with_dependencies',
                        action='store_true',
                        help='Include tools which depend on other tools')

    parser.add_argument('--generate_files',
                        action='store_true',
                        help='Generate all available Dockerfiles')
    parser.add_argument('--output_dir',
                        default=os.path.join(_file_path, 'docker'),
                        metavar='dir',
                        help='Output directory to write the dockerfiles to')

    args = parser.parse_args()

    _registry = args.registry
    _tools_filter = args.include_tools

    builder_name, builder_tag, _ = base_image_details()
    _images = {
        "builder": {
            'tool': "builder",
            'name': get_image_name(builder_name, builder_tag, False),
            'check_name': get_image_name(builder_name, builder_tag, True),
            'builder_name': None
        }
    }

    for tool, _ in _get_tools():
        tool_image_name, version, _ = tool_image_details(tool)
        _images[tool] = {
            'tool': tool,
            'name': get_image_name(tool_image_name, version, False),
            'check_name': get_image_name(tool_image_name, _get_tool_image_check_tag(tool), True),
            'builder_name': builder_name
        }

    tools_name, tools_tag, _ = tools_image_details(_get_tool_images(), _get_tool_versions())
    _images['tools'] = {
        'tool': "tools",
        'name': get_image_name(tools_name, tools_tag, False),
        'check_name': get_image_name(tools_name, tools_tag, True),
        'builder_name': None
    }
    _images['runner'] = {
        'tool': "runner",
        'name': get_image_name('sc_runner', f'v{__version__}', False),
        'check_name': get_image_name('sc_runner', f'v{__version__}', True),
        'builder_name': None
    }

    if args.json_tools:
        json_tools = {'include': []}
        for tool, depends in _get_tools():
            if (not depends and not args.with_dependencies) or (depends and args.with_dependencies):
                tool_info = _images[tool]
                if not check_image(tool_info['check_name']):
                    json_tools['include'].append(tool_info)
        if len(json_tools['include']) == 0:
            print(json.dumps({}))
        else:
            print(json.dumps(json_tools))
        exit(0)

    if args.check_image:
        if check_image(args.check_image):
            print('true')
        else:
            print('false')
        exit(0)

    if args.tool:
        key = 'name'
        if args.tool_as_hash_name:
            key = 'check_name'
        print(_images[args.tool][key])
        exit(0)

    if args.generate_files:
        make_base_tool_docker(output_dir=args.output_dir)

        for tool, depends in _get_tools():
            make_tool_docker(tool, reference_tool=depends, output_dir=args.output_dir)

        make_sc_tools_docker(_get_tool_images(),
                             _get_tool_versions(),
                             output_dir=args.output_dir)
        _, sc_tools_tag, _ = tools_image_details(_get_tool_images(), _get_tool_versions())
        if not _tools_filter:
            make_sc_runner_docker(sc_tools_tag, output_dir=args.output_dir)
        exit(0)
