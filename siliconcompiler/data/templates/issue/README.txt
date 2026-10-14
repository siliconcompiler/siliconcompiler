SiliconCompiler test case

To run this testcase:
{% if has_run %}./run.sh   (./run.sh --help lists its options)
-- or --
{% endif %}sc-issue -run -file {{ archive_name }}

** SiliconCompiler information **
Version: {{ version['sc'] }}
Schema: {{ version['schema'] }}

** Run **
Testcase built: {{ date }}
Tool: {{ run['tool'] }} {% if run['toolversion'] %}{{ run['toolversion'] }}{% endif %}
Task: {{ run['task'] }}
Node: {{ run['step'] }}/{{ run['index'] }}

** Python **
Version: {{ python['version'] }}

** Machine **
System: {{ machine['system'] }}
Distribution: {{ machine['distro'] }}
Version: {{ machine['osversion'] }}
Kernel version: {{ machine['kernelversion'] }}
Architecture: {{ machine['arch'] }}
