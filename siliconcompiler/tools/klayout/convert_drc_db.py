from siliconcompiler.tools.klayout import KLayoutTask


class ConvertDRCDBTask(KLayoutTask):
    '''
    Convert a DRC db from .lyrdb or .ascii to an openroad json marker file
    '''
    def task(self):
        return "convert_drc_db"

    def setup(self):
        super().setup()

        self.set_script("klayout_convert_drc_db.py")

        for file, nodes in self.get_files_from_input_nodes().items():
            if file not in (f'{self.design_topmodule}.lyrdb', f'{self.design_topmodule}.ascii'):
                continue

            if len(nodes) == 1:
                self.add_input_file(file)
            else:
                for in_step, in_index in nodes:
                    self.add_input_file(self.compute_input_file_node_name(file, in_step, in_index))

        self.add_output_file(ext="json")
