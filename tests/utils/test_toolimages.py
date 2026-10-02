import json
import sys

import docker
import pytest

from pathlib import Path
from unittest import mock

from siliconcompiler.utils import toolimages


_PREFIX = "myorg/mylib_"


def _make_package(manifest=None, scripts=None):
    root = Path("pkg")
    root.mkdir()
    if manifest is not None:
        (root / "_tools.json").write_text(json.dumps(manifest))
    for path, text in (scripts or {}).items():
        script = root / path
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(text)
    return root.resolve()


def _package_images(fake_plugins, manifest=None, scripts=None):
    root = _make_package(manifest, scripts)
    fake_plugins("install", "toolscripts", lambda: root)
    return toolimages.get_tool_images(prefix=_PREFIX)


def _built(images):
    return {tool for tool, _ in images.get_built_tools()}


def test_no_package_reuses_everything(fake_plugins):
    sc = toolimages.get_tool_images()
    images = _package_images(fake_plugins)

    assert _built(images) == set()
    for tool, _ in sc._get_tools():
        assert images.is_reused(tool)
        assert images.tool_image(tool, True) == sc.tool_image(tool, True)
        assert images.tool_image(tool, True).startswith("ghcr.io/siliconcompiler/sc_")


def test_package_tool_builds_on_sc_dependency(fake_plugins):
    """A new tool is built under the prefix, on SiliconCompiler's image of what it needs."""
    sc = toolimages.get_tool_images()
    images = _package_images(
        fake_plugins,
        manifest={"newtool": {"git-url": "https://example.com/newtool.git",
                              "git-commit": "v0.1.0", "docker-depends": "yosys"}},
        scripts={"ubuntu24/install-newtool.sh": "#!/bin/bash\n"})

    assert _built(images) == {"newtool"}
    assert images.is_reused("yosys")
    assert images.tool_image("newtool", False) == \
        "ghcr.io/myorg/mylib_newtool:v0.1.0"
    assert images.tool_image("newtool", True).startswith(
        "ghcr.io/myorg/mylib_newtool:sc-check-")

    images.make_tool_docker("newtool", "out")
    context = Path("out") / "mylib_newtool"
    dockerfile = (context / "Dockerfile").read_text()
    assert f"FROM {sc.builder_image(False)}\n" in dockerfile
    assert f"COPY --from={sc.tool_image('yosys', True)} $SC_PREFIX $SC_PREFIX" in dockerfile
    assert (context / "install-newtool.sh").read_text() == "#!/bin/bash\n"
    with open(context / "_tools.json") as f:
        assert json.load(f)["newtool"]["git-commit"] == "v0.1.0"


@pytest.mark.parametrize("registry,expect", [
    ("registry.example.com", "registry.example.com/myorg/mylib_newtool:v0.1.0"),
    # Docker Hub: no registry in the name at all
    ("", "myorg/mylib_newtool:v0.1.0")])
def test_package_registry(fake_plugins, registry, expect):
    """A package's images go to its own registry, built on SiliconCompiler's from ghcr.io."""
    sc = toolimages.get_tool_images()
    root = _make_package(
        manifest={"newtool": {"git-commit": "v0.1.0", "docker-depends": "yosys"}},
        scripts={"ubuntu24/install-newtool.sh": "#!/bin/bash\n"})
    fake_plugins("install", "toolscripts", lambda: root)
    images = toolimages.get_tool_images(registry=registry, prefix=_PREFIX)

    assert images.tool_image("newtool", False) == expect
    assert images.builder_image(False) == sc.builder_image(False)
    assert images.builder_image(False).startswith("ghcr.io/siliconcompiler/sc_tool_builder:")
    assert images.tool_image("yosys", True) == sc.tool_image("yosys", True)

    images.make_tool_docker("newtool", "out")
    dockerfile = (Path("out") / "mylib_newtool" / "Dockerfile").read_text()
    assert f"FROM {sc.builder_image(False)}\n" in dockerfile
    assert f"COPY --from={sc.tool_image('yosys', True)} $SC_PREFIX" in dockerfile


