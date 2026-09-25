import pytest

from siliconcompiler.remote.server import images
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.store import Store


# The registry, on its own. Nothing here needs Flask, a port or a job: the
# resolution is a pure function of what an operator registered, which is what
# makes it testable at all -- the submit path that calls it needs an archive,
# a scheduler and a manifest before it can ask a single question.


def digest(letter):
    return "sha256:" + letter * 64


def py(name=None, wanted=None, tools=None):
    '''A bucketed `requires`, which is what the resolution reads.

    🔴 Two buckets because they are satisfied differently: the whole python set
    has to be held by ONE image, and a tool is satisfied per node.
    '''
    return {"python": {name: wanted} if name else {}, "tools": tools or {}}


@pytest.fixture
def store():
    with Store("server.db") as db:
        user = db.upsert_user("operator", "someone@host")
        db.actor = user["id"]
        yield db


@pytest.fixture
def registry(store):
    '''Two images: a small one with the framework, a big one with a tool.

    The pair the whole design exists for -- an import node has no business
    pulling the one OpenROAD is in.
    '''
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


###########################
# Naming what runs
###########################

@pytest.mark.parametrize("ref,expected", [
    ("ghcr.io/org/sc:0.39.1", "ghcr.io/org/sc"),
    ("ghcr.io/org/sc", "ghcr.io/org/sc"),
    # A colon before the last slash is a registry port and not a tag.
    ("localhost:5000/sc", "localhost:5000/sc"),
    ("localhost:5000/sc:v2", "localhost:5000/sc"),
])
def test_the_tag_comes_off_and_the_port_does_not(ref, expected):
    assert images.pinned_ref(ref, digest("c")) == f"{expected}@{digest('c')}"


def test_an_image_is_registered_by_digest_and_not_by_tag(registry, store):
    '''🔴 Rebuilding a tag must not change what a job runs.

    Which is only true if the digest is the string that reaches the node.
    '''
    plan = images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                               {("import", "0"): None})

    assert plan.ref(plan.job) == f"ghcr.io/x/sc-python@{digest('a')}"


def test_a_digest_that_is_not_one_is_refused(store):
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor)

    with pytest.raises(ValueError):
        images.register_image(store, "ghcr.io/x/y:1", "latest",
                              [("siliconcompiler", "0.39.1")], store.actor)


def test_an_image_declaring_a_version_nobody_registered(store):
    '''The FK would catch it; this catches it with a sentence.'''
    with pytest.raises(ValueError, match="not a registered version"):
        images.register_image(store, "ghcr.io/x/y:1", digest("a"),
                              [("siliconcompiler", "0.39.1")], store.actor)


def test_registering_the_same_digest_again_is_the_same_image(registry, store):
    '''The digest is the identity, so a new tag over the same bytes is an
    update and not a second row claiming to be the same thing.'''
    first = store.one("SELECT id FROM images WHERE digest = ?", (digest("a"),))["id"]

    again = images.register_image(store, "ghcr.io/x/sc-python:latest", digest("a"),
                                  [("siliconcompiler", "0.39.1")], store.actor)

    assert again == first
    assert len(images.live_images(store)) == 2


###########################
# The resolution
###########################

def test_the_smallest_image_that_fits_wins(registry, store):
    '''🔴 The payoff of resolving per node: an import node pulling a twelve
    gigabyte OpenROAD image to run thirty seconds of Python is what one image
    per job costs.'''
    plan = images.plan_for_job(
        store, py("siliconcompiler", "0.39.1"),
        {("import", "0"): None, ("place", "0"): "openroad"})

    assert plan.ref(plan.nodes[("import", "0")]).startswith("ghcr.io/x/sc-python@")
    assert plan.ref(plan.nodes[("place", "0")]).startswith("ghcr.io/x/sc-tools@")


def test_a_tool_nobody_registered_is_refused_when_it_needs_a_program(
        registry, store):
    '''🔴 **This reverses the earlier rule, and a live failure is why.** It
    used to be that only a REGISTERED name raised a requirement -- a deployment
    curating images for the framework was not claiming to have Verilator and
    was not refused for lacking one. That holds where jobs run on the host,
    which may well have it.

    ⚠️ Once `containers` is on the registry IS the world. A Bluespec design
    submitted to a deployment that had never heard of `bsc` was accepted, its
    `convert` node placed in the PYTHON-ONLY image because nothing raised a
    requirement, dispatched, and died on the first node with every other node
    cancelled behind it.'''
    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                            {("lint", "0"): "verilator"})

    assert raised.value.error.slug == "unsatisfiable-request"
    assert raised.value.members["resource"] == "verilator"
    assert "nowhere for it to run" in raised.value.detail


