
`timescale 1ns/1ps
`default_nettype none

module GPIO (
		// Wrapper ports
		output 	wire [15:0] WGPIODIN,
        input 	wire [15:0] WGPIODOUT,
        input 	wire [15:0] WGPIOPU,
        input 	wire [15:0] WGPIOPD,
        input 	wire [15:0] WGPIODIR,		
		// Externals
        input 	wire [15:0] GPIOIN,
        output 	wire [15:0] GPIOOUT,
        output 	wire [15:0] GPIOPU,
        output 	wire [15:0] GPIOPD,
        output 	wire [15:0] GPIOOEN		
);
		assign GPIOOEN 	= WGPIODIR;
		assign GPIOPU 	= WGPIOPU;
		assign GPIOPD 	= WGPIOPD;
		assign GPIOOUT	= WGPIODOUT;
		assign WGPIODIN = GPIOIN;
endmodule