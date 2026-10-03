import os

import pytest

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.running import runner, runspec
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.state.store import Store


# The registry on its own: resolution is a pure function of what an operator
# registered, with no Flask, port or job needed.


def digest(letter):
    return "sha256:" + letter * 64


def py(name=None, wanted=None, tools=None):
    '''A bucketed `requested_versions`. 🔴 The whole python set has to be held
    by ONE image; a tool is satisfied per node.'''
    return {"python": {name: wanted} if name else {}, "tools": tools or {}}


# The SiliconCompiler this registry holds, so the one the server runs (§5).
OWN = "0.39.1"


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(images, "own_version", lambda: OWN)
    with Store("server.db") as db:
        user = db.upsert_user("operator", "someone@host")
        db.actor = user["id"]
        yield db


@pytest.fixture
def registry(store):
    '''A small image with the framework and a big one with a tool: an import
    node has no business pulling the one OpenROAD is in.'''
    images.register_software(store, "siliconcompiler", "SiliconCompiler", store.actor, "python")
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor, preference=10)
    images.register_software(store, "openroad", "OpenROAD", store.actor, "tool")
    images.register_version(store, "openroad", "2.0", store.actor)

    images.register_image(store, "ghcr.io/x/sc-python:0.39.1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor)
    images.register_image(store, "ghcr.io/x/sc-tools:0.39.1", digest("b"),
                          [("siliconcompiler", "0.39.1"), ("openroad", "2.0")],
                          store.actor)
    return store


def sc(store, *versions):
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")
    for version in versions:
        images.register_version(store, "siliconcompiler", version, store.actor)


def live_refs(store, ref):
    return [image["digest"] for image in images.live_images(store)
            if image["registry_ref"] == ref]


def refused(store, requires, nodes, **kwargs):
    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, requires, nodes, **kwargs)
    return raised.value


###########################
# Naming what runs
###########################

@pytest.mark.parametrize("ref,expected", [
    ("ghcr.io/org/sc:0.39.1", "ghcr.io/org/sc"),
    ("ghcr.io/org/sc", "ghcr.io/org/sc"),
    # A colon before the last slash is a registry port and not a tag.
    ("localhost:5000/sc", "localhost:5000/sc"),
    ("localhost:5000/sc:v2", "localhost:5000/sc"),
    # A tag beside a digest comes off too.
    (f"localhost:5000/sc:v2@{'sha256:' + 'd' * 64}", "localhost:5000/sc"),
])
def test_the_tag_comes_off_and_the_port_does_not(ref, expected):
    assert images.pinned_ref(ref, digest("c")) == f"{expected}@{digest('c')}"


def test_an_image_with_a_bad_digest_or_an_unregistered_version_is_refused(store):
    '''The FK would catch the version; this catches it with a sentence.'''
    sc(store, "0.39.1")

    with pytest.raises(ValueError):
        images.register_image(store, "ghcr.io/x/y:1", "latest",
                              [("siliconcompiler", "0.39.1")], store.actor)
    with pytest.raises(ValueError, match="not a registered version"):
        images.register_image(store, "ghcr.io/x/y:1", digest("a"),
                              [("siliconcompiler", "0.40.0")], store.actor)


