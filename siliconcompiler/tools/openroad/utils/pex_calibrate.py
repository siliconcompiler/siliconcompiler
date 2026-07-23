# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
"""Calibrate OpenROAD's pre-route parasitic estimate for a PDK.

OpenROAD estimates net parasitics before routing from a per-layer R/C model (the
PDK ``rclayer`` values fed to ``set_layer_rc``). This utility derives that model,
and a correction on top of it, from the PDK's OpenRCX signoff deck in two phases:

1. **Initial model** (``bench_wires``, no design): synthetic wire patterns are
   extracted with the deck and walked into a per-layer R/C model - one per corner
   the PDK ships a deck for. These seed ``add_openroad_rclayer``.
2. **Correction factors** (a design survey): each design is routed, the real
   per-layer capacitance is measured, pooled across designs, and divided by the
   initial value to give one ``cap_factor`` per layer. These seed
   ``add_openroad_rccorrection``. The pooled ratio is a property of the process,
   not of any one design. Resistance needs no correction (bench resistance
   reproduces the deck), so only ``cap_factor`` is prescribed.

The tool writes ``<pdk>.rclayer.csv`` and ``<pdk>.rccorr.csv`` and prints the
paste-able PDK setup lines. A second run reuses the CSVs; ``--rerun`` recomputes.

Command line::

    python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo

Python::

    from siliconcompiler.tools.openroad.utils import pex_calibrate
    model, factors = pex_calibrate.calibrate("freepdk45_demo")
"""

import argparse
import csv
import importlib
import os
import sys

from siliconcompiler import ASIC, Design

from siliconcompiler.flows.openroad_pex import GeneratePEXEstimateFlow, PEXCalibrateFlow


# Dummy design for the bench phase. bench_wires builds its own pattern block, so
# the design is just a named container (no RTL); a dedicated name keeps the bench
# job out of a real design's build directory.
BENCH_DESIGN = "openroad_bench"


class PEXCalibrateError(Exception):
    """Raised when a calibration cannot be set up or completed."""


class GCD(Design):
    """Demo design: GCD (scgallery)."""
    def __init__(self):
        super().__init__("gcd")
        self.set_dataroot("scgallery", "git+https://github.com/siliconcompiler/scgallery.git",
                          tag="b672ee5cbd6d18e040422a011056a2ef5f6095c0")
        with self.active_dataroot("scgallery"), self.active_fileset("rtl"):
            self.set_topmodule("gcd")
            self.add_file("scgallery/designs/gcd/src/gcd.v")


class AES(Design):
    """Demo design: AES cipher (scgallery)."""
    def __init__(self):
        super().__init__("aes")
        self.set_dataroot("scgallery", "git+https://github.com/siliconcompiler/scgallery.git",
                          tag="b672ee5cbd6d18e040422a011056a2ef5f6095c0")
        with self.active_dataroot("scgallery"), self.active_fileset("rtl"):
            self.set_topmodule("aes_cipher_top")
            self.add_file([
                "scgallery/designs/aes/src/aes_cipher_top.v",
                "scgallery/designs/aes/src/aes_inv_cipher_top.v",
                "scgallery/designs/aes/src/aes_inv_sbox.v",
                "scgallery/designs/aes/src/aes_key_expand_128.v",
                "scgallery/designs/aes/src/aes_rcon.v",
                "scgallery/designs/aes/src/aes_sbox.v"])
            self.add_idir("scgallery/designs/aes/src")


