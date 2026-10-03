import ast
import gzip
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import tarfile
import tempfile

from pathlib import Path

import pytest

from siliconcompiler.remote import environment
from siliconcompiler.remote.server.packages import envbuild, pipbuild
from siliconcompiler.remote.server.software import images, oci

from test_environment import make_wheel, simple_index


# A job's Python packages built into an image while it stages (§L, container
# mode). No container, index or registry is reached: each is faked at its edge.


def digest(letter):
    return "sha256:" + letter * 64


@pytest.mark.parametrize("ref,parts", [
    ("registry:5000/sc-runtime@sha256:" + "a" * 64,
     ("registry:5000", "sc-runtime", "sha256:" + "a" * 64)),
    ("registry:5000/sc-runtime:v1", ("registry:5000", "sc-runtime", "v1")),
    ("ghcr.io/org/sc:v1@sha256:" + "b" * 64, ("ghcr.io", "org/sc", "sha256:" + "b" * 64)),
    ("registry:5000/a/b/c:tag", ("registry:5000", "a/b/c", "tag")),
    ("registry:5000/sc-runtime", None),                 # nothing to pull
])
def test_a_reference_splits_as_docker_reads_it(ref, parts):
    if parts is None:
        with pytest.raises(ValueError, match="host/repository@digest"):
            oci.split_ref(ref)
    else:
        assert oci.split_ref(ref) == parts


@pytest.mark.parametrize("conf,scheme", [
    ('[[registry]]\nlocation = "reg:5000"\ninsecure = true\n', "http"),
    ("[[registry]]\nlocation = 'reg:5000'\ninsecure = true\n", "http"),
    ('[[registry]]\nlocation = "reg:5000"\n# insecure = true\n', "https"),
    ('[[registry]]\nlocation = "reg:5000"\n[[registry.mirror]]\n'
     'location = "mirror:5000"\ninsecure = true\n', "https"),
    ('[[registry]]\nlocation = "other:5000"\ninsecure = true\n', "https"),
    ("not toml at all [[[", "https"),
], ids=["insecure", "single-quoted", "commented-out", "mirror-only", "other-host", "unreadable"])
def test_a_registry_is_plain_http_only_where_registries_conf_says_so(tmp_path, conf, scheme,
                                                                     monkeypatch):
    '''Read as TOML, as skopeo reads it: a commented-out `insecure`, or a
    mirror's own, never sends a push over plain http.'''
    monkeypatch.delenv("CONTAINERS_REGISTRIES_CONF", raising=False)
    (tmp_path / "registries.conf").write_text(conf)

    assert oci._scheme("reg:5000", confs=[str(tmp_path / "registries.conf")]) == scheme


def test_a_layer_puts_the_tree_where_it_is_asked_and_is_reproducible(tmp_path):
    site = tmp_path / "site"
    (site / "pkg").mkdir(parents=True)
    (site / "pkg" / "__init__.py").write_text("VALUE = 1\n")
    (site / "link").symlink_to("pkg")

    first = oci.layer_from(site, "/opt/sc/python-env/site")
    os.utime(site / "pkg" / "__init__.py", (1, 1))
    assert oci.layer_from(site, "/opt/sc/python-env/site") == first   # no times of this host's
    data, layer_digest, diff_id = first
    assert layer_digest == "sha256:" + hashlib.sha256(data).hexdigest()
    assert diff_id == "sha256:" + hashlib.sha256(gzip.decompress(data)).hexdigest()

    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        members = {member.name: member for member in tar.getmembers()}
    assert {"opt", "opt/sc", "opt/sc/python-env", "opt/sc/python-env/site",
            "opt/sc/python-env/site/pkg/__init__.py"} <= set(members)
    assert members["opt/sc/python-env/site/link"].issym()     # a link stays a link
    assert {member.mtime for member in members.values()} == {0}


@pytest.fixture
def registry(monkeypatch, tmp_path, runs_test_version):
    '''A registry at registry:5000, marked insecure as the rig marks it, with
    one base image of two layers in `sc-tools`. Records every upload.'''
    responses = pytest.importorskip("responses")

    conf = tmp_path / "registries.conf"
    conf.write_text('[[registry]]\nlocation = "registry:5000"\ninsecure = true\n')
    monkeypatch.setenv("CONTAINERS_REGISTRIES_CONF", str(conf))

    config = json.dumps({"architecture": "amd64", "os": "linux",
                         "rootfs": {"type": "layers", "diff_ids": [digest("1"), digest("2")]},
                         "history": [{"created_by": "base"}]}).encode()
    layer = "application/vnd.oci.image.layer.v1.tar+gzip"
    manifest = {
        "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {"mediaType": "application/vnd.oci.image.config.v1+json",
                   "digest": "sha256:" + hashlib.sha256(config).hexdigest(),
                   "size": len(config)},
        "layers": [{"mediaType": layer, "digest": digest("3"), "size": 10},
                   {"mediaType": layer, "digest": digest("4"), "size": 20}]}
    root = "http://registry:5000/v2/sc-tools"
    uploaded = {}

    def take(request):
        from urllib.parse import parse_qs, urlsplit

        uploaded[parse_qs(urlsplit(request.url).query)["digest"][0]] = request.body
        return (201, {}, "")

    def put_manifest(request):
        uploaded["manifest"] = json.loads(request.body)
        uploaded["manifest-at"] = request.url.rsplit("/", 1)[1]
        uploaded["manifest-digest"] = "sha256:" + hashlib.sha256(request.body).hexdigest()
        return (201, {}, "")

    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        mock.get(f"{root}/manifests/{digest('b')}", json=manifest)
        mock.get(f"{root}/blobs/{manifest['config']['digest']}", body=config)
        mock.head(re.compile(rf"{root}/blobs/.*"), status=404)
        mock.post(f"{root}/blobs/uploads/", status=202,
                  headers={"Location": "/v2/sc-tools/blobs/uploads/u1?state=s"})
        mock.add_callback("PUT", re.compile(rf"{root}/blobs/uploads/u1.*"), callback=take)
        mock.add_callback("PUT", re.compile(rf"{root}/manifests/.*"), callback=put_manifest)
        mock.uploaded = uploaded
        mock.manifest = manifest
        yield mock


