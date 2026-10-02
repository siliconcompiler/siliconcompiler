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


# A job's Python packages, built into an image while the job is `staging`
# (implementation-notes §L, container mode). Nothing here runs a container, reaches an
# index or pushes to a registry: each of those is faked at its edge, and what
# is asserted is what crosses it.


def digest(letter):
    return "sha256:" + letter * 64


###########################
# The layer, and the registry
###########################

@pytest.mark.parametrize("ref,parts", [
    ("registry:5000/sc-runtime@sha256:" + "a" * 64,
     ("registry:5000", "sc-runtime", "sha256:" + "a" * 64)),
    ("registry:5000/sc-runtime:v1", ("registry:5000", "sc-runtime", "v1")),
    ("ghcr.io/org/sc:v1@sha256:" + "b" * 64, ("ghcr.io", "org/sc", "sha256:" + "b" * 64)),
    ("registry:5000/a/b/c:tag", ("registry:5000", "a/b/c", "tag")),
])
def test_a_reference_splits_as_docker_reads_it(ref, parts):
    assert oci.split_ref(ref) == parts


def test_a_reference_with_nothing_to_pull_is_refused():
    with pytest.raises(ValueError, match="host/repository@digest"):
        oci.split_ref("registry:5000/sc-runtime")


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
    '''🔴 Read as TOML, as skopeo reads it: a commented-out `insecure`, or a
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
    again = oci.layer_from(site, "/opt/sc/python-env/site")

    assert first == again                       # no times of this machine's
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

    config = {"architecture": "amd64", "os": "linux",
              "rootfs": {"type": "layers", "diff_ids": [digest("1"), digest("2")]},
              "history": [{"created_by": "base"}]}
    config_bytes = json.dumps(config).encode()
    manifest = {
        "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {"mediaType": "application/vnd.oci.image.config.v1+json",
                   "digest": "sha256:" + hashlib.sha256(config_bytes).hexdigest(),
                   "size": len(config_bytes)},
        "layers": [{"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "digest": digest("3"), "size": 10},
                   {"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "digest": digest("4"), "size": 20}]}
    root = "http://registry:5000/v2/sc-tools"
    uploaded = {}

    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        mock.get(f"{root}/manifests/{digest('b')}", json=manifest)
        mock.get(f"{root}/blobs/{manifest['config']['digest']}", body=config_bytes)
        mock.head(re.compile(rf"{root}/blobs/.*"), status=404)
        mock.post(f"{root}/blobs/uploads/", status=202,
                  headers={"Location": "/v2/sc-tools/blobs/uploads/u1?state=s"})

        def take(request):
            from urllib.parse import parse_qs, urlsplit

            uploaded[parse_qs(urlsplit(request.url).query)["digest"][0]] = request.body
            return (201, {}, "")
        mock.add_callback("PUT", re.compile(rf"{root}/blobs/uploads/u1.*"), callback=take)

        def put_manifest(request):
            uploaded["manifest"] = json.loads(request.body)
            uploaded["manifest-at"] = request.url.rsplit("/", 1)[1]
            uploaded["manifest-digest"] = \
                "sha256:" + hashlib.sha256(request.body).hexdigest()
            return (201, {}, "")
        mock.add_callback("PUT", re.compile(rf"{root}/manifests/.*"), callback=put_manifest)
        mock.uploaded = uploaded
        mock.manifest = manifest
        yield mock


def test_a_derived_image_is_the_base_with_one_layer_more(registry, tmp_path):
    '''🔴 In the base's own repository, so every layer it names is one the
    registry already holds there -- and only three small blobs move.'''
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "x.py").write_text("")
    layer = oci.layer_from(tmp_path / "site", environment.IMAGE_SITE)

    ref, derived = oci.derive(f"registry:5000/sc-tools@{digest('b')}", layer,
                              comment="a node's Python")

    uploaded = registry.uploaded
    # 🔴 By digest, with no tag: nothing can be pointed at other content later.
    assert derived == uploaded["manifest-digest"] == uploaded["manifest-at"]
    assert ref == f"registry:5000/sc-tools@{derived}"
    manifest = uploaded["manifest"]
    assert manifest["layers"][:2] == registry.manifest["layers"]
    assert manifest["layers"][2]["digest"] == layer[1]
    assert uploaded[layer[1]] == layer[0]

    config = json.loads(uploaded[manifest["config"]["digest"]])
    assert config["rootfs"]["diff_ids"] == [digest("1"), digest("2"), layer[2]]
    assert config["history"][-1]["comment"] == "a node's Python"


def test_an_index_cannot_take_a_layer(registry, tmp_path):
    registry.replace("GET", f"http://registry:5000/v2/sc-tools/manifests/{digest('b')}",
                     json={"schemaVersion": 2, "manifests": [],
                           "mediaType": "application/vnd.oci.image.index.v1+json"})

    with pytest.raises(RuntimeError, match="multi-platform index"):
        oci.derive(f"registry:5000/sc-tools@{digest('b')}", (b"", digest("0"), digest("0")),
                   comment="")


###########################
# The install: pipbuild
###########################

def test_the_install_imports_nothing_but_the_standard_library():
    '''🔴 It runs under the base image's Python, whose SiliconCompiler may be a
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


