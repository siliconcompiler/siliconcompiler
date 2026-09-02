import glob
import os
import re
import shutil
import subprocess
import sys

import pytest

import siliconcompiler


TOOLSCRIPTS = os.path.join(os.path.dirname(siliconcompiler.__file__), "toolscripts")
PREREQS = os.path.join(TOOLSCRIPTS, "_prereqs.sh")

INSTALL_SCRIPTS = sorted(
    os.path.relpath(path, TOOLSCRIPTS)
    for path in glob.glob(os.path.join(TOOLSCRIPTS, "*", "install-*.sh")))

# Every sudo left in an install script, and nothing else. These are the
# ones that genuinely need root whatever the machine already has. Prerequisites
# do not belong here -- install_prereqs handles those and asks for root only when
# something is actually missing.
#
# Adding a line here is a deliberate act. The point of the list is that the
# unconditional-sudo surface cannot grow quietly: it grew back once before, when
# an unconditional 'apt-get update' was added to every ubuntu script months after
# the selective-sudo mechanism had landed.
#
# Several entries are the RHEL 'devel' repository toggle. Those are not
# unconditional: each sits inside an `if prereqs_missing ...` for the very
# install it exists to serve, so it is skipped along with it. They appear here
# because this list is about the literal sudo, not about reachability.
DEVEL_REPO_TOGGLE = {
    "sudo dnf config-manager --set-enabled devel || true",
    "sudo dnf config-manager --set-disabled devel || true",
}

ALLOWED_SUDO = {
    "install-klayout.sh": {
        # KLayout itself, a system package rather than a prerequisite. The apt
        # installs are preceded by an explicit apt_update, since they no longer
        # inherit one from the prerequisite block.
        "sudo apt-get install -y klayout",
        "sudo apt-get install -y ./klayout.deb",
        'sudo cp ./klayout.deb "${SC_PREFIX}/"',
        "sudo yum install -y ./klayout.rpm",
    },
    "install-ghdl.sh": {
        # An unversioned clang++ in /usr/local for GHDL's LLVM backend build,
        # which invokes it by that name. Expected to go away with a GHDL update
        # that lets the build use the versioned clang++-20 directly.
        'sudo ln -sf "$(command -v clang++-20 || echo /usr/lib/llvm-20/bin/clang++)"'
        ' /usr/local/bin/clang++',
    },
    "install-surelog.sh": DEVEL_REPO_TOGGLE,
    "install-gtkwave.sh": DEVEL_REPO_TOGGLE,
    "install-xyce.sh": DEVEL_REPO_TOGGLE,
    "install-vpr.sh": {
        # The one toggle that stays unconditional: VPR installs its dependencies
        # through an upstream script, so there is no package list to probe.
        *DEVEL_REPO_TOGGLE,
    },
    "install-openroad.sh": {
        # Enabling CodeReady Builder for the GUI xcb packages, inside the
        # `if prereqs_missing` for that same install.
        "sudo /usr/bin/crb enable || sudo dnf config-manager --set-enabled crb",
    },
}


# strip <args> <file>. Records the invocation so a test can assert which flags a
# given kind of object got, and refuses the one file the real strip refuses, so
# the helper's "a refusal is not fatal" path is exercised.
STRIP_STUB = """#!/bin/sh
for arg in "$@"; do
    case "$arg" in
        *unstrippable*) echo "strip: $arg: file format not recognized" >&2; exit 1 ;;
    esac
done
echo "strip $*" >> "$SC_TEST_LOG"
"""


# Stand-ins for the three commands install_prereqs reaches for. Everything the
# helper does is recorded in $SC_TEST_LOG, so a test asserts on what it ran (and,
# just as importantly, on what it did not run).
COMMON_STUBS = {
    "sudo": """#!/bin/sh
echo "sudo $*" >> "$SC_TEST_LOG"
exec "$@"
""",
    # The helper drops sudo when it is already root, so the uid decides what the
    # log looks like. Stub it rather than inheriting the runner's: the daily CI
    # job runs the whole suite inside a container, where the real id says 0.
    "id": """#!/bin/sh
echo "${SC_TEST_UID:-1000}"
""",
    "strip": STRIP_STUB,
}

