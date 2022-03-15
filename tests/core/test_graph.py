import os
import siliconcompiler
import json

def test_graph():

    chip = siliconcompiler.Chip()
    chip.load_target('skywater130_demo')

    chip.graph("top","asicflow", prefix="a_")
    chip.graph("top","signoffflow", prefix="b_")
    chip.edge("top", "a_export", "b_import")

    chip.write_flowgraph("top.png", flow="top")

#########################
if __name__ == "__main__":
    test_graph()
