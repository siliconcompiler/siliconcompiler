import os
import platform
from pathlib import Path
import shutil

from siliconcompiler.tools.klayout.klayout import setup as setup_tool
from siliconcompiler.tools.klayout.klayout import process_metrics
from siliconcompiler.tools.klayout.klayout import runtime_options as runtime_options_tool
from siliconcompiler.tools.klayout.screenshot import setup_gui_screenshot
from siliconcompiler.tools._common import input_provides, get_tool_task
from siliconcompiler.tools._common.asic import get_libraries


from siliconcompiler.tool import ASICTaskSchema


class ExportTask(ASICTaskSchema):
    def __init__(self):
        super().__init__()

        self.add_parameter("stream", "<gds,oas>", "Extension to use for stream generation", defvalue="gds")
        self.add_parameter("timestamps", "bool", "Export GDSII with timestamps", defvalue=True)
        self.add_parameter("screenshot", "bool", "true/false: true will cause KLayout to generate a screenshot of the layout", defvalue=True)

        # Screenshot
        self.add_parameter("show_resolution", "(int,int)", "Horizontal and vertical resolution in pixels", defvalue=(4096, 4096), unit="px")
        self.add_parameter("show_bins", "(int,int)", "If greater than 1, splits the image into multiple segments along x-axis and y-axis", defvalue=(1, 1))
        self.add_parameter("show_margin", "float", "Margin around design in microns", defvalue=10, unit="um")
        self.add_parameter("show_linewidth", "int", "Width of lines in detailed screenshots", defvalue=0, unit="px")
        self.add_parameter("show_oversampling", "int", "Image oversampling used in detailed screenshots'", defvalue=2)
        self.add_parameter("hide_layers", "[str]", "list of layers to hide")

    def tool(self):
        return "klayout"

    def task(self):
        return "export"

    def parse_version(self, stdout):
        # KLayout 0.26.11
        return stdout.split()[1]

    def setup(self):
        super().setup()

        klayout_exe = 'klayout'
        if self.schema().get('option', 'scheduler', 'name', step=self.step, index=self.index) != 'docker':
            if platform.system() == 'Windows':
                klayout_exe = 'klayout_app.exe'
                if not shutil.which(klayout_exe):
                    loc_dir = os.path.join(Path.home(), 'AppData', 'Roaming', 'KLayout')
                    global_dir = os.path.join(os.path.splitdrive(Path.home())[0],
                                              os.path.sep,
                                              'Program Files (x86)',
                                              'KLayout')
                    if os.path.isdir(loc_dir):
                        self.set_path(loc_dir)
                    elif os.path.isdir(global_dir):
                        self.set_path(global_dir)
            elif platform.system() == 'Darwin':
                klayout_exe = 'klayout'
                if not shutil.which(klayout_exe):
                    klayout_dir = os.path.join(os.path.sep,
                                               'Applications',
                                               'klayout.app',
                                               'Contents',
                                               'MacOS')
                    # different install directory when installed using Homebrew
                    klayout_brew_dir = os.path.join(os.path.sep,
                                                    'Applications',
                                                    'KLayout',
                                                    'klayout.app',
                                                    'Contents',
                                                    'MacOS')
                    if os.path.isdir(klayout_dir):
                        self.set_path(klayout_dir)
                    elif os.path.isdir(klayout_brew_dir):
                        self.set_path(klayout_brew_dir)

        self.set_exe(klayout_exe, vswitch=['-zz', '-v'], format="json")
        self.add_version(">=0.28.0")

        self.add_commandline_option(['-z', '-nc', '-rx', '-r'], clobber=True)

        self.set_dataroot("refdir", __file__)
        with self.active_dataroot("refdir"):
            self.set_refdir(".")

        if self.schema().get('option', 'nodisplay'):
            # Tells QT to use the offscreen platform if nodisplay is used
            self.set_environmentalvariable('QT_QPA_PLATFORM', 'offscreen')

        self.add_regex("warnings", r'(WARNING|warning)')
        self.add_regex("errors", r'ERROR')

        self.set_threads(1)

        self.set_script("klayout_export.py")

        self.add_required_tool_key("var", "stream")

        default_stream = self.get("var", "stream")
        sc_stream_order = [default_stream, *[s for s in ("gds", "oas") if s != default_stream]]
        req_set = False
        for s in sc_stream_order:
            if self.pdk.valid("pdk", "layermapfileset", "klayout", "def", s):
                self.add_required_key(self.pdk, "pdk", "layermapfileset", "klayout", "def", s)
                req_set = True
                break
        if not req_set:
            self.add_required_key(self.pdk, "pdk", "layermapfileset", "klayout", "def", "klayout")

        for lib in self.schema().get("asic", "asiclib"):
            lib_requires_stream = True
            if self.schema().valid('library', lib, "tool", "klayout", 'allow_missing_cell') and \
                    self.schema().get('library', lib, "tool", "klayout", 'allow_missing_cell'):
                lib_requires_stream = False

            req_set = False
            libobj = self.schema().get("library", lib, field="schema")
            for s in sc_stream_order:
                for fileset in libobj.get("asic", "aprfileset"):
                    if libobj.valid("fileset", fileset, "file", s):
                        self.add_required_key(libobj, "fileset", fileset, "file", s)
                        req_set = True
                if req_set:
                    break
            req_set = False
            for fileset in libobj.get("asic", "aprfileset"):
                if libobj.valid("fileset", fileset, "file", "lef"):
                    self.add_required_key(libobj, "fileset", fileset, "file", "lef")
                    req_set = True

        if self.get("var", "show_bins") == (1, 1):
            self.add_output_file(ext="png")
        else:
            xbins, ybins = self.get("var", "show_bins")
            for x in range(xbins):
                for y in range(ybins):
                    self.add_output_file(f"{self.design_topmodule}_X{x}_Y{y}.png")

    def runtime_options(self):
        options = super().runtime_options()
        options.extend(['-rd', f'SC_KLAYOUT_ROOT={os.path.dirname(__file__)}'])
        options.extend(['-rd', f'SC_TOOLS_ROOT={os.path.dirname(os.path.dirname(__file__))}'])
        return options