DEB_STUBS = {
    # dpkg-query -W -f='${Status}' <pkg>. Only "install ok installed" means the
    # package is there; "deinstall ok config-files" is the removed-but-not-purged
    # state that `dpkg -s` would wrongly accept, and an unknown name exits 1 with
    # no output, exactly as the real dpkg-query does.
    "dpkg-query": """#!/bin/sh
case "$3" in
    present-*) echo "install ok installed" ;;
    configfiles-*) echo "deinstall ok config-files" ;;
    *) exit 1 ;;
esac
""",
    "apt-get": """#!/bin/sh
echo "apt-get $*" >> "$SC_TEST_LOG"
""",
}

# rpm -q <pkg>: exit 0 when installed, 1 otherwise. Verified against real rpm on
# RHEL 8 and 9 as an unprivileged user.
RPM_QUERY_STUB = """#!/bin/sh
case "$2" in
    present-*) echo "$2-1.0-1.el9.x86_64" ;;
    *) echo "package $2 is not installed"; exit 1 ;;
esac
"""


def _manager_stub(name):
    return f'#!/bin/sh\necho "{name} $*" >> "$SC_TEST_LOG"\n'


RPM_STUBS = {"rpm": RPM_QUERY_STUB, "yum": _manager_stub("yum")}


# RHEL 8 and 9 both ship yum as an alias for dnf, but a dnf-only system has to
# work too: the helper picks whichever command is actually there.
DNF_STUBS = {"rpm": RPM_QUERY_STUB, "dnf": _manager_stub("dnf")}

BACKEND_STUBS = {"deb": DEB_STUBS, "rpm": RPM_STUBS, "dnf": DNF_STUBS}

# The backend is chosen by which package manager is on PATH, so each case runs
# with a PATH holding nothing but its own stubs plus the few real tools the
# helper shells out to.
# sc_strip_prefix walks the prefix and reads each file's ELF magic, so it needs a
# few more real tools than install_prereqs does.
REAL_TOOLS = ("grep", "find", "dd", "od", "tr", "basename")