def write_dist(site, name, version, requires=()):
    dist = os.path.join(site, f"{name}-{version}.dist-info")
    os.makedirs(dist)
    with open(os.path.join(dist, "METADATA"), "w") as f:
        f.write(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
        for requirement in requires:
            f.write(f"Requires-Dist: {requirement}\n")


def requirements(tmp_path, requirements="", constraints=""):
    (tmp_path / "req.txt").write_text(requirements)
    (tmp_path / "con.txt").write_text(constraints)
    return str(tmp_path / "req.txt"), str(tmp_path / "con.txt")


def test_the_layer_is_the_environments_own_site_packages(pip, tmp_path):
    '''🔴 A venv that sees this Python's packages, pip run from it: never
    `--target`, which ignores what is installed -- and every distribution
    this Python holds pinned, with the job's constraints after them.'''
    from importlib import metadata

    listed, limited = requirements(tmp_path, "a_pkg==1.0\n", "zz-not-here==3.1\n")

    result = pipbuild.install(listed, limited, str(tmp_path / "out" / "site"))

    (command, _, constraints), = pip.calls
    assert command[1:4] == ["-m", "pip", "install"]
    assert command[0] != sys.executable
    assert command[command.index("--only-binary") + 1] == ":all:"
    assert "--target" not in command
    assert f"pytest=={metadata.version('pytest')}" in constraints.splitlines()
    assert constraints.splitlines()[-1] == "zz-not-here==3.1"
    assert result["installed"] == [["a-pkg", "1.0"], ["b-ext", "1.0"]]
    # Only what was added: not the .pth that let it see this Python's.
    assert sorted(os.listdir(tmp_path / "out" / "site")) == [
        "a_pkg", "a_pkg-1.0.dist-info", "b_ext", "b_ext-1.0.dist-info"]
    assert sorted(os.listdir(tmp_path / "out")) == ["site"]     # the work dir is gone


def test_behind_the_proxy_pip_sees_no_configuration_but_the_proxy(pip, tmp_path,
                                                                  monkeypatch):
    monkeypatch.setenv("PIP_INDEX_URL", "https://pkgs.example.com/simple/")
    monkeypatch.setenv("HTTPS_PROXY", "http://somewhere-else:3128")
    listed, limited = requirements(tmp_path, "a_pkg==1.0\n")
    sockets = tempfile.mkdtemp(prefix="sc-t-")

    pipbuild.install(listed, limited, str(tmp_path / "site"),
                     proxy_socket=os.path.join(sockets, "proxy.sock"))

    (_, env, _), = pip.calls
    assert "PIP_INDEX_URL" not in env
    assert env["PIP_CONFIG_FILE"] == os.devnull
    assert env["HTTPS_PROXY"].startswith("http://127.0.0.1:")


###########################
# The install, for real: pip against a Python that holds cocotb
###########################

def wheel(where, name, version, requires=()):
    '''A pure wheel, as small as pip will take. Returns its path.'''
    import zipfile

    path = os.path.join(where, f"{name}-{version}-py3-none-any.whl")
    info = f"{name}-{version}.dist-info"
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n" + \
        "".join(f"Requires-Dist: {requirement}\n" for requirement in requires)
    files = {f"{name}/__init__.py": "",
             f"{info}/METADATA": metadata,
             f"{info}/WHEEL": "Wheel-Version: 1.0\nGenerator: test\n"
                              "Root-Is-Purelib: true\nTag: py3-none-any\n"}
    files[f"{info}/RECORD"] = "".join(f"{name},,\n" for name in [*files, f"{info}/RECORD"])
    with zipfile.ZipFile(path, "w") as archive:
        for member, body in files.items():
            archive.writestr(member, body)
    return path


def placeholder(where, filename):
    '''A file an index lists that pip never fetches: a source distribution
    under `--only-binary`, or a wheel for another platform.'''
    open(os.path.join(where, filename), "wb").close()


@pytest.fixture
def image_python(tmp_path):
    '''A Python that holds cocotb 2.0 -- in a venv of its own, as
    SiliconCompiler's images hold it -- and an index of wheels on disk: a
    cocotb 1.9, two testbench packages depending on cocotb, a cocotb-bus
    0.3.7 built for another platform only, two packages published only as
    source (one of them compiled elsewhere), and a release yanked from its
    line.'''
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
    wheel(index, "cocotb", "1.9")
    wheel(index, "cocotb_bus", "0.3.0", ["cocotb>=1.6"])
    placeholder(index, "cocotb_bus-0.3.7-cp27-cp27m-win32.whl")
    wheel(index, "pyuvm", "3.0.0", ["cocotb<2.0,>=1.6"])
    placeholder(index, "scfake_pure-1.0.tar.gz")
    placeholder(index, "scfake_fast-1.0.tar.gz")
    placeholder(index, "scfake_fast-1.0-cp27-cp27m-win32.whl")
    wheel(index, "scfake_old", "1.0")
    wheel(index, "scfake_old", "1.1")
    return image / "bin" / "python", simple_index(
        index, yanked={"scfake_old-1.1-py3-none-any.whl"})


def simple_index(flat, yanked=()):
    '''A PEP 503 index on disk over a directory of wheels: what
    `package_indexes` names, as a file: URL -- each of ``yanked`` marked so,
    as PEP 592 marks it.'''
    import re

    root = flat.parent / "simple"
    for name in sorted(os.listdir(flat)):
        project = re.sub(r"[-_.]+", "-", name.split("-", 1)[0]).lower()
        (root / project).mkdir(parents=True, exist_ok=True)
        os.replace(flat / name, root / project / name)
    for project in os.listdir(root):
        links = "".join(f'<a href="{name}"{' data-yanked=""' if name in yanked else ''}>'
                        f'{name}</a>\n'
                        for name in sorted(os.listdir(root / project)))
        (root / project / "index.html").write_text(f"<html><body>{links}</body></html>\n")
    return root.as_uri() + "/"


def build_in(image_python, tmp_path, text, constraints="", wheels=(), offline=False):
    '''One install in the image's Python -- from the index above, or, where
    ``offline``, from no index at all: image-only mode.'''
    python, index = image_python
    listed, limited = requirements(tmp_path, text, constraints)
    env = {key: value for key, value in os.environ.items() if not key.startswith("PIP_")}
    # Offline: the index above, named as a deployment names its indexes, and
    # pip from wherever this Python finds it.
    env.update(PYTHONPATH=os.path.dirname(os.path.dirname(
        pytest.importorskip("pip").__file__)))
    subprocess.run([str(python), pipbuild.__file__, "--requirements", listed,
                    "--constraints", limited, "--site", str(tmp_path / "out" / "site"),
                    "--result", str(tmp_path / "result.json"),
                    *([] if offline else ["--index-url", index]),
                    *[part for path in wheels for part in ("--wheel", str(path))]],
                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.loads((tmp_path / "result.json").read_text())


def test_a_package_depending_on_cocotb_does_not_bring_a_second_one(image_python, tmp_path):
    '''🔴 The failure this exists to prevent: the simulator loading one cocotb
    and SiliconCompiler's process another.'''
    result = build_in(image_python, tmp_path, "cocotb-bus==0.3.0\n")

    assert result["returncode"] == 0, result.get("tail")
    assert result["installed"] == [["cocotb-bus", "0.3.0"]]
    assert not (tmp_path / "out" / "site" / "cocotb").exists()


def test_a_pin_needing_another_cocotb_is_uninstallable(image_python, tmp_path):
    result = build_in(image_python, tmp_path, "pyuvm==3.0.0\n")

    assert result["returncode"] != 0
    assert "cocotb==2.0" in result["unresolved"] or any(
        "cocotb" in name for name in result["unresolved"]), result
    assert not result.get("absent")
    assert not (tmp_path / "out").joinpath("site").exists()


def test_a_listed_version_the_image_holds_another_of_stays_the_images(image_python, tmp_path):
    '''🔴 Never installed a second time: the listed version is ignored, and
    said.'''
    result = build_in(image_python, tmp_path, "cocotb==1.9\n")

    assert result["returncode"] == 0, result.get("tail")
    assert result["installed"] == []
    assert result["ignored"] == {"cocotb": ["1.9", "2.0"]}


def test_a_version_the_index_lists_only_others_of_is_sent_back(image_python, tmp_path):
    '''🔴 Absent is the exact version (surface D292): an index holding the
    name at other versions says nothing about this one, which may be another
    project's -- sent back for, and never taken from its release line.'''
    result = build_in(image_python, tmp_path, "cocotb-bus==0.3.5\n")

    assert result["returncode"] != 0
    assert result["absent"] == ["cocotb-bus"]
    assert not result.get("substituted")
    assert not (tmp_path / "out").joinpath("site").exists()


def test_a_version_with_no_file_for_this_platform_is_taken_from_its_line(image_python,
                                                                         tmp_path):
    '''§L's order: the exact version, else the newest in its line where that
    version is listed and nothing of it installs here -- that entry relaxed
    alone, and recorded.'''
    result = build_in(image_python, tmp_path, "cocotb-bus==0.3.7\n")

    assert result["returncode"] == 0, result.get("tail")
    assert result["installed"] == [["cocotb-bus", "0.3.0"]]
    assert result["substituted"] == {"cocotb-bus": ["0.3.7", "0.3.0"]}


def test_a_pure_package_with_only_a_source_is_sent_back(image_python, tmp_path):
    '''No source builds, and nothing in its line to take instead: the
    client's wheel of its installed copy answers it -- and what else was
    listed still installs, so one trip asks for it.'''
    result = build_in(image_python, tmp_path, "scfake-pure==1.0\ncocotb-bus==0.3.0\n")

    assert result["returncode"] != 0
    assert result["source_only"] == ["scfake-pure"]
    assert result["absent"] == []
    assert not (tmp_path / "out").joinpath("site").exists()


def test_a_compiled_package_with_only_a_source_here_is_uninstallable(image_python, tmp_path):
    '''🔴 Built for another platform, and no source builds: no wheel of the
    client's could run here either, so it is not sent back for one.'''
    result = build_in(image_python, tmp_path, "scfake-fast==1.0\n")

    assert result["returncode"] != 0
    assert result["only_source"] == ["scfake-fast"]
    assert not result.get("absent") and not result.get("source_only")


def test_a_yanked_release_is_never_installed_and_its_line_is_recorded(image_python,
                                                                      tmp_path):
    '''PEP 592: pip installs a yanked file when pinned with `==`, so it is
    held to its release line before pip runs, and the substitution said.'''
    result = build_in(image_python, tmp_path, "scfake-old==1.1\n")

    assert result["returncode"] == 0, result.get("tail")
    assert result["installed"] == [["scfake-old", "1.0"]]
    assert result["substituted"] == {"scfake-old": ["1.1", "1.0"]}
    assert result["yanked"] == ["scfake-old"]


def test_a_package_no_index_has_is_absent_not_uninstallable(image_python, tmp_path):
    '''What sends the job back for its wheel: no configured index has the
    project at all -- and the rest of the lists are still worked through, so
    one trip asks for every one.'''
    result = build_in(image_python, tmp_path,
                      "scfake-private==1.2.0\ncocotb-bus==0.3.0\nscfake-other==0.1.0\n")

    assert result["returncode"] != 0
    assert result["absent"] == ["scfake-other", "scfake-private"]
    assert not (tmp_path / "out").joinpath("site").exists()


def test_an_uploaded_wheel_is_installed_with_the_rest(image_python, tmp_path):
    '''Its dependencies come from the index, under the constraints; the
    wheel itself runs nothing.'''
    made = tmp_path / "made"
    made.mkdir()
    helper = wheel(made, "scfake_helper", "0.1.0", ["cocotb-bus>=0.3"])

    result = build_in(image_python, tmp_path, "", wheels=[helper])

    assert result["returncode"] == 0, result.get("tail")
    assert result["installed"] == [["cocotb-bus", "0.3.0"], ["scfake-helper", "0.1.0"]]


def test_with_no_index_what_the_image_lacks_is_sent_back_for(image_python, tmp_path):
    '''Image-only mode: a listed package the image lacks, and a wheel's own
    dependency it lacks, both go back for their wheels -- a dependency found
    only once its wheel arrives is a second trip, which is accepted.'''
    made = tmp_path / "made"
    made.mkdir()
    helper = wheel(made, "scfake_helper", "0.1.0", ["scfake-needed>=1.0"])

    result = build_in(image_python, tmp_path, "scfake-listed==1.0\n", wheels=[helper],
                      offline=True)

    assert result["returncode"] != 0
    assert result["absent"] == ["scfake-listed", "scfake-needed"]
    assert not (tmp_path / "out").joinpath("site").exists()


def test_with_no_index_a_wheel_against_the_images_pins_is_uninstallable(image_python,
                                                                        tmp_path):
    '''🔴 Image-only mode's `uninstallable`: a wheel that will not install,
    or that conflicts with what the image pins -- never one merely lacking a
    dependency.'''
    made = tmp_path / "made"
    made.mkdir()
    helper = wheel(made, "scfake_helper", "0.1.0", ["cocotb<2.0"])

    result = build_in(image_python, tmp_path, "", wheels=[helper], offline=True)

    assert result["returncode"] != 0
    assert not result.get("absent") and not result.get("source_only")
    assert any("cocotb" in name for name in result["unresolved"]), result


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
    # Every index has numpy, a dependency nothing pinned: what failed is the
    # version, never the name.
    monkeypatch.setattr(pipbuild, "on_index", lambda name, indexes, proxy=None: True)

    result = pipbuild.install(listed, limited, str(tmp_path / "site"))

    assert result["returncode"] == 1
    assert (result["unresolved"], result["network"]) == (named, network)
    assert not (tmp_path / "site").exists()


###########################
# The build container
###########################

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
    # 🔴 A network of its own: nothing in it but a loopback.
    assert [ns["type"] for ns in config["linux"]["namespaces"]].count("network") == 1
    assert config["process"]["args"] == ["python3", "x"]
    assert "SECRET=from-the-image-config" not in config["process"]["env"]
    assert "PATH=/venv/bin:/usr/bin:/bin" in config["process"]["env"]
    # 🔴 crun's, on the node; no container's process holds it (profile D39).
    assert config["process"]["capabilities"] == {"bounding": ["CAP_CHOWN"], "effective": []}
    assert BASE["mounts"][2]["destination"] == "/sc_server"        # the base untouched


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


def test_no_node_bundle_grants_net_admin(tmp_path):
    '''The node's own bundle, as staging writes it: whatever the image asked
    for, its process holds no NET_ADMIN.'''
    config = tmp_path / "config.json"
    config.write_text(json.dumps(BASE))

    images._prepare_spec(config, mounts=["/sc_server"])

    held = json.loads(config.read_text())["process"]["capabilities"]
    assert not any("CAP_NET_ADMIN" in caps for caps in held.values())


def test_a_build_pushes_one_layer_and_stages_a_bundle_on_the_base(
        tmp_path, base_bundle, pushed):
    run = container({"returncode": 0, "python": "cpython-312", "version": "3.12.3",
                     "platform": "linux-x86_64", "installed": [["numpy", "2.0.1"]]},
                    files={"numpy/__init__.py": "x = 1\n"})
    workspace, spec = workspace_for(tmp_path, base_bundle.root)

    result = envbuild.build(spec, workspace, run=run)

    assert result == {"ok": True, "ref": f"registry:5000/sc-tools@{digest('d')}",
                      "digest": digest("d"), "installed": [["numpy", "2.0.1"]],
                      "substituted": {}, "ignored": {}, "yanked": [],
                      "python": "cpython-312", "version": "3.12.3",
                      "platform": "linux-x86_64"}
    assert base_bundle.staged == [(spec["base_ref"], digest("b"), ["/sc_server"])]
    assert run.seen["req"] == ["constraints.txt", "pipbuild.py", "requirements.txt"]
    assert run.seen["path"] == "/venv/bin:/usr/bin:/bin"

    # 🔴 Its bundle is the base's root with the layer bound in -- no second
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


@pytest.mark.parametrize("source_builds", [False, True])
def test_the_build_installs_from_the_deployments_indexes_and_may_build_from_source(
        tmp_path, base_bundle, pushed, source_builds):
    '''🔴 The indexes are configuration and a job names none; and this
    container, with no mounts and no way out but the proxy, is the one place
    a source distribution's code may run -- where the operator's
    `python_source_builds` says it may, and nowhere by default.'''
    run = container({"returncode": 0, "python": "cpython-312", "version": "3.12.3",
                     "platform": "linux-x86_64", "installed": []})
    workspace, spec = workspace_for(tmp_path, base_bundle.root)
    spec["indexes"] = ["https://pypi.org/simple/", "https://extra.example/simple/"]
    if source_builds:
        spec["source_builds"] = True

    envbuild.build(spec, workspace, run=run)

    command = run.seen["command"]
    assert [command[at + 1] for at, part in enumerate(command) if part == "--index-url"] \
        == spec["indexes"]
    assert ("--allow-source" in command) is source_builds


def test_the_wheels_go_in_beside_the_lists(tmp_path, base_bundle, pushed):
    run = container({"returncode": 0, "python": "cpython-312", "version": "3.12.3",
                     "platform": "linux-x86_64", "installed": []})
    workspace, spec = workspace_for(tmp_path, base_bundle.root)
    (workspace / envbuild.WHEELS).mkdir()
    wheel(workspace / envbuild.WHEELS, "scfake_helper", "0.1.0")

    envbuild.build(spec, workspace, run=run)

    assert run.seen["req"] == ["constraints.txt", "pipbuild.py", "requirements.txt", "wheels"]
    command = run.seen["command"]
    assert command[command.index("--wheel") + 1] == \
        "/tmp/sc-req/wheels/scfake_helper-0.1.0-py3-none-any.whl"
    assert command[command.index("--constraints") + 1] == "/tmp/sc-req/constraints.txt"


def test_a_package_no_index_has_comes_back_as_absent(tmp_path, base_bundle, pushed):
    run = container({"returncode": 1, "absent": ["scfake-private"], "unresolved": [],
                     "python": "cpython-312", "platform": "linux-x86_64", "tail": ""})
    workspace, spec = workspace_for(tmp_path, base_bundle.root)

    result = envbuild.build(spec, workspace, run=run)

    assert (result["ok"], result["reason"], result["absent"]) == \
        (False, "absent", ["scfake-private"])
    assert pushed == []


@pytest.mark.parametrize("pip_result,reason", [
    ({"returncode": 1, "unresolved": ["numpy==9.9"], "network": False,
      "python": "cpython-312", "platform": "linux-x86_64", "tail": "no wheel"},
     "uninstallable"),
    # The index did not answer: nothing about the pins, so the server's failure.
    ({"returncode": 1, "unresolved": ["numpy==9.9"], "network": True,
      "python": "cpython-312", "platform": "linux-x86_64", "tail": "Retrying"}, "error"),
    (None, "error"),                        # the container never ran to the end
])
def test_a_build_that_fails_pushes_nothing(tmp_path, base_bundle, pushed, pip_result, reason):
    workspace, spec = workspace_for(tmp_path, base_bundle.root)

    result = envbuild.build(spec, workspace, run=container(pip_result))

    assert (result["ok"], result["reason"]) == (False, reason)
    assert pushed == []


def test_a_build_gone_without_a_result_is_given_up_on_after_a_grace(tmp_path):
    asked = []

    def alive():
        asked.append(1)
        return False

    assert envbuild.wait_for(tmp_path, 60, alive=alive, pause=0.01, grace=0.05) is None
    assert len(asked) == 1                    # the scheduler is asked once, not per look


def test_a_result_that_lands_after_its_job_ended_is_still_read(tmp_path):
    def alive():
        (tmp_path / envbuild.RESULT).write_text(json.dumps({"ok": True}))
        return False

    assert envbuild.wait_for(tmp_path, 60, alive=alive, pause=0.01, grace=5) == {"ok": True}


def test_the_result_is_written_whatever_happens(tmp_path):
    (tmp_path / envbuild.SPEC).write_text("not json")

    assert envbuild.main([str(tmp_path / envbuild.SPEC)]) == 0

    result = json.loads((tmp_path / envbuild.RESULT).read_text())
    assert (result["ok"], result["reason"]) == (False, "error")


###########################
# The proxy: the build's only way out
###########################

@pytest.fixture
def proxy():
    sockets = tempfile.mkdtemp(prefix="sc-t-")
    path = os.path.join(sockets, "proxy.sock")
    running = envbuild.Proxy(path, ["https://pypi.org/simple/",
                                    "https://files.pythonhosted.org/",
                                    "https://localhost/", "http://mirror.example.com/pypi/"])
    running.start()
    running.path = path
    yield running
    running.close()


def ask(proxy, request: bytes) -> bytes:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(proxy.path)
    client.sendall(request)
    answer = b""
    while b"\r\n\r\n" not in answer:
        chunk = client.recv(4096)
        if not chunk:
            break
        answer += chunk
    client.close()
    return answer


def test_what_the_proxy_admits(proxy):
    assert proxy.admits_connect("pypi.org", 443)
    assert proxy.admits_connect("files.pythonhosted.org", 443)
    assert not proxy.admits_connect("pypi.org", 8443)
    assert not proxy.admits_connect("evil.example.com", 443)
    assert proxy.admits_get("http://mirror.example.com/pypi/simple/numpy/")
    assert not proxy.admits_get("http://mirror.example.com/other/")
    assert not proxy.admits_get("https://pypi.org/simple/")      # that is CONNECT's


def test_a_host_off_the_allowlist_is_refused_and_named(proxy):
    answer = ask(proxy, b"CONNECT evil.example.com:443 HTTP/1.1\r\n\r\n")

    assert answer.startswith(b"HTTP/1.1 403")
    assert proxy.refused == ["evil.example.com"]


def test_an_allowlisted_name_that_is_not_public_is_never_connected(proxy):
    '''🔴 Whatever the list says: a name is whatever its owner's DNS answers.'''
    answer = ask(proxy, b"CONNECT localhost:443 HTTP/1.1\r\n\r\n")

    assert answer.startswith(b"HTTP/1.1 403") and b"non-public" in answer


def test_an_admitted_tunnel_carries_both_ways(proxy, monkeypatch):
    here, there = socket.socketpair()
    monkeypatch.setattr(envbuild, "_open_public", lambda host, port, **kwargs: there)

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(proxy.path)
    client.sendall(b"CONNECT pypi.org:443 HTTP/1.1\r\nHost: pypi.org\r\n\r\nhello")

    assert client.recv(4096).startswith(b"HTTP/1.1 200")
    here.settimeout(5)
    assert here.recv(5) == b"hello"
    here.sendall(b"world")
    assert client.recv(5) == b"world"
    client.close()
    here.close()


def test_an_admitted_get_is_sent_on_without_the_proxys_own_headers(proxy, monkeypatch):
    '''A plain http GET goes upstream in origin form, closing, with nothing
    meant for the proxy -- and the answer comes back as it was sent.'''
    here, there = socket.socketpair()
    monkeypatch.setattr(envbuild, "_open_public", lambda host, port, **kwargs: there)

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(proxy.path)
    client.sendall(b"GET http://mirror.example.com/pypi/simple/numpy/?a=1 HTTP/1.1\r\n"
                   b"Host: mirror.example.com\r\nProxy-Authorization: x\r\n"
                   b"Connection: keep-alive\r\nAccept: text/html\r\n\r\n")

    here.settimeout(5)
    sent = b""
    while b"\r\n\r\n" not in sent:
        sent += here.recv(4096)
    head = sent.decode().split("\r\n")
    assert head[0] == "GET /pypi/simple/numpy/?a=1 HTTP/1.1"
    assert "Accept: text/html" in head and "Connection: close" in head
    assert not any(line.lower().startswith(("proxy-", "connection: keep")) for line in head)

    here.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
    here.close()
    answer = b""
    while True:
        chunk = client.recv(4096)
        if not chunk:
            break
        answer += chunk
    client.close()
    assert answer == b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"


def test_anything_but_a_tunnel_or_a_plain_get_is_refused(proxy):
    assert ask(proxy, b"POST http://mirror.example.com/pypi/ HTTP/1.1\r\n\r\n") \
        .startswith(b"HTTP/1.1 405")


###########################
# The registry: derived images
###########################

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


def test_a_derived_image_is_never_resolved_to(store):
    '''🔴 Reached only by its derivation key, or one user's packages would
    place another user's node.'''
    images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest('e')}", digest("e"),
                            "k1", [("numpy", "2.0.1")], note="")

    assert [image["id"] for image in images.live_images(store)] == [store.base]
    assert "numpy" not in json.dumps(store.advertised_software(containers=True))