def test_a_derived_image_is_the_base_with_one_layer_more_and_an_index_takes_none(
        registry, tmp_path):
    '''In the base's own repository, so every layer it names is one the
    registry already holds there -- and only three small blobs move.'''
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "x.py").write_text("")
    layer = oci.layer_from(tmp_path / "site", environment.IMAGE_SITE)
    base = f"registry:5000/sc-tools@{digest('b')}"

    ref, derived = oci.derive(base, layer, comment="a node's Python")

    uploaded = registry.uploaded
    # By digest, with no tag: nothing can be pointed at other content later.
    assert derived == uploaded["manifest-digest"] == uploaded["manifest-at"]
    assert ref == f"registry:5000/sc-tools@{derived}"
    manifest = uploaded["manifest"]
    assert manifest["layers"][:2] == registry.manifest["layers"]
    assert manifest["layers"][2]["digest"] == layer[1]
    assert uploaded[layer[1]] == layer[0]
    config = json.loads(uploaded[manifest["config"]["digest"]])
    assert config["rootfs"]["diff_ids"] == [digest("1"), digest("2"), layer[2]]
    assert config["history"][-1]["comment"] == "a node's Python"

    registry.replace("GET", f"http://registry:5000/v2/sc-tools/manifests/{digest('b')}",
                     json={"schemaVersion": 2, "manifests": [],
                           "mediaType": "application/vnd.oci.image.index.v1+json"})
    with pytest.raises(RuntimeError, match="multi-platform index"):
        oci.derive(base, layer, comment="")


def test_the_install_imports_nothing_but_the_standard_library():
    '''It runs under the base image's Python, whose SiliconCompiler may be a
    release without this module -- or without any of this server.'''
    tree = ast.parse(open(pipbuild.__file__).read())
    imported = {alias.name.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.Import) for alias in node.names} | \
        {node.module.split(".")[0] for node in ast.walk(tree)
         if isinstance(node, ast.ImportFrom) and node.module}

    assert imported <= set(sys.stdlib_module_names)


@pytest.fixture
def pip(monkeypatch):
    '''pip, faked: what it was run with, and an install into the environment
    whose Python ran it.'''
    import glob

    calls = []

    def fake(command, **kwargs):
        calls.append((command, kwargs["env"], open(command[command.index("-c") + 1]).read()))
        if fake.output:
            return subprocess.CompletedProcess(command, 1, stdout=fake.output)
        environment = os.path.dirname(os.path.dirname(command[0]))
        site, = {os.path.realpath(path) for path in glob.glob(
            os.path.join(environment, "lib*", "python*", "site-packages"))}
        for name in ("a_pkg", "b_ext"):
            os.makedirs(os.path.join(site, name))
            write_dist(site, name, "1.0")
        return subprocess.CompletedProcess(command, 0, stdout="installed")

    fake.output = None
    monkeypatch.setattr(subprocess, "run", fake)
    fake.calls = calls
    return fake


