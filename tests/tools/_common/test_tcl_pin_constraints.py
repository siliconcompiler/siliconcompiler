# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import pytest

# sc_collect_pin_constraints is pure Tcl driven by the global sc_cfg
# "constraint pin" dict plus a layer-lookup callback, so we exercise it through
# Python's embedded Tcl interpreter (tkinter.Tcl()). Skip when Tk is missing.
tkinter = pytest.importorskip("tkinter")


@pytest.fixture
def collect(tcl_interp):
    '''Returns a helper that runs sc_collect_pin_constraints against a set of
    pin constraints and returns the parsed result.

    pins maps a pin name to a {order, side, placement} dict. The layer callback
    maps every pin to a fixed layer unless ``layers`` overrides per pin.

    Returns a dict with:
      placement_pins -> list of pin names with explicit placement
      ordered        -> {side: {layer: [pins in order]}}
      warnings       -> list of emitted warning strings
    '''
    # sc_collect_pin_constraints relies on sc_cfg_get from sc_schema_access.
    interp = tcl_interp("sc_schema_access.tcl", "sc_pin_constraints.tcl")

    # Capturing warning sink and a wrapper that surfaces the upvar outputs.
    interp.eval(
        """
        proc _capture { msg } { lappend ::warnings $msg }
        proc _run { layer_func } {
            sc_collect_pin_constraints placement_pins ordered_pins $layer_func _capture
            set ::placement_pins $placement_pins
            set ::ordered_pins $ordered_pins
        }
        """
    )

    def _collect(pins, layers=None, default_layer="metal1"):
        interp.eval("set sc_cfg [dict create]")
        interp.eval("set ::warnings {}")
        for name, params in pins.items():
            for key in ("order", "side", "placement"):
                interp.call(
                    "dict", "set", "sc_cfg", "constraint", "pin",
                    name, key, params.get(key, ""))

        # Build the per-pin layer lookup as a Tcl proc.
        if layers:
            branches = " ".join(
                f'"{pin}" {{ return {layer} }}' for pin, layer in layers.items())
            interp.eval(
                f"proc _layer {{ pin }} {{ switch -- $pin {branches}"
                f" default {{ return {default_layer} }} }}")
        else:
            interp.eval(f"proc _layer {{ pin }} {{ return {default_layer} }}")

        interp.eval("_run _layer")

        placement_pins = [str(p) for p in interp.tk.splitlist(interp.eval("set ::placement_pins"))]
        warnings = [str(w) for w in interp.tk.splitlist(interp.eval("set ::warnings"))]

        ordered = {}
        sides = [str(s) for s in interp.tk.splitlist(interp.eval("dict keys $::ordered_pins"))]
        for side in sides:
            ordered[side] = {}
            side_layers = interp.tk.splitlist(
                interp.eval(f"dict keys [dict get $::ordered_pins {side}]"))
            for layer in side_layers:
                pins_in = interp.tk.splitlist(
                    interp.eval(f"dict get $::ordered_pins {side} {layer}"))
                ordered[side][str(layer)] = [str(p) for p in pins_in]

        return {"placement_pins": placement_pins, "ordered": ordered, "warnings": warnings}

    return _collect


def test_placement_pin_collected(collect):
    result = collect({
        "A": {"placement": "10 10"},
    })
    assert result["placement_pins"] == ["A"]
    assert result["ordered"] == {}
    assert result["warnings"] == []


def test_ordered_pins_sorted_by_order(collect):
    # Two pins on the same side; lower "order" comes first.
    result = collect({
        "B": {"side": "north", "order": "2"},
        "C": {"side": "north", "order": "1"},
    })
    assert result["placement_pins"] == []
    assert result["ordered"] == {"north": {"metal1": ["C", "B"]}}


def test_ordered_pins_grouped_by_layer(collect):
    result = collect(
        {
            "C": {"side": "north", "order": "1"},
            "B": {"side": "north", "order": "2"},
        },
        layers={"C": "m1", "B": "m2"},
    )
    assert result["ordered"] == {"north": {"m1": ["C"], "m2": ["B"]}}


def test_placement_with_order_warns(collect):
    result = collect({
        "E": {"side": "north", "order": "5", "placement": "20 20"},
    })
    # Still treated as a placement pin, but a warning is emitted.
    assert result["placement_pins"] == ["E"]
    assert len(result["warnings"]) == 1
    assert "placement specified" in result["warnings"][0]


def test_incomplete_pin_warns(collect):
    # No placement and missing side/order -> cannot be placed.
    result = collect({
        "D": {"side": "", "order": ""},
    })
    assert result["placement_pins"] == []
    assert result["ordered"] == {}
    assert len(result["warnings"]) == 1
    assert "enough information" in result["warnings"][0]


def test_mixed_constraints(collect):
    result = collect({
        "A": {"placement": "10 10"},
        "B": {"side": "north", "order": "2"},
        "C": {"side": "north", "order": "1"},
        "D": {"side": "", "order": ""},
        "S": {"side": "south", "order": "1"},
    })
    assert result["placement_pins"] == ["A"]
    assert result["ordered"] == {
        "north": {"metal1": ["C", "B"]},
        "south": {"metal1": ["S"]},
    }
    assert len(result["warnings"]) == 1
    assert "enough information" in result["warnings"][0]
