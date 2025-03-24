# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_snapshot(gcd_chip_dir, copy_chip_dir):
    chip = copy_chip_dir(gcd_chip_dir)

    assert not chip.getworkdir().startswith(gcd_chip_dir[1])

    assert not os.path.exists(os.path.join(chip.getworkdir(), "gcd.png"))
    chip.snapshot()
    assert os.path.exists(os.path.join(chip.getworkdir(), "gcd.png"))

    assert not os.path.exists("test.png")
    chip.snapshot(path="test.png")
    assert os.path.exists("test.png")