def write_dist(site, name, version):
    dist = os.path.join(site, f"{name}-{version}.dist-info")
    os.makedirs(dist)
    with open(os.path.join(dist, "METADATA"), "w") as f:
        f.write(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")


def requirements(tmp_path, requirements="", constraints=""):
    (tmp_path / "req.txt").write_text(requirements)
    (tmp_path / "con.txt").write_text(constraints)
    return str(tmp_path / "req.txt"), str(tmp_path / "con.txt")


def test_the_layer_is_the_environments_own_site_packages_and_pip_sees_only_the_proxy(
        pip, tmp_path, monkeypatch):
    '''pip run from a venv that sees this Python's packages, all pinned
    ahead of the job's constraints -- never `--target`, which ignores them.'''
    from importlib import metadata

    monkeypatch.setenv("PIP_INDEX_URL", "https://pkgs.example.com/simple/")
    monkeypatch.setenv("HTTPS_PROXY", "http://somewhere-else:3128")
    listed, limited = requirements(tmp_path, "a_pkg==1.0\n", "zz-not-here==3.1\n")

    result = pipbuild.install(listed, limited, str(tmp_path / "out" / "site"),
                              proxy_socket=os.path.join(tempfile.mkdtemp(prefix="sc-t-"),
                                                        "proxy.sock"))

    (command, env, constraints), = pip.calls
    assert command[1:4] == ["-m", "pip", "install"] and command[0] != sys.executable
    assert command[command.index("--only-binary") + 1] == ":all:"
    assert "--target" not in command
    assert f"pytest=={metadata.version('pytest')}" in constraints.splitlines()
    assert constraints.splitlines()[-1] == "zz-not-here==3.1"
    assert result["installed"] == [["a-pkg", "1.0"], ["b-ext", "1.0"]]
    # Only what was added: not the .pth that let it see this Python's.
    assert sorted(os.listdir(tmp_path / "out" / "site")) == [
        "a_pkg", "a_pkg-1.0.dist-info", "b_ext", "b_ext-1.0.dist-info"]
    assert sorted(os.listdir(tmp_path / "out")) == ["site"]     # the work dir is gone
    assert "PIP_INDEX_URL" not in env and env["PIP_CONFIG_FILE"] == os.devnull
    assert env["HTTPS_PROXY"].startswith("http://127.0.0.1:")


@pytest.mark.parametrize("output,named,network", [
    ("ERROR: Could not find a version that satisfies the requirement numpy==9.9 "
     "(from versions: 1.0)\nERROR: No matching distribution found for numpy==9.9",
     ["numpy==9.9"], False),
    ("ERROR: Cannot install pyuvm==3.0.0 because these package versions have "
     "conflicting dependencies.\nThe conflict is caused by:\n    The user requested "
     "(constraint) cocotb==2.1.0\n", ["cocotb==2.1.0"], False),
    ("WARNING: Retrying (Retry(total=4...)) after connection broken by "
     "'ProxyError('Cannot connect to proxy.')'\nERROR: No matching distribution "
     "found for numpy==2.0.1", ["numpy==2.0.1"], True),
])
def test_a_failed_install_says_which_and_whether_it_was_the_network(
        pip, tmp_path, monkeypatch, output, named, network):
    pip.output = output
    # A name this Python does not hold, or it is never handed to pip at all.
    listed, limited = requirements(tmp_path, "scnotheld==9.9\n")
    # Every index has numpy: what failed is the version, never the name.
    monkeypatch.setattr(pipbuild, "on_index", lambda name, indexes, proxy=None: True)

    result = pipbuild.install(listed, limited, str(tmp_path / "site"))

    assert result["returncode"] == 1
    assert (result["unresolved"], result["network"]) == (named, network)
    assert not (tmp_path / "site").exists()


@pytest.fixture
def image_python(tmp_path):
    '''A venv holding cocotb 2.0, as SiliconCompiler's images do, and an index
    on disk of what the tests below install.'''
    import glob
    import venv

    pytest.importorskip("pip")
    image = tmp_path / "image"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(image)
    site, = {os.path.realpath(path) for path in glob.glob(
        str(image / "lib*" / "python*" / "site-packages"))}
    os.makedirs(os.path.join(site, "cocotb"))
    write_dist(site, "cocotb", "2.0")

    index = tmp_path / "index"
    index.mkdir()
    for name, version, requires in (
            ("cocotb", "1.9", ()), ("cocotb_bus", "0.3.0", ["cocotb>=1.6"]),
            ("pyuvm", "3.0.0", ["cocotb<2.0,>=1.6"]),
            ("scfake_old", "1.0", ()), ("scfake_old", "1.1", ())):
        make_wheel(index, name, version, requires)
    # Listed, never fetched: a source under `--only-binary`, or another platform's wheel.
    for placeholder in ("cocotb_bus-0.3.7-cp27-cp27m-win32.whl", "scfake_pure-1.0.tar.gz",
                        "scfake_fast-1.0.tar.gz", "scfake_fast-1.0-cp27-cp27m-win32.whl"):
        (index / placeholder).touch()
    return image / "bin" / "python", simple_index(
        index, yanked={"scfake_old-1.1-py3-none-any.whl"})


def build_in(image_python, tmp_path, text, needs=None, offline=False):
    '''One install of ``text`` in the image's Python, with a wheel requiring
    ``needs`` where given -- from the index, or none (image-only mode).'''
    python, index = image_python
    listed, limited = requirements(tmp_path, text)
    wheels = []
    if needs is not None:
        (tmp_path / "made").mkdir()
        wheels = ["--wheel", make_wheel(tmp_path / "made", "scfake_helper", "0.1.0", needs)]
    env = {key: value for key, value in os.environ.items() if not key.startswith("PIP_")}
    env.update(PYTHONPATH=os.path.dirname(os.path.dirname(
        pytest.importorskip("pip").__file__)))
    subprocess.run([str(python), pipbuild.__file__, "--requirements", listed,
                    "--constraints", limited, "--site", str(tmp_path / "out" / "site"),
                    "--result", str(tmp_path / "result.json"),
                    *([] if offline else ["--index-url", index]), *wheels],
                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.loads((tmp_path / "result.json").read_text())


def check(result, expected):
    '''Each of ``expected`` in ``result``: None for absent or empty, a callable
    to test the value.'''
    for key, want in expected.items():
        if want is None:
            assert not result.get(key), (key, result)
        else:
            assert want(result[key]) if callable(want) else result[key] == want, (key, result)


def names_cocotb(names):
    return any("cocotb" in name for name in names)


@pytest.mark.parametrize("text,needs,expected", [
    # A dependency on cocotb brings no second one for the simulator to load.
    ("cocotb-bus==0.3.0\n", None, {"installed": [["cocotb-bus", "0.3.0"]]}),
    # A listed version of one the image holds is ignored, and said.
    ("cocotb==1.9\n", None, {"installed": [], "ignored": {"cocotb": ["1.9", "2.0"]}}),
    # §L: listed, but nothing of it installs here -- the newest of its line, said.
    ("cocotb-bus==0.3.7\n", None, {"installed": [["cocotb-bus", "0.3.0"]],
                                   "substituted": {"cocotb-bus": ["0.3.7", "0.3.0"]}}),
    # PEP 592: pip installs a yanked file pinned with `==`, so it is held to its line.
    ("scfake-old==1.1\n", None, {"installed": [["scfake-old", "1.0"]],
                                 "substituted": {"scfake-old": ["1.1", "1.0"]},
                                 "yanked": ["scfake-old"]}),
    # An uploaded wheel goes in with the rest, its dependencies from the index.
    ("", ["cocotb-bus>=0.3"], {"installed": [["cocotb-bus", "0.3.0"],
                                             ["scfake-helper", "0.1.0"]]}),
])
def test_an_install_in_the_images_python_keeps_the_images_own(
        image_python, tmp_path, text, needs, expected):
    result = build_in(image_python, tmp_path, text, needs)

    assert result["returncode"] == 0, result.get("tail")
    check(result, expected)
    assert not (tmp_path / "out" / "site" / "cocotb").exists()


@pytest.mark.parametrize("text,needs,offline,expected", [
    ("pyuvm==3.0.0\n", None, False, {"unresolved": names_cocotb, "absent": None}),
    # Absent is the exact version (D292): never taken from its line.
    ("cocotb-bus==0.3.5\n", None, False, {"absent": ["cocotb-bus"], "substituted": None}),
    # Pure, only a source: sent back for, the rest still worked through.
    ("scfake-pure==1.0\ncocotb-bus==0.3.0\n", None, False,
     {"source_only": ["scfake-pure"], "absent": []}),
    # Compiled elsewhere, only a source here: no client's wheel could run either.
    ("scfake-fast==1.0\n", None, False,
     {"only_source": ["scfake-fast"], "absent": None, "source_only": None}),
    # No index has it: every one sent back for in one trip.
    ("scfake-private==1.2.0\ncocotb-bus==0.3.0\nscfake-other==0.1.0\n", None, False,
     {"absent": ["scfake-other", "scfake-private"]}),
    # Image-only mode: what the image lacks, listed or a wheel's dependency.
    ("scfake-listed==1.0\n", ["scfake-needed>=1.0"], True,
     {"absent": ["scfake-listed", "scfake-needed"]}),
    # Image-only mode's `uninstallable`: a wheel against the image's pins.
    ("", ["cocotb<2.0"], True, {"unresolved": names_cocotb, "absent": None,
                                "source_only": None}),
])
def test_an_install_that_cannot_finish_says_why_and_leaves_nothing(
        image_python, tmp_path, text, needs, offline, expected):
    result = build_in(image_python, tmp_path, text, needs, offline)

    assert result["returncode"] != 0
    check(result, expected)
    assert not (tmp_path / "out" / "site").exists()


BASE = {
    "ociVersion": "1.0.2",
    "process": {"terminal": False, "cwd": "/", "args": ["sh"],
                "env": ["PATH=/venv/bin:/usr/bin:/bin", "SECRET=from-the-image-config"],
                "capabilities": {"bounding": ["CAP_CHOWN", "CAP_NET_ADMIN"],
                                 "effective": ["CAP_NET_ADMIN"]}},
    "root": {"path": "rootfs"},
    "mounts": [
        {"destination": "/proc", "type": "proc", "source": "proc"},
        {"destination": "/sys/fs/cgroup", "type": "cgroup", "source": "cgroup"},
        # What `_prepare_spec` writes for the data directory and the cluster.
        {"destination": "/sc_server", "type": "none", "source": "/sc_server",
         "options": ["rbind", "rw"]},
        {"destination": "/run/munge", "type": "bind", "source": "/run/munge"},
    ],
    "linux": {"namespaces": [{"type": "pid"}, {"type": "mount"}, {"type": "ipc"}]},
}

TARGET = {"python": "cpython-312", "version": "3.12.3", "platform": "linux-x86_64"}


def test_the_build_container_reaches_nothing_but_its_three_directories(tmp_path):
    config = envbuild.build_config(BASE, tmp_path, tmp_path / "req",
                                   tmp_path / "out", tmp_path / "sock", ["python3", "x"])

    assert config["root"] == {"path": str((tmp_path / "rootfs").resolve()), "readonly": True}
    binds = {mount["destination"]: mount for mount in config["mounts"]
             if "rbind" in (mount.get("options") or [])}
    assert set(binds) == {"/tmp/sc-req", "/tmp/sc-out", "/tmp/sc-proxy"}   # no /sc_server
    assert "ro" in binds["/tmp/sc-req"]["options"]
    destinations = [mount["destination"] for mount in config["mounts"]]
    assert "/run/munge" not in destinations and "/sys/fs/cgroup" not in destinations
    assert destinations.index("/tmp") < destinations.index("/tmp/sc-out")
    # A network of its own: nothing in it but a loopback.
    assert [ns["type"] for ns in config["linux"]["namespaces"]].count("network") == 1
    assert config["process"]["args"] == ["python3", "x"]
    assert "SECRET=from-the-image-config" not in config["process"]["env"]
    assert "PATH=/venv/bin:/usr/bin:/bin" in config["process"]["env"]
    # NET_ADMIN is crun's, on the node: no build's or node's process holds it (D39).
    assert config["process"]["capabilities"] == {"bounding": ["CAP_CHOWN"], "effective": []}
    assert BASE["mounts"][2]["destination"] == "/sc_server"        # the base untouched
    (tmp_path / "config.json").write_text(json.dumps(BASE))
    images._prepare_spec(tmp_path / "config.json", mounts=["/sc_server"])
    held = json.loads((tmp_path / "config.json").read_text())["process"]["capabilities"]
    assert not any("CAP_NET_ADMIN" in caps for caps in held.values())


@pytest.fixture
def base_bundle(monkeypatch, tmp_path):
    '''The base's bundle, as staging it would leave it -- without skopeo.'''
    root = tmp_path / "images"
    staged = []

    def stage(where, ref, image_digest, mounts=()):
        bundle = images.bundle_path(where, image_digest)
        (bundle / "rootfs").mkdir(parents=True, exist_ok=True)
        (bundle / "config.json").write_text(json.dumps(BASE))
        staged.append((ref, image_digest, list(mounts)))
        return bundle

    monkeypatch.setattr(images, "stage_bundle", stage)
    stage.root = root
    stage.staged = staged
    return stage


@pytest.fixture
def pushed(monkeypatch):
    calls = []

    def derive(base_ref, layer, comment):
        calls.append((base_ref, layer))
        return f"registry:5000/sc-tools@{digest('d')}", digest("d")

    monkeypatch.setattr(oci, "derive", derive)
    return calls


def workspace_for(tmp_path, root, text="numpy==2.0.1\n"):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / envbuild.REQUIREMENTS).write_text(text)
    (workspace / envbuild.CONSTRAINTS).write_text("scapy==2.5.0\n")
    return workspace, {"key": "k" * 64, "base_ref": f"registry:5000/sc-tools@{digest('b')}",
                       "base_digest": digest("b"), "bundles_root": str(root),
                       "mounts": ["/sc_server"],
                       "index_allowlist": ["https://pypi.org/simple/"], "timeout": 60}


def container(pip_result, files=None):
    '''A build container that writes what pip would have.'''
    seen = {}

    def run(bundle, command, path, timeout):
        config = json.loads((bundle / "config.json").read_text())
        seen.update(config=config, command=command, path=path,
                    req=sorted(os.listdir(next(m["source"] for m in config["mounts"]
                                               if m["destination"] == "/tmp/sc-req"))))
        out = next(m["source"] for m in config["mounts"] if m["destination"] == "/tmp/sc-out")
        for name, body in (files or {}).items():
            os.makedirs(os.path.dirname(os.path.join(out, "site", name)), exist_ok=True)
            open(os.path.join(out, "site", name), "w").write(body)
        if pip_result is not None:
            open(os.path.join(out, "pip.json"), "w").write(json.dumps(pip_result))
        return "the container's output"

    run.seen = seen
    return run


@pytest.mark.parametrize("source_builds", [False, True])
def test_a_build_installs_from_the_deployments_indexes_and_pushes_one_layer_on_the_base(
        tmp_path, base_bundle, pushed, source_builds):
    '''Indexes are configuration, never the job's; a source distribution's
    code runs only here, sealed, and only where `python_source_builds` says.'''
    run = container(dict(TARGET, returncode=0, installed=[["numpy", "2.0.1"]]),
                    files={"numpy/__init__.py": "x = 1\n"})
    workspace, spec = workspace_for(tmp_path, base_bundle.root)
    spec["indexes"] = ["https://pypi.org/simple/", "https://extra.example/simple/"]
    if source_builds:
        spec["source_builds"] = True
    (workspace / envbuild.WHEELS).mkdir()
    make_wheel(workspace / envbuild.WHEELS, "scfake_helper", "0.1.0")

    result = envbuild.build(spec, workspace, run=run)

    assert result == dict(TARGET, ok=True, ref=f"registry:5000/sc-tools@{digest('d')}",
                          digest=digest("d"), installed=[["numpy", "2.0.1"]],
                          substituted={}, ignored={}, yanked=[])
    command = run.seen["command"]
    assert [command[at + 1] for at, part in enumerate(command) if part == "--index-url"] \
        == spec["indexes"]
    assert ("--allow-source" in command) is source_builds
    assert run.seen["req"] == ["constraints.txt", "pipbuild.py", "requirements.txt", "wheels"]
    assert command[command.index("--wheel") + 1] == \
        "/tmp/sc-req/wheels/scfake_helper-0.1.0-py3-none-any.whl"
    assert command[command.index("--constraints") + 1] == "/tmp/sc-req/constraints.txt"
    assert run.seen["path"] == "/venv/bin:/usr/bin:/bin"
    assert base_bundle.staged == [(spec["base_ref"], digest("b"), ["/sc_server"])]

    # Its bundle is the base's root with the layer bound in -- no second
    # unpack of a tool image per environment.
    bundle = images.bundle_path(base_bundle.root, digest("d"))
    config = json.loads((bundle / "config.json").read_text())
    assert config["root"]["path"] == str((images.bundle_path(base_bundle.root, digest("b"))
                                          / "rootfs").resolve())
    layer = next(m for m in config["mounts"] if m["destination"] == environment.IMAGE_SITE)
    assert "ro" in layer["options"]
    assert (bundle / "layer" / "numpy" / "__init__.py").is_file()
    assert {mount["destination"] for mount in config["mounts"]} >= {"/sc_server"}
    assert not (workspace / "bundle").exists() and not (workspace / "out").exists()


@pytest.mark.parametrize("pip_result,reason", [
    (dict(TARGET, returncode=1, absent=["scfake-private"], unresolved=[], tail=""), "absent"),
    (dict(TARGET, returncode=1, unresolved=["numpy==9.9"], network=False, tail="no wheel"),
     "uninstallable"),
    # The index did not answer: nothing about the pins, so the server's failure.
    (dict(TARGET, returncode=1, unresolved=["numpy==9.9"], network=True, tail="Retrying"),
     "error"),
    (None, "error"),                        # the container never ran to the end
])
def test_a_build_that_fails_pushes_nothing(tmp_path, base_bundle, pushed, pip_result, reason):
    workspace, spec = workspace_for(tmp_path, base_bundle.root)

    result = envbuild.build(spec, workspace, run=container(pip_result))

    assert (result["ok"], result["reason"]) == (False, reason)
    if reason == "absent":
        assert result["absent"] == ["scfake-private"]
    assert pushed == []


def test_a_build_gone_without_a_result_is_given_up_on_after_a_grace(tmp_path):
    asked = []

    def gone():
        asked.append(1)
        return False

    def landed():
        (tmp_path / envbuild.RESULT).write_text(json.dumps({"ok": True}))
        return False

    assert envbuild.wait_for(tmp_path, 60, alive=gone, pause=0.01, grace=0.05) is None
    assert len(asked) == 1                    # the scheduler is asked once, not per look
    # A result that lands after its job ended is still read.
    assert envbuild.wait_for(tmp_path, 60, alive=landed, pause=0.01, grace=5) == {"ok": True}


def test_the_result_is_written_whatever_happens(tmp_path):
    (tmp_path / envbuild.SPEC).write_text("not json")

    assert envbuild.main([str(tmp_path / envbuild.SPEC)]) == 0
    result = json.loads((tmp_path / envbuild.RESULT).read_text())
    assert (result["ok"], result["reason"]) == (False, "error")


def start_proxy(allowlist, **kwargs):
    path = os.path.join(tempfile.mkdtemp(prefix="sc-t-"), "proxy.sock")
    running = envbuild.Proxy(path, allowlist, **kwargs)
    running.start()
    running.path = path
    return running


@pytest.fixture
def proxy():
    running = start_proxy(["https://pypi.org/simple/", "https://files.pythonhosted.org/",
                           "https://localhost/", "http://mirror.example.com/pypi/"])
    yield running
    running.close()


def send(proxy, request, monkeypatch=None):
    '''A client that sent ``request`` -- and, given ``monkeypatch``, the far
    end of the upstream the proxy opens for it.'''
    here = None
    if monkeypatch:
        here, there = socket.socketpair()
        here.settimeout(5)
        monkeypatch.setattr(envbuild, "_open_public", lambda host, port, **kwargs: there)
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(proxy.path)
    client.sendall(request)
    return client, here


def read(sock, until=b"\r\n\r\n"):
    '''What ``sock`` receives up to ``until``, or (None) until it closes.'''
    data = b""
    while (until is None or until not in data) and (chunk := sock.recv(4096)):
        data += chunk
    return data


def test_what_the_proxy_admits(proxy):
    assert proxy.admits_connect("pypi.org", 443)
    assert proxy.admits_connect("files.pythonhosted.org", 443)
    assert not proxy.admits_connect("pypi.org", 8443)
    assert not proxy.admits_connect("evil.example.com", 443)
    assert proxy.admits_get("http://mirror.example.com/pypi/simple/numpy/")
    assert not proxy.admits_get("http://mirror.example.com/other/")
    assert not proxy.admits_get("https://pypi.org/simple/")      # that is CONNECT's


@pytest.mark.parametrize("request_line,status,said,refused", [
    (b"CONNECT evil.example.com:443", b"403", b"", ["evil.example.com"]),
    # Whatever the list says: a name is whatever its owner's DNS answers.
    (b"CONNECT localhost:443", b"403", b"non-public", ["localhost"]),
    (b"POST http://mirror.example.com/pypi/", b"405", b"", []),   # neither tunnel nor GET
])
def test_what_the_proxy_refuses_it_names(proxy, request_line, status, said, refused):
    client, _ = send(proxy, request_line + b" HTTP/1.1\r\n\r\n")
    with client:
        answer = read(client)

    assert answer.startswith(b"HTTP/1.1 " + status) and said in answer
    assert proxy.refused == refused


def test_an_admitted_tunnel_and_get_carry_both_ways(proxy, monkeypatch):
    '''A GET goes upstream in origin form, closing, with nothing meant for the
    proxy -- and the answer comes back as it was sent.'''
    client, here = send(proxy, b"CONNECT pypi.org:443 HTTP/1.1\r\nHost: pypi.org\r\n\r\nhello",
                        monkeypatch)
    with client, here:
        assert client.recv(4096).startswith(b"HTTP/1.1 200")
        assert here.recv(5) == b"hello"
        here.sendall(b"world")
        assert client.recv(5) == b"world"

    client, here = send(proxy, b"GET http://mirror.example.com/pypi/simple/numpy/?a=1 HTTP/1.1"
                        b"\r\nHost: mirror.example.com\r\nProxy-Authorization: x\r\n"
                        b"Connection: keep-alive\r\nAccept: text/html\r\n\r\n", monkeypatch)
    with client:
        head = read(here).decode().split("\r\n")
        assert head[0] == "GET /pypi/simple/numpy/?a=1 HTTP/1.1"
        assert "Accept: text/html" in head and "Connection: close" in head
        assert not any(line.lower().startswith(("proxy-", "connection: keep")) for line in head)
        here.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
        here.close()
        assert read(client, until=None) == b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"


@pytest.mark.parametrize("private_exact,target,public_only", [
    (True, "mirror.corp.example.com:443", False),     # an exact host: the operator's choice
    (True, "a.pkgs.example.org:443", True),           # a wildcard never is
    (False, "mirror.corp.example.com:443", True),     # nor any entry of a source list
])
def test_only_an_exact_index_host_may_be_a_private_address(
        monkeypatch, private_exact, target, public_only):
    '''Surface D172: an exact index host is a mirror on the operator's own
    network; a wildcard, and every source-allowlist entry, keep the address rule.'''
    asked = []

    def opened(host, port, public_only=True):
        asked.append(public_only)
        return None

    monkeypatch.setattr(envbuild, "_open_public", opened)
    running = start_proxy(["https://mirror.corp.example.com/simple/",
                           "https://*.pkgs.example.org/"], private_exact_hosts=private_exact)
    try:
        client, _ = send(running, f"CONNECT {target} HTTP/1.1\r\n\r\n".encode())
        with client:
            read(client)
    finally:
        running.close()

    assert asked == [public_only]


@pytest.fixture
def store(runs_test_version):
    from siliconcompiler.remote.server.state.store import Store

    with Store("server.db") as db:
        user = db.upsert_user("operator", "someone@host")
        db.actor = user["id"]
        images.register_software(db, "siliconcompiler", "SiliconCompiler", db.actor, "python")
        images.register_version(db, "siliconcompiler", "0.38.0", db.actor)
        db.base = images.register_image(db, "ghcr.io/x/sc:0.38.0", digest("a"),
                                        [("siliconcompiler", "0.38.0")], db.actor)
        yield db


def derive(store, letter, key, installed=()):
    return images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest(letter)}",
                                   digest(letter), key, list(installed), note="")


