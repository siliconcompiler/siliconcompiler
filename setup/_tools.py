#!/usr/bin/env python3
# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

import argparse
import json
import os

tools = None
data_file = os.path.join(os.path.dirname(__file__), "_tools.json")
with open(data_file, "r") as f:
    tools = json.load(f)

def bump_commit(tools, tool):
    if "git-url" not in tools[tool]:
        return None

    import git, tempfile

    with tempfile.TemporaryDirectory(prefix=tool) as repo_work_dir:
        repo = git.Repo.clone_from(tools[tool]["git-url"], repo_work_dir)

        return repo.head.commit.hexsha

    return None

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
        prog = "SiliconCompiler Tool Helper",
        description = "Maintains current known good versions for all install scripts to use")
    parser.add_argument("--tool", type=str, help=f"Tool name, supported options: {supported_tools}")
    parser.add_argument("--json_tools", action="store_true", help="Flag to get json matrix used by github to update tools")

    parser.add_argument("--field", type=str, help=f"Field to get information from, supported options: {supported_fields}")
    parser.add_argument("--bump_commit", action="store_true", help="Flag to indicate that the specified tool should be updated.")

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

    new_value = bump_commit(tools, args.tool)
    if new_value and tools[args.tool]["git-commit"] != new_value:
        print(f"Updating {args.tool} to {new_value}")
        tools[args.tool]["git-commit"] = new_value

    with open(data_file, "w") as f:
        f.write(json.dumps(tools, indent=2))