def test_a_derived_image_holds_its_base_and_what_it_installed(store):
    derived = images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest('e')}",
                                      digest("e"), "k1", [("numpy", "2.0.1")], note="")

    assert images.contents_of(store, [derived]) == {
        "python": {"numpy": ["2.0.1"], "siliconcompiler": ["0.38.0"]}, "tools": {}}
    assert images.derived_image(store, store.base, "k1")["id"] == derived


def test_a_second_build_of_the_same_key_is_the_first(store):
    '''A restart, or a second process: the first registered is what every
    later job reuses, whatever digest the second push got.'''
    first = images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest('e')}",
                                    digest("e"), "k1", [], note="")
    second = images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest('e')}",
                                     digest("f"), "k1", [], note="")

    assert first == second


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
    '''`drop-built`: every derived image holding it retired, and every host
    environment holding it removed -- at a version, or at any -- so the next
    job asking for that set builds it again. What holds anything else stays,
    and the retired rows stay answerable.'''
    from siliconcompiler.remote.server.jobs.pythonenv import ENVIRONMENTS
    from siliconcompiler.remote.server.software import registry

    images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest('e')}", digest("e"),
                            "k1", [("numpy", "2.0.1")], note="")
    other = images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest('f')}",
                                    digest("f"), "k2", [("scapy", "2.5.0")], note="")
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