class JPEG(Design):
    """Demo design: JPEG encoder (scgallery)."""
    def __init__(self):
        super().__init__("jpeg")
        self.set_dataroot("scgallery", "git+https://github.com/siliconcompiler/scgallery.git",
                          tag="b672ee5cbd6d18e040422a011056a2ef5f6095c0")
        with self.active_dataroot("scgallery"), self.active_fileset("rtl"):
            self.set_topmodule("jpeg_encoder")
            self.add_file([
                "scgallery/designs/jpeg/src/jpeg_encoder.v",
                "scgallery/designs/jpeg/src/jpeg_qnr.v",
                "scgallery/designs/jpeg/src/jpeg_rle.v",
                "scgallery/designs/jpeg/src/jpeg_rle1.v",
                "scgallery/designs/jpeg/src/jpeg_rzs.v",
                "scgallery/designs/jpeg/src/dct.v",
                "scgallery/designs/jpeg/src/dct_mac.v",
                "scgallery/designs/jpeg/src/dctu.v",
                "scgallery/designs/jpeg/src/dctub.v",
                "scgallery/designs/jpeg/src/div_su.v",
                "scgallery/designs/jpeg/src/div_uu.v",
                "scgallery/designs/jpeg/src/fdct.v",
                "scgallery/designs/jpeg/src/zigzag.v"])
            self.add_idir("scgallery/designs/jpeg/src/include")


class PicoRV32(Design):
    """Demo design: PicoRV32 RISC-V core (upstream YosysHQ)."""
    def __init__(self):
        super().__init__("picorv32")
        self.set_dataroot("picorv32", "git+https://github.com/YosysHQ/picorv32.git",
                          tag="c0acaebf0d50afc6e4d15ea9973b60f5f4d03c42")
        with self.active_dataroot("picorv32"), self.active_fileset("rtl"):
            self.set_topmodule("picorv32")
            self.add_file("picorv32.v")


# Bundled demo survey: name -> Design class. RTL is fetched (and cached under
# ``~/.sc``) from the pinned git source in each class on first use - nothing is
# vendored into the wheel and there is no scgallery package dependency. Replace
# with your own designs for a real calibration (see ``designs`` in ``calibrate``).
DEMO_DESIGNS = {
    "gcd": GCD,
    "picorv32": PicoRV32,
    "aes": AES,
    "jpeg": JPEG,
}


def resolve_target(target):
    """Resolve a target spec to the target setup callable.

    ``target`` is a callable (returned unchanged) or a string: a bare name under
    ``siliconcompiler.targets`` (``freepdk45_demo``), or an explicit
    ``module:function`` / ``module.function`` path.
    """
    if callable(target):
        return target
    if not isinstance(target, str):
        raise PEXCalibrateError(
            f"target must be a callable or string, got {type(target).__name__}")
    try:
        if ":" in target:
            modname, func = target.split(":", 1)
            return getattr(importlib.import_module(modname), func)
        if "." in target:
            modname, func = target.rsplit(".", 1)
            return getattr(importlib.import_module(modname), func)
        module = importlib.import_module(f"siliconcompiler.targets.{target}")
        return getattr(module, target)
    except (ImportError, AttributeError) as exc:
        raise PEXCalibrateError(f"could not resolve target '{target}': {exc}") from exc


def design_from_dir(directory, name=None, topmodule=None, rtl=None, sdc=None):
    """Build a :class:`~siliconcompiler.Design` from a directory of sources.

    By convention ``foo/`` holds ``foo.v`` (and optionally ``foo.sdc``) with top
    module ``foo``; override any of ``name``/``topmodule``/``rtl``/``sdc``.
    """
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        raise PEXCalibrateError(f"design directory not found: {directory}")
    name = name or os.path.basename(directory.rstrip(os.sep))
    topmodule = topmodule or name
    rtl = rtl if rtl is not None else [f"{name}.v"]
    if sdc is None:
        sdc = [f"{name}.sdc"] if os.path.isfile(os.path.join(directory, f"{name}.sdc")) else []

    design = Design(name)
    design.set_dataroot(name, directory + os.sep)
    design.set_topmodule(topmodule, fileset="rtl")
    for src in rtl:
        design.add_file(src, fileset="rtl", dataroot=name)
    for src in sdc:
        design.add_file(src, fileset="sdc", dataroot=name)
    return design


def _bench_design():
    """A minimal (fileless) dummy design for the bench phase."""
    design = Design(BENCH_DESIGN)
    design.set_topmodule(BENCH_DESIGN, fileset="rtl")
    return design


def _apply_target(target, design, filesets):
    """Build an ASIC project for ``design`` with ``target`` applied."""
    project = ASIC(design)
    project.add_fileset(filesets)
    resolve_target(target)(project)
    return project