def test_a_node_that_declares_nothing_gets_the_jobs_own_image(registry, store):
    '''A builtin join runs in SiliconCompiler's own process, so the small
    image is exactly right for it.'''
    plan = images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                               {("join", "0"): None})

    assert plan.nodes[("join", "0")] == plan.job


def test_a_node_that_follows_its_input_runs_where_that_input_ran(registry,
                                                                 store):
    '''🆕 The execute tasks assemble a command out of the manifest, so there
    is nothing to require an image for -- and the environment that produced
    the inputs is the one most likely to be able to run it.'''
    plan = images.plan_for_job(
        store, py("siliconcompiler", "0.39.1"),
        {("place", "0"): "openroad", ("after", "0"): None},
        inherits={("after", "0"): ("place", "0")})

    assert plan.nodes[("after", "0")] == plan.nodes[("place", "0")]
    assert plan.nodes[("after", "0")] != plan.job


def test_a_follower_whose_input_is_not_in_this_run_takes_the_jobs_image(
        registry, store):
    '''Falls back rather than failing: that is what a node needing nothing
    gets anyway.'''
    plan = images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                               {("after", "0"): None},
                               inherits={("after", "0"): None})

    assert plan.nodes[("after", "0")] == plan.job


def test_a_registered_tool_with_no_image_fails_the_whole_submit(registry, store):
    images.register_software(store, "yosys", "Yosys", store.actor, "tool")
    images.register_version(store, "yosys", "0.44", store.actor)

    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                            {("syn", "0"): "yosys"})

    assert raised.value.error.slug == "unsatisfiable-request"
    assert raised.value.members["resource_kind"] == "tool"
    assert raised.value.members["resource"] == "yosys"


def test_a_framework_version_no_image_holds(registry, store):
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor)

    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py("siliconcompiler", "0.40.0"),
                            {("import", "0"): None})

    assert raised.value.members["resource_kind"] == "library"
    assert raised.value.members["resource"] == "siliconcompiler==0.40.0"


def test_preference_breaks_the_tie_and_not_recency(store):
    '''⚠️ Newest-wins is the tempting default and it is wrong: a rebuilt image
    is newer and is not necessarily preferred.'''
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor, preference=10)
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor, preference=1)

    images.register_image(store, "ghcr.io/x/old:0.39.1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor)
    # Registered second, so it is the newer row.
    images.register_image(store, "ghcr.io/x/new:0.40.0", digest("b"),
                          [("siliconcompiler", "0.40.0")], store.actor)

    plan = images.plan_for_job(store, py(), {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/old@")


def test_a_client_that_names_no_version_gets_the_preferred_one(registry, store):
    plan = images.plan_for_job(store, py(), {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/sc-python@")


def test_a_version_this_deployment_does_not_track_is_not_a_requirement(registry, store):
    '''`version-skew` at create is where an unknown version is answered, if it
    is answered at all. It must not become an unsatisfiable image here.'''
    plan = images.plan_for_job(store, py("za-sclib", "0.1.80"),
                               {("import", "0"): None})

    assert plan.job is not None


def test_an_empty_registry_is_a_refusal_and_not_a_bypass(store):
    '''⚠️ This is only reached where the deployment runs containers, so an
    empty registry is a misconfiguration. The bare-Slurm deployment -- which is
    conforming, and leaves both image_id columns NULL -- never calls this at
    all; see test_server_jobs.'''
    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                            {("import", "0"): None, ("place", "0"): "openroad"})

    assert raised.value.error.slug == "unsatisfiable-request"


def test_retiring_the_last_image_does_not_quietly_run_on_the_host(registry, store):
    for image in images.live_images(store):
        images.retire_image(store, image["id"], store.actor)

    with pytest.raises(ProblemError):
        images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                            {("import", "0"): None})


def test_a_retired_image_keeps_its_row(registry, store):
    '''⚠️ Images are never deleted: a job from last year names one, and *what
    did this run in* has to stay answerable.'''
    image = images.live_images(store)[0]
    images.retire_image(store, image["id"], store.actor)

    assert store.one("SELECT retired_by FROM images WHERE id = ?",
                     (image["id"],))["retired_by"] == store.actor


def test_a_retired_version_stops_satisfying(registry, store):
    images.retire_version(store, "openroad", "2.0", store.actor)

    with pytest.raises(ProblemError):
        images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                            {("place", "0"): "openroad"})


###########################
# What GET /v1 says about it
###########################

def test_a_version_is_advertised_only_where_an_image_holds_it(registry, store):
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor)

    assert store.advertised_software(containers=True) == {
        "python": {"siliconcompiler": ["0.39.1"]},
        "tools": {"openroad": ["2.0"]}}


def test_without_containers_the_join_is_the_wrong_answer(registry, store):
    '''⚠️ A deployment that runs no containers has no images by definition, so
    joining to them would advertise nothing while the versions it genuinely
    runs sit in the table.'''
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor)

    assert store.advertised_software(containers=False)["python"] == \
        {"siliconcompiler": ["0.39.1", "0.40.0"]}


