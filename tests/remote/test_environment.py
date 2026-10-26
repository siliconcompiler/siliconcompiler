import importlib.metadata
import os
import zipfile

import pytest

from siliconcompiler.remote import environment


# A job's Python packages: the lists, held to one grammar at both ends, and the
# uploaded wheels, held to what an upload may carry -- installed while staging.

HELD = importlib.metadata.version("packaging")


def make_wheel(where, name, version, requires=(), files=None, tag="py3-none-any",
               wheel_tags=None, purelib=True):
    '''A wheel as small as pip takes, with what a test needs wrong in it.'''
    escaped = name.replace("-", "_")
    path = os.path.join(str(where), f"{escaped}-{version}-{tag}.whl")
    info = f"{escaped}-{version}.dist-info"
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n" + \
        "".join(f"Requires-Dist: {requirement}\n" for requirement in requires)
    members = dict(files if files is not None else {f"{escaped}/__init__.py": "VALUE = 1\n"})
    members[f"{info}/METADATA"] = metadata
    members[f"{info}/WHEEL"] = (
        "Wheel-Version: 1.0\nGenerator: test\n"
        f"Root-Is-Purelib: {'true' if purelib else 'false'}\n"
        + "".join(f"Tag: {one}\n" for one in (wheel_tags or [tag])))
    members[f"{info}/RECORD"] = "".join(f"{member},,\n" for member in
                                        [*members, f"{info}/RECORD"])
    with zipfile.ZipFile(path, "w") as archive:
        for member, body in members.items():
            archive.writestr(member, body)
    return path


def test_what_the_lists_take_and_how_the_builder_writes_them():
    packages = environment.parse({"requirements": ["numpy==1.26.4", "pyuvm==3.0.0"],
                                  "constraints": ["scapy==2.5.0", "cocotbext-eth==0.1.28"]})

    assert [str(pin) for pin in packages.requirements] == ["numpy==1.26.4", "pyuvm==3.0.0"]
    assert [str(pin) for pin in packages.constraints] == \
        ["scapy==2.5.0", "cocotbext-eth==0.1.28"]
    assert packages.names() == {"numpy", "pyuvm", "scapy", "cocotbext-eth"}
    assert environment.parse({}) == environment.Packages()
    # Every PEP 440 form in its canonical spelling.
    for version in ("2!1.0", "1.0rc1", "1.0.post2", "1.0.dev3", "2.1.0+cpu.1"):
        assert environment.parse_entry(f"x=={version}").version == version
    # Nothing the job wrote is handed to pip: the builder writes canonical names.
    assert environment.render(environment.parse({"requirements": ["PyUVM==3.0.0"]})
                              .requirements, header="here") == "# here\npyuvm==3.0.0\n"


@pytest.mark.parametrize("entry", [
    "numpy>=1.26",                              # a range
    "numpy==1.26.*",                            # a wildcard
    "numpy[extra]==1.26.4",                     # extras
    "numpy==1.26.4; python_version>'3'",        # a marker
    "numpy == 1.26.4",                          # whitespace
    "numpy===1.26.4",                           # arbitrary equality
    "numpy==v1.26.4",                           # not canonical
    "numpy==1.0-rc1",                           # not canonical
    "git+https://github.com/x/y",               # a VCS URL
    "./local",                                  # a path
    "-e .",                                     # an option
    "--index-url https://pkgs.example.com/",    # an index
    "",
    "numpy",
    7,
])
def test_everything_else_is_refused_naming_the_entry(entry):
    with pytest.raises(environment.PackagesError) as refused:
        environment.parse({"requirements": ["ok==1.0", entry]})

    assert refused.value.entry is not None


def test_the_bounds_and_each_name_once_across_both_lists_as_pep_503_sees_it():
    with pytest.raises(environment.PackagesError, match="named twice") as refused:
        environment.parse({"requirements": ["Foo_Bar==1.0"], "constraints": ["foo-bar==2.0"]})
    assert refused.value.entry == "foo-bar==2.0"
    with pytest.raises(environment.PackagesError, match="1001 entries"):
        environment.parse({"constraints": [f"p{n}==1.0" for n in range(1001)]})
    long = "x" * 100
    with pytest.raises(environment.PackagesError, match="bytes"):
        environment.parse({"constraints": [f"{long}{n}==1.0" for n in range(700)]})
    with pytest.raises(environment.PackagesError, match="no member 'extras'"):
        environment.parse({"requirements": [], "extras": []})
    with pytest.raises(environment.PackagesError, match="is an object"):
        environment.parse(["numpy==1.0"])


