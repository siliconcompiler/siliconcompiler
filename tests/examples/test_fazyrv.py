import json
import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_optimize():
    from fazyrv import make
    make.optimize(count=2)

    assert os.path.exists('optimize.json')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_reuse():
    from fazyrv import make

    data = {"data": [
        {
            "parameters": {
                "tool,openroad,task,global_placement,var,place_density": {
                    "key": [
                        "tool",
                        "openroad",
                        "task",
                        "global_placement",
                        "var",
                        "place_density"
                    ],
                    "step": None,
                    "index": None,
                    "print": "[tool,openroad,task,global_placement,var,place_density]",
                    "value": 0.3694111103562264
                },
                "tool,openroad,task,global_placement,var,gpl_routability_driven": {
                    "key": [
                        "tool",
                        "openroad",
                        "task",
                        "global_placement",
                        "var",
                        "gpl_routability_driven"
                    ],
                    "step": None,
                    "index": None,
                    "print": "[tool,openroad,task,global_placement,var,gpl_routability_driven]",
                    "value": True
                },
                "tool,openroad,task,global_placement,var,gpl_timing_driven": {
                    "key": [
                        "tool",
                        "openroad",
                        "task",
                        "global_placement",
                        "var",
                        "gpl_timing_driven"
                    ],
                    "step": None,
                    "index": None,
                    "print": "[tool,openroad,task,global_placement,var,gpl_timing_driven]",
                    "value": False
                }
            }
        }]
    }

    with open("optimize.json", "w") as f:
        json.dump(data, f)

    make.reuse()

    assert os.path.exists('build/fazyrv/job0/write.gds/0/outputs/fsoc.gds')