def test_retiring_the_software_retracts_the_claim(registry, store):
    '''The other half of the distinction above: retiring a version says *not
    this one*, retiring the software says *not any more*.

    ⚠️ And *not any more* now means a node needing it is refused rather than
    quietly placed in the job's own image -- which is the same correction:
    where every node runs in a container, a tool no image holds has nowhere to
    run whether it was once registered or never was.'''
    images.retire_version(store, "openroad", "2.0", store.actor)
    images.retire_software(store, "openroad", store.actor)

    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                            {("place", "0"): "openroad"})

    assert raised.value.members["resource"] == "openroad"


###########################
# What the compute node does with it
###########################

def test_a_cluster_is_placed_by_slurm_and_never_by_docker(nop_project):
    """🔴 `option,scheduler,name` holds ONE value, so a node handed to the
    docker scheduler is a node Slurm never sees -- and on a cluster Slurm is
    what should be placing the work.

    ⚠️ `queue` must stay untouched there too: for Slurm it is the PARTITION and
    goes straight to `srun --partition`, so an image reference in it would
    submit every node to a partition named after a container.
    """
    from siliconcompiler.remote.server import runspec

    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): "/sc_server/images/659b"},
                      cluster="slurm")

    scheduler = nop_project.option.scheduler
    assert scheduler.get_name(step="stepone", index="0") == "slurm"
    assert scheduler.get_queue(step="stepone", index="0") is None

    options = scheduler.get_options(step="stepone", index="0")
    assert "--container" in options
    assert options[options.index("--container") + 1] == "/sc_server/images/659b"
    # 🔴 A job of its own and never a step in the orchestrator's allocation.
    # `--partition` on a step is accepted and then silently ignored, so a node
    # sharing that allocation would quietly run on the one core the
    # orchestrator was given.
    assert "--overlap" not in options


def test_a_server_with_no_cluster_uses_the_docker_scheduler(nop_project):
    """There is no Slurm to place anything, and a digest is what the docker
    scheduler reads out of `queue`."""
    from siliconcompiler.remote.server import runspec

    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): f"ghcr.io/x/sc@{digest('a')}"},
                      cluster="local")

    scheduler = nop_project.option.scheduler
    assert scheduler.get_name(step="stepone", index="0") == "docker"
    assert scheduler.get_queue(step="stepone", index="0") == \
        f"ghcr.io/x/sc@{digest('a')}"


def test_the_manifest_carries_the_placement_to_the_compute_node(nop_project):
    """The runner holds no database connection and should not need one: the
    server writes the answer into the same file the run loads."""
    from siliconcompiler.remote.server import runspec

    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): f"ghcr.io/x/sc@{digest('a')}"})

    assert runspec.node_image(nop_project, "stepone", "0") == \
        ("image", f"ghcr.io/x/sc@{digest('a')}")
    assert runspec.node_image(nop_project, "steptwo", "0") is None


def test_the_runner_leaves_its_own_allocation(monkeypatch):
    """🔴 Slurm decides between a STEP and a JOB by whether SLURM_JOB_ID is set.

    Measured on the rig: `srun --partition=sc` inside an allocation returned
    `job=5 step=1` -- the same allocation, the partition silently ignored --
    and the identical call with SLURM_JOB_ID cleared returned `job=6 step=0`.
    """
    import os

    from siliconcompiler.remote.server import runner

    monkeypatch.setenv("SLURM_JOB_ID", "5")
    monkeypatch.setenv("SLURM_STEP_ID", "1")

    runner._leave_the_allocation()

    assert "SLURM_JOB_ID" not in os.environ
    assert "SLURM_STEP_ID" not in os.environ


def test_a_slurm_placement_reads_back_as_a_bundle(nop_project):
    from siliconcompiler.remote.server import runspec

    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): "/sc_server/images/659b"},
                      cluster="slurm")

    assert runspec.node_image(nop_project, "stepone", "0") == \
        ("container", "/sc_server/images/659b")