def test_override_rebuilds_dependents(fake_plugins):
    """Moving a pin rebuilds that tool and everything built against it, and nothing else."""
    sc = toolimages.get_tool_images()
    images = _package_images(fake_plugins, manifest={"yosys": {"git-commit": "v0.70"}})

    assert _built(images) == {"yosys", "sby", "yosys-moosic", "wildebeest"}
    assert images.tool_image("yosys", False) == "ghcr.io/myorg/mylib_yosys:v0.70"
    assert images.tool_image("openroad", True) == sc.tool_image("openroad", True)

    images.make_tool_docker("wildebeest", "out")
    dockerfile = (Path("out") / "mylib_wildebeest" / "Dockerfile").read_text()
    assert f"COPY --from={images.tool_image('yosys', True)} $SC_PREFIX" in dockerfile
    with open(Path("out") / "mylib_wildebeest" / "_tools.json") as f:
        assert json.load(f)["yosys"]["git-commit"] == "v0.70"


def test_replaced_recipe_rebuilds(fake_plugins):
    """A package's script for one of SiliconCompiler's tools is a different image."""
    images = _package_images(fake_plugins, scripts={"ubuntu24/install-sv2v.sh": "#!/bin/bash\n"})

    assert _built(images) == {"sv2v"}


def test_new_build_input_rebuilds_dependency(fake_plugins):
    """
    A tool SiliconCompiler builds nothing against is pruned of its headers, so a package
    tool building against it gets one rebuilt with them kept.
    """
    images = _package_images(
        fake_plugins,
        manifest={"mytool": {"git-commit": "v1", "docker-depends": "opensta"}},
        scripts={"ubuntu24/install-mytool.sh": "#!/bin/bash\n"})

    assert _built(images) == {"mytool", "opensta"}

    images.make_tool_docker("opensta", "out")
    dockerfile = (Path("out") / "mylib_opensta" / "Dockerfile").read_text()
    assert "sc_strip_prefix_managed" not in dockerfile


def test_tools_image_without_package_is_sc_tools(fake_plugins):
    """A package that builds nothing runs in sc_tools itself."""
    sc = toolimages.get_tool_images()
    images = _package_images(fake_plugins)

    assert images.tools_image(False) == sc.tools_image(False)
    images.make_tools_docker("out")
    assert not Path("out").exists()


def test_tools_image_layers_added_tools(fake_plugins):
    """Tools added and none of SiliconCompiler's changed: sc_tools and one layer."""
    sc = toolimages.get_tool_images()
    images = _package_images(
        fake_plugins,
        manifest={"newtool": {"git-commit": "v0.1.0", "docker-depends": "yosys"}},
        scripts={"ubuntu24/install-newtool.sh": "#!/bin/bash\n"})

    assert not images.overrides_sc_tool()
    assert images.tools_image(False).startswith("ghcr.io/myorg/mylib_tools:")

    images.make_tools_docker("out")
    dockerfile = (Path("out") / "mylib_tools" / "Dockerfile").read_text()
    assert f"FROM {sc.tools_image(False)} AS assemble\n" in dockerfile
    assert f"\nFROM {sc.tools_image(False)}\n" in dockerfile
    assert f"COPY --from={images.tool_image('newtool', True)} $SC_PREFIX /sc_new" in dockerfile
    # The dependency arrives inside the tool's image, not on its own
    assert sc.tool_image("yosys", True) not in dockerfile


def test_tools_image_tag_moves_with_package_pin(fake_plugins):
    root = _make_package(
        manifest={"newtool": {"git-commit": "v0.1.0", "docker-depends": "yosys"}},
        scripts={"ubuntu24/install-newtool.sh": "#!/bin/bash\n"})
    fake_plugins("install", "toolscripts", lambda: root)
    before = toolimages.get_tool_images(prefix=_PREFIX).tools_image(False)

    (root / "_tools.json").write_text(json.dumps(
        {"newtool": {"git-commit": "v0.2.0", "docker-depends": "yosys"}}))
    assert toolimages.get_tool_images(prefix=_PREFIX).tools_image(False) != before


def test_tools_image_assembled_on_override(fake_plugins):
    """
    A changed pin is assembled from every tool's image, so nothing of the version it
    replaces survives underneath.
    """
    sc = toolimages.get_tool_images()
    images = _package_images(fake_plugins, manifest={"yosys": {"git-commit": "v0.70"}})

    assert images.overrides_sc_tool()
    images.make_tools_docker("out")
    dockerfile = (Path("out") / "mylib_tools" / "Dockerfile").read_text()
    assert "FROM ubuntu:24.04 AS assemble\n" in dockerfile
    assert sc.tools_image(False) not in dockerfile
    for tool in ("wildebeest", "sby", "yosys-moosic"):
        assert f"COPY --from={images.tool_image(tool, True)} $SC_PREFIX" in dockerfile
        assert f"COPY --from={sc.tool_image(tool, True)} " not in dockerfile
    assert f"COPY --from={sc.tool_image('openroad', True)} $SC_PREFIX" in dockerfile
    with open(Path("out") / "mylib_tools" / "_tools.json") as f:
        assert json.load(f)["yosys"]["git-commit"] == "v0.70"


