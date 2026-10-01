'''
What this deployment promises, and where those numbers come from.

Every value has a working default, so a bare ``-datadir`` that has never been
used starts a server which serves a complete ``GET /v1``. An optional
``<datadir>/config.json`` overrides any subset of them; anything it does not
mention keeps its default.

Limits come from here rather than from a table because there are no plans and
no per-user overrides in this profile -- a ceiling is the operator's policy, not
an account's data.
'''

import json

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from siliconcompiler.remote.server.errors import FEATURES
from siliconcompiler.remote.server.staging import allowlist

__all__ = ["Config", "DEFAULTS", "CONFIG_FILENAME", "TEST_MODES"]


CONFIG_FILENAME = "config.json"

# Every value is a base unit and its own name says which: bytes are never MB,
# and a count is never a duration. The refusal that names a key back spells it
# identically, which is what makes the error registry double as the enforcement
# trace.
DEFAULT_LIMITS: Dict[str, int] = {
    "max_job_nodes": 1000,                  # nodes in one flow
    "max_upload_bytes": 1073741824,         # bytes
    "artifact_retention_seconds": 2592000,  # seconds: the least any artifact is kept
    "pending_uploads": 8,                   # jobs held in created or awaiting_input
    "concurrent_jobs": 4,                   # jobs staging, queued, running or cancelling
    # Open /logs streams per caller, and the number is chosen rather than
    # inherited. What one costs, now that there is something to measure: a
    # worker thread and an open file for as long as it lives, which is up to
    # the token that opened it, plus a stat twice a second while the log is quiet.
    # Under a threaded WSGI server there is no fixed pool to exhaust, so what
    # runs out is memory and descriptors rather than capacity.
    #
    # 8 is generous for a person -- nobody reads eight logs at once -- and
    # deliberately not generous enough for a client that would open one per node
    # of a wide flow. That client should poll the job, which is one request for
    # the whole run, and tail only the nodes somebody is actually watching.
    "concurrent_log_streams": 8,
    "max_archive_members": 100000,          # members in the upload archive
    "max_archive_expanded_bytes": 10737418240,   # bytes, after expansion

    # The largest single object this server will hand over an API fetch.
    #
    # 🔴 **A real ceiling that refuses, not advice a client applies to
    # itself.** It began as the latter and that was the defect: it was the only
    # published limit with no refusal behind it, so an operator who set it was
    # setting policy that any client could ignore by not reading it. An
    # over-ceiling fetch is `limit-exceeded` naming this key, and `null` means
    # unlimited exactly as it does everywhere else on the wire.
    #
    # 🔴 **There is no API override -- not a query parameter, not a header.**
    # The portal is the only way past it, because the portal is a different
    # surface with a person on it who has just clicked the thing.
    #
    # 🔴 It is deliberately not `fetchable: false`. `fetchable` answers *may
    # this caller have these bytes*, and a client renders a false one as
    # deleted, withheld, aged out or not entitled -- so using it for size would
    # tell somebody they lack permission to read their own output.
    #
    # ⚠️ It bounds one object, not the run. Forty nodes each just under it
    # still fetch forty times it, because the alternative -- a budget for the
    # whole listing -- makes what arrives depend on what order it arrives in.
    #
    # ⚠️ Per account, so `GET /v1/me` carries the number that binds THIS
    # caller and `GET /v1` carries the deployment's default.
    "max_download_bytes": 104857600,        # bytes, per artifact (100 MiB)

    # The most of a refusal's `detail` a caller is given.
    #
    # 🔴 **CHARACTERS and not bytes, which is the one place this contract's
    # usual `_bytes` is wrong.** Truncating UTF-8 by byte count splits a
    # codepoint, and what comes out is not text.
    #
    # 🔴 Published, because otherwise every deployment truncates differently
    # and a client rendering a refusal in a fixed box, or a log pipeline
    # indexing on it, sees a different answer from each server -- which reads
    # as a client bug. `detail` is a single line.
    "max_detail_chars": 300,

    # 🆕 How long a job may sit with no upload before it is `abandoned`.
    #
    # 🔴 A ceiling rather than a constant, because it is a judgement about
    # people and not about the protocol: a slow link uploading a gigabyte and a
    # script that died between create and PUT look identical from here, and
    # only an operator knows which their deployment has more of.
    #
    # ⚠️ It is the floor and not the whole answer -- a job holding a grant that
    # has not yet lapsed is never abandoned, however old it is. Otherwise
    # setting this below the grant's own lifetime would abandon uploads that
    # were still legitimately in flight.
    "abandon_after_seconds": 900,           # seconds

    # How long a job may spend staging, each time it stages: fetching its
    # sources, reading its manifest and installing its Python packages,
    # together (surface D294). Past it the job ends `failed`,
    # `staging-timed-out` -- its own limit, not this server's failure -- so one
    # user's oversized package set cannot hold the build queue for everyone.
    # A job sent back and submitted again gets it afresh.
    "max_staging_seconds": 3600,            # seconds
}

