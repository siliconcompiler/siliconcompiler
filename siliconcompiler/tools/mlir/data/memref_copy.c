// Vendored from PNNL's soda-benchmarks, scripts/lib/memref_copy.c
//   https://github.com/pnnl/soda-benchmarks
//   Apache License v2.0 with LLVM Exceptions.
//
// Linked into an LLVM IR module by siliconcompiler.tools.mlir.link.LinkTask when
// that module calls memrefCopy without defining it. Bufferized MLIR lowers
// memref.copy to this call and expects MLIR's runner support library to provide
// it; an HLS backend has no runtime to link against, so the definition is merged
// into the module instead. Unlike MLIR's own implementation, this one indexes
// through fixed-size arrays rather than a dynamic alloca, which HLS backends
// reject.

#include <stdint.h>
#include <string.h>

// Maximum supported tensor rank. The examples uses rank 4 at most.
#define MAX_RANK 8

// UnrankedMemRefType: { int64_t rank, void *descriptor }
// The descriptor points to a flat struct laid out as:
//   { T *basePtr, T *data, int64_t offset, int64_t sizes[rank], int64_t strides[rank] }
// This matches the MLIR StridedMemRefType layout.

struct UnrankedMemRef {
  int64_t rank;
  void *descriptor;
};

// Parsed view into the descriptor
struct DynamicMemRef {
  int64_t rank;
  char *basePtr;
  char *data;
  int64_t offset;
  const int64_t *sizes;
  const int64_t *strides;
};

static void parseDynamicMemRef(struct DynamicMemRef *out,
                               const struct UnrankedMemRef *in) {
  out->rank = in->rank;
  // The descriptor is laid out as:
  //   ptr basePtr;    (offset 0)
  //   ptr data;       (offset 1 pointer)
  //   i64 offset;     (offset 2 pointers)
  //   i64 sizes[rank];
  //   i64 strides[rank];
  // We cast through char* to access fields.
  // On the MLIR/LLVM level, pointers and i64 are both 8 bytes (64-bit target).
  char *desc = (char *)in->descriptor;
  out->basePtr = *(char **)desc;
  out->data = *(char **)(desc + sizeof(char *));
  out->offset = *(int64_t *)(desc + 2 * sizeof(char *));
  if (in->rank == 0) {
    out->sizes = NULL;
    out->strides = NULL;
  } else {
    out->sizes = (const int64_t *)(desc + 2 * sizeof(char *) + sizeof(int64_t));
    out->strides = out->sizes + in->rank;
  }
}

void memrefCopy(int64_t elemSize, struct UnrankedMemRef *srcArg,
                struct UnrankedMemRef *dstArg) {
  struct DynamicMemRef src, dst;
  parseDynamicMemRef(&src, srcArg);
  parseDynamicMemRef(&dst, dstArg);

  int64_t rank = src.rank;

  // Handle empty shapes -> nothing to copy.
  for (int64_t rankp = 0; rankp < rank; ++rankp)
    if (src.sizes[rankp] == 0)
      return;

  char *srcPtr = src.data + src.offset * elemSize;
  char *dstPtr = dst.data + dst.offset * elemSize;

  if (rank == 0) {
    memcpy(dstPtr, srcPtr, elemSize);
    return;
  }

  // Fixed-size arrays to avoid dynamic alloca (unsupported by HLS backends).
  int64_t indices[MAX_RANK];
  int64_t srcStrides[MAX_RANK];
  int64_t dstStrides[MAX_RANK];

  // Initialize index and scale strides.
  for (int64_t rankp = 0; rankp < rank; ++rankp) {
    indices[rankp] = 0;
    srcStrides[rankp] = src.strides[rankp] * elemSize;
    dstStrides[rankp] = dst.strides[rankp] * elemSize;
  }

  int64_t readIndex = 0, writeIndex = 0;
  for (;;) {
    // Copy over the element, byte by byte.
    memcpy(dstPtr + writeIndex, srcPtr + readIndex, elemSize);
    // Advance index and read position.
    for (int64_t axis = rank - 1; axis >= 0; --axis) {
      // Advance at current axis.
      int64_t newIndex = ++indices[axis];
      readIndex += srcStrides[axis];
      writeIndex += dstStrides[axis];
      // If this is a valid index, we have our next index, so continue copying.
      if (src.sizes[axis] != newIndex)
        break;
      // We reached the end of this axis. If this is axis 0, we are done.
      if (axis == 0)
        return;
      // Else, reset to 0 and undo the advancement of the linear index that
      // this axis had. Then continue with the axis one outer.
      indices[axis] = 0;
      readIndex -= src.sizes[axis] * srcStrides[axis];
      writeIndex -= dst.sizes[axis] * dstStrides[axis];
    }
  }
}