def test_a_node_waiting_for_its_image_is_preparing(monkeypatch, nop_project):
    """🔴 What `preparing` is for. A tool image is gigabytes and takes minutes
    on a cold host; without a state for it the wait is indistinguishable from a
    hang, and a node sitting at `pending` while nothing happens is the report
    somebody opens a ticket about."""
    from siliconcompiler.remote.server import runner, runspec

    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): f"ghcr.io/x/sc@{digest('a')}",
                              ("steptwo", "0"): f"ghcr.io/x/sc@{digest('a')}"})

    seen = []
    monkeypatch.setattr(runner, "_placement_present", lambda placement: False)
    monkeypatch.setattr(
        runner, "_make_placement",
        lambda placement: seen.append(
            {key: node["state"] for key, node in runner._progress["nodes"].items()}))

    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "pending"},
                                  "steptwo/0": {"state": "pending"}}}
    runner._fetch_images(nop_project)

    # Both nodes were visibly waiting while the fetch was happening...
    assert seen == [{"stepone/0": "preparing", "steptwo/0": "preparing"}]
    # ...and neither was left there afterwards.
    assert {key: node["state"] for key, node in runner._progress["nodes"].items()} == \
        {"stepone/0": "queued", "steptwo/0": "queued"}


def test_an_image_already_on_the_host_is_never_preparing(monkeypatch, nop_project):
    """There was nothing to wait for, so saying so would be noise."""
    from siliconcompiler.remote.server import runner, runspec

    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): f"ghcr.io/x/sc@{digest('a')}"})

    monkeypatch.setattr(runner, "_placement_present", lambda placement: True)
    monkeypatch.setattr(runner, "_make_placement",
                        lambda placement: pytest.fail("fetched"))

    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "pending"}}}
    runner._fetch_images(nop_project)

    assert runner._progress["nodes"]["stepone/0"]["state"] == "pending"


def test_a_half_written_bundle_counts_as_absent(monkeypatch):
    """An OCI bundle is a directory, so its existence says nothing. The config
    is what a complete one has, and the unpack renames it into place last."""
    import os

    from siliconcompiler.remote.server import runner

    os.makedirs("bundle", exist_ok=True)
    assert runner._placement_present(("container", "bundle")) is False

    with open("bundle/config.json", "w") as f:
        f.write("{}")
    assert runner._placement_present(("container", "bundle")) is True


def test_a_fetch_that_fails_does_not_end_the_run(monkeypatch, nop_project):
    """⚠️ The node's own launch tries again and fails with the message that
    knows about registry credentials, and a failed node is already something
    this reports. Ending the run from here would replace that with worse."""
    from siliconcompiler.remote.server import runner, runspec

    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): f"ghcr.io/x/sc@{digest('a')}"})

    monkeypatch.setattr(runner, "_placement_present", lambda placement: False)
    monkeypatch.setattr(
        runner, "_make_placement",
        lambda placement: (_ for _ in ()).throw(RuntimeError("no such host")))

    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "pending"}}}
    runner._fetch_images(nop_project)

    assert runner._progress["nodes"]["stepone/0"]["state"] == "queued"


def test_a_bundle_with_no_recorded_source_says_so(nop_project):
    """The bundle path names a digest and nothing in it says which registry to
    unpack from, which is the whole reason the sources file exists."""
    from siliconcompiler.remote.server import runner

    runner._image_sources = {}

    with pytest.raises(RuntimeError, match="nothing recorded to unpack"):
        runner._unpack_bundle("/sc_server/images/659b")


def test_a_run_with_no_placement_fetches_nothing(monkeypatch, nop_project):
    """Every deployment that runs no containers, which is the default one."""
    from siliconcompiler.remote.server import runner, runspec

    runspec.normalize(nop_project, "job-id", "build", "cache")

    monkeypatch.setattr(runner, "_placement_present",
                        lambda placement: pytest.fail("looked for an image"))

    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "pending"}}}
    runner._fetch_images(nop_project)

    assert runner._progress["nodes"]["stepone/0"]["state"] == "pending"


def test_a_node_the_flow_skipped_never_waits_for_an_image(monkeypatch, nop_project):
    """`_settle` runs first, so a node the flow has already written off is
    terminal here -- and walking it back to `preparing` would be a state going
    backwards on a client that renders them."""
    from siliconcompiler.remote.server import runner, runspec

    runspec.normalize(nop_project, "job-id", "build", "cache",
                      images={("stepone", "0"): f"ghcr.io/x/sc@{digest('a')}"})

    monkeypatch.setattr(runner, "_placement_present", lambda placement: False)
    monkeypatch.setattr(runner, "_make_placement",
                        lambda placement: pytest.fail("fetched"))

    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "skipped"}}}
    runner._fetch_images(nop_project)

    assert runner._progress["nodes"]["stepone/0"]["state"] == "skipped"