def test_a_derived_image_is_reached_only_by_its_key(store):
    '''Never resolved to, or one user's packages would place another user's
    node; and the first registered for a key is what every later job reuses.'''
    derived = derive(store, "e", "k1", [("numpy", "2.0.1")])

    assert [image["id"] for image in images.live_images(store)] == [store.base]
    assert "numpy" not in json.dumps(store.advertised_software(containers=True))
    assert images.contents_of(store, [derived]) == {
        "python": {"numpy": ["2.0.1"], "siliconcompiler": ["0.38.0"]}, "tools": {}}
    assert images.derived_image(store, store.base, "k1")["id"] == derived
    catalogue = images.catalogue(store)
    assert [image["id"] for image in catalogue["images"]] == [store.base]
    (built,) = catalogue["derived"]
    assert (built["base"], built["installed"]) == ("ghcr.io/x/sc:0.38.0", ["numpy==2.0.1"])
    assert derive(store, "f", "k1") == derived        # whatever digest a second push got


def test_the_key_is_the_base_the_lists_the_wheels_and_the_framework(store):
    '''§L, *What it caches*: whatever changes what the install gives the run
    changes the key.'''
    def key(base="a", listed="numpy==2.0.1\n", limited="", wheels=(), names=("cocotb",),
            indexes=(), source_builds=False):
        return images.derivation(digest(base), listed, limited, wheels, names,
                                 indexes=indexes, source_builds=source_builds)

    assert len({key(), key(base="b"), key(listed="numpy==2.0.2\n"),
                key(limited="scapy==2.5.0\n"), key(wheels=["w1"]),
                key(names=("cocotb", "pyuvm")),
                key(indexes=["https://mirror.example/simple/"]),
                key(source_builds=True)}) == 8
    assert key(wheels=["w1", "w2"]) == key(wheels=["w2", "w1"])


