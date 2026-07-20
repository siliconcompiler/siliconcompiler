# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
"""Integrate generated wrappers + hardened variants into a SiliconCompiler flow.

This is the orchestration layer on top of
:mod:`~siliconcompiler.tools.slang.utils.uniquify` (enumeration) and
:mod:`~siliconcompiler.tools.slang.utils.wrapper` (code generation).

The :class:`Uniquified` class drives the whole lifecycle for one or more
parameterized modules of a design:

* **setup** (on construction) -- enumerate each module's parameterizations,
  generate the parameter-free variants + the parameterized wrappers (in memory),
  and add filesets to the design. The generated sources are written to disk only
  on the first :meth:`~Uniquified.build`/:meth:`~Uniquified.wireup` (or an
  explicit :meth:`~Uniquified.write`), so construction has no disk side effects.
  The filesets added are:

  - ``rtl.hardened.<variant>`` -- one per parameterization; the variant module
    (parameter-free) plus a dependency on the original module's RTL. This is the
    top hardened into a macro.
  - ``rtl.<module>.wrapper`` -- the parameterized wrapper that keeps the module's
    interface and dispatches to the matching variant.
  - ``rtl.wrapper`` -- an aggregate fileset depending on every per-module
    wrapper, so a parent can pull all wrappers at once.

* **build** -- harden the variants into :class:`~siliconcompiler.StdCellLibrary`
  macros, persisting each to disk so subsequent runs can skip or rebuild a
  subset. Hardening is *not* done at construction; call :meth:`~Uniquified.build`.

* **wireup** -- alias each module's RTL to its wrapper and inject the macros into
  an ASIC project (the lambdalib ``alias``/``add_asiclib`` pattern).

:func:`build_macro` (used by :meth:`~Uniquified.build`) packages a single
completed hardening run into a macro library, as the ``macro_reuse`` example does.
"""

from __future__ import annotations

import fnmatch
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

from siliconcompiler import ASIC, Design, Project, StdCellLibrary
from siliconcompiler.tools.slang.utils import wrapper
from siliconcompiler.tools.slang.utils.uniquify import (
    Parameterization, UniquifyError, build_compilation_from_design,
    enumerate_modules)


_GENERATED_DATAROOT = "uniquify-generated"


