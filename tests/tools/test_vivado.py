from siliconcompiler.tools.vivado import syn_fpga


def test_vivado_parameter_synth_directive():
    task = syn_fpga.SynthesisTask()
    task.set_vivado_synthdirective('Remap')
    assert task.get("var", "synth_directive") == 'Remap'
    task.set_vivado_synthdirective('AlternateRoutability', step='syn_fpga', index='1')
    assert task.get("var", "synth_directive", step='syn_fpga', index='1') == 'AlternateRoutability'
    assert task.get("var", "synth_directive") == 'Remap'


def test_vivado_parameter_synth_mode():
    task = syn_fpga.SynthesisTask()
    task.set_vivado_synthmode('out_of_context')
    assert task.get("var", "synth_mode") == 'out_of_context'
    task.set_vivado_synthmode('flow', step='syn_fpga', index='1')
    assert task.get("var", "synth_mode", step='syn_fpga', index='1') == 'flow'
    assert task.get("var", "synth_mode") == 'out_of_context'
