# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_list_metrics(datadir):

    chip = siliconcompiler.Chip('test')
    chip.list_metrics()

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_list_metrics(datadir(__file__))