def test_registering_the_same_digest_again_is_the_same_image(registry, store):
    '''The digest is the identity: the same bytes again supersede nothing
    (that would retire itself), and a new tag over them is an update.'''
    first = store.one("SELECT id FROM images WHERE digest = ?", (digest("a"),))["id"]

    images.register_image(store, "ghcr.io/x/sc-python:0.39.1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor)
    assert live_refs(store, "ghcr.io/x/sc-python:0.39.1") == [digest("a")]

    again = images.register_image(store, "ghcr.io/x/sc-python:latest", digest("a"),
                                  [("siliconcompiler", "0.39.1")], store.actor)
    assert again == first
    assert len(images.live_images(store)) == 2


def test_rebuilding_a_tag_supersedes_the_build_before_it(registry, store):
    '''🔴 One live image per reference: two are indistinguishable to the
    resolution, and on the rig jobs kept starting in the previous build.
    Superseded, not deleted, so *what did this run in* stays answerable.'''
    before = next(image for image in images.live_images(store)
                  if image["registry_ref"] == "ghcr.io/x/sc-python:0.39.1")

    images.register_image(store, "ghcr.io/x/sc-python:0.39.1", digest("e"),
                          [("siliconcompiler", "0.39.1")], store.actor)

    assert live_refs(store, "ghcr.io/x/sc-python:0.39.1") == [digest("e")]
    assert store.one("SELECT retired_at FROM images WHERE id = ?",
                     (before["id"],))["retired_at"]


###########################
# The resolution
###########################

@pytest.mark.parametrize("requires", [
    py("siliconcompiler", "0.39.1"),
    py(),                                                       # the preferred one
    py("siliconcompiler", ">=0.39,<0.40"),
    py("siliconcompiler", ["==9.9.9", "0.39.1"]),               # alternatives
    py(tools={"openroad": ">=2.0"}),
    py(tools={"openroad": [">=9.0", "==2.0"]}),
    py(tools={"openroad": []}),                                 # any version
    py("za-sclib", "0.1.80"),                                   # not tracked here
], ids=["bare", "unnamed", "range", "python-list", "tool-range", "tool-list",
        "tool-empty", "untracked"])
def test_each_node_resolves_to_the_smallest_image_that_fits(registry, store, requires):
    '''🔴 Per node and by digest: an import node never pulls the OpenROAD
    image, a node declaring nothing (a builtin join) gets the job's own, and a
    rebuilt tag cannot change what runs.

    A bare version means exactly that; a range is resolved here, not by the
    client (the image join is over combinations); a list is alternatives, as a
    `Task`'s version is; an empty list is any version (what a client sends,
    since setup() runs in the image); a version this deployment does not
    track is no requirement (`version-skew` at create answers it).'''
    plan = images.plan_for_job(store, requires,
                               {("import", "0"): None, ("place", "0"): "openroad"})

    assert plan.ref(plan.job) == f"ghcr.io/x/sc-python@{digest('a')}"
    assert plan.nodes[("import", "0")] == plan.job
    assert plan.ref(plan.nodes[("place", "0")]) == f"ghcr.io/x/sc-tools@{digest('b')}"


def test_specifiers_read_a_bare_version_as_exact_and_a_list_as_alternatives():
    assert images.specifiers("0.39.1") == ("==0.39.1",)
    assert images.specifiers(">=0.39") == (">=0.39",)
    assert images.specifiers("") == ()
    assert images.specifiers(None) == ()
    # An empty entry in a list is not a requirement.
    assert images.specifiers([">=0.39", "2.0"]) == (">=0.39", "==2.0")
    assert images.specifiers([""]) == ()


@pytest.mark.parametrize("version,admitted", [
    ("0.38.10.dev7", True), ("0.38.10", True), ("0.38.10rc1", True), ("0.38.11.dev1", False)])
def test_a_prefix_admits_pre_releases(version, admitted):
    '''🔴 Surface D154: `packaging` before 26.0 leaves `0.38.10.dev7` out of
    `==0.38.10.*` by default, so the match passes `prereleases=True`.'''
    assert images.matches(version, "reported", ("==0.38.10.*",)) is admitted


def test_a_node_that_follows_its_input_runs_where_that_input_ran(registry, store):
    '''🆕 An execute task's command comes out of the manifest; the environment
    that made its inputs is likeliest to run it. With that input not in this
    run, it falls back to the job's image.'''
    plan = images.plan_for_job(
        store, py("siliconcompiler", "0.39.1"),
        {("place", "0"): "openroad", ("after", "0"): None},
        inherits={("after", "0"): ("place", "0")})

    assert plan.nodes[("after", "0")] == plan.nodes[("place", "0")]
    assert plan.nodes[("after", "0")] != plan.job

    alone = images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                                {("after", "0"): None}, inherits={("after", "0"): None})
    assert alone.nodes[("after", "0")] == alone.job


@pytest.mark.parametrize("tool,retired", [("verilator", False), ("openroad", True)])
def test_a_tool_with_no_live_software_is_refused_as_a_resource(registry, store, tool,
                                                               retired):
    '''🔴 Reverses the old rule that only a REGISTERED name raises a
    requirement: with containers on, the registry IS the world, and a `bsc`
    node placed in the python-only image died on the rig. Retiring the
    software (*not any more*, beside a version's *not this one*) is the same.'''
    if retired:
        images.retire_version(store, "openroad", "2.0", store.actor)
        images.retire_software(store, "openroad", store.actor)

    problem = refused(store, py("siliconcompiler", "0.39.1"), {("x", "0"): tool})

    # `unsatisfiable-request` was retired (D116): a tool is a resource too.
    assert problem.error.slug == "resource-unavailable"
    assert problem.members == {"resource_kind": "tool", "resource": tool}
    assert "nowhere for it to run" in problem.detail


@pytest.mark.parametrize("extra,requires,nodes,unresolved", [
    # A range nothing satisfies, refused before anything runs.
    ([], py("siliconcompiler", ">=0.40"), {("import", "0"): None},
     ("python", "siliconcompiler", [">=0.40"], ["0.39.1"])),
    # 🔴 D91: what IS available, so the caller can act on it.
    ([], py(tools={"openroad": ">=3.0"}), {("place", "0"): "openroad"},
     ("tools", "openroad", [">=3.0"], ["2.0"])),
    # The alternatives exactly as asked for.
    ([], py(tools={"openroad": [">=9.0", "==8.0"]}), {("place", "0"): "openroad"},
     ("tools", "openroad", [">=9.0", "==8.0"], ["2.0"])),
    # Registered, and no image holds it.
    ([("siliconcompiler", "0.40.0")], py("siliconcompiler", "0.40.0"),
     {("import", "0"): None}, ("python", "siliconcompiler", ["==0.40.0"], ["0.39.1"])),
    ([("yosys", "0.44")], py(), {("syn", "0"): "yosys"}, ("tools", "yosys", [], [])),
])
def test_a_requirement_no_image_holds_fails_the_whole_submit(
        registry, store, extra, requires, nodes, unresolved):
    for name, version in extra:
        if name != "siliconcompiler":
            images.register_software(store, name, name.title(), store.actor, "tool")
        images.register_version(store, name, version, store.actor)

    problem = refused(store, requires, nodes)

    assert problem.error.slug == "software-unavailable"
    assert problem.members["reason"] == "unavailable"
    kind, name, requirement, available = unresolved
    assert problem.members["unresolved"] == [
        {"kind": kind, "name": name, "requirement": requirement, "available": available}]


def test_a_job_missing_two_tools_reports_both(registry, store):
    '''Not just the first the node loop reached: that is two round trips.'''
    images.register_software(store, "yosys", "Yosys", store.actor, "tool")
    images.register_version(store, "yosys", "0.40", store.actor)
    images.register_image(store, "ghcr.io/x/yosys:1", digest("e"),
                          [("siliconcompiler", "0.39.1"), ("yosys", "0.40")],
                          store.actor)

    problem = refused(store, py(tools={"openroad": ">=3.0", "yosys": ">=99"}),
                      {("place", "0"): "openroad", ("syn", "0"): "yosys"})

    assert problem.members["reason"] == "unavailable"
    assert {e["name"] for e in problem.members["unresolved"]} == {"openroad", "yosys"}


def test_an_empty_registry_is_a_refusal_and_not_a_bypass(store):
    '''⚠️ Only reached where the deployment runs containers, so an empty
    registry is a misconfiguration (bare Slurm never calls this).'''
    problem = refused(store, py("siliconcompiler", "0.39.1"),
                      {("import", "0"): None, ("place", "0"): "openroad"})

    assert problem.error.slug == "software-unavailable"
    assert problem.members["reason"] == "unavailable"


@pytest.mark.parametrize("retire", ["version", "images"])
def test_what_is_retired_stops_satisfying_and_never_runs_on_the_host(
        registry, store, retire):
    '''⚠️ An image is never deleted: a job from last year names one.'''
    if retire == "version":
        images.retire_version(store, "openroad", "2.0", store.actor)
    else:
        for image in images.live_images(store):
            images.retire_image(store, image["id"], store.actor)
            assert store.one("SELECT retired_by FROM images WHERE id = ?",
                             (image["id"],))["retired_by"] == store.actor

    problem = refused(store, py("siliconcompiler", "0.39.1"),
                      {("import", "0"): None, ("place", "0"): "openroad"})
    assert problem.error.slug == "software-unavailable"


###########################
# What GET /v1 says about it
###########################

def test_a_version_is_advertised_only_where_an_image_holds_it(registry, store):
    '''⚠️ Without containers there are no images, so the join would advertise
    nothing while the versions it genuinely runs sit in the table.'''
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor)

    assert store.advertised_software(containers=True) == {
        "python": {"siliconcompiler": ["0.39.1"]},
        "tools": {"openroad": ["2.0"]}, "interpreter": {}}
    assert store.advertised_software(containers=False)["python"] == \
        {"siliconcompiler": ["0.39.1", "0.40.0"]}


###########################
# What the compute node does with it
###########################

def test_tracking_is_the_deployments_to_turn_on(nop_project, tmp_path):
    """`track_provenance`: each node records its machine, through the run file.
    Off, the job's own setting stands rather than being switched off."""
    runspec.normalize(nop_project, "job-id", "build", "cache")
    assert not nop_project.option.get_track()

    run = tmp_path / runspec.RUN_FILENAME
    runspec.write_run(run, "job-id", "build", "cache", "local", track=True)
    runspec.apply_run(nop_project, runspec.read_run(run))
    assert nop_project.option.get_track() is True

    runspec.normalize(nop_project, "job-id", "build", "cache")
    assert nop_project.option.get_track() is True


