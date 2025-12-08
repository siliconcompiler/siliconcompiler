from typing import Optional, Union

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADPSMParameter


class PowerGridAnalysisTask(APRTask, OpenROADPSMParameter, OpenROADSTAParameter):
    '''
    Performs static IR drop analysis on the power grid using OpenROAD.

    This task utilizes the OpenROAD PDN (Power Distribution Network) analysis
    capabilities (PSM) to calculate static IR drop based on instance power
    consumption and grid resistance.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("source_disconnection_rate", "float",
                           "Fraction (0.0-100.0) of power source bumps to simulate "
                           "disconnected/failing bumps.",
                           defvalue=0.0)
        self.add_parameter("source_disconnection_seed", "int",
                           "Random seed used for determining which power bumps to disconnect.",
                           defvalue=123)

        self.add_parameter("instance_power", "[(str,float)]",
                           "List of (instance_name, power_value) tuples to override specific "
                           "instance power consumption.")

        self.add_parameter("net", "{str}",
                           "Set of specific power/ground nets to analyze (e.g., VDD, VSS).")

        self.add_parameter("heatmap_grid", "(float,float)",
                           "Resolution of the IR drop heatmap grid (x_step, y_step).",
                           defvalue=(10, 10), units="um")

        self.add_parameter("external_resistance", "float",
                           "Resistance value to add to the power grid model to account for "
                           "external factors (e.g., package, PCB).",
                           units="ohm")

    def set_openroad_disconnectrate(self, rate: float,
                                    step: Optional[str] = None,
                                    index: Optional[Union[str, int]] = None):
        '''
        Sets the fraction of power pads/bumps to disconnect to simulate robustness.

        Args:
            rate (float): A value between 0.0 and 100.0 representing the percentage to disconnect.
            step (str, optional): step name
            index (str, optional): index
        '''
        self.set("var", "source_disconnection_rate", rate, step=step, index=index)

    def set_openroad_disconnectseed(self, seed: int,
                                    step: Optional[str] = None,
                                    index: Optional[Union[str, int]] = None):
        '''
        Sets the random seed for the power bump disconnection logic.

        Args:
            seed (int): The random seed integer.
            step (str, optional): step name
            index (str, optional): index
        '''
        self.set("var", "source_disconnection_seed", seed, step=step, index=index)

    def set_openroad_heatmapgrid(self, x: float, y: float,
                                 step: Optional[str] = None,
                                 index: Optional[Union[str, int]] = None):
        '''
        Sets the resolution for the IR drop heatmap generation.

        Args:
            x (float): Grid spacing in the X direction (microns).
            y (float): Grid spacing in the Y direction (microns).
            step (str, optional): step name
            index (str, optional): index
        '''
        self.set("var", "heatmap_grid", (x, y), step=step, index=index)

    def set_openroad_externalresistance(self, res: float,
                                        step: Optional[str] = None,
                                        index: Optional[Union[str, int]] = None):
        '''
        Sets the external resistance to be modeled in the power grid analysis.

        Args:
            res (float): External resistance to add.
            step (str, optional): step name
            index (str, optional): index
        '''
        self.set("var", "external_resistance", res, step=step, index=index)

    def add_openroad_irdropnet(self, net: str,
                               step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                               clobber: bool = False):
        '''
        Adds a specific net to the list of nets to be analyzed for IR drop.

        Args:
            net (str): The name of the net (e.g., "VDD").
            step (str, optional): step name
            index (str, optional): index
            clobber (bool): If True, replaces existing nets. If False, appends to the list.
        '''
        if clobber:
            self.set("var", "net", net, step=step, index=index)
        else:
            self.add("var", "net", net, step=step, index=index)

    def add_openroad_instancepower(self, inst: str, power: float,
                                   step: Optional[str] = None,
                                   index: Optional[Union[str, int]] = None,
                                   clobber: bool = False):
        '''
        Manually sets the power consumption for a specific instance.

        Args:
            inst (str): The name of the instance.
            power (float): The power value (typically in Watts, depending on library units).
            step (str, optional): step name
            index (str, optional): index
            clobber (bool): If True, replaces the existing list. If False, appends.
        '''
        if clobber:
            self.set("var", "instance_power", (inst, power), step=step, index=index)
        else:
            self.add("var", "instance_power", (inst, power), step=step, index=index)

    def task(self) -> str:
        '''
        Returns the internal task name for this tool task.
        '''
        return "irdrop_analysis"

    def setup(self):
        '''
        Configures the tool runtime parameters, scripts, and requirements.
        '''
        super().setup()
        self.set_script("apr/sc_irdrop.tcl")

        self.add_version(">=v2.0-26750", clobber=True)

        # Output is not a standard design file, unset default expectation
        self.unset("output")

        # Define keys required for this task to run successfully
        self.add_required_key("var", "source_disconnection_rate")
        self.add_required_key("var", "source_disconnection_seed")
        self.add_required_key("var", "heatmap_grid")

        # Conditionally require these keys if they have been set
        if self.get("var", "instance_power"):
            self.add_required_key("var", "instance_power")

        if self.get("var", "net"):
            self.add_required_key("var", "net")
        if self.get("var", "external_resistance") is not None:
            self.add_required_key("var", "external_resistance")

    def runtime_options(self):
        '''
        Returns the command line arguments for the OpenROAD executable.

        Ensures the GUI flag is present, as visualization is often required
        or implied for heatmap analysis contexts in this workflow.
        '''
        args = super().runtime_options()
        if "-gui" not in args:
            args.append("-gui")
        return args