class Uniquified:
    """Uniquify parameterized modules of a design and integrate the results.

    .. note::
        **Beta feature.** This API is new and may change in a future release.

    Construction performs *setup* only -- enumeration, code generation (in
    memory) and fileset registration on ``design``. It writes nothing to disk and
    runs no EDA tools; the generated sources are materialized on the first
    :meth:`build`/:meth:`wireup` (or an explicit :meth:`write`). Call
    :meth:`build` to harden the variants and :meth:`wireup` to wire the wrappers
    and macros into a parent project.

    Unparameterized modules are supported too: one with no overridable parameters
    needs no wrapper, so it is hardened directly and blackboxed at :meth:`wireup`
    (the ``macro_reuse`` pattern). This means a single ``Uniquified`` can harden a
    mix of parameterized and unparameterized modules.

    Args:
        design (Design | Project): The context that instantiates the target
            modules (its elaboration determines the real parameterizations). If a
            :class:`~siliconcompiler.Project` is given, its design and selected
            filesets are used.
        modules (list): Names of the modules to uniquify/harden (parameterized or
            not).
        filesets (list, optional): Design filesets to elaborate. Defaults to the
            project's filesets, or ``["rtl"]`` for a bare design.
        libdir (str, optional): Root directory for uniquify's artifacts -- the
            persisted macro manifests at its root and the generated sources +
            hardening build tree under ``<libdir>/build``. Defaults to
            ``build/<design>/uniquify``.

    Raises:
        UniquifyError: If a requested module is not found among the filesets or is
            not instantiated anywhere in the design.
    """

    def __init__(self, design: Union[Design, Project], modules: Sequence[str],
                 filesets: Optional[Sequence[str]] = None,
                 libdir: Optional[str] = None) -> None:
        if isinstance(design, Project):
            self._design = design.design
            self._filesets = list(filesets) if filesets \
                else list(design.get("option", "fileset"))
        else:
            self._design = design
            self._filesets = list(filesets) if filesets else ["rtl"]

        self._modules = list(dict.fromkeys(modules))
        self._instance = wrapper.DEFAULT_INSTANCE_NAME
        # Everything lives under libdir: the persisted macro manifests at its root
        # and the generated sources + hardening build tree under <libdir>/build.
        self._libdir = os.path.abspath(
            libdir or os.path.join("build", str(self._design.name), "uniquify"))
        self._outdir = os.path.join(self._libdir, "build")

        # module -> (defining Design, its fileset)
        self._module_ref: Dict[str, Tuple[Design, str]] = self._resolve_modules()
        # module -> [Parameterization]
        self._combos: Dict[str, List[Parameterization]] = {}
        # module -> generated {"wrapper", "variants"} (in memory until write())
        self._generated: Dict[str, wrapper.GeneratedModule] = {}
        # variant name -> built/loaded macro
        self._macros: Dict[str, StdCellLibrary] = {}

        self._setup()

    # -- setup ---------------------------------------------------------------

    def _resolve_modules(self) -> Dict[str, Tuple[Design, str]]:
        """Map each target module to the dependency design/fileset that defines it."""
        pairs = self._design.get_fileset(self._filesets)
        resolved: Dict[str, Tuple[Design, str]] = {}
        for module in self._modules:
            for dep, fset in pairs:
                try:
                    top = dep.get_topmodule(fileset=fset)
                except Exception:
                    continue
                if top == module:
                    resolved[module] = (dep, fset)
                    break
            if module not in resolved:
                raise UniquifyError(
                    f"module {module!r} is not the top of any resolved fileset "
                    f"of {self._filesets}; each uniquified module must be its own "
                    f"design dependency")
        return resolved

    @staticmethod
    def _is_trivial(combos: List[Parameterization]) -> bool:
        """True if a module has no overridable parameters (one empty combo).

        Such a module is already parameter-free, so it needs no wrapper or
        generated variant: it is hardened directly and blackboxed at wireup, like
        the ``macro_reuse`` example.
        """
        return len(combos) == 1 and not combos[0].params

    def _module_of(self, variant: str) -> Optional[str]:
        """Return the source module a variant name belongs to (or None)."""
        for module, combos in self._combos.items():
            if any(c.name == variant for c in combos):
                return module
        return None

    @staticmethod
    def _wrapper_filename(module: str) -> str:
        return f"{module}.wrapper.v"

    @staticmethod
    def _variant_filename(variant: str) -> str:
        return f"{variant}.v"

    def _setup(self) -> None:
        """Enumerate, generate (in memory) and register filesets -- no disk I/O.

        The generated sources are held in ``self._generated`` and written to disk
        only when :meth:`write` is called (by :meth:`build`/:meth:`wireup`).
        """
        compilation = build_compilation_from_design(self._design, self._filesets)
        self._combos = enumerate_modules(compilation, self._modules)
        self._generated = {}
        for module in self._modules:
            combos = self._combos[module]
            if not combos:
                raise UniquifyError(
                    f"module {module!r} is not instantiated in "
                    f"{str(self._design.name)!r}; nothing to uniquify")
            if self._is_trivial(combos):
                # Unparameterized: no wrapper/variant sources -- hardened
                # directly and blackboxed at wireup.
                self._generated[module] = None
            else:
                self._generated[module] = wrapper.generate_uniquified(
                    compilation, module, combos=combos,
                    instance_name=self._instance)
        self._register_filesets()

    def _register_filesets(self) -> None:
        """Add the wrapper/variant filesets to the design (paths only)."""
        self._design.set_dataroot(_GENERATED_DATAROOT, self._outdir, clobber=True)
        for module in self._modules:
            module_design, module_fileset = self._module_ref[module]
            combos = self._combos[module]

            if self._generated[module] is None:
                # Unparameterized module: harden the original RTL directly. The
                # hardened fileset just re-points at the module's own (parameter-
                # free) top; no wrapper, no generated variant.
                combo = combos[0]
                with self._design.active_fileset(f"rtl.hardened.{combo.name}"):
                    self._design.set_topmodule(combo.name)
                    self._design.add_depfileset(module_design,
                                                depfileset=module_fileset)
                continue

            # Parameterized wrapper (keeps the module's name + interface).
            with self._design.active_fileset(f"rtl.{module}.wrapper"), \
                    self._design.active_dataroot(_GENERATED_DATAROOT):
                self._design.set_topmodule(module)
                self._design.add_file(self._wrapper_filename(module))

            # One parameter-free variant per combination, to harden.
            for combo in combos:
                with self._design.active_fileset(f"rtl.hardened.{combo.name}"), \
                        self._design.active_dataroot(_GENERATED_DATAROOT):
                    self._design.set_topmodule(combo.name)
                    self._design.add_file(self._variant_filename(combo.name))
                    # The variant is a baked copy of the module; depend on the
                    # original fileset for any submodules it instantiates.
                    self._design.add_depfileset(module_design,
                                                depfileset=module_fileset)

        # Aggregate wrapper fileset (pulls every generated per-module wrapper).
        wrapped = [m for m in self._modules if self._generated[m] is not None]
        if wrapped:
            with self._design.active_fileset("rtl.wrapper"):
                for module in wrapped:
                    self._design.add_depfileset(self._design,
                                                depfileset=f"rtl.{module}.wrapper")

    def _write_file(self, filename: str, text: str) -> None:
        with open(os.path.join(self._outdir, filename), "w") as fobj:
            fobj.write(text)

    def write(self) -> str:
        """Write the generated wrapper/variant sources to ``outdir`` (idempotent).

        Construction registers the filesets but does not touch disk; the sources
        are materialized here. :meth:`build` and :meth:`wireup` call this
        automatically -- call it directly only to materialize the sources without
        hardening (e.g. to lint the wrappers).

        Returns:
            str: The output directory the sources were written to.
        """
        os.makedirs(self._outdir, exist_ok=True)
        for module in self._modules:
            generated = self._generated[module]
            if generated is None:      # unparameterized: nothing to write
                continue
            self._write_file(self._wrapper_filename(module), generated["wrapper"])
            for combo in self._combos[module]:
                self._write_file(self._variant_filename(combo.name),
                                 generated["variants"][combo.name])
        return self._outdir

    # -- state ---------------------------------------------------------------

    @property
    def design(self) -> Design:
        """The design the generated filesets were added to."""
        return self._design

    @property
    def modules(self) -> List[str]:
        """The uniquified module names."""
        return list(self._modules)

    @property
    def variants(self) -> Dict[str, List[str]]:
        """Mapping of module name -> its variant (macro) names."""
        return {m: [c.name for c in combos] for m, combos in self._combos.items()}

    @property
    def variant_names(self) -> List[str]:
        """All variant (macro) names across every module."""
        return [c.name for combos in self._combos.values() for c in combos]

    @property
    def wrapper_filesets(self) -> Dict[str, str]:
        """Mapping of module name -> its wrapper fileset (plus 'all').

        Only parameterized modules have a wrapper; unparameterized modules are
        omitted (they are hardened and blackboxed directly, with no wrapper).
        """
        filesets = {m: f"rtl.{m}.wrapper" for m in self._modules
                    if self._generated[m] is not None}
        if filesets:
            filesets["all"] = "rtl.wrapper"
        return filesets

    @property
    def hardened_filesets(self) -> Dict[str, str]:
        """Mapping of variant name -> its hardening fileset."""
        return {v: f"rtl.hardened.{v}" for v in self.variant_names}

    @property
    def macros(self) -> Dict[str, StdCellLibrary]:
        """Variant name -> built (or loaded) macro; populated by :meth:`build`."""
        return dict(self._macros)

    @property
    def outdir(self) -> str:
        """Directory the generated wrapper/variant sources are written to."""
        return self._outdir

    @property
    def libdir(self) -> str:
        """Directory the variants are hardened under and their macros persisted."""
        return self._libdir

    def manifest(self, variant: str) -> str:
        """Path to the hardening run manifest for ``variant``.

        Points at the ``<design>.pkg.json`` written by :meth:`build` under
        :attr:`libdir`; load it (``ASIC.from_manifest``) to locate the variant's
        implementation results (netlist, SDC, parasitics).

        Args:
            variant (str): A variant (macro) name.

        Returns:
            str: Absolute path to the run's manifest.
        """
        name = str(self._design.name)
        return os.path.join(self._outdir, name, variant, f"{name}.pkg.json")

    def instance_path(self, variant: str, parent: Optional[str] = None) -> str:
        """Hierarchy path from a wrapper down to its hardened variant instance.

        The generated wrapper dispatches to each variant inside a ``generate``
        block labelled ``g_<variant>`` holding an instance named after the
        configured instance name, so within the wrapper the variant sits at
        ``g_<variant>/<instance>``. This is the scope needed to, e.g., map VCD
        switching activity onto the hardened netlist.

        Args:
            variant (str): A variant (macro) name.
            parent (str, optional): The wrapper's own instance path (e.g. a
                testbench DUT scope). If given, it is prepended to form an
                absolute path.

        Only parameterized modules have a wrapper generate block; calling this for
        a variant of an unparameterized module is an error (it is instantiated
        directly, with no ``g_<variant>`` level).

        Args:
            variant (str): A variant (macro) name.
            parent (str, optional): The wrapper's own instance path (e.g. a
                testbench DUT scope). If given, it is prepended to form an
                absolute path.

        Returns:
            str: ``g_<variant>/<instance>``, prefixed with ``parent`` if given.

        Raises:
            UniquifyError: If ``variant`` is unknown or belongs to an
                unparameterized (unwrapped) module.
        """
        module = self._module_of(variant)
        if module is None:
            raise UniquifyError(f"unknown variant {variant!r}")
        if self._generated[module] is None:
            raise UniquifyError(
                f"variant {variant!r} belongs to unparameterized module "
                f"{module!r}, which has no wrapper generate scope")
        path = f"g_{variant}/{self._instance}"
        return f"{parent}/{path}" if parent else path

    # -- build ---------------------------------------------------------------

    def _select(self, macros: Optional[Union[str, Sequence[str]]]) -> List[str]:
        variants = self.variant_names
        if macros is None:
            return variants
        patterns = [macros] if isinstance(macros, str) else list(macros)
        selected: List[str] = []
        for item in patterns:
            if item in self._combos:                       # a module name
                selected.extend(c.name for c in self._combos[item])
            else:                                          # a variant name / glob
                selected.extend(fnmatch.filter(variants, item))
        if not selected:
            raise UniquifyError(f"no variants match {macros!r}")
        return list(dict.fromkeys(selected))

    def _build_one(self, variant: str, target: Optional[Callable[[ASIC], None]],
                   rebuild: bool) -> StdCellLibrary:
        manifest = os.path.join(self._libdir, f"{variant}.json")
        if not rebuild and os.path.exists(manifest):
            return StdCellLibrary.from_manifest(filepath=manifest)

        if target is None:
            raise UniquifyError(
                f"no cached macro for {variant!r} and no `target` callback "
                f"given to harden it")

        project = ASIC(self._design)
        project.add_fileset(self.hardened_filesets[variant])
        target(project)
        # Harden under <libdir>/build (== self._outdir), one job per variant (they
        # share the design name), keeping the build tree separate from the
        # persisted macro manifests at the libdir root.
        project.option.set_builddir(self._outdir)
        project.option.set_jobname(variant)
        project.run()

        macro = build_macro(project, variant)
        macro.write_manifest(manifest)
        return macro

    def build(self, target: Optional[Callable[[ASIC], None]] = None,
              macros: Optional[Union[str, Sequence[str]]] = None,
              parallel: bool = False,
              rebuild: bool = False) -> Dict[str, StdCellLibrary]:
        """Harden the variants into macro libraries.

        Built macros are persisted under this instance's ``libdir`` so subsequent
        runs reuse them (unless ``rebuild`` is set).

        Args:
            target: SiliconCompiler target callback ``fn(project)`` that sets the
                PDK/flow/SDC on each variant's ASIC project (e.g.
                ``freepdk45_demo``). Required unless every selected macro already
                has a cached build.
            macros: Which macros (variants) to build. ``None`` builds all; a
                module name expands to its variants; anything else is matched as a
                variant name or glob (e.g. ``"mod__W*"``) -- useful for a rebuild.
            parallel: If True, harden the selected macros concurrently.
            rebuild: Force re-hardening even if a cached macro exists.

        Returns:
            dict: ``{variant: StdCellLibrary}`` for the selected macros.
        """
        self.write()  # materialize the generated sources on first use
        os.makedirs(self._libdir, exist_ok=True)
        selected = self._select(macros)

        results: Dict[str, StdCellLibrary] = {}
        if parallel and len(selected) > 1:
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._build_one, v, target, rebuild): v
                    for v in selected}
                for future in futures:
                    results[futures[future]] = future.result()
        else:
            for variant in selected:
                results[variant] = self._build_one(variant, target, rebuild)

        self._macros.update(results)
        return results

    def load_macros(self) -> Dict[str, StdCellLibrary]:
        """Load previously built macros from :attr:`libdir` into state.

        Reuses macros persisted by an earlier :meth:`build` without re-hardening.

        Returns:
            dict: ``{variant: StdCellLibrary}`` for every macro found.
        """
        for variant in self.variant_names:
            manifest = os.path.join(self._libdir, f"{variant}.json")
            if os.path.exists(manifest):
                self._macros[variant] = StdCellLibrary.from_manifest(filepath=manifest)
        return dict(self._macros)

    # -- integration ---------------------------------------------------------

    def wireup(self, project: ASIC, require_all: bool = True) -> ASIC:
        """Wire the wrappers and macros into a parent ASIC project.

        For a parameterized module, aliases its RTL to the generated wrapper (so
        synthesis elaborates the dispatch). For an unparameterized module,
        blackboxes it (aliases to nothing) so the injected macro provides it. In
        both cases the hardened macros are added via ``add_asiclib``.

        Args:
            project: The parent ASIC project instantiating the modules.
            require_all: If True (default), raise unless every variant has a
                built/loaded macro -- an unhardened but used variant would make
                the wrapper's ``$error`` branch fire at elaboration.

        Returns:
            ASIC: The same ``project``, wired up.

        Raises:
            UniquifyError: If ``require_all`` and some variants have no macro.
        """
        missing = [v for v in self.variant_names if v not in self._macros]
        if missing and require_all:
            raise UniquifyError(
                f"no macro for variant(s) {missing}; run build() first "
                f"(or pass require_all=False)")

        # The parent synthesizes the wrappers, so ensure they exist on disk.
        self.write()

        for module in self._modules:
            module_design, module_fileset = self._module_ref[module]
            if self._generated[module] is not None:
                # Parameterized: elaborate the wrapper's dispatch.
                project.add_alias(module_design, module_fileset,
                                  self._design, f"rtl.{module}.wrapper")
            else:
                # Unparameterized: blackbox it; the macro provides the module.
                project.add_alias(module_design, module_fileset, None, None)

        for macro in self._macros.values():
            project.add_asiclib(macro)

        return project


