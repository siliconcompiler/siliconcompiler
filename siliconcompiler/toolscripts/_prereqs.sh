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

# True when dpkg reports PKG fully installed for this machine's architecture.
_sc_deb_installed() {
    # Test the status string rather than using `dpkg -s`, which also succeeds
    # for a removed-but-not-purged package whose config files are all that is
    # left. "install ok installed" is the state that means the package is
    # actually there.
    #
    # A Multi-Arch: same package such as zlib1g-dev gets a line per installed
    # architecture once a foreign one is enabled, and only a native or
    # architecture-independent copy builds a native tool. An i386 copy alone
    # therefore reads as missing.
    dpkg-query -W -f='${Architecture} ${Status}\n' "$1" 2>/dev/null |
        grep -Eq "^($(dpkg --print-architecture)|all) install ok installed$"
}

# Echo the subset of "$@" that dpkg does not report as fully installed.
_sc_missing_deb() {
    _sc_missing=""
    for _sc_pkg in "$@"; do
        if ! _sc_deb_installed "$_sc_pkg"; then
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

# Echo the mandatory members of a package group, as the package manager reports
# them. Empty when it cannot say -- an unknown group, an older dnf that words
# the heading differently, or no group support at all.
_sc_group_payload() {
    set +x

    if [ "$_sc_backend" != "rpm" ]; then
        return 0
    fi

    # "Mandatory Packages:" only. Default and optional members can legitimately
    # be absent from a fully installed group, so probing them would report the
    # group as missing forever and install it on every run.
    $_sc_yum group info "$1" 2>/dev/null | awk '
        /^ *Mandatory Packages:/ { in_block = 1; next }
        /^ *[A-Za-z][A-Za-z ]*:/ { in_block = 0 }
        in_block {
            gsub(/^[ \t]+/, ""); gsub(/[ \t]+$/, "")
            # dnf marks installed members with a leading "+" or "-"
            sub(/^[+-]/, "")
            if ($0 != "") print
        }'
}

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

    # What the group contains is the package manager's answer to give, not a
    # copy of it kept here: a list would go stale against the distribution and
    # would have to be written out per release. A query that fails or returns
    # nothing leaves the payload empty, which installs -- the same answer this
    # gave for a group it did not recognise.
    _sc_payload=$(_sc_group_payload "$_sc_group")

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
        if _sc_deb_installed "$_sc_pkg"; then
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

# Per-image exceptions to the classification below, set by sc_remove_build_only
# from its own arguments. They are per image and not a list here on purpose: a
# package is build-only or not according to the tool that installed it, and a
# global list of tool facts in this file makes every tool image depend on every
# other tool's exceptions. _prereqs.sh feeds the check tag of all 30 tool
# images, so one tool's exception would rebuild all of them.
#
# The tool declares them in _tools.json instead -- "docker-keep-pkgs" for a
# package it needs at run time, "docker-drop-pkgs" for one only its build needs
# -- and siliconcompiler/data/docker/tool.docker passes them here.
_sc_keep_pkgs=""
_sc_drop_pkgs=""

# True when a package name is build-only material: headers and static libraries,
# the build tools, and documentation generators.
#
# This is the definition of the class, and the only naming left in this file:
# the conventions every deb image shares, which class the same way whatever
# built the image. A package that is build-only in one image and load-bearing
# in another is not a rule, it is a fact about a tool, and it belongs in that
# tool's _tools.json entry -- "docker-keep-pkgs" to hold one back,
# "docker-drop-pkgs" to add one. Putting such a name here instead makes every
# one of the 30 tool images depend on it: _prereqs.sh feeds all of their check
# tags, so one tool's exception rebuilds all of them.
#
# dpkg's own Section field is the obvious way to have no names here at all, and
# it does not work: measured on ubuntu 24.04, section "devel" holds gcc, g++,
# make, ccache and binutils along with cmake and autoconf, so classing by it
# sweeps the toolchain verilator invokes to compile the model it generates and
# the clang bambu shells out to. It also misses pandoc, groff and texinfo,
# which sit in "text" and "perl". Keeping the patterns costs one rebuild of
# everything on the rare occasion they change, which is honest: a change here
# does change every image.
_sc_is_build_only() {
    # Word splitting of the pattern lists is intended: each entry is a case
    # pattern, so "libllvm17*" matches the family without naming every member.
    # shellcheck disable=SC2086
    for _sc_bo_pat in $_sc_keep_pkgs; do
        case "$1" in
            $_sc_bo_pat) return 1 ;;
        esac
    done

    # shellcheck disable=SC2086
    for _sc_bo_pat in $_sc_drop_pkgs; do
        case "$1" in
            $_sc_bo_pat) return 0 ;;
        esac
    done

    case "$1" in
        *-dev) return 0 ;;
        cmake|cmake-data|ninja-build|autoconf|automake|libtool|libtool-bin|m4|bison|\
        flex|swig|pkg-config|pkgconf|dpkg-dev|build-essential|lcov|help2man|\
        autopoint) return 0 ;;
        doxygen|pandoc|groff|texinfo|perl-doc|icu-devtools) return 0 ;;
    esac

    return 1
}