def test_the_catalogue_keeps_what_the_server_built_apart(store):
    images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest('e')}", digest("e"),
                            "k1", [("numpy", "2.0.1")], note="")

    catalogue = images.catalogue(store)

    assert [image["id"] for image in catalogue["images"]] == [store.base]
    (built,) = catalogue["derived"]
    assert (built["base"], built["installed"]) == ("ghcr.io/x/sc:0.38.0", ["numpy==2.0.1"])


def test_a_bundle_lives_as_long_as_its_base(store, tmp_path):
    '''A derived bundle runs on its base's root filesystem: kept while the
    base is live, and both go when the base is retired and nothing runs.'''
    images.register_derived(store, store.base, f"ghcr.io/x/sc@{digest('e')}", digest("e"),
                            "k1", [], note="")
    root = tmp_path / "images"
    for letter in "ae":
        (images.bundle_path(root, digest(letter)) / "rootfs").mkdir(parents=True)

    images.sweep_bundles(root, store)
    assert sorted(path.name[:1] for path in root.iterdir()) == ["a", "e"]

    images.retire_image(store, store.base, store.actor)
    images.sweep_bundles(root, store)
    assert list(root.iterdir()) == []


###########################
# The tool's path
###########################

def test_a_node_in_a_derived_image_finds_its_layer(monkeypatch, tmp_path, gcd_design):
    '''Where the node runs the user's Python, and only there.'''
    from pytasks import RunsPython

    from siliconcompiler import Flowgraph, Project
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler.tools.builtin.nop import NOPTask

    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("tbflow")
    flow.node("sim", RunsPython())
    flow.node("other", NOPTask())
    project.set_flow(flow)

    def path(step):
        node = SchedulerNode(project, step, "0")
        with node.runtime():
            return node.task.get_runtime_environmental_variables().get("PYTHONPATH", "")

    layer = tmp_path / "layer"
    monkeypatch.setattr(environment, "IMAGE_SITE", str(layer))
    assert str(layer) not in path("sim").split(os.pathsep)     # every other image

    layer.mkdir()
    assert str(layer) in path("sim").split(os.pathsep)
    assert str(layer) not in path("other").split(os.pathsep)