DEFAULTS: Dict[str, Any] = {
    # What a caller may ask for. The device grant is not served here, so it is
    # not advertised: this list is what the client branches on, never
    # identity_assurance.
    "grant_types_supported": ["client_credentials", "refresh_token"],

    # A registry, not free text: absent and unrecognised mean the same thing to
    # a client, so a value is only listed once it is served. `logs.stream` is
    # one node's live tail and `logs.stream.job` every node's, merged; the old
    # `logs` is folded into the first. A finished node's log is an artifact.
    #
    # ✅ `logs.stream.job` is advertised because the stream host IS this host,
    # so the merge is N tails in one process -- and one connection per job is
    # what lets a flow wider than `concurrent_log_streams` be watched in full.
    "features": ["logs.stream", "logs.stream.job"],

    # How often a quiet log stream says it is alive: below every intermediary's
    # idle timeout, Cloudflare's 100 seconds included.
    "stream_keepalive_seconds": 15,

    # The honesty half, pairing with the startup log. "verified" is the only
    # value that asserts anything; every other value, known or unknown, means
    # do not rely on this identity.
    "identity_assurance": "self_asserted",

    # REQUIRED, and [] is the answer here. An operator with something to say
    # puts it in config.json, each as `{"level", "message", "starts_at",
    # "ends_at"}`: `level` is `info` or `warning`, `message` 1 to 500
    # characters, and the two times describe the event the notice announces,
    # each null or RFC 3339 in UTC. A notice is published from when the server
    # starts until its `ends_at` passes. `GET /v1` takes no credential, so a
    # message names no customer, no incident detail and no internal host.
    "notices": [],

    # OPTIONAL: absent unless the operator sets one. Absent is not empty.
    "terms_url": None,

    "limits": DEFAULT_LIMITS,

    # Where bytes go. A URI, so file:// is a first-class deployment -- the
    # artifact 303 is then a signed route on this server's own host rather than
    # a presigned URL somewhere else.
    "storage_location_id": "primary",
    "storage_uri_base": None,               # defaults to file://<datadir>/artifacts/

    # How long a running job may go without its runner saying anything before
    # this server stops believing it is running.
    #
    # 🔴 **Deployment config and NOT a published limit, because no client can
    # see it or act on it.** The heartbeat is written by this server's own
    # runner on the compute node; a caller neither sends one nor is told when
    # the last one arrived, so a number on `GET /v1` would be a promise about
    # machinery on the other side of the API. It is the state reconciler's
    # tuning parameter, which is what deployment config is for.
    #
    # 🔴 The backstop for a scheduler that is wrong. Until this existed the
    # ONLY way a dead run was noticed was the scheduler forgetting it, so a
    # node that vanished without deleting itself left Slurm reporting RUNNING
    # for ever and the job with it.
    #
    # ⚠️ Generously larger than the runner's own 60s beat. A missed beat is a
    # busy filesystem; fifteen minutes of silence from a process whose only job
    # is to write one line a minute is a dead process.
    "run_heartbeat_seconds": 900,

    # How long a client is told to wait before polling a job again, served as
    # `Retry-After`.
    #
    # 🔴 One second, and it is affordable only because a poll no longer costs a
    # scheduler query. Reading a job is a SQLite read plus a stat of the run's
    # progress file -- cheap, local, and the thing that actually changes second
    # to second. Asking Slurm which job each node became is the expensive half,
    # and it is throttled independently (`SCHEDULER_QUERY_FLOOR`), so shortening
    # this makes the CLI feel live without multiplying RPCs into slurmctld.
    #
    # ⚠️ A deployment with many concurrent watchers should raise it. This
    # profile is a demo and a test rig, where the watcher is a person waiting.
    "poll_interval_seconds": 1,

    # The portal's origin, absolute: what `POST /v1/auth/browser`'s sign-in
    # link is built on, the portal's own paths appended. None builds it on the
    # configured public origin the request arrived at.
    #
    # 🔴 **Config, and never `Host` or `X-Forwarded-Host`.** Both are attacker
    # controlled unless a trusted proxy is rewriting them, and the output here
    # is a link opened in somebody's browser -- the same trap as trusting a
    # forwarded client address, with a worse payoff for whoever poisons it.
    "web_url_base": None,

    # The origins this deployment is reached at, one or several, as
    # scheme://host[:port]: what a DPoP proof's `htu` is checked against, and
    # what every URL this server hands out is built on -- the upload PUT, the
    # artifact 303, the stream URL and the portal handover.
    #
    # 🔴 **Config, and never `Host` or `X-Forwarded-Host`**, for the reason
    # `web_url_base` is. None takes the ones the server was started with: this
    # host's names on its own port.
    "public_origins": None,

    # Whether the compute nodes run each job's work inside a container this
    # deployment registered.
    #
    # Off, and it has to default off: whether a compute node has a container
    # runtime at all is not something the API process can find out by looking,
    # and a bare Slurm cluster that runs jobs on the host is conforming rather
    # than degraded -- it leaves both image_id columns NULL for the life of
    # every job.
    #
    # What turning it on changes, all of it:
    #   - `GET /v1`'s `software` is filtered to the versions a live image
    #     actually holds, because a version with no image is a promise this
    #     server cannot keep
    #   - submit resolves one image per node and RECORDS it, which is only
    #     honest if the node really ran there
    #   - a node whose tool this deployment tracks and has no image for is
    #     refused, for the whole job, before anything runs
    "containers": False,

    # Which Slurm partition the job's own orchestrating process runs in.
    #
    # 🔴 It is not where the work happens. That process loads the manifest,
    # runs SiliconCompiler's scheduler and writes the progress file; every node
    # is submitted from it as a job of its own, with its own resources, in
    # whatever partition the cluster makes default. So this wants a small
    # partition with a long time limit -- it holds one core for the length of
    # the flow and uses almost none of it, and on a compute partition that is a
    # node slot doing nothing.
    #
    # None leaves it to the cluster's default, which is correct for a
    # deployment that has not made a partition for it.
    "batch_queue": None,

    # Whether every job's nodes record where they ran: SiliconCompiler's
    # `option,track`, which puts each node's machine name, IP and MAC
    # address, OS, kernel, user and region into its `record` -- in the manifest
    # the submitter downloads.
    #
    # ⚠️ Off by default because that is this deployment's layout, published:
    # the host names and addresses `detail` is scrubbed of. A test rig wants
    # it, to see which compute node ran what. Off leaves a job's own setting
    # as it was sent.
    "track_provenance": False,

    # Host paths every container must be able to see, whoever's job it is.
    # Never the data directory, which holds the signing key and the store: what
    # one job sees -- its own tree and cache, and the supplied roots read-only
    # -- goes in a bundle of that job's own (`JobService.job_mounts`).
    #
    # 🔴 Deployment config rather than something derived, because what a
    # container needs is a fact about the cluster. A framework image submits
    # every node of the flow it drives, so on Slurm it needs the munge socket
    # and wherever slurm.conf lives; a deployment whose licence server is
    # reached through a file, or whose tools read a shared scratch, names those
    # here too.
    #
    # ⚠️ Changing this does not restage bundles that already exist: the mounts
    # are written into each bundle's config.json when it is unpacked. Remove
    # <datadir>/images and re-stage.
    "container_mounts": [],

    # Which artifact kinds the API hands over, or None for all of them. A test
    # knob, off by default: the profile has no kind that needs an approval.
    #
    # 🔴 **The API's answer and not the portal's.** A kind left out stays in
    # the listing with `fetchable: false` and `can_request_access: false` -- it
    # exists, and there is no path to yes from here -- and fetching it is the
    # ladder's own answer for a kind that needs an approval, row 7:
    # `403 artifact-not-approved`. The portal lists and serves it as before,
    # which is the surface split `max_download_bytes` already makes: a person
    # clicking one object is not an automated sweep.
    #
    # ⚠️ Omitting a kind from the LISTING would be legal too -- no kind is
    # guaranteed -- but it says something different: *this server does not keep
    # those*, which is untrue while the portal is showing them.
    "api_fetchable_kinds": None,

    # PDKs, libraries and tools no caller may use, as globs per resource kind:
    # `{"pdk": ["GF180*"], "library": [...], "tool": [...]}`.
    #
    # 🔴 A stand-in for grants, which this profile does not serve, so that the
    # refusal a grant-backed deployment gives can be seen from a client. It is
    # a deny list where a grant is an allow list, and it binds everybody alike.
    # What it produces is exactly the grant's refusal -- `entitlement-denied`
    # at submit, naming `resource_kind` and `resource`, and the job `rejected`.
    #
    # ⚠️ `GET /v1/me` still omits `authorized`: that member lists what a caller
    # MAY use, and a deny list cannot be written as one. So a client learns of a
    # denial the way it would where `authorized` is too coarse to say -- at
    # submit, after the upload.
    "denied_resources": {},

    # Where this server fetches a job's remote sources from (D113, D128). An
    # entry may be a glob: scheme exact, a host wildcard only as the whole
    # leftmost label, `*` within one path segment. See `allowlist`.
    #
    # 🔴 The list decides who fetches, never whether the data arrives: a source
    # not on it is asked of the client, which sends it with its own
    # credentials. The default is SiliconCompiler's GitHub organisation, which
    # is what lambdapdk needs -- and codeload only under it, where GitHub's
    # archive redirects land; the whole codeload host would admit every public
    # repository's archive.
    "fetch_allowlist": list(allowlist.DEFAULT),

    # Where a job's Python packages are installed from: the primary index, then
    # any extra ones, PyPI by default. Configuration and never the job's -- a
    # job names no index -- so an index's credential is only ever the
    # deployment's.
    "package_indexes": ["https://pypi.org/simple/"],

    # What the install of a job's packages may reach, by the same rules as
    # `fetch_allowlist`: each of `package_indexes`, and the hosts they serve
    # files from. A separate list, because letting an install reach an index is
    # not letting the server fetch a source.
    "index_allowlist": ["https://pypi.org/simple/",
                        "https://files.pythonhosted.org/"],

    # Whether this server builds an image for a job's Python packages
    # (implementation-notes §L, container mode): the image a node running the
    # user's Python resolved to, with the job's `python_packages` and uploaded
    # wheels installed in a layer of its own, built once per base and set and
    # shared by every job asking for the same.
    #
    # 🔴 Needs `containers`, and turning it on is what advertises `python.env`
    # there -- false is the kill switch. The build runs as a job of its own on
    # a compute node (`build_queue`), in a container whose only way out is a
    # proxy that admits `index_allowlist` and nothing else. Installing a wheel
    # runs none of its code; a source distribution is built only there.
    "env_builder": False,

    # 🔴 Whether a job's Python packages may be built from source, where an
    # index has no wheel for the target (surface D291). Off: installing from
    # source runs the package's own build code, and this server grants no
    # capabilities, so this is the deployment's policy in place of
    # `python-sdist`. Built only in the isolated builder, so it needs
    # `env_builder`; where it is off, a pure package offered only as a source
    # is sent back for the client's wheel.
    "python_source_builds": False,

    # Which Slurm partition an environment build runs in, or None for the
    # cluster's default. A queue of its own keeps a burst of builds -- the
    # first jobs after a new tool image, each asking for its own set -- from
    # holding the node slots flows are waiting on.
    "build_queue": None,

    # Private dataroots this server supplies, by where SiliconCompiler keeps
    # each (surface D298), a library's and a tool's apart:
    #
    #   {"library": {"acme_pdk": {"acme_pdk": "/opt/pdks/acme"}},
    #    "tool":    {"acme_sim": {"scripts": "/opt/acme/scripts"}},
    #    "task":    {"acme_sim": {"run": {"scripts": "/opt/acme/run-scripts"}}}}
    #
    # `library` is `library,<name>,dataroot,<root>`. `tool` covers
    # `tool,<tool>,task,<task>,dataroot,<root>` on every task of the tool -- a
    # tool's private root is normally the same for all of them -- and `task`,
    # for one (tool, task), overrides it.
    #
    # 🔴 A dataroot marked private never leaves the submitter's machine, so its
    # files reach a run from this server alone: from here first, then a copy of
    # its source this server holds, then a fetch of it from `fetch_allowlist`
    # (surface D299). This is the one of the three that needs no source -- the
    # way for a `file+private` root, and for anything the allowlist does not
    # admit -- and a path under a root is confined to it. Mounted read-only
    # into every job; a change needs the bundles re-staged, as
    # `container_mounts` does.
    "private_dataroots": {},

    # How long one source may take to fetch, and how long a job may wait for
    # all of its sources, after submit. Past the deadline, what is still
    # missing is asked of the client.
    "fetch_timeout_seconds": 300,
    "fetch_deadline_seconds": 1800,

    # The manifest's read, while the job stages (`manifestread`): how long it
    # may take, wall clock, and the CPU time and memory it holds itself to. A
    # read past any of them has not read the manifest, and the job is
    # rejected `invalid_manifest`.
    "manifest_read_timeout_seconds": 300,
    "manifest_read_cpu_seconds": 300,
    "manifest_read_memory_bytes": 4 * 1024 ** 3,

    # Every fetch fails for good, and no copy this server already holds is
    # used -- what a server with an empty cache and no route out looks like.
    # An allowlisted source is still not asked for at create, so every job
    # that needs one is sent back after submit and its client uploads it as a
    # follow-up. For testing that path (test mode 4); nothing else wants it.
    "fetch_fails": False,

    # Task-driver modules outside `siliconcompiler.tools` that software may name
    # (D95). The probe imports a driver on the server, so this is the list of
    # what an operator allows it to import; SiliconCompiler has no entry-point
    # group for tools, so an out-of-tree driver is named here or not at all.
    "software_drivers": [],
}

