library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.sim_console.all;

entity uart_top is
    port(
        wb_clk_i    : in std_ulogic;
        wb_rst_i    : in std_ulogic;
        wb_adr_i    : in std_ulogic_vector(2 downto 0);
        wb_dat_i    : in std_ulogic_vector(7 downto 0);
        wb_dat_o    : out std_ulogic_vector(7 downto 0);
        wb_we_i     : in std_ulogic;
        wb_stb_i    : in std_ulogic;
        wb_cyc_i    : in std_ulogic;
        wb_ack_o    : out std_ulogic;
        int_o       : out std_ulogic;
        stx_pad_o   : out std_ulogic;
        srx_pad_i   : in std_ulogic;
        rts_pad_o   : out std_ulogic;
        cts_pad_i   : in std_ulogic;
        dtr_pad_o   : out std_ulogic;
        dsr_pad_i   : in std_ulogic;
        ri_pad_i    : in std_ulogic;
        dcd_pad_i   : in std_ulogic
	);
end entity uart_top;

architecture behaviour of uart_top is

    -- Call POLL every N clocks to generate interrupts
    constant POLL_DELAY       : natural   := 100;

    -- Register definitions
    subtype reg_adr_t is std_ulogic_vector(2 downto 0);

    constant REG_IDX_RXTX     : reg_adr_t := "000";
    constant REG_IDX_IER      : reg_adr_t := "001";
    constant REG_IDX_IIR_FCR  : reg_adr_t := "010";
    constant REG_IDX_LCR      : reg_adr_t := "011";
    constant REG_IDX_MCR      : reg_adr_t := "100";
    constant REG_IDX_LSR      : reg_adr_t := "101";
    constant REG_IDX_MSR      : reg_adr_t := "110";
    constant REG_IDX_SCR      : reg_adr_t := "111";

    -- IER bits
    constant REG_IER_RDI_BIT    : natural := 0;
    constant REG_IER_THRI_BIT   : natural := 1;
    constant REG_IER_RLSI_BIT   : natural := 2;
    constant REG_IER_MSI_BIT    : natural := 3;

    -- IIR bit
    constant REG_IIR_NO_INT     : natural := 0;
    -- IIR values for bit 3 downto 0
    constant REG_IIR_RDI        : std_ulogic_vector(3 downto 1) := "010";
    constant REG_IIR_THRI       : std_ulogic_vector(3 downto 1) := "001";
    constant REG_IIR_RLSI       : std_ulogic_vector(3 downto 1) := "011";
    constant REG_IIR_MSI        : std_ulogic_vector(3 downto 1) := "000";

    -- FCR bits
    constant REG_FCR_EN_FIFO_BIT  : natural := 0;  -- Always 1
    constant REG_FCR_CLR_RCVR_BIT : natural := 1;
    constant REG_FCR_CLR_XMIT_BIT : natural := 2;
    constant REG_FCR_DMA_SEL_BIT  : natural := 3;  -- Not implemented
    -- FCR values for FIFO threshold in bits 7 downto 6
    constant REG_FCR_FIFO_TRIG1   : std_ulogic_vector(7 downto 6) := "00";
    constant REG_FCR_FIFO_TRIG4   : std_ulogic_vector(7 downto 6) := "01";
    constant REG_FCR_FIFO_TRIG8   : std_ulogic_vector(7 downto 6) := "10";
    constant REG_FCR_FIFO_TRIG14  : std_ulogic_vector(7 downto 6) := "11";

    -- LCR bits
    constant REG_LCR_STOP_BIT     : natural := 2;
    constant REG_LCR_PARITY_BIT   : natural := 3;
    constant REG_LCR_EPAR_BIT     : natural := 4;
    constant REG_LCR_SPAR_BIT     : natural := 5;
    constant REG_LCR_SBC_BIT      : natural := 6;
    constant REG_LCR_DLAB_BIT     : natural := 7;
    -- LCR values for data length (bits 1 downto 0)
    constant REG_LCR_WLEN5       : std_ulogic_vector(1 downto 0) := "00";
    constant REG_LCR_WLEN6       : std_ulogic_vector(1 downto 0) := "01";
    constant REG_LCR_WLEN7       : std_ulogic_vector(1 downto 0) := "10";
    constant REG_LCR_WLEN8       : std_ulogic_vector(1 downto 0) := "11";

    -- MCR bits
    constant REG_MCR_DTR_BIT     : natural := 0;
    constant REG_MCR_RTS_BIT     : natural := 1;
    constant REG_MCR_OUT1_BIT    : natural := 2;
    constant REG_MCR_OUT2_BIT    : natural := 3;
    constant REG_MCR_LOOP_BIT    : natural := 4;

    -- LSR bits
    constant REG_LSR_DR_BIT     : natural := 0;
    constant REG_LSR_OE_BIT     : natural := 1;
    constant REG_LSR_PE_BIT     : natural := 2;
    constant REG_LSR_FE_BIT     : natural := 3;
    constant REG_LSR_BI_BIT     : natural := 4;
    constant REG_LSR_THRE_BIT   : natural := 5;
    constant REG_LSR_TEMT_BIT   : natural := 6;
    constant REG_LSR_FIFOE_BIT  : natural := 7;

    -- MSR bits
    constant REG_MSR_DCTS_BIT    : natural := 0;
    constant REG_MSR_DDSR_BIT    : natural := 1;
    constant REG_MSR_TERI_BIT    : natural := 2;
    constant REG_MSR_DDCD_BIT    : natural := 3;
    constant REG_MSR_CTS_BIT     : natural := 4;
    constant REG_MSR_DSR_BIT     : natural := 5;
    constant REG_MSR_RI_BIT      : natural := 6;
    constant REG_MSR_DCD_BIT     : natural := 7;

    -- Wishbone signals decode:
    signal reg_idx               : reg_adr_t;
    signal wb_phase              : std_ulogic;
    signal reg_write             : std_ulogic;
    signal reg_read              : std_ulogic;

    -- Register storage
    signal reg_ier  : std_ulogic_vector(3 downto 0);
    signal reg_iir  : std_ulogic_vector(3 downto 0);
    signal reg_fcr  : std_ulogic_vector(7 downto 6);
    signal reg_lcr  : std_ulogic_vector(7 downto 0);
    signal reg_mcr  : std_ulogic_vector(4 downto 0);
    signal reg_lsr  : std_ulogic_vector(7 downto 0);
    signal reg_msr  : std_ulogic_vector(7 downto 0);
    signal reg_scr  : std_ulogic_vector(7 downto 0);

    signal reg_div  : std_ulogic_vector(15 downto 0);

    -- Control signals
    signal rx_fifo_clr : std_ulogic;
    signal tx_fifo_clr : std_ulogic;

    -- Pending interrupts
    signal int_rdi_pending  : std_ulogic;
    signal int_thri_pending : std_ulogic;
    signal int_rlsi_pending : std_ulogic;
    signal int_msi_pending  : std_ulogic;

    -- Actual data output
    signal data_out : std_ulogic_vector(7 downto 0) := x"00";

    -- Incoming data pending signal
    signal data_in_pending : std_ulogic := '0';

    -- Useful aliases
    alias dlab      : std_ulogic is reg_lcr(REG_LCR_DLAB_BIT);

    alias clk       : std_ulogic is wb_clk_i;
    alias rst       : std_ulogic is wb_rst_i;
    alias cyc       : std_ulogic is wb_cyc_i;
    alias stb       : std_ulogic is wb_stb_i;
    alias we        : std_ulogic is wb_we_i;