@pytest.fixture
def run_prereqs():
    """Run shell against _prereqs.sh with a stubbed package manager."""
    log = os.path.abspath("prereqs.log")

    def run(body, backend="deb", root=False):
        bindir = os.path.abspath(f"stubbin-{backend}")
        os.makedirs(bindir, exist_ok=True)

        stubs = dict(COMMON_STUBS)
        stubs.update(BACKEND_STUBS[backend])
        for name, stub in stubs.items():
            path = os.path.join(bindir, name)
            with open(path, "w") as f:
                f.write(stub)
            os.chmod(path, 0o755)
        for name in REAL_TOOLS:
            real, link = shutil.which(name), os.path.join(bindir, name)
            if real and not os.path.exists(link):
                os.symlink(real, link)

        if os.path.exists(log):
            os.remove(log)

        script = os.path.abspath("script.sh")
        with open(script, "w") as f:
            f.write(f"set -e\n. {PREREQS}\n{body}\n")

        proc = subprocess.run(
            ["/bin/sh", script], capture_output=True, text=True,
            env={"PATH": bindir, "SC_TEST_LOG": log,
                 "SC_TEST_UID": "0" if root else "1000"})
        assert proc.returncode == 0, proc.stderr

        if not os.path.exists(log):
            return []
        with open(log) as f:
            return [line.strip() for line in f if line.strip()]

    return run


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_all_present_runs_nothing(run_prereqs):
    """Nothing missing means no sudo, and no apt-get update either."""
    assert run_prereqs("install_prereqs present-git present-curl") == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_missing_package_is_installed(run_prereqs):
    """One missing package still installs, and only the missing one."""
    log = run_prereqs("install_prereqs present-git missing-libfl-dev present-curl")

    assert log == [
        "sudo apt-get update",
        "apt-get update",
        "sudo apt-get install -y missing-libfl-dev",
        "apt-get install -y missing-libfl-dev",
    ]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_config_files_state_counts_as_missing(run_prereqs):
    """A removed-but-not-purged package is reinstalled, not skipped."""
    log = run_prereqs("install_prereqs configfiles-tcl-dev")

    assert "apt-get install -y configfiles-tcl-dev" in log


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_unknown_package_falls_through_to_apt(run_prereqs):
    """A name dpkg does not recognise is handed to apt, which errors as before."""
    log = run_prereqs("install_prereqs unknown-libgnat-9")

    assert "apt-get install -y unknown-libgnat-9" in log


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_update_runs_once(run_prereqs):
    """apt-get update is the slow step: it runs once, however many calls follow."""
    log = run_prereqs(
        "install_prereqs missing-one\n"
        "install_prereqs missing-two\n"
        "apt_update")

    assert log.count("apt-get update") == 1
    assert "apt-get install -y missing-one" in log
    assert "apt-get install -y missing-two" in log


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_apt_update_refreshes_when_nothing_was_installed(run_prereqs):
    """A skipped prereq install leaves the index stale, so apt_update still runs."""
    log = run_prereqs("install_prereqs present-wget\napt_update")

    assert log.count("apt-get update") == 1


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_empty_list_is_a_noop(run_prereqs):
    assert run_prereqs("install_prereqs") == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_rpm_all_present_runs_nothing(run_prereqs):
    """Same contract on rhel: nothing missing means yum is never invoked."""
    assert run_prereqs("install_prereqs present-git present-gcc", backend="rpm") == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_rpm_missing_package_is_installed(run_prereqs):
    """Only the missing package reaches yum, and there is no update step."""
    log = run_prereqs("install_prereqs present-git missing-tcl-devel", backend="rpm")

    assert log == [
        "sudo yum install -y missing-tcl-devel",
        "yum install -y missing-tcl-devel",
    ]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_rpm_flags_are_passed_through_not_probed(run_prereqs):
    """A leading flag goes to yum instead of being treated as a package name."""
    log = run_prereqs("install_prereqs --skip-broken missing-git", backend="rpm")

    assert "yum install -y --skip-broken missing-git" in log


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_rpm_flags_alone_install_nothing(run_prereqs):
    assert run_prereqs("install_prereqs --skip-broken", backend="rpm") == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_group_installs_when_payload_is_missing(run_prereqs):
    """A group with any mandatory member missing is installed, as before."""
    log = run_prereqs('install_prereq_group "Development Tools"', backend="rpm")

    assert 'yum group install -y Development Tools' in log


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_group_skips_when_payload_is_present(run_prereqs):
    """
    The whole point of probing the payload: 'dnf group list --installed' reports
    a group as installed even after its packages are gone, so the group itself
    cannot be asked. With every mandatory member present the install is a no-op.
    """
    log = run_prereqs(
        '_SC_GROUP_DEVELOPMENT_TOOLS="present-gcc present-make"\n'
        'install_prereq_group "Development Tools"',
        backend="rpm")

    assert log == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_unknown_group_is_installed_unconditionally(run_prereqs):
    """No payload to probe means no confident skip, so it installs."""
    log = run_prereqs('install_prereq_group "Some Other Group"', backend="rpm")

    assert "yum group install -y Some Other Group" in log


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_root_installs_without_sudo(run_prereqs):
    """
    Already root -- the container builds, where sudo may not even be installed.
    The package manager is invoked directly.
    """
    log = run_prereqs("install_prereqs missing-git", root=True)

    assert log == ["apt-get update", "apt-get install -y missing-git"]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_root_installs_without_sudo_on_rpm(run_prereqs):
    log = run_prereqs("install_prereqs missing-git", backend="rpm", root=True)

    assert log == ["yum install -y missing-git"]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_root_still_skips_what_is_present(run_prereqs):
    """Being root is not a reason to reinstall."""
    assert run_prereqs("install_prereqs present-git", root=True) == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_dnf_only_system_uses_dnf(run_prereqs):
    """A system with dnf but no yum alias installs with dnf, not a missing yum."""
    log = run_prereqs("install_prereqs missing-tcl-devel", backend="dnf")

    assert log == [
        "sudo dnf install -y missing-tcl-devel",
        "dnf install -y missing-tcl-devel",
    ]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_dnf_only_system_installs_groups_with_dnf(run_prereqs):
    log = run_prereqs('install_prereq_group "Development Tools"', backend="dnf")

    assert "dnf group install -y Development Tools" in log


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_prereqs_missing_gates_a_block(run_prereqs):
    """
    The predicate that lets a repository enable/disable pair be skipped along
    with the install it wraps.
    """
    present = run_prereqs(
        "if prereqs_missing present-gcc; then sudo yum config-manager x; fi",
        backend="rpm")
    assert present == []

    absent = run_prereqs(
        "if prereqs_missing missing-gcc; then sudo yum config-manager x; fi",
        backend="rpm")
    assert absent == ["sudo yum config-manager x", "yum config-manager x"]