###########################
# Configuration
###########################

def config_with(tmp_path, values):
    from siliconcompiler.remote.server.config import Config

    (tmp_path / "config.json").write_text(json.dumps(values))
    return Config.load(tmp_path)


def test_the_builder_is_what_offers_python_env_where_nodes_run_in_containers(tmp_path):
    assert "python.env" in config_with(
        tmp_path, {"containers": True, "env_builder": True})["features"]
    assert "python.env" not in config_with(tmp_path, {"containers": True})["features"]


def test_a_builder_needs_containers(tmp_path):
    with pytest.raises(ValueError, match="env_builder"):
        config_with(tmp_path, {"env_builder": True})


###########################
# While staging
###########################

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


BUILT = {"ok": True, "ref": f"ghcr.io/x/sc@{digest('e')}", "digest": digest("e"),
         "installed": [["numpy", "2.0.1"]], "python": "cpython-312",
         "version": "3.12.3", "platform": "linux-x86_64"}


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


def submitted(client, key, token, job_archive, project,
              packages=("numpy==2.0.1",), jobname=None):
    archive, upload_digest, size = job_archive(project)
    job = stage(client, key, token, archive, size, requested_versions=wants("0.38.0"),
                python_packages={"requirements": list(packages),
                                 "constraints": ["scapy==2.5.0"]},
                **({"jobname": jobname} if jobname else {}))
    response = submit(client, key, token, job["id"], upload_digest, size)
    assert response.status_code == 202, response.get_json()
    return response.get_json()