def setup(chip):
    '''
    Generate a GDSII file from an input DEF file
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'klayout'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    clobber = False

    chip.set('tool', tool, 'task', task, 'threads', 1, step=step, index=index, clobber=clobber)

    script = 'klayout_export.py'
    option = ['-z', '-nc', '-rx', '-r']
    chip.set('tool', tool, 'task', task, 'script', script, step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=clobber)

    targetlibs = get_libraries(chip, 'logic')
    stackup = chip.get('option', 'stackup')
    pdk = chip.get('option', 'pdk')

    # Set stream extension
    streams = ('gds', 'oas')
    chip.set('tool', tool, 'task', task, 'var', 'stream', 'gds',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'stream',
             f'Extension to use for stream generation ({streams})',
             field='help')
    default_stream = chip.get('tool', tool, 'task', task, 'var', 'stream',
                              step=step, index=index)[0]
    sc_stream_order = [default_stream, *[s for s in streams if s != default_stream]]

    if stackup:
        macrolibs = get_libraries(chip, 'macro')

        chip.add('tool', tool, 'task', task, 'require', ",".join(['option', 'stackup']),
                 step=step, index=index)
        req_set = False
        for s in sc_stream_order:
            if chip.valid('pdk', pdk, 'layermap', 'klayout', 'def', s, stackup):
                chip.add('tool', tool, 'task', task, 'require',
                         ",".join(['pdk', pdk, 'layermap', 'klayout', 'def', s, stackup]),
                         step=step, index=index)
                req_set = True
                break
        if not req_set:
            # add default require
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['pdk', pdk, 'layermap', 'klayout', 'def', 'klayout', stackup]),
                     step=step, index=index)

        for lib in (targetlibs + macrolibs):
            lib_requires_stream = True
            if chip.valid('library', lib, 'option', 'var', 'klayout_allow_missing_cell') and \
               chip.get('library', lib, 'option', 'var', 'klayout_allow_missing_cell'):
                lib_requires_stream = False
            req_set = False
            for s in sc_stream_order:
                if chip.valid('library', lib, 'output', stackup, s):
                    chip.add('tool', tool, 'task', task, 'require',
                             ",".join(['library', lib, 'output', stackup, s]),
                             step=step, index=index)
                    req_set = True
                    break
            if not req_set and lib_requires_stream:
                chip.add('tool', tool, 'task', task, 'require',
                         ",".join(['library', lib, 'output', stackup, default_stream]),
                         step=step, index=index)
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['library', lib, 'output', stackup, 'lef']),
                     step=step, index=index)
    else:
        chip.error('Stackup parameter required for Klayout.')

    if not targetlibs:
        chip.add('tool', tool, 'task', task, 'require',
                 'option,var,klayout_libtype',
                 step=step, index=index)

    # Input/Output requirements for default flow
    design = chip.top()
    if design + '.def' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.def',
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require', 'input,layout,def',
                 step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', f'{design}.{default_stream}',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.lyt',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.lyp',
             step=step, index=index)

    # Export GDS with timestamps by default.
    chip.set('tool', tool, 'task', task, 'var', 'timestamps', 'true',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'timestamps',
             'Export GDSII with timestamps',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'screenshot', 'true',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'screenshot',
             'true/false: true will cause KLayout to generate a screenshot of the layout',
             field='help')

    if chip.get('tool', tool, 'task', task, 'var', 'screenshot',
                step=step, index=index) == ['true']:
        setup_gui_screenshot(chip, require_input=False)


def runtime_options(chip):
    return runtime_options_tool(chip) + [
        '-rd', f'SC_TOOLS_ROOT={os.path.dirname(os.path.dirname(__file__))}'
    ]


def post_process(chip):
    process_metrics(chip)
