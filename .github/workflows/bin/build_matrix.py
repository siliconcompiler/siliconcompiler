import argparse
import json
import glob
import os.path


# Tools that cannot be built for aarch64 and are therefore skipped in the arm64
# matrix.
#  - bambu requires x86 32-bit multilib / -m32 code generation, which is not
#    packaged for arm64 (g++-11-multilib does not exist there).
#  - openroad builds its Qt GUI against the *system* X libraries on aarch64
#    (qt_bazel_prebuilts selects on @platforms//cpu:aarch64; x86_64 links its
#    bundled .ifso interface stubs instead). Those libraries reference glibc
#    symbols newer than the sysroot of OpenROAD's hermetic bazel LLVM
#    toolchain, so lld rejects them under its default --no-allow-shlib-undefined
#    (stat@GLIBC_2.33 and dlopen@GLIBC_2.34 from libX11 on ubuntu22, plus
#    __isoc23_*@GLIBC_2.38 on ubuntu24/26). Upstream issue; x86_64 builds fine.
AARCH64_UNSUPPORTED = {"bambu", "openroad"}

# Tools that cannot be built for a specific (os, arch) combination:
#  - bluespec: vendored MINISAT clashes with the newer glibc <time.h> on
#    ubuntu26/aarch64 (builds fine on ubuntu22/24 aarch64 and on all x86_64).
OS_ARCH_UNSUPPORTED = {
    ("ubuntu26", "aarch64"): {"bluespec"},
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate the tool-build matrix, optionally filtered.")
    parser.add_argument(
        "tool", nargs='?', default=None,
        help="(deprecated) single tool name; prefer --tools")
    parser.add_argument(
        "--tools", default="",
        help="comma-separated tool names to build (empty = all)")
    parser.add_argument(
        "--os", dest="oses", default="",
        help="comma-separated OS names, e.g. ubuntu26,rhel9 (empty = all)")
    parser.add_argument(
        "--arch", default="",
        help="comma-separated arches: x86_64,aarch64 (empty = all)")
    args = parser.parse_args()

    def _split(value):
        return {item.strip() for item in value.split(",") if item.strip()}

    tools = _split(args.tools)
    if args.tool:
        tools.add(args.tool)
    oses = _split(args.oses)
    arches = _split(args.arch)

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
        if oses and osname not in oses:
            continue

        for script in glob.glob(os.path.join(f, "install-*.sh")):
            scriptname = os.path.basename(script)
            toolname = scriptname[8:-3]
            if tools and toolname not in tools:
                continue
            if toolname not in tool_data:
                continue
            prebuild = []
            if "docker-depends" in tool_data[toolname]:
                prebuild = tool_data[toolname]["docker-depends"]
                if isinstance(prebuild, str):
                    prebuild = [prebuild]
                prebuild = [f"install-{pretool}.sh" for pretool in prebuild]

            for runon, arm64 in (("ubuntu-latest", False), ("ubuntu-24.04-arm", True)):
                if arm64 and osname not in ("ubuntu22", "ubuntu24", "ubuntu26"):
                    continue
                if arm64 and toolname in AARCH64_UNSUPPORTED:
                    continue

                arch = "x86_64"
                if arm64:
                    arch = "aarch64"

                if arches and arch not in arches:
                    continue

                if toolname in OS_ARCH_UNSUPPORTED.get((osname, arch), ()):
                    continue

                matrix.append({
                    "script": ",".join([*prebuild, scriptname]),
                    "runon": runon,
                    "path": os.path.relpath(os.path.join(buildroot, osname), scroot),
                    "name": f"{toolname} for {osname}-{arch}"
                })

    print(json.dumps({'include': matrix}))
