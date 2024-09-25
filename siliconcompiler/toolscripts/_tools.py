#!/usr/bin/env python3
# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

import argparse
import json
import os
import tempfile
import subprocess
import re

tools = None
data_file = os.path.join(os.path.dirname(__file__), "_tools.json")
with open(data_file, "r") as f:
    tools = json.load(f)


def __make_github_url(url, old_version, new_version):
    if 'github' not in url:
        return None

    if url.endswith('.git'):
        url = url[0:-4]

    return f'{url}/compare/{old_version}...{new_version}'


def bump_commit(tools, tool):
    if "git-url" not in tools[tool]:
        return (None, None)

    if not re.fullmatch(r"[a-f0-9]{40}", tools[tool]["git-commit"]):
        return bump_commit_tag(tools, tool)

    import git

    with tempfile.TemporaryDirectory(prefix=tool) as repo_work_dir:
        repo = git.Repo.clone_from(tools[tool]["git-url"], repo_work_dir)

        return (repo.head.commit.hexsha,
                __make_github_url(tools[tool]["git-url"],
                                  tools[tool]["git-commit"],
                                  repo.head.commit.hexsha))

    return (None, None)


def bump_commit_tag(tools, tool):
    if "git-url" not in tools[tool]:
        return (None, None)

    import git

    version_prefix = 'v'
    if "version-prefix" in tools[tool]:
        version_prefix = tools[tool]["version-prefix"]

    with tempfile.TemporaryDirectory(prefix=tool) as repo_work_dir:
        repo = git.Repo.clone_from(tools[tool]["git-url"], repo_work_dir)

        newest = None
        for tag in repo.tags:
            if not tag.name.startswith(version_prefix):
                continue

            if not newest or tag.commit.committed_datetime > newest.commit.committed_datetime:
                newest = tag
        if newest:
            newest = newest.name
            return (newest,
                    __make_github_url(tools[tool]["git-url"],
                                      tools[tool]["git-commit"],
                                      newest))

    return (None, None)


def bump_version(tools, tool):
    if "git-url" not in tools[tool]:
        return (None, None)

    import git

    with tempfile.TemporaryDirectory(prefix=tool) as repo_work_dir:
        repo = git.Repo.clone_from(tools[tool]["git-url"], repo_work_dir)

        if "run-version" in tools[tool]:
            script = os.path.join(repo_work_dir, 'sc_get_version.sh')
            with open(script, 'w') as f:
                f.write(tools[tool]["run-version"])
            os.chmod(script, 0o700)
            proc = subprocess.run(['bash', script],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  universal_newlines=True,
                                  cwd=repo_work_dir)
            version = proc.stdout.strip()
            if not version:
                return (None, None)

            releasenotes = None
            if "release-notes" in tools[tool]:
                releasenotes = tools[tool]["release-notes"]
            return (version, releasenotes)

        newest = None
        for tag in repo.tags:
            if not newest:
                newest = tag
            else:
                if tag.commit.committed_datetime > newest.commit.committed_datetime:
                    newest = tag
        if newest:
            newest = newest.name
            has_v = False
            if newest[0] == 'v':
                newest = newest[1:]
                has_v = True

            new_version = newest
            old_version = tools[tool]["version"]
            if has_v:
                new_version = f'v{new_version}'
                old_version = f'v{old_version}'

            return (newest,
                    __make_github_url(tools[tool]["git-url"],
                                      old_version,
                                      new_version))

        return (None, None)

    return (None, None)


def has_tool(tool):
    return tool in tools


def get_field(tool, field):
    if field not in tools[tool]:
        return None
    return tools[tool][field]


def get_tools():
    return list(tools.keys())


if __name__ == "__main__":
    supported_tools = ", ".join(get_tools())
    supported_fields = set()
    for tool, fields in tools.items():
        for field in fields:
            supported_fields.add(field)
    supported_fields = ", ".join(supported_fields)

    parser = argparse.ArgumentParser(
        prog="SiliconCompiler Tool Helper",
        description="Maintains current known good versions for all install scripts to use")
    parser.add_argument("--tool", type=str,
                        help=f"Tool name, supported tools: {supported_tools}")
    parser.add_argument("--json_tools", action="store_true",
                        help="Flag to get json matrix used by github to update tools")

    parser.add_argument("--field", type=str,
                        help=f"Field to get information from, supported fields: {supported_fields}")
    parser.add_argument("--bump_commit", action="store_true",
                        help="Flag to indicate that the specified tool should be updated.")

    args = parser.parse_args()

    if args.json_tools:
        json_tools = {'include': []}
        for tool in get_tools():
            field = get_field(tool, "git-url")
            update = get_field(tool, "auto-update")
            if field and update:
                json_tools['include'].append({"tool": tool})
        if len(json_tools['include']) == 0:
            print(json.dumps({}))
        else:
            print(json.dumps(json_tools))
        exit(0)

    if not has_tool(args.tool):
        print(f"{args.tool} is not a supported tool.")
        print(f"Supported tools are: {supported_tools}")
        exit(1)

    if not args.bump_commit:
        tool_fields = tools[args.tool]
        if args.field not in tool_fields:
            print(f"{args.field} is not a supported field for {args.tool}.")
            tool_supported_fields = ", ".join(tool_fields.keys())
            print(f"Supported fields are: {tool_supported_fields}")
            exit(1)

        print(tool_fields[args.field])
        exit(0)

    if "git-commit" in tools[args.tool]:
        new_value, url = bump_commit(tools, args.tool)
        if new_value and tools[args.tool]["git-commit"] != new_value:
            print(f"Updating {args.tool} from {tools[args.tool]['git-commit']} to {new_value}")
            if url:
                print(f'Check {url} for changes')
            tools[args.tool]["git-commit"] = new_value
    elif "version" in tools[args.tool]:
        new_value, url = bump_version(tools, args.tool)
        if new_value and tools[args.tool]["version"] != new_value:
            print(f"Updating {args.tool} from {tools[args.tool]['version']} to {new_value}")
            if url:
                print(f'Check {url} for changes')
            tools[args.tool]["version"] = new_value
    else:
        print('Unsupported update tool')
        exit(1)

    with open(data_file, "w") as f:
        f.write(json.dumps(tools, indent=2))

    exit(0)