def test_install_scripts_exist():
    assert INSTALL_SCRIPTS, "no install scripts found"


@pytest.mark.parametrize("script", INSTALL_SCRIPTS)
def test_script_sources_the_helper(script):
    """Every script gets install_prereqs, so a new one inherits it too."""
    with open(os.path.join(TOOLSCRIPTS, script)) as f:
        text = f.read()

    assert '. "${src_path}/_prereqs.sh"' in text
    assert "install_prereqs " in text or "install_prereq_group " in text


@pytest.mark.parametrize("script", INSTALL_SCRIPTS)
def test_script_sudo_is_on_the_allowlist(script):
    """
    Every remaining sudo is one somebody signed off on. A prerequisite install is
    never one of them: install_prereqs asks for root only when a package is
    actually missing, which is what lets an unprivileged user install tools into
    the default ~/.local prefix.
    """
    allowed = ALLOWED_SUDO.get(os.path.basename(script), set())

    with open(os.path.join(TOOLSCRIPTS, script)) as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            # Skip comments and the SUDO_INSTALL assignments, which are already
            # conditional on the prefix being writable.
            if line.startswith("#") or line.startswith("SUDO_INSTALL="):
                continue
            if not re.search(r"\bsudo\b", line):
                continue
            assert line in allowed, \
                f"{script}:{lineno}: unexpected sudo, use install_prereqs instead: {line!r}"

# ---------------------------------------------------------------------------
# sc_remove_prereqs
#
# The mirror of install_prereqs, and asymmetric with it on purpose. Installing
# errs toward acting: an unrecognised name is handed to the package manager.
# Removing errs toward leaving things alone, because "apt-get remove" exits 100
# on a name it does not recognise -- and tool.docker cleans /var/lib/apt/lists
# before docker-cmds run, so the only names apt recognises there are the
# installed ones. An unfiltered remove list fails the image build outright.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_remove_drops_installed_packages(run_prereqs):
    """The straightforward case: everything named is installed, so all of it goes."""
    log = run_prereqs("sc_remove_prereqs present-ghc present-tcl-dev")

    assert log == [
        "sudo apt-get remove -y --purge present-ghc present-tcl-dev",
        "apt-get remove -y --purge present-ghc present-tcl-dev",
    ]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_remove_of_nothing_installed_runs_no_package_manager(run_prereqs):
    """The build-breaking case. Not installed means the package manager is never
    called, because calling it would exit 100 and fail the image build."""
    assert run_prereqs("sc_remove_prereqs llvm-18-tools clang-18 libz-dev") == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_remove_filters_to_the_installed_subset(run_prereqs):
    """A partly-stale list removes what is there and says nothing about the rest."""
    log = run_prereqs(
        "sc_remove_prereqs absent-llvm-18-dev present-pandoc absent-gnat present-groff")

    assert log == [
        "sudo apt-get remove -y --purge present-pandoc present-groff",
        "apt-get remove -y --purge present-pandoc present-groff",
    ]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_remove_never_autoremoves(run_prereqs):
    """No autoremove, ever.

    These images keep runtime libraries that arrived only as a build package's
    dependency -- libxcb-keysyms1 under libxcb-keysyms1-dev, libgmp10 under ghc,
    libllvm18 under llvm-18-dev. An autoremove would take them along with the
    build packages and break the tool at run time rather than at build time.
    """
    log = run_prereqs("sc_remove_prereqs present-ghc")

    assert not any("autoremove" in line for line in log)


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_remove_empty_list_is_a_noop(run_prereqs):
    assert run_prereqs("sc_remove_prereqs") == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_remove_configfiles_state_is_not_removed_again(run_prereqs):
    """Already removed, config files left behind. Nothing to do."""
    assert run_prereqs("sc_remove_prereqs configfiles-tcl-dev") == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_remove_as_root_drops_sudo(run_prereqs):
    """The container builds run as root, where sudo may not be installed."""
    log = run_prereqs("sc_remove_prereqs present-ghc", root=True)

    assert log == ["apt-get remove -y --purge present-ghc"]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