# Remove every build-only package that nothing outside that class depends on.
#
#     sc_remove_build_only [--keep "PATTERN..."] [--drop "PATTERN..."]
#
# --keep protects packages this image needs at run time that the rules above
# would otherwise class as build-only: verilator's zlib1g-dev, which it needs to
# compile the model it generates. --drop adds packages those rules do not
# recognise but this image has no use for: the distribution clang stack that
# arrives under ghdl's "llvm-dev", or the ROCm and MPI libraries that arrive
# under xyce's libboost-all-dev and that nothing links. Both take shell case
# patterns ("libllvm17*"), and both are per image: the tool declares them in its
# _tools.json entry and tool.docker passes them.
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
    _sc_keep_pkgs=""
    _sc_drop_pkgs=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --keep) _sc_keep_pkgs="$_sc_keep_pkgs $2"; shift 2 ;;
            --drop) _sc_drop_pkgs="$_sc_drop_pkgs $2"; shift 2 ;;
            *)
                echo "sc_remove_build_only: unknown argument $1" >&2
                return 1
                ;;
        esac
    done

    if [ "$_sc_backend" != "deb" ]; then
        echo "sc_remove_build_only: deb only, skipping"
        return 0
    fi

    _sc_bo_class=$(mktemp)
    _sc_bo_deps=$(mktemp)

    # The shell owns the classification, because _sc_is_build_only is a shell
    # function; awk below owns the graph.
    for _sc_bo_pkg in $(dpkg-query -W -f='${Package}\n'); do
        if _sc_is_build_only "$_sc_bo_pkg"; then
            printf '%s\tb\n' "$_sc_bo_pkg"
        else
            printf '%s\tp\n' "$_sc_bo_pkg"
        fi
    done > "$_sc_bo_class"

    dpkg-query -W -f='${Package}\t${Provides}\t${Depends}, ${Pre-Depends}\n' \
        > "$_sc_bo_deps"

    # "apt-get remove X" takes everything that depends on X as well, so a
    # candidate is only safe to drop when its whole reverse-dependency closure
    # is also droppable. Checking one level deep is not enough: with a protected
    # package K depending on build-only M depending on build-only C, M is
    # correctly held back by K, but dropping C still takes M and K with it.
    #
    # So this grows the protected set to a fixpoint instead -- any build-only
    # package with a protected dependent becomes protected, repeatedly, until
    # nothing changes. What is left unprotected is safe to remove.
    _sc_bo_drop=$(awk -F'\t' '
        FNR == NR { class[$1] = $2; next }

        {
            pkg = $1
            pkgs[++np] = pkg

            # Every alternative name this package answers to, so a dependency
            # written against a virtual name still resolves. The t64 transition
            # made this concrete: libamd-comgr2 depends on "libllvm17", a name
            # libllvm17t64 provides rather than its own.
            n = split($2, provs, ",")
            for (i = 1; i <= n; i++) {
                gsub(/\([^)]*\)/, "", provs[i]); gsub(/[ ]/, "", provs[i])
                if (provs[i] != "") alias[provs[i]] = pkg
            }

            d = $3
            gsub(/\([^)]*\)/, "", d); gsub(/[ ]/, "", d)
            depends[pkg] = d
        }

        END {
            # Reverse edges: for each package, which packages depend on it.
            for (p = 1; p <= np; p++) {
                pk = pkgs[p]
                n = split(depends[pk], parts, ",")
                for (i = 1; i <= n; i++) {
                    m = split(parts[i], alts, "|")
                    for (j = 1; j <= m; j++) {
                        t = alts[j]
                        if (t == "") continue
                        if (!(t in class) && (t in alias)) t = alias[t]
                        if (t in class) rdep[t] = rdep[t] " " pk
                    }
                }
            }

            changed = 1
            while (changed) {
                changed = 0
                for (t in rdep) {
                    if (class[t] != "b") continue
                    n = split(rdep[t], ds, " ")
                    for (i = 1; i <= n; i++) {
                        if (ds[i] != "" && class[ds[i]] == "p") {
                            class[t] = "p"
                            changed = 1
                            break
                        }
                    }
                }
            }

            for (p = 1; p <= np; p++) {
                if (class[pkgs[p]] == "b") printf "%s ", pkgs[p]
            }
        }' "$_sc_bo_class" "$_sc_bo_deps")

    rm -f "$_sc_bo_class" "$_sc_bo_deps"

    # Word splitting of the package list is intended.
    # shellcheck disable=SC2086
    sc_remove_prereqs $_sc_bo_drop
}

