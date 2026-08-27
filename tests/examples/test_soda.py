import pytest

import os.path


def test_py_make_check():
    from soda import make
    make.check()


@pytest.mark.timeout(600)
def test_py_make_model():
    """Regenerating mm.mlir from the PyTorch model produces the file the flow reads.

    What is checked is the two things about the export the whole flow depends on:
    that the entry function is still called ``forward`` -- soda-opt outlines
    ``<function>_kernel``, so that name is what the design's topmodule has to be
    -- and that the model really came out in TOSA rather than in a torch dialect.

    model() imports torch and torch-mlir itself, so what it raises when they are
    absent is what this skips on. Neither is a SiliconCompiler dependency: they
    are in the example's own requirements.txt, and mm.mlir is checked in
    precisely so that nothing else here needs them.
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
    from soda import make
    make.syn()

    assert os.path.isfile('build/mm/syn-optimized/mm.pkg.json')
    assert os.path.isfile(
        'build/mm/syn-optimized/synthesis/0/outputs/forward_kernel.vg')


@pytest.mark.eda
@pytest.mark.timeout(3600)
def test_py_make_asic():
    from soda import make
    make.asic()

    assert os.path.isfile(
        'build/mm/asic-optimized/write.gds/0/outputs/forward_kernel.gds.gz')
