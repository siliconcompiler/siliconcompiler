'''
``python3 -m siliconcompiler.remote.server.software.registry``

The operator's command for the image registry: which distributions this
deployment curates, at which versions, and which containers hold them.

🔴 Every write names the person on the host running it, and a tag is resolved to
a digest once, here (`images.register_image`). ⚠️ A separate entry point that
works on a datadir, not a running server, so a deployment can be curated before
it first starts; the portal calls the same `images` functions.
'''

import argparse
import getpass
import json
import logging
import re
import socket
import sys

from pathlib import Path
from typing import List, Optional

from siliconcompiler.remote.server.config import Config
from siliconcompiler.remote.server.software import images, probe
from siliconcompiler.remote.server.state.store import Store, StoreVersionError

__all__ = ["main"]


logger = logging.getLogger("sc-server")

# An administrative action is a person's (identity.md): here, whoever has a shell
# on the host, under an issuer of its own so it never collides with an API login.
OPERATOR_ISSUER = "operator"


def _operator(store) -> str:
    '''The user id every write in this session is recorded against.'''
    subject = f"{getpass.getuser()}@{socket.gethostname()}"
    with store.transaction():
        user = store.upsert_user(OPERATOR_ISSUER, subject, display_name=subject)
    return user["id"]


def _wants(values: Optional[List[str]]):
    '''``-requires openroad>=26.3`` into pairs, with any PEP 440 operator.

    🔴 Not `images._contains`, which accepts only exact stored versions.
    '''
    pairs = []
    for value in values or []:
        found = re.match(r"^\s*([^=!<>~\s]+)\s*(.*)$", value)
        if not found or not found.group(1):
            raise SystemExit(f"{value!r} is not name<specifier>")
        name, spec = found.group(1), found.group(2).strip()
        pairs.append((name, spec or None))
    return pairs


def _resolve_digest(registry_ref: str) -> str:
    '''Pin a tag to the bytes it names right now, once (`images.pinned_ref`).'''
    try:
        import docker
    except ModuleNotFoundError:                                  # pragma: no cover
        raise SystemExit("resolving a tag needs the docker package; "
                         "pass -digest sha256:... instead")

    client = docker.from_env()
    try:
        image = client.images.get(registry_ref)
    except Exception:                                            # noqa: BLE001
        image = client.images.pull(registry_ref)

    for digest in image.attrs.get("RepoDigests") or []:
        return digest.split("@", 1)[1]

    # Never pushed: its id hashes the config, not the manifest, so it is refused.
    raise SystemExit(
        f"{registry_ref} has no repository digest: push it to a registry, or "
        "pass -digest sha256:... if you know the one it will have")


######################################################################
# The commands
######################################################################

def _cmd_list(store, args) -> int:
    catalogue = images.catalogue(store, include_retired=args.all)

    if args.json:
        print(json.dumps(catalogue, indent=2))
        return 0

    versions = {}
    for row in catalogue["versions"]:
        versions.setdefault(row["software_name"], []).append(row)

    print("software")
    for row in catalogue["software"] or []:
        retired = " (retired)" if row["retired_at"] else ""
        driven = f"  driven by {row['driver']}" if row["driver"] else ""
        print(f"  {row['name']}  {row['kind']}{driven}{retired}")
        for version in versions.get(row["name"], []):
            mark = " (retired)" if version["retired_at"] else ""
            if version["version_source"] != "reported":
                mark += "  (no version reported)"
            print(f"    {version['version']}  preference {version['preference']}{mark}")
    if not catalogue["software"]:
        print("  (none)")

    print("images")
    for row in catalogue["images"] or []:
        retired = " (retired)" if row["retired_at"] else ""
        print(f"  {row['registry_ref']}{retired}")
        print(f"    {row['id']}")
        print(f"    {row['digest']}")
        if row["built_at"]:
            print(f"    built {row['built_at']}")
        print(f"    holds {', '.join(row['contents']) or '(nothing)'}")
    if not catalogue["images"]:
        print("  (none)")

    if catalogue["derived"]:
        print("built environments")
        for row in catalogue["derived"]:
            retired = " (retired)" if row["retired_at"] else ""
            print(f"  {row['registry_ref']}{retired}")
            print(f"    {row['digest']}")
            print(f"    on {row['base']}")
            print(f"    installed {', '.join(row['installed']) or '(nothing)'}")

    return 0