def test_a_cluster_is_placed_by_slurm_and_never_by_docker(nop_project):
    """🔴 `option,scheduler,name` holds ONE value, and on a cluster Slurm
    places the work. ⚠️ `queue` is Slurm's PARTITION, so it stays untouched; the
    placement reads back as a bundle."""
    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): "/sc_server/images/659b"},
                      cluster="slurm")

    scheduler = nop_project.option.scheduler
    assert scheduler.get_name(step="stepone", index="0") == "slurm"
    assert scheduler.get_queue(step="stepone", index="0") is None

    options = scheduler.get_options(step="stepone", index="0")
    assert options[options.index("--container") + 1] == "/sc_server/images/659b"
    # 🔴 A job of its own, never a step: `--partition` on a step is silently
    # ignored, so it would run on the orchestrator's one core.
    assert "--overlap" not in options
    assert runspec.node_image(nop_project, "stepone", "0") == \
        ("container", "/sc_server/images/659b")


def test_a_server_with_no_cluster_uses_the_docker_scheduler(nop_project):
    """A digest is what the docker scheduler reads out of `queue`, and the
    manifest carries the placement: the runner holds no database connection."""
    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): f"ghcr.io/x/sc@{digest('a')}"},
                      cluster="local")

    scheduler = nop_project.option.scheduler
    assert scheduler.get_name(step="stepone", index="0") == "docker"
    assert scheduler.get_queue(step="stepone", index="0") == f"ghcr.io/x/sc@{digest('a')}"
    assert runspec.node_image(nop_project, "stepone", "0") == \
        ("image", f"ghcr.io/x/sc@{digest('a')}")
    assert runspec.node_image(nop_project, "steptwo", "0") is None


@pytest.mark.parametrize("cluster,name", [("slurm", "slurm"), ("local", None)])
def test_a_node_with_no_image_is_scheduled_only_on_a_cluster(nop_project, cluster, name):
    '''🔴 On a cluster every node is its own Slurm job, image or not; one
    allocation could never use more than the machine it landed on. No
    `--no-requeue`, which srun refuses: a node is never requeued anyway.'''
    runspec.normalize(nop_project, "job-id", "build", "cache", cluster=cluster)

    scheduler = nop_project.option.scheduler
    for step in ("stepone", "steptwo"):
        assert scheduler.get_name(step=step, index="0") == name
        assert not scheduler.get_options(step=step, index="0")


def test_the_runner_leaves_its_own_allocation(monkeypatch):
    """🔴 Slurm makes a STEP, not a JOB, while SLURM_JOB_ID is set: measured on
    the rig, `srun --partition=sc` inside one ignored the partition."""
    monkeypatch.setenv("SLURM_JOB_ID", "5")
    monkeypatch.setenv("SLURM_STEP_ID", "1")

    runner._leave_the_allocation()

    assert "SLURM_JOB_ID" not in os.environ
    assert "SLURM_STEP_ID" not in os.environ


def progress(monkeypatch, **states):
    monkeypatch.setattr(runner, "_progress_path", None)
    monkeypatch.setattr(runner, "_progress",
                        {"nodes": {key: {"state": state} for key, state in states.items()}})
    return runner._progress["nodes"]


def placed(nop_project, *steps):
    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={(step, "0"): f"ghcr.io/x/sc@{digest('a')}" for step in steps})


def test_a_node_waiting_for_its_image_is_preparing(monkeypatch, nop_project):
    """🔴 A tool image takes minutes on a cold host; without a state for the
    wait it is indistinguishable from a hang."""
    placed(nop_project, "stepone", "steptwo")
    nodes = progress(monkeypatch, **{"stepone/0": "pending", "steptwo/0": "pending"})

    seen = []
    monkeypatch.setattr(runner, "_placement_present", lambda placement: False)
    monkeypatch.setattr(runner, "_make_placement", lambda placement: seen.append(
        {key: node["state"] for key, node in nodes.items()}))

    runner._fetch_images(nop_project)

    assert seen == [{"stepone/0": "preparing", "steptwo/0": "preparing"}]
    assert {key: node["state"] for key, node in nodes.items()} == \
        {"stepone/0": "queued", "steptwo/0": "queued"}


def fails(message):
    def make(placement):
        raise RuntimeError(message)
    return make


