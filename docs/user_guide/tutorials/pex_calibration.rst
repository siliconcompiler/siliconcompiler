.. _pex_calibration:

Calibrating the parasitic estimate (PEX)
========================================

Before it routes a design, OpenROAD *estimates* every net's parasitics from a
small per-layer resistance/capacitance model -- the :term:`PDK` ``rclayer``
values fed to ``set_layer_rc``. That estimate drives every timing-repair
decision in :term:`place-and-route`, yet it is only a model, and a PDK ships
with it hand-tuned (or missing). This tutorial shows how to build that model,
and a correction on top of it, **directly from the PDK's OpenRCX
:term:`signoff` deck** using the ``pex_calibrate`` utility, so the
:term:`routing` layers no longer need hand tuning.
(Vias and any layer the bench cannot reproduce still come from whatever the PDK
already prescribes -- see the note below.)

.. admonition:: Who this is for / prerequisites
   :class: note

   This is an advanced, PDK-owner-facing tutorial. It assumes you are
   comfortable with parasitic extraction and signoff (OpenRCX decks,
   :term:`SPEF`), per-layer R/C models and ``set_layer_rc``, PDK process
   :term:`corners <corner>`, and the
   difference between global-route and detailed-route wirelength. You also need:

   * a target whose PDK ships an OpenRCX deck
     (``pdk.add_pexmodelfileset("openroad", ...)`` with an ``openrcx`` file --
     see :ref:`dev_pdks`),
   * a working OpenROAD :term:`ASIC` flow for that target (the survey routes real
     designs end to end), and
   * OpenROAD **26Q3-23 or newer**. Both extraction tasks select the deck with
     ``set_extraction_rules_file`` and the calibration walks parasitics through
     the multi-corner :term:`STA` scene API; the tasks declare this floor, so an older
     install is rejected up front rather than failing mid-run.

   If you only want to *use* a PDK that is already calibrated, you do not need
   this tutorial: the corrections are applied automatically once a PDK owner
   commits them.

The tool works in two phases:

#. **Initial model** -- ``bench_wires`` builds synthetic wire patterns from the
   tech, extracts them with the OpenRCX deck, and walks the per-segment
   parasitics into a per-layer resistance/capacitance model. One model is
   produced for every corner the PDK ships a deck for. These seed
   ``pdk.add_openroad_rclayer(...)``.
#. **Correction factors** -- a small survey of designs is routed; on each routed
   database the *real* per-layer capacitance is measured (again by extracting
   with the deck and walking segments), pooled across designs, and divided by
   the initial per-layer capacitance to give one ``cap_factor`` per layer. These
   seed ``pdk.add_openroad_rccorrection(...)``.

.. note::

   The correction is a *pooled ratio* of capacitance **per unit wire length**,
   summed over all nets of all survey designs. Because it is per-unit-length, it
   is far more a property of the **process** than of any one design: a bigger or
   busier design contributes more wire to the same ratio rather than shifting it.
   It is not literally survey-independent -- layers a design barely routes on
   contribute little, so lightly-used upper layers stay noisy -- so add designs
   until the factors on the layers you care about stop moving.

Quick start
-----------

Run the calibration on FreePDK45 using the bundled demo survey (``gcd``,
``picorv32``, ``aes`` and ``jpeg``):

.. code-block:: bash

   python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo -o pex

The demo designs are not vendored into the package; their RTL is fetched from
pinned git sources (the scgallery repo, and upstream for ``picorv32``) and
cached under ``~/.sc`` on first use - so the first run needs network access,
later runs do not. There is no dependency on the scgallery *package*.

The tool prints the lines to paste into a PDK setup:

.. code-block:: text

   # Initial PEX estimate model for corner 'typical' (from bench_wires); res in ohm/um, cap in F/um
   pdk.add_openroad_rclayer("typical", "routing", "metal2", 3.5714, 1.19382e-16)
   pdk.add_openroad_rclayer("typical", "routing", "metal3", 3.5714, 1.55445e-16)
   ...
   # Calibrated PEX corrections for corner 'typical'
   pdk.add_openroad_rccorrection("typical", "metal2", cap_factor=0.6960)
   pdk.add_openroad_rccorrection("typical", "metal3", cap_factor=0.6412)
   ...

