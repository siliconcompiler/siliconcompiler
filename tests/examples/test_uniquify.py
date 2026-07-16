# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.


def test_py_uniquify_setup():
    """The example enumerates + generates and registers the new filesets."""
    from uniquify import uniquify

    uq = uniquify.uniquify()

    assert set(uq.variants) == {"heartbeat", "prescaler"}
    assert set(uq.variants["heartbeat"]) == {
        "heartbeat__N8", "heartbeat__N24", "heartbeat__N48"}
    assert set(uq.variants["prescaler"]) == {"prescaler__W4", "prescaler__W8"}

    # The generated filesets are registered on the design.
    filesets = uq.design.getkeys("fileset")
    assert "rtl.wrapper" in filesets
    assert "rtl.heartbeat.wrapper" in filesets
    assert "rtl.hardened.heartbeat__N8" in filesets
    assert "rtl.hardened.prescaler__W8" in filesets


def test_py_uniquify_main(capsys):
    """The example's main() runs and prints variants + the generated wrapper."""
    from uniquify import uniquify

    uniquify.main()
    out = capsys.readouterr().out
    assert "'heartbeat' -> 3 variant(s)" in out
    assert "'prescaler' -> 2 variant(s)" in out
    assert "Generated wrapper for 'heartbeat'" in out
    assert "module heartbeat" in out