@pytest.mark.parametrize("image,state,present,make,after", [
    # Already on the host: nothing to wait for, so saying so would be noise.
    (True, "pending", lambda p: True, lambda p: pytest.fail("fetched"), "pending"),
    # ⚠️ A failed fetch does not end the run: the node's own launch fails with
    # the message that knows about registry credentials.
    (True, "pending", lambda p: False, fails("no such host"), "queued"),
    # No placement, the default deployment: nothing is looked for.
    (False, "pending", lambda p: pytest.fail("looked for an image"), None, "pending"),
    # A node `_settle` already wrote off never walks back to `preparing`.
    (True, "skipped", lambda p: False, lambda p: pytest.fail("fetched"), "skipped"),
])
def test_a_node_is_preparing_only_while_its_image_is_fetched(monkeypatch, nop_project,
                                                             image, state, present,
                                                             make, after):
    placed(nop_project, *(["stepone"] if image else []))
    nodes = progress(monkeypatch, **{"stepone/0": state})
    monkeypatch.setattr(runner, "_placement_present", present)
    monkeypatch.setattr(runner, "_make_placement", make)

    runner._fetch_images(nop_project)

    assert nodes["stepone/0"]["state"] == after


def test_a_node_whose_image_would_not_pull_is_interrupted_naming_it(
        monkeypatch, nop_project):
    '''🔴 Told by the runtime's pull error, never an exit status: the node
    failed with its image absent, its pull having failed first (§10).'''
    placed(nop_project, "stepone")
    nodes = progress(monkeypatch, **{"stepone/0": "pending"})
    monkeypatch.setattr(runner, "_placement_present", lambda placement: False)
    monkeypatch.setattr(runner, "_make_placement",
                        fails("pull access denied for ghcr.io/x/sc"))
    monkeypatch.setattr(runner, "_watch_for_oom", lambda: None)
    monkeypatch.setattr(runner, "_pull_errors", {})
    runner._fetch_images(nop_project)

    nop_project.set("record", "status", "error", step="stepone", index="0")
    runner._node_finished(nop_project, "stepone", "0")

    assert nodes["stepone/0"]["state"] == "failed"
    assert nodes["stepone/0"]["interrupted"]["image"] == f"ghcr.io/x/sc@{digest('a')}"
    assert "pull access denied" in nodes["stepone/0"]["interrupted"]["error"]


def test_a_node_killed_for_memory_names_the_limit(monkeypatch, nop_project):
    '''By the docker daemon's `oom` event for the node's label -- never exit
    status 137, which any SIGKILL gives.'''
    monkeypatch.setattr(runner, "_oom_killed", {("stepone", "0")})
    monkeypatch.setattr(runner, "_pull_errors", {})
    nodes = progress(monkeypatch, **{"stepone/0": "running", "steptwo/0": "running"})

    for step in ("stepone", "steptwo"):
        nop_project.set("record", "status", "error", step=step, index="0")
        nop_project.set("record", "toolexitcode", 137, step=step, index="0")
        runner._node_finished(nop_project, step, "0")

    assert nodes["stepone/0"]["limit"] == "memory"
    assert "limit" not in nodes["steptwo/0"]


def test_a_half_written_bundle_counts_as_absent():
    """A bundle is a directory; its config is renamed into place last."""
    os.makedirs("bundle", exist_ok=True)
    assert runner._placement_present(("container", "bundle")) is False

    with open("bundle/config.json", "w") as f:
        f.write("{}")
    assert runner._placement_present(("container", "bundle")) is True


def test_a_bundle_with_no_recorded_source_says_so(monkeypatch):
    """The bundle path names a digest, never the registry to unpack from."""
    monkeypatch.setattr(runner, "_image_sources", {})

    with pytest.raises(RuntimeError, match="nothing recorded to unpack"):
        runner._unpack_bundle("/sc_server/images/659b")


def test_what_a_node_needs_is_declared_and_never_inferred():
    '''🔴 Inferring from the tool NAME says `builtin` (a nop flow was refused
    for it on the rig); from `exe`, nothing for slang, which drives pyslang
    in-process. ⚠️ Read off a BARE task class, one attribute per node; the
    drivers declare the three cases an inference rule gets wrong.'''
    from siliconcompiler.remote.runflow import node_tools
    from siliconcompiler.tools.builtin.nop import NOPTask
    from siliconcompiler.tools.execute.exec_input import ExecInputTask
    from siliconcompiler.tools.slang.elaborate import Elaborate

    declared = {"join": None, "compute": None, "place": "openroad",
                "elaborate": "slang"}

    class Flow:
        def get_task_module(self, step, index):
            class Task:
                _remote_toolname = declared[step]
            return Task

    assert node_tools(Flow(), [(step, "0") for step in declared]) == \
        {(step, "0"): tool for step, tool in declared.items()}

    assert NOPTask()._remote_toolname is None
    assert NOPTask()._remote_inherits_env is False
    assert Elaborate()._remote_toolname == "slang"
    # 🆕 The command comes out of the manifest; it follows its input.
    assert ExecInputTask()._remote_toolname is None
    assert ExecInputTask()._remote_inherits_env is True


