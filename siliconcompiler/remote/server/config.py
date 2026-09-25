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
from typing import Any, Dict, Union

__all__ = ["Config", "DEFAULTS", "CONFIG_FILENAME"]


CONFIG_FILENAME = "config.json"

# Every value is a base unit and its own name says which: bytes are never MB,
# and a count is never a duration. The refusal that names a key back spells it
# identically, which is what makes the error registry double as the enforcement
# trace.
DEFAULT_LIMITS: Dict[str, int] = {
    "max_job_nodes": 1000,                  # nodes in one flow
    "max_upload_bytes": 1073741824,         # bytes
    "job_retention_days": 30,               # days
    "pending_uploads": 8,                   # jobs held in created or awaiting_input
    "concurrent_jobs": 4,                   # jobs in queued, running or cancelling
    # Open /logs streams per caller, and the number is chosen rather than
    # inherited. What one costs, now that there is something to measure: a
    # worker thread and an open file for as long as it lives, which is up to
    # max_log_stream_seconds, plus a stat twice a second while the log is quiet.
    # Under a threaded WSGI server there is no fixed pool to exhaust, so what
    # runs out is memory and descriptors rather than capacity.
    #
    # 8 is generous for a person -- nobody reads eight logs at once -- and
    # deliberately not generous enough for a client that would open one per node
    # of a wide flow. That client should poll the job, which is one request for
    # the whole run, and tail only the nodes somebody is actually watching.
    "concurrent_log_streams": 8,
    "max_log_stream_seconds": 14400,        # 4h; the client sets its reconnect timer from it,
                                            # and jobs routinely outlast it
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
}

DEFAULTS: Dict[str, Any] = {
    # What a caller may ask for. The device grant is not served here, so it is
    # not advertised: this list is what the client branches on, never
    # identity_assurance.
    "grant_types_supported": ["client_credentials", "refresh_token"],

    # A registry, not free text: absent and unrecognised mean the same thing to
    # a client, so a value is only listed once it is served. Both are, now:
    # `logs` is the archived file and `logs.stream` is the live tail, and they
    # are two strings because one could not say which of the two a deployment
    # had.
    "features": ["logs", "logs.stream"],

    # The honesty half, pairing with the startup log. "verified" is the only
    # value that asserts anything; every other value, known or unknown, means
    # do not rely on this identity.
    "identity_assurance": "self-asserted",

    # REQUIRED, and [] is the answer here. An operator with something to say
    # puts it in config.json.
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

    # Where a person reads about a job, as an absolute origin -- this
    # deployment then appends its own portal path. `GET /v1/jobs/{id}` and the
    # create response publish the result as `web_url`.
    #
    # 🔴 **Config, and never `Host` or `X-Forwarded-Host`.** Both are attacker
    # controlled unless a trusted proxy is rewriting them, and the output here
    # is a link that gets pasted into a ticket and clicked by somebody else --
    # the same trap as trusting a forwarded client address, with a worse
    # payoff for whoever poisons it.
    #
    # None means ABSENT rather than null: null would claim there is a portal
    # and that this job has no page on it, which is never true.
    "web_url_base": None,

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

    # Host paths every container must be able to see, on top of the data
    # directory, which is always mounted because every path in a job's manifest
    # is under it.
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
}


class Config:
    '''One deployment's policy.

    Read once at startup. Nothing reloads it: a value that changed under a
    running server would make two requests in the same second answer
    differently, and the restart is cheap.
    '''

    def __init__(self, values: Dict[str, Any]):
        self._values = values

    @classmethod
    def load(cls, datadir: Union[str, Path]) -> "Config":
        '''Defaults, overlaid with ``<datadir>/config.json`` if it is there.'''
        values = dict(DEFAULTS)
        values["limits"] = dict(DEFAULT_LIMITS)

        path = Path(datadir) / CONFIG_FILENAME
        if path.exists():
            overlay = json.loads(path.read_text())
            if not isinstance(overlay, dict):
                raise ValueError(f"{path} must hold a JSON object")

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
            "limits": dict(self._values["limits"]),
            "features": list(self._values["features"]),
            "identity_assurance": self._values["identity_assurance"],
            "notices": list(self._values["notices"]),
        }

        # OPTIONAL, and absent means the operator set none. Emitting null would
        # say something different.
        if self._values["terms_url"]:
            block["terms_url"] = self._values["terms_url"]

        return block
