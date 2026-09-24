'''
``python3 -m siliconcompiler.remote.server.registry``

The operator's side of the image registry: which distributions this deployment
curates, at which versions, and which containers hold them.

🔴 **Registering an image is the most dangerous write this server has.** It
chooses what code executes on the cluster -- higher stakes than any read
permission, because a permission decides who may see something and this decides
what runs as the account a job maps to. So every write here names the person who
made it, taken from the account running the command on the server host, and the
tag is resolved to a digest once, here, rather than re-resolved at every
dispatch.

⚠️ **A separate entry point rather than more flags on the server**, which has
three and should keep them. This one runs against a datadir, not against a
running server, and needs nothing from the ``server`` extra: a deployment can be
curated before it is first started, and from a shell on the host rather than
over the API. When the portal arrives it calls the same functions in
:mod:`~siliconcompiler.remote.server.images`, so there is one implementation of
each of these writes and not two.
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

from siliconcompiler.remote.server import images
from siliconcompiler.remote.server.config import Config
from siliconcompiler.remote.server.store import Store, StoreVersionError

__all__ = ["main"]


logger = logging.getLogger("sc-server")

# A registry write is administrative, and identity.md's rule is that an
# administrative action is authenticated as a person and never as a service
# account. On this deployment the person is whoever has a shell on the host, so
# that is what is recorded -- under its own issuer, so it can never collide with
# a client that logged in over the API or with an identity provider added later.
OPERATOR_ISSUER = "operator"


def _operator(store) -> str:
    '''The user id every write in this session is recorded against.'''
    subject = f"{getpass.getuser()}@{socket.gethostname()}"
    with store.transaction():
        user = store.upsert_user(OPERATOR_ISSUER, subject, display_name=subject)
    return user["id"]


def _contains(values: Optional[List[str]]):
    '''``-contains siliconcompiler==0.38.9`` into pairs.

    ``==`` and nothing else: no ranges anywhere in this registry. A range needs
    a version-comparison grammar that the client, the server and every tool
    agree on, and two implementations disagreeing about what ``>=0.38`` covers
    is a job dispatched into the wrong container.
    '''
    pairs = []
    for value in values or []:
        name, sep, version = value.partition("==")
        if not sep or not name or not version:
            raise SystemExit(f"{value!r} is not name==version")
        pairs.append((name.strip(), version.strip()))
    return pairs


def _wants(values: Optional[List[str]]):
    '''``-requires openroad>=26.3`` into pairs, with any PEP 440 operator.

    🔴 Not `_contains`, and the difference is the *no ranges* rule's scope: a
    STORED version is exact, because a stored range is a promise nobody can
    check, while a REQUIREMENT is a range by nature. Using the storage parser
    here refused `>=26.3` as "not name==version", which is the registry
    rejecting the one shape this command exists to try.
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
    '''Pin a tag to the bytes it names right now.

    🔴 Once, here, and never again. Rebuilding ``sc-runtime:0.39.1`` must not
    silently change what a job runs -- that takes a re-registration, which is a
    decision somebody made. Two jobs a month apart running different code off
    the same tag is the failure this prevents.
    '''
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

    # A locally built image has no repository digest because it was never
    # pushed. Its own id is a sha256 of the config rather than of the manifest,
    # which is not the same thing -- so it is refused rather than recorded as
    # something it is not.
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
                # It is in the catalogue and it can never satisfy a range, and
                # the number alone does not say so.
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

    return 0


def _cmd_add_software(store, args) -> int:
    kind = args.kind or ("tool" if args.driver else None)
    if not kind:
        # 🔴 Refused rather than defaulted. The kind decides which bucket the
        # name is published in, and therefore whether ONE image has to hold it
        # or each node's image does -- a default would make that a silent
        # guess about what a client's job needs.
        raise SystemExit(
            f"{args.name}: say -kind python or -kind tool. A tool with a "
            "driver can say -driver instead, which implies it")

    try:
        images.register_software(store, args.name, args.display or args.name,
                                 _operator(store), kind, driver=args.driver)
    except ValueError as e:
        raise SystemExit(str(e))

    print(f"registered {args.name} as {kind}")
    if args.driver:
        # Said, because it is what a probe inside an image is handed and what
        # decides whether this tool can ever report a version.
        print(f"  driven by {args.driver}")
    elif kind == "tool":
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
        # Normalised, and said so. Silently storing a different string than
        # the operator typed is how a later `add-image -contains` fails to
        # match a version that is right there in the catalogue.
        print(f"  normalised from {args.version}")
    if args.unversioned:
        print("  marked published_date: it can never satisfy a version "
              "requirement, and it always sorts below a reported version")
    return 0