def test_a_cluster_schedules_every_node_image_or_not(nop_project):
    '''🔴 The cluster is what should be scheduling the work.

    Inside one allocation a flow can never use more than the machine it landed
    on, so scaling the cluster would do nothing for a single run -- and the
    orchestrator could not be given a partition of its own, because the work
    would follow it there.
    '''
    from siliconcompiler.remote.server import runspec

    runspec.normalize(nop_project, "job-id", "build", "cache", cluster="slurm")

    scheduler = nop_project.option.scheduler
    for step in ("stepone", "steptwo"):
        assert scheduler.get_name(step=step, index="0") == "slurm"
        assert not scheduler.get_options(step=step, index="0")


def test_a_server_with_no_cluster_schedules_nothing_per_node(nop_project):
    '''There is no Slurm, so a node with no image is left exactly as the
    caller sent it.'''
    from siliconcompiler.remote.server import runspec

    runspec.normalize(nop_project, "job-id", "build", "cache", cluster="local")

    assert nop_project.option.scheduler.get_name(step="stepone", index="0") is None


def test_rebuilding_a_tag_supersedes_the_build_before_it(registry, store):
    '''🔴 One live image per reference.

    The digest identifies the bytes and the reference identifies the thing an
    operator curates. Two live rows for one reference are indistinguishable to
    the resolution -- same declared contents, same name -- so it would pick
    between them arbitrarily, and a rebuild would appear to have no effect
    while the old bytes went on running. Which is exactly what happened on the
    rig: a rebuilt runtime image was registered, and jobs kept starting in the
    previous one.
    '''
    before = next(image for image in images.live_images(store)
                  if image["registry_ref"] == "ghcr.io/x/sc-python:0.39.1")

    images.register_image(store, "ghcr.io/x/sc-python:0.39.1", digest("e"),
                          [("siliconcompiler", "0.39.1")], store.actor)

    live = [image for image in images.live_images(store)
            if image["registry_ref"] == "ghcr.io/x/sc-python:0.39.1"]

    assert [image["digest"] for image in live] == [digest("e")]

    # ⚠️ Superseded and not deleted: a job from last year names that row, and
    # *what did this run in* has to stay answerable.
    assert store.one("SELECT retired_at FROM images WHERE id = ?",
                     (before["id"],))["retired_at"]


