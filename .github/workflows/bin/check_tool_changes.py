"""
Module for detecting changes in tool configurations between versions.
"""

import argparse
import json
import sys
from typing import Set


def get_changed_tools(tools_v1: str, tools_v2: str) -> Set[str]:
    """
    Compare two versions of the _tools.json configuration and return changed tools.

    This function identifies tools that have been added, removed, or modified
    between two versions of the tools configuration.

    Args:
        tools_v1: File path to the original _tools.json file.
        tools_v2: File path to the updated _tools.json file.

    Returns:
        A set of tool names (strings) that have changed between versions.
        Returns an empty set if no tools have changed.
        Changed includes: tools added, removed, or with modified configuration.

    Raises:
        FileNotFoundError: If either file path doesn't exist.
        json.JSONDecodeError: If either file contains invalid JSON.

    Examples:
        >>> changed = get_changed_tools('old_tools.json', 'new_tools.json')
        >>> print(changed)  # {'openroad', 'surelog'}
    """
    with open(tools_v1, 'r') as f:
        config_v1 = json.load(f)

    with open(tools_v2, 'r') as f:
        config_v2 = json.load(f)

    # Find changed tools
    changed_tools: Set[str] = set()

    # Check for added or modified tools
    for tool_name in config_v2:
        if tool_name not in config_v1:
            # Tool was added
            changed_tools.add(tool_name)
        elif config_v1[tool_name] != config_v2[tool_name]:
            # Tool was modified
            changed_tools.add(tool_name)

    # Check for removed tools
    for tool_name in config_v1:
        if tool_name not in config_v2:
            # Tool was removed
            changed_tools.add(tool_name)

    return changed_tools


def main() -> int:
    """Parse command line arguments and compare tool configurations."""
    workflows = {
        "asic": ("openroad", "yosys", "sv2v", "klayout", "yosys-slang", "surelog", "chisel"),
    }

    parser = argparse.ArgumentParser(
        description="Compare two versions of _tools.json and report changed tools."
    )
    parser.add_argument(
        "tools_v1",
        type=str,
        help="Path to the original _tools.json file",
    )
    parser.add_argument(
        "tools_v2",
        type=str,
        help="Path to the updated _tools.json file",
    )
    parser.add_argument(
        "--workflow",
        type=str,
        choices=workflows.keys(),
        required=True,
        help="Workflow to check for tool changes",
    )

    args = parser.parse_args()

    changed = get_changed_tools(args.tools_v1, args.tools_v2)

    # Filter changed tools by workflow if specified
    workflow_tools = set(workflows[args.workflow])
    changed = changed.intersection(workflow_tools)

    if changed:
        print("Yes")
    else:
        print("No")
    return 0


if __name__ == "__main__":
    sys.exit(main())
