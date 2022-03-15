import os
import siliconcompiler

def test_graph():

    chip = siliconcompiler.Chip()
    chip.load_target('freepdk45_demo')

    chip.graph("top","asicflow")
    chip.graph("top","signoffflow")

    chip.write_flowgraph("top.png", flow="top")

#########################
if __name__ == "__main__":
    test_graph()