def derive_pdk_name(target):
    """Return the PDK library name a target selects."""
    pdk = _apply_target(target, _bench_design(), "rtl").get("asic", "pdk")
    if not pdk:
        raise PEXCalibrateError(
            f"target '{target}' selects no PDK ([asic,pdk] is unset); a PEX calibration needs "
            "a PDK with an OpenRCX deck")
    return str(pdk)


##############################################################################
# rclayer model application / readback
##############################################################################
def apply_initial_rclayer(pdk, model):
    """Force the bench-derived values into the PDK's routing ``rclayer``.

    Only ``source="bench"`` routing entries are applied, so the PDK's rclayer
    becomes the bench estimate the correction factor divides by. Preserved
    entries (vias, uncharacterized layers) are already the PDK's own values.
    """
    override = {(corner, layer)
                for corner, layers in model.items()
                for layer, entry in layers.items()
                if entry["source"] == "bench" and entry["layertype"] == "routing"}
    kept = [e for e in pdk.get("tool", "openroad", "rclayer")
            if not (e[1] == "routing" and (e[0], e[2]) in override)]
    pdk.set("tool", "openroad", "rclayer", kept)
    for corner, layers in model.items():
        for layer, entry in layers.items():
            if entry["source"] == "bench" and entry["layertype"] == "routing":
                pdk.add_openroad_rclayer(corner, "routing", layer, entry["res"], entry["cap"])


def rclayer_model(pdk, corner):
    """Read the PDK's routing ``rclayer`` for ``corner`` into ``{layer: (res, cap)}``."""
    return {layer: (res, cap)
            for pex_corner, layertype, layer, res, cap in pdk.get("tool", "openroad", "rclayer")
            if pex_corner == corner and layertype == "routing"}


##############################################################################
# Phase 1: bench (initial per-layer model)
##############################################################################
def run_bench(target):
    """Run the bench flow and return the initial per-layer model.

    Runs :class:`.GeneratePEXEstimateFlow` on the dummy :data:`BENCH_DESIGN`,
    covering every corner the PDK ships a deck for. The model is
    ``{corner: {layer: entry}}`` where ``entry`` is ``{res, cap, layertype,
    source}``: bench-characterized layers carry ``source="bench"``; any PDK
    ``rclayer`` value the bench cannot reproduce (vias, and layers absent from
    the routing tech LEF such as a thick top metal) is preserved with
    ``source="pdk"``.
    """
    project = _apply_target(target, _bench_design(), "rtl")
    pdk_name = str(project.get("asic", "pdk"))
    project.option.set_jobname(pdk_name)
    project.option.set_nodashboard(True)
    project.set_flow(GeneratePEXEstimateFlow())
    project.run()

    csv_path = project.find_result(filetype="rclayer.csv", step="extract")
    if not csv_path:
        raise PEXCalibrateError(
            f"the bench flow (job '{pdk_name}') produced no rclayer.csv; check the "
            "'extract' step log")
    model = _read_bench_rclayer(csv_path)
    if not model:
        raise PEXCalibrateError(
            f"the bench flow characterized no layers ({csv_path} is empty); the OpenRCX "
            "deck extraction of the bench patterns produced no routing segments")
    _merge_preserved(model, project.get_library(pdk_name))
    return model


def _read_bench_rclayer(path):
    # Bench flow columns: corner,layer,cap_F_per_um,res_ohm_per_um,length_um,nseg
    model = {}
    with open(path, newline="") as fid:
        for row in csv.DictReader(fid):
            model.setdefault(row["corner"], {})[row["layer"]] = {
                "res": float(row["res_ohm_per_um"]),
                "cap": float(row["cap_F_per_um"]),
                "layertype": "routing",
                "source": "bench",
            }
    return model


