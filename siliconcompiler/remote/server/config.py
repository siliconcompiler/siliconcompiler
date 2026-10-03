'''
What this deployment promises: every limit, feature and setting, with defaults.

Every value has a working default; an optional ``<datadir>/config.json``
overrides any subset. Limits are the operator's policy rather than an account's
data, since this profile has no plans; the one per-account override is
`max_download_bytes` in `user_limits` (`identity.accounts`).
'''

import json

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from siliconcompiler.remote.server.errors import FEATURES
from siliconcompiler.remote.server.staging import allowlist

__all__ = ["Config", "DEFAULTS", "CONFIG_FILENAME", "TEST_MODES"]


CONFIG_FILENAME = "config.json"

# Every value is in a base unit its name gives: bytes are never MB. A refusal
# names the key with the same spelling.
DEFAULT_LIMITS: Dict[str, int] = {
    "max_job_nodes": 1000,                  # nodes in one flow
    "max_upload_bytes": 1073741824,         # bytes
    "artifact_retention_seconds": 2592000,  # seconds: the least any artifact is kept
    "pending_uploads": 8,                   # jobs held in created or awaiting_input
    "concurrent_jobs": 4,                   # jobs staging, queued, running or cancelling
    # Open /logs streams per caller; each holds a thread and an open file until
    # its token expires. Generous for a person, deliberately too few for a
    # client opening one per node of a wide flow, which should poll the job.
    "concurrent_log_streams": 8,
    "max_archive_members": 100000,          # members in the upload archive
    "max_archive_expanded_bytes": 10737418240,   # bytes, after expansion

    # The largest single object handed over an API fetch.
    # 🔴 A ceiling that refuses (`download-too-large`), not advice, and no query
    # parameter or header overrides it: the portal is the only way past it
    # (`ResultsMixin.artifact`).
    # 🔴 Deliberately not `fetchable: false`, which a client renders as not
    # entitled to read one's own output.
    # ⚠️ It bounds one object, not the run: a budget for the whole listing would
    # make what arrives depend on order. Per account, so `GET /v1/me` carries
    # the caller's number and `GET /v1` the default.
    "max_download_bytes": 104857600,        # bytes, per artifact (100 MiB)

    # 🔴 CHARACTERS, not bytes (`errors.DETAIL_MAX`). Enforced and not published
    # (`_NOT_PUBLISHED`): it bounds this server's own output.
    "max_detail_chars": 300,

    # 🆕 How long a job may sit with no upload before it is `abandoned`.
    # 🔴 A ceiling, not a constant: a slow link and a script that died look
    # identical from here, and only an operator knows which is likelier.
    # ⚠️ A floor: a job holding an unlapsed grant is never abandoned
    # (`ReconcileMixin.abandon_if_expired`).
    "abandon_after_seconds": 900,           # seconds

    # One pass of staging: sources, manifest read and Python packages together
    # (surface D294). Past it the job ends `failed`, `staging-timed-out`, so one
    # user's package set cannot hold the queue. Each resubmit gets it afresh.
    "max_staging_seconds": 3600,            # seconds
}