# Keys this server once read and no longer does, and why. A config.json that
# still sets one starts, with a warning, rather than refusing as it would an
# unknown key: the operator set it on purpose, and it now means nothing.
RETIRED_KEYS = {
    "portal_plaintext_peers": "the portal is served wherever the API is, and this "
                              "server warns at startup where that is plain http "
                              "beyond this machine",
    "env_build_timeout_seconds": "a build is bounded by the job's limits."
                                 "max_staging_seconds, with the rest of staging",
}

# A notice's shape (surface §1). `starts_at` and `ends_at` are REQUIRED on the
# wire and nullable, so where config leaves one out it is null.
NOTICE_LEVELS = ("info", "warning")
NOTICE_MEMBERS = ("level", "message", "starts_at", "ends_at")
MAX_NOTICE_CHARS = 500

# The resource kinds `denied_resources` is keyed by -- the contract's closed
# `resource_kinds` set.
RESOURCE_KINDS = ("pdk", "library", "fpga", "tool")

# Limits this server enforces and does not publish.
_NOT_PUBLISHED = ("max_detail_chars",)


# Presets for testing a client against deployments that serve less, from what
# this server does by default to the most it can withhold -- and one, mode 4,
# that can fetch nothing, so every job takes the follow-up path.
#
# 🔴 **Every one is a legal v1 deployment, and `GET /v1` says which.** Nothing
# here is a flag a client is told about; a client that behaves correctly under
# these does so because it read what the server published. That is what makes
# them worth testing against.
#
# ⚠️ Applied over the defaults and UNDER `config.json`, so any one value can
# still be moved on top of a mode without writing out the rest.
#
# ⚠️ Mode 3's denials are chosen so that each one is tripped by a different
# demo target and the skywater130 demo still runs: `gf180_demo` for the PDK
# (a glob, because a grant's name is one), `freepdk45_demo` for its library,
# and any flow that runs verilator for the tool.
TEST_MODES: Dict[int, Dict[str, Any]] = {
    # What this server does by default.
    1: {},

    # Each node's live log but not the job's merged one, so a client falls
    # back to one stream per running node; the manifest, logs and reports come
    # over the API and the node archives only through the portal.
    2: {
        "features": ["logs.stream"],
        "api_fetchable_kinds": ["manifest", "logs", "staging", "reports"],
        "limits": {
            "concurrent_jobs": 2,
            "pending_uploads": 4,
            "max_download_bytes": 52428800,             # 50 MiB
        },
    },

    # Manifests and nothing else over the API -- the job's, and each node's,
    # which carry the record and the metrics; no logs, live or archived;
    # one job at a time; and a PDK, a library and a tool nobody may use.
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

    # What mode 1 serves, from a server that can fetch nothing: every job on a
    # remote PDK goes `staging -> awaiting_input` asking for it, and its client
    # sends a second archive -- so a job carries two uploads, each its own
    # `input`, to look at side by side.
    4: {
        "fetch_fails": True,
    },
}