###########################
# Versions: normalised, and reported vs published_date
###########################

def test_a_version_is_normalised_when_it_is_registered(store):
    '''🔴 At registration, not request time, so client and server releases
    cannot normalise one string differently and silently disagree. An image
    may name what the tool printed: `verilator 5.052` is stored `5.52`.'''
    sc(store)
    images.register_software(store, "verilator", "Verilator", store.actor, "tool")

    assert images.register_version(store, "siliconcompiler", "v0.39.1",
                                   store.actor) == "0.39.1"
    assert images.live_software(store)["python"]["siliconcompiler"] == ["0.39.1"]
    assert images.register_version(store, "verilator", "5.052", store.actor) == "5.52"

    images.register_image(store, "ghcr.io/x/v:1", digest("a"), [("verilator", "5.052")],
                          store.actor)
    held = images.live_images(store)[0]["contents"]
    assert [(entry.name, entry.version) for entry in held] == [("verilator", "5.52")]


def test_a_version_that_is_not_pep_440_is_refused_unless_it_is_a_published_date(store):
    '''🔴 `version_norm` is NOT NULL, so `initialize` (gtkwave's parse of
    `Could not initialize GTK!`) is refused, not coerced -- and accepted as
    `published_date`, stored exactly as given.'''
    images.register_software(store, "gtkwave", "GTKWave", store.actor, "tool")

    with pytest.raises(ValueError, match="not a PEP 440 version"):
        images.register_version(store, "gtkwave", "initialize", store.actor)
    assert store.one("SELECT version FROM software_versions "
                     "WHERE software_name = 'gtkwave'") is None

    assert images.register_version(store, "gtkwave", "20260924", store.actor,
                                   source="published_date") == "20260924"


def test_an_unversioned_tool_runs_and_cannot_satisfy_a_requirement(store):
    '''A complete tool list beats a partial one: the mark costs version
    matching, not existence -- 🔴 `20260924` beats `2.0.1` under any
    comparison. The refusal says *reports no version*, not *no image
    matches*, which sends somebody hunting for an installed tool.'''
    sc(store, "0.39.1")
    images.register_software(store, "magic", "Magic", store.actor, "tool")
    images.register_version(store, "magic", "20260924", store.actor, source="published_date")
    images.register_image(store, "ghcr.io/x/sc-magic:1", digest("c"),
                          [("siliconcompiler", "0.39.1"), ("magic", "20260924")],
                          store.actor)

    assert images.plan_for_job(store, py(), {("drc", "0"): "magic"}).nodes[("drc", "0")]

    problem = refused(store, py(tools={"magic": ">=1.0"}), {("drc", "0"): "magic"})
    assert problem.error.slug == "software-unavailable"
    assert "reports no version" in problem.detail
    assert "no image on this server holds" not in problem.detail

    assert not images.matches("20260924", "published_date", ">=2.0")
    assert not images.matches("20260924", "published_date", "==20260924")
    assert images.matches("20260924", "published_date", None)


def test_every_bucket_is_listed_and_reported_sorts_above_published_date(store):
    '''The buckets are a closed set, all always there.'''
    images.register_software(store, "magic", "Magic", store.actor, "tool")
    images.register_version(store, "magic", "20260924", store.actor,
                            source="published_date")
    images.register_version(store, "magic", "8.3.2", store.actor)

    live = images.live_software(store)
    assert set(live) == {"python", "tools", "interpreter"}
    assert live["python"] == {}
    assert live["tools"]["magic"] == ["8.3.2", "20260924"]


###########################
# What the job ran in
###########################

def test_a_descriptor_resolves_to_its_digests_with_no_upload(registry, store):
    '''🔴 What lets create fold them into the job identity: resolution needs the
    declared versions and the registry, nothing else; nothing to run is refused.'''
    assert images.job_image_for(
        store, py("siliconcompiler", ">=0.39,<0.40"))["digest"] == digest("a")

    with pytest.raises(ProblemError):
        images.job_image_for(store, py("siliconcompiler", "==9.9.9"))


def test_what_a_job_ran_is_the_union_of_its_images(registry, store):
    '''⚠️ A list per name: a wide flow's images may hold different versions.'''
    plan = images.plan_for_job(store, py(), {("import", "0"): None,
                                             ("place", "0"): "openroad"})

    held = images.contents_of(store, [plan.job, *plan.nodes.values()])

    assert held == {"python": {"siliconcompiler": ["0.39.1"]},
                    "tools": {"openroad": ["2.0"]}}
    assert images.contents_of(store, [None, None]) == {}