DEFAULTS: Dict[str, Any] = {
    # What a client branches on. The device grant is not served, so not listed.
    "grant_types_supported": ["client_credentials", "refresh_token"],

    # A registry: a value is listed only once it is served. `logs.stream` is one
    # node's live tail and `logs.stream.job` every node's merged, which is cheap
    # because the stream host is this host.
    "features": ["logs.stream", "logs.stream.job"],

    # Below every intermediary's idle timeout, Cloudflare's 100 seconds included.
    "stream_keepalive_seconds": 15,

    # Only "verified" asserts anything; any other value means do not rely on it.
    "identity_assurance": "self_asserted",

    # REQUIRED, [] by default. Each is `{"level", "message", "starts_at",
    # "ends_at"}` (`_notice`), published from server start until `ends_at`.
    # `GET /v1` takes no credential, so a message names no customer, incident
    # detail or internal host.
    "notices": [],

    # OPTIONAL: absent unless the operator sets one. Absent is not empty.
    "terms_url": None,

    "limits": DEFAULT_LIMITS,

    # Where bytes go, as a URI (see `state.storage`).
    "storage_location_id": "primary",
    "storage_uri_base": None,               # defaults to file://<datadir>/artifacts/

    # How long a running job's runner may stay silent before this server stops
    # believing it is running (`ReconcileMixin._silent`).
    # 🔴 Deployment config, not a published limit: no client sends or sees the
    # heartbeat.
    # ⚠️ Generously above the runner's 60s beat: a missed beat is a busy
    # filesystem, fifteen silent minutes a dead process.
    "run_heartbeat_seconds": 900,

    # The `Retry-After` on a job poll.
    # 🔴 One second is affordable because a poll is a SQLite read and a stat;
    # scheduler queries are throttled apart (`SCHEDULER_QUERY_FLOOR`).
    # ⚠️ A deployment with many concurrent watchers should raise it.
    "poll_interval_seconds": 1,

    # The portal's absolute origin, which `POST /v1/auth/browser`'s sign-in link
    # is built on; None uses the public origin the request arrived at.
    # 🔴 Config, never `Host` or `X-Forwarded-Host`: both are attacker controlled
    # without a trusted proxy, and this link is opened in somebody's browser.
    "web_url_base": None,

    # The origins this deployment is reached at, as scheme://host[:port]: what a
    # DPoP proof's `htu` is checked against and every URL handed out is built
    # on. None takes this host's names on its own port.
    # 🔴 Config, never `Host` or `X-Forwarded-Host`, as for `web_url_base`.
    "public_origins": None,

    # Whether compute nodes run each job inside a container this deployment
    # registered. Off by default: the API process cannot see whether nodes have
    # a runtime, and running on the host is conforming (image_id stays NULL).
    # On, `GET /v1`'s `software` lists only versions a live image holds, submit
    # records one image per node, and a job using a tracked tool that has no
    # image is refused before anything runs.
    "containers": False,

    # The Slurm partition for the job's orchestrating process; None is the
    # cluster's default.
    # 🔴 Not where the work runs: each node is a job of its own. This process
    # holds one mostly idle core for the whole flow, so it wants a small
    # partition with a long time limit.
    "batch_queue": None,

    # SiliconCompiler's `option,track` on every job: each node's host name, IP
    # and MAC, OS, user and region in the manifest the submitter downloads.
    # ⚠️ Off by default, since that publishes the layout `detail` is scrubbed
    # of. Off leaves a job's own setting as sent.
    "track_provenance": False,

    # Host paths every container sees, whoever's job it is: the munge socket and
    # slurm.conf, say, or a licence file. Never the data directory; what one job
    # sees is `JobService.job_mounts`.
    # ⚠️ Written into each bundle when it is unpacked: after a change, remove
    # <datadir>/images and re-stage.
    "container_mounts": [],

    # Which artifact kinds the API hands over, or None for all. A test knob.
    # 🔴 The API's answer, not the portal's: a kind left out stays listed with
    # `fetchable: false` and `can_request_access: false`, and fetching it is
    # `403 artifact-not-approved` (ladder row 7). Leaving it out of the listing
    # would claim this server does not keep it while the portal shows it.
    "api_fetchable_kinds": None,

    # PDKs, libraries and tools no caller may use, as globs per resource kind:
    # `{"pdk": ["GF180*"], "library": [...], "tool": [...]}`.
    # 🔴 A deny-list stand-in for grants, which this profile does not serve, so a
    # client can see a grant's refusal: `entitlement-denied` at submit naming
    # `resource_kind` and `resource`, and the job `rejected`.
    # ⚠️ `GET /v1/me` still omits `authorized`, an allow list a deny list cannot
    # be written as, so a client learns of a denial at submit.
    "denied_resources": {},

    # Where this server fetches a job's remote sources from (D113, D128), as
    # globs (see `allowlist`).
    # 🔴 Decides who fetches, not whether the data arrives: a source not on it
    # is asked of the client. The default is SiliconCompiler's GitHub org, which
    # lambdapdk needs, and codeload only under it; all of codeload would admit
    # every public repository's archive.
    "fetch_allowlist": list(allowlist.DEFAULT),

    # The primary index, then extras. A job names no index, so an index's
    # credential is only ever the deployment's.
    "package_indexes": ["https://pypi.org/simple/"],

    # What a package install may reach, by `fetch_allowlist`'s rules: the indexes
    # and the hosts they serve files from. Separate, because reaching an index
    # is not fetching a source.
    "index_allowlist": ["https://pypi.org/simple/",
                        "https://files.pythonhosted.org/"],

    # Whether this server builds an image of a job's Python packages over the
    # node's base image (implementation-notes §L), shared by every job asking
    # for the same set.
    # 🔴 Needs `containers`; on advertises `python.env`, and false is the kill
    # switch. A build runs on a compute node (`build_queue`) whose only way out
    # is a proxy admitting `index_allowlist`.
    "env_builder": False,

    # 🔴 Whether packages may be built from source where no wheel fits (surface
    # D291): the deployment's policy in place of `python-sdist`, off because a
    # build runs the package's own code. Only in the builder: needs `env_builder`.
    "python_source_builds": False,

    # The Slurm partition for environment builds, None for the default; its own
    # keeps a burst of builds off the slots flows are waiting on.
    "build_queue": None,

    # Private dataroots this server supplies (surface D298):
    #   {"library": {"acme_pdk": {"acme_pdk": "/opt/pdks/acme"}},
    #    "tool":    {"acme_sim": {"scripts": "/opt/acme/scripts"}},
    #    "task":    {"acme_sim": {"run": {"scripts": "/opt/acme/run-scripts"}}}}
    # `library` is `library,<name>,dataroot,<root>`; `tool` covers every task of
    # the tool, and `task` overrides it for one (tool, task).
    # 🔴 Such a root never leaves the submitter, so its files come from here
    # first, then a held copy of its source, then a fetch (surface D299); this is
    # the one needing no source. A path is confined to its root. Mounted
    # read-only; a change needs the bundles re-staged.
    "private_dataroots": {},

    # Per source, and for all of a job's sources after submit; what is missing
    # at the deadline is asked of the client.
    "fetch_timeout_seconds": 300,
    "fetch_deadline_seconds": 1800,

    # Bounds on the manifest read while a job stages (`manifestread`); past any,
    # the job is rejected `invalid_manifest`.
    "manifest_read_timeout_seconds": 300,
    "manifest_read_cpu_seconds": 300,
    "manifest_read_memory_bytes": 4 * 1024 ** 3,

    # Every fetch fails and no held copy is used, so every job needing a source
    # takes the follow-up path after submit. For test mode 4.
    "fetch_fails": False,

    # Out-of-tree task-driver modules software may name (D95). The probe imports
    # them on the server, so this is what an operator allows it to import.
    "software_drivers": [],
}