def _cmd_add_image(store, args) -> int:
    digest = args.digest or _resolve_digest(args.ref)

    try:
        image_id = images.register_image(
            store, args.ref, digest, _contains(args.contains), _operator(store),
            note=args.note, built_at=args.built)
    except ValueError as e:
        raise SystemExit(str(e))

    print(f"registered {args.ref}")
    print(f"  {image_id}")
    print(f"  {digest}")

    if args.stage:
        print(f"  {_stage(args, images.pinned_ref(args.ref, digest), digest)}")

    return 0


def _stage(args, ref: str, digest: str):
    '''Unpack one image where a Slurm job can run it.

    🔴 Only needed on a deployment whose cluster runs the containers, and doing
    it here is what keeps it off the request path: ``sbatch --container`` names
    a bundle that has to exist before the job starts, so a framework image
    nobody staged is unpacked by the first submit that needs it -- correct, and
    minutes of somebody's HTTP request.
    '''
    datadir = Path(args.datadir).resolve()

    # 🔴 The deployment's own mount list, read from the same config the server
    # reads. Staging with a different one produces a bundle that looks right
    # and is missing whatever the cluster needed -- and the failure lands far
    # away, as a node that cannot contact the controller.
    mounts = [datadir] + [
        str(path) for path in (Config.load(datadir)["container_mounts"] or [])]

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


def _cmd_resolve(store, args) -> int:
    '''Ask what a job would be placed in, without submitting one.

    The one command here that writes nothing. An operator curating a registry
    needs to see the answer the submit path will give before a user does, and
    the alternative -- submitting a job to find out -- is a slow way to learn
    that a tool has no image.
    '''
    # 🔴 The two buckets, because they resolve differently: the python set has
    # to be held by ONE image and a tool is satisfied per node. `-versions`
    # names python requirements and `-requires` names tool ones, which is the
    # same split the descriptor carries.
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
    """`unlimited`, `inherit`, or a number with an optional binary suffix.

    ⚠️ Three answers rather than two, because the table's encoding has three:
    `inherit` clears the override back to the deployment's value, and
    `unlimited` is a decision to have no ceiling. A bare number is the number.
    """
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

    🔴 The operator sets a ceiling and the portal shows it. A ceiling is
    policy, and this deployment has no admin mode -- so there is no endpoint
    and no form, and this is the whole of the write path.
    """
    from siliconcompiler.remote.server import accounts
    from siliconcompiler.remote.server.config import Config

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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m siliconcompiler.remote.server.registry",
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
        "-kind", choices=("python", "tool"),
        help="python or tool. Derived by probing this process when omitted, "
             "which is the right answer unless you are describing an image "
             "this process is not")
    software.add_argument(
        "-driver", metavar="<module>",
        help="the module carrying this tool's Task driver, for one that is "
             "not in siliconcompiler's own tree. Found by scanning when "
             "omitted, and naming one makes this a tool")
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

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="| %(levelname)-8s | %(message)s")

    datadir = Path(args.datadir).resolve()
    if not datadir.exists():
        raise SystemExit(f"{datadir} does not exist")

    # 🔴 The refusal already says what to do; a traceback on top of it buries
    # that in twenty lines of frames and makes an operational message read like
    # a crash. This is the one error here that a person is meant to act on.
    try:
        store = Store(datadir / "server.db")
    except StoreVersionError as e:
        raise SystemExit(str(e))

    with store:
        return args.run(store, args)


if __name__ == "__main__":                                      # pragma: no cover
    sys.exit(main())
