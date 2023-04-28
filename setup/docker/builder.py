#!/usr/bin/env python3

import os
import sys

import argparse
import docker
import hashlib
from jinja2 import Template
import json
import shutil
import requests

_file_path = os.path.dirname(__file__)
_tools_path = os.path.abspath(os.path.join(_file_path, '..'))
sys.path.append(_tools_path)

# Import tools which contains all the version information
import _tools

_registry = None

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

def tools_image_details(tools):
    '''
    Details about the sc_tools image, which contains all the tools
    '''
    docker_file = os.path.join(_file_path, 'sc_tools.docker')

    hash = hashlib.sha1()
    for tool in sorted(tools):
        hash.update(tool.encode('utf-8'))
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

def get_image_name(name, tag):
    '''
    Returns the image name with tag
    '''
    image_name = f'siliconcompiler/{name}:{tag}'
    if _registry:
        image_name = f'{_registry}/{image_name}'
    return image_name

def assemble_docker_file(name, tag, template, options, output_dir, copy_files=None):
    '''
    Generate a Dockerfile based on the provided template
    '''

    print(f'Generating: {name}:{tag}')
    tool_template = None
    with open(template, 'r') as docker_f:
        tool_template = Template(docker_f.read())

    if not tool_template:
        raise FileNotFoundError('Template file is missing')

    docker_dir = os.path.join(output_dir, name)
    os.makedirs(docker_dir, exist_ok=True)

    with open(os.path.join(docker_dir, 'Dockerfile'), 'w') as f:
        f.write(tool_template.render(options))

    if copy_files:
        for cp_file in copy_files:
            shutil.copy(cp_file, docker_dir)

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
    if reference_tool:
        base_name, base_tag, _ = tool_image_details(reference_tool)

    name, tag, docker_file = tool_image_details(tool)

    extracmds = _tools.get_field(tool, 'docker-cmds')
    if extracmds:
        extracmds = '\n'.join(extracmds)
    else:
        extracmds = ''
    template_opts = {
        'tool': tool,
        'base_build_image': get_image_name(base_name, base_tag),
        'install_script': f'install-{tool}.sh',
        'extra_commands': extracmds
    }

    copy_files = []
    for f in ('_tools.json',
              '_tools.py',
              template_opts['install_script']):
        copy_files.append(os.path.join(_tools_path, f))
    assemble_docker_file(name, tag, docker_file, template_opts, output_dir, copy_files=copy_files)

def make_sc_tools_docker(tools, output_dir):
    '''
    Generate sc_tools dockerfile which contains all the tools
    '''
    name, tag, docker_file = tools_image_details(tools)

    skip_build = []
    for tool in _tools.get_tools():
        if _tools.get_field(tool, 'docker-skip'):
            skip_build.append(tool)

    template_opts = {
        'tools': tools,
        'skip_build': skip_build,
        'slurm_version': _tools.get_field('slurm', 'version')
    }

    copy_files = ['_tools.json', '_tools.py']
    for tool in skip_build:
        copy_files.append(f'install-{tool}.sh')
    for slurm_file in ['cgroup.conf', 'slurm.conf', 'start_slurm.sh']:
        copy_files.append(os.path.join('docker', 'slurm', slurm_file))
    cp_files = []
    for f in copy_files:
        cp_files.append(os.path.join(_tools_path, f))

    assemble_docker_file(name, tag, docker_file, template_opts, output_dir, copy_files=cp_files)

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

def _get_tools():
    '''
    Helper function to provide a list of tools
    '''
    tools = []
    for tool in _tools.get_tools():
        if not os.path.exists(os.path.join(_tools_path, f'install-{tool}.sh')):
            continue
        if not _tools.get_field(tool, 'docker-skip'):
            tools.append((tool, _tools.get_field(tool, 'docker-depends')))
    return tools

def _get_tool_images(tool=None):
    '''
    Returns the image name for a tool.
    If tool is not provided, return all image names in a dict
    '''
    tool_images = {}
    for tool_name, _ in _get_tools():
        tool_image_name, tool_tag, _ = tool_image_details(tool_name)
        tool_images[tool_name] = get_image_name(tool_image_name, tool_tag)

    if tool:
        return tool_images[tool]
    else:
        return [tool_images[tool] for tool, _ in _get_tools()]

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

    if args.json_tools:
        builder_name, builder_tag, _ = base_image_details()
        builder_name = get_image_name(builder_name, builder_tag)
        json_tools = {'include': []}
        for tool, depends in _get_tools():
            if (not depends and not args.with_dependencies) or (depends and args.with_dependencies):
                tool_name, tool_tag, _ = tool_image_details(tool)
                image_name = get_image_name(tool_name, tool_tag)
                hash = hashlib.sha1()
                hash.update(builder_tag.encode('utf-8'))
                hash.update(tool_tag.encode('utf-8'))
                check_name = get_image_name(tool_name, hash.hexdigest())
                json_tool = {
                    'tool': tool,
                    'name': _get_tool_images(tool),
                    'check_name': check_name,
                    'builder_name': builder_name
                }
                if not check_image(check_name):
                    json_tools['include'].append(json_tool)
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
        if args.tool == 'builder':
            name, tag, _ = base_image_details()
        elif args.tool == 'tools':
            name, tag, _ = tools_image_details(_get_tool_images())
        else:
            name, tag, _ = tool_image_details(args.tool)
        print(get_image_name(name, tag))
        exit(0)

    if args.generate_files:
        make_base_tool_docker(output_dir=args.output_dir)

        for tool, depends in _get_tools():
            make_tool_docker(tool, reference_tool=depends, output_dir=args.output_dir)

        make_sc_tools_docker(_get_tool_images(), output_dir=args.output_dir)
        exit(0)
