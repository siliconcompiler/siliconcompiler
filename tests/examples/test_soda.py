import pytest

import os.path


def test_py_make_check():
    from soda import make
    make.check()


@pytest.mark.timeout(600)
def test_py_make_model():
    """The regenerated MLIR is TOSA with entry function forward, which soda-opt outlines as the
    forward_kernel topmodule; skips without the example's torch requirements.
    """
    from soda import make

    try:
        # An explicit output, into this test's own directory. model() defaults to
        # the checked-in mm.mlir, which every other target here reads, so a
        # default call would let this test rewrite the input of the rest of the
        # suite.
        output = make.model(output="regenerated.mlir")
    except ImportError as e:
        pytest.skip(f"{e}: pip install -r examples/soda/requirements.txt")

    assert os.path.isfile(output)
    with open(output, encoding="utf-8") as f:
        mlir = f.read()

    assert "func.func @forward(" in mlir
    assert "tosa.matmul" in mlir
    # [bs, M, K] x [bs, K, N], the shapes model() traces the module with.
    assert "tensor<1x4x8xf32>" in mlir
    assert "tensor<1x8x4xf32>" in mlir


@pytest.mark.eda
@pytest.mark.timeout(900)
@pytest.mark.parametrize("strategy", ("baseline", "optimized"))
def test_py_make_elaborate(strategy):
    from soda import make
    make.elaborate(strategy=strategy)

    # The MLIR front end's product is Verilog for the outlined kernel; the
    # topmodule is forward_kernel because that is what soda-opt names it.
    assert os.path.isfile(
        f'build/mm/elaborate-{strategy}/convert/0/outputs/forward_kernel.v')


@pytest.mark.eda
@pytest.mark.timeout(1200)
def test_py_make_syn():
    """The optimized strategy synthesizes to a mapped netlist; this is its only coverage past
    elaboration, so do not demote it to the baseline to save time.
    """
    from soda import make
    make.syn()

    assert os.path.isfile('build/mm/syn-optimized/mm.pkg.json')
    assert os.path.isfile(
        'build/mm/syn-optimized/synthesis/0/outputs/forward_kernel.vg')


@pytest.mark.eda
# Measured ~12 minutes on the two cores limit_cpus leaves; detailed routing is over half.
@pytest.mark.timeout(1800)
def test_py_make_asic():
    """The baseline kernel reaches GDSII; the optimized one runs the same nodes on ~7x the cells,
    and its strategy is covered by test_py_make_elaborate and test_py_make_syn.
    """
    from soda import make
    make.asic(strategy="baseline")

    assert os.path.isfile(
        'build/mm/asic-baseline/write.gds/0/outputs/forward_kernel.gds.gz')
