# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest


@pytest.mark.eda
def test_snapshot(gcd_chip):
    gcd_chip.run()
    assert not os.path.exists(os.path.join(gcd_chip.getworkdir(), "gcd.png"))
    gcd_chip.snapshot()
    assert os.path.exists(os.path.join(gcd_chip.getworkdir(), "gcd.png"))

    assert not os.path.exists("test.png")
    gcd_chip.snapshot(path="test.png")
    assert os.path.exists("test.png")