def row(server, job_id):
    return server.config["SC_STORE"].one("SELECT * FROM jobs WHERE id = ?", (job_id,))


def placed(server, job_id):
    return {(node["step"], node["index"]): node["image_id"]
            for node in server.config["SC_STORE"].all(
                "SELECT * FROM job_nodes WHERE job_id = ?", (job_id,))}


def test_a_node_running_the_users_python_runs_in_the_image_built_for_it(
        builder_server, client, key, token, job_archive, python_project):
    fake = builder(builder_server, lambda spec: BUILT)

    job = submitted(client, key, token, job_archive, python_project)

    assert job["state"] == "staging"              # nothing waits on a build
    assert until(lambda: fake.submitted)

    (build,) = fake.builds
    assert build["queue"] == "build"
    assert build["spec"]["base_ref"] == f"ghcr.io/x/sc@{digest('a')}"
    # 🔴 The server's own files, written from what parsed.
    assert build["file"].splitlines()[1:] == ["numpy==2.0.1"]
    assert build["constraints"].splitlines()[1:] == ["scapy==2.5.0"]
    assert "constrain" not in build["spec"]

    store = builder_server.config["SC_STORE"]
    derived = images.derived_image(store, placed(builder_server, job["id"])[("steptwo", "0")],
                                   build["spec"]["key"])
    assert placed(builder_server, job["id"]) == {
        ("stepone", "0"): derived["id"],
        ("steptwo", "0"): row(builder_server, job["id"])["image_id"]}

    from conftest import run_manifest
    project = run_manifest(fake.submitted[0][2])
    assert project.option.scheduler.get_queue(step="stepone", index="0") == \
        f"ghcr.io/x/sc@{digest('e')}"

    # What ran, including what was installed.
    from test_server_sources_flow import read
    assert read(client, key, token, job["id"])["resolved_versions"] == {
        "python": {"numpy": ["2.0.1"], "siliconcompiler": ["0.38.0"]}, "tools": {}}