def test_replaced_recipe_is_an_override(fake_plugins):
    images = _package_images(fake_plugins, scripts={"ubuntu24/install-sv2v.sh": "#!/bin/bash\n"})

    assert images.overrides_sc_tool()


def test_layered_image_skips_carried_dependency(fake_plugins):
    """
    A dependency rebuilt for a package tool to build on arrives inside that tool's
    image, and is not layered on its own with what the tool's image pruned.
    """
    images = _package_images(
        fake_plugins,
        manifest={"mytool": {"git-commit": "v1", "docker-depends": "opensta"}},
        scripts={"ubuntu24/install-mytool.sh": "#!/bin/bash\n"})

    assert _built(images) == {"mytool", "opensta"}
    assert images._get_layered_images() == [images.tool_image("mytool", True)]

    images.make_tools_docker("out")
    dockerfile = (Path("out") / "mylib_tools" / "Dockerfile").read_text()
    assert images.tool_image("opensta", True) not in dockerfile


def test_package_extra_files_are_the_packages(fake_plugins):
    """docker-extra-files in a package's manifest are relative to the package."""
    root = _make_package(
        manifest={"newtool": {"git-commit": "v1", "docker-extra-files": ["extra/patch.txt"]}},
        scripts={"ubuntu24/install-newtool.sh": "#!/bin/bash\n",
                 "extra/patch.txt": "first\n"})
    fake_plugins("install", "toolscripts", lambda: root)

    images = toolimages.get_tool_images(prefix=_PREFIX)
    before = images.tool_image("newtool", True)
    images.make_tool_docker("newtool", "out")
    assert (Path("out") / "mylib_newtool" / "patch.txt").read_text() == "first\n"

    (root / "extra" / "patch.txt").write_text("second\n")
    assert toolimages.get_tool_images(prefix=_PREFIX).tool_image("newtool", True) != before


def test_other_source_is_not_reused(fake_plugins):
    """The same tag of a fork is other code, so it gets an image of its own."""
    images = _package_images(
        fake_plugins, manifest={"yosys": {"git-url": "https://example.com/fork/yosys.git"}})

    assert _built(images) == {"yosys", "sby", "yosys-moosic", "wildebeest"}


def test_build_depends_pin_rebuilds(fake_plugins):
    """sby builds bitwuzla in-image, so moving bitwuzla's pin rebuilds sby."""
    sc = toolimages.get_tool_images()
    assert "bitwuzla" in (sc.get_field("sby", "build-depends") or [])

    images = _package_images(fake_plugins, manifest={"bitwuzla": {"git-commit": "9.9.9"}})

    assert "sby" in _built(images)
    assert images.tool_image("sby", True) != sc.tool_image("sby", True)


def test_build_stages(fake_plugins):
    """An image waits for every image it is built on that is built too, one stage each."""
    sc = toolimages.get_tool_images()
    assert sc.get_build_stage("yosys") == 1
    assert sc.get_build_stage("sby") == 2

    images = _package_images(
        fake_plugins,
        manifest={"yosys": {"git-commit": "v0.70"},
                  "newtool": {"git-commit": "v1", "docker-depends": "wildebeest"},
                  "addon": {"git-commit": "v1", "docker-depends": "icepack"}},
        scripts={"ubuntu24/install-newtool.sh": "#!/bin/bash\n",
                 "ubuntu24/install-addon.sh": "#!/bin/bash\n"})

    assert images.get_build_stage("yosys") == 1
    assert images.get_build_stage("wildebeest") == 2
    assert images.get_build_stage("newtool") == 3
    # Built on SiliconCompiler's image, which exists already: nextpnr builds on
    # icepack, so it keeps what addon needs. A tool nothing is built on yet, like
    # openroad, would be rebuilt to keep it, and addon would wait for that.
    assert images.is_reused("icepack")
    assert images.get_build_stage("addon") == 1


