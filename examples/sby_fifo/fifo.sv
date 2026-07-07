// From the SymbiYosys (sby) project examples (ISC license):
// https://github.com/YosysHQ/sby -- docs/examples/fifo/fifo.sv

// address generator/counter
module addr_gen 
#(  parameter MAX_DATA=16
) ( input en, clk, rst,
    output reg [3:0] addr
);
    initial addr <= 0;

    // async reset
    // increment address when enabled
    always @(posedge clk or posedge rst)
        if (rst)
            addr <= 0;
        else if (en) begin
            if (addr == MAX_DATA-1)
                addr <= 0;
            else
                addr <= addr + 1;
        end
endmodule

// Define our top level fifo entity
module fifo 
#(  parameter MAX_DATA=16
) ( input wen, ren, clk, rst,
    input [7:0] wdata,
    output [7:0] rdata,
    output [4:0] count,
    output full, empty
);
    wire wskip, rskip;
    reg [4:0] data_count;

    // fifo storage
    // async read, sync write
    wire [3:0] waddr, raddr;
    reg [7:0] data [MAX_DATA-1:0];
    always @(posedge clk)
        if (wen) 
            data[waddr] <= wdata;
    assign rdata = data[raddr];
    // end storage

    // addr_gen for both write and read addresses
    addr_gen #(.MAX_DATA(MAX_DATA))
    fifo_writer (
        .en     (wen || wskip),
        .clk    (clk  ),
        .rst    (rst),
        .addr   (waddr)
    );

    addr_gen #(.MAX_DATA(MAX_DATA))
    fifo_reader (
        .en     (ren || rskip),
        .clk    (clk  ),
        .rst    (rst),
        .addr   (raddr)
    );

    // status signals
    initial data_count <= 0;

    always @(posedge clk or posedge rst) begin
        if (rst)
            data_count <= 0;
        else if (wen && !ren && data_count < MAX_DATA)
            data_count <= data_count + 1;
        else if (ren && !wen && data_count > 0)
            data_count <= data_count - 1;
    end

    assign full  = data_count == MAX_DATA;
    assign empty = (data_count == 0) && ~rst;
    assign count = data_count;

    // overflow protection
`ifndef NO_FULL_SKIP
    // write while full => overwrite oldest data, move read pointer
    assign rskip = wen && !ren && data_count >= MAX_DATA;
    // read while empty => read invalid data, keep write pointer in sync
    assign wskip = ren && !wen && data_count == 0;
`else
    assign rskip = 0;
    assign wskip = 0;
`endif // NO_FULL_SKIP

`ifdef FORMAL
    // observers
    wire [4:0] addr_diff;
    assign addr_diff = waddr >= raddr 
                     ? waddr - raddr 
                     : waddr + MAX_DATA - raddr;

    // tests
    always @(posedge clk) begin
        if (~rst) begin
            // waddr and raddr can only be non zero if reset is low
            w_nreset: cover (waddr || raddr);

            // count never more than max
            a_oflow:  assert (count <= MAX_DATA);
            a_oflow2: assert (waddr < MAX_DATA);

            // count should be equal to the difference between writer and reader address
            a_count_diff: assert (count == addr_diff 
                               || count == MAX_DATA && addr_diff == 0);

            // count should only be able to increase or decrease by 1
            a_counts: assert (count == 0
                           || count == $past(count)
                           || count == $past(count) + 1
                           || count == $past(count) - 1);

            // read/write addresses can only increase (or stay the same)
            a_raddr: assert (raddr == 0
                          || raddr == $past(raddr)
                          || raddr == $past(raddr + 1));
            a_waddr: assert (waddr == 0
                          || waddr == $past(waddr)
                          || waddr == $past(waddr + 1));

            // full and empty work as expected
            a_full:  assert (!full || count == MAX_DATA);
            w_full:  cover  (wen && !ren && count == MAX_DATA-1);
            a_empty: assert (!empty || count == 0);
            w_empty: cover  (ren && !wen && count == 1);

            // reading/writing non zero values
            w_nzero_write: cover (wen && wdata);
            w_nzero_read:  cover (ren && rdata);
        end else begin
            // waddr and raddr are zero while reset is high
            a_reset: assert (!waddr && !raddr);
            w_reset: cover  (rst);

            // outputs are zero while reset is high
            a_zero_out: assert (!empty && !full && !count);
        end
    end

`ifdef VERIFIC
    // if we have verific we can also do the following additional tests
    // read/write enables enable
    ap_raddr2: assert property (@(posedge clk) disable iff (rst) ren |=> $changed(raddr));
    ap_waddr2: assert property (@(posedge clk) disable iff (rst) wen |=> $changed(waddr));

    // read/write needs enable UNLESS full/empty
    ap_raddr3: assert property (@(posedge clk) disable iff (rst) !ren && !full  |=> $stable(raddr));
    ap_waddr3: assert property (@(posedge clk) disable iff (rst) !wen && !empty |=> $stable(waddr));

    // use block formatting for w_underfill so it's easier to describe in docs
    // and is more readily comparable with the non SVA implementation
    property write_skip;
        @(posedge clk) disable iff (rst)
        !wen |=> $changed(waddr);
    endproperty
    w_underfill: cover property (write_skip);

    // look for an overfill where the value in memory changes
    // the change in data makes certain that the value is overriden
    let d_change = (wdata != rdata);
    property read_skip;
        @(posedge clk) disable iff (rst) 
        !ren && d_change |=> $changed(raddr);
    endproperty
    w_overfill:  cover property (read_skip);
`else // !VERIFIC
    // implementing w_underfill without properties
    // can't use !$past(wen) since it will always trigger in the first cycle
    reg past_nwen;
    initial past_nwen <= 0;
    always @(posedge clk) begin
        if (rst) past_nwen <= 0;
        if (!rst) begin
            w_underfill: cover (past_nwen && $changed(waddr));
            past_nwen <= !wen;
        end
    end
    // end w_underfill

    // w_overfill does the same, but has been separated so that w_underfill
    // can be included in the docs more cleanly
    reg past_nren;
    initial past_nren <= 0;
    always @(posedge clk) begin
        if (rst) past_nren <= 0;
        if (!rst) begin
            w_overfill: cover (past_nren && $changed(raddr));
            past_nren <= !ren;
        end
    end
`endif // VERIFIC

`endif // FORMAL

endmodule