def _merge_preserved(model, pdk):
    """Carry over PDK ``rclayer`` entries the bench did not characterize.

    Any PDK routing/via entry not already in the model is added verbatim with
    ``source="pdk"``: vias, layers missing from the routing tech LEF, and every
    entry of a corner the bench did not cover at all (a corner whose deck the
    bench could not extract, or that ships no OpenRCX deck). The emitted model is
    therefore a complete picture of the PDK's ``rclayer``, so pasting it can never
    silently drop a corner's estimate.
    """
    for corner, layertype, layer, res, cap in pdk.get("tool", "openroad", "rclayer"):
        corner_model = model.setdefault(corner, {})
        if layer in corner_model:
            continue
        corner_model[layer] = {
            "res": res, "cap": cap, "layertype": layertype, "source": "pdk"}


##############################################################################
# Phase 2: survey (correction factors)
##############################################################################
def run_survey(target, designs, initial_rclayer=None):
    """Route each design, measure golden per-layer parasitics, pool per corner.

    Returns ``(pooled, pdk)`` where ``pooled`` is ``{corner: {layer: [sum_len,
    sum_cap, sum_res, nseg]}}`` and ``pdk`` is the PDK object (with
    ``initial_rclayer`` forced in) used to compute factors.
    """
    if not designs:
        raise PEXCalibrateError("the calibration survey needs at least one design")

    perlayers = []
    pdk = None
    for design in designs:
        # An SDC is optional - timing constraints do not affect the routed
        # geometry we measure - so include it only when the design ships one.
        filesets = ["rtl"] + (["sdc"] if design.has_fileset("sdc") else [])
        project = _apply_target(target, design, filesets)
        pdk_name = str(project.get("asic", "pdk"))
        project.option.set_jobname(pdk_name)
        project.option.set_nodashboard(True)
        project.set_flow(PEXCalibrateFlow())
        # Walk only the graph feeding calibrate (skip e.g. synthesis.timing).
        project.option.add_to("calibrate", clobber=True)
        pdk = project.get_library(pdk_name)
        if initial_rclayer:
            apply_initial_rclayer(pdk, initial_rclayer)
        # Derive against an uncorrected estimate. The factor is independent of
        # any correction (it divides golden sums by the stored rclayer), but
        # clearing it keeps the routing identical to the '--score' before pass so
        # that pass is a cache hit.
        pdk.unset_openroad_rccorrection()
        project.run()

        csv_path = project.find_result(filetype="perlayer.csv", step="calibrate")
        if not csv_path:
            # The run() above raises on a failed node, so a missing CSV means the
            # calibrate node was skipped or wrote nothing. Silently pooling the
            # remaining designs would understate the survey, so stop instead.
            raise PEXCalibrateError(
                f"design '{design.name}' produced no perlayer.csv; check the 'calibrate' "
                "step log")
        perlayers.append(_read_perlayer(csv_path))
    return _pool_perlayer(perlayers), pdk


def _read_perlayer(path):
    # Calibrate node <top>.perlayer.csv columns:
    # pexcorner,layer,sum_length_um,sum_cap_F,sum_res_ohm,nseg
    out = {}
    with open(path, newline="") as fid:
        for row in csv.DictReader(fid):
            out.setdefault(row["pexcorner"], {})[row["layer"]] = [
                float(row["sum_length_um"]), float(row["sum_cap_F"]),
                float(row["sum_res_ohm"]), int(row["nseg"])]
    return out


def _pool_perlayer(perlayers):
    """Pool per-layer sums across designs, per corner (net/length weighted)."""
    pooled = {}
    for perlayer in perlayers:
        for corner, layers in perlayer.items():
            dst = pooled.setdefault(corner, {})
            for layer, sums in layers.items():
                acc = dst.setdefault(layer, [0.0, 0.0, 0.0, 0])
                for i, value in enumerate(sums):
                    acc[i] += value
    return pooled


def compute_factors(pooled_layers, rcmodel):
    """Per-layer factors for one corner: ``{layer: {cap_factor, res_factor, nseg}}``.

    Only layers present in both the pooled survey and the rclayer model are
    included.
    """
    factors = {}
    for layer, (hand_res, hand_cap) in rcmodel.items():
        if layer not in pooled_layers:
            continue
        sum_len, sum_cap, sum_res, nseg = pooled_layers[layer]
        if sum_len <= 0 or nseg == 0:
            continue
        golden_cap, golden_res = sum_cap / sum_len, sum_res / sum_len
        factors[layer] = {
            "cap_factor": golden_cap / hand_cap if hand_cap else None,
            "res_factor": golden_res / hand_res if hand_res else None,
            "nseg": nseg,
        }
    return factors