def build_macro(project: ASIC, name: str) -> StdCellLibrary:
    """Package a completed variant hardening run into a ``StdCellLibrary``.

    Bundles the results of ``project`` (a finished ASIC run of one variant) into a
    macro library, following the ``macro_reuse`` example. Beyond the physical
    (LEF/GDS) and per-corner Liberty views a reusable macro needs, it also carries
    the implementation's gate-level netlist and constraints so downstream flows
    (gate-level simulation, timing/power signoff) can pull them straight from the
    macro. The filesets are:

    * ``models.physical`` -- LEF + GDS for place-and-route in a parent.
    * ``models.timing.<corner>`` -- Liberty (``nldm``) per timing scenario
      (:keypath:`ASIC,constraint,timing,scenario`), so it adapts to single- and
      multi-corner PDKs.
    * ``rtl`` -- the gate-level netlist as a *simulation* view, bundling the
      standard-cell Verilog models (as a dependency) so it simulates standalone.
    * ``netlist`` -- the same gate-level netlist as a *structural* view for STA,
      dependency-free (STA resolves cells from Liberty).
    * ``sdc`` -- the implementation-generated constraints (propagated clocks).

    The ``rtl`` view's cell-model dependency is serialized into the macro's
    manifest (see :class:`DependencySchema`), so it is recovered when the macro is
    reloaded: a consumer can simulate the ``rtl`` view without re-registering the
    PDK library. The ``rtl``/``netlist``/``sdc`` filesets are added only when the
    run produced the corresponding result, so flows that stop short of them still
    yield a valid macro.

    Args:
        project: A completed ASIC project whose top module is a variant.
        name (str): Name for the resulting macro library. Also the netlist's top
            module name (the parameter-free variant).

    Returns:
        StdCellLibrary: The packaged macro, ready for :meth:`Uniquified.wireup`.

    Raises:
        UniquifyError: If the project defines no timing scenario.
    """
    library = StdCellLibrary(name)
    library.add_asic_pdk(project.get("asic", "pdk"))

    with library.active_fileset("models.physical"):
        library.add_file(project.find_result("lef", step="write.views"))
        library.add_file(project.find_result("gds", step="write.gds"))
        library.add_asic_aprfileset()

    corners = project.getkeys("constraint", "timing", "scenario")
    if not corners:
        raise UniquifyError(
            f"project defines no timing scenario; cannot build macro {name!r}")

    for corner in corners:
        with library.active_fileset(f"models.timing.{corner}"):
            library.add_file(project.find_result(f"{corner}.lib", step="write.views"))
            library.add_asic_libcornerfileset(corner, "nldm")

    # Gate-level netlist as two views, both topping out at the variant module.
    netlist = project.find_result("lec.vg", step="write.views")
    if netlist:
        # 'rtl' (simulation): bundle the standard-cell Verilog models so the
        # netlist simulates standalone; the dependency is serialized into the
        # macro manifest and recovered on reload.
        with library.active_fileset("rtl"):
            library.set_topmodule(name)
            library.add_file(netlist)
            mainlib = project.get_library(project.get("asic", "mainlib"))
            if mainlib is not None:
                library.add_depfileset(mainlib, "rtl")
        # 'netlist' (structural, for STA): dependency-free -- STA resolves cells
        # from Liberty, so no cell Verilog is bundled.
        with library.active_fileset("netlist"):
            library.set_topmodule(name)
            library.add_file(netlist)

    sdc = project.find_result("sdc", step="write.views")
    if sdc:
        with library.active_fileset("sdc"):
            library.add_file(sdc)

    return library