begin

    -- Register index shortcut
    reg_idx <= wb_adr_i(2 downto 0);

    -- 2 phases WB process.
    --
    -- Among others, this gives us a "free" cycle for the
    -- side effects of some accesses percolate in the form
    -- of status bit changes in other registers.
    wb_cycle: process(clk)
        variable phase : std_ulogic := '0';
    begin
        if rising_edge(clk) then
            if wb_phase = '0' then
                if cyc = '1' and stb = '1' then
                    wb_ack_o <= '1';
                    wb_phase <= '1';
                end if;
            else
                wb_ack_o <= '0';
                wb_phase <= '0';
            end if;
        end if;
    end process;

    -- Reg read/write signals
    reg_write <= cyc and stb and we and not wb_phase;
    reg_read  <= cyc and stb and not we and not wb_phase;

    -- Register read is synchronous to avoid collisions with
    -- read-clear side effects
    do_reg_read: process(clk)
    begin
        if rising_edge(clk) then
            wb_dat_o <= x"00";
            if reg_read = '1' then
                case reg_idx is
                when REG_IDX_RXTX =>
                    if dlab = '1' then
                        wb_dat_o <= reg_div(7 downto 0);
                    else
                        wb_dat_o <= data_out;
                    end if;
                when REG_IDX_IER =>
                    if dlab = '1' then
                        wb_dat_o <= reg_div(15 downto 8);
                    else
                        wb_dat_o <= "0000" & reg_ier;
                    end if;
                when REG_IDX_IIR_FCR =>
                    -- Top bits always set as FIFO is always enabled
                    wb_dat_o <= "1100" & reg_iir;
                when REG_IDX_LCR =>
                    wb_dat_o <= reg_lcr;
                when REG_IDX_LSR =>
                    wb_dat_o <= reg_lsr;
                when REG_IDX_MSR =>
                    wb_dat_o <= reg_msr;
                when REG_IDX_SCR =>
                    wb_dat_o <= reg_scr;
                when others =>
                end case;
            end if;
        end if;
    end process;

    -- Receive/send synchronous process
    rxtx: process(clk)
        variable dp       : std_ulogic;
        variable poll_cnt : natural;
        variable sim_tmp  : std_ulogic_vector(63 downto 0);
    begin
        if rising_edge(clk) then
            if rst = '0' then
                dp := data_in_pending;
                if dlab = '0' and reg_idx = REG_IDX_RXTX then
                    if reg_write = '1' then
                        -- FIFO write
                        -- XXX Simulate the FIFO and delays for more
                        -- accurate behaviour & interrupts
                        sim_console_write(x"00000000000000" & wb_dat_i);
                    end if;
                    if reg_read = '1' then
                        dp := '0';
                        data_out <= x"00";
                    end if;
                end if;

                -- Poll for incoming data
                if poll_cnt = 0 or (reg_read = '1' and reg_idx = REG_IDX_LSR) then
                    sim_console_poll(sim_tmp);
                    poll_cnt := POLL_DELAY;
                    if dp = '0' and sim_tmp(0) = '1' then
                        dp := '1';
                        sim_console_read(sim_tmp);
                        data_out <= sim_tmp(7 downto 0);
                    end if;
                    poll_cnt := poll_cnt - 1;
                end if;
                data_in_pending <= dp;
            end if;
        end if;
    end process;

    -- Interrupt pending bits
    int_rdi_pending  <= data_in_pending;
    int_thri_pending <= '1';
    int_rlsi_pending <= reg_lsr(REG_LSR_OE_BIT) or
                        reg_lsr(REG_LSR_PE_BIT) or
                        reg_lsr(REG_LSR_FE_BIT) or
                        reg_lsr(REG_LSR_BI_BIT);
    int_msi_pending  <= reg_msr(REG_MSR_DCTS_BIT) or
                        reg_msr(REG_MSR_DDSR_BIT) or
                        reg_msr(REG_MSR_TERI_BIT) or
                        reg_msr(REG_MSR_DDCD_BIT);

    -- Derive interrupt output from IIR
    int_o <= not reg_iir(REG_IIR_NO_INT);

    -- Divisor register
    div_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                reg_div <= (others => '0');
            elsif reg_write = '1' and dlab = '1' then
                if reg_idx = REG_IDX_RXTX then
                    reg_div(7 downto 0) <= wb_dat_i;
                elsif reg_idx = REG_IDX_IER then
                    reg_div(15 downto 8) <= wb_dat_i;
                end if;
            end if;
        end if;
    end process;

    -- IER register
    ier_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                reg_ier <= "0000";
            else
                if reg_write = '1' and dlab = '0' and reg_idx = REG_IDX_IER then
                    reg_ier <= wb_dat_i(3 downto 0);
                end if;
            end if;
        end if;
    end process;

    -- IIR (read only) generation
    iir_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            reg_iir <= "0001";
            if int_rlsi_pending = '1' and reg_ier(REG_IER_RLSI_BIT) = '1' then
                reg_iir <= REG_IIR_RLSI & "0";
            elsif int_rdi_pending = '1' and reg_ier(REG_IER_RDI_BIT) = '1' then
                reg_iir <= REG_IIR_RDI & "0";
            elsif int_thri_pending = '1' and reg_ier(REG_IER_THRI_BIT) = '1' then
                reg_iir <= REG_IIR_THRI & "0";
            elsif int_msi_pending = '1' and reg_ier(REG_IER_MSI_BIT) = '1' then
                reg_iir <= REG_IIR_MSI & "0";
            end if;

            -- It *seems* like reading IIR should clear THRI for
            -- some amount of time until it gets set again  a few
            -- clocks later if the transmitter is still empty. We
            -- don't do that at this point.
        end if;
    end process;

    -- FCR (write only) register
    fcr_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                reg_fcr <= "11";
                rx_fifo_clr <= '1';
                tx_fifo_clr <= '1';
            elsif reg_write = '1' and reg_idx = REG_IDX_IIR_FCR then
                reg_fcr <= wb_dat_i(7 downto 6);
                rx_fifo_clr <= wb_dat_i(REG_FCR_CLR_RCVR_BIT);
                tx_fifo_clr <= wb_dat_i(REG_FCR_CLR_XMIT_BIT);
            else
                rx_fifo_clr <= '0';
                tx_fifo_clr <= '0';
            end if;
        end if;
    end process;

    -- LCR register
    lcr_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                reg_lcr <= "00000011";
            elsif reg_write = '1' and reg_idx = REG_IDX_LCR then
                reg_lcr <= wb_dat_i;
            end if;
        end if;
    end process;

    -- MCR register
    mcr_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                reg_mcr <= "00000";
            elsif reg_write = '1' and reg_idx = REG_IDX_MCR then
                reg_mcr <= wb_dat_i(4 downto 0);
            end if;
        end if;
    end process;

    -- LSR register
    lsr_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                reg_lsr <= "00000000";
            else
                reg_lsr(REG_LSR_DR_BIT) <= data_in_pending;

                -- Clear error bits on read. Those bits are
                -- always 0 in sim for now.
                -- if reg_read = '1' and reg_idx = REG_IDX_LSR then
                --     reg_lsr(REG_LSR_OE_BIT)    <= '0';
                --     reg_lsr(REG_LSR_PE_BIT)    <= '0';
                --     reg_lsr(REG_LSR_FE_BIT)    <= '0';
                --     reg_lsr(REG_LSR_BI_BIT)    <= '0';
                --     reg_lsr(REG_LSR_FIFOE_BIT) <= '0';
                -- end if;

                -- Tx FIFO empty indicators. Always empty in sim
                reg_lsr(REG_LSR_THRE_BIT) <= '1';
                reg_lsr(REG_LSR_TEMT_BIT) <= '1';
            end if;
        end if;
    end process;

    -- MSR register
    msr_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                reg_msr <= "00000000";
            elsif reg_read = '1' and reg_idx = REG_IDX_MSR then
                reg_msr <= "00000000";
                -- XXX TODO bit setting machine...
            end if;
        end if;
    end process;

    -- SCR register
    scr_reg_w: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                reg_scr <= "00000000";
            elsif reg_write = '1' and reg_idx = REG_IDX_SCR then
                reg_scr <= wb_dat_i;
            end if;
        end if;
    end process;

end architecture behaviour;
