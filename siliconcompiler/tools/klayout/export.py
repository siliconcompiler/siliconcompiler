from siliconcompiler.tools.klayout import KLayoutTask
from siliconcompiler.tools.klayout.screenshot import ScreenshotParams


class ExportTask(KLayoutTask, ScreenshotParams):
    def __init__(self):
        super().__init__()

        self.add_parameter("stream", "<gds,oas>", "Extension to use for stream generation",
                           defvalue="gds")
        self.add_parameter("timestamps", "bool", "Export GDSII with timestamps", defvalue=True)
        self.add_parameter("screenshot", "bool",
                           "true/false: true will cause KLayout to generate a screenshot of "
                           "the layout", defvalue=True)

    def task(self):
        return "export"

    def setup(self):
        super().setup()

        self.set_script("klayout_export.py")

        if f"{self.design_topmodule}.def" in self.get_files_from_input_nodes():
            self.add_input_file(ext="def")
        else:
            for lib, fileset in self.schema().get_filesets():
                if lib.get_file(fileset=fileset, filetype="def"):
                    self.add_required_key(lib, "fileset", fileset, "file", "def")
                    break

        default_stream = self.get("var", "stream")

        self.add_output_file(ext=default_stream)
        self.add_output_file(ext="lyt")
        self.add_output_file(ext="lyp")

        self.add_required_tool_key("var", "stream")

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


# def setup(chip):
#     '''
#     Generate a GDSII file from an input DEF file
#     '''

#     # Generic tool setup.
#     setup_tool(chip)

#     tool = 'klayout'
#     step = chip.get('arg', 'step')
#     index = chip.get('arg', 'index')
#     _, task = get_tool_task(chip, step, index)
#     clobber = False

#     chip.set('tool', tool, 'task', task, 'threads', 1, step=step, index=index, clobber=clobber)

#     script = 'klayout_export.py'
#     option = ['-z', '-nc', '-rx', '-r']
#     chip.set('tool', tool, 'task', task, 'script', script, step=step, index=index,
# clobber=clobber)
#     chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index,
# clobber=clobber)

#     targetlibs = get_libraries(chip, 'logic')
#     stackup = chip.get('option', 'stackup')
#     pdk = chip.get('option', 'pdk')

#     # Set stream extension
#     streams = ('gds', 'oas')
#     chip.set('tool', tool, 'task', task, 'var', 'stream', 'gds',
#              step=step, index=index, clobber=False)
#     chip.set('tool', tool, 'task', task, 'var', 'stream',
#              f'Extension to use for stream generation ({streams})',
#              field='help')
#     default_stream = chip.get('tool', tool, 'task', task, 'var', 'stream',
#                               step=step, index=index)[0]
#     sc_stream_order = [default_stream, *[s for s in streams if s != default_stream]]

#     if stackup:
#         macrolibs = get_libraries(chip, 'macro')

#         chip.add('tool', tool, 'task', task, 'require', ",".join(['option', 'stackup']),
#                  step=step, index=index)
#         req_set = False
#         for s in sc_stream_order:
#             if chip.valid('pdk', pdk, 'layermap', 'klayout', 'def', s, stackup):
#                 chip.add('tool', tool, 'task', task, 'require',
#                          ",".join(['pdk', pdk, 'layermap', 'klayout', 'def', s, stackup]),
#                          step=step, index=index)
#                 req_set = True
#                 break
#         if not req_set:
#             # add default require
#             chip.add('tool', tool, 'task', task, 'require',
#                      ",".join(['pdk', pdk, 'layermap', 'klayout', 'def', 'klayout', stackup]),
#                      step=step, index=index)

#         for lib in (targetlibs + macrolibs):
#             lib_requires_stream = True
#             if chip.valid('library', lib, 'option', 'var', 'klayout_allow_missing_cell') and \
#                chip.get('library', lib, 'option', 'var', 'klayout_allow_missing_cell'):
#                 lib_requires_stream = False
#             req_set = False
#             for s in sc_stream_order:
#                 if chip.valid('library', lib, 'output', stackup, s):
#                     chip.add('tool', tool, 'task', task, 'require',
#                              ",".join(['library', lib, 'output', stackup, s]),
#                              step=step, index=index)
#                     req_set = True
#                     break
#             if not req_set and lib_requires_stream:
#                 chip.add('tool', tool, 'task', task, 'require',
#                          ",".join(['library', lib, 'output', stackup, default_stream]),
#                          step=step, index=index)
#             chip.add('tool', tool, 'task', task, 'require',
#                      ",".join(['library', lib, 'output', stackup, 'lef']),
#                      step=step, index=index)
#     else:
#         chip.error('Stackup parameter required for Klayout.')

#     if not targetlibs:
#         chip.add('tool', tool, 'task', task, 'require',
#                  'option,var,klayout_libtype',
#                  step=step, index=index)

#     # Input/Output requirements for default flow
#     design = chip.top()
#     if design + '.def' in input_provides(chip, step, index):
#         chip.add('tool', tool, 'task', task, 'input', design + '.def',
#                  step=step, index=index)
#     else:
#         chip.add('tool', tool, 'task', task, 'require', 'input,layout,def',
#                  step=step, index=index)

#     chip.add('tool', tool, 'task', task, 'output', f'{design}.{default_stream}',
#              step=step, index=index)
#     chip.add('tool', tool, 'task', task, 'output', f'{design}.lyt',
#              step=step, index=index)
#     chip.add('tool', tool, 'task', task, 'output', f'{design}.lyp',
#              step=step, index=index)

#     # Export GDS with timestamps by default.
#     chip.set('tool', tool, 'task', task, 'var', 'timestamps', 'true',
#              step=step, index=index, clobber=False)
#     chip.set('tool', tool, 'task', task, 'var', 'timestamps',
#              'Export GDSII with timestamps',
#              field='help')

#     chip.set('tool', tool, 'task', task, 'var', 'screenshot', 'true',
#              step=step, index=index, clobber=False)
#     chip.set('tool', tool, 'task', task, 'var', 'screenshot',
#              'true/false: true will cause KLayout to generate a screenshot of the layout',
#              field='help')

#     if chip.get('tool', tool, 'task', task, 'var', 'screenshot',
#                 step=step, index=index) == ['true']:
#         setup_gui_screenshot(chip, require_input=False)


# def runtime_options(chip):
#     return runtime_options_tool(chip) + [
#         '-rd', f'SC_TOOLS_ROOT={os.path.dirname(os.path.dirname(__file__))}'
#     ]


# def post_process(chip):
#     process_metrics(chip)
