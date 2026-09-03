# shellcheck shell=sh
#
# Shared prerequisite handling for the SiliconCompiler tool install scripts.
#
# Source this alongside the src_path definition and declare what the script
# needs:
#
#     . "${src_path}/_prereqs.sh"
#     install_prereqs git build-essential zlib1g-dev
#
# Packages the machine already has are dropped from the list, and when nothing
# is left the package manager -- and with it sudo -- is never invoked at all.
# That is what makes an unprivileged install possible: sc-install defaults to a
# prefix of ~/.local, which needs no root of its own, but the unconditional
# "sudo apt-get" at the top of every script used to abort the run under `set -e`
# before anything was built.
#
# Unsure means install. Only a confident "already installed" skips a package;
# an unknown name, a virtual package or rpm provide, a removed-but-not-purged
# dpkg state, or a failure of the probe itself all fall through to the package
# manager, which then behaves -- and fails -- exactly as these scripts did
# before. A probe that treated "I do not recognise this" as "it is fine" would
# turn a packaging bug into a mystery build failure twenty minutes later.
#
# The invariant that makes this safe: what reaches the package manager is always
# a subset of what these scripts passed it before. Never a superset. So the probe
# cannot introduce an install that did not already happen -- only skip one.
#
# Entry points:
#
#     install_prereqs [flags] PKG...   install what is missing
#     install_prereq_group GROUP       install a package group if its payload is
#                                      not already there (rpm only)
#     prereqs_missing PKG...           true if any are missing; use it to gate
#                                      work that only makes sense around an
#                                      install, such as enabling a repository
#     apt_update                       refresh the apt index, at most once

if [ "$(id -u)" = "0" ]; then
    # Already root, as in the container builds, where sudo may not be installed.
    _sc_sudo=""
else
    _sc_sudo="sudo"
fi

# Which package manager installs, decided once when this file is sourced. The
# probe used to decide what is already present is chosen separately below, so a
# system with a package manager but no query tool still installs (unsure means
# install) rather than erroring.
if command -v apt-get > /dev/null 2>&1; then
    _sc_backend="deb"
elif command -v yum > /dev/null 2>&1; then
    # RHEL 8 and 9 both ship yum as an alias for dnf. Prefer it, because it is
    # what these scripts have always called.
    _sc_backend="rpm"
    _sc_yum="yum"
elif command -v dnf > /dev/null 2>&1; then
    _sc_backend="rpm"
    _sc_yum="dnf"
else
    _sc_backend="none"
fi

# "apt-get update" is the slowest step in most of these scripts. Run it at most
# once, and only once something actually has to be installed. yum/dnf refresh
# their metadata as part of the install, so they need no equivalent.
_sc_apt_updated="no"

# Refresh the package index, at most once per script. Call this before an
# apt-get install that does not go through install_prereqs.
apt_update() {
    if [ "$_sc_apt_updated" = "yes" ]; then
        return 0
    fi

    $_sc_sudo apt-get update
    _sc_apt_updated="yes"
}

# Echo the subset of "$@" that dpkg does not report as fully installed.
_sc_missing_deb() {
    _sc_missing=""
    for _sc_pkg in "$@"; do
        # Test the status string rather than using `dpkg -s`, which also
        # succeeds for a removed-but-not-purged package whose config files are
        # all that is left. "install ok installed" is the state that means the
        # package is actually there.
        if ! dpkg-query -W -f='${Status}' "$_sc_pkg" 2>/dev/null |
                grep -q '^install ok installed$'; then
            _sc_missing="$_sc_missing $_sc_pkg"
        fi
    done

    printf '%s' "$_sc_missing"
}

# Echo the subset of "$@" that rpm does not report as installed.
_sc_missing_rpm() {
    _sc_missing=""
    for _sc_pkg in "$@"; do
        # Query the package name only. A name that is merely provided by some
        # other package (a virtual provide) reads as missing here and falls
        # through to yum, which is the same thing these scripts did before.
        if ! rpm -q "$_sc_pkg" > /dev/null 2>&1; then
            _sc_missing="$_sc_missing $_sc_pkg"
        fi
    done

    printf '%s' "$_sc_missing"
}