# The largest object S3 takes in one PUT.
S3_ONE_PUT_BYTES = 5 * 1024 ** 3


def _check_policy(values: Dict[str, Any]) -> None:
    '''Refuse a policy value that would silently mean nothing.

    The same rule as an unknown key: a kind or a resource kind spelled wrong is
    a restriction the operator believes they set.
    '''
    from siliconcompiler.remote.server.outputs.artifacts import KINDS

    # 🔴 A limit is a count or a size, or null for none; nothing negative is
    # ever published (surface D177). `-1` is the store's spelling of unlimited
    # in `user_limits`, never the wire's or this file's.
    for name, value in (values["limits"] or {}).items():
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)
                                  or value < 0):
            raise ValueError(f"limits.{name} is a whole number of zero or more, or null "
                             f"for unlimited; not {value!r}")

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

    # A client reading `logs.stream.job` falls back to per-node streams.
    features = values["features"]
    if "logs" in features:
        raise ValueError("features lists logs, which is folded into logs.stream")
    # 🔴 `features` is a registry, not free text (surface *features is a
    # registry*): a string it does not hold would be advertised in `GET /v1`,
    # and a client that knows it would rely on what nothing here serves.
    unregistered = sorted(set(features) - set(FEATURES))
    if unregistered:
        raise ValueError(f"features lists {', '.join(unregistered)}, which is not a "
                         f"registered features string: {', '.join(FEATURES)}")
    if "logs.stream.job" in features and "logs.stream" not in features:
        raise ValueError("features lists logs.stream.job without logs.stream, "
                         "which it implies")

    keepalive = values["stream_keepalive_seconds"]
    if not isinstance(keepalive, int) or isinstance(keepalive, bool) \
            or not 1 <= keepalive < 100:
        raise ValueError("stream_keepalive_seconds is whole seconds, 1 to 99: below "
                         "an intermediary's idle timeout")

    # Refused at LOAD, never trusted to a careful matcher: a bare `*` host, a
    # wildcard anywhere but the leftmost label, a globbed scheme.
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

    # 🔴 Advertised only where this server can serve it: nodes that install on
    # the host -- an operator's choice, since a node then reaches an index --
    # or, where nodes run in containers, the builder.
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

    # 🔴 A reuse hit compares the host's tools among the inputs it was built
    # from (surface §13), and a job run on the host records none: until this
    # server records them, reuse waits for containers (profile §5).
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
    '''Every root `private_dataroots` maps to, once each, in the order the
    configuration gives them: what jobs are given read-only, and what a
    published `detail` must never say.'''
    found: List[str] = []
    for section in ("library", "tool"):
        for roots in (private.get(section) or {}).values():
            found.extend(roots.values())
    for tasks in (private.get("task") or {}).values():
        for roots in tasks.values():
            found.extend(roots.values())
    return list(dict.fromkeys(found))