def _cmd_add_software(store, args) -> int:
    kind = args.kind or ("tool" if args.driver else None)
    if not kind:
        # 🔴 Refused, not defaulted: the kind decides whether one image or each
        # node's must hold it.
        raise SystemExit(
            f"{args.name}: say -kind python, -kind tool or -kind interpreter. A "
            "tool with a driver can say -driver instead, which implies it")

    try:
        allowed = list(Config.load(Path(args.datadir).resolve())["software_drivers"] or [])
    except Exception:                                            # noqa: BLE001
        allowed = []
    try:
        images.register_software(store, args.name, args.display or args.name,
                                 _operator(store), kind, driver=args.driver,
                                 version_package=args.version_package,
                                 allowed_drivers=allowed)
    except ValueError as e:
        raise SystemExit(str(e))

    print(f"registered {args.name} as {kind}")
    if args.driver:
        print(f"  driven by {args.driver}")
    if args.version_package:
        print(f"  version read from the {args.version_package} distribution")
    elif kind == "tool" and not args.driver:
        print("  nothing here drives it, so no version can be read from an "
              "image: register its versions with -unversioned")
    return 0


def _cmd_add_version(store, args) -> int:
    source = "published_date" if args.unversioned else "reported"
    try:
        stored = images.register_version(
            store, args.name, args.version, _operator(store),
            preference=args.preference, source=source)
    except ValueError as e:
        raise SystemExit(str(e))

    print(f"registered {args.name}=={stored}")
    if stored != args.version:
        print(f"  normalised from {args.version}")
    if args.unversioned:
        print("  marked published_date: it can never satisfy a version "
              "requirement, and it always sorts below a reported version")
    return 0


def _cmd_add_image(store, args) -> int:
    digest = args.digest or _resolve_digest(args.ref)

    try:
        contents = images._contains(args.contains)
        image_id = images.register_image(
            store, args.ref, digest, contents, _operator(store),
            note=args.note, built_at=args.built)
    except ValueError as e:
        raise SystemExit(str(e))

    print(f"registered {args.ref}")
    print(f"  {image_id}")
    print(f"  {digest}")

    # 🔴 One SiliconCompiler, this server's (profile §5).
    held = [version for name, version in contents if name == images.PRIMARY]
    if not any(images.normalize(version) == images.normalize(images.own_version())
               for version in held):
        print(f"warning: this image holds siliconcompiler "
              f"{', '.join(held) if held else '(none)'}, and this server runs "
              f"{images.own_version()}: it will be neither advertised nor used",
              file=sys.stderr)

    if args.stage:
        print(f"  {_stage(args, images.pinned_ref(args.ref, digest), digest)}")

    return 0


def _stage(args, ref: str, digest: str):
    '''Unpack one image where a Slurm job can run it, keeping that off the first submit.'''
    datadir = Path(args.datadir).resolve()

    # 🔴 The server's own mount list, or the bundle quietly lacks what the
    # cluster needs. Never the data directory: per-job mounts are the job's.
    mounts = [str(path) for path in (Config.load(datadir)["container_mounts"] or [])]

    try:
        return images.stage_bundle(datadir / "images", ref, digest,
                                   mounts=mounts)
    except Exception as e:                                       # noqa: BLE001
        raise SystemExit(f"could not stage {ref}: {e}")


def _cmd_stage(store, args) -> int:
    '''Unpack every live image, or one of them.'''
    staged = 0
    for image in images.live_images(store):
        if args.image and image["id"] != args.image:
            continue
        ref = images.pinned_ref(image["registry_ref"], image["digest"])
        print(f"{image['registry_ref']}")
        print(f"  {_stage(args, ref, image['digest'])}")
        staged += 1

    if not staged:
        print("nothing to stage")
    return 0


def _cmd_retire(store, args) -> int:
    actor = _operator(store)

    if args.what == "image":
        images.retire_image(store, args.name, actor)
    elif args.what == "version":
        name, sep, version = args.name.partition("==")
        if not sep:
            raise SystemExit("retiring a version takes name==version")
        images.retire_version(store, name, version, actor)
    else:
        images.retire_software(store, args.name, actor)

    print(f"retired {args.what} {args.name}")
    return 0


def _cmd_drop_built(store, args) -> int:
    '''Drop every built Python environment holding a distribution.'''
    from siliconcompiler.remote.server.jobs.pythonenv import ENVIRONMENTS

    name, _, version = args.distribution.partition("==")
    dropped = images.drop_built(store, name, version or None, _operator(store),
                                environments=Path(args.datadir).resolve() / ENVIRONMENTS)
    for one in dropped:
        print(f"dropped {one}")
    if not dropped:
        print(f"nothing built holds {args.distribution}")
    return 0


