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


# Tags that name a pre-release. Both spellings turn up in the repositories these
# scripts track: the marker introduced by a separator (ghdl's v0.36-rc1, sbt's
# v2.0.0-M2) and the marker run straight onto a digit (ghdl's v1.0.0rc1 and
# ghdl_0.31dev, bsc's 2023.00.90alpha). One list of markers feeds both forms so
# that the two cannot drift apart, which they had: the second form knew only
# rc, alpha and beta, so a dev or milestone tag was caught in one spelling and
# missed in the other. "preview" precedes "pre" to be preferred over it.
_PRERELEASE_MARKERS = "rc|alpha|beta|preview|pre|snapshot|dev|milestone|m"

_prerelease_tag = re.compile(
    # A marker at a boundary -- the start of the name, a separator, or a digit
    # -- followed either by its number or by the end of the name. Demanding one
    # or the other is what stops a marker from matching the head of an ordinary
    # word: v1.0-m1 and v1.0-rc are candidates, v1.0-master is a release.
    #
    # Not anchored as a whole, because a candidate can carry something after
    # its number: sbt respun one as v2.0.0-RC13-1.
    rf"(?:^|[-._]|[0-9])(?:{_PRERELEASE_MARKERS})(?:[-._]?[0-9]+|$)",
    re.IGNORECASE)


def is_version_tag(name, version_prefix):
    """Whether a tag name is a release this updater should be willing to move to.

    The selection below picks the most recently committed tag, so anything that
    is not a release has to be excluded here rather than sorted around. Two
    kinds get through a prefix test on its own:

    A pre-release. A project that cuts release candidates from a branch opens
    the series before it finishes it, so the newest tag is an rc for as long as
    the series is open -- ghdl tagged v6.0.0-rc.1 and v6.0.0-rc2 ahead of
    v6.0.0, and sbt ran v2.0.0-M2 through v2.0.0-RC16 ahead of v2.0.0.

    A tag that is not a version at all. yosys is tracked with an empty prefix,
    because its tags have run 0.45, yosys-0.46 and v0.47 over the years, and
    that also matches "resources" and "docs-previewtest" -- branch-like tags
    that would hand the bot a git-commit of "resources" the first time one of
    them was pushed. A release name carries a number; these do not.
    """

    if not name.startswith(version_prefix):
        return False

    if not any(char.isdigit() for char in name):
        return False

    return _prerelease_tag.search(name) is None


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
            if not is_version_tag(tag.name, version_prefix):
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
            if not is_version_tag(tag.name, ""):
                continue

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