def test_the_same_packages_on_the_same_image_are_built_once(
        builder_server, client, key, token, job_archive, python_project):
    fake = builder(builder_server, lambda spec: BUILT)

    first = submitted(client, key, token, job_archive, python_project)
    assert until(lambda: len(fake.submitted) == 1)
    second = submitted(client, key, token, job_archive, python_project)
    assert until(lambda: len(fake.submitted) == 2)

    assert len(fake.builds) == 1
    assert placed(builder_server, first["id"])[("stepone", "0")] == \
        placed(builder_server, second["id"])[("stepone", "0")]


def test_packages_that_will_not_install_reject_the_job(
        builder_server, client, key, token, job_archive, python_project):
    '''🔴 Never asked for as an upload: the package could carry binaries this
    server cannot run.'''
    fake = builder(builder_server, lambda spec: {
        "ok": False, "reason": "uninstallable", "unresolved": ["numpy==2.0.1"],
        "python": "cpython-312", "version": "3.12.3", "platform": "linux-x86_64",
        "refused": [], "tail": "ERROR: No matching distribution found for numpy==2.0.1"})

    job = submitted(client, key, token, job_archive, python_project)
    assert until(lambda: row(builder_server, job["id"])["state"] == "rejected")

    stored = row(builder_server, job["id"])
    assert stored["error_type"].endswith("/software-unavailable")
    reason = builder_server.config["SC_STORE"].one(
        "SELECT reason FROM job_state_transitions WHERE job_id = ? AND to_state = 'rejected'",
        (job["id"],))["reason"]
    assert "stepone/0's image" in reason and "numpy==2.0.1" in reason
    assert "cpython-312" in reason and "linux-x86_64" in reason
    assert fake.submitted == []
    assert stored["upload_sources"] is None       # nothing asked of the client