def _cmd_resolve(store, args) -> int:
    '''Ask what a job would be placed in, without submitting one; writes nothing.'''
    # 🔴 Two buckets, resolved differently (`images.live_software`); no interpreter.
    requires = {"python": dict(_wants(args.versions)),
                "tools": dict(_wants(args.requires))}
    tools = {(tool, "0"): tool for tool in (args.tools or [])} or {("job", "0"): None}

    try:
        plan = images.plan_for_job(store, requires, tools)
    except Exception as e:                                       # noqa: BLE001
        print(str(e))
        return 1

    refs = {image["id"]: image["registry_ref"] for image in images.live_images(store)}
    print(f"job: {refs.get(plan.job, '(none)')}")
    for (step, _), image_id in sorted(plan.nodes.items()):
        print(f"  {step}: {refs.get(image_id, '(none)')}")
    return 0


_SCALE = {"": 1, "k": 1024, "ki": 1024, "m": 1024 ** 2, "mi": 1024 ** 2,
          "g": 1024 ** 3, "gi": 1024 ** 3, "t": 1024 ** 4, "ti": 1024 ** 4}


def _bytes(text: str) -> Optional[int]:
    """`unlimited` (-1), `inherit` (None, the deployment's value), or a size."""
    value = text.strip().lower()
    if value in ("inherit", "default", "none"):
        return None
    if value in ("unlimited", "-1"):
        return -1

    match = re.fullmatch(r"(\d+)\s*([kmgt]i?)?b?", value)
    if not match:
        raise SystemExit(
            f"{text!r} is not a size: try 100MiB, unlimited, or inherit")
    return int(match.group(1)) * _SCALE[match.group(2) or ""]


def _cmd_limits(store, args) -> int:
    """Show or set what one account is allowed.

    🔴 The whole write path: with no admin mode there is no endpoint or form.
    """
    from siliconcompiler.remote.server.identity import accounts

    config = Config.load(Path(args.datadir).resolve())

    if args.user:
        who = store.one(
            "SELECT id FROM users WHERE id = ? OR subject = ?",
            (args.user, args.user))
        if who is None:
            raise SystemExit(f"no such user: {args.user}")
        people = [who["id"]]
    else:
        people = [row["id"] for row in store.all("SELECT id FROM users ORDER BY id")]

    if args.set:
        if not args.user:
            raise SystemExit("-set needs a user")
        name, sep, value = args.set.partition("=")
        if not sep:
            raise SystemExit("-set takes name=value, e.g. max_download_bytes=1GiB")
        try:
            accounts.set_limit(store, people[0], name.strip(), _bytes(value),
                               _operator(store), note=args.note)
        except ValueError as e:
            raise SystemExit(str(e))

    for user_id in people:
        row = store.one("SELECT * FROM users WHERE id = ?", (user_id,))
        effective = accounts.effective_limits(store, config, user_id)
        override = store.one(
            "SELECT * FROM user_limits WHERE user_id = ?", (user_id,))

        print(f"{user_id}  {row['issuer']}:{row['subject']}")
        for name in accounts.OVERRIDABLE:
            value = effective[name]
            shown = "unlimited" if value is None else str(value)
            source = "set" if override and override[name] is not None else "default"
            print(f"  {name} = {shown}  ({source})")
        if override and override["note"]:
            print(f"  note: {override['note']}")

    return 0


