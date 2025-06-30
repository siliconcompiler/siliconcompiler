import shutil
import os

import os.path

from siliconcompiler.tools.openroad import make_docs as or_make_docs
from siliconcompiler.tools.openroad._apr import setup as tool_setup
from siliconcompiler.tools.openroad._apr import set_reports
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools._common import find_incoming_ext, input_provides, get_tool_task
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params


from siliconcompiler.tool import ShowTaskSchema
from siliconcompiler.tools.openroad._apr import APRTask, OpenROADSTAParameter


class ShowTask(ShowTaskSchema, APRTask, OpenROADSTAParameter):
    def __init__(self):
        super().__init__()

    def setup(self):
        super().setup()

        self.unset("input")
        self.unset("output")

        self.set_script("sc_show.tcl")

        self.set("var", "showexit", False, clobber=False)

    def pre_process(self):
        super().pre_process()
        self._copy_show_files()

    def preferred_show_extensions(self):
        return ["odb", "def"]

    def _copy_show_files(self):
        if not self.get("var", "showfilepath"):
            return

        show_file = self.find_files('var', 'showfilepath')
        show_type = self.get('var', 'showfiletype')

        show_job, show_step, show_index = (None, None, None)
        show_node = self.get("var", "shownode")
        if show_node:
            show_job, show_step, show_index = show_node

        # copy source in to keep sc_apr.tcl simple
        dst_file = f"inputs/{self.design_topmodule}.{show_type}"
        shutil.copy2(show_file, dst_file)

        job_root = self.schema()
        if show_job:
            job_root = job_root.history(show_job)

        if show_step and show_index:
            sdc_file = os.path.join(job_root.getworkdir(show_step, show_index),
                                    "output",
                                    f"{self.design_topmodule}.sdc")
            if sdc_file and os.path.exists(sdc_file):
                shutil.copy2(sdc_file, f"inputs/{self.design_topmodule}.sdc")

    def runtime_options(self):
        options = super().runtime_options()
        try:
            options.remove("-exit")
        except KeyError:
            pass
        options.append("-gui")
        return options


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    or_make_docs(chip)
    chip.set('tool', 'openroad', 'task', 'show', 'var', 'show_filepath', '<path>')


def setup(chip):
    '''
    Show a design in openroad
    '''
    generic_show_setup(chip, False)


def generic_show_setup(chip, exit):
    # Generic tool setup.
    tool_setup(chip, exit=exit)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    design = chip.top()

    chip.set('tool', tool, 'task', task, 'script', 'sc_show.tcl',
             step=step, index=index)

    # Add GUI option
    chip.add('tool', tool, 'task', task, 'option', '-gui',
             step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'show_exit', exit,
             step=step, index=index, clobber=False)
    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', 'show_filepath']),
                 step=step, index=index)
    else:
        incoming_ext = find_incoming_ext(chip, ('odb', 'def'), 'def')
        chip.set('tool', tool, 'task', task, 'var', 'show_filetype', incoming_ext,
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'input', f'{design}.{incoming_ext}',
                 step=step, index=index)
        if f'{design}.sdc' in input_provides(chip, step, index):
            chip.add('tool', tool, 'task', task, 'input', f'{design}.sdc',
                     step=step, index=index)

    # set default values for task
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)

    set_reports(chip, [])


def pre_process(chip):
    copy_show_files(chip)
    define_ord_files(chip)
    build_pex_corners(chip)


def copy_show_files(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        show_file = chip.get('tool', tool, 'task', task, 'var', 'show_filepath',
                             step=step, index=index)[0]
        show_type = chip.get('tool', tool, 'task', task, 'var', 'show_filetype',
                             step=step, index=index)[0]
        show_job = chip.get('tool', tool, 'task', task, 'var', 'show_job',
                            step=step, index=index)
        show_step = chip.get('tool', tool, 'task', task, 'var', 'show_step',
                             step=step, index=index)
        show_index = chip.get('tool', tool, 'task', task, 'var', 'show_index',
                              step=step, index=index)

        # copy source in to keep sc_apr.tcl simple
        dst_file = f"inputs/{chip.top()}.{show_type}"
        shutil.copy2(show_file, dst_file)
        if show_job and show_step and show_index:
            sdc_file = chip.find_result('sdc', show_step[0],
                                        jobname=show_job[0],
                                        index=show_index[0])
            if sdc_file and os.path.exists(sdc_file):
                shutil.copy2(sdc_file, f"inputs/{chip.top()}.sdc")