def test_a_package_no_index_has_sends_the_job_back_from_the_builder(
        builder_server, client, key, token, job_archive, python_project):
    fake = builder(builder_server, lambda spec: {
        "ok": False, "reason": "absent", "absent": ["scfake-private"],
        "python": "cpython-312", "version": "3.12.3", "platform": "linux-x86_64"})

    job = submitted(client, key, token, job_archive, python_project,
                    packages=("numpy==2.0.1", "scfake-private==1.0.0"))
    assert until(lambda: row(builder_server, job["id"])["state"] == "awaiting_input")

    stored = row(builder_server, job["id"])
    assert json.loads(stored["upload_sources"]) == [{"kind": "python", "name": "scfake-private"}]
    assert json.loads(stored["python_answered"]) == ["scfake-private"]
    assert fake.submitted == []


def test_the_jobs_wheels_are_handed_to_the_build(
        builder_server, client, key, token, job_archive, python_project, tmp_path):
    from test_environment import make_wheel

    fake = builder(builder_server, lambda spec: BUILT)
    helper = make_wheel(tmp_path, "scfake-helper", "0.1.0")
    archive, upload_digest, size = job_archive(python_project, extra={
        f"{environment.wheels_path()}/{os.path.basename(helper)}": open(helper, "rb").read()})
    job = stage(client, key, token, archive, size, requested_versions=wants("0.38.0"))
    assert submit(client, key, token, job["id"], upload_digest, size).status_code == 202

    assert until(lambda: fake.submitted)
    (build,) = fake.builds
    assert build["wheels"] == [os.path.basename(helper)]
    assert build["file"].splitlines()[1:] == []


def test_a_build_the_server_could_not_run_is_its_own_failure(
        builder_server, client, key, token, job_archive, python_project):
    builder(builder_server, lambda spec: {"ok": False, "reason": "error",
                                          "detail": "the registry did not answer"})

    job = submitted(client, key, token, job_archive, python_project)
    # This server's own failure: `failed`, never `rejected`.
    assert until(lambda: row(builder_server, job["id"])["state"] == "failed")

    assert row(builder_server, job["id"])["error_type"].endswith("/staging-failed")


def test_a_build_job_that_vanishes_is_not_waited_on(
        builder_server, client, key, token, job_archive, python_project):
    fake = builder(builder_server, lambda spec: None)
    fake.alive = False

    job = submitted(client, key, token, job_archive, python_project)

    assert until(lambda: row(builder_server, job["id"])["state"] == "failed")
    assert row(builder_server, job["id"])["error_type"].endswith("/staging-failed")
    assert fake.cancelled == ["build:1"]


@pytest.mark.threaded_staging
def test_a_job_cancelled_while_it_builds_stays_cancelled(
        builder_server, client, key, token, job_archive, python_project):
    '''🔴 Refusing it afterwards would rewrite what its owner did as something
    the server decided.'''
    from conftest import call

    fake = builder(builder_server, lambda spec: None)
    job = submitted(client, key, token, job_archive, python_project)
    assert until(lambda: fake.builds)

    call(client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token, json={})
    fake.alive = False
    assert until(lambda: not builder_server.config["SC_JOBS"]._preparing)

    assert row(builder_server, job["id"])["state"] == "cancelled"
    # 🔴 And the build itself stopped: nobody is waiting for it.
    assert fake.cancelled == ["build:1"]


@pytest.mark.parametrize("private_exact,target,public_only", [
    (True, "mirror.corp.example.com:443", False),     # an exact host: the operator's choice
    (True, "a.pkgs.example.org:443", True),           # a wildcard never is
    (False, "mirror.corp.example.com:443", True),     # nor any entry of a source list
])
def test_only_an_exact_index_host_may_be_a_private_address(
        monkeypatch, private_exact, target, public_only):
    '''Surface D172: an index entry naming one exact host is a mirror on the
    operator's own network; a wildcard, and every source-allowlist entry, keep
    the address rule.'''
    sockets = tempfile.mkdtemp(prefix="sc-t-")
    asked = []

    def opened(host, port, public_only=True):
        asked.append(public_only)
        return None

    monkeypatch.setattr(envbuild, "_open_public", opened)
    running = envbuild.Proxy(os.path.join(sockets, "proxy.sock"),
                             ["https://mirror.corp.example.com/simple/",
                              "https://*.pkgs.example.org/"],
                             private_exact_hosts=private_exact)
    running.start()
    running.path = os.path.join(sockets, "proxy.sock")
    try:
        ask(running, f"CONNECT {target} HTTP/1.1\r\n\r\n".encode())
    finally:
        running.close()

    assert asked == [public_only]