def test_the_python_set_must_be_held_by_one_image(store):
    '''🔴 They share an interpreter. D110: each resolves alone and no image
    holds them together, so it is a combination naming every requirement with
    what is available.'''
    both = {"python": {"siliconcompiler": "0.39.1", "za-sclib": "0.1.80"}, "tools": {}}
    sc(store, "0.39.1")
    images.register_software(store, "za-sclib", "ZA", store.actor, "python")
    images.register_version(store, "za-sclib", "0.1.80", store.actor)
    images.register_image(store, "ghcr.io/x/sc:1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor)
    images.register_image(store, "ghcr.io/x/lib:1", digest("b"),
                          [("za-sclib", "0.1.80")], store.actor)

    problem = refused(store, both, {("import", "0"): None})

    assert problem.error.slug == "software-unavailable"
    assert problem.members["reason"] == "combination"
    assert {(e["name"], tuple(e["available"])) for e in problem.members["unresolved"]} \
        == {("siliconcompiler", ("0.39.1",)), ("za-sclib", ("0.1.80",))}

    images.register_image(store, "ghcr.io/x/both:1", digest("c"),
                          [("siliconcompiler", "0.39.1"), ("za-sclib", "0.1.80")],
                          store.actor)
    plan = images.plan_for_job(store, both, {("import", "0"): None})
    assert plan.ref(plan.job).startswith("ghcr.io/x/both@")


def test_requested_versions_is_the_one_member_and_every_value_is_a_list():
    '''🔴 `versions` and its per-name fallback are gone (D126, superseded); a
    bare string is refused.'''
    from siliconcompiler.remote.server.jobs.common import requirements

    found = requirements({
        "versions": {"python": {"za-sclib": "1.4.0"}},        # ignored
        "requested_versions": {"python": {"siliconcompiler": ["==0.39.1"],
                                          "za-sclib": ["==1.4.0"]},
                               "tools": {"openroad": [">=24.3.2011", "==2.0"], "yosys": []}}})

    assert found["python"] == {"siliconcompiler": ["==0.39.1"], "za-sclib": ["==1.4.0"]}
    assert found["tools"] == {"openroad": [">=24.3.2011", "==2.0"], "yosys": []}

    with pytest.raises(ProblemError, match="bare string"):
        requirements({"requested_versions": {"python": {"siliconcompiler": "==0.39.1"}}})


###########################
# What software may be registered as
###########################

@pytest.mark.parametrize("name,kind,driver,match", [
    ("za-sclib", "python", "za_sclib.tools", "a driver is what makes"),
    # 🔴 D95: the probe imports the driver, and anyone can register software.
    *[("x", "tool", driver, "not a driver this server imports")
      for driver in ("os", "subprocess", "evil.module", "siliconcompiler.toolsx", "a..b")],
    ("pypy", "interpreter", None, "one name"),
])
def test_software_is_refused_a_driver_it_may_not_have(store, name, kind, driver, match):
    with pytest.raises(ValueError, match=match):
        images.register_software(store, name, name.upper(), store.actor, kind, driver=driver)


def _recorded(store, name):
    return dict(store.one("SELECT driver, version_package FROM software WHERE name = ?",
                          (name,)))


def test_a_driver_is_recorded_so_a_probe_can_be_handed_it(store):
    '''🔴 The probe runs in another interpreter, so the driver is data. An
    out-of-tree one is the deployment's `software_drivers`, never a form's;
    none at all is a tool nothing here drives.'''
    images.register_software(store, "openroad", "OpenROAD", store.actor, "tool",
                             driver="siliconcompiler.tools.openroad")
    images.register_software(store, "acme", "Acme", store.actor, "tool",
                             driver="acme_tools.acme", allowed_drivers=["acme_tools.acme"])
    images.register_software(store, "x", "X", store.actor, "tool", driver="")

    assert _recorded(store, "openroad") == {"driver": "siliconcompiler.tools.openroad",
                                            "version_package": None}
    assert _recorded(store, "acme")["driver"] == "acme_tools.acme"


def test_the_registry_command_records_the_distribution_a_version_is_read_from(store, capsys):
    '''Stored, not only echoed: the probe reads slang's version by it.'''
    from siliconcompiler.remote.server.software import registry as command

    assert command.main(["-datadir", ".", "add-software", "slang", "-kind", "tool",
                         "-version-package", "pyslang"]) == 0
    assert "version read from the pyslang distribution" in capsys.readouterr().out

    assert _recorded(store, "slang") == {"driver": None, "version_package": "pyslang"}


###########################
# Two images, identical versions
###########################

@pytest.mark.parametrize("built_a,built_b,pin_a,pin_b", [
    # The build time breaks the tie preference cannot, against the pin.
    ("2026-01-01T00:00:00.000Z", "2026-09-01T00:00:00.000Z", "2026-09-01", "2026-01-01"),
    # ⚠️ NULL is a manifest that said nothing, not *old*: it sorts last.
    (None, "2020-01-01T00:00:00.000Z", "2026-09-01", "2026-01-01"),
    # Equal or NULL (ko, Nix and Bazel stamp 1970): the later pin decides.
    (None, None, "2026-01-01", "2026-09-01"),
    ("1970-01-01T00:00:01.000Z", "1970-01-01T00:00:01.000Z", "2026-01-01", "2026-09-01"),
])
def test_the_build_time_then_the_pin_breaks_a_tie(store, built_a, built_b, pin_a, pin_b):
    '''🔴 Same preference, contents and version: never whichever reference
    sorts first (`b` sorts second, so only the tie-break puts it first).'''
    sc(store, "0.39.1")
    for name, built, pinned in (("a", built_a, pin_a), ("b", built_b, pin_b)):
        image_id = images.register_image(store, f"ghcr.io/x/{name}:1", digest(name),
                                         [("siliconcompiler", "0.39.1")], store.actor,
                                         built_at=built)
        store.execute("UPDATE images SET resolved_at = ? WHERE id = ?",
                      (f"{pinned}T00:00:00.000Z", image_id))

    plan = images.plan_for_job(store, py(), {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/b@")


def test_preference_wins_over_recency_and_the_build_time(store):
    '''🔴 Newest-wins is tempting and wrong: a rebuilt image is newer and is
    not necessarily preferred. The build time breaks ties, never the operator.'''
    sc(store)
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor, preference=10)
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor, preference=1)

    images.register_image(store, "ghcr.io/x/old:1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor,
                          built_at="2020-01-01T00:00:00.000Z")
    images.register_image(store, "ghcr.io/x/new:1", digest("b"),
                          [("siliconcompiler", "0.40.0")], store.actor,
                          built_at="2026-09-01T00:00:00.000Z")

    plan = images.plan_for_job(store, py(), {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/old@")


###########################
# The interpreter a node running the user's Python needs (surface D293)
###########################

@pytest.fixture
def pythons(store):
    '''Two tool images that differ in their own Python, and nothing else.'''
    sc(store, "0.39.1")
    images.register_software(store, "icarus", "Icarus", store.actor, "tool")
    images.register_version(store, "icarus", "12.0", store.actor)
    images.register_software(store, "python", "Python", store.actor, "interpreter")
    images.register_version(store, "python", "3.11.9", store.actor)
    images.register_version(store, "python", "3.12.4", store.actor)

    for name, digit, version in (("sim-311", "d", "3.11.9"), ("sim-312", "e", "3.12.4")):
        images.register_image(store, f"ghcr.io/x/{name}:1", digest(digit),
                              [("siliconcompiler", "0.39.1"), ("icarus", "12.0"),
                               ("python", version)], store.actor)
    return store


def interpreted(version):
    requires = py()
    requires["interpreter"] = {"python": [version]}
    return requires


def test_a_node_running_the_users_python_lands_where_its_python_is(pythons, store):
    '''`resolved_versions.interpreter` is the Python of the images such a node
    ran in, and absent where none did.'''
    plan = images.plan_for_job(store, interpreted("==3.12.*"),
                               {("sim", "0"): "icarus", ("lint", "0"): "icarus"},
                               python_nodes=[("sim", "0")])
    ran = plan.nodes[("sim", "0")]

    assert plan.refs[ran].startswith("ghcr.io/x/sim-312@")
    assert images.contents_of(store, [ran], [ran])["interpreter"] == {"python": ["3.12.4"]}
    assert "interpreter" not in images.contents_of(store, [ran])


def test_only_the_users_python_nodes_are_held_to_the_interpreter(pythons, store):
    '''A Python no image has is refused naming what there is -- but only for
    a node running the user's Python; any other is placed as usual.'''
    body = refused(store, interpreted("==3.10.*"), {("sim", "0"): "icarus"},
                   python_nodes=[("sim", "0")]).body()

    assert body["type"].endswith("/software-unavailable")
    entry, = [e for e in body["unresolved"] if e["kind"] == "interpreter"]
    assert (entry["name"], entry["requirement"], sorted(entry["available"])) == \
        ("python", ["==3.10.*"], ["3.11.9", "3.12.4"])

    plan = images.plan_for_job(store, interpreted("==3.10.*"), {("lint", "0"): "icarus"},
                               python_nodes=[])
    assert plan.nodes[("lint", "0")]
