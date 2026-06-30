from typing import Optional

from siliconcompiler import ASIC, Project


def asic_target(proj: ASIC, pdk: Optional[str] = None):
    '''A factory function to configure an ASIC for a given PDK.

    This function acts as a dispatcher, calling the appropriate setup function
    (e.g., `skywater130_demo`, `asap7_demo`) based on the provided PDK name.
    It simplifies the process of targeting different silicon manufacturing
    processes by centralizing the selection logic.

    Args:
        proj (ASIC): The siliconcompiler project to configure.
        pdk (Optional[str]): The name of the Process Design Kit to target. Supported
            values are "asap7", "freepdk45", "gf180", "ihp130", and
            "skywater130".

    Raises:
        ValueError: If the provided `pdk` name is not supported.
    '''

    from siliconcompiler.targets import asap7_demo, freepdk45_demo, gf180_demo, \
        ihp130_demo, skywater130_demo

    # Conditionally call the setup function that matches the requested PDK.
    if pdk == "asap7":
        asap7_demo(proj)
    elif pdk == "freepdk45":
        freepdk45_demo(proj)
    elif pdk == "gf180":
        gf180_demo(proj)
    elif pdk == "ihp130":
        ihp130_demo(proj)
    elif pdk == "skywater130":
        skywater130_demo(proj)
    else:
        # If the PDK is not in the list of supported targets, raise an error.
        raise ValueError(f"pdk not supported: {pdk}")


def detect_elaboration_language(proj: Project, default: str = "verilog") -> Optional[str]:
    '''Detects the hardware description language of the design.

    This function inspects the source files in the provided project to determine
    the primary hardware description language (HDL) used. It checks for the
    presence of Verilog, SystemVerilog, Chisel, VHDL, HLS, and Bluespec source files.

    Args:
        proj (ASIC): The siliconcompiler project containing the design sources.
        default (str, optional): The default language to return if no specific
            language is detected.

    Returns:
        Optional[str]: The detected hardware description language, or the default
        if no specific language is found.
    '''

    # Language detection is best-effort: an incomplete project (no design, no
    # filesets, unresolved filesets, ...) should never raise here, it should
    # simply fall back to the default language.
    try:
        filesets = proj.get_filesets()
    except Exception:
        return default

    for lib, fileset in filesets:
        if lib.has_file(fileset=fileset, filetype="chisel") or \
                lib.has_file(fileset=fileset, filetype="scala"):
            return "chisel"
        if lib.has_file(fileset=fileset, filetype="vhdl"):
            return "vhdl"
        if lib.has_file(fileset=fileset, filetype="c"):
            return "hls"
        if lib.has_file(fileset=fileset, filetype="bsv"):
            return "bluespec"
        if lib.has_file(fileset=fileset, filetype="systemverilog"):
            return "systemverilog"
        if lib.has_file(fileset=fileset, filetype="verilog"):
            return "verilog"

    return default
