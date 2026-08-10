from typing import Optional, Union

from siliconcompiler.tools.openroad import OpenROADTask
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter


class PEXBaseTask(OpenROADTask):
    '''
    Shared setup for the ``bench_wires``-based PEX/RCX tasks. Each reads only the
    tech LEF (the patterns are synthetic, so no standard cells, liberty, or SDCs
    are needed) and runs single-threaded.
    '''
    def setup(self):
        self.set_threads(1)

        super().setup()

        # Tech LEF (routing layers) via the fileset the APR flow uses.
        self.add_required_key(self.pdk, "pdk", "aprtechfileset", "openroad")
        for fileset in self.pdk.get("pdk", "aprtechfileset", "openroad"):
            self.add_required_key(self.pdk, "fileset", fileset, "file", "lef")


class PEXBenchTask(PEXBaseTask):
    '''
    Generate synthetic wire patterns (``bench_wires``) for deriving the initial
    per-layer parasitic estimate model.

    Reads only the tech LEF and writes a pattern verilog netlist and DEF, which
    ``PEXBenchExtractTask`` re-reads and extracts. The two are separate
    tasks because a same-process ``bench_wires`` followed by
    ``extract_parasitics`` fails (RCX-0487); the DEF must be re-read in a fresh
    process.

    This is the same bench used to seed the OpenRCX deck-generation flow
    (``ORXBenchTask``); the highest routing layer defaults to the top of
    the tech when ``max_layer`` is not set.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("max_layer", "str",
                           "maximum routing layer to generate the bench for; defaults to the "
                           "top routing layer in the tech")
        self.add_parameter("bench_length", "float<0.0..>", "length of the bench wires",
                           defvalue=100, units="um")

    def set_openroad_benchmaxlayer(self, layer: str,
                                   step: Optional[str] = None,
                                   index: Optional[Union[int, str]] = None):
        """Sets the maximum routing layer to generate the bench for."""
        self.set("var", "max_layer", layer, step=step, index=index)

    def set_openroad_benchlength(self, length: float,
                                 step: Optional[str] = None,
                                 index: Optional[Union[int, str]] = None):
        """Sets the length of the bench wires, in microns."""
        self.set("var", "bench_length", length, step=step, index=index)

    def task(self):
        return "pex_bench"

    def setup(self):
        super().setup()

        self.set_script("pex/sc_bench.tcl")

        if self.get("var", "max_layer"):
            self.add_required_key("var", "max_layer")
        self.add_required_key("var", "bench_length")

        self.add_output_file(ext="vg")
        self.add_output_file(ext="def.gz")


class PEXBenchExtractTask(PEXBaseTask):
    '''
    Extract the ``bench_wires`` patterns with the PDK's OpenRCX deck to derive
    the initial per-layer estimate model (resistance Ω/μm, capacitance F/μm).

    Walks the per-segment parasitics (the same method as the calibrate task) to
    produce one row per (corner, layer). These values seed
    :meth:`.OpenROADPDK.add_openroad_rclayer`; the design survey then refines
    them with :meth:`.OpenROADPDK.add_openroad_rccorrection`.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("pex_corners", "{str}",
                           "set of pex corners to derive the estimate model for")

    def task(self):
        return "pex_bench_extract"

    def setup(self):
        super().setup()

        self.set_script("pex/sc_pex_extract.tcl")

        # The script selects the deck with set_extraction_rules_file, which only
        # exists from 26Q3-23 (older releases took extract_parasitics
        # -ext_model_file); clobber the base >=24Q3 requirement.
        self.add_version(">=26Q3-23", clobber=True)

        if not self._has_openrcx():
            raise ValueError(
                "pex_bench_extract requires an OpenRCX extraction deck "
                "(pdk 'pexmodelfileset' / 'openrcx' file) to derive the estimate model.")

        # Characterize every corner the PDK ships an OpenRCX deck for. The bench
        # needs no timing scenario (it only reads the tech LEF and the deck), so
        # the initial model covers all deck corners, not just the ones a target
        # happens to wire into a timing scenario. A pexmodelfileset corner that
        # carries no openrcx file (only a Tcl estimate, say) cannot be benched, so
        # it is skipped rather than declared as a missing requirement.
        corners = [corner for corner in self.pdk.getkeys("pdk", "pexmodelfileset", "openroad")
                   if self._get_openrcx_filesets(corner)]
        self.set("var", "pex_corners", corners)
        self.add_required_key("var", "pex_corners")

        self.add_input_file(ext="def.gz")

        # OpenRCX deck for each corner (the golden reference).
        for corner in corners:
            self.add_required_key(self.pdk, "pdk", "pexmodelfileset", "openroad", corner)
            for fileset in self._get_openrcx_filesets(corner):
                self.add_required_key(self.pdk, "fileset", fileset, "file", "openrcx")

        # Single per-layer output across all corners (rows carry a corner column).
        self.add_output_file(ext="rclayer.csv")


