import os.path

from siliconcompiler.tools.vpr import VPRTask
from siliconcompiler import ShowTask


class ShowTask(ShowTask, VPRTask):
    '''
    Show placed and/or routed designs in VPR GUI
    '''
    def get_supported_show_extentions(self):
        return ["place", "route"]

    def runtime_options(self):
        options = super().runtime_options()

        file_path = self.get("var", "showfilepath")
        file_dir = os.path.dirname(file_path)
        blif_file = os.path.join(file_dir, f'{self.design_topmodule}.blif')
        net_file = os.path.join(file_dir, f'{self.design_topmodule}.net')
        place_file = os.path.join(file_dir, f'{self.design_topmodule}.place')
        route_file = os.path.join(file_dir, f'{self.design_topmodule}.route')

        if os.path.exists(blif_file):
            options.append(blif_file)
        else:
            raise FileNotFoundError("Blif file does not exist")

        if os.path.exists(net_file):
            options.extend(['--net_file', net_file])
        else:
            raise FileNotFoundError("Net file does not exist")

        if os.path.exists(route_file) and os.path.exists(place_file):
            options.append('--analysis')
            options.extend(['--place_file', place_file])
            options.extend(['--route_file', route_file])
        elif os.path.exists(place_file):
            # NOTE: This is a workaround to display the VPR GUI on the output of the place step.
            # VPR GUI can be invoked during the place, route or analysis steps - not after they
            # are run.
            # Analysis can only be run after route. Hence, the only way to display the output
            # of the is to run the route step. Performing routing could take a significant amount
            # of time, which would not be useful if the user is simply looking to visualize
            # the placed design. Setting max_router_iterations to 0 avoids running routing
            # iterations
            # and provides a fast way to invoke VPR GUI on the placed design.
            options.append('--route')
            options.extend(['--max_router_iterations', 0])
            options.extend(['--place_file', place_file])
        else:
            raise FileNotFoundError("Place file does not exist")

        options.extend(["--disp", "on"])

        return options