@pytest.mark.parametrize("backend,manager", [("rpm", "yum"), ("dnf", "dnf")])
def test_remove_on_rpm_uses_the_right_manager(run_prereqs, backend, manager):
    log = run_prereqs("sc_remove_prereqs present-ghc absent-gnat", backend=backend)

    assert log == [
        f"sudo {manager} remove -y present-ghc",
        f"{manager} remove -y present-ghc",
    ]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_remove_on_rpm_with_nothing_installed_is_a_noop(run_prereqs):
    assert run_prereqs("sc_remove_prereqs absent-gnat", backend="rpm") == []


# ---------------------------------------------------------------------------
# sc_strip_prefix
# ---------------------------------------------------------------------------

ELF_MAGIC = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8


def _make_prefix(root, files):
    """Build a fake install prefix. A file whose content is ELF magic is treated
    as an object to strip; anything else stands in for a script or data file."""
    for relpath, elf in files.items():
        path = os.path.join(root, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(ELF_MAGIC if elf else b"#!/bin/sh\necho hello\n")
        os.chmod(path, 0o755)
    return root


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_strip_uses_strip_all_on_executables_and_strip_unneeded_on_libraries(
        run_prereqs, tmp_path):
    """The distinction that matters.

    A shared object keeps .dynsym, which is what the loader and dlopen() resolve
    against -- strip it and every plugin in the tree stops loading. An
    executable has no such constraint, so it gets the full strip.
    """
    prefix = _make_prefix(str(tmp_path / "px"), {
        "bin/yosys": True,
        "lib/libyosys.so": True,
        "lib/libghdl-5_1_1.so.1": True,
    })

    log = run_prereqs(f"sc_strip_prefix {prefix}")
    flags = {line.rsplit("/", 1)[-1]: line for line in log}

    assert "--strip-all" in flags["yosys"]
    assert "--strip-unneeded" in flags["libyosys.so"]
    assert "--strip-unneeded" in flags["libghdl-5_1_1.so.1"]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_strip_leaves_static_archives_alone(run_prereqs, tmp_path):
    """Static archives are skipped, and not as an oversight.

    Three tools link an archive from their own prefix at run time --
    lib/ghdl/libgrt.a into every elaborated design, lib/panda/*.a into bambu's
    generated designs, lib/Bluesim/*.a for "bsc -sim" -- and stripping an
    archive breaks linking against it. The container drops the archives it does
    not need by name instead.
    """
    prefix = _make_prefix(str(tmp_path / "pa"), {
        "lib/ghdl/libgrt.a": True,
        "lib/panda/libbambu_clang16.a": True,
        "bin/ghdl": True,
    })

    log = run_prereqs(f"sc_strip_prefix {prefix}")

    assert not any(".a" in line for line in log)
    assert any(line.endswith("/ghdl") for line in log)


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_strip_skips_non_elf_files(run_prereqs, tmp_path):
    """The prefixes are full of executable shell, Tcl and Python. The helper
    checks the magic number rather than trusting the mode bit."""
    prefix = _make_prefix(str(tmp_path / "pn"), {
        "bin/sc-install": False,
        "bin/verilator": False,
        "bin/verilator_bin": True,
    })

    log = run_prereqs(f"sc_strip_prefix {prefix}")

    assert len(log) == 1
    assert log[0].endswith("/verilator_bin")


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_strip_survives_an_object_it_cannot_strip(run_prereqs, tmp_path):
    """A refusal is not fatal: a tool that builds is worth more than the bytes.

    The install scripts run under "set -e", so a non-zero strip would otherwise
    abort the whole install.
    """
    prefix = _make_prefix(str(tmp_path / "pu"), {
        "bin/unstrippable-thing": True,
        "bin/openroad": True,
    })

    log = run_prereqs(f"sc_strip_prefix {prefix}")

    assert [line.rsplit("/", 1)[-1] for line in log] == ["openroad"]


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_strip_of_a_missing_prefix_is_a_noop(run_prereqs, tmp_path):
    assert run_prereqs(f"sc_strip_prefix {tmp_path}/not-there") == []


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_strip_with_no_argument_falls_back_to_prefix(run_prereqs, tmp_path):
    """tool.docker passes $SC_PREFIX explicitly, but the install scripts export
    PREFIX, so a bare call has to work too."""
    prefix = _make_prefix(str(tmp_path / "pp"), {"bin/sta": True})

    log = run_prereqs(f"PREFIX={prefix}\nexport PREFIX\nsc_strip_prefix")

    assert len(log) == 1
    assert log[0].endswith("/sta")