and writes two CSV data files under ``-o`` (here ``./pex/``):

* ``freepdk45.rclayer.csv`` -- the initial per-layer model (one row per
  corner/layer).
* ``freepdk45.rccorr.csv`` -- the correction factors (one row per corner/layer).

The target argument is resolved to a target setup function, and the PDK name is
derived from it automatically -- you do not name the PDK or the corners. A bare
name is looked up under ``siliconcompiler.targets`` (``freepdk45_demo`` ->
``siliconcompiler.targets.freepdk45_demo``); a ``module:function`` or
``module.function`` path also works for a custom target.

.. note::

   The segment walk characterizes routing layers only, so anything the bench
   cannot reproduce -- **vias**, and any layer absent from the routing tech LEF
   (for example a thick top metal such as gf180's ``MetalTop``) -- is **carried
   over from the PDK's existing** ``rclayer`` **verbatim** and marked in both the
   printed output and the ``source`` column of ``<pdk>.rclayer.csv``::

     pdk.add_openroad_rclayer("typ", "via", "Via1", 5.3)  # preserved from PDK (not characterized by OpenRCX)

   So a layer the tool cannot measure is never dropped or zeroed; it keeps
   whatever the PDK already prescribed.

Reusing the results (no rerun)
------------------------------

The two CSV files *are* the calibration. Running the tool again with the files
already present just reprints the lines -- it does **not** rerun the flows:

.. code-block:: bash

   # instant: reads pex/*.csv and reprints the PDK lines
   python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo -o pex

   # or, explicitly print-only (errors if the files are missing)
   python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo -o pex --print

Each phase reuses its own file independently, so if only the initial model was
produced, a later run completes just the survey. To recompute from scratch:

.. code-block:: bash

   python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo -o pex --rerun

.. warning::

   The cache is keyed on the **PDK name only** -- it does not know which designs
   produced it. So after **changing the survey** (adding a design, editing one)
   you must pass ``--rerun``, or delete ``<pdk>.rccorr.csv``; otherwise the tool
   reuses the previous survey's factors and the numbers will look identical for
   the wrong reason. This matters most for the "add designs until the factors stop
   moving" workflow below. The tool prints a note whenever it reuses the file.

Applying the calibration
------------------------

Copy both blocks of emitted lines into your PDK setup (the PDK owner commits
them as policy). The ``add_openroad_rclayer`` lines are the estimate model; the
``add_openroad_rccorrection`` lines scale its capacitance toward signoff:

.. code-block:: python

   pdk.add_openroad_rclayer("typical", "routing", "metal2", 3.5714, 1.19382e-16)
   pdk.add_openroad_rccorrection("typical", "metal2", cap_factor=0.6960)

.. important::

   The two blocks are **one calibration** -- paste both, and replace the PDK's
   existing ``rclayer`` for the benched layers rather than adding to it. A
   ``cap_factor`` is the ratio of measured capacitance to *the bench value
   printed beside it*, so applying it on top of a different (for example
   hand-tuned) ``rclayer`` scales the wrong baseline and can be worse than no
   correction at all. Conversely, pasting the new ``rclayer`` without the
   corrections leaves the estimate at the uncorrected bench value. Re-run the
   tool whenever you change either block. Lines marked ``# preserved from PDK``
   are your existing values echoed back unchanged, so the emitted block is a
   complete picture of the PDK's ``rclayer`` -- if you would rather re-seed from
   scratch, ``pdk.unset_openroad_rclayer()`` clears it first.

Every place-and-route node then estimates parasitics through this corrected
model. A layer with no correction entry is left unchanged, so an empty
correction is identical to running without one; a correction naming a layer with
no ``rclayer`` entry is ignored, and OpenROAD warns about it so a misspelled
layer name is not silent. To run a node against the raw, uncalibrated estimate
without editing the PDK, call ``set_openroad_applypexcorrection(False)`` on the
place-and-route task. During the derivation survey the
PDK carries no correction, so the ``calibrate`` node measures the *uncorrected*
estimate the factor is derived from. The bench models every corner the deck
ships, but the survey only calibrates the corners wired into a timing
:term:`scenario`;
the calibration step warns about any modeled corner it does not cover, so a
corner that will keep the uncalibrated estimate is not a silent surprise.

Quantifying the improvement
---------------------------

The two CSVs *are* the calibration; the ``--score`` flag additionally
**measures** what they buy. It re-routes the survey twice -- once uncorrected,
once with the derived correction applied to the whole flow -- and reports the
per-net estimate error against the golden extraction, before and after:

.. code-block:: bash

   python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo --score

.. code-block:: text

   PEX estimate error vs golden -- |est - golden| / golden over signal/clock nets:
   corner       metric     before     after    change
   --------------------------------------------------
   typical      median      31.2%     12.4%    -18.8%
   typical      p90         58.0%     24.1%    -33.9%
   typical      mean        34.5%     15.0%    -19.5%

Each row is the per-net relative gap between OpenROAD's pre-route estimate and
the OpenRCX golden extraction, so a smaller *after* number means the calibrated
estimate tracks signoff more closely. The exact numbers depend on the survey
designs and the PDK (the illustrative values above are not a guarantee).

Two caveats on reading this table. It is an **in-sample** measurement: the same
designs that produced the factors are being scored, so it reports how well the
per-layer model fits the survey, not how it generalises -- hold a design out of
``--design`` and score it separately if you want that. And the *remaining* error
is not attributed by the tool; the wirelength difference described below is the
expected dominant contributor, but the table does not decompose it.

This is an opt-in diagnostic: it roughly doubles the survey work (an extra routed
pass per design), so it is for *validating* a calibration, not for every run.

Calibrating your own PDK
------------------------

Point the tool at your target and (optionally) your own survey designs. Corners
are discovered automatically: an initial model is produced for **every** corner
the PDK ships an OpenRCX deck for, and a correction factor for every corner your
target wires into a timing scenario (routing and timing need a scenario).

From the command line, each ``--design`` is a directory holding ``<name>.v``
(and optionally ``<name>.sdc``):

.. code-block:: bash

   python -m siliconcompiler.tools.openroad.utils.pex_calibrate my_pkg.targets:my_target \
       --design designs/aes --design designs/jpeg -o pex

From Python you pass :class:`.Design` objects, which lets you build the survey
designs however you like (multiple sources, include dirs, remote dataroots)
rather than relying on the ``<name>.v`` layout ``--design`` assumes. The survey
consumes the ``rtl`` fileset, plus ``sdc`` when the design has one:

.. code-block:: python

   from siliconcompiler import Design
   from siliconcompiler.tools.openroad.utils import pex_calibrate

   designs = [
       pex_calibrate.design_from_dir("designs/aes"),
       pex_calibrate.design_from_dir("designs/jpeg"),
   ]
   # calibrate() prints the paste-able PDK lines at the end and also returns
   # them as data for further processing.
   model, factors = pex_calibrate.calibrate("my_pkg.targets:my_target",
                                            designs=designs, outdir="pex")

Guidance for the survey:

* Add designs until the factors stop moving -- passing ``--rerun`` each time, or
  the cached factors come straight back (see the warning above). A handful of
  medium designs is usually enough. The upper metal layers need designs that
  actually route on them, or their factors stay noisy; the ``nseg`` column of
  ``<pdk>.rccorr.csv`` is the per-layer sample count to judge that by.
* Your PDK must ship an OpenRCX deck
  (``pdk.add_pexmodelfileset("openroad", ...)`` with an ``openrcx`` file) -- it
  is the golden reference for both phases. A deck is needed for every corner a
  timing scenario names: a scenario pointing at a corner with no deck fails
  setup rather than being quietly dropped from the calibration.

What gets calibrated (and what does not)
----------------------------------------

The estimate error has two independent parts:

#. **Per-layer capacitance model** -- capacitance per unit wire length on each
   layer. This is essentially a property of the process, and it is what the
   calibration corrects. The resistance already reproduces the deck, so only
   ``cap_factor`` is prescribed; the resistance ratio is written to the CSV as a
   ~1.0 sanity check and is never applied.
#. **Wirelength** -- the estimate uses the *global-route* wirelength, which
   differs from the final *detailed-route* wirelength. This gap is
   design-density-dependent (a sparse design and a dense one differ even in
   sign), so it is **not** something a single per-layer factor can fix, and the
   tool deliberately does not try. Chasing it would produce a different factor
   for every design -- which is not a calibration.

So the calibration makes the per-layer capacitance model match signoff; the
residual per-net total-capacitance gap is expected to be dominated by the
wirelength difference and is out of scope.

.. note::

   The correction is derived from, and scored against, the *global-route*
   estimate (``estimate_parasitics -global_routing`` on the routed database).
   Earlier place-and-route nodes -- global placement, repair, detailed placement
   -- estimate from placement instead (``-placement``), which uses a Steiner
   wirelength model. Both consume the same corrected ``set_layer_rc`` values, so
   both benefit from a better per-unit-length capacitance; only the wirelength
   half of the error differs between them, and that half is out of scope either
   way.

.. note::

   The survey routes **untimed** by default -- a design's ``sdc`` fileset is used
   only when it ships one, and no clock is required. Adding a clock (clock-tree
   synthesis, timing-driven placement, timing repair) does add wiring, but
   ``cap_factor`` is a *per-unit-length* quantity, so the extra wiring does not
   move it. Measured across this survey, constraining the designs shifts the
   pooled factor by well under 1% on the layers that carry essentially all the
   routing; the only larger movement is on the top one or two layers, which are
   too lightly used to calibrate reliably either way. Timing the survey is
   therefore not worth the extra runtime.

.. note::

   The demo survey (``gcd``, ``picorv32``, ``aes``, ``jpeg`` on FreePDK45) is a
   small illustrative sample, so the upper-layer factors are still somewhat noisy.
   On this PDK the ``cap_factor`` comes out below 1.0: the ``bench_wires``
   pattern set runs at tighter effective coupling than real routing does, so it
   over-predicts capacitance per unit length and the survey de-rates it. That
   direction is an observation about the pattern set, not a guarantee -- read the
   sign of your own factors rather than assuming it. The demo exists to exercise
   the flow end to end; a production calibration wants a representative sample of
   your own designs.

How it works
------------

* ``GeneratePEXEstimateFlow`` (``siliconcompiler.flows.openroad_pex``):
  ``bench`` (``bench_wires`` -> pattern DEF) -> ``extract`` (re-read the DEF in a
  fresh process, extract with the deck, walk segments -> per-layer R/C). It runs
  on a dummy ``openroad_bench`` design so the bench job stays out of a real
  design's build directory, and it needs no design of its own -- only the tech
  :term:`LEF` and the OpenRCX deck.
* ``PEXCalibrateFlow`` (``siliconcompiler.flows.openroad_pex``): the core ASIC
  flow (:term:`synthesis` through routing) with a ``calibrate`` node in place of
  the view/:term:`GDS <GDSII>` write. The ``calibrate`` node records the pre-route estimate per net,
  then extracts the golden reference (``extract_parasitics -max_res 0
  -no_merge_via_res``) and walks the per-segment parasitics into per-layer
  capacitance and length.

Walking single-layer segments is what makes the per-layer capacitance
measurable directly (``C = ΣC / Σlength`` per layer) -- a merged/reduced SPEF has
already thrown that per-segment layer detail away, which is why both flows
re-extract rather than reading a signoff SPEF.

.. seealso::

   ``examples/pex_calibration/calibrate.py`` -- a runnable thin wrapper around
   ``siliconcompiler.tools.openroad.utils.pex_calibrate.calibrate`` for the
   FreePDK45 demo.