def test_a_distribution_found_wrong_after_it_was_built_is_built_again(store, capsys):
    '''`drop-built`: every derived image and host environment holding it, at a
    version or any, retired; the rest stays, and retired rows stay answerable.'''
    from siliconcompiler.remote.server.jobs.pythonenv import ENVIRONMENTS
    from siliconcompiler.remote.server.software import registry

    derive(store, "e", "k1", [("numpy", "2.0.1")])
    other = derive(store, "f", "k2", [("scapy", "2.5.0")])
    environments = Path(ENVIRONMENTS)
    for name, installed in (("cpython-312-aaaa", [["NumPy", "2.0.1"]]),
                            ("cpython-312-bbbb", [["numpy", "1.26.4"]])):
        (environments / name).mkdir(parents=True)
        (environments / f"{name}.json").write_text(json.dumps({"installed": installed}))

    assert registry.main(["-datadir", ".", "drop-built", "numpy==2.0.2"]) == 0
    assert capsys.readouterr().out == "nothing built holds numpy==2.0.2\n"
    assert registry.main(["-datadir", ".", "drop-built", "numpy==2.0.1"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"dropped ghcr.io/x/sc@{digest('e')}",
        f"dropped {(environments / 'cpython-312-aaaa').resolve()}"]
    assert images.derived_image(store, store.base, "k1") is None
    assert images.derived_image(store, store.base, "k2")["id"] == other
    assert sorted(os.listdir(environments)) == ["cpython-312-bbbb", "cpython-312-bbbb.json"]
    assert store.one("SELECT retired_at FROM images WHERE derivation = 'k1'")["retired_at"]
    # By name alone: every version.
    assert images.drop_built(store, "numpy", None, store.actor,
                             environments=environments) == \
        [str(environments / "cpython-312-bbbb")]


def test_a_bundle_lives_as_long_as_its_base(store, tmp_path):
    '''A derived bundle runs on its base's root filesystem: both go when the
    base is retired.'''
    derive(store, "e", "k1")
    root = tmp_path / "images"
    for letter in "ae":
        (images.bundle_path(root, digest(letter)) / "rootfs").mkdir(parents=True)

    images.sweep_bundles(root, store)
    assert sorted(path.name[:1] for path in root.iterdir()) == ["a", "e"]
    images.retire_image(store, store.base, store.actor)
    images.sweep_bundles(root, store)
    assert list(root.iterdir()) == []


flask = pytest.importorskip("flask", reason="the server extra is not installed")

from test_server_jobs import FakeDispatcher, login, stage, submit, wants  # noqa: E402
from test_server_sources_flow import wait_for as until                     # noqa: E402


class Builder(FakeDispatcher):
    '''A dispatcher whose builds answer at once, as ``answer`` says.'''

    def __init__(self, answer):
        super().__init__()
        self.answer = answer
        self.builds = []

    def submit_build(self, name, workspace, spec, queue=None):
        spec = json.loads(open(spec).read())
        wheels = workspace / envbuild.WHEELS
        self.builds.append({"queue": queue, "spec": spec,
                            "file": (workspace / envbuild.REQUIREMENTS).read_text(),
                            "constraints": (workspace / envbuild.CONSTRAINTS).read_text(),
                            "wheels": sorted(os.listdir(wheels)) if wheels.is_dir() else []})
        result = self.answer(spec)
        if result is not None:
            (workspace / envbuild.RESULT).write_text(json.dumps(result))
        return f"build:{len(self.builds)}"


BUILT = dict(TARGET, ok=True, ref=f"ghcr.io/x/sc@{digest('e')}", digest=digest("e"),
             installed=[["numpy", "2.0.1"]])


@pytest.fixture
def builder_server(runs_test_version):
    from siliconcompiler.remote.server.app import create_app
    from siliconcompiler.remote.server.state.store import Store

    os.makedirs("builder-datadir", exist_ok=True)
    with open("builder-datadir/config.json", "w") as f:
        json.dump({"containers": True, "env_builder": True, "build_queue": "build"}, f)
    with Store("builder-datadir/server.db") as store:
        with store.transaction():
            actor = store.upsert_user("operator", "someone@host")["id"]
        images.register_software(store, "siliconcompiler", "SiliconCompiler", actor, "python")
        images.register_version(store, "siliconcompiler", "0.38.0", actor, preference=10)
        images.register_image(store, "ghcr.io/x/sc:0.38.0", digest("a"),
                              [("siliconcompiler", "0.38.0")], actor)

    return create_app("builder-datadir", cluster="local")


@pytest.fixture
def client(builder_server):
    return builder_server.test_client()


@pytest.fixture
def token(client, key):
    return login(client, key).get_json()["access_token"]


def builder(server, answer):
    fake = Builder(answer)
    server.config["SC_JOBS"]._dispatcher = fake
    server.config["SC_JOBS"]._build_wait = {"pause": 0.02, "ask_every": 0.02, "grace": 0.1}
    return fake


def submitted(client, key, token, job_archive, project, packages=("numpy==2.0.1",),
              wheels=()):
    '''A job submitted with ``packages`` (None: no lists) and ``wheels``.'''
    archive, upload_digest, size = job_archive(project, extra={
        f"{environment.wheels_path()}/{os.path.basename(path)}": open(path, "rb").read()
        for path in wheels})
    body = {} if packages is None else {"python_packages": {
        "requirements": list(packages), "constraints": ["scapy==2.5.0"]}}
    job = stage(client, key, token, archive, size, requested_versions=wants("0.38.0"), **body)
    response = submit(client, key, token, job["id"], upload_digest, size)
    assert response.status_code == 202, response.get_json()
    return response.get_json()


def row(server, job_id):
    return server.config["SC_STORE"].one("SELECT * FROM jobs WHERE id = ?", (job_id,))


def placed(server, job_id):
    return {(node["step"], node["index"]): node["image_id"]
            for node in server.config["SC_STORE"].all(
                "SELECT * FROM job_nodes WHERE job_id = ?", (job_id,))}


def test_a_node_running_the_users_python_runs_in_the_image_built_once_for_it(
        builder_server, client, key, token, job_archive, python_project):
    from conftest import run_manifest
    from test_server_sources_flow import read

    fake = builder(builder_server, lambda spec: BUILT)

    job = submitted(client, key, token, job_archive, python_project)

    assert job["state"] == "staging"              # nothing waits on a build
    assert until(lambda: fake.submitted)
    (build,) = fake.builds
    assert build["queue"] == "build"
    assert build["spec"]["base_ref"] == f"ghcr.io/x/sc@{digest('a')}"
    # The server's own files, written from what parsed.
    assert build["file"].splitlines()[1:] == ["numpy==2.0.1"]
    assert build["constraints"].splitlines()[1:] == ["scapy==2.5.0"]
    assert "constrain" not in build["spec"]
    derived = images.derived_image(builder_server.config["SC_STORE"],
                                   placed(builder_server, job["id"])[("steptwo", "0")],
                                   build["spec"]["key"])
    assert placed(builder_server, job["id"]) == {
        ("stepone", "0"): derived["id"],
        ("steptwo", "0"): row(builder_server, job["id"])["image_id"]}
    assert run_manifest(fake.submitted[0][2]).option.scheduler.get_queue(
        step="stepone", index="0") == f"ghcr.io/x/sc@{digest('e')}"
    # What ran, including what was installed.
    assert read(client, key, token, job["id"])["resolved_versions"] == {
        "python": {"numpy": ["2.0.1"], "siliconcompiler": ["0.38.0"]}, "tools": {}}

    # The same packages on the same image again: built once.
    second = submitted(client, key, token, job_archive, python_project)
    assert until(lambda: len(fake.submitted) == 2)
    assert len(fake.builds) == 1
    assert placed(builder_server, second["id"]) == placed(builder_server, job["id"])


def test_the_jobs_wheels_alone_are_handed_to_the_build(
        builder_server, client, key, token, job_archive, python_project, tmp_path):
    fake = builder(builder_server, lambda spec: BUILT)
    helper = make_wheel(tmp_path, "scfake-helper", "0.1.0")

    submitted(client, key, token, job_archive, python_project, packages=None, wheels=[helper])

    assert until(lambda: fake.submitted)
    (build,) = fake.builds
    assert build["wheels"] == [os.path.basename(helper)]
    assert build["file"].splitlines()[1:] == []


@pytest.mark.parametrize("answer,state", [
    # Never asked for as an upload: it could carry binaries this server cannot run.
    (dict(TARGET, ok=False, reason="uninstallable", unresolved=["numpy==2.0.1"], refused=[],
          tail="ERROR: No matching distribution found for numpy==2.0.1"), "rejected"),
    (dict(TARGET, ok=False, reason="absent", absent=["scfake-private"]), "awaiting_input"),
    # The server's own failure: `failed`, never `rejected`.
    ({"ok": False, "reason": "error", "detail": "the registry did not answer"}, "failed"),
    (None, "failed"),                         # the build job vanished: not waited on
])
def test_a_build_that_does_not_finish_dispatches_nothing(
        builder_server, client, key, token, job_archive, python_project, answer, state):
    fake = builder(builder_server, lambda spec: answer)
    fake.alive = answer is not None

    job = submitted(client, key, token, job_archive, python_project,
                    packages=("numpy==2.0.1", "scfake-private==1.0.0"))

    assert until(lambda: row(builder_server, job["id"])["state"] == state)
    stored = row(builder_server, job["id"])
    assert fake.submitted == []
    if state == "awaiting_input":
        assert json.loads(stored["upload_sources"]) == \
            [{"kind": "python", "name": "scfake-private"}]
        assert json.loads(stored["python_answered"]) == ["scfake-private"]
        return
    assert stored["upload_sources"] is None       # nothing asked of the client
    assert stored["error_type"].endswith(
        "/software-unavailable" if state == "rejected" else "/staging-failed")
    if state == "rejected":
        reason = builder_server.config["SC_STORE"].one(
            "SELECT reason FROM job_state_transitions WHERE job_id = ? "
            "AND to_state = 'rejected'", (job["id"],))["reason"]
        assert "stepone/0's image" in reason and "numpy==2.0.1" in reason
        assert "cpython-312" in reason and "linux-x86_64" in reason
    if answer is None:
        assert fake.cancelled == ["build:1"]


@pytest.mark.threaded_staging
def test_a_job_cancelled_while_it_builds_stays_cancelled(
        builder_server, client, key, token, job_archive, python_project):
    '''Refusing it afterwards would rewrite what its owner did as something
    the server decided -- and the build stops: nobody waits for it.'''
    from conftest import call

    fake = builder(builder_server, lambda spec: None)
    job = submitted(client, key, token, job_archive, python_project)
    assert until(lambda: fake.builds)

    call(client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token, json={})
    fake.alive = False
    assert until(lambda: not builder_server.config["SC_JOBS"]._preparing)

    assert row(builder_server, job["id"])["state"] == "cancelled"
    assert fake.cancelled == ["build:1"]
