// This module compares two 32-bit values A and B. LT is '1' if A < B 
// and EQ is '1'if A = B. LT and GT are both '0' if A > B.
//
// J. E. Stine and M. J. Schulte, "A combined two's complement and
// floating-point comparator," 2005 IEEE International Symposium on
// Circuits and Systems, Kobe, 2005, pp. 89-92 Vol. 1. 
// doi: 10.1109/ISCAS.2005.1464531

module magcompare32 (GT, LT, EQ, A, B);

   input wire [31:0] A;
   input wire [31:0] B;
   
   output wire       LT;
   output wire       EQ;
   output wire       GT;   
   
   wire [15:0]       s;
   wire [15:0]       t;
   wire [7:0] 	      u;
   wire [7:0] 	      v;
   wire [3:0] 	      w;
   wire [3:0] 	      x;
   wire [1:0] 	      y;
   wire [1:0] 	      z;
   
   magcompare2b mag1(s[0], t[0], A[1:0], B[1:0]);
   magcompare2b mag2(s[1], t[1], A[3:2], B[3:2]);
   magcompare2b mag3(s[2], t[2], A[5:4], B[5:4]);
   magcompare2b mag4(s[3], t[3], A[7:6], B[7:6]);
   magcompare2b mag5(s[4], t[4], A[9:8], B[9:8]);
   magcompare2b mag6(s[5], t[5], A[11:10], B[11:10]);
   magcompare2b mag7(s[6], t[6], A[13:12], B[13:12]);
   magcompare2b mag8(s[7], t[7], A[15:14], B[15:14]);
   magcompare2b mag9(s[8], t[8], A[17:16], B[17:16]);
   magcompare2b magA(s[9], t[9], A[19:18], B[19:18]);
   magcompare2b magB(s[10], t[10], A[21:20], B[21:20]);
   magcompare2b magC(s[11], t[11], A[23:22], B[23:22]);
   magcompare2b magD(s[12], t[12], A[25:24], B[25:24]);
   magcompare2b magE(s[13], t[13], A[27:26], B[27:26]);
   magcompare2b magF(s[14], t[14], A[29:28], B[29:28]);
   magcompare2b mag10(s[15], t[15], A[31:30], B[31:30]);

   magcompare2c mag21(u[0], v[0], t[1:0], s[1:0]);
   magcompare2c mag22(u[1], v[1], t[3:2], s[3:2]);
   magcompare2c mag23(u[2], v[2], t[5:4], s[5:4]);
   magcompare2c mag24(u[3], v[3], t[7:6], s[7:6]);
   magcompare2c mag25(u[4], v[4], t[9:8], s[9:8]);
   magcompare2c mag26(u[5], v[5], t[11:10], s[11:10]);
   magcompare2c mag27(u[6], v[6], t[13:12], s[13:12]);
   magcompare2c mag28(u[7], v[7], t[15:14], s[15:14]);

   magcompare2c mag31(w[0], x[0], v[1:0], u[1:0]);
   magcompare2c mag32(w[1], x[1], v[3:2], u[3:2]);
   magcompare2c mag33(w[2], x[2], v[5:4], u[5:4]);
   magcompare2c mag34(w[3], x[3], v[7:6], u[7:6]);
   
   magcompare2c mag39(y[0], z[0], x[1:0], w[1:0]);
   magcompare2c mag3A(y[1], z[1], x[3:2], w[3:2]);
   
   magcompare2c mag3F(LT, GT, z[1:0], y[1:0]);
   
   assign EQ = ~(LT | GT);

endmodule // magcompare32
