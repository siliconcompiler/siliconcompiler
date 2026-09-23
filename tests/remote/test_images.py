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
    images.register_software(store, "siliconcompiler", "SiliconCompiler", store.actor)
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor, preference=10)
    images.register_software(store, "openroad", "OpenROAD", store.actor)
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
    plan = images.plan_for_job(store, {"siliconcompiler": "0.39.1"},
                               {("import", "0"): None})

    assert plan.ref(plan.job) == f"ghcr.io/x/sc-python@{digest('a')}"


def test_a_digest_that_is_not_one_is_refused(store):
    images.register_software(store, "siliconcompiler", "SC", store.actor)
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
        store, {"siliconcompiler": "0.39.1"},
        {("import", "0"): None, ("place", "0"): "openroad"})

    assert plan.ref(plan.nodes[("import", "0")]).startswith("ghcr.io/x/sc-python@")
    assert plan.ref(plan.nodes[("place", "0")]).startswith("ghcr.io/x/sc-tools@")


def test_a_tool_nobody_registered_raises_no_requirement(registry, store):
    '''A deployment curating images for the framework and saying nothing about
    Verilator is not claiming to have a Verilator image, and is not refused for
    lacking one. Registering the name is how an operator takes that claim on.'''
    plan = images.plan_for_job(store, {"siliconcompiler": "0.39.1"},
                               {("lint", "0"): "verilator"})

    assert plan.nodes[("lint", "0")] == plan.job


def test_a_registered_tool_with_no_image_fails_the_whole_submit(registry, store):
    images.register_software(store, "yosys", "Yosys", store.actor)
    images.register_version(store, "yosys", "0.44", store.actor)

    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, {"siliconcompiler": "0.39.1"},
                            {("syn", "0"): "yosys"})

    assert raised.value.error.slug == "unsatisfiable-request"
    assert raised.value.members["resource_kind"] == "tool"
    assert raised.value.members["resource"] == "yosys"


def test_a_framework_version_no_image_holds(registry, store):
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor)

    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, {"siliconcompiler": "0.40.0"},
                            {("import", "0"): None})

    assert raised.value.members["resource_kind"] == "library"
    assert raised.value.members["resource"] == "siliconcompiler==0.40.0"


def test_preference_breaks_the_tie_and_not_recency(store):
    '''⚠️ Newest-wins is the tempting default and it is wrong: a rebuilt image
    is newer and is not necessarily preferred.'''
    images.register_software(store, "siliconcompiler", "SC", store.actor)
    images.register_version(store, "siliconcompiler", "0.39.1", store.actor, preference=10)
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor, preference=1)

    images.register_image(store, "ghcr.io/x/old:0.39.1", digest("a"),
                          [("siliconcompiler", "0.39.1")], store.actor)
    # Registered second, so it is the newer row.
    images.register_image(store, "ghcr.io/x/new:0.40.0", digest("b"),
                          [("siliconcompiler", "0.40.0")], store.actor)

    plan = images.plan_for_job(store, {}, {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/old@")


def test_a_client_that_names_no_version_gets_the_preferred_one(registry, store):
    plan = images.plan_for_job(store, {}, {("import", "0"): None})

    assert plan.ref(plan.job).startswith("ghcr.io/x/sc-python@")


def test_a_version_this_deployment_does_not_track_is_not_a_requirement(registry, store):
    '''`version-skew` at create is where an unknown version is answered, if it
    is answered at all. It must not become an unsatisfiable image here.'''
    plan = images.plan_for_job(store, {"za-sclib": "0.1.80"},
                               {("import", "0"): None})

    assert plan.job is not None


def test_an_empty_registry_is_a_refusal_and_not_a_bypass(store):
    '''⚠️ This is only reached where the deployment runs containers, so an
    empty registry is a misconfiguration. The bare-Slurm deployment -- which is
    conforming, and leaves both image_id columns NULL -- never calls this at
    all; see test_server_jobs.'''
    with pytest.raises(ProblemError) as raised:
        images.plan_for_job(store, {"siliconcompiler": "0.39.1"},
                            {("import", "0"): None, ("place", "0"): "openroad"})

    assert raised.value.error.slug == "unsatisfiable-request"


def test_retiring_the_last_image_does_not_quietly_run_on_the_host(registry, store):
    for image in images.live_images(store):
        images.retire_image(store, image["id"], store.actor)

    with pytest.raises(ProblemError):
        images.plan_for_job(store, {"siliconcompiler": "0.39.1"},
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
        images.plan_for_job(store, {"siliconcompiler": "0.39.1"},
                            {("place", "0"): "openroad"})


###########################
# What GET /v1 says about it
###########################

def test_a_version_is_advertised_only_where_an_image_holds_it(registry, store):
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor)

    assert store.advertised_software(containers=True) == {
        "siliconcompiler": ["0.39.1"], "openroad": ["2.0"]}


def test_without_containers_the_join_is_the_wrong_answer(registry, store):
    '''⚠️ A deployment that runs no containers has no images by definition, so
    joining to them would advertise nothing while the versions it genuinely
    runs sit in the table.'''
    images.register_version(store, "siliconcompiler", "0.40.0", store.actor)

    assert store.advertised_software(containers=False)["siliconcompiler"] == \
        ["0.39.1", "0.40.0"]


def test_retiring_the_software_retracts_the_claim(registry, store):
    '''The other half of the distinction above: retiring a version says *not
    this one*, retiring the software says *not any more*.'''
    images.retire_version(store, "openroad", "2.0", store.actor)
    images.retire_software(store, "openroad", store.actor)

    plan = images.plan_for_job(store, {"siliconcompiler": "0.39.1"},
                               {("place", "0"): "openroad"})

    assert plan.nodes[("place", "0")] == plan.job


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