def test_the_same_digest_again_supersedes_nothing(registry, store):
    '''Re-registering identical bytes is an update to one row, so there is no
    earlier build to retire -- and retiring it would retire itself.'''
    images.register_image(store, "ghcr.io/x/sc-python:0.39.1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor)

    live = [image for image in images.live_images(store)
            if image["registry_ref"] == "ghcr.io/x/sc-python:0.39.1"]

    assert [image["digest"] for image in live] == [digest("a")]


def test_what_a_node_needs_is_declared_and_never_inferred(registry, store):
    '''🔴 Every rule that guesses gets a real task wrong.

    Inferring from the tool NAME says `builtin`, which is not a thing anybody
    installs -- seen on the rig, a four-node nop flow refused with
    `unsatisfiable-request, resource: builtin`. Inferring from `exe` says
    *nothing* for the slang tasks, which have no executable at all and drive
    pyslang in this process: an image without pyslang cannot run them, so
    "needs nothing" would place them anywhere.

    ⚠️ Read off a BARE task, so a forty-node flow costs forty attribute reads.
    '''
    from siliconcompiler.remote.server.runspec import node_tools

    declared = {"join": None, "compute": None, "place": "openroad",
                "elaborate": "slang"}

    class Flow:
        def get_task_module(self, step, index):
            class Task:
                def image_requirement(self_inner):
                    return declared[step]
            return Task

    assert node_tools(Flow(), [(step, "0") for step in declared]) == {
        ("join", "0"): None,
        ("compute", "0"): None,
        ("place", "0"): "openroad",
        ("elaborate", "0"): "slang",
    }


def test_the_real_tasks_declare_what_they_need():
    '''The three cases an inference rule gets wrong, from the drivers.'''
    from siliconcompiler.tools.builtin.nop import NOPTask
    from siliconcompiler.tools.execute.exec_input import ExecInputTask
    from siliconcompiler.tools.slang.elaborate import Elaborate

    assert NOPTask().image_requirement() is None
    assert NOPTask().inherits_image() is False

    # No executable, and still has to be placed somewhere holding it.
    assert Elaborate().image_requirement() == "slang"

    # 🆕 Nothing to require -- the command comes out of the manifest -- and it
    # follows its input rather than defaulting to the job's image.
    assert ExecInputTask().image_requirement() is None
    assert ExecInputTask().inherits_image() is True


###########################
# Version requirements, resolved here and not by the client
###########################

def test_a_range_on_the_wire_resolves_to_an_image(registry, store):
    '''🔴 The whole reason the server resolves: `GET /v1`'s `software` map is
    flat per name while the image join is over combinations, so a client
    resolving each requirement on its own can name a set no single image holds
    -- every version published, every one satisfiable, and nothing to run
    them in.'''
    plan = images.plan_for_job(store, py("siliconcompiler", ">=0.39,<0.40"),
                               {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/sc-python@")


def test_a_range_nothing_satisfies_is_refused_before_anything_runs(registry,
                                                                   store):
    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py("siliconcompiler", ">=0.40"),
                            {("import", "0"): None})

    assert raised.value.error.slug == "unsatisfiable-request"
    assert raised.value.members["resource"] == "siliconcompiler>=0.40"


def test_a_bare_version_still_means_exactly_that(registry, store):
    '''⚠️ It is what every client sent before the wire carried ranges, and it
    is what a person writes.'''
    assert images.specifiers("0.39.1") == ("==0.39.1",)
    assert images.specifiers(">=0.39") == (">=0.39",)
    assert images.specifiers("") == ()
    assert images.specifiers(None) == ()
    # A list is alternatives, which is what SiliconCompiler already means by a
    # version requirement -- and an empty entry in it is not a requirement.
    assert images.specifiers([">=0.39", "2.0"]) == (">=0.39", "==2.0")
    assert images.specifiers([""]) == ()

    plan = images.plan_for_job(store, py("siliconcompiler", "0.39.1"),
                               {("import", "0"): None})
    assert plan.job


def test_a_version_is_normalised_when_it_is_registered(store):
    '''🔴 At registration and not at request time: it keeps per-tool version
    handling off the request path, and it removes a skew that would otherwise
    be silent -- a client and a server on different releases normalising the
    same string differently would disagree about whether an image matched, and
    neither would say so.'''
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")

    assert images.register_version(store, "siliconcompiler", "v0.39.1",
                                   store.actor) == "0.39.1"
    assert images.live_software(store)["python"]["siliconcompiler"] == ["0.39.1"]


def test_a_reported_version_that_is_not_pep_440_is_refused(store):
    '''🔴 `version_norm` is NOT NULL in the contract: a value with no PEP 440
    form has nothing to put there, so the row cannot be written. Refused, not
    coerced -- `initialize` is what gtkwave's parser took out of `Could not
    initialize GTK!`.'''
    images.register_software(store, "gtkwave", "GTKWave", store.actor, "tool")

    with pytest.raises(ValueError, match="not a PEP 440 version"):
        images.register_version(store, "gtkwave", "initialize", store.actor)
    assert store.one("SELECT version FROM software_versions "
                     "WHERE software_name = 'gtkwave'") is None


def test_the_same_value_is_accepted_as_published_date(store):
    '''The fallback that works: stored exactly as given, and it can never
    satisfy a range.'''
    images.register_software(store, "gtkwave", "GTKWave", store.actor, "tool")

    assert images.register_version(store, "gtkwave", "20260924", store.actor,
                                   source="published_date") == "20260924"


###########################
# reported vs published_date
###########################

@pytest.fixture
def unversioned(store):
    '''A tool that reports nothing, recorded from its image's publish date.'''
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor)
    images.register_software(store, "magic", "Magic", store.actor, "tool")
    images.register_version(store, "magic", "20260924", store.actor,
                            source="published_date")

    images.register_image(store, "ghcr.io/x/sc-magic:1", digest("c"),
                          [("siliconcompiler", "0.39.1"), ("magic", "20260924")],
                          store.actor)
    return store


def test_an_unversioned_tool_still_runs_when_no_version_is_asked_for(
        unversioned, store):
    '''A complete tool list beats a partial one. The mark costs it version
    matching, not existence.'''
    plan = images.plan_for_job(store, py(), {("drc", "0"): "magic"})

    assert plan.nodes[("drc", "0")]


def test_a_published_date_can_never_satisfy_a_requirement(unversioned, store):
    '''🔴 This is the whole reason for the mark. `20260924` beats `2.0.1` under
    any comparison there is, so an unversioned build from years ago would
    outrank a current release for ever.'''
    assert not images.matches("20260924", "published_date", ">=2.0")
    assert not images.matches("20260924", "published_date", "==20260924")
    assert images.matches("20260924", "published_date", None)


def test_the_refusal_says_present_but_reports_no_version(unversioned, store):
    '''🔴 Not *no image matches*. That sends somebody looking for a version of
    a tool that is already installed. `GET /v1`'s `software` has nowhere to
    carry the mark, so their own preflight said yes -- the refusal has to be
    the thing that explains it.'''
    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py(tools={"magic": ">=1.0"}), {("drc", "0"): "magic"})

    assert raised.value.error.slug == "unsatisfiable-request"
    assert "reports no version" in raised.value.detail
    assert "no image on this server holds" not in raised.value.detail


