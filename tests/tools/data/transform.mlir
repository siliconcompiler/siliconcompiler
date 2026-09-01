// Transform dialect schedule for the "transformed" SODA strategy.
//
// This is the identity schedule PNNL ships with the mm-no_weights example: the
// named sequence is applied to the outlined kernel by
// --transform-interpreter and then erased, so the kernel is lowered without
// any rewrite. It is the starting point for writing a real one -- tile, fuse or
// unroll the payload here and the strategy becomes a genuine alternative to the
// fixed optimization pipeline.
module @transforms attributes { transform.with_named_sequence } {
  transform.named_sequence @__transform_main(
      %root: !transform.any_op {transform.readonly}) {
    transform.yield
  }
}
