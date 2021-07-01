-- GPIO module for microwatt
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.wishbone_types.all;

entity gpio is
    generic (
        NGPIO : integer := 32
        );
    port (
        clk : in std_ulogic;
        rst : in std_ulogic;

        -- Wishbone
        wb_in  : in wb_io_master_out;
        wb_out : out wb_io_slave_out;

        -- GPIO lines
        gpio_in  : in std_ulogic_vector(NGPIO - 1 downto 0);
        gpio_out : out std_ulogic_vector(NGPIO - 1 downto 0);
        -- 1 = output, 0 = input
        gpio_dir : out std_ulogic_vector(NGPIO - 1 downto 0);

        -- Interrupt
        intr : out std_ulogic
        );
end entity gpio;

architecture behaviour of gpio is
    constant GPIO_REG_BITS  : positive := 5;

    -- Register addresses, matching addr downto 2, so 4 bytes per reg
    constant GPIO_REG_DATA_OUT : std_ulogic_vector(GPIO_REG_BITS-1 downto 0) := "00000";
    constant GPIO_REG_DATA_IN  : std_ulogic_vector(GPIO_REG_BITS-1 downto 0) := "00001";
    constant GPIO_REG_DIR      : std_ulogic_vector(GPIO_REG_BITS-1 downto 0) := "00010";
    constant GPIO_REG_DATA_SET : std_ulogic_vector(GPIO_REG_BITS-1 downto 0) := "00100";
    constant GPIO_REG_DATA_CLR : std_ulogic_vector(GPIO_REG_BITS-1 downto 0) := "00101";

    -- Current output value and direction
    signal reg_data : std_ulogic_vector(NGPIO - 1 downto 0) := (others => '0');
    signal reg_dirn : std_ulogic_vector(NGPIO - 1 downto 0) := (others => '0');
    signal reg_in1  : std_ulogic_vector(NGPIO - 1 downto 0);
    signal reg_in2  : std_ulogic_vector(NGPIO - 1 downto 0);

    signal wb_rsp   : wb_io_slave_out;
    signal reg_out  : std_ulogic_vector(NGPIO - 1 downto 0);

begin

    -- No interrupt facility for now
    intr <= '0';

    gpio_out <= reg_data;
    gpio_dir <= reg_dirn;

    -- Wishbone response
    wb_rsp.ack <= wb_in.cyc and wb_in.stb;
    with wb_in.adr(GPIO_REG_BITS + 1 downto 2) select reg_out <=
        reg_data when GPIO_REG_DATA_OUT,
        reg_in2  when GPIO_REG_DATA_IN,
        reg_dirn when GPIO_REG_DIR,
        (others => '0') when others;
    wb_rsp.dat(wb_rsp.dat'left downto NGPIO) <= (others => '0');
    wb_rsp.dat(NGPIO - 1 downto 0) <= reg_out;
    wb_rsp.stall <= '0';

    regs_rw: process(clk)
    begin
        if rising_edge(clk) then
            wb_out <= wb_rsp;
            reg_in2 <= reg_in1;
            reg_in1 <= gpio_in;
            if rst = '1' then
                reg_data <= (others => '0');
                reg_dirn <= (others => '0');
                wb_out.ack <= '0';
            else
                if wb_in.cyc = '1' and wb_in.stb = '1' and wb_in.we = '1' then
                    case wb_in.adr(GPIO_REG_BITS + 1 downto 2) is
                        when GPIO_REG_DATA_OUT =>
                            reg_data <= wb_in.dat(NGPIO - 1 downto 0);
                        when GPIO_REG_DIR =>
                            reg_dirn <= wb_in.dat(NGPIO - 1 downto 0);
                        when GPIO_REG_DATA_SET =>
                            reg_data <= reg_data or wb_in.dat(NGPIO - 1 downto 0);
                        when GPIO_REG_DATA_CLR =>
                            reg_data <= reg_data and not wb_in.dat(NGPIO - 1 downto 0);
                        when others =>
                    end case;
                end if;
            end if;
        end if;
    end process;

end architecture behaviour;
        