def compute_all_factors(pooled, pdk):
    """Per-corner factors from pooled survey sums and the PDK's rclayer model."""
    factors = {}
    for corner, layers in pooled.items():
        corner_factors = compute_factors(layers, rclayer_model(pdk, corner))
        if corner_factors:
            factors[corner] = corner_factors
    return factors


##############################################################################
# Scoring: quantify the per-net estimate error before vs after calibration
##############################################################################
def apply_factors(pdk, factors):
    """Apply calibration factors to the PDK as ``rccorrection`` (cap_factor only)."""
    pdk.unset_openroad_rccorrection()
    for corner, layers in factors.items():
        for layer, info in layers.items():
            cap = info.get("cap_factor")
            if cap is None:
                continue
            pdk.add_openroad_rccorrection(corner, layer, cap_factor=cap)


def _read_nets(path):
    """Read a calibrate ``<top>.nets.csv`` into (pexcorner, sigtype, golden, est) rows.

    ``est`` is ``None`` for a net the estimator produced no capacitance for (the
    Tcl writes that field empty); such rows are excluded from the score.
    """
    rows = []
    with open(path, newline="") as fid:
        for row in csv.DictReader(fid):
            est = row["est_cap_F"]
            rows.append((row["pexcorner"], row["sigtype"],
                         float(row["golden_cap_F"]), float(est) if est else None))
    return rows


def _score_errors(rows):
    """Per corner: relative ``|est-golden|/golden`` over signal/clock nets, golden>0.

    Nets with no estimate are skipped: counting them as 0 F would report a fake
    100% error rather than a missing measurement.
    """
    per = {}
    for corner, sigtype, golden, est in rows:
        if sigtype not in ("SIGNAL", "CLOCK") or golden <= 0 or est is None:
            continue
        per.setdefault(corner, []).append(abs(est - golden) / golden)
    return per


def _percentile(sorted_vals, frac):
    if not sorted_vals:
        return None
    return sorted_vals[min(len(sorted_vals) - 1, int(frac * len(sorted_vals)))]


def _score_summary(rows):
    """Per-corner error stats from raw nets rows: ``{median, mean, p90, nnets}``."""
    summary = {}
    for corner, errs in _score_errors(rows).items():
        errs.sort()
        summary[corner] = {
            "nnets": len(errs),
            "median": _percentile(errs, 0.5),
            "mean": sum(errs) / len(errs),
            "p90": _percentile(errs, 0.9),
        }
    return summary


def _survey_nets(target, designs, initial_rclayer, factors=None):
    """Route each design and read per-net golden-vs-estimate capacitance.

    When ``factors`` is given the calibration is applied to the whole flow (both
    the routing and the measured estimate reflect it); otherwise the estimate is
    uncorrected. Returns per-corner error stats (see :func:`_score_summary`).
    """
    scoring = factors is not None
    rows = []
    for design in designs:
        filesets = ["rtl"] + (["sdc"] if design.has_fileset("sdc") else [])
        project = _apply_target(target, design, filesets)
        pdk_name = str(project.get("asic", "pdk"))
        # A distinct jobname for the scored (corrected) run so it does not
        # clobber the uncorrected derive/before run's cached routing.
        project.option.set_jobname(pdk_name + ("_scored" if scoring else ""))
        project.option.set_nodashboard(True)
        project.set_flow(PEXCalibrateFlow())
        project.option.add_to("calibrate", clobber=True)
        pdk = project.get_library(pdk_name)
        if initial_rclayer:
            apply_initial_rclayer(pdk, initial_rclayer)
        # The whole flow (routing and the measured estimate) honors the PDK's
        # rccorrection: apply the derived factors for the corrected 'after' pass,
        # clear them for the uncorrected 'before' pass.
        if scoring:
            apply_factors(pdk, factors)
        else:
            pdk.unset_openroad_rccorrection()
        project.run()

        csv_path = project.find_result(filetype="nets.csv", step="calibrate")
        if csv_path:
            rows.extend(_read_nets(csv_path))
    return _score_summary(rows)