def test_main_json_tools_by_stage(monkeypatch, fake_plugins, capsys):
    _package_images(
        fake_plugins,
        manifest={"yosys": {"git-commit": "v0.70"},
                  "newtool": {"git-commit": "v1", "docker-depends": "wildebeest"}},
        scripts={"ubuntu24/install-newtool.sh": "#!/bin/bash\n"})

    def stage(n):
        assert _main(monkeypatch, "--image_prefix", _PREFIX, "--json_tools", "--reportall",
                     "--stage", str(n)) == 0
        out = json.loads(capsys.readouterr().out)
        return {entry["tool"] for entry in out.get("include", [])}

    assert stage(1) == {"yosys"}
    assert stage(2) == {"sby", "yosys-moosic", "wildebeest"}
    assert stage(3) == {"newtool"}
    assert stage(4) == set()


def test_check_image_not_found(monkeypatch):
    client = mock.MagicMock()
    client.images.get_registry_data.side_effect = docker.errors.NotFound("missing")
    client.images.get.side_effect = docker.errors.ImageNotFound("missing")
    monkeypatch.setattr(docker, "from_env", lambda: client)

    assert toolimages.check_image("ghcr.io/siliconcompiler/sc_yosys:sc-check-0") is False


def test_check_image_raises_on_denied(monkeypatch):
    """A registry that refuses the credentials is not a missing image."""
    response = mock.MagicMock(status_code=401)
    client = mock.MagicMock()
    client.images.get_registry_data.side_effect = docker.errors.APIError(
        "unauthorized", response=response)
    monkeypatch.setattr(docker, "from_env", lambda: client)

    with pytest.raises(docker.errors.APIError, match="^401 Client Error"):
        toolimages.check_image("ghcr.io/siliconcompiler/sc_yosys:sc-check-0")


def _main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["toolimages", *args])
    return toolimages.main()


def test_main_plan(monkeypatch, fake_plugins, capsys):
    images = _package_images(
        fake_plugins,
        manifest={"newtool": {"git-commit": "v0.1.0", "docker-depends": "yosys"}},
        scripts={"ubuntu24/install-newtool.sh": "#!/bin/bash\n"})

    assert _main(monkeypatch, "--image_prefix", _PREFIX, "--plan") == 0
    assert capsys.readouterr().out.splitlines() == [
        f"build  newtool          {images.tool_image('newtool', True)}",
        f"reuse  yosys            {images.tool_image('yosys', True)}",
        f"tools  layered          {images.tools_image(False)}"]


def test_main_json_tools_lists_only_built(monkeypatch, fake_plugins, capsys):
    _package_images(fake_plugins, manifest={"yosys": {"git-commit": "v0.70"}})

    assert _main(monkeypatch, "--image_prefix", _PREFIX, "--json_tools", "--reportall") == 0
    assert [entry["tool"] for entry in json.loads(capsys.readouterr().out)["include"]] == \
        ["yosys"]

    assert _main(monkeypatch, "--image_prefix", _PREFIX, "--json_tools", "--reportall",
                 "--stage", "2") == 0
    assert {entry["tool"] for entry in json.loads(capsys.readouterr().out)["include"]} == \
        {"sby", "yosys-moosic", "wildebeest"}


def test_main_generate_files_only_built(monkeypatch, fake_plugins):
    _package_images(fake_plugins, manifest={"yosys": {"git-commit": "v0.70"}})

    assert _main(monkeypatch, "--image_prefix", _PREFIX, "--generate_files",
                 "--output_dir", "out") == 0
    assert sorted(path.name for path in Path("out").iterdir()) == \
        ["mylib_sby", "mylib_tools", "mylib_wildebeest", "mylib_yosys", "mylib_yosys-moosic"]


def test_main_no_sc_runner_for_package(monkeypatch, fake_plugins, capsys):
    _package_images(fake_plugins)

    assert _main(monkeypatch, "--image_prefix", _PREFIX, "--tool", "runner") == 1
    assert "sc_runner is only built for SiliconCompiler itself" in capsys.readouterr().out


def test_main_ignores_packages_without_prefix(monkeypatch, fake_plugins, capsys):
    """SiliconCompiler's own images do not move because a package is installed."""
    sc = toolimages.get_tool_images()
    _package_images(fake_plugins, manifest={"yosys": {"git-commit": "v0.70"}})

    assert _main(monkeypatch, "--tool", "yosys", "--tool_as_hash_name") == 0
    assert capsys.readouterr().out.strip() == sc.tool_image("yosys", True)