def test_a_pure_wheel_is_taken(tmp_path):
    path = make_wheel(tmp_path, "scfake-helper", "0.1.0")

    wheel = environment.check_wheel(path)
    assert wheel[:3] == ("scfake-helper", "0.1.0", os.path.basename(path))
    # What it holds, for the extraction limits: the module and its dist-info.
    assert wheel.members == 4 and wheel.expanded > 0
    assert environment.wheel_name(path) == "scfake-helper"
    # Only a TOP-LEVEL sitecustomize runs by itself; one in a package is its module.
    assert environment.check_wheel(make_wheel(
        tmp_path, "scfake", "1.0", files={"scfake/sitecustomize.py": ""})).name == "scfake"


@pytest.mark.parametrize("change,why", [
    (dict(tag="cp312-cp312-linux_x86_64"), "only a pure wheel"),
    (dict(files={"scfake/_c.so": "\x7fELF"}), "compiled file"),
    (dict(files={"scfake/_c.cpython-312-darwin.DYLIB": "x"}), "compiled file"),
    (dict(files={"../escape.py": ""}), "does not stay inside"),
    (dict(files={"/abs.py": ""}), "does not stay inside"),
    (dict(purelib=False), "Root-Is-Purelib"),
    (dict(wheel_tags=["py3-none-manylinux1_x86_64"]), "tags it for a platform"),
    # Nothing that runs by itself, and no dependency by URL.
    (dict(files={"scfake_hook.pth": "import os\n"}), "a .pth file"),
    (dict(files={"scfake/nested.pth": "import os\n"}), "a .pth file"),
    (dict(files={"sitecustomize.py": "print('hello')\n"}), "runs in any Python"),
    (dict(files={"usercustomize.py": "print('hello')\n"}), "runs in any Python"),
    (dict(files={"scfake-1.0.data/scripts/run": "#!/bin/sh\n"}), "installs outside"),
    (dict(requires=["scfake-bits @ https://example.test/bits.whl"]), "dependency by URL"),
    (dict(requires=["scfake-bits @ file:///home/someone/bits"]), "dependency by URL"),
])
def test_a_wheel_that_is_not_pure_or_is_malformed_is_refused(tmp_path, change, why):
    path = make_wheel(tmp_path, "scfake", "1.0", **change)

    with pytest.raises(environment.WheelError, match=why):
        environment.check_wheel(path)


def test_a_wheel_misnamed_not_a_zip_or_holding_a_link_is_refused(tmp_path):
    path = make_wheel(tmp_path, "scfake", "1.0")
    os.rename(path, tmp_path / "other-1.0-py3-none-any.whl")
    with pytest.raises(environment.WheelError, match="names another"):
        environment.check_wheel(tmp_path / "other-1.0-py3-none-any.whl")

    (tmp_path / "junk-1.0-py3-none-any.whl").write_bytes(b"not a zip")
    with pytest.raises(environment.WheelError, match="not a zip"):
        environment.check_wheel(tmp_path / "junk-1.0-py3-none-any.whl")

    with pytest.raises(environment.WheelError, match="not named as a wheel"):
        environment.check_wheel(tmp_path / "scfake.zip")

    path = make_wheel(tmp_path, "scfake", "1.0")
    with zipfile.ZipFile(path, "a") as archive:
        info = zipfile.ZipInfo("scfake/link")
        info.external_attr = 0o120777 << 16
        archive.writestr(info, "/etc/passwd")
    with pytest.raises(environment.WheelError, match="link"):
        environment.check_wheel(path)


def test_the_packages_go_on_the_path_of_a_node_running_the_users_python_only(
        python_project, monkeypatch, tmp_path):
    '''The host's site, then a derived image's layer, where each exists.'''
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler.utils.paths import jobdir

    site = os.path.join(jobdir(python_project), environment.site_path())
    layer = str(tmp_path / "layer")
    monkeypatch.setattr(environment, "IMAGE_SITE", layer)

    def path(step):
        node = SchedulerNode(python_project, step, "0")
        with node.runtime():
            return node.task.get_runtime_environmental_variables().get(
                "PYTHONPATH", "").split(os.pathsep)

    assert site not in path("stepone") and layer not in path("stepone")   # none installed
    os.makedirs(site)
    os.makedirs(layer)
    assert path("stepone")[:2] == [site, layer]
    assert site not in path("steptwo") and layer not in path("steptwo")