# A notice (surface §1). The times are REQUIRED and nullable on the wire.
NOTICE_LEVELS = ("info", "warning")
NOTICE_MEMBERS = ("level", "message", "starts_at", "ends_at")
MAX_NOTICE_CHARS = 500

# `denied_resources` keys: the contract's closed `resource_kinds` set.
RESOURCE_KINDS = ("pdk", "library", "fpga", "tool")

# Limits this server enforces and does not publish.
_NOT_PUBLISHED = ("max_detail_chars",)


# Presets for testing a client against deployments that serve less; mode 4
# fetches nothing, so every job takes the follow-up path.
# 🔴 Each is a legal v1 deployment that `GET /v1` describes, so a client passes
# by reading what was published.
# ⚠️ Applied over the defaults and under `config.json`.
# ⚠️ Mode 3's denials are each tripped by a different demo target while the
# skywater130 demo still runs: `gf180_demo`, `freepdk45_demo`, verilator.
TEST_MODES: Dict[int, Dict[str, Any]] = {
    # What this server does by default.
    1: {},

    # Per-node live logs only; manifest, logs and reports over the API, node
    # archives only through the portal.
    2: {
        "features": ["logs.stream"],
        "api_fetchable_kinds": ["manifest", "logs", "staging", "reports"],
        "limits": {
            "concurrent_jobs": 2,
            "pending_uploads": 4,
            "max_download_bytes": 52428800,             # 50 MiB
        },
    },

    # Manifests only over the API, no logs, one job at a time, and a PDK, a
    # library and a tool nobody may use.
    3: {
        "features": [],
        "api_fetchable_kinds": ["manifest"],
        "denied_resources": {
            "pdk": ["GF180*"],
            "library": ["nangate45"],
            "tool": ["verilator"],
        },
        "limits": {
            "concurrent_jobs": 1,
            "pending_uploads": 2,
            "max_job_nodes": 200,
            "max_upload_bytes": 104857600,              # 100 MiB
            "max_download_bytes": 20971520,             # 20 MiB
        },
    },

    # Mode 1 with nothing fetchable: a remote PDK sends the job to
    # `awaiting_input`, so it carries two uploads.
    4: {
        "fetch_fails": True,
    },
}


