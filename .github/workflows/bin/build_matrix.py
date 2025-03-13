import json
import glob
import os.path


if __name__ == "__main__":
    binroot = os.path.abspath(os.path.dirname(__file__))
    scroot = os.path.dirname(os.path.dirname(os.path.dirname(binroot)))
    toolsroot = os.path.join(scroot, "siliconcompiler", "toolscripts")
    buildroot = os.path.join(scroot, "setup")

    with open(os.path.join(toolsroot, "_tools.json")) as f:
        tool_data = json.load(f)

    matrix = []

    for f in glob.glob(os.path.join(toolsroot, "*")):
        if f.endswith("__pycache__"):
            continue
        if not os.path.isdir(f):
            continue

        osname = os.path.basename(f)

        for script in glob.glob(os.path.join(f, "install-*.sh")):
            scriptname = os.path.basename(script)
            toolname = scriptname[8:-3]
            if toolname not in tool_data:
                continue
            if "docker-depends" in tool_data[toolname] and tool_data[toolname]["docker-depends"]:
                continue

            for runon, arm64 in (("ubuntu-latest", False), ("ubuntu-24.04-arm", True)):
                if arm64 and osname not in ("ubuntu22", "ubuntu24"):
                    continue

                matrix.append({
                    "script": scriptname,
                    "runon": runon,
                    "path": os.path.relpath(os.path.join(buildroot, osname), scroot)
                })

    print(json.dumps({'include': matrix}))