class ORXBenchTask(PEXBenchTask):
    '''
    Builds the ``bench_wires`` pattern design used to characterize the OpenRCX
    extraction deck.

    Shares the bench script with ``PEXBenchTask`` - it writes the pattern
    verilog netlist and DEF for a third-party "golden" PEX tool and the OpenRCX
    extract step. The difference is the top layer: this deck-generation bench
    defaults ``max_layer`` to the PDK's ``rcx_maxlayer`` when set, because some
    PDKs cannot bench all the way to the top metal and the golden tool only needs
    the layers the deck characterizes. (The PEX estimate bench has no such limit
    and benches to the top routing layer.) An explicit ``max_layer`` still wins.
    '''
    def task(self):
        return "rcx_bench"

    def setup(self):
        super().setup()

        # Default the top layer to the PDK's rcx_maxlayer when the task var was
        # not set explicitly.
        if not self.get("var", "max_layer") and \
                self.pdk.get("tool", "openroad", "rcx_maxlayer"):
            self.set("var", "max_layer", self.pdk.get("tool", "openroad", "rcx_maxlayer"))
            self.add_required_key("var", "max_layer")
            self.add_required_key(self.pdk, "tool", "openroad", "rcx_maxlayer")


class ORXExtractTask(PEXBaseTask):
    '''
    Convert a third-party "golden" SPEF of the bench_wires patterns into a
    calibrated OpenRCX rules deck.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("corner", "str", "Parasitic corner to generate RCX file for")

    def set_openroad_rcxcorner(self, corner: str,
                               step: Optional[str] = None, index: Optional[Union[int, str]] = None):
        """
        Sets the parasitic corner to generate the RCX file for.

        Args:
            corner (str): The parasitic corner name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "corner", corner, step=step, index=index)

    def task(self):
        return "rcx_extract"

    @classmethod
    def make_docs(cls):
        from siliconcompiler import Flowgraph, Design, ASIC
        from siliconcompiler.scheduler import SchedulerNode
        from siliconcompiler.targets import freepdk45_demo
        design = Design("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = ASIC(design)
        proj.add_fileset("docs")
        freepdk45_demo(proj)
        flow = Flowgraph("docsflow")
        flow.node("<step>", cls(), index="<index>")
        proj.set_flow(flow)

        node = SchedulerNode(proj, "<step>", "<index>")
        # setup() requires the parasitic corner (it names the SPEF input and the
        # RCX output) and docs generation has no caller to set it, so seed a
        # placeholder in the same style as <step>/<index>. Flowgraph.node()
        # records only the task module, so the corner has to be set on the task
        # the project instantiated rather than on the instance passed to node()
        # -- hence the keypath set_openroad_rcxcorner() wraps.
        node.task.set("var", "corner", "<corner>")
        node.setup()
        return node.task

    def setup(self):
        super().setup()

        self.set_script("pex/sc_rcx_extract.tcl")

        self.add_required_key("var", "corner")

        corner = self.get("var", "corner")
        if not corner:
            # Without this the task would declare '<top>.None.spef' as its input
            # and fail on a missing file with no hint at the real cause.
            raise ValueError(
                "rcx_extract requires the parasitic corner to be set "
                "(see set_openroad_rcxcorner).")

        self.add_input_file(ext="def.gz")
        self.add_input_file(ext=f"{corner}.spef")
        self.add_output_file(ext=f"{corner}.rcx")


class CalibratePEXTask(APRTask, OpenROADSTAParameter):
    '''
    Calibrate OpenROAD's pre-route parasitic estimate against a golden OpenRCX
    extraction on a routed design.

    For each PEX corner this task extracts the design with the PDK's OpenRCX
    deck, walks the extracted parasitic segments to accumulate per-layer
    capacitance / resistance / length (the inputs used to calibrate
    :meth:`.OpenROADPDK.add_openroad_rccorrection`), and records a per-net estimate-vs-golden
    capacitance report so the estimation error can be scored before and after
    calibration. It is a terminal analysis node and produces no design views.

    The estimate honors the PDK's ``rccorrection`` like any node: the derivation
    survey runs against a PDK with no correction (uncorrected estimate -- and the
    derived factor is independent of it anyway, since it divides the golden sums
    by the stored ``rclayer``), while the ``--score`` step applies the derived
    correction to the whole flow and re-runs to measure the residual error.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("pex_corners", "{str}",
                           "set of pex corners to calibrate against")

    def task(self):
        return "calibrate_pex"

    def _warn_uncovered_pex_corners(self):
        """Warn about corners with an estimate model this survey won't calibrate.

        The bench characterizes every corner the PDK's OpenRCX deck ships (so the
        PDK's ``rclayer`` covers them all), but this survey only calibrates the
        corners wired into a timing scenario (``pex_corners``). Any modeled corner
        not covered here keeps the uncalibrated (typically pessimistic) estimate;
        surface that so the gap is not silent. Only the calibration task warns --
        emitting this from every place-and-route node would be far too noisy.
        """
        if not self.logger:
            return
        calibrating = set(self.get("var", "pex_corners"))
        modeled = {entry[0] for entry in self.pdk.get("tool", "openroad", "rclayer")
                   if entry[1] == "routing"}
        for corner in sorted(modeled - calibrating):
            self.logger.warning(
                f"PEX corner '{corner}' has an estimate model (rclayer) but is not "
                f"covered by this calibration (not in a timing scenario); it will "
                f"keep the uncalibrated estimate.")

    def _add_pnr_outputs(self):
        # Terminal analysis node: it emits only per-corner calibration CSVs and
        # no design views (odb/def/vg), so suppress the standard PNR outputs. The
        # library cell dependencies the preamble reads are declared separately by
        # APRTask._add_pnr_cell_keys and are unaffected by this override.
        pass

    def setup(self):
        super().setup()

        self.set_script("apr/sc_calibrate_pex.tcl")

        # Two newer APIs are used unconditionally: the multi-corner (mcmm) STA
        # scene API the segment walk relies on (26Q1-1133, see
        # sc_has_sta_mcmm_support) and set_extraction_rules_file (26Q3-23, which
        # replaced extract_parasitics -ext_model_file). Pin the later of the two
        # and clobber the base >=24Q3 requirement.
        self.add_version(">=26Q3-23", clobber=True)

        # Analysis node: no images.
        self.set("var", "ord_enable_images", False)

        if not self._has_openrcx():
            raise ValueError(
                "calibrate_pex requires an OpenRCX extraction deck "
                "(pdk 'pexmodelfileset' / 'openrcx' file) to build the golden reference.")

        # Every corner a timing scenario asks for. Corners are not dropped: a
        # scenario pointing at a corner with no deck has no golden reference, and
        # quietly calibrating the rest would emit a correction that silently
        # omits that corner, so name it instead.
        corners = sorted(set(self._get_pex_mapping().values()))
        if not corners:
            raise ValueError(
                "calibrate_pex found no timing scenario with a pex corner "
                "(constraint 'timing' scenario 'pexcorner').")
        missing = [corner for corner in corners if not self._get_openrcx_filesets(corner)]
        if missing:
            raise ValueError(
                f"calibrate_pex cannot calibrate pex corner(s) {', '.join(missing)}: the PDK "
                "ships no OpenRCX extraction deck (pdk 'pexmodelfileset' / 'openrcx' file) for "
                "them. Add a deck for these corners or point the timing scenarios at corners "
                "that have one.")
        self.set("var", "pex_corners", corners)
        self.add_required_key("var", "pex_corners")

        self._warn_uncovered_pex_corners()

        for corner in corners:
            self.add_required_key(self.pdk, "pdk", "pexmodelfileset", "openroad", corner)
            for fileset in self._get_openrcx_filesets(corner):
                self.add_required_key(self.pdk, "fileset", fileset, "file", "openrcx")

        # Per-layer golden sums across all corners (rows carry a pexcorner
        # column). Named 'perlayer' rather than 'rccorr' because these are the
        # raw measurement inputs, not the derived correction factors that the
        # calibration utility pools into <pdk>.rccorr.csv.
        self.add_output_file(ext="perlayer.csv")
        # Per-net estimate-vs-golden capacitance (used by the --score step).
        self.add_output_file(ext="nets.csv")