def print_score(before, after):
    """Print a per-corner before/after table of relative estimate error."""
    print("PEX estimate error vs golden -- |est - golden| / golden over "
          "signal/clock nets:", file=sys.stderr)
    header = f"{'corner':<12} {'metric':<7} {'before':>9} {'after':>9} {'change':>9}"
    print(header)
    print("-" * len(header))
    for corner in sorted(set(before) | set(after)):
        b = before.get(corner, {})
        a = after.get(corner, {})
        for metric in ("median", "p90", "mean"):
            bv, av = b.get(metric), a.get(metric)
            if bv is None or av is None:
                continue
            print(f"{corner:<12} {metric:<7} {bv * 100:>8.1f}% {av * 100:>8.1f}% "
                  f"{(av - bv) * 100:>+8.1f}%")


##############################################################################
# CSV data files
##############################################################################
def write_rclayer_csv(path, model):
    """Write the initial model to a CSV (``source`` = bench-characterized or pdk-preserved)."""
    with open(path, "w", newline="") as fid:
        writer = csv.writer(fid)
        writer.writerow(
            ["pexcorner", "layertype", "layer", "res_ohm_per_um", "cap_F_per_um", "source"])
        for corner, layers in model.items():
            for layer, entry in layers.items():
                cap = "" if entry["cap"] is None else f'{entry["cap"]:.6e}'
                writer.writerow([corner, entry["layertype"], layer,
                                 f'{entry["res"]:.6e}', cap, entry["source"]])


def read_rclayer_csv(path):
    """Read a ``<pdk>.rclayer.csv`` into ``{corner: {layer: entry}}``."""
    model = {}
    with open(path, newline="") as fid:
        for row in csv.DictReader(fid):
            cap = row["cap_F_per_um"]
            model.setdefault(row["pexcorner"], {})[row["layer"]] = {
                "res": float(row["res_ohm_per_um"]),
                "cap": float(cap) if cap else None,
                "layertype": row["layertype"],
                "source": row["source"],
            }
    return model


def write_rccorr_csv(path, factors):
    """Write correction factors to a CSV (layers with no cap_factor are skipped).

    ``res_factor`` is a diagnostic (it is expected to be ~1.0 and is never
    prescribed) and ``nseg`` records how well-sampled the layer was; both are
    written empty when unknown so they read back as ``None`` rather than as a
    fabricated value.
    """
    with open(path, "w", newline="") as fid:
        writer = csv.writer(fid)
        writer.writerow(["pexcorner", "layer", "cap_factor", "res_factor", "nseg"])
        for corner, layers in factors.items():
            for layer, info in layers.items():
                if info["cap_factor"] is None:
                    continue
                res_factor = info.get("res_factor")
                nseg = info.get("nseg")
                writer.writerow([
                    corner, layer, f'{info["cap_factor"]:.6f}',
                    "" if res_factor is None else f"{res_factor:.6f}",
                    "" if nseg is None else nseg])


def read_rccorr_csv(path):
    """Read a ``<pdk>.rccorr.csv`` into ``{corner: {layer: {cap_factor, res_factor, nseg}}}``.

    The shape matches :func:`compute_factors` so a cache hit and a fresh
    derivation return interchangeable data.
    """
    factors = {}
    with open(path, newline="") as fid:
        for row in csv.DictReader(fid):
            res_factor, nseg = row.get("res_factor"), row.get("nseg")
            factors.setdefault(row["pexcorner"], {})[row["layer"]] = {
                "cap_factor": float(row["cap_factor"]),
                "res_factor": float(res_factor) if res_factor else None,
                "nseg": int(nseg) if nseg else None,
            }
    return factors


##############################################################################
# PDK setup line rendering
##############################################################################
_PRESERVED_NOTE = "  # preserved from PDK (not characterized by OpenRCX)"


