; From https://github.com/pnnl/soda-opt/blob/dec670d7d30912b711e5df016b3e6c904a41197d/docs/tutorials/tensorflow/docker-version-executed/output/baseline/visualize.ll
; ModuleID = 'input.ll'
source_filename = "LLVMDialectModule"

; Function Attrs: nofree norecurse nosync nounwind memory(argmem: readwrite)
define void @main_kernel(float* nocapture readonly %0, float* nocapture readonly %1, float* nocapture %2) local_unnamed_addr #0 {
  br label %.preheader1

.preheader1:                                      ; preds = %3, %75
  %4 = phi i64 [ 0, %3 ], [ %76, %75 ]
  %5 = shl nuw nsw i64 %4, 3
  %6 = shl nuw nsw i64 %4, 2
  %7 = getelementptr float, float* %0, i64 %5
  %8 = or i64 %5, 1
  %9 = getelementptr float, float* %0, i64 %8
  %10 = or i64 %5, 2
  %11 = getelementptr float, float* %0, i64 %10
  %12 = or i64 %5, 3
  %13 = getelementptr float, float* %0, i64 %12
  %14 = or i64 %5, 4
  %15 = getelementptr float, float* %0, i64 %14
  %16 = or i64 %5, 5
  %17 = getelementptr float, float* %0, i64 %16
  %18 = or i64 %5, 6
  %19 = getelementptr float, float* %0, i64 %18
  %20 = or i64 %5, 7
  %21 = getelementptr float, float* %0, i64 %20
  br label %.preheader

.preheader:                                       ; preds = %.preheader1, %.preheader
  %22 = phi i64 [ 0, %.preheader1 ], [ %73, %.preheader ]
  %23 = add nuw nsw i64 %22, %6
  %24 = getelementptr float, float* %2, i64 %23
  %25 = load float, float* %7, align 4
  %26 = getelementptr float, float* %1, i64 %22
  %27 = load float, float* %26, align 4
  %28 = load float, float* %24, align 4
  %29 = fmul float %25, %27
  %30 = fadd float %28, %29
  store float %30, float* %24, align 4
  %31 = load float, float* %9, align 4
  %32 = add nuw nsw i64 %22, 4
  %33 = getelementptr float, float* %1, i64 %32
  %34 = load float, float* %33, align 4
  %35 = fmul float %31, %34
  %36 = fadd float %30, %35
  store float %36, float* %24, align 4
  %37 = load float, float* %11, align 4
  %38 = add nuw nsw i64 %22, 8
  %39 = getelementptr float, float* %1, i64 %38
  %40 = load float, float* %39, align 4
  %41 = fmul float %37, %40
  %42 = fadd float %36, %41
  store float %42, float* %24, align 4
  %43 = load float, float* %13, align 4
  %44 = add nuw nsw i64 %22, 12
  %45 = getelementptr float, float* %1, i64 %44
  %46 = load float, float* %45, align 4
  %47 = fmul float %43, %46
  %48 = fadd float %42, %47
  store float %48, float* %24, align 4
  %49 = load float, float* %15, align 4
  %50 = add nuw nsw i64 %22, 16
  %51 = getelementptr float, float* %1, i64 %50
  %52 = load float, float* %51, align 4
  %53 = fmul float %49, %52
  %54 = fadd float %48, %53
  store float %54, float* %24, align 4
  %55 = load float, float* %17, align 4
  %56 = add nuw nsw i64 %22, 20
  %57 = getelementptr float, float* %1, i64 %56
  %58 = load float, float* %57, align 4
  %59 = fmul float %55, %58
  %60 = fadd float %54, %59
  store float %60, float* %24, align 4
  %61 = load float, float* %19, align 4
  %62 = add nuw nsw i64 %22, 24
  %63 = getelementptr float, float* %1, i64 %62
  %64 = load float, float* %63, align 4
  %65 = fmul float %61, %64
  %66 = fadd float %60, %65
  store float %66, float* %24, align 4
  %67 = load float, float* %21, align 4
  %68 = add nuw nsw i64 %22, 28
  %69 = getelementptr float, float* %1, i64 %68
  %70 = load float, float* %69, align 4
  %71 = fmul float %67, %70
  %72 = fadd float %66, %71
  store float %72, float* %24, align 4
  %73 = add nuw nsw i64 %22, 1
  %74 = icmp ult i64 %22, 3
  br i1 %74, label %.preheader, label %75

75:                                               ; preds = %.preheader
  %76 = add nuw nsw i64 %4, 1
  %77 = icmp ult i64 %4, 3
  br i1 %77, label %.preheader1, label %78

78:                                               ; preds = %75
  ret void
}

!llvm.module.flags = !{!0}

!0 = !{i32 2, !"Debug Info Version", i32 3}
