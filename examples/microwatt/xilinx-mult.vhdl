library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;

library unisim;
use unisim.vcomponents.all;

entity multiply is
    port (
        clk   : in std_logic;

        m_in  : in MultiplyInputType;
        m_out : out MultiplyOutputType
        );
end entity multiply;

architecture behaviour of multiply is
    signal m00_p, m01_p, m02_p, m03_p : std_ulogic_vector(47 downto 0);
    signal m00_pc : std_ulogic_vector(47 downto 0);
    signal m10_p, m11_p, m12_p, m13_p : std_ulogic_vector(47 downto 0);
    signal m11_pc, m12_pc, m13_pc : std_ulogic_vector(47 downto 0);
    signal m20_p, m21_p, m22_p, m23_p : std_ulogic_vector(47 downto 0);
    signal s0_pc, s1_pc : std_ulogic_vector(47 downto 0);
    signal product_lo : std_ulogic_vector(31 downto 0);
    signal product : std_ulogic_vector(127 downto 0);
    signal addend : std_ulogic_vector(127 downto 0);
    signal s0_carry, p0_carry : std_ulogic_vector(3 downto 0);
    signal p0_mask : std_ulogic_vector(47 downto 0);
    signal p0_pat, p0_patb : std_ulogic;
    signal p1_pat, p1_patb : std_ulogic;

    signal req_32bit, r32_1 : std_ulogic;
    signal req_not, rnot_1 : std_ulogic;
    signal valid_1 : std_ulogic;
    signal overflow, ovf_in : std_ulogic;