def test_reported_sorts_above_published_date_whatever_the_numbers_say(store):
    images.register_software(store, "magic", "Magic", store.actor, "tool")
    images.register_version(store, "magic", "20260924", store.actor,
                            source="published_date")
    images.register_version(store, "magic", "8.3.2", store.actor)

    assert images.live_software(store)["tools"]["magic"] == ["8.3.2", "20260924"]


###########################
# What the job ran in
###########################

def test_the_digests_a_descriptor_resolves_to_need_no_upload(registry, store):
    '''🔴 What lets create fold them into the job identity and skip the
    upload: resolution needs the declared versions and the registry, and
    nothing else.'''
    assert images.digests_for(store, py("siliconcompiler", ">=0.39,<0.40")) == \
        [digest("a")]


def test_a_descriptor_nothing_can_run_is_refused_at_create(registry, store):
    with pytest.raises(ProblemError):
        images.digests_for(store, py("siliconcompiler", "==9.9.9"))


def test_what_a_job_ran_is_the_union_of_its_images(registry, store):
    '''⚠️ A list per name, because a wide flow resolves several images and
    where the client pinned nothing they can hold different versions of the
    same distribution. One value would have to pick and be wrong.'''
    plan = images.plan_for_job(store, py(), {("import", "0"): None,
                                             ("place", "0"): "openroad"})

    held = images.contents_of(store, [plan.job, *plan.nodes.values()])

    assert held == {"openroad": ["2.0"], "siliconcompiler": ["0.39.1"]}
    assert images.contents_of(store, [None, None]) == {}


###########################
# Two buckets, because they are satisfied differently
###########################

def test_the_python_set_must_be_held_by_one_image(store):
    '''🔴 They share an interpreter. Spreading `siliconcompiler` and a site
    library over two containers is not a deployment, it is a broken one.'''
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor)
    images.register_software(store, "za-sclib", "ZA", store.actor, "python")
    images.register_version(store, "za-sclib", "0.1.80", store.actor)

    # One image each, and neither holds both.
    images.register_image(store, "ghcr.io/x/sc:1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor)
    images.register_image(store, "ghcr.io/x/lib:1", digest("b"),
                          [("za-sclib", "0.1.80")], store.actor)

    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(
            store,
            {"python": {"siliconcompiler": "0.39.1", "za-sclib": "0.1.80"},
             "tools": {}},
            {("import", "0"): None})

    assert raised.value.error.slug == "unsatisfiable-request"

    # And one that holds both resolves.
    images.register_image(store, "ghcr.io/x/both:1", digest("c"),
                          [("siliconcompiler", "0.39.1"), ("za-sclib", "0.1.80")],
                          store.actor)
    plan = images.plan_for_job(
        store,
        {"python": {"siliconcompiler": "0.39.1", "za-sclib": "0.1.80"},
         "tools": {}},
        {("import", "0"): None})
    assert plan.ref(plan.job).startswith("ghcr.io/x/both@")


def test_a_tool_requirement_is_satisfied_per_node(registry, store):
    '''⚠️ And each node's image carries the python set PLUS its own tool,
    which is exactly what the two image_id columns have always meant.'''
    plan = images.plan_for_job(store, py(tools={"openroad": ">=2.0"}),
                               {("import", "0"): None, ("place", "0"): "openroad"})

    assert plan.nodes[("import", "0")] != plan.nodes[("place", "0")]
    assert plan.ref(plan.nodes[("import", "0")]).startswith("ghcr.io/x/sc-python@")
    assert plan.ref(plan.nodes[("place", "0")]).startswith("ghcr.io/x/sc-tools@")


def test_a_tool_range_nothing_holds_is_refused(registry, store):
    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py(tools={"openroad": ">=3.0"}),
                            {("place", "0"): "openroad"})

    assert raised.value.members["resource"] == "openroad>=3.0"


def test_the_buckets_are_a_closed_set_and_both_are_always_there(store):
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")

    assert set(images.live_software(store)) == {"python", "tools"}
    assert images.live_software(store)["tools"] == {}


def test_a_python_distribution_may_not_name_a_task_driver(store):
    '''A driver is what makes something a tool.'''
    with pytest.raises(ValueError, match="a driver is what makes"):
        images.register_software(store, "za-sclib", "ZA", store.actor, "python",
                                 driver="za_sclib.tools")