def format_rclayer_lines(model, factors=None):
    """Render the initial model as ``add_openroad_rclayer`` calls.

    PDK-preserved rows (vias and layers the bench did not characterize) are
    emitted verbatim with a note that they are not from OpenRCX. When ``factors``
    is given, a corner the survey did not calibrate is called out: pasting a raw
    bench value for such a corner replaces whatever the PDK prescribed with an
    *uncorrected* estimate, which is the one case where the output can be a step
    backwards.
    """
    lines = []
    for corner, layers in model.items():
        lines.append(f"# Initial PEX estimate model for corner '{corner}' (from bench_wires); "
                     f"res in ohm/um, cap in F/um")
        if factors is not None and not factors.get(corner):
            lines.append(f"# WARNING: corner '{corner}' was not covered by the calibration "
                         f"survey (no timing scenario uses it), so it gets NO cap_factor "
                         f"below. Review these values before replacing the PDK's own.")
        for layer, entry in layers.items():
            note = _PRESERVED_NOTE if entry["source"] == "pdk" else ""
            if entry["layertype"] == "via" or entry["cap"] is None:
                lines.append(f'pdk.add_openroad_rclayer("{corner}", "{entry["layertype"]}", '
                             f'"{layer}", {entry["res"]:.5g}){note}')
            else:
                lines.append(f'pdk.add_openroad_rclayer("{corner}", "routing", "{layer}", '
                             f'{entry["res"]:.5g}, {entry["cap"]:.5e}){note}')
    return "\n".join(lines)


def format_rccorr_lines(factors):
    """Render the correction factors as ``add_openroad_rccorrection`` calls."""
    lines = []
    for corner, layers in factors.items():
        lines.append(f"# Calibrated PEX corrections for corner '{corner}'")
        for layer, info in layers.items():
            if info["cap_factor"] is None:
                continue
            lines.append(f'pdk.add_openroad_rccorrection("{corner}", "{layer}", '
                         f'cap_factor={info["cap_factor"]:.4f})')
    return "\n".join(lines)


def print_calibration(model, factors):
    """Print the paste-able ``add_openroad_rclayer`` / ``rccorrection`` lines."""
    print(format_rclayer_lines(model, factors))
    print()
    print(format_rccorr_lines(factors))


##############################################################################
# Orchestration
##############################################################################
def calibrate(target, designs=None, outdir="pex", rerun=False, score=False):
    """Two-phase calibration: return ``(model, factors)``, write the CSVs, and
    print the paste-able PDK lines.

    Each phase reuses its CSV when present (a second run just reprints; a partial
    run finishes the missing phase). ``rerun=True`` recomputes both. ``designs``
    defaults to the bundled demo survey (:data:`DEMO_DESIGNS`). ``score=True``
    additionally re-routes the survey twice (uncorrected, then with the derived
    calibration applied to the whole flow) and prints the per-net estimate error
    before vs after -- a second, expensive pass that quantifies the improvement.

    Raises:
        PEXCalibrateError: if a phase completes without producing any values. A
            phase's CSV is only written once it holds real data, so a failed run
            never leaves an empty file behind for the next run to reuse.
    """
    if designs is not None and not designs:
        # None means "use the demo survey"; an explicitly empty list is a caller
        # bug that would otherwise silently produce an empty calibration.
        raise PEXCalibrateError(
            "designs is empty; pass None for the bundled demo survey or at least one design")

    pdk_name = derive_pdk_name(target)
    os.makedirs(outdir, exist_ok=True)
    rclayer_path = os.path.join(outdir, f"{pdk_name}.rclayer.csv")
    rccorr_path = os.path.join(outdir, f"{pdk_name}.rccorr.csv")

    if not rerun and os.path.isfile(rclayer_path):
        _log(f"Reusing initial model: {rclayer_path}")
        model = read_rclayer_csv(rclayer_path)
    else:
        _log("Phase 1: deriving initial estimate model from the OpenRCX deck")
        model = run_bench(target)
        write_rclayer_csv(rclayer_path, model)

    if not rerun and os.path.isfile(rccorr_path):
        # The cache is keyed on the PDK name only, so it cannot tell that the
        # survey changed. Say so loudly: silently returning the previous survey's
        # factors would look exactly like "the factors stopped moving".
        _log(f"Reusing correction factors: {rccorr_path}")
        _log("  NOTE: the cached survey is reused as-is; the 'designs' passed to this run "
             "were NOT surveyed. Use --rerun (or delete the file) after changing the survey.")
        factors = read_rccorr_csv(rccorr_path)
    else:
        if designs is None:
            designs = [design_cls() for design_cls in DEMO_DESIGNS.values()]
        _log(f"Phase 2: calibration survey over {len(designs)} design(s)")
        pooled, pdk = run_survey(target, designs, initial_rclayer=model)
        factors = compute_all_factors(pooled, pdk)
        if not factors:
            raise PEXCalibrateError(
                "the calibration survey produced no correction factors; no surveyed layer "
                "matched a corner in the initial rclayer model")
        write_rccorr_csv(rccorr_path, factors)

    _log(f"Data files in {outdir}: {pdk_name}.rclayer.csv, {pdk_name}.rccorr.csv")
    print_calibration(model, factors)

    if score:
        score_designs = designs if designs is not None else \
            [design_cls() for design_cls in DEMO_DESIGNS.values()]
        _log("Scoring: routing the survey uncorrected, then with the calibration "
             "applied, to quantify the per-net estimate improvement")
        before = _survey_nets(target, score_designs, model, factors=None)
        after = _survey_nets(target, score_designs, model, factors=factors)
        print_score(before, after)

    return model, factors