# The largest object S3 takes in one PUT.
S3_ONE_PUT_BYTES = 5 * 1024 ** 3


# The limits this server treats null as unlimited for.
UNLIMITED_ALLOWED = ("pending_uploads", "concurrent_jobs", "max_download_bytes")


def _check_policy(values: Dict[str, Any]) -> None:
    '''Refuse a policy value that would silently mean nothing, such as a
    misspelled kind the operator believes restricts something.'''
    from siliconcompiler.remote.server.outputs.artifacts import KINDS

    # 🔴 A limit is a non-negative number, or null where this server treats it
    # as unlimited (surface D177). `-1` is only the store's spelling, in
    # `user_limits`.
    for name, value in (values["limits"] or {}).items():
        if value is None and name not in UNLIMITED_ALLOWED:
            raise ValueError(f"limits.{name} may not be null: only "
                             f"{', '.join(UNLIMITED_ALLOWED)} may be unlimited here")
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)
                                  or value < 0):
            raise ValueError(f"limits.{name} is a whole number of zero or more; "
                             f"not {value!r}")

    for name in ("manifest_read_timeout_seconds", "manifest_read_cpu_seconds",
                 "manifest_read_memory_bytes"):
        value = values[name]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} is a whole number above zero; not {value!r}")

    kinds = values["api_fetchable_kinds"]
    if kinds is not None:
        unknown = set(kinds) - set(KINDS)
        if unknown:
            raise ValueError(
                f"api_fetchable_kinds names unknown kinds: "
                f"{', '.join(sorted(unknown))}")

    features = values["features"]
    # 🔴 A registry (surface *features is a registry*): an unknown string would
    # be advertised for something nothing here serves.
    unregistered = sorted(set(features) - set(FEATURES))
    if unregistered:
        raise ValueError(f"features lists {', '.join(unregistered)}, which is not a "
                         f"registered features string: {', '.join(FEATURES)}")
    # A client reading `logs.stream.job` falls back to per-node streams.
    if "logs.stream.job" in features and "logs.stream" not in features:
        raise ValueError("features lists logs.stream.job without logs.stream, "
                         "which it implies")

    keepalive = values["stream_keepalive_seconds"]
    if not isinstance(keepalive, int) or isinstance(keepalive, bool) \
            or not 1 <= keepalive < 100:
        raise ValueError("stream_keepalive_seconds is whole seconds, 1 to 99: below "
                         "an intermediary's idle timeout")

    # Refused at load, never trusted to a careful matcher: a bare `*` host, a
    # wildcard off the leftmost label, a globbed scheme.
    for entries in (values["fetch_allowlist"], values["index_allowlist"]):
        for warning in allowlist.check_entries(entries or []):
            import logging
            logging.getLogger("sc-server").warning(warning)

    indexes = values["package_indexes"]
    if not isinstance(indexes, list) or not indexes or \
            not all(isinstance(url, str) and url.startswith(("https://", "http://"))
                    for url in indexes):
        raise ValueError("package_indexes is a list of index URLs, the primary first")
    rules = [allowlist.parse(entry) for entry in values["index_allowlist"] or []]
    for url in indexes:
        if not allowlist.allows(rules, url):
            raise ValueError(f"package_indexes names {url}, which index_allowlist does "
                             "not admit: an install could not reach it")

    # 🔴 `python.env` is served by nodes installing on the host (an operator's
    # choice) or, where nodes run in containers, by the builder.
    if values["python_source_builds"] and not values["env_builder"]:
        raise ValueError("python_source_builds is on and there is no env_builder: a "
                         "source distribution is built only in the isolated builder, "
                         "never where nodes run on this host")
    if values["env_builder"] and not values["containers"]:
        raise ValueError("env_builder builds images, and this deployment runs no "
                         "containers; where nodes run on the host, list python.env "
                         "in features and each node installs its own")
    if "python.env" in features and values["containers"] and not values["env_builder"]:
        raise ValueError("features lists python.env, and nodes here run in "
                         "containers with no env_builder to build them an image")

    # 🔴 A reuse hit compares the host's tools among its inputs (surface §13),
    # and a host run records none: reuse waits for containers (profile §5).
    if "jobs.reuse" in features and not values["containers"]:
        raise ValueError("features lists jobs.reuse, and nodes here run on the host, "
                         "whose tools this server does not record, so a reused job's "
                         "inputs could not be compared; turn on containers, or leave "
                         "jobs.reuse out")

    _check_private_dataroots(values["private_dataroots"] or {})

    denied = values["denied_resources"] or {}
    unknown = set(denied) - set(RESOURCE_KINDS)
    if unknown:
        raise ValueError(
            f"denied_resources names unknown resource kinds: "
            f"{', '.join(sorted(unknown))}; the kinds are "
            f"{', '.join(RESOURCE_KINDS)}")
    for kind, names in denied.items():
        if not isinstance(names, list) or \
                not all(isinstance(name, str) for name in names):
            raise ValueError(f"denied_resources.{kind} must be a list of names")

    values["notices"] = [_notice(entry) for entry in values["notices"] or []]

    # Served as `Retry-After`, which is whole seconds and never below 1.
    interval = values["poll_interval_seconds"]
    if not isinstance(interval, int) or isinstance(interval, bool) or interval < 1:
        raise ValueError("poll_interval_seconds is a whole number of seconds, at least 1")