# Echo the subset of "$@" that is not installed, using whichever probe fits.
_sc_missing_pkgs() {
    # This always runs in a command substitution, so quieting the trace here
    # affects only the probe: with `set -x` the caller would otherwise get
    # several lines per package and the install would be buried in them.
    set +x

    # A file path or URL is not a package name, and asking a probe about one gets
    # an answer about the wrong thing: `rpm -q ./foo.rpm` (a URL included, which it
    # downloads to do it) reports the NEVRA of that *file* and exits 0, whatever is
    # or is not installed. Probing one would therefore skip the install of a package
    # the machine does not have. So these never reach a probe -- unsure means
    # install, and about a file the probe has nothing to say.
    _sc_literal=""
    _sc_probe=""
    for _sc_arg in "$@"; do
        case "$_sc_arg" in
            */*|*.rpm|*.deb) _sc_literal="$_sc_literal $_sc_arg" ;;
            *) _sc_probe="$_sc_probe $_sc_arg" ;;
        esac
    done

    printf '%s' "$_sc_literal"

    if [ -z "$_sc_probe" ]; then
        return 0
    fi

    # Word splitting of the probe list is intended.
    # shellcheck disable=SC2086
    if command -v dpkg-query > /dev/null 2>&1; then
        _sc_missing_deb $_sc_probe
    elif command -v rpm > /dev/null 2>&1; then
        _sc_missing_rpm $_sc_probe
    else
        # Nothing to ask, so ask for all of it.
        printf '%s' "$_sc_probe"
    fi
}

# True when any of the named packages is missing.
prereqs_missing() {
    [ -n "$(_sc_missing_pkgs "$@")" ]
}

# Install the listed packages, skipping any the system already has. Leading
# flags (--skip-broken, say) are passed to the package manager rather than
# probed as package names.
install_prereqs() {
    _sc_flags=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            -*)
                _sc_flags="$_sc_flags $1"
                shift
                ;;
            *) break ;;
        esac
    done

    if [ "$#" -eq 0 ]; then
        return 0
    fi

    _sc_needed=$(_sc_missing_pkgs "$@")

    if [ -z "$_sc_needed" ]; then
        echo "Prerequisites already installed, skipping install: $*"
        return 0
    fi

    echo "Installing missing prerequisites (requires root):$_sc_needed"

    # Word splitting of the flag and package lists is intended throughout.
    case "$_sc_backend" in
        deb)
            apt_update
            # shellcheck disable=SC2086
            $_sc_sudo apt-get install -y $_sc_flags $_sc_needed
            ;;
        rpm)
            # shellcheck disable=SC2086
            $_sc_sudo $_sc_yum install -y $_sc_flags $_sc_needed
            ;;
        *)
            echo "install_prereqs: no supported package manager found" >&2
            return 1
            ;;
    esac
}

# Mandatory members of the "Development Tools" group, which is the only group
# these scripts install. Verified identical on RHEL 8 and RHEL 9.
_SC_GROUP_DEVELOPMENT_TOOLS="autoconf automake binutils bison flex gcc gcc-c++
gdb glibc-devel libtool make pkgconf pkgconf-m4 pkgconf-pkg-config
redhat-rpm-config rpm-build rpm-sign strace"

# Install a package group unless its payload is already present.
#
# A group has no reliable installed-state probe of its own: `dnf group list
# --installed` still reports a group as installed after its member packages have
# been removed, so asking about the group can answer yes and be wrong. Ask about
# the packages instead -- if every mandatory member is installed then the group
# install has nothing to do, and a group this helper does not know the payload of
# is installed unconditionally.
install_prereq_group() {
    _sc_group=$1

    case "$_sc_group" in
        "Development Tools") _sc_payload="$_SC_GROUP_DEVELOPMENT_TOOLS" ;;
        *) _sc_payload="" ;;
    esac

    # shellcheck disable=SC2086
    if [ -n "$_sc_payload" ] && ! prereqs_missing $_sc_payload; then
        echo "Group already installed, skipping install: $_sc_group"
        return 0
    fi

    echo "Installing group (requires root): $_sc_group"
    $_sc_sudo $_sc_yum group install -y "$_sc_group"
}

# Echo the subset of "$@" that is installed. The mirror of _sc_missing_pkgs, and
# the reason it exists is asymmetric with installing: "apt-get remove" exits 100
# on a package name it does not recognise, and once tool.docker has cleaned
# /var/lib/apt/lists the only names apt recognises are the installed ones. So an
# unfiltered remove list fails the build the moment a tool's dependency set
# shifts and one of the names is no longer there.
_sc_installed_deb() {
    _sc_installed=""
    for _sc_pkg in "$@"; do
        if dpkg-query -W -f='${Status}' "$_sc_pkg" 2>/dev/null |
                grep -q '^install ok installed$'; then
            _sc_installed="$_sc_installed $_sc_pkg"
        fi
    done

    printf '%s' "$_sc_installed"
}

_sc_installed_rpm() {
    _sc_installed=""
    for _sc_pkg in "$@"; do
        if rpm -q "$_sc_pkg" > /dev/null 2>&1; then
            _sc_installed="$_sc_installed $_sc_pkg"
        fi
    done

    printf '%s' "$_sc_installed"
}

_sc_installed_pkgs() {
    set +x

    # Same probe selection as _sc_missing_pkgs: whichever query tool is present
    # decides, independently of which package manager will do the work. Without
    # a probe nothing is reported installed, so nothing is removed -- the safe
    # direction here, since the cost is an image that stays large.
    # Word splitting of the package list is intended.
    # shellcheck disable=SC2086
    if command -v dpkg-query > /dev/null 2>&1; then
        _sc_installed_deb "$@"
    elif command -v rpm > /dev/null 2>&1; then
        _sc_installed_rpm "$@"
    else
        printf '%s' ""
    fi
}

# Remove packages a tool needed to build but does not need to run, skipping any
# that are not installed.
#
#     sc_remove_prereqs PKG...
#
# Where install_prereqs errs toward installing, this errs toward keeping: a name
# the probe cannot confirm is installed is left alone rather than handed to the
# package manager. The worst case is a package that stays in the image, which is
# the behaviour this whole mechanism is trying to improve on rather than a
# regression from it.
#
# Deliberately no "apt-get autoremove". These images keep runtime libraries that
# arrived only as some build package's dependency -- libxcb-keysyms1 under
# libxcb-keysyms1-dev, libgmp10 under ghc, libllvm18 under llvm-18-dev -- and
# autoremove would take them along with the build packages, breaking the tool at
# run time rather than at build time.
sc_remove_prereqs() {
    if [ "$#" -eq 0 ]; then
        return 0
    fi

    _sc_drop=$(_sc_installed_pkgs "$@")

    if [ -z "$_sc_drop" ]; then
        echo "No build-only prerequisites to remove: $*"
        return 0
    fi

    echo "Removing build-only prerequisites:$_sc_drop"

    # Word splitting of the package list is intended.
    case "$_sc_backend" in
        deb)
            # shellcheck disable=SC2086
            $_sc_sudo apt-get remove -y --purge $_sc_drop
            ;;
        rpm)
            # shellcheck disable=SC2086
            $_sc_sudo $_sc_yum remove -y $_sc_drop
            ;;
        *)
            echo "sc_remove_prereqs: no supported package manager found" >&2
            return 1
            ;;
    esac
}

# Packages that look build-only by name but are needed at RUN time. Each entry
# is here because something invokes or links it after the build, which no
# dependency graph records:
#
#   zlib1g-dev   verilator compiles the generated model, and --trace-fst needs
#                zlib's headers; "ghdl -e" links -lz into every design
#   ccache       verilated.mk sets "OBJCACHE ?= ccache" and invokes it
#                unconditionally, so removing it breaks every model build
#   graphviz     yosys' "show" shells out to dot
#   xdot         the viewer "show" opens
#   libc6-dev    bambu compiles its 32-bit MDPI runtime at run time
#   libllvm18    ghdl1-llvm links libLLVM.so.18.1. Nothing records it: ghdl is
#                built from source, so the link never becomes a package
#                dependency, and once clang-18 and doxygen are classed as
#                removable below, libllvm18 looks free. It is not -- dropping it
#                breaks every "ghdl -e".
_SC_KEEP_BUILD_PKGS="zlib1g-dev ccache graphviz xdot libc6-dev libc-dev libllvm18"

# True when a package name is build-only material: headers and static libraries,
# the build tools, and documentation generators.
_sc_is_build_only() {
    case " $_SC_KEEP_BUILD_PKGS " in
        *" $1 "*) return 1 ;;
    esac

    case "$1" in
        *-dev) return 0 ;;
        cmake|cmake-data|ninja-build|autoconf|automake|libtool|libtool-bin|m4|bison|\
        flex|swig|pkg-config|pkgconf|dpkg-dev|build-essential|lcov|help2man|\
        autotools-dev|autopoint) return 0 ;;
        doxygen|pandoc|groff|texinfo|manpages-dev|perl-doc|icu-devtools) return 0 ;;
    esac

    # Distribution toolchain runtimes that arrive under a build dependency and
    # that no tool in the image links. Checked one at a time against every ELF
    # object in the prefix, because a shared library nothing links is dead
    # weight however much it looks like a runtime package:
    #
    #   libllvm17t64   orphaned outright -- no package depends on it and no
    #                  binary links libLLVM.so.17
    #   the clang-18   held up only by doxygen and by ghdl's "clang", both of
    #   stack          which are removed. ghdl links libllvm18 directly and
    #                  shells out to no compiler, so the front end is unused.
    #
    # libllvm18 is deliberately NOT here -- see _SC_KEEP_BUILD_PKGS.
    case "$1" in
        libllvm17*|llvm-17|llvm-17-*) return 0 ;;
        clang-18|clang|clang-format-18|libclang-cpp18|libclang1-18) return 0 ;;
        llvm-18-linker-tools|llvm-18-runtime|llvm-runtime) return 0 ;;
    esac

    # The MPI and ROCm stack that install-xyce.sh drags in through
    # libopenmpi-dev. SC builds Xyce serially -- "ldd Xyce" links no libmpi at
    # all -- so none of this is reachable, and it is a lot: libamd-comgr2 alone
    # is 59MB and it pulls libllvm17 behind it.
    #
    # Named rather than left to the dependency test because these are runtime
    # packages that legitimately depend on each other, so the test only sees a
    # self-consistent island and leaves all of it in place.
    case "$1" in
        libamd-comgr2|libamdhip64-*|libucx0|libopenmpi3*|openmpi-bin) return 0 ;;
    esac

    return 1
}

# Remove every build-only package that nothing outside that class depends on.
#
#     sc_remove_build_only
#
# A criterion rather than a list, because a list of package names goes stale the
# moment a tool changes its prerequisites, and because the names differ per
# distribution. What makes it safe is the second half: a candidate is dropped
# only when no package outside the build-only class declares a hard dependency
# on it. So clang-16's libclang-common-16-dev stays, g++'s libstdc++-13-dev
# stays, and the multilib set bambu needs stays -- without any of them being
# named here.
#
# Recommends and Suggests are deliberately not consulted. "apt-cache rdepends"
# reports them alongside real dependencies, which makes half the tree look
# load-bearing when it is not.
#
# This does not replace a tool's own docker-cmds removals: it only catches what
# the name patterns above describe, so a build-only package like ghc, gnat-13 or
# a distribution's llvm-18 still has to be named by the tool that installs it.
sc_remove_build_only() {
    if [ "$_sc_backend" != "deb" ]; then
        echo "sc_remove_build_only: deb only, skipping"
        return 0
    fi

    _sc_bo_deps=$(mktemp)
    _sc_bo_drop=""
    dpkg-query -W -f='${Package}\t${Depends}, ${Pre-Depends}\n' > "$_sc_bo_deps"

    for _sc_bo_pkg in $(dpkg-query -W -f='${Package}\n'); do
        _sc_is_build_only "$_sc_bo_pkg" || continue

        # A dependency can name a package through anything it Provides, not just
        # its real name, so the search has to cover both. The t64 transition made
        # this concrete: libamd-comgr2 depends on "libllvm17", which is a virtual
        # name libllvm17t64 provides, and matching the real name alone reported
        # libllvm17t64 as unreferenced when it was not.
        _sc_bo_names=$_sc_bo_pkg
        for _sc_bo_prov in $(dpkg-query -W -f='${Provides}' "$_sc_bo_pkg" 2>/dev/null |
                tr ',' ' ' | sed 's/([^)]*)//g'); do
            _sc_bo_names="$_sc_bo_names $_sc_bo_prov"
        done

        # Any hard dependant outside the class pins it in place.
        _sc_bo_blocked=""
        for _sc_bo_rd in $(awk -F'\t' -v names="$_sc_bo_names" '
                BEGIN { split(names, want, " ") }
                { n = $1; d = $2
                  gsub(/\([^)]*\)/, "", d); gsub(/ /, "", d)
                  split(d, parts, ",")
                  for (i in parts) {
                      split(parts[i], alts, "|")
                      for (j in alts) for (k in want) if (alts[j] == want[k]) print n
                  } }' "$_sc_bo_deps" | sort -u); do
            if ! _sc_is_build_only "$_sc_bo_rd"; then
                _sc_bo_blocked=$_sc_bo_rd
                break
            fi
        done

        [ -n "$_sc_bo_blocked" ] || _sc_bo_drop="$_sc_bo_drop $_sc_bo_pkg"
    done

    rm -f "$_sc_bo_deps"

    # Word splitting of the package list is intended.
    # shellcheck disable=SC2086
    sc_remove_prereqs $_sc_bo_drop
}

# Directories whose static archives are linked at RUN time, not build time, and
# so are not build artifacts however much they look like them:
#
#   lib/ghdl      libgrt.a, linked into every design by "ghdl -e"
#   lib/panda     bambu's softfloat and libm, linked into generated designs
#   lib/Bluesim   Bluespec's simulation kernel, linked by "bsc -sim"
_SC_RUNTIME_ARCHIVE_DIRS="ghdl panda Bluesim"

# Delete the build-only half of an install prefix: static archives, headers,
# and the build-system and documentation trees.
#
#     sc_prune_build_artifacts [DIR]
#
# $PREFIX/include and $PREFIX/lib/cmake are dev material by convention and no
# flow reads them. Note that the headers tools genuinely need at run time do not
# live there -- verilator's are under share/verilator/include and bambu's under
# share/panda -- so both survive.
sc_prune_build_artifacts() {
    _sc_prune_dir="${1:-${PREFIX:-}}"

    if [ -z "$_sc_prune_dir" ] || [ ! -d "$_sc_prune_dir" ]; then
        echo "sc_prune_build_artifacts: no prefix to prune" >&2
        return 0
    fi

    echo "Pruning build artifacts from $_sc_prune_dir"

    _sc_prune_args=""
    for _sc_prune_keep in $_SC_RUNTIME_ARCHIVE_DIRS; do
        _sc_prune_args="$_sc_prune_args ! -path */$_sc_prune_keep/*"
    done

    # shellcheck disable=SC2086
    find "$_sc_prune_dir" -name '*.a' $_sc_prune_args -delete 2>/dev/null

    rm -rf "$_sc_prune_dir/include" \
           "$_sc_prune_dir/lib/cmake" \
           "$_sc_prune_dir/lib/pkgconfig" \
           "$_sc_prune_dir/share/doc" \
           "$_sc_prune_dir/share/man"
}

# The binutils family on deb, including what binutils drags in transitively.
# sc_strip_prefix_managed installs binutils and then removes exactly the subset
# that was not there before, so everything the install can add has to be
# nameable -- without libctf0, libctf-nobfd0 and libsframe1 the removal leaves
# them orphaned and they land in apt.txt.
#
# Names absent on a distribution (rpm ships only "binutils") fall out on their
# own: they probe as missing, and sc_remove_prereqs re-probes and skips whatever
# the install did not actually add.
_SC_STRIP_PKGS="binutils binutils-common libbinutils binutils-x86-64-linux-gnu
    libctf0 libctf-nobfd0 libsframe1"

# Strip a prefix even on an image that has no "strip", borrowing binutils for
# the duration.
#
#     sc_strip_prefix_managed [DIR]
#
# Several tools build with bazel against a prebuilt toolchain and never install
# binutils, so plain sc_strip_prefix finds no strip and skips. It skips silently
# and on purpose -- a tool that builds is worth more than the bytes -- which is
# exactly why it went unnoticed that openroad was shipping 27MB of symbol
# tables and two verible binaries another 2MB.
#
# Installing binutils in the base builder image is the easy fix and the wrong
# one: it would land in every tool's apt.txt and ship in the runtime image, and
# it would retag every tool image to do it. Borrowing it here costs nothing,
# because apt.txt is generated after this runs.
sc_strip_prefix_managed() {
    if command -v strip > /dev/null 2>&1; then
        sc_strip_prefix "$@"
        return 0
    fi

    # Take back out exactly what this adds. On an image where part of the family
    # was already present, removing all of it would be a change this function
    # has no business making.
    # Word splitting of the package list is intended.
    # shellcheck disable=SC2086
    _sc_strip_added=$(_sc_missing_pkgs $_SC_STRIP_PKGS)

    install_prereqs binutils

    sc_strip_prefix "$@"

    # shellcheck disable=SC2086
    sc_remove_prereqs $_sc_strip_added
}

# Remove symbol tables and debug sections from everything installed under a
# prefix. Nothing in the flows reads them: they exist for debugging a tool build,
# and they are a third of the size of an installed tool tree.
#
#     sc_strip_prefix [DIR]      strip DIR, defaulting to $PREFIX
#
# Measured across the 30-tool container prefix: 6,497MB -> 5,500MB. About 300MB
# of that is .debug_* and 700MB is .symtab/.strtab, which is why this does a full
# strip rather than the more commonly seen --strip-debug.
#
# Executables are stripped outright. Shared objects get --strip-unneeded, which
# removes .symtab but keeps .dynsym -- the dynamic symbol table is what the
# loader and dlopen() resolve against, so stripping it would break every plugin
# in the tree (yosys' and bambu's included).
#
# Static archives are left alone. They are link-time only and stripping them
# risks breaking a later build against this prefix; the container drops them
# wholesale instead.
sc_strip_prefix() {
    _sc_strip_dir="${1:-${PREFIX:-}}"

    if [ -z "$_sc_strip_dir" ] || [ ! -d "$_sc_strip_dir" ]; then
        echo "sc_strip_prefix: no prefix to strip" >&2
        return 0
    fi

    if ! command -v strip > /dev/null 2>&1; then
        echo "sc_strip_prefix: strip not available, skipping" >&2
        return 0
    fi

    echo "Stripping symbols from $_sc_strip_dir"

    # Only ELF objects. A wrong guess from the filename is not enough -- the
    # prefixes carry shell wrappers, Tcl, Python and the odd foreign-platform
    # binary, and "strip" on those either fails or corrupts them. Check the
    # magic number instead.
    # Static archives are excluded explicitly rather than left to chance. They
    # are usually mode 644 and so would not match -perm -u+x anyway, but three
    # tools ship an archive their runtime links against -- lib/ghdl/libgrt.a,
    # lib/panda/*.a, lib/Bluesim/*.a -- and stripping one breaks linking against
    # it, which is not a failure worth risking on a mode bit.
    find "$_sc_strip_dir" -type f ! -name '*.a' \
        \( -perm -u+x -o -name '*.so' -o -name '*.so.*' \) \
        -print 2>/dev/null | while IFS= read -r _sc_obj; do
        case "$(dd if="$_sc_obj" bs=4 count=1 2>/dev/null | od -An -tx1 | tr -d ' \n')" in
            7f454c46) ;;
            *) continue ;;
        esac

        case "$_sc_obj" in
            *.so|*.so.*) _sc_strip_args="--strip-unneeded" ;;
            *)           _sc_strip_args="--strip-all" ;;
        esac

        # A refusal is not fatal. Some objects legitimately cannot be stripped,
        # and a tool that builds is worth more than the bytes.
        strip $_sc_strip_args --preserve-dates "$_sc_obj" 2>/dev/null || \
            echo "  could not strip $_sc_obj" >&2
    done
}
