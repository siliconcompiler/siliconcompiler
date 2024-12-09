#!/usr/bin/env python3
# SiliconCompiler Replay
# From {{ source }}
# Jobname: {{ jobname }}

from siliconcompiler import Chip


if __name__ == "__main__":
    chip = Chip("{{ design }}")

    # Read manifest{% for cfg in cfgs %}
    chip.read_manifest("{{ cfg }}"){% endfor %}

    # Set tool versions{% for node, tool, version in tool_versions %}
    chip.set("tool", "{{ tool }}", "version", "=={{ version }}", step="{{ node[0] }}", index="{{ node[1] }}"){% endfor %}

    # Run
    chip.run()

    # Report summary
    chip.summary()
