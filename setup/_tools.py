#!/usr/bin/env python3
# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

import argparse
import json
import os

def bump_commit(tools, tool):
    if "git-url" not in tools[tool]:
        return None

    import git, tempfile

    with tempfile.TemporaryDirectory(prefix=tool) as repo_work_dir:
        repo = git.Repo.clone_from(tools[tool]["git-url"], repo_work_dir)

        return repo.head.commit.hexsha

    return None

if __name__ == "__main__":
    tools = None
    data_file = os.path.join(os.path.dirname(__file__), "_tools.json")
    with open(data_file, "r") as f:
        tools = json.load(f)

    supported_tools = ", ".join(tools.keys())
    supported_fields = set()
    for tool, fields in tools.items():
        for field in fields:
            supported_fields.add(field)
    supported_fields = ", ".join(supported_fields)

    parser = argparse.ArgumentParser(
        prog = "SiliconCompiler Tool Helper",
        description = "Maintains current known good versions for all install scripts to use")
    parser.add_argument("--tool", type=str, required=True, help=f"Tool name, supported options: {supported_tools}")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--field", type=str, help=f"Field to get information from, supported options: {supported_fields}")
    group.add_argument("--bump_commit", action="store_true", help="Flag to indicate that the speficied tool should be updated.")

    args = parser.parse_args()

    if args.tool not in tools:
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

    new_value = bump_commit(tools, args.tool)
    if new_value and tools[args.tool]["git-commit"] != new_value:
        print(f"Updating {args.tool} to {new_value}")
        tools[args.tool]["git-commit"] = new_value

    with open(data_file, "w") as f:
        f.write(json.dumps(tools, indent=2))