def _check_private_dataroots(private) -> None:
    '''`private_dataroots` held to its shape: `library`, `tool` and `task`,
    each down to `{dataroot name: absolute path}`.'''
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
        # 🔴 Said plainly: the shape before keypaths was {name: {root: path}},
        # which is `library`'s now, and a tool's root was never named by its
        # task at all.
        raise ValueError(f"{shape}; {unknown[0]!r} is none of library, tool and task. "
                         "An entry of the old {name: {root: path}} shape goes under "
                         '"library", or under "tool" where it is a tool\'s')
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
    '''One deployment's policy.

    Read once at startup. Nothing reloads it: a value that changed under a
    running server would make two requests in the same second answer
    differently, and the restart is cheap.
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

            for key in set(overlay) & set(RETIRED_KEYS):
                import logging
                logging.getLogger("sc-server").warning(
                    f"{path} sets {key}, which is no longer read: {RETIRED_KEYS[key]}")
                overlay.pop(key)

            unknown = set(overlay) - set(DEFAULTS)
            if unknown:
                # Refused rather than ignored: a misspelled key that silently
                # does nothing is a ceiling the operator believes they set.
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
        # (surface §14): a larger limit is a promise that store cannot keep.
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

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    @property
    def limits(self) -> Dict[str, int]:
        return self._values["limits"]

    def api_fetchable(self, kind: str) -> bool:
        '''Whether the API hands over artifacts of this kind.'''
        kinds = self._values["api_fetchable_kinds"]
        return kinds is None or kind in kinds

    def denied_kind(self, name: str) -> Optional[str]:
        '''The kind of resource ``name`` is denied as, or None: a name
        matches at most one resource of any kind (entitlements D75), so the
        kind is found from the name alone.'''
        for kind in sorted(self._values["denied_resources"] or {}):
            if self.denied(kind, name):
                return kind
        return None

    def denied(self, resource_kind: str, name: str) -> bool:
        '''Whether no caller may use this PDK, library or tool.'''
        from fnmatch import fnmatchcase

        patterns = (self._values["denied_resources"] or {}).get(resource_kind, [])
        return any(fnmatchcase(name, pattern) for pattern in patterns)

    def notices(self, at: Optional[float] = None) -> list:
        '''The notices published now: each from when it was posted -- here,
        when the server started -- until its `ends_at` passes.'''
        import time

        at = time.time() if at is None else at
        return [dict(notice) for notice in self._values["notices"]
                if notice["ends_at"] is None or _instant(notice["ends_at"]) > at]

    def capabilities(self, software: Dict[str, list]) -> Dict[str, Any]:
        '''The ``GET /v1`` body.

        ``software`` is passed in rather than read here because it is the one
        member that comes from the store: a version is advertised only where a
        live image contains it.
        '''
        block = {
            "api_version": "v1",
            "software": software,
            "grant_types_supported": list(self._values["grant_types_supported"]),
            # Ten, every one REQUIRED (surface §1): `max_detail_chars` bounds
            # this server's own output and no client acts on it -- the test
            # `run_heartbeat_seconds` failed -- so it stays in config and off
            # the wire.
            "limits": {name: value for name, value in self._values["limits"].items()
                       if name not in _NOT_PUBLISHED},
            "features": list(self._values["features"]),
            "identity_assurance": self._values["identity_assurance"],
            "notices": self.notices(),
        }

        # OPTIONAL, and absent means the operator set none. Emitting null would
        # say something different.
        if self._values["terms_url"]:
            block["terms_url"] = self._values["terms_url"]

        return block
