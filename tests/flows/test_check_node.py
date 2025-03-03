from siliconcompiler.scheduler import _setup_node, get_check_node_keys


def test_check_node(gcd_chip):
    _setup_node(gcd_chip, "syn", "0")

    required = get_check_node_keys(gcd_chip, "syn", "0")
    # Check tool params
    assert "tool,yosys,task,syn_asic,prescript" in required
    assert "tool,yosys,task,syn_asic,postscript" in required
    assert "tool,yosys,task,syn_asic,refdir" in required
    assert "tool,yosys,task,syn_asic,option" in required
    assert "tool,yosys,task,syn_asic,threads" in required
    assert "tool,yosys,task,syn_asic,script" in required