def _cmd_release(store, args) -> int:
    """Release a subject's key binding, so its next login enrols a new key.

    🔴 A person does it, or anybody could claim somebody else's key was lost.
    """
    from siliconcompiler.remote.server.identity.auth import TokenIssuer

    who = store.one("SELECT id, issuer, subject FROM users WHERE id = ? OR subject = ?",
                    (args.user, args.user))
    if who is None:
        raise SystemExit(f"no such user: {args.user}")

    issuer = TokenIssuer(Path(args.datadir).resolve(), store)
    released = issuer.release_binding(who["id"], _operator(store))
    print(f"{who['id']}  {who['issuer']}:{who['subject']}: released "
          f"{released} device{'s' if released != 1 else ''}; its next login enrols a "
          "new key")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m siliconcompiler.remote.server.software.registry",
        description="Curate what a SiliconCompiler server runs jobs in.")
    parser.add_argument(
        "-datadir", default="./sc_server", metavar="<dir>",
        help="the server's data directory (default: %(default)s)")

    commands = parser.add_subparsers(dest="command", required=True)

    listing = commands.add_parser("list", help="show the registry")
    listing.add_argument("-all", action="store_true", help="include retired rows")
    listing.add_argument("-json", action="store_true", help="as JSON")
    listing.set_defaults(run=_cmd_list)

    software = commands.add_parser(
        "add-software",
        help="declare that this deployment curates images for a distribution")
    software.add_argument("name", help="the distribution name: siliconcompiler, openroad")
    software.add_argument(
        "-kind", choices=probe.KINDS,
        help="python, tool, or interpreter for the one name python -- an image's "
             "own Python, which a node running the user's Python is matched on. "
             "Required unless -driver is given, which implies tool")
    software.add_argument(
        "-driver", metavar="<module>",
        help="the module carrying this tool's Task driver. Spelled out and "
             "never defaulted from the name: kepler-formal is driven from "
             "siliconcompiler.tools.keplerformal, so a convention that is "
             "right most of the time is wrong exactly where nobody looks")
    software.add_argument(
        "-version-package", dest="version_package", metavar="<distribution>",
        help="read this tool's version from a python distribution of this "
             "name instead of by running it: pyslang, for the tool slang")
    software.add_argument("-display", metavar="<text>", help="what to call it")
    software.set_defaults(run=_cmd_add_software)

    version = commands.add_parser("add-version", help="one exact version of it")
    version.add_argument("name")
    version.add_argument("version")
    version.add_argument(
        "-preference", type=int, default=0, metavar="<int>",
        help="higher is offered first, and breaks a tie between two images "
             "that both fit (default: %(default)s)")
    version.add_argument(
        "-unversioned", action="store_true",
        help="this tool reports no version, so <version> is the date its "
             "image was published. Listing it beats leaving it out, but it "
             "can never satisfy a version requirement")
    version.set_defaults(run=_cmd_add_version)

    image = commands.add_parser("add-image", help="a container this server may run")
    image.add_argument("ref", help="ghcr.io/org/sc-runtime:0.39.1")
    image.add_argument(
        "-digest", metavar="sha256:...",
        help="what it pins to. Resolved from the tag through docker if omitted")
    image.add_argument(
        "-contains", action="append", metavar="name==version",
        help="what is inside it, repeatable. Declared and unverified: nothing "
             "opens the image to check, so a wrong one fails at run time")
    image.add_argument(
        "-built", metavar="<when>",
        help="when the IMAGE was built, from its own manifest. Breaks the tie "
             "between two images carrying identical versions, which preference "
             "cannot -- and it is never the time you registered it, or pinning "
             "an old image on purpose would make it the newest")
    image.add_argument("-note", metavar="<text>")
    image.add_argument(
        "-stage", action="store_true",
        help="unpack it into an OCI bundle now. Needed before a Slurm cluster "
             "can run it, and doing it here keeps the unpack off the first "
             "submit that wants it")
    image.set_defaults(run=_cmd_add_image)

    stage = commands.add_parser(
        "stage", help="unpack registered images into OCI bundles")
    stage.add_argument(
        "image", nargs="?", metavar="<id>",
        help="one image id; every live image if omitted")
    stage.set_defaults(run=_cmd_stage)

    retire = commands.add_parser(
        "retire", help="stop using one, and keep the row")
    retire.add_argument("what", choices=("image", "version", "software"))
    retire.add_argument("name", help="an image id, name==version, or a name")
    retire.set_defaults(run=_cmd_retire)

    drop = commands.add_parser(
        "drop-built",
        help="stop reusing every built Python environment holding a distribution, "
             "or one at a version: derived images are retired, host environments "
             "removed, and the next job builds its set again")
    drop.add_argument("distribution", help="a name, or name==version")
    drop.set_defaults(run=_cmd_drop_built)

    resolve = commands.add_parser(
        "resolve", help="what a job would be placed in, without submitting one")
    resolve.add_argument(
        "-versions", action="append", metavar="name==version",
        help="what the job requires of the PYTHON bucket, repeatable. One "
             "image has to hold all of it")
    resolve.add_argument(
        "-requires", action="append", metavar="name==version",
        help="what it requires of a TOOL, repeatable. Satisfied per node")
    resolve.add_argument(
        "-tools", action="append", metavar="<tool>",
        help="one node per tool, repeatable")
    resolve.set_defaults(run=_cmd_resolve)

    limits = commands.add_parser(
        "limits", help="what one account is allowed, and setting it")
    limits.add_argument("user", nargs="?", help="a user id or subject; omit for all")
    limits.add_argument(
        "-set", metavar="name=value",
        help="max_download_bytes=1GiB, =unlimited, or =inherit")
    limits.add_argument("-note", help="why, for whoever reads this later")
    limits.set_defaults(run=_cmd_limits)

    release = commands.add_parser(
        "release-binding",
        help="let a user log in with a new key: ends their device's sessions and "
             "frees the subject to enrol another")
    release.add_argument("user", help="a user id or subject")
    release.set_defaults(run=_cmd_release)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="| %(levelname)-8s | %(message)s")

    datadir = Path(args.datadir).resolve()
    if not datadir.exists():
        raise SystemExit(f"{datadir} does not exist")

    # 🔴 No traceback: the refusal already says what to do.
    try:
        store = Store(datadir / "server.db")
    except StoreVersionError as e:
        raise SystemExit(str(e))

    with store:
        return args.run(store, args)


if __name__ == "__main__":                                      # pragma: no cover
    sys.exit(main())