def test_a_driver_is_recorded_so_a_probe_can_be_handed_it(store):
    '''🔴 The process that resolves an image and the process inside it are not
    the same interpreter and do not have the same packages, so where the driver
    lives has to be data by the time the probe runs.'''
    images.register_software(store, "openroad", "OpenROAD", store.actor, "tool",
                             driver="siliconcompiler.tools.openroad")

    assert images.how_to_ask(store) == {
        "openroad": {"driver": "siliconcompiler.tools.openroad",
                     "version_package": None}}


###########################
# Two images, identical versions
###########################

def test_built_at_breaks_the_tie_preference_cannot(store):
    '''🔴 Same preference, same contents, same version: nothing is left to
    choose by, and before this the answer was whichever reference sorted
    first.'''
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor)

    images.register_image(store, "ghcr.io/x/a:1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor,
                          built_at="2026-01-01T00:00:00.000Z")
    images.register_image(store, "ghcr.io/x/b:1", digest("b"),
                          [("siliconcompiler", "0.39.1")], store.actor,
                          built_at="2026-09-01T00:00:00.000Z")

    plan = images.plan_for_job(store, py(), {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/b@")


def test_an_image_whose_manifest_said_nothing_sorts_last(store):
    '''⚠️ NULL means the manifest carried no build time, not *old*.'''
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor)

    images.register_image(store, "ghcr.io/x/a:1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor)
    images.register_image(store, "ghcr.io/x/b:1", digest("b"),
                          [("siliconcompiler", "0.39.1")], store.actor,
                          built_at="2020-01-01T00:00:00.000Z")

    plan = images.plan_for_job(store, py(), {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/b@")


def test_preference_still_wins_over_the_build_time(store):
    '''🔴 The order of the two levels: `built_at` breaks a tie, it does not
    overrule the operator. Newest-wins is the tempting default and it is wrong
    -- a rebuilt image is newer and is not necessarily preferred.'''
    images.register_software(store, "siliconcompiler", "SC", store.actor, "python")
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor,
                            preference=10)
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor,
                            preference=1)

    images.register_image(store, "ghcr.io/x/old:1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor,
                          built_at="2020-01-01T00:00:00.000Z")
    images.register_image(store, "ghcr.io/x/new:1", digest("b"),
                          [("siliconcompiler", "0.40.0")], store.actor,
                          built_at="2026-09-01T00:00:00.000Z")

    plan = images.plan_for_job(store, py(), {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/old@")


def test_an_image_may_name_the_version_the_tool_printed(store):
    '''🔴 `verilator 5.052` is stored as `5.52` -- PEP 440 strips the leading
    zero -- so naming what the tool actually said has to find the row that
    normalisation created, or the registry refuses a version it just
    registered.'''
    images.register_software(store, "verilator", "Verilator", store.actor, "tool")
    stored = images.register_version(store, "verilator", "5.052", store.actor)
    assert stored == "5.52"

    images.register_image(store, "ghcr.io/x/v:1", digest("a"),
                          [("verilator", "5.052")], store.actor)

    held = images.live_images(store)[0]["contents"]
    assert [(entry.name, entry.version) for entry in held] == [("verilator", "5.52")]


def test_a_requirement_is_a_list_of_alternatives(registry, store):
    '''🔴 Two tasks of the same tool can want different versions, and
    SiliconCompiler already says so with a list: `Task.get('version')` holds
    alternative specifier sets and `check_exe_version` accepts a match against
    any of them. Saying it once beats naming every node that wants it.'''
    plan = images.plan_for_job(
        store, py(tools={"openroad": [">=9.0", "==2.0"]}),
        {("place", "0"): "openroad"})

    assert plan.ref(plan.nodes[("place", "0")]).startswith("ghcr.io/x/sc-tools@")


def test_none_of_the_alternatives_holding_is_still_a_refusal(registry, store):
    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, py(tools={"openroad": [">=9.0", "==8.0"]}),
                            {("place", "0"): "openroad"})

    assert raised.value.error.slug == "unsatisfiable-request"
    assert raised.value.members["resource"] == "openroad>=9.0 or ==8.0"


def test_an_empty_list_is_any_version(registry, store):
    '''What a client that knows the tool and not the version sends, which is
    the ordinary case: a task's requirement is set in setup(), and setup
    happens in the image.'''
    plan = images.plan_for_job(store, py(tools={"openroad": []}),
                               {("place", "0"): "openroad"})

    assert plan.nodes[("place", "0")]


def test_a_python_requirement_may_be_a_list_too(registry, store):
    plan = images.plan_for_job(store, py("siliconcompiler", ["==9.9.9", "0.39.1"]),
                               {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/sc-python@")
