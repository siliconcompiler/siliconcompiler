
(* techmap_celltype = "$fa" *)
module _tech_fa (A, B, C, X, Y);
  parameter WIDTH = 1;
  (* force_downto *)
    input [WIDTH-1 : 0] A, B, C;
  (* force_downto *)
    output [WIDTH-1 : 0] X, Y;
  
  parameter _TECHMAP_CONSTVAL_A_ = WIDTH'bx;
  parameter _TECHMAP_CONSTVAL_B_ = WIDTH'bx;
  parameter _TECHMAP_CONSTVAL_C_ = WIDTH'bx;
  
  genvar i;
  generate for (i = 0; i < WIDTH; i = i + 1) begin
      if (_TECHMAP_CONSTVAL_A_[i] === 1'b0 || _TECHMAP_CONSTVAL_B_[i] === 1'b0 || _TECHMAP_CONSTVAL_C_[i] === 1'b0) begin
        if (_TECHMAP_CONSTVAL_C_[i] === 1'b0) begin
          sky130_fd_sc_hd__ha_1 halfadder_Cconst (
              .A(A[i]),
              .B(B[i]),
              .COUT(X[i]), .SUM(Y[i])
            );
        end 
        else begin
          if (_TECHMAP_CONSTVAL_B_[i] === 1'b0) begin
            sky130_fd_sc_hd__ha_1 halfadder_Bconst (
                .A(A[i]),
                .B(C[i]),
                .COUT(X[i]), .SUM(Y[i])
              );
          end
          else begin
            sky130_fd_sc_hd__ha_1 halfadder_Aconst (
                .A(B[i]),
                .B(C[i]),
                .COUT(X[i]), .SUM(Y[i])
              );
          end
        end
      end
      else begin
        sky130_fd_sc_hd__fa_1 fulladder (
            .A(A[i]), .B(B[i]), .CIN(C[i]), .COUT(X[i]), .SUM(Y[i])
          );
      end
    end endgenerate

endmodule