def private_paths(private) -> List[str]:
    '''Every root `private_dataroots` maps to, once each, in config order: what
    jobs get read-only, and what a published `detail` must never say.'''
    found: List[str] = []
    for section in ("library", "tool"):
        for roots in (private.get(section) or {}).values():
            found.extend(roots.values())
    for tasks in (private.get("task") or {}).values():
        for roots in tasks.values():
            found.extend(roots.values())
    return list(dict.fromkeys(found))


def _check_private_dataroots(private) -> None:
    '''Hold `private_dataroots` to its shape, down to absolute paths.'''
    shape = ('private_dataroots is {"library": {name: {root: path}}, '
             '"tool": {tool: {root: path}}, "task": {tool: {task: {root: path}}}}, '
             'each path absolute')

    def roots(value) -> bool:
        return isinstance(value, dict) and all(
            isinstance(root, str) and isinstance(path, str) and path.startswith("/")
            for root, path in value.items())

    if not isinstance(private, dict):
        raise ValueError(shape)
    unknown = sorted(set(private) - {"library", "tool", "task"})
    if unknown:
        raise ValueError(f"{shape}; {unknown[0]!r} is none of library, tool and task")
    for section in ("library", "tool"):
        held = private.get(section) or {}
        if not isinstance(held, dict) or not all(roots(value) for value in held.values()):
            raise ValueError(shape)
    tasks = private.get("task") or {}
    if not isinstance(tasks, dict) or not all(
            isinstance(value, dict) and all(roots(inner) for inner in value.values())
            for value in tasks.values()):
        raise ValueError(shape)


def _notice(entry) -> Dict[str, Any]:
    '''One configured notice, checked and in its wire shape.'''
    if not isinstance(entry, dict):
        raise ValueError("a notice is {\"level\", \"message\", \"starts_at\", "
                         f"\"ends_at\"}}; not {entry!r}")
    unknown = set(entry) - set(NOTICE_MEMBERS)
    if unknown:
        raise ValueError(f"a notice has no {', '.join(sorted(unknown))}; its members are "
                         f"{', '.join(NOTICE_MEMBERS)}")
    if entry.get("level") not in NOTICE_LEVELS:
        raise ValueError(f"a notice's level is {' or '.join(NOTICE_LEVELS)}; "
                         f"not {entry.get('level')!r}")
    message = entry.get("message")
    if not isinstance(message, str) or not 1 <= len(message) <= MAX_NOTICE_CHARS:
        raise ValueError(f"a notice's message is 1 to {MAX_NOTICE_CHARS} characters")

    notice = {"level": entry["level"], "message": message}
    for name in ("starts_at", "ends_at"):
        value = entry.get(name)
        if value is not None and _instant(value) is None:
            raise ValueError(f"a notice's {name} is null or an RFC 3339 time in UTC, "
                             f"such as 2026-09-27T02:00:00Z; not {value!r}")
        notice[name] = value
    return notice


def _instant(value) -> Optional[float]:
    '''Seconds since the epoch for an RFC 3339 time in UTC, or None.'''
    import re
    from datetime import datetime, timezone

    if not isinstance(value, str) or \
            not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{1,6})?Z", value):
        return None
    try:
        moment = datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    fraction = float("0" + value[19:-1]) if value[19:-1] else 0.0
    return moment.replace(tzinfo=timezone.utc).timestamp() + fraction