# Delete what a tool says its prefix holds that is build-only.
#
#     sc_prune_build_artifacts [DIR] [--dirs "PATH..."]
#
# Each PATH is relative to the prefix and may be a glob: "include",
# "lib/pkgconfig", "lib/*.a", "trilinos/lib/*.a". Nothing else goes. There is no
# blanket rule and no exception list to go with it -- an earlier version deleted
# every *.a in the prefix and then had to be told, by name, about the three
# directories whose archives are linked at RUN time (ghdl's lib/ghdl/libgrt.a
# for "ghdl -e", lib/panda for bambu's generated designs, lib/Bluesim for
# "bsc -sim"). A tool that lists "lib/*.a" says the same thing without the
# exception, because the glob does not reach into lib/ghdl.
#
# Two things are reported rather than enforced, because a wrong list here costs
# image size and a build failure costs a tool:
#
#   - an entry that matches nothing is called out, so a path that upstream
#     stopped shipping shows up in the build log instead of rotting
#   - archives left in the prefix are listed, so a tool that has never declared
#     them is one grep of a build log away from a correct list
#
# Note that the headers a tool needs at run time do not live in the prefix's own
# include/ -- verilator's are under share/verilator/include and bambu's under
# share/panda -- which is why "include" is safe for a tool to list.
sc_prune_build_artifacts() {
    _sc_prune_dir=""
    _sc_prune_dirs=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --dirs) _sc_prune_dirs="$_sc_prune_dirs $2"; shift 2 ;;
            -*)
                echo "sc_prune_build_artifacts: unknown argument $1" >&2
                return 1
                ;;
            *) _sc_prune_dir="$1"; shift ;;
        esac
    done
    _sc_prune_dir="${_sc_prune_dir:-${PREFIX:-}}"

    if [ -z "$_sc_prune_dir" ] || [ ! -d "$_sc_prune_dir" ]; then
        echo "sc_prune_build_artifacts: no prefix to prune" >&2
        return 0
    fi

    echo "Pruning build artifacts from $_sc_prune_dir"

    for _sc_prune_entry in $_sc_prune_dirs; do
        _sc_prune_hit=""
        # Unquoted on purpose: the entry is a glob and this is where it expands.
        # The prefix stays quoted, so a path with a space in it still works.
        for _sc_prune_path in "$_sc_prune_dir"/$_sc_prune_entry; do
            [ -e "$_sc_prune_path" ] || continue
            rm -rf "$_sc_prune_path"
            _sc_prune_hit="yes"
        done

        if [ -z "$_sc_prune_hit" ]; then
            echo "  nothing matched, drop it from docker-prune-dirs: $_sc_prune_entry"
        fi
    done

    # Static archives are link-time material in every prefix that has them, so
    # one left behind is either a tool that links it at run time or a list that
    # has not caught up. Reported, never guessed at.
    _sc_prune_left=$(find "$_sc_prune_dir" -name '*.a' 2>/dev/null)
    if [ -n "$_sc_prune_left" ]; then
        echo "  static archives left in the prefix, declare the build-only ones:"
        echo "$_sc_prune_left" | sed "s|^$_sc_prune_dir/|    |"
    fi
}

# Echo every installed package name, one per line, sorted. Empty when there is
# no probe to ask, which makes the caller's before/after diff empty too -- the
# safe direction, since the cost is a package left installed.
_sc_installed_names() {
    set +x

    if command -v dpkg-query > /dev/null 2>&1; then
        dpkg-query -W -f='${Package}\n' 2>/dev/null | sort
    elif command -v rpm > /dev/null 2>&1; then
        rpm -qa --qf '%{NAME}\n' 2>/dev/null | sort
    fi
}

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

    # Take back out exactly what this adds, by comparing the installed set
    # before and after rather than by naming the binutils family: what
    # "apt-get install binutils" pulls in differs by distribution and moves
    # between releases -- libsframe1 and libctf-nobfd0 both appeared in one --
    # and a list that misses one leaves it installed and shipping. On an image
    # where part of the family was already present, the diff leaves it alone.
    _sc_strip_before=$(mktemp)
    _sc_strip_after=$(mktemp)

    _sc_installed_names > "$_sc_strip_before"
    install_prereqs binutils
    _sc_installed_names > "$_sc_strip_after"

    _sc_strip_added=$(comm -13 "$_sc_strip_before" "$_sc_strip_after" | tr '\n' ' ')
    rm -f "$_sc_strip_before" "$_sc_strip_after"

    sc_strip_prefix "$@"

    # Word splitting of the package list is intended.
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
