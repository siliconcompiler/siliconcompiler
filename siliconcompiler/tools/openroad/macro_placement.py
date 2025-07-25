from siliconcompiler import NodeStatus

from siliconcompiler.tools._common import has_pre_post_script, get_tool_task

from siliconcompiler.tools.openroad._apr import setup as apr_setup
from siliconcompiler.tools.openroad._apr import set_reports, set_pnr_inputs, set_pnr_outputs
from siliconcompiler.tools.openroad._apr import \
    define_ord_params, define_sta_params, define_sdc_params, \
    define_mpl_params, define_gpl_params
from siliconcompiler.tools.openroad._apr import build_pex_corners, define_ord_files
from siliconcompiler.tools.openroad._apr import extract_metrics


from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADGPLParameter


class MacroPlacementTask(APRTask, OpenROADSTAParameter, OpenROADGPLParameter):
    def __init__(self):
        super().__init__()

        self.add_parameter("mpl_constraints", "[file]", "contraints script for macro placement")

        self.add_parameter("macro_place_halo", "(float,float)", "macro halo to use when performing automated macro placement ([x, y] in microns)", unit="um")

        self.add_parameter("mpl_min_instances", "int", "minimum number of instances to use while clustering for macro placement")
        self.add_parameter("mpl_max_instances", "int", "maximum number of instances to use while clustering for macro placement")
        self.add_parameter("mpl_min_macros", "int", "minimum number of macros to use while clustering for macro placement")
        self.add_parameter("mpl_max_macros", "int", "maximum number of macros to use while clustering for macro placement")
        self.add_parameter("mpl_max_levels", "int", "maximum depth of physical hierarchical tree")
        self.add_parameter("mpl_min_aspect_ratio", "float", "Specifies the minimum aspect ratio of its width to height of a standard cell cluster")
        self.add_parameter("mpl_fence", "(float,float,float,float)", "Defines the global fence bounding box coordinates (llx, lly, urx, ury)", unit="um")
        self.add_parameter("mpl_bus_planning", "bool", "Flag to enable bus planning", defvalue=False)
        self.add_parameter("mpl_target_dead_space", "float", "Specifies the target dead space percentage, which influences the utilization of standard cell clusters")

        self.add_parameter("mpl_area_weight", "float", "Weight for the area of current floorplan")
        self.add_parameter("mpl_outline_weight", "float", "Weight for violating the fixed outline constraint, meaning that all clusters should be placed within the shape of their parent cluster")
        self.add_parameter("mpl_wirelength_weight", "float", "Weight for half-perimeter wirelength")
        self.add_parameter("mpl_guidance_weight", "float", "Weight for guidance cost or clusters being placed near specified regions if users provide such constraints")
        self.add_parameter("mpl_fence_weight", "float", "Weight for fence cost, or how far the macro is from zero fence violation")
        self.add_parameter("mpl_boundary_weight", "float", "Weight for the boundary, or how far the hard macro clusters are from boundaries. Note that mixed macro clusters are not pushed, thus not considered in this cost.")
        self.add_parameter("mpl_blockage_weight", "float", "Weight for the boundary, or how far the hard macro clusters are from boundaries")
        self.add_parameter("mpl_notch_weight", "float", "Weight for the notch, or the existence of dead space that cannot be used for placement & routing")
        self.add_parameter("mpl_macro_blockage_weight", "float", "Weight for macro blockage, or the overlapping instances of the macro")

    def task(self):
        return "macro_placement"

    def setup(self):
        super().setup()

        self.set("script", "apr/sc_macro_placement.tcl")

        self._set_reports([
            'setup',
            'unconstrained'
        ])

        self.set_asic_var("macro_place_halo", require=True, mainlib_key="macro_placement_halo")

    def pre_process(self):
        if all([
                self.schema("metric").get('macros', step=in_step, index=in_index) == 0
                for in_step, in_index in self.schema("record").get('inputnode', step=self.step, index=self.index)
                ]):
            self.schema("record").set('status', NodeStatus.SKIPPED, step=self.step, index=self.index)
            self.logger.warning(f'{self.step}/{self.index} will be skipped since are no macros to place.')
            return

        super().pre_process()


def setup(chip):
    '''
    Macro placement
    '''

    # Generic apr tool setup.
    apr_setup(chip)

    # Task setup
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'apr/sc_macro_placement.tcl',
             step=step, index=index)

    # Setup task IO
    set_pnr_inputs(chip)
    set_pnr_outputs(chip)

    # set default values for openroad
    define_ord_params(chip)
    define_sta_params(chip)
    define_sdc_params(chip)
    define_mpl_params(chip)
    define_gpl_params(chip)

    set_reports(chip, [
        'setup',
        'unconstrained'
    ])

    chip.set('tool', tool, 'task', task, 'file', 'rtlmp_constraints',
             'contraints script for macro placement',
             field='help')

    if chip.get('tool', tool, 'task', task, 'file', 'rtlmp_constraints', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'file', 'rtlmp_constraints']),
                 step=step, index=index)


def pre_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    input_nodes = chip.get('record', 'inputnode', step=step, index=index)
    if not has_pre_post_script(chip) and all([
            chip.get('metric', 'macros', step=in_step, index=in_index) == 0
            for in_step, in_index in input_nodes
            ]):
        chip.set('record', 'status', NodeStatus.SKIPPED, step=step, index=index)
        chip.logger.warning(f'{step}/{index} will be skipped since are no macros to place.')
        return

    build_pex_corners(chip)
    define_ord_files(chip)


def post_process(chip):
    extract_metrics(chip)