class Config:
    '''One deployment's policy, read once at startup.

    Nothing reloads it, so two requests in one second never answer differently.
    '''

    def __init__(self, values: Dict[str, Any]):
        self._values = values

    @classmethod
    def load(cls, datadir: Union[str, Path],
             test_mode: Optional[int] = None) -> "Config":
        '''Defaults, then ``test_mode``'s preset, then ``<datadir>/config.json``
        if it is there.'''
        values = dict(DEFAULTS)
        values["limits"] = dict(DEFAULT_LIMITS)

        if test_mode is not None:
            if test_mode not in TEST_MODES:
                raise ValueError(
                    f"test mode {test_mode} is not one of "
                    f"{', '.join(map(str, TEST_MODES))}")
            preset = dict(TEST_MODES[test_mode])
            values["limits"].update(preset.pop("limits", {}))
            values.update(preset)

        path = Path(datadir) / CONFIG_FILENAME
        if path.exists():
            overlay = json.loads(path.read_text())
            if not isinstance(overlay, dict):
                raise ValueError(f"{path} must hold a JSON object")

            unknown = set(overlay) - set(DEFAULTS)
            if unknown:
                # Refused, not ignored: a misspelled key is a ceiling the
                # operator believes they set.
                raise ValueError(
                    f"{path} sets unknown keys: {', '.join(sorted(unknown))}")

            limits = overlay.pop("limits", None)
            if limits is not None:
                unknown_limits = set(limits) - set(DEFAULT_LIMITS)
                if unknown_limits:
                    raise ValueError(
                        f"{path} sets unknown limits: "
                        f"{', '.join(sorted(unknown_limits))}")
                values["limits"].update(limits)

            values.update(overlay)

        _check_policy(values)

        if values["env_builder"] and "python.env" not in values["features"]:
            values["features"] = list(values["features"]) + ["python.env"]

        # S3 takes one PUT of at most 5 GiB, and the upload is one PUT
        # (surface §14).
        base = values["storage_uri_base"] or ""
        if base.startswith("s3://") and values["limits"]["max_upload_bytes"] > S3_ONE_PUT_BYTES:
            raise ValueError(
                f"max_upload_bytes is {values['limits']['max_upload_bytes']}, and an S3 "
                f"store takes at most {S3_ONE_PUT_BYTES} bytes in one PUT")

        if values["storage_uri_base"] is None:
            artifacts = (Path(datadir) / "artifacts").resolve()
            values["storage_uri_base"] = artifacts.as_uri() + "/"

        return cls(values)

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    @property
    def limits(self) -> Dict[str, int]:
        return self._values["limits"]

    def api_fetchable(self, kind: str) -> bool:
        '''Whether the API hands over artifacts of this kind.'''
        kinds = self._values["api_fetchable_kinds"]
        return kinds is None or kind in kinds

    def denied(self, resource_kind: str, name: str) -> bool:
        '''Whether no caller may use this PDK, library or tool.'''
        from fnmatch import fnmatchcase

        patterns = (self._values["denied_resources"] or {}).get(resource_kind, [])
        return any(fnmatchcase(name, pattern) for pattern in patterns)

    def notices(self, at: Optional[float] = None) -> list:
        '''The notices published now: from server start until `ends_at` passes.'''
        import time

        at = time.time() if at is None else at
        return [dict(notice) for notice in self._values["notices"]
                if notice["ends_at"] is None or _instant(notice["ends_at"]) > at]

    def capabilities(self, software: Dict[str, list]) -> Dict[str, Any]:
        '''The ``GET /v1`` body. ``software`` comes from the store: a version is
        advertised only where a live image holds it.'''
        block = {
            "api_version": "v1",
            "software": software,
            "grant_types_supported": list(self._values["grant_types_supported"]),
            # Every one REQUIRED (surface §1), less `_NOT_PUBLISHED`.
            "limits": {name: value for name, value in self._values["limits"].items()
                       if name not in _NOT_PUBLISHED},
            "features": list(self._values["features"]),
            "identity_assurance": self._values["identity_assurance"],
            "notices": self.notices(),
        }

        # OPTIONAL: absent means the operator set none, which null would not.
        if self._values["terms_url"]:
            block["terms_url"] = self._values["terms_url"]

        return block