begin
    addend <= m_in.addend;

    m00: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "0000000" & m_in.data1(22 downto 0),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(16 downto 0),
            BCIN => (others => '0'),
            C => "00000000000000" & addend(33 downto 0),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0110101",
            P => m00_p,
            PCIN => (others => '0'),
            PCOUT => m00_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m01: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "0000000" & m_in.data1(22 downto 0),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(33 downto 17),
            BCIN => (others => '0'),
            C => (others => '0'),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "1010101",
            P => m01_p,
            PCIN => m00_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m02: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "0000000" & m_in.data1(22 downto 0),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(50 downto 34),
            BCIN => (others => '0'),
            C => x"0000000" & "000" & addend(50 downto 34),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0110101",
            P => m02_p,
            PCIN => (others => '0'),
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m03: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "0000000" & m_in.data1(22 downto 0),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => "00000" & m_in.data2(63 downto 51),
            BCIN => (others => '0'),
            C => x"000000" & '0' & addend(73 downto 51),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0110101",
            P => m03_p,
            PCIN => (others => '0'),
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m10: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            CREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "0000000000000" & m_in.data1(39 downto 23),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(16 downto 0),
            BCIN => (others => '0'),
            C => x"000" & "00" & m01_p(39 downto 6),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '0',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0110101",
            P => m10_p,
            PCIN => (others => '0'),
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m11: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            CREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "0000000000000" & m_in.data1(39 downto 23),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(33 downto 17),
            BCIN => (others => '0'),
            C => x"000" & "00" & m02_p(39 downto 6),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '0',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0110101",
            P => m11_p,
            PCIN => (others => '0'),
            PCOUT => m11_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m12: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            CREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "0000000000000" & m_in.data1(39 downto 23),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(50 downto 34),
            BCIN => (others => '0'),
            C => x"0000" & '0' & m03_p(36 downto 6),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '0',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0110101",
            P => m12_p,
            PCIN => (others => '0'),
            PCOUT => m12_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m13: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "0000000000000" & m_in.data1(39 downto 23),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => "00000" & m_in.data2(63 downto 51),
            BCIN => (others => '0'),
            C => x"0000000" & "000" & addend(90 downto 74),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0110101",
            P => m13_p,
            PCIN => (others => '0'),
            PCOUT => m13_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m20: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "000000" & m_in.data1(63 downto 40),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(16 downto 0),
            BCIN => (others => '0'),
            C => (others => '0'),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0010101",
            P => m20_p,
            PCIN => m11_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m21: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "000000" & m_in.data1(63 downto 40),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(33 downto 17),
            BCIN => (others => '0'),
            C => (others => '0'),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0010101",
            P => m21_p,
            PCIN => m12_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m22: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "000000" & m_in.data1(63 downto 40),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => '0' & m_in.data2(50 downto 34),
            BCIN => (others => '0'),
            C => (others => '0'),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0010101",
            P => m22_p,
            PCIN => m13_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    m23: DSP48E1
        generic map (
            ACASCREG => 0,
            ALUMODEREG => 0,
            AREG => 0,
            BCASCREG => 0,
            BREG => 0,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            INMODEREG => 0,
            OPMODEREG => 0,
            PREG => 0
            )
        port map (
            A => "000000" & m_in.data1(63 downto 40),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => "00000" & m_in.data2(63 downto 51),
            BCIN => (others => '0'),
            C => x"00" & "000" & addend(127 downto 91),
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => '0',
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => '0',
            CEC => '1',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => m_in.valid,
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0110101",
            P => m23_p,
            PCIN => (others => '0'),
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    s0: DSP48E1
        generic map (
            ACASCREG => 1,
            ALUMODEREG => 0,
            AREG => 1,
            BCASCREG => 1,
            BREG => 1,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            CREG => 1,
            INMODEREG => 0,
            MREG => 0,
            OPMODEREG => 0,
            PREG => 0,
            USE_MULT => "none"
            )
        port map (
            A => m22_p(5 downto 0) & x"0000" & m10_p(34 downto 27),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => m10_p(26 downto 9),
            BCIN => (others => '0'),
            C => m20_p(39 downto 0) & m02_p(5 downto 0) & "00",
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CARRYOUT => s0_carry,
            CEA1 => '0',
            CEA2 => valid_1,
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => valid_1,
            CEC => valid_1,
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => '0',
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0001111",
            PCIN => (others => '0'),
            PCOUT => s0_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    s1: DSP48E1
        generic map (
            ACASCREG => 1,
            ALUMODEREG => 0,
            AREG => 1,
            BCASCREG => 1,
            BREG => 1,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            CREG => 1,
            INMODEREG => 0,
            MREG => 0,
            OPMODEREG => 0,
            PREG => 0,
            USE_MULT => "none"
            )
        port map (
            A => x"000" & m22_p(41 downto 24),
            ACIN => (others => '0'),
            ALUMODE => "0000",
            B => m22_p(23 downto 6),
            BCIN => (others => '0'),
            C => m23_p(36 downto 0) & x"00" & "0" & m20_p(41 downto 40),
            CARRYCASCIN => '0',
            CARRYIN => s0_carry(3),
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => valid_1,
            CEAD => '0',
            CEALUMODE => '0',
            CEB1 => '0',
            CEB2 => valid_1,
            CEC => valid_1,
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => '0',
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0001111",
            PCIN => (others => '0'),
            PCOUT => s1_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    -- mask is 0 for 32-bit ops, 0x0000ffffffff for 64-bit
    p0_mask(47 downto 31) <= (others => '0');
    p0_mask(30 downto 0) <= (others => not r32_1);

    p0: DSP48E1
        generic map (
            ACASCREG => 1,
            ALUMODEREG => 1,
            AREG => 1,
            BCASCREG => 1,
            BREG => 1,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            CREG => 1,
            INMODEREG => 0,
            MREG => 0,
            OPMODEREG => 0,
            PREG => 0,
            SEL_MASK => "C",
            USE_MULT => "none",
            USE_PATTERN_DETECT => "PATDET"
            )
        port map (
            A => m21_p(22 downto 0) & m03_p(5 downto 0) & '0',
            ACIN => (others => '0'),
            ALUMODE => "00" & rnot_1 & '0',
            B => (others => '0'),
            BCIN => (others => '0'),
            C => p0_mask,
            CARRYCASCIN => '0',
            CARRYIN => '0',
            CARRYINSEL => "000",
            CARRYOUT => p0_carry,
            CEA1 => '0',
            CEA2 => valid_1,
            CEAD => '0',
            CEALUMODE => valid_1,
            CEB1 => '0',
            CEB2 => valid_1,
            CEC => valid_1,
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => '0',
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0010011",
            P => product(79 downto 32),
            PATTERNDETECT => p0_pat,
            PATTERNBDETECT => p0_patb,
            PCIN => s0_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    p1: DSP48E1
        generic map (
            ACASCREG => 1,
            ALUMODEREG => 1,
            AREG => 1,
            BCASCREG => 1,
            BREG => 1,
            CARRYINREG => 0,
            CARRYINSELREG => 0,
            CREG => 0,
            INMODEREG => 0,
            MASK => x"000000000000",
            MREG => 0,
            OPMODEREG => 0,
            PREG => 0,
            USE_MULT => "none",
            USE_PATTERN_DETECT => "PATDET"
            )
        port map (
            A => x"0000000" & '0' & m21_p(41),
            ACIN => (others => '0'),
            ALUMODE => "00" & rnot_1 & '0',
            B => m21_p(40 downto 23),
            BCIN => (others => '0'),
            C => (others => '0'),
            CARRYCASCIN => '0',
            CARRYIN => p0_carry(3),
            CARRYINSEL => "000",
            CEA1 => '0',
            CEA2 => valid_1,
            CEAD => '0',
            CEALUMODE => valid_1,
            CEB1 => '0',
            CEB2 => valid_1,
            CEC => '0',
            CECARRYIN => '0',
            CECTRL => '0',
            CED => '0',
            CEINMODE => '0',
            CEM => '0',
            CEP => '0',
            CLK => clk,
            D => (others => '0'),
            INMODE => "00000",
            MULTSIGNIN => '0',
            OPMODE => "0010011",
            P => product(127 downto 80),
            PATTERNDETECT => p1_pat,
            PATTERNBDETECT => p1_patb,
            PCIN => s1_pc,
            RSTA => '0',
            RSTALLCARRYIN => '0',
            RSTALUMODE => '0',
            RSTB => '0',
            RSTC => '0',
            RSTCTRL => '0',
            RSTD => '0',
            RSTINMODE => '0',
            RSTM => '0',
            RSTP => '0'
            );

    product(31 downto 0) <= product_lo xor (31 downto 0 => req_not);

    mult_out: process(all)
        variable ov : std_ulogic;
    begin
        -- set overflow if the high bits are neither all zeroes nor all ones
        if req_32bit = '0' then
            ov := not ((p1_pat and p0_pat) or (p1_patb and p0_patb));
        else
            ov := not ((p1_pat and p0_pat and not product(31)) or
                       (p1_patb and p0_patb and product(31)));
        end if;
        ovf_in <= ov;

        m_out.result <= product;
        m_out.overflow <= overflow;
    end process;

    process(clk)
    begin
        if rising_edge(clk) then
            product_lo <= m10_p(8 downto 0) & m01_p(5 downto 0) & m00_p(16 downto 0);
            m_out.valid <= valid_1;
            valid_1 <= m_in.valid;
            req_32bit <= r32_1;
            r32_1 <= m_in.is_32bit;
            req_not <= rnot_1;
            rnot_1 <= m_in.not_result;
            overflow <= ovf_in;
        end if;
    end process;

end architecture behaviour;