def _log(message):
    print(message, file=sys.stderr)


##############################################################################
# CLI
##############################################################################
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Calibrate OpenROAD's pre-route parasitic estimate for a PDK and emit the "
                    "add_openroad_rclayer / add_openroad_rccorrection lines for its setup.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  # calibrate FreePDK45 on the bundled demo survey (writes ./pex/<pdk>.*.csv)
  python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo

  # force a recompute
  python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo --rerun

  # also quantify the win: re-route uncorrected vs calibrated and print the
  # per-net estimate error before/after (extra runtime)
  python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo --score

  # use your own survey designs (each DIR holds <name>.v [and <name>.sdc])
  python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo \\
      --design designs/aes --design designs/jpeg""")
    parser.add_argument(
        "target",
        help="target setup function: a bare name under siliconcompiler.targets "
             "(e.g. 'freepdk45_demo'), or a 'module:function' / 'module.function' path")
    parser.add_argument(
        "-o", "--outdir", default="pex", metavar="DIR",
        help="directory for the <pdk>.rclayer.csv / <pdk>.rccorr.csv data files (default: ./pex)")
    parser.add_argument(
        "--design", action="append", metavar="DIR",
        help="survey design directory holding <name>.v (and optional <name>.sdc); repeatable. "
             "Defaults to the bundled demo suite.")
    parser.add_argument(
        "--rerun", action="store_true",
        help="recompute even if the data files already exist")
    parser.add_argument(
        "--score", action="store_true",
        help="after calibrating, re-route the survey with the calibration applied "
             "and report the per-net estimate error before vs after (extra runtime)")
    parser.add_argument(
        "--print", dest="print_only", action="store_true",
        help="only print the PDK setup lines from existing data files (never run)")
    args = parser.parse_args(argv)

    try:
        if args.print_only:
            pdk_name = derive_pdk_name(args.target)
            rclayer_path = os.path.join(args.outdir, f"{pdk_name}.rclayer.csv")
            rccorr_path = os.path.join(args.outdir, f"{pdk_name}.rccorr.csv")
            if not (os.path.isfile(rclayer_path) and os.path.isfile(rccorr_path)):
                parser.error(f"data files not found in {args.outdir}; run without --print first")
            print_calibration(read_rclayer_csv(rclayer_path), read_rccorr_csv(rccorr_path))
        else:
            designs = [design_from_dir(d) for d in args.design] if args.design else None
            # calibrate() prints the paste-able lines at the end.
            calibrate(args.target, designs=designs, outdir=args.outdir, rerun=args.rerun,
                      score=args.score)
    except PEXCalibrateError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
