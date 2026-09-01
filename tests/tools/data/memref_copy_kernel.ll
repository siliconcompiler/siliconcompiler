; A kernel that calls memrefCopy without defining it, which is the case the
; link task exists for: bufferized MLIR lowers memref.copy to this call and
; expects MLIR's runner support library to provide it, which an HLS backend has
; no way to link against.
declare void @memrefCopy(i64, ptr, ptr)

define void @copy_kernel(ptr %0, ptr %1) {
  call void @memrefCopy(i64 4, ptr %0, ptr %1)
  ret void
}
