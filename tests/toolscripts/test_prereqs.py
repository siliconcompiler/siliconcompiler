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


# Stand-ins for the three commands install_prereqs reaches for. Everything the
# helper does is recorded in $SC_TEST_LOG, so a test asserts on what it ran (and,
# just as importantly, on what it did not run).
COMMON_STUBS = {
    "sudo": """#!/bin/sh
echo "sudo $*" >> "$SC_TEST_LOG"
exec "$@"
""",
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

RPM_STUBS = {
    # rpm -q <pkg>: exit 0 when installed, 1 otherwise. Verified against real
    # rpm on RHEL 8 and 9 as an unprivileged user.
    "rpm": """#!/bin/sh
case "$2" in
    present-*) echo "$2-1.0-1.el9.x86_64" ;;
    *) echo "package $2 is not installed"; exit 1 ;;
esac
""",
    "yum": """#!/bin/sh
echo "yum $*" >> "$SC_TEST_LOG"
""",
}

# The backend is chosen by which package manager is on PATH, so each case runs
# with a PATH holding nothing but its own stubs plus the few real tools the
# helper shells out to.
REAL_TOOLS = ("id", "grep")


@pytest.fixture
def run_prereqs():
    """Run shell against _prereqs.sh with a stubbed package manager."""
    log = os.path.abspath("prereqs.log")

    def run(body, backend="deb"):
        bindir = os.path.abspath(f"stubbin-{backend}")
        os.makedirs(bindir, exist_ok=True)

        stubs = dict(COMMON_STUBS)
        stubs.update(DEB_STUBS if backend == "deb" else RPM_STUBS)
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
            env={"PATH": bindir, "SC_TEST_LOG": log})
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
