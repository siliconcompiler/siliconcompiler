// Batched matrix multiply, in the TOSA dialect.
//
// This is PNNL's soda-benchmarks "mm-no_weights" model
// (examples/pytorch-to-gds/mm-no_weights/torchscript.py), a stateless
// torch.matmul over a [1, 4, 8] and a [1, 8, 4] tensor, exported through
// torch-mlir with output_type="tosa". Regenerate it with `smake model`, which
// runs the same export -- it is checked in so that the flow can be built
// without a PyTorch and torch-mlir install.
//
// The entry function must be named `forward`: soda-opt outlines the kernel it
// finds into `<function>_kernel`, and that outlined kernel -- `forward_kernel`
// -- is what Bambu synthesizes and what the design's topmodule has to be.
module attributes {torch.debug_module_name = "MM"} {
  func.func @forward(%arg0: tensor<1x4x8xf32>, %arg1: tensor<1x8x4xf32>) -> tensor<1x4x4xf32> {
    %0 = tosa.matmul %arg0, %arg1 : (tensor<1x4x8xf32>, tensor<1x8x4xf32>) -> tensor<1x4x4xf32>
    return %0 : tensor<1x4x4xf32>
  }
}
