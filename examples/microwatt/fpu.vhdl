-- Floating-point unit for Microwatt

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.insn_helpers.all;
use work.decode_types.all;
use work.crhelpers.all;
use work.helpers.all;
use work.common.all;

entity fpu is
    port (
        clk : in std_ulogic;
        rst : in std_ulogic;

        e_in  : in  Execute1toFPUType;
        e_out : out FPUToExecute1Type;

        w_out : out FPUToWritebackType
        );
end entity fpu;

architecture behaviour of fpu is
    type fp_number_class is (ZERO, FINITE, INFINITY, NAN);

    constant EXP_BITS : natural := 13;

    type fpu_reg_type is record
        class    : fp_number_class;
        negative : std_ulogic;
        exponent : signed(EXP_BITS-1 downto 0);         -- unbiased
        mantissa : std_ulogic_vector(63 downto 0);      -- 10.54 format
    end record;

    type state_t is (IDLE,
                     DO_MCRFS, DO_MTFSB, DO_MTFSFI, DO_MFFS, DO_MTFSF,
                     DO_FMR, DO_FMRG, DO_FCMP, DO_FTDIV, DO_FTSQRT,
                     DO_FCFID, DO_FCTI,
                     DO_FRSP, DO_FRI,
                     DO_FADD, DO_FMUL, DO_FDIV, DO_FSQRT, DO_FMADD,
                     DO_FRE, DO_FRSQRTE,
                     DO_FSEL,
                     FRI_1,
                     ADD_1, ADD_SHIFT, ADD_2, ADD_3,
                     CMP_1, CMP_2,
                     MULT_1,
                     FMADD_1, FMADD_2, FMADD_3,
                     FMADD_4, FMADD_5, FMADD_6,
                     LOOKUP,
                     DIV_2, DIV_3, DIV_4, DIV_5, DIV_6,
                     FRE_1,
                     RSQRT_1,
                     FTDIV_1,
                     SQRT_1, SQRT_2, SQRT_3, SQRT_4,
                     SQRT_5, SQRT_6, SQRT_7, SQRT_8,
                     SQRT_9, SQRT_10, SQRT_11, SQRT_12,
                     INT_SHIFT, INT_ROUND, INT_ISHIFT,
                     INT_FINAL, INT_CHECK, INT_OFLOW,
                     FINISH, NORMALIZE,
                     ROUND_UFLOW, ROUND_OFLOW,
                     ROUNDING, ROUNDING_2, ROUNDING_3,
                     DENORM,
                     RENORM_A, RENORM_A2,
                     RENORM_B, RENORM_B2,
                     RENORM_C, RENORM_C2,
                     NAN_RESULT, EXC_RESULT);

    type reg_type is record
        state        : state_t;
        busy         : std_ulogic;
        instr_done   : std_ulogic;
        do_intr      : std_ulogic;
        illegal      : std_ulogic;
        op           : insn_type_t;
        insn         : std_ulogic_vector(31 downto 0);
        nia          : std_ulogic_vector(63 downto 0);
        instr_tag    : instr_tag_t;
        dest_fpr     : gspr_index_t;
        fe_mode      : std_ulogic;
        rc           : std_ulogic;
        is_cmp       : std_ulogic;
        single_prec  : std_ulogic;
        fpscr        : std_ulogic_vector(31 downto 0);
        a            : fpu_reg_type;
        b            : fpu_reg_type;
        c            : fpu_reg_type;
        r            : std_ulogic_vector(63 downto 0);  -- 10.54 format
        s            : std_ulogic_vector(55 downto 0);  -- extended fraction
        x            : std_ulogic;
        p            : std_ulogic_vector(63 downto 0);  -- 8.56 format
        y            : std_ulogic_vector(63 downto 0);  -- 8.56 format
        result_sign  : std_ulogic;
        result_class : fp_number_class;
        result_exp   : signed(EXP_BITS-1 downto 0);
        shift        : signed(EXP_BITS-1 downto 0);
        writing_back : std_ulogic;
        int_result   : std_ulogic;
        cr_result    : std_ulogic_vector(3 downto 0);
        cr_mask      : std_ulogic_vector(7 downto 0);
        old_exc      : std_ulogic_vector(4 downto 0);
        update_fprf  : std_ulogic;
        quieten_nan  : std_ulogic;
        tiny         : std_ulogic;
        denorm       : std_ulogic;
        round_mode   : std_ulogic_vector(2 downto 0);
        is_subtract  : std_ulogic;
        exp_cmp      : std_ulogic;
        madd_cmp     : std_ulogic;
        add_bsmall   : std_ulogic;
        is_multiply  : std_ulogic;
        is_sqrt      : std_ulogic;
        first        : std_ulogic;
        count        : unsigned(1 downto 0);
        doing_ftdiv  : std_ulogic_vector(1 downto 0);
        opsel_a      : std_ulogic_vector(1 downto 0);
        use_a        : std_ulogic;
        use_b        : std_ulogic;
        use_c        : std_ulogic;
        invalid      : std_ulogic;
        negate       : std_ulogic;
        longmask     : std_ulogic;
    end record;

    type lookup_table is array(0 to 1023) of std_ulogic_vector(17 downto 0);

    signal r, rin : reg_type;

    signal fp_result     : std_ulogic_vector(63 downto 0);
    signal opsel_b       : std_ulogic_vector(1 downto 0);
    signal opsel_r       : std_ulogic_vector(1 downto 0);
    signal opsel_s       : std_ulogic_vector(1 downto 0);
    signal opsel_ainv    : std_ulogic;
    signal opsel_mask    : std_ulogic;
    signal opsel_binv    : std_ulogic;
    signal in_a          : std_ulogic_vector(63 downto 0);
    signal in_b          : std_ulogic_vector(63 downto 0);
    signal result        : std_ulogic_vector(63 downto 0);
    signal carry_in      : std_ulogic;
    signal lost_bits     : std_ulogic;
    signal r_hi_nz       : std_ulogic;
    signal r_lo_nz       : std_ulogic;
    signal s_nz          : std_ulogic;
    signal misc_sel      : std_ulogic_vector(3 downto 0);
    signal f_to_multiply : MultiplyInputType;
    signal multiply_to_f : MultiplyOutputType;
    signal msel_1        : std_ulogic_vector(1 downto 0);
    signal msel_2        : std_ulogic_vector(1 downto 0);
    signal msel_add      : std_ulogic_vector(1 downto 0);
    signal msel_inv      : std_ulogic;
    signal inverse_est   : std_ulogic_vector(18 downto 0);

    -- opsel values
    constant AIN_R    : std_ulogic_vector(1 downto 0) := "00";
    constant AIN_A    : std_ulogic_vector(1 downto 0) := "01";
    constant AIN_B    : std_ulogic_vector(1 downto 0) := "10";
    constant AIN_C    : std_ulogic_vector(1 downto 0) := "11";

    constant BIN_ZERO : std_ulogic_vector(1 downto 0) := "00";
    constant BIN_R    : std_ulogic_vector(1 downto 0) := "01";
    constant BIN_RND  : std_ulogic_vector(1 downto 0) := "10";
    constant BIN_PS6  : std_ulogic_vector(1 downto 0) := "11";

    constant RES_SUM   : std_ulogic_vector(1 downto 0) := "00";
    constant RES_SHIFT : std_ulogic_vector(1 downto 0) := "01";
    constant RES_MULT  : std_ulogic_vector(1 downto 0) := "10";
    constant RES_MISC  : std_ulogic_vector(1 downto 0) := "11";

    constant S_ZERO  : std_ulogic_vector(1 downto 0) := "00";
    constant S_NEG   : std_ulogic_vector(1 downto 0) := "01";
    constant S_SHIFT : std_ulogic_vector(1 downto 0) := "10";
    constant S_MULT  : std_ulogic_vector(1 downto 0) := "11";

    -- msel values
    constant MUL1_A : std_ulogic_vector(1 downto 0) := "00";
    constant MUL1_B : std_ulogic_vector(1 downto 0) := "01";
    constant MUL1_Y : std_ulogic_vector(1 downto 0) := "10";
    constant MUL1_R : std_ulogic_vector(1 downto 0) := "11";

    constant MUL2_C   : std_ulogic_vector(1 downto 0) := "00";
    constant MUL2_LUT : std_ulogic_vector(1 downto 0) := "01";
    constant MUL2_P   : std_ulogic_vector(1 downto 0) := "10";
    constant MUL2_R   : std_ulogic_vector(1 downto 0) := "11";

    constant MULADD_ZERO  : std_ulogic_vector(1 downto 0) := "00";
    constant MULADD_CONST : std_ulogic_vector(1 downto 0) := "01";
    constant MULADD_A     : std_ulogic_vector(1 downto 0) := "10";
    constant MULADD_RS    : std_ulogic_vector(1 downto 0) := "11";

    -- Inverse lookup table, indexed by the top 8 fraction bits
    -- The first 256 entries are the reciprocal (1/x) lookup table,
    -- and the remaining 768 entries are the reciprocal square root table.
    -- Output range is [0.5, 1) in 0.19 format, though the top
    -- bit isn't stored since it is always 1.
    -- Each output value is the inverse of the center of the input
    -- range for the value, i.e. entry 0 is 1 / (1 + 1/512),
    -- entry 1 is 1 / (1 + 3/512), etc.
    signal inverse_table : lookup_table := (
        -- 1/x lookup table
        -- Unit bit is assumed to be 1, so input range is [1, 2)
        18x"3fc01", 18x"3f411", 18x"3ec31", 18x"3e460", 18x"3dc9f", 18x"3d4ec", 18x"3cd49", 18x"3c5b5",
        18x"3be2f", 18x"3b6b8", 18x"3af4f", 18x"3a7f4", 18x"3a0a7", 18x"39968", 18x"39237", 18x"38b14",
        18x"383fe", 18x"37cf5", 18x"375f9", 18x"36f0a", 18x"36828", 18x"36153", 18x"35a8a", 18x"353ce",
        18x"34d1e", 18x"3467a", 18x"33fe3", 18x"33957", 18x"332d7", 18x"32c62", 18x"325f9", 18x"31f9c",
        18x"3194a", 18x"31303", 18x"30cc7", 18x"30696", 18x"30070", 18x"2fa54", 18x"2f443", 18x"2ee3d",
        18x"2e841", 18x"2e250", 18x"2dc68", 18x"2d68b", 18x"2d0b8", 18x"2caee", 18x"2c52e", 18x"2bf79",
        18x"2b9cc", 18x"2b429", 18x"2ae90", 18x"2a900", 18x"2a379", 18x"29dfb", 18x"29887", 18x"2931b",
        18x"28db8", 18x"2885e", 18x"2830d", 18x"27dc4", 18x"27884", 18x"2734d", 18x"26e1d", 18x"268f6",
        18x"263d8", 18x"25ec1", 18x"259b3", 18x"254ac", 18x"24fad", 18x"24ab7", 18x"245c8", 18x"240e1",
        18x"23c01", 18x"23729", 18x"23259", 18x"22d90", 18x"228ce", 18x"22413", 18x"21f60", 18x"21ab4",
        18x"2160f", 18x"21172", 18x"20cdb", 18x"2084b", 18x"203c2", 18x"1ff40", 18x"1fac4", 18x"1f64f",
        18x"1f1e1", 18x"1ed79", 18x"1e918", 18x"1e4be", 18x"1e069", 18x"1dc1b", 18x"1d7d4", 18x"1d392",
        18x"1cf57", 18x"1cb22", 18x"1c6f3", 18x"1c2ca", 18x"1bea7", 18x"1ba8a", 18x"1b672", 18x"1b261",
        18x"1ae55", 18x"1aa50", 18x"1a64f", 18x"1a255", 18x"19e60", 18x"19a70", 18x"19686", 18x"192a2",
        18x"18ec3", 18x"18ae9", 18x"18715", 18x"18345", 18x"17f7c", 18x"17bb7", 18x"177f7", 18x"1743d",
        18x"17087", 18x"16cd7", 18x"1692c", 18x"16585", 18x"161e4", 18x"15e47", 18x"15ab0", 18x"1571d",
        18x"1538e", 18x"15005", 18x"14c80", 18x"14900", 18x"14584", 18x"1420d", 18x"13e9b", 18x"13b2d",
        18x"137c3", 18x"1345e", 18x"130fe", 18x"12da2", 18x"12a4a", 18x"126f6", 18x"123a7", 18x"1205c",
        18x"11d15", 18x"119d2", 18x"11694", 18x"11359", 18x"11023", 18x"10cf1", 18x"109c2", 18x"10698",
        18x"10372", 18x"10050", 18x"0fd31", 18x"0fa17", 18x"0f700", 18x"0f3ed", 18x"0f0de", 18x"0edd3",
        18x"0eacb", 18x"0e7c7", 18x"0e4c7", 18x"0e1ca", 18x"0ded2", 18x"0dbdc", 18x"0d8eb", 18x"0d5fc",
        18x"0d312", 18x"0d02b", 18x"0cd47", 18x"0ca67", 18x"0c78a", 18x"0c4b1", 18x"0c1db", 18x"0bf09",
        18x"0bc3a", 18x"0b96e", 18x"0b6a5", 18x"0b3e0", 18x"0b11e", 18x"0ae5f", 18x"0aba3", 18x"0a8eb",
        18x"0a636", 18x"0a383", 18x"0a0d4", 18x"09e28", 18x"09b80", 18x"098da", 18x"09637", 18x"09397",
        18x"090fb", 18x"08e61", 18x"08bca", 18x"08936", 18x"086a5", 18x"08417", 18x"0818c", 18x"07f04",
        18x"07c7e", 18x"079fc", 18x"0777c", 18x"074ff", 18x"07284", 18x"0700d", 18x"06d98", 18x"06b26",
        18x"068b6", 18x"0664a", 18x"063e0", 18x"06178", 18x"05f13", 18x"05cb1", 18x"05a52", 18x"057f5",
        18x"0559a", 18x"05342", 18x"050ed", 18x"04e9a", 18x"04c4a", 18x"049fc", 18x"047b0", 18x"04567",
        18x"04321", 18x"040dd", 18x"03e9b", 18x"03c5c", 18x"03a1f", 18x"037e4", 18x"035ac", 18x"03376",
        18x"03142", 18x"02f11", 18x"02ce2", 18x"02ab5", 18x"0288b", 18x"02663", 18x"0243d", 18x"02219",
        18x"01ff7", 18x"01dd8", 18x"01bbb", 18x"019a0", 18x"01787", 18x"01570", 18x"0135b", 18x"01149",
        18x"00f39", 18x"00d2a", 18x"00b1e", 18x"00914", 18x"0070c", 18x"00506", 18x"00302", 18x"00100",
        -- 1/sqrt(x) lookup table
        -- Input is in the range [1, 4), i.e. two bits to the left of the
        -- binary point.  Those 2 bits index the following 3 blocks of 256 values.
        -- 1.0 ... 1.9999
        18x"3fe00", 18x"3fa06", 18x"3f612", 18x"3f224", 18x"3ee3a", 18x"3ea58", 18x"3e67c", 18x"3e2a4",
        18x"3ded2", 18x"3db06", 18x"3d73e", 18x"3d37e", 18x"3cfc2", 18x"3cc0a", 18x"3c85a", 18x"3c4ae",
        18x"3c106", 18x"3bd64", 18x"3b9c8", 18x"3b630", 18x"3b29e", 18x"3af10", 18x"3ab86", 18x"3a802",
        18x"3a484", 18x"3a108", 18x"39d94", 18x"39a22", 18x"396b6", 18x"3934e", 18x"38fea", 18x"38c8c",
        18x"38932", 18x"385dc", 18x"3828a", 18x"37f3e", 18x"37bf6", 18x"378b2", 18x"37572", 18x"37236",
        18x"36efe", 18x"36bca", 18x"3689a", 18x"36570", 18x"36248", 18x"35f26", 18x"35c06", 18x"358ea",
        18x"355d4", 18x"352c0", 18x"34fb0", 18x"34ca4", 18x"3499c", 18x"34698", 18x"34398", 18x"3409c",
        18x"33da2", 18x"33aac", 18x"337bc", 18x"334cc", 18x"331e2", 18x"32efc", 18x"32c18", 18x"32938",
        18x"3265a", 18x"32382", 18x"320ac", 18x"31dd8", 18x"31b0a", 18x"3183e", 18x"31576", 18x"312b0",
        18x"30fee", 18x"30d2e", 18x"30a74", 18x"307ba", 18x"30506", 18x"30254", 18x"2ffa4", 18x"2fcf8",
        18x"2fa4e", 18x"2f7a8", 18x"2f506", 18x"2f266", 18x"2efca", 18x"2ed2e", 18x"2ea98", 18x"2e804",
        18x"2e572", 18x"2e2e4", 18x"2e058", 18x"2ddce", 18x"2db48", 18x"2d8c6", 18x"2d646", 18x"2d3c8",
        18x"2d14c", 18x"2ced4", 18x"2cc5e", 18x"2c9ea", 18x"2c77a", 18x"2c50c", 18x"2c2a2", 18x"2c038",
        18x"2bdd2", 18x"2bb70", 18x"2b90e", 18x"2b6b0", 18x"2b454", 18x"2b1fa", 18x"2afa4", 18x"2ad4e",
        18x"2aafc", 18x"2a8ac", 18x"2a660", 18x"2a414", 18x"2a1cc", 18x"29f86", 18x"29d42", 18x"29b00",
        18x"298c2", 18x"29684", 18x"2944a", 18x"29210", 18x"28fda", 18x"28da6", 18x"28b74", 18x"28946",
        18x"28718", 18x"284ec", 18x"282c4", 18x"2809c", 18x"27e78", 18x"27c56", 18x"27a34", 18x"27816",
        18x"275fa", 18x"273e0", 18x"271c8", 18x"26fb0", 18x"26d9c", 18x"26b8a", 18x"2697a", 18x"2676c",
        18x"26560", 18x"26356", 18x"2614c", 18x"25f46", 18x"25d42", 18x"25b40", 18x"2593e", 18x"25740",
        18x"25542", 18x"25348", 18x"2514e", 18x"24f58", 18x"24d62", 18x"24b6e", 18x"2497c", 18x"2478c",
        18x"2459e", 18x"243b0", 18x"241c6", 18x"23fde", 18x"23df6", 18x"23c10", 18x"23a2c", 18x"2384a",
        18x"2366a", 18x"2348c", 18x"232ae", 18x"230d2", 18x"22efa", 18x"22d20", 18x"22b4a", 18x"22976",
        18x"227a2", 18x"225d2", 18x"22402", 18x"22234", 18x"22066", 18x"21e9c", 18x"21cd2", 18x"21b0a",
        18x"21944", 18x"2177e", 18x"215ba", 18x"213fa", 18x"21238", 18x"2107a", 18x"20ebc", 18x"20d00",
        18x"20b46", 18x"2098e", 18x"207d6", 18x"20620", 18x"2046c", 18x"202b8", 18x"20108", 18x"1ff58",
        18x"1fda8", 18x"1fbfc", 18x"1fa50", 18x"1f8a4", 18x"1f6fc", 18x"1f554", 18x"1f3ae", 18x"1f208",
        18x"1f064", 18x"1eec2", 18x"1ed22", 18x"1eb82", 18x"1e9e4", 18x"1e846", 18x"1e6aa", 18x"1e510",
        18x"1e378", 18x"1e1e0", 18x"1e04a", 18x"1deb4", 18x"1dd20", 18x"1db8e", 18x"1d9fc", 18x"1d86c",
        18x"1d6de", 18x"1d550", 18x"1d3c4", 18x"1d238", 18x"1d0ae", 18x"1cf26", 18x"1cd9e", 18x"1cc18",
        18x"1ca94", 18x"1c910", 18x"1c78c", 18x"1c60a", 18x"1c48a", 18x"1c30c", 18x"1c18e", 18x"1c010",
        18x"1be94", 18x"1bd1a", 18x"1bba0", 18x"1ba28", 18x"1b8b2", 18x"1b73c", 18x"1b5c6", 18x"1b452",
        18x"1b2e0", 18x"1b16e", 18x"1affe", 18x"1ae8e", 18x"1ad20", 18x"1abb4", 18x"1aa46", 18x"1a8dc",
        -- 2.0 ... 2.9999
        18x"1a772", 18x"1a608", 18x"1a4a0", 18x"1a33a", 18x"1a1d4", 18x"1a070", 18x"19f0c", 18x"19da8",
        18x"19c48", 18x"19ae6", 18x"19986", 18x"19828", 18x"196ca", 18x"1956e", 18x"19412", 18x"192b8",
        18x"1915e", 18x"19004", 18x"18eae", 18x"18d56", 18x"18c00", 18x"18aac", 18x"18958", 18x"18804",
        18x"186b2", 18x"18562", 18x"18412", 18x"182c2", 18x"18174", 18x"18026", 18x"17eda", 18x"17d8e",
        18x"17c44", 18x"17afa", 18x"179b2", 18x"1786a", 18x"17724", 18x"175de", 18x"17498", 18x"17354",
        18x"17210", 18x"170ce", 18x"16f8c", 18x"16e4c", 18x"16d0c", 18x"16bcc", 18x"16a8e", 18x"16950",
        18x"16814", 18x"166d8", 18x"1659e", 18x"16464", 18x"1632a", 18x"161f2", 18x"160ba", 18x"15f84",
        18x"15e4e", 18x"15d1a", 18x"15be6", 18x"15ab2", 18x"15980", 18x"1584e", 18x"1571c", 18x"155ec",
        18x"154bc", 18x"1538e", 18x"15260", 18x"15134", 18x"15006", 18x"14edc", 18x"14db0", 18x"14c86",
        18x"14b5e", 18x"14a36", 18x"1490e", 18x"147e6", 18x"146c0", 18x"1459a", 18x"14476", 18x"14352",
        18x"14230", 18x"1410c", 18x"13fea", 18x"13eca", 18x"13daa", 18x"13c8a", 18x"13b6c", 18x"13a4e",
        18x"13930", 18x"13814", 18x"136f8", 18x"135dc", 18x"134c2", 18x"133a8", 18x"1328e", 18x"13176",
        18x"1305e", 18x"12f48", 18x"12e30", 18x"12d1a", 18x"12c06", 18x"12af2", 18x"129de", 18x"128ca",
        18x"127b8", 18x"126a6", 18x"12596", 18x"12486", 18x"12376", 18x"12266", 18x"12158", 18x"1204a",
        18x"11f3e", 18x"11e32", 18x"11d26", 18x"11c1a", 18x"11b10", 18x"11a06", 18x"118fc", 18x"117f4",
        18x"116ec", 18x"115e4", 18x"114de", 18x"113d8", 18x"112d2", 18x"111ce", 18x"110ca", 18x"10fc6",
        18x"10ec2", 18x"10dc0", 18x"10cbe", 18x"10bbc", 18x"10abc", 18x"109bc", 18x"108bc", 18x"107be",
        18x"106c0", 18x"105c2", 18x"104c4", 18x"103c8", 18x"102cc", 18x"101d0", 18x"100d6", 18x"0ffdc",
        18x"0fee2", 18x"0fdea", 18x"0fcf0", 18x"0fbf8", 18x"0fb02", 18x"0fa0a", 18x"0f914", 18x"0f81e",
        18x"0f72a", 18x"0f636", 18x"0f542", 18x"0f44e", 18x"0f35a", 18x"0f268", 18x"0f176", 18x"0f086",
        18x"0ef94", 18x"0eea4", 18x"0edb4", 18x"0ecc6", 18x"0ebd6", 18x"0eae8", 18x"0e9fa", 18x"0e90e",
        18x"0e822", 18x"0e736", 18x"0e64a", 18x"0e55e", 18x"0e474", 18x"0e38a", 18x"0e2a0", 18x"0e1b8",
        18x"0e0d0", 18x"0dfe8", 18x"0df00", 18x"0de1a", 18x"0dd32", 18x"0dc4c", 18x"0db68", 18x"0da82",
        18x"0d99e", 18x"0d8ba", 18x"0d7d6", 18x"0d6f4", 18x"0d612", 18x"0d530", 18x"0d44e", 18x"0d36c",
        18x"0d28c", 18x"0d1ac", 18x"0d0cc", 18x"0cfee", 18x"0cf0e", 18x"0ce30", 18x"0cd54", 18x"0cc76",
        18x"0cb9a", 18x"0cabc", 18x"0c9e0", 18x"0c906", 18x"0c82a", 18x"0c750", 18x"0c676", 18x"0c59c",
        18x"0c4c4", 18x"0c3ea", 18x"0c312", 18x"0c23a", 18x"0c164", 18x"0c08c", 18x"0bfb6", 18x"0bee0",
        18x"0be0a", 18x"0bd36", 18x"0bc62", 18x"0bb8c", 18x"0baba", 18x"0b9e6", 18x"0b912", 18x"0b840",
        18x"0b76e", 18x"0b69c", 18x"0b5cc", 18x"0b4fa", 18x"0b42a", 18x"0b35a", 18x"0b28a", 18x"0b1bc",
        18x"0b0ee", 18x"0b01e", 18x"0af50", 18x"0ae84", 18x"0adb6", 18x"0acea", 18x"0ac1e", 18x"0ab52",
        18x"0aa86", 18x"0a9bc", 18x"0a8f0", 18x"0a826", 18x"0a75c", 18x"0a694", 18x"0a5ca", 18x"0a502",
        18x"0a43a", 18x"0a372", 18x"0a2aa", 18x"0a1e4", 18x"0a11c", 18x"0a056", 18x"09f90", 18x"09ecc",
        -- 3.0 ... 3.9999
        18x"09e06", 18x"09d42", 18x"09c7e", 18x"09bba", 18x"09af6", 18x"09a32", 18x"09970", 18x"098ae",
        18x"097ec", 18x"0972a", 18x"09668", 18x"095a8", 18x"094e8", 18x"09426", 18x"09368", 18x"092a8",
        18x"091e8", 18x"0912a", 18x"0906c", 18x"08fae", 18x"08ef0", 18x"08e32", 18x"08d76", 18x"08cba",
        18x"08bfe", 18x"08b42", 18x"08a86", 18x"089ca", 18x"08910", 18x"08856", 18x"0879c", 18x"086e2",
        18x"08628", 18x"08570", 18x"084b6", 18x"083fe", 18x"08346", 18x"0828e", 18x"081d8", 18x"08120",
        18x"0806a", 18x"07fb4", 18x"07efe", 18x"07e48", 18x"07d92", 18x"07cde", 18x"07c2a", 18x"07b76",
        18x"07ac2", 18x"07a0e", 18x"0795a", 18x"078a8", 18x"077f4", 18x"07742", 18x"07690", 18x"075de",
        18x"0752e", 18x"0747c", 18x"073cc", 18x"0731c", 18x"0726c", 18x"071bc", 18x"0710c", 18x"0705e",
        18x"06fae", 18x"06f00", 18x"06e52", 18x"06da4", 18x"06cf6", 18x"06c4a", 18x"06b9c", 18x"06af0",
        18x"06a44", 18x"06998", 18x"068ec", 18x"06840", 18x"06796", 18x"066ea", 18x"06640", 18x"06596",
        18x"064ec", 18x"06442", 18x"0639a", 18x"062f0", 18x"06248", 18x"061a0", 18x"060f8", 18x"06050",
        18x"05fa8", 18x"05f00", 18x"05e5a", 18x"05db4", 18x"05d0e", 18x"05c68", 18x"05bc2", 18x"05b1c",
        18x"05a76", 18x"059d2", 18x"0592e", 18x"05888", 18x"057e4", 18x"05742", 18x"0569e", 18x"055fa",
        18x"05558", 18x"054b6", 18x"05412", 18x"05370", 18x"052ce", 18x"0522e", 18x"0518c", 18x"050ec",
        18x"0504a", 18x"04faa", 18x"04f0a", 18x"04e6a", 18x"04dca", 18x"04d2c", 18x"04c8c", 18x"04bee",
        18x"04b50", 18x"04ab0", 18x"04a12", 18x"04976", 18x"048d8", 18x"0483a", 18x"0479e", 18x"04700",
        18x"04664", 18x"045c8", 18x"0452c", 18x"04490", 18x"043f6", 18x"0435a", 18x"042c0", 18x"04226",
        18x"0418a", 18x"040f0", 18x"04056", 18x"03fbe", 18x"03f24", 18x"03e8c", 18x"03df2", 18x"03d5a",
        18x"03cc2", 18x"03c2a", 18x"03b92", 18x"03afa", 18x"03a62", 18x"039cc", 18x"03934", 18x"0389e",
        18x"03808", 18x"03772", 18x"036dc", 18x"03646", 18x"035b2", 18x"0351c", 18x"03488", 18x"033f2",
        18x"0335e", 18x"032ca", 18x"03236", 18x"031a2", 18x"03110", 18x"0307c", 18x"02fea", 18x"02f56",
        18x"02ec4", 18x"02e32", 18x"02da0", 18x"02d0e", 18x"02c7c", 18x"02bec", 18x"02b5a", 18x"02aca",
        18x"02a38", 18x"029a8", 18x"02918", 18x"02888", 18x"027f8", 18x"0276a", 18x"026da", 18x"0264a",
        18x"025bc", 18x"0252e", 18x"024a0", 18x"02410", 18x"02384", 18x"022f6", 18x"02268", 18x"021da",
        18x"0214e", 18x"020c0", 18x"02034", 18x"01fa8", 18x"01f1c", 18x"01e90", 18x"01e04", 18x"01d78",
        18x"01cee", 18x"01c62", 18x"01bd8", 18x"01b4c", 18x"01ac2", 18x"01a38", 18x"019ae", 18x"01924",
        18x"0189c", 18x"01812", 18x"01788", 18x"01700", 18x"01676", 18x"015ee", 18x"01566", 18x"014de",
        18x"01456", 18x"013ce", 18x"01346", 18x"012c0", 18x"01238", 18x"011b2", 18x"0112c", 18x"010a4",
        18x"0101e", 18x"00f98", 18x"00f12", 18x"00e8c", 18x"00e08", 18x"00d82", 18x"00cfe", 18x"00c78",
        18x"00bf4", 18x"00b70", 18x"00aec", 18x"00a68", 18x"009e4", 18x"00960", 18x"008dc", 18x"00858",
        18x"007d6", 18x"00752", 18x"006d0", 18x"0064e", 18x"005cc", 18x"0054a", 18x"004c8", 18x"00446",
        18x"003c4", 18x"00342", 18x"002c2", 18x"00240", 18x"001c0", 18x"00140", 18x"000c0", 18x"00040"
        );

    -- Left and right shifter with 120 bit input and 64 bit output.
    -- Shifts inp left by shift bits and returns the upper 64 bits of
    -- the result.  The shift parameter is interpreted as a signed
    -- number in the range -64..63, with negative values indicating
    -- right shifts.
    function shifter_64(inp: std_ulogic_vector(119 downto 0);
                        shift: std_ulogic_vector(6 downto 0))
        return std_ulogic_vector is
        variable s1 : std_ulogic_vector(94 downto 0);
        variable s2 : std_ulogic_vector(70 downto 0);
        variable result : std_ulogic_vector(63 downto 0);
    begin
        case shift(6 downto 5) is
            when "00" =>
                s1 := inp(119 downto 25);
            when "01" =>
                s1 := inp(87 downto 0) & "0000000";
            when "10" =>
                s1 := x"0000000000000000" & inp(119 downto 89);
            when others =>
                s1 := x"00000000" & inp(119 downto 57);
        end case;
        case shift(4 downto 3) is
            when "00" =>
                s2 := s1(94 downto 24);
            when "01" =>
                s2 := s1(86 downto 16);
            when "10" =>
                s2 := s1(78 downto 8);
            when others =>
                s2 := s1(70 downto 0);
        end case;
        case shift(2 downto 0) is
            when "000" =>
                result := s2(70 downto 7);
            when "001" =>
                result := s2(69 downto 6);
            when "010" =>
                result := s2(68 downto 5);
            when "011" =>
                result := s2(67 downto 4);
            when "100" =>
                result := s2(66 downto 3);
            when "101" =>
                result := s2(65 downto 2);
            when "110" =>
                result := s2(64 downto 1);
            when others =>
                result := s2(63 downto 0);
        end case;
        return result;
    end;

    -- Generate a mask with 0-bits on the left and 1-bits on the right which
    -- selects the bits will be lost in doing a right shift.  The shift
    -- parameter is the bottom 6 bits of a negative shift count,
    -- indicating a right shift.
    function right_mask(shift: unsigned(5 downto 0)) return std_ulogic_vector is
        variable result: std_ulogic_vector(63 downto 0);
    begin
        result := (others => '0');
        for i in 0 to 63 loop
            if i >= shift then
                result(63 - i) := '1';
            end if;
        end loop;
        return result;
    end;

    -- Split a DP floating-point number into components and work out its class.
    -- If is_int = 1, the input is considered an integer
    function decode_dp(fpr: std_ulogic_vector(63 downto 0); is_int: std_ulogic) return fpu_reg_type is
        variable r       : fpu_reg_type;
        variable exp_nz  : std_ulogic;
        variable exp_ao  : std_ulogic;
        variable frac_nz : std_ulogic;
        variable cls     : std_ulogic_vector(2 downto 0);
    begin
        r.negative := fpr(63);
        exp_nz := or (fpr(62 downto 52));
        exp_ao := and (fpr(62 downto 52));
        frac_nz := or (fpr(51 downto 0));
        if is_int = '0' then
            r.exponent := signed(resize(unsigned(fpr(62 downto 52)), EXP_BITS)) - to_signed(1023, EXP_BITS);
            if exp_nz = '0' then
                r.exponent := to_signed(-1022, EXP_BITS);
            end if;
            r.mantissa := "000000000" & exp_nz & fpr(51 downto 0) & "00";
            cls := exp_ao & exp_nz & frac_nz;
            case cls is
                when "000"  => r.class := ZERO;
                when "001"  => r.class := FINITE;    -- denormalized
                when "010"  => r.class := FINITE;
                when "011"  => r.class := FINITE;
                when "110"  => r.class := INFINITY;
                when others => r.class := NAN;
            end case;
        else
            r.mantissa := fpr;
            r.exponent := (others => '0');
            if (fpr(63) or exp_nz or frac_nz) = '1' then
                r.class := FINITE;
            else
                r.class := ZERO;
            end if;
        end if;
        return r;
    end;

    -- Construct a DP floating-point result from components
    function pack_dp(sign: std_ulogic; class: fp_number_class; exp: signed(EXP_BITS-1 downto 0);
                     mantissa: std_ulogic_vector; single_prec: std_ulogic; quieten_nan: std_ulogic)
        return std_ulogic_vector is
        variable result : std_ulogic_vector(63 downto 0);
    begin
        result := (others => '0');
        result(63) := sign;
        case class is
            when ZERO =>
            when FINITE =>
                if mantissa(54) = '1' then
                    -- normalized number
                    result(62 downto 52) := std_ulogic_vector(resize(exp, 11) + 1023);
                end if;
                result(51 downto 29) := mantissa(53 downto 31);
                if single_prec = '0' then
                    result(28 downto 0) := mantissa(30 downto 2);
                end if;
            when INFINITY =>
                result(62 downto 52) := "11111111111";
            when NAN =>
                result(62 downto 52) := "11111111111";
                result(51) := quieten_nan or mantissa(53);
                result(50 downto 29) := mantissa(52 downto 31);
                if single_prec = '0' then
                    result(28 downto 0) := mantissa(30 downto 2);
                end if;
        end case;
        return result;
    end;

    -- Determine whether to increment when rounding
    -- Returns rounding_inc & inexact
    -- Assumes x includes the bottom 29 bits of the mantissa already
    -- if single_prec = 1 (usually arranged by setting set_x = 1 earlier).
    function fp_rounding(mantissa: std_ulogic_vector(63 downto 0); x: std_ulogic;
                         single_prec: std_ulogic; rn: std_ulogic_vector(2 downto 0);
                         sign: std_ulogic)
        return std_ulogic_vector is
        variable grx : std_ulogic_vector(2 downto 0);
        variable ret : std_ulogic_vector(1 downto 0);
        variable lsb : std_ulogic;
    begin
        if single_prec = '0' then
            grx := mantissa(1 downto 0) & x;
            lsb := mantissa(2);
        else
            grx := mantissa(30 downto 29) & x;
            lsb := mantissa(31);
        end if;
        ret(1) := '0';
        ret(0) := or (grx);
        case rn(1 downto 0) is
            when "00" =>        -- round to nearest
                if grx = "100" and rn(2) = '0' then
                    ret(1) := lsb; -- tie, round to even
                else
                    ret(1) := grx(2);
                end if;
            when "01" =>        -- round towards zero
            when others =>      -- round towards +/- inf
                if rn(0) = sign then
                    -- round towards greater magnitude
                    ret(1) := ret(0);
                end if;
        end case;
        return ret;
    end;

    -- Determine result flags to write into the FPSCR
    function result_flags(sign: std_ulogic; class: fp_number_class; unitbit: std_ulogic)
        return std_ulogic_vector is
    begin
        case class is
            when ZERO =>
                return sign & "0010";
            when FINITE =>
                return (not unitbit) & sign & (not sign) & "00";
            when INFINITY =>
                return '0' & sign & (not sign) & "01";
            when NAN =>
                return "10001";
        end case;
    end;

begin
    fpu_multiply_0: entity work.multiply
        port map (
            clk => clk,
            m_in => f_to_multiply,
            m_out => multiply_to_f
            );

    fpu_0: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                r.state <= IDLE;
                r.busy <= '0';
                r.instr_done <= '0';
                r.do_intr <= '0';
                r.fpscr <= (others => '0');
                r.writing_back <= '0';
            else
                assert not (r.state /= IDLE and e_in.valid = '1') severity failure;
                r <= rin;
            end if;
        end if;
    end process;

    -- synchronous reads from lookup table
    lut_access: process(clk)
        variable addrhi : std_ulogic_vector(1 downto 0);
        variable addr   : std_ulogic_vector(9 downto 0);
    begin
        if rising_edge(clk) then
            if r.is_sqrt = '1' then
                addrhi := r.b.mantissa(55 downto 54);
            else
                addrhi := "00";
            end if;
            addr := addrhi & r.b.mantissa(53 downto 46);
            inverse_est <= '1' & inverse_table(to_integer(unsigned(addr)));
        end if;
    end process;

    e_out.busy <= r.busy;
    e_out.exception <= r.fpscr(FPSCR_FEX);

    w_out.valid <= r.instr_done and not r.do_intr;
    w_out.instr_tag <= r.instr_tag;
    w_out.write_enable <= r.writing_back;
    w_out.write_reg <= r.dest_fpr;
    w_out.write_data <= fp_result;
    w_out.write_cr_enable <= r.instr_done and (r.rc or r.is_cmp);
    w_out.write_cr_mask <= r.cr_mask;
    w_out.write_cr_data <= r.cr_result & r.cr_result & r.cr_result & r.cr_result &
                           r.cr_result & r.cr_result & r.cr_result & r.cr_result;
    w_out.interrupt <= r.do_intr;
    w_out.intr_vec <= 16#700#;
    w_out.srr0 <= r.nia;
    w_out.srr1 <= (47-44 => r.illegal, 47-43 => not r.illegal, others => '0');

    fpu_1: process(all)
        variable v           : reg_type;
        variable adec        : fpu_reg_type;
        variable bdec        : fpu_reg_type;
        variable cdec        : fpu_reg_type;
        variable fpscr_mask  : std_ulogic_vector(31 downto 0);
        variable illegal     : std_ulogic;
        variable j, k        : integer;
        variable flm         : std_ulogic_vector(7 downto 0);
        variable int_input   : std_ulogic;
        variable mask        : std_ulogic_vector(63 downto 0);
        variable in_a0       : std_ulogic_vector(63 downto 0);
        variable in_b0       : std_ulogic_vector(63 downto 0);
        variable misc        : std_ulogic_vector(63 downto 0);
        variable shift_res   : std_ulogic_vector(63 downto 0);
        variable round       : std_ulogic_vector(1 downto 0);
        variable update_fx   : std_ulogic;
        variable arith_done  : std_ulogic;
        variable invalid     : std_ulogic;
        variable zero_divide : std_ulogic;
        variable mant_nz     : std_ulogic;
        variable min_exp     : signed(EXP_BITS-1 downto 0);
        variable max_exp     : signed(EXP_BITS-1 downto 0);
        variable bias_exp    : signed(EXP_BITS-1 downto 0);
        variable new_exp     : signed(EXP_BITS-1 downto 0);
        variable exp_tiny    : std_ulogic;
        variable exp_huge    : std_ulogic;
        variable renormalize : std_ulogic;
        variable clz         : std_ulogic_vector(5 downto 0);
        variable set_x       : std_ulogic;
        variable mshift      : signed(EXP_BITS-1 downto 0);
        variable need_check  : std_ulogic;
        variable msb         : std_ulogic;
        variable is_add      : std_ulogic;
        variable set_a       : std_ulogic;
        variable set_b       : std_ulogic;
        variable set_c       : std_ulogic;
        variable set_y       : std_ulogic;
        variable set_s       : std_ulogic;
        variable qnan_result : std_ulogic;
        variable px_nz       : std_ulogic;
        variable pcmpb_eq    : std_ulogic;
        variable pcmpb_lt    : std_ulogic;
        variable pshift      : std_ulogic;
        variable renorm_sqrt : std_ulogic;
        variable sqrt_exp    : signed(EXP_BITS-1 downto 0);
        variable shiftin     : std_ulogic;
        variable mulexp      : signed(EXP_BITS-1 downto 0);
        variable maddend     : std_ulogic_vector(127 downto 0);
        variable sum         : std_ulogic_vector(63 downto 0);
        variable round_inc   : std_ulogic_vector(63 downto 0);
    begin
        v := r;
        illegal := '0';
        v.busy := '0';
        int_input := '0';

        -- capture incoming instruction
        if e_in.valid = '1' then
            v.insn := e_in.insn;
            v.nia := e_in.nia;
            v.op := e_in.op;
            v.instr_tag := e_in.itag;
            v.fe_mode := or (e_in.fe_mode);
            v.dest_fpr := e_in.frt;
            v.single_prec := e_in.single;
            v.longmask := e_in.single;
            v.int_result := '0';
            v.rc := e_in.rc;
            v.is_cmp := e_in.out_cr;
            if e_in.out_cr = '0' then
                v.cr_mask := num_to_fxm(1);
            else
                v.cr_mask := num_to_fxm(to_integer(unsigned(insn_bf(e_in.insn))));
            end if;
            int_input := '0';
            if e_in.op = OP_FPOP_I then
                int_input := '1';
            end if;
            v.quieten_nan := '1';
            v.tiny := '0';
            v.denorm := '0';
            v.round_mode := '0' & r.fpscr(FPSCR_RN+1 downto FPSCR_RN);
            v.is_subtract := '0';
            v.is_multiply := '0';
            v.is_sqrt := '0';
            v.add_bsmall := '0';
            v.doing_ftdiv := "00";

            adec := decode_dp(e_in.fra, int_input);
            bdec := decode_dp(e_in.frb, int_input);
            cdec := decode_dp(e_in.frc, int_input);
            v.a := adec;
            v.b := bdec;
            v.c := cdec;

            v.exp_cmp := '0';
            if adec.exponent > bdec.exponent then
                v.exp_cmp := '1';
            end if;
            v.madd_cmp := '0';
            if (adec.exponent + cdec.exponent + 1) >= bdec.exponent then
                v.madd_cmp := '1';
            end if;
        end if;

        r_hi_nz <= or (r.r(55 downto 31));
        r_lo_nz <= or (r.r(30 downto 2));
        s_nz <= or (r.s);

        if r.single_prec = '0' then
            if r.doing_ftdiv(1) = '0' then
                max_exp := to_signed(1023, EXP_BITS);
            else
                max_exp := to_signed(1020, EXP_BITS);
            end if;
            if r.doing_ftdiv(0) = '0' then
                min_exp := to_signed(-1022, EXP_BITS);
            else
                min_exp := to_signed(-1021, EXP_BITS);
            end if;
            bias_exp := to_signed(1536, EXP_BITS);
        else
            max_exp := to_signed(127, EXP_BITS);
            min_exp := to_signed(-126, EXP_BITS);
            bias_exp := to_signed(192, EXP_BITS);
        end if;
        new_exp := r.result_exp - r.shift;
        exp_tiny := '0';
        exp_huge := '0';
        if new_exp < min_exp then
            exp_tiny := '1';
        end if;
        if new_exp > max_exp then
            exp_huge := '1';
        end if;

        -- Compare P with zero and with B
        px_nz := or (r.p(57 downto 4));
        pcmpb_eq := '0';
        if r.p(59 downto 4) = r.b.mantissa(55 downto 0) then
            pcmpb_eq := '1';
        end if;
        pcmpb_lt := '0';
        if unsigned(r.p(59 downto 4)) < unsigned(r.b.mantissa(55 downto 0)) then
            pcmpb_lt := '1';
        end if;

        v.writing_back := '0';
        v.instr_done := '0';
        v.update_fprf := '0';
        v.shift := to_signed(0, EXP_BITS);
        v.first := '0';
        v.opsel_a := AIN_R;
        opsel_ainv <= '0';
        opsel_mask <= '0';
        opsel_b <= BIN_ZERO;
        opsel_binv <= '0';
        opsel_r <= RES_SUM;
        opsel_s <= S_ZERO;
        carry_in <= '0';
        misc_sel <= "0000";
        fpscr_mask := (others => '1');
        update_fx := '0';
        arith_done := '0';
        invalid := '0';
        zero_divide := '0';
        renormalize := '0';
        set_x := '0';
        qnan_result := '0';
        set_a := '0';
        set_b := '0';
        set_c := '0';
        set_s := '0';
        f_to_multiply.is_32bit <= '0';
        f_to_multiply.valid <= '0';
        msel_1 <= MUL1_A;
        msel_2 <= MUL2_C;
        msel_add <= MULADD_ZERO;
        msel_inv <= '0';
        set_y := '0';
        pshift := '0';
        renorm_sqrt := '0';
        shiftin := '0';
        case r.state is
            when IDLE =>
                v.use_a := '0';
                v.use_b := '0';
                v.use_c := '0';
                v.invalid := '0';
                v.negate := '0';
                if e_in.valid = '1' then
                    case e_in.insn(5 downto 1) is
                        when "00000" =>
                            if e_in.insn(8) = '1' then
                                if e_in.insn(6) = '0' then
                                    v.state := DO_FTDIV;
                                else
                                    v.state := DO_FTSQRT;
                                end if;
                            elsif e_in.insn(7) = '1' then
                                v.state := DO_MCRFS;
                            else
                                v.opsel_a := AIN_B;
                                v.state := DO_FCMP;
                            end if;
                        when "00110" =>
                            if e_in.insn(10) = '0' then
                                if e_in.insn(8) = '0' then
                                    v.state := DO_MTFSB;
                                else
                                    v.state := DO_MTFSFI;
                                end if;
                            else
                                v.state := DO_FMRG;
                            end if;
                        when "00111" =>
                            if e_in.insn(8) = '0' then
                                v.state := DO_MFFS;
                            else
                                v.state := DO_MTFSF;
                            end if;
                        when "01000" =>
                            v.opsel_a := AIN_B;
                            if e_in.insn(9 downto 8) /= "11" then
                                v.state := DO_FMR;
                            else
                                v.state := DO_FRI;
                            end if;
                        when "01100" =>
                            v.opsel_a := AIN_B;
                            v.state := DO_FRSP;
                        when "01110" =>
                            v.opsel_a := AIN_B;
                            if int_input = '1' then
                                -- fcfid[u][s]
                                v.state := DO_FCFID;
                            else
                                v.state := DO_FCTI;
                            end if;
                        when "01111" =>
                            v.round_mode := "001";
                            v.opsel_a := AIN_B;
                            v.state := DO_FCTI;
                        when "10010" =>
                            v.opsel_a := AIN_A;
                            if v.b.mantissa(54) = '0' and v.a.mantissa(54) = '1' then
                                v.opsel_a := AIN_B;
                            end if;
                            v.state := DO_FDIV;
                        when "10100" | "10101" =>
                            v.opsel_a := AIN_A;
                            v.state := DO_FADD;
                        when "10110" =>
                            v.is_sqrt := '1';
                            v.opsel_a := AIN_B;
                            v.state := DO_FSQRT;
                        when "10111" =>
                            v.state := DO_FSEL;
                        when "11000" =>
                            v.opsel_a := AIN_B;
                            v.state := DO_FRE;
                        when "11001" =>
                            v.is_multiply := '1';
                            v.opsel_a := AIN_A;
                            if v.c.mantissa(54) = '0' and v.a.mantissa(54) = '1' then
                                v.opsel_a := AIN_C;
                            end if;
                            v.state := DO_FMUL;
                        when "11010" =>
                            v.is_sqrt := '1';
                            v.opsel_a := AIN_B;
                            v.state := DO_FRSQRTE;
                        when "11100" | "11101" | "11110" | "11111" =>
                            if v.a.mantissa(54) = '0' then
                                v.opsel_a := AIN_A;
                            elsif v.c.mantissa(54) = '0' then
                                v.opsel_a := AIN_C;
                            else
                                v.opsel_a := AIN_B;
                            end if;
                            v.state := DO_FMADD;
                        when others =>
                            illegal := '1';
                    end case;
                end if;
                v.x := '0';
                v.old_exc := r.fpscr(FPSCR_VX downto FPSCR_XX);
                set_s := '1';

            when DO_MCRFS =>
                j := to_integer(unsigned(insn_bfa(r.insn)));
                for i in 0 to 7 loop
                    if i = j then
                        k := (7 - i) * 4;
                        v.cr_result := r.fpscr(k + 3 downto k);
                        fpscr_mask(k + 3 downto k) := "0000";
                    end if;
                end loop;
                v.fpscr := r.fpscr and (fpscr_mask or x"6007F8FF");
                v.instr_done := '1';
                v.state := IDLE;

            when DO_FTDIV =>
                v.instr_done := '1';
                v.state := IDLE;
                v.cr_result := "0000";
                if r.a.class = INFINITY or r.b.class = ZERO or r.b.class = INFINITY or
                    (r.b.class = FINITE and r.b.mantissa(53) = '0') then
                    v.cr_result(2) := '1';
                end if;
                if r.a.class = NAN or r.a.class = INFINITY or
                    r.b.class = NAN or r.b.class = ZERO or r.b.class = INFINITY or
                    (r.a.class = FINITE and r.a.exponent <= to_signed(-970, EXP_BITS)) then
                    v.cr_result(1) := '1';
                else
                    v.doing_ftdiv := "11";
                    v.first := '1';
                    v.state := FTDIV_1;
                    v.instr_done := '0';
                end if;

            when DO_FTSQRT =>
                v.instr_done := '1';
                v.state := IDLE;
                v.cr_result := "0000";
                if r.b.class = ZERO or r.b.class = INFINITY or
                    (r.b.class = FINITE and r.b.mantissa(53) = '0') then
                    v.cr_result(2) := '1';
                end if;
                if r.b.class = NAN or r.b.class = INFINITY or r.b.class = ZERO
                    or r.b.negative = '1' or r.b.exponent <= to_signed(-970, EXP_BITS) then
                    v.cr_result(1) := '0';
                end if;

            when DO_FCMP =>
                -- fcmp[uo]
                -- r.opsel_a = AIN_B
                v.instr_done := '1';
                v.state := IDLE;
                update_fx := '1';
                v.result_exp := r.b.exponent;
                if (r.a.class = NAN and r.a.mantissa(53) = '0') or
                    (r.b.class = NAN and r.b.mantissa(53) = '0') then
                    -- Signalling NAN
                    v.fpscr(FPSCR_VXSNAN) := '1';
                    if r.insn(6) = '1' and r.fpscr(FPSCR_VE) = '0' then
                        v.fpscr(FPSCR_VXVC) := '1';
                    end if;
                    invalid := '1';
                    v.cr_result := "0001";          -- unordered
                elsif r.a.class = NAN or r.b.class = NAN then
                    if r.insn(6) = '1' then
                        -- fcmpo
                        v.fpscr(FPSCR_VXVC) := '1';
                        invalid := '1';
                    end if;
                    v.cr_result := "0001";          -- unordered
                elsif r.a.class = ZERO and r.b.class = ZERO then
                    v.cr_result := "0010";          -- equal
                elsif r.a.negative /= r.b.negative then
                    v.cr_result := r.a.negative & r.b.negative & "00";
                elsif r.a.class = ZERO then
                    -- A and B are the same sign from here down
                    v.cr_result := not r.b.negative & r.b.negative & "00";
                elsif r.a.class = INFINITY then
                    if r.b.class = INFINITY then
                        v.cr_result := "0010";
                    else
                        v.cr_result := r.a.negative & not r.a.negative & "00";
                    end if;
                elsif r.b.class = ZERO then
                    -- A is finite from here down
                    v.cr_result := r.a.negative & not r.a.negative & "00";
                elsif r.b.class = INFINITY then
                    v.cr_result := not r.b.negative & r.b.negative & "00";
                elsif r.exp_cmp = '1' then
                    -- A and B are both finite from here down
                    v.cr_result := r.a.negative & not r.a.negative & "00";
                elsif r.a.exponent /= r.b.exponent then
                    -- A exponent is smaller than B
                    v.cr_result := not r.a.negative & r.a.negative & "00";
                else
                    -- Prepare to subtract mantissas, put B in R
                    v.cr_result := "0000";
                    v.instr_done := '0';
                    v.opsel_a := AIN_A;
                    v.state := CMP_1;
                end if;
                v.fpscr(FPSCR_FL downto FPSCR_FU) := v.cr_result;

            when DO_MTFSB =>
                -- mtfsb{0,1}
                j := to_integer(unsigned(insn_bt(r.insn)));
                for i in 0 to 31 loop
                    if i = j then
                        v.fpscr(31 - i) := r.insn(6);
                    end if;
                end loop;
                v.instr_done := '1';
                v.state := IDLE;

            when DO_MTFSFI =>
                -- mtfsfi
                j := to_integer(unsigned(insn_bf(r.insn)));
                if r.insn(16) = '0' then
                    for i in 0 to 7 loop
                        if i = j then
                            k := (7 - i) * 4;
                            v.fpscr(k + 3 downto k) := insn_u(r.insn);
                        end if;
                    end loop;
                end if;
                v.instr_done := '1';
                v.state := IDLE;

            when DO_FMRG =>
                -- fmrgew, fmrgow
                opsel_r <= RES_MISC;
                misc_sel <= "01" & r.insn(8) & '0';
                v.int_result := '1';
                v.writing_back := '1';
                v.instr_done := '1';
                v.state := IDLE;

            when DO_MFFS =>
                v.int_result := '1';
                v.writing_back := '1';
                opsel_r <= RES_MISC;
                case r.insn(20 downto 16) is
                    when "00000" =>
                        -- mffs
                    when "00001" =>
                        -- mffsce
                        v.fpscr(FPSCR_VE downto FPSCR_XE) := "00000";
                    when "10100" | "10101" =>
                        -- mffscdrn[i] (but we don't implement DRN)
                        fpscr_mask := x"000000FF";
                    when "10110" =>
                        -- mffscrn
                        fpscr_mask := x"000000FF";
                        v.fpscr(FPSCR_RN+1 downto FPSCR_RN) :=
                            r.b.mantissa(FPSCR_RN+1 downto FPSCR_RN);
                    when "10111" =>
                        -- mffscrni
                        fpscr_mask := x"000000FF";
                        v.fpscr(FPSCR_RN+1 downto FPSCR_RN) := r.insn(12 downto 11);
                    when "11000" =>
                        -- mffsl
                        fpscr_mask := x"0007F0FF";
                    when others =>
                        illegal := '1';
                end case;
                v.instr_done := '1';
                v.state := IDLE;

            when DO_MTFSF =>
                if r.insn(25) = '1' then
                    flm := x"FF";
                elsif r.insn(16) = '1' then
                    flm := x"00";
                else
                    flm := r.insn(24 downto 17);
                end if;
                for i in 0 to 7 loop
                    k := i * 4;
                    if flm(i) = '1' then
                        v.fpscr(k + 3 downto k) := r.b.mantissa(k + 3 downto k);
                    end if;
                end loop;
                v.instr_done := '1';
                v.state := IDLE;

            when DO_FMR =>
                -- r.opsel_a = AIN_B
                v.result_class := r.b.class;
                v.result_exp := r.b.exponent;
                v.quieten_nan := '0';
                if r.insn(9) = '1' then
                    v.result_sign := '0';              -- fabs
                elsif r.insn(8) = '1' then
                    v.result_sign := '1';              -- fnabs
                elsif r.insn(7) = '1' then
                    v.result_sign := r.b.negative;     -- fmr
                elsif r.insn(6) = '1' then
                    v.result_sign := not r.b.negative; -- fneg
                else
                    v.result_sign := r.a.negative;     -- fcpsgn
                end if;
                v.writing_back := '1';
                v.instr_done := '1';
                v.state := IDLE;

            when DO_FRI =>    -- fri[nzpm]
                -- r.opsel_a = AIN_B
                v.result_class := r.b.class;
                v.result_sign := r.b.negative;
                v.result_exp := r.b.exponent;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                if r.b.class = NAN and r.b.mantissa(53) = '0' then
                    -- Signalling NAN
                    v.fpscr(FPSCR_VXSNAN) := '1';
                    invalid := '1';
                end if;
                if r.b.class = FINITE then
                    if r.b.exponent >= to_signed(52, EXP_BITS) then
                        -- integer already, no rounding required
                        arith_done := '1';
                    else
                        v.shift := r.b.exponent - to_signed(52, EXP_BITS);
                        v.state := FRI_1;
                        v.round_mode := '1' & r.insn(7 downto 6);
                    end if;
                else
                    arith_done := '1';
                end if;

            when DO_FRSP =>
                -- r.opsel_a = AIN_B, r.shift = 0
                v.result_class := r.b.class;
                v.result_sign := r.b.negative;
                v.result_exp := r.b.exponent;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                if r.b.class = NAN and r.b.mantissa(53) = '0' then
                    -- Signalling NAN
                    v.fpscr(FPSCR_VXSNAN) := '1';
                    invalid := '1';
                end if;
                set_x := '1';
                if r.b.class = FINITE then
                    if r.b.exponent < to_signed(-126, EXP_BITS) then
                        v.shift := r.b.exponent - to_signed(-126, EXP_BITS);
                        v.state := ROUND_UFLOW;
                    elsif r.b.exponent > to_signed(127, EXP_BITS) then
                        v.state := ROUND_OFLOW;
                    else
                        v.state := ROUNDING;
                    end if;
                else
                    arith_done := '1';
                end if;

            when DO_FCTI =>
                -- instr bit 9: 1=dword 0=word
                -- instr bit 8: 1=unsigned 0=signed
                -- instr bit 1: 1=round to zero 0=use fpscr[RN]
                -- r.opsel_a = AIN_B
                v.result_class := r.b.class;
                v.result_sign := r.b.negative;
                v.result_exp := r.b.exponent;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                if r.b.class = NAN and r.b.mantissa(53) = '0' then
                    -- Signalling NAN
                    v.fpscr(FPSCR_VXSNAN) := '1';
                    invalid := '1';
                end if;

                v.int_result := '1';
                case r.b.class is
                    when ZERO =>
                        arith_done := '1';
                    when FINITE =>
                        if r.b.exponent >= to_signed(64, EXP_BITS) or
                            (r.insn(9) = '0' and r.b.exponent >= to_signed(32, EXP_BITS)) then
                            v.state := INT_OFLOW;
                        elsif r.b.exponent >= to_signed(52, EXP_BITS) then
                            -- integer already, no rounding required,
                            -- shift into final position
                            v.shift := r.b.exponent - to_signed(54, EXP_BITS);
                            if r.insn(8) = '1' and r.b.negative = '1' then
                                v.state := INT_OFLOW;
                            else
                                v.state := INT_ISHIFT;
                            end if;
                        else
                            v.shift := r.b.exponent - to_signed(52, EXP_BITS);
                            v.state := INT_SHIFT;
                        end if;
                    when INFINITY | NAN =>
                        v.state := INT_OFLOW;
                end case;

            when DO_FCFID =>
                -- r.opsel_a = AIN_B
                v.result_sign := '0';
                if r.insn(8) = '0' and r.b.negative = '1' then
                    -- fcfid[s] with negative operand, set R = -B
                    opsel_ainv <= '1';
                    carry_in <= '1';
                    v.result_sign := '1';
                end if;
                v.result_class := r.b.class;
                v.result_exp := to_signed(54, EXP_BITS);
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                if r.b.class = ZERO then
                    arith_done := '1';
                else
                    v.state := FINISH;
                end if;

            when DO_FADD =>
                -- fadd[s] and fsub[s]
                -- r.opsel_a = AIN_A
                v.result_sign := r.a.negative;
                v.result_class := r.a.class;
                v.result_exp := r.a.exponent;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                v.use_a := '1';
                v.use_b := '1';
                is_add := r.a.negative xor r.b.negative xor r.insn(1);
                if r.a.class = FINITE and r.b.class = FINITE then
                    v.is_subtract := not is_add;
                    v.add_bsmall := r.exp_cmp;
                    v.opsel_a := AIN_B;
                    if r.exp_cmp = '0' then
                        v.shift := r.a.exponent - r.b.exponent;
                        v.result_sign := r.b.negative xnor r.insn(1);
                        if r.a.exponent = r.b.exponent then
                            v.state := ADD_2;
                        else
                            v.longmask := '0';
                            v.state := ADD_SHIFT;
                        end if;
                    else
                        v.state := ADD_1;
                    end if;
                else
                    if r.a.class = NAN or r.b.class = NAN then
                        v.state := NAN_RESULT;
                    elsif r.a.class = INFINITY and r.b.class = INFINITY and is_add = '0' then
                        -- invalid operation, construct QNaN
                        v.fpscr(FPSCR_VXISI) := '1';
                        qnan_result := '1';
                        arith_done := '1';
                    elsif r.a.class = ZERO and r.b.class = ZERO and is_add = '0' then
                        -- return -0 for rounding to -infinity
                        v.result_sign := r.round_mode(1) and r.round_mode(0);
                        arith_done := '1';
                    elsif r.a.class = INFINITY or r.b.class = ZERO then
                        -- result is A
                        v.opsel_a := AIN_A;
                        v.state := EXC_RESULT;
                    else
                        -- result is +/- B
                        v.opsel_a := AIN_B;
                        v.negate := not r.insn(1);
                        v.state := EXC_RESULT;
                    end if;
                end if;

            when DO_FMUL =>
                -- fmul[s]
                -- r.opsel_a = AIN_A unless C is denorm and A isn't
                v.result_sign := r.a.negative xor r.c.negative;
                v.result_class := r.a.class;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                v.use_a := '1';
                v.use_c := '1';
                if r.a.class = FINITE and r.c.class = FINITE then
                    v.result_exp := r.a.exponent + r.c.exponent;
                    -- Renormalize denorm operands
                    if r.a.mantissa(54) = '0' then
                        v.state := RENORM_A;
                    elsif r.c.mantissa(54) = '0' then
                        v.state := RENORM_C;
                    else
                        f_to_multiply.valid <= '1';
                        v.state := MULT_1;
                    end if;
                else
                    if r.a.class = NAN or r.c.class = NAN then
                        v.state := NAN_RESULT;
                    elsif (r.a.class = INFINITY and r.c.class = ZERO) or
                        (r.a.class = ZERO and r.c.class = INFINITY) then
                        -- invalid operation, construct QNaN
                        v.fpscr(FPSCR_VXIMZ) := '1';
                        qnan_result := '1';
                    elsif r.a.class = ZERO or r.a.class = INFINITY then
                        -- result is +/- A
                        arith_done := '1';
                    else
                        -- r.c.class is ZERO or INFINITY
                        v.opsel_a := AIN_C;
                        v.negate := r.a.negative;
                        v.state := EXC_RESULT;
                    end if;
                end if;

            when DO_FDIV =>
                -- r.opsel_a = AIN_A unless B is denorm and A isn't
                v.result_class := r.a.class;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                v.use_a := '1';
                v.use_b := '1';
                v.result_sign := r.a.negative xor r.b.negative;
                v.result_exp := r.a.exponent - r.b.exponent;
                v.count := "00";
                if r.a.class = FINITE and r.b.class = FINITE then
                    -- Renormalize denorm operands
                    if r.a.mantissa(54) = '0' then
                        v.state := RENORM_A;
                    elsif r.b.mantissa(54) = '0' then
                        v.state := RENORM_B;
                    else
                        v.first := '1';
                        v.state := DIV_2;
                    end if;
                else
                    if r.a.class = NAN or r.b.class = NAN then
                        v.state := NAN_RESULT;
                    elsif r.b.class = INFINITY then
                        if r.a.class = INFINITY then
                            v.fpscr(FPSCR_VXIDI) := '1';
                            qnan_result := '1';
                        else
                            v.result_class := ZERO;
                        end if;
                        arith_done := '1';
                    elsif r.b.class = ZERO then
                        if r.a.class = ZERO then
                            v.fpscr(FPSCR_VXZDZ) := '1';
                            qnan_result := '1';
                        else
                            if r.a.class = FINITE then
                                zero_divide := '1';
                            end if;
                            v.result_class := INFINITY;
                        end if;
                        arith_done := '1';
                    else -- r.b.class = FINITE, result_class = r.a.class
                        arith_done := '1';
                    end if;
                end if;

            when DO_FSEL =>
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                if r.a.class = ZERO or (r.a.negative = '0' and r.a.class /= NAN) then
                    v.opsel_a := AIN_C;
                else
                    v.opsel_a := AIN_B;
                end if;
                v.quieten_nan := '0';
                v.state := EXC_RESULT;

            when DO_FSQRT =>
                -- r.opsel_a = AIN_B
                v.result_class := r.b.class;
                v.result_sign := r.b.negative;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                v.use_b := '1';
                case r.b.class is
                    when FINITE =>
                        v.result_exp := r.b.exponent;
                        if r.b.negative = '1' then
                            v.fpscr(FPSCR_VXSQRT) := '1';
                            qnan_result := '1';
                        elsif r.b.mantissa(54) = '0' then
                            v.state := RENORM_B;
                        elsif r.b.exponent(0) = '0' then
                            v.state := SQRT_1;
                        else
                            v.shift := to_signed(1, EXP_BITS);
                            v.state := RENORM_B2;
                        end if;
                    when NAN =>
                        v.state := NAN_RESULT;
                    when ZERO =>
                        -- result is B
                        arith_done := '1';
                    when INFINITY =>
                        if r.b.negative = '1' then
                            v.fpscr(FPSCR_VXSQRT) := '1';
                            qnan_result := '1';
                        -- else result is B
                        end if;
                        arith_done := '1';
                end case;

            when DO_FRE =>
                -- r.opsel_a = AIN_B
                v.result_class := r.b.class;
                v.result_sign := r.b.negative;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                v.use_b := '1';
                case r.b.class is
                    when FINITE =>
                        v.result_exp := - r.b.exponent;
                        if r.b.mantissa(54) = '0' then
                            v.state := RENORM_B;
                        else
                            v.state := FRE_1;
                        end if;
                    when NAN =>
                        v.state := NAN_RESULT;
                    when INFINITY =>
                        v.result_class := ZERO;
                        arith_done := '1';
                    when ZERO =>
                        v.result_class := INFINITY;
                        zero_divide := '1';
                        arith_done := '1';
                end case;

            when DO_FRSQRTE =>
                -- r.opsel_a = AIN_B
                v.result_class := r.b.class;
                v.result_sign := r.b.negative;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                v.use_b := '1';
                v.shift := to_signed(1, EXP_BITS);
                case r.b.class is
                    when FINITE =>
                        v.result_exp := r.b.exponent;
                        if r.b.negative = '1' then
                            v.fpscr(FPSCR_VXSQRT) := '1';
                            qnan_result := '1';
                        elsif r.b.mantissa(54) = '0' then
                            v.state := RENORM_B;
                        elsif r.b.exponent(0) = '0' then
                            v.state := RSQRT_1;
                        else
                            v.state := RENORM_B2;
                        end if;
                    when NAN =>
                        v.state := NAN_RESULT;
                    when INFINITY =>
                        if r.b.negative = '1' then
                            v.fpscr(FPSCR_VXSQRT) := '1';
                            qnan_result := '1';
                        else
                            v.result_class := ZERO;
                        end if;
                        arith_done := '1';
                    when ZERO =>
                        v.result_class := INFINITY;
                        zero_divide := '1';
                        arith_done := '1';
                end case;

            when DO_FMADD =>
                -- fmadd, fmsub, fnmadd, fnmsub
                -- r.opsel_a = AIN_A if A is denorm, else AIN_C if C is denorm,
                -- else AIN_B
                v.result_sign := r.a.negative;
                v.result_class := r.a.class;
                v.result_exp := r.a.exponent;
                v.fpscr(FPSCR_FR) := '0';
                v.fpscr(FPSCR_FI) := '0';
                v.use_a := '1';
                v.use_b := '1';
                v.use_c := '1';
                is_add := r.a.negative xor r.c.negative xor r.b.negative xor r.insn(1);
                if r.a.class = FINITE and r.c.class = FINITE and
                    (r.b.class = FINITE or r.b.class = ZERO) then
                    v.is_subtract := not is_add;
                    mulexp := r.a.exponent + r.c.exponent;
                    v.result_exp := mulexp;
                    -- Make sure A and C are normalized
                    if r.a.mantissa(54) = '0' then
                        v.state := RENORM_A;
                    elsif r.c.mantissa(54) = '0' then
                        v.state := RENORM_C;
                    elsif r.b.class = ZERO then
                        -- no addend, degenerates to multiply
                        v.result_sign := r.a.negative xor r.c.negative xor r.insn(2);
                        f_to_multiply.valid <= '1';
                        v.is_multiply := '1';
                        v.state := MULT_1;
                    elsif r.madd_cmp = '0' then
                        -- addend is bigger, do multiply first
                        v.result_sign := not (r.b.negative xor r.insn(1) xor r.insn(2));
                        f_to_multiply.valid <= '1';
                        v.state := FMADD_1;
                    else
                        -- product is bigger, shift B right and use it as the
                        -- addend to the multiplier
                        v.shift := r.b.exponent - mulexp + to_signed(64, EXP_BITS);
                        -- for subtract, multiplier does B - A * C
                        v.result_sign := not (r.a.negative xor r.c.negative xor r.insn(2) xor is_add);
                        v.result_exp := r.b.exponent;
                        v.state := FMADD_2;
                    end if;
                else
                    if r.a.class = NAN or r.b.class = NAN or r.c.class = NAN then
                        v.state := NAN_RESULT;
                    elsif (r.a.class = ZERO and r.c.class = INFINITY) or
                        (r.a.class = INFINITY and r.c.class = ZERO) then
                        -- invalid operation, construct QNaN
                        v.fpscr(FPSCR_VXIMZ) := '1';
                        qnan_result := '1';
                    elsif r.a.class = INFINITY or r.c.class = INFINITY then
                        if r.b.class = INFINITY and is_add = '0' then
                            -- invalid operation, construct QNaN
                            v.fpscr(FPSCR_VXISI) := '1';
                            qnan_result := '1';
                        else
                            -- result is infinity
                            v.result_class := INFINITY;
                            v.result_sign := r.a.negative xor r.c.negative xor r.insn(2);
                            arith_done := '1';
                        end if;
                    else
                        -- Here A is zero, C is zero, or B is infinity
                        -- Result is +/-B in all of those cases
                        v.opsel_a := AIN_B;
                        if r.b.class /= ZERO or is_add = '1' then
                            v.negate := not (r.insn(1) xor r.insn(2));
                        else
                            -- have to be careful about rule for 0 - 0 result sign
                            v.negate := r.b.negative xor (r.round_mode(1) and r.round_mode(0)) xor r.insn(2);
                        end if;
                        v.state := EXC_RESULT;
                    end if;
                end if;

            when RENORM_A =>
                renormalize := '1';
                v.state := RENORM_A2;
                if r.insn(4) = '1' then
                    v.opsel_a := AIN_C;
                else
                    v.opsel_a := AIN_B;
                end if;

            when RENORM_A2 =>
                -- r.opsel_a = AIN_C for fmul/fmadd, AIN_B for fdiv
                set_a := '1';
                v.result_exp := new_exp;
                if r.insn(4) = '1' then
                    if r.c.mantissa(54) = '1' then
                        if r.insn(3) = '0' or r.b.class = ZERO then
                            v.first := '1';
                            v.state := MULT_1;
                        else
                            v.madd_cmp := '0';
                            if new_exp + 1 >= r.b.exponent then
                                v.madd_cmp := '1';
                            end if;
                            v.opsel_a := AIN_B;
                            v.state := DO_FMADD;
                        end if;
                    else
                        v.state := RENORM_C;
                    end if;
                else
                    if r.b.mantissa(54) = '1' then
                        v.first := '1';
                        v.state := DIV_2;
                    else
                        v.state := RENORM_B;
                    end if;
                end if;

            when RENORM_B =>
                renormalize := '1';
                renorm_sqrt := r.is_sqrt;
                v.state := RENORM_B2;

            when RENORM_B2 =>
                set_b := '1';
                if r.is_sqrt = '0' then
                    v.result_exp := r.result_exp + r.shift;
                else
                    v.result_exp := new_exp;
                end if;
                v.opsel_a := AIN_B;
                v.state := LOOKUP;

            when RENORM_C =>
                renormalize := '1';
                v.state := RENORM_C2;

            when RENORM_C2 =>
                set_c := '1';
                v.result_exp := new_exp;
                if r.insn(3) = '0' or r.b.class = ZERO then
                    v.first := '1';
                    v.state := MULT_1;
                else
                    v.madd_cmp := '0';
                    if new_exp + 1 >= r.b.exponent then
                        v.madd_cmp := '1';
                    end if;
                    v.opsel_a := AIN_B;
                    v.state := DO_FMADD;
                end if;

            when ADD_1 =>
                -- transferring B to R
                v.shift := r.b.exponent - r.a.exponent;
                v.result_exp := r.b.exponent;
                v.longmask := '0';
                v.state := ADD_SHIFT;

            when ADD_SHIFT =>
                -- r.shift = - exponent difference, r.longmask = 0
                opsel_r <= RES_SHIFT;
                v.x := s_nz;
                set_x := '1';
                v.longmask := r.single_prec;
                if r.add_bsmall = '1' then
                    v.opsel_a := AIN_A;
                else
                    v.opsel_a := AIN_B;
                end if;
                v.state := ADD_2;

            when ADD_2 =>
                -- r.opsel_a = AIN_A if r.add_bsmall = 1 else AIN_B
                opsel_b <= BIN_R;
                opsel_binv <= r.is_subtract;
                carry_in <= r.is_subtract and not r.x;
                v.shift := to_signed(-1, EXP_BITS);
                v.state := ADD_3;

            when ADD_3 =>
                -- check for overflow or negative result (can't get both)
                -- r.shift = -1
                if r.r(63) = '1' then
                    -- result is opposite sign to expected
                    v.result_sign := not r.result_sign;
                    opsel_ainv <= '1';
                    carry_in <= '1';
                    v.state := FINISH;
                elsif r.r(55) = '1' then
                    -- sum overflowed, shift right
                    opsel_r <= RES_SHIFT;
                    set_x := '1';
                    if exp_huge = '1' then
                        v.state := ROUND_OFLOW;
                    else
                        v.state := ROUNDING;
                    end if;
                elsif r.r(54) = '1' then
                    set_x := '1';
                    v.state := ROUNDING;
                elsif (r_hi_nz or r_lo_nz or r.r(1) or r.r(0)) = '0' then
                    -- r.x must be zero at this point
                    v.result_class := ZERO;
                    if r.is_subtract = '1' then
                        -- set result sign depending on rounding mode
                        v.result_sign := r.round_mode(1) and r.round_mode(0);
                    end if;
                    arith_done := '1';
                else
                    renormalize := '1';
                    v.state := NORMALIZE;
                end if;

            when CMP_1 =>
                -- r.opsel_a = AIN_A
                opsel_b <= BIN_R;
                opsel_binv <= '1';
                carry_in <= '1';
                v.state := CMP_2;

            when CMP_2 =>
                if r.r(63) = '1' then
                    -- A is smaller in magnitude
                    v.cr_result := not r.a.negative & r.a.negative & "00";
                elsif (r_hi_nz or r_lo_nz) = '0' then
                    v.cr_result := "0010";
                else
                    v.cr_result := r.a.negative & not r.a.negative & "00";
                end if;
                v.fpscr(FPSCR_FL downto FPSCR_FU) := v.cr_result;
                v.instr_done := '1';
                v.state := IDLE;

            when MULT_1 =>
                f_to_multiply.valid <= r.first;
                opsel_r <= RES_MULT;
                if multiply_to_f.valid = '1' then
                    v.state := FINISH;
                end if;

            when FMADD_1 =>
                -- Addend is bigger here
                v.result_sign := not (r.b.negative xor r.insn(1) xor r.insn(2));
                -- note v.shift is at most -2 here
                v.shift := r.result_exp - r.b.exponent;
                opsel_r <= RES_MULT;
                opsel_s <= S_MULT;
                set_s := '1';
                f_to_multiply.valid <= r.first;
                if multiply_to_f.valid = '1' then
                    v.longmask := '0';
                    v.state := ADD_SHIFT;
                end if;

            when FMADD_2 =>
                -- Product is potentially bigger here
                -- r.shift = addend exp - product exp + 64, r.r = r.b.mantissa
                set_s := '1';
                opsel_s <= S_SHIFT;
                v.shift := r.shift - to_signed(64, EXP_BITS);
                v.state := FMADD_3;

            when FMADD_3 =>
                -- r.shift = addend exp - product exp
                opsel_r <= RES_SHIFT;
                v.first := '1';
                v.state := FMADD_4;

            when FMADD_4 =>
                msel_add <= MULADD_RS;
                f_to_multiply.valid <= r.first;
                msel_inv <= r.is_subtract;
                opsel_r <= RES_MULT;
                opsel_s <= S_MULT;
                set_s := '1';
                if multiply_to_f.valid = '1' then
                    v.state := FMADD_5;
                end if;

            when FMADD_5 =>
                -- negate R:S:X if negative
                if r.r(63) = '1' then
                    v.result_sign := not r.result_sign;
                    opsel_ainv <= '1';
                    carry_in <= not (s_nz or r.x);
                    opsel_s <= S_NEG;
                    set_s := '1';
                end if;
                v.shift := to_signed(56, EXP_BITS);
                v.state := FMADD_6;

            when FMADD_6 =>
                -- r.shift = 56 (or 0, but only if r is now nonzero)
                if (r.r(56) or r_hi_nz or r_lo_nz or r.r(1) or r.r(0)) = '0' then
                    if s_nz = '0' then
                        -- must be a subtraction, and r.x must be zero
                        v.result_class := ZERO;
                        v.result_sign := r.round_mode(1) and r.round_mode(0);
                        arith_done := '1';
                    else
                        -- R is all zeroes but there are non-zero bits in S
                        -- so shift them into R and set S to 0
                        opsel_r <= RES_SHIFT;
                        set_s := '1';
                        -- stay in state FMADD_6
                    end if;
                elsif r.r(56 downto 54) = "001" then
                    v.state := FINISH;
                else
                    renormalize := '1';
                    v.state := NORMALIZE;
                end if;

            when LOOKUP =>
                -- r.opsel_a = AIN_B
                -- wait one cycle for inverse_table[B] lookup
                v.first := '1';
                if r.insn(4) = '0' then
                    if r.insn(3) = '0' then
                        v.state := DIV_2;
                    else
                        v.state := SQRT_1;
                    end if;
                elsif r.insn(2) = '0' then
                    v.state := FRE_1;
                else
                    v.state := RSQRT_1;
                end if;

            when DIV_2 =>
                -- compute Y = inverse_table[B] (when count=0); P = 2 - B * Y
                msel_1 <= MUL1_B;
                msel_add <= MULADD_CONST;
                msel_inv <= '1';
                if r.count = 0 then
                    msel_2 <= MUL2_LUT;
                else
                    msel_2 <= MUL2_P;
                end if;
                set_y := r.first;
                pshift := '1';
                f_to_multiply.valid <= r.first;
                if multiply_to_f.valid = '1' then
                    v.first := '1';
                    v.count := r.count + 1;
                    v.state := DIV_3;
                end if;

            when DIV_3 =>
                -- compute Y = P = P * Y
                msel_1 <= MUL1_Y;
                msel_2 <= MUL2_P;
                f_to_multiply.valid <= r.first;
                pshift := '1';
                if multiply_to_f.valid = '1' then
                    v.first := '1';
                    if r.count = 3 then
                        v.state := DIV_4;
                    else
                        v.state := DIV_2;
                    end if;
                end if;

            when DIV_4 =>
                -- compute R = P = A * Y (quotient)
                msel_1 <= MUL1_A;
                msel_2 <= MUL2_P;
                set_y := r.first;
                f_to_multiply.valid <= r.first;
                pshift := '1';
                if multiply_to_f.valid = '1' then
                    opsel_r <= RES_MULT;
                    v.first := '1';
                    v.state := DIV_5;
                end if;

            when DIV_5 =>
                -- compute P = A - B * R (remainder)
                msel_1 <= MUL1_B;
                msel_2 <= MUL2_R;
                msel_add <= MULADD_A;
                msel_inv <= '1';
                f_to_multiply.valid <= r.first;
                if multiply_to_f.valid = '1' then
                    v.state := DIV_6;
                end if;

            when DIV_6 =>
                -- test if remainder is 0 or >= B
                if pcmpb_lt = '1' then
                    -- quotient is correct, set X if remainder non-zero
                    v.x := r.p(58) or px_nz;
                else
                    -- quotient needs to be incremented by 1
                    carry_in <= '1';
                    v.x := not pcmpb_eq;
                end if;
                v.state := FINISH;

            when FRE_1 =>
                opsel_r <= RES_MISC;
                misc_sel <= "0111";
                v.shift := to_signed(1, EXP_BITS);
                v.state := NORMALIZE;

            when FTDIV_1 =>
                v.cr_result(1) := exp_tiny or exp_huge;
                if exp_tiny = '1' or exp_huge = '1' or r.a.class = ZERO or r.first = '0' then
                    v.instr_done := '1';
                    v.state := IDLE;
                else
                    v.shift := r.a.exponent;
                    v.doing_ftdiv := "10";
                end if;

            when RSQRT_1 =>
                opsel_r <= RES_MISC;
                misc_sel <= "0111";
                sqrt_exp := r.b.exponent(EXP_BITS-1) & r.b.exponent(EXP_BITS-1 downto 1);
                v.result_exp := - sqrt_exp;
                v.shift := to_signed(1, EXP_BITS);
                v.state := NORMALIZE;

            when SQRT_1 =>
                -- put invsqr[B] in R and compute P = invsqr[B] * B
                -- also transfer B (in R) to A
                set_a := '1';
                opsel_r <= RES_MISC;
                misc_sel <= "0111";
                msel_1 <= MUL1_B;
                msel_2 <= MUL2_LUT;
                f_to_multiply.valid <= '1';
                v.shift := to_signed(-1, EXP_BITS);
                v.count := "00";
                v.state := SQRT_2;

            when SQRT_2 =>
                -- shift R right one place
                -- not expecting multiplier result yet
                -- r.shift = -1
                opsel_r <= RES_SHIFT;
                v.first := '1';
                v.state := SQRT_3;

            when SQRT_3 =>
                -- put R into Y, wait for product from multiplier
                msel_2 <= MUL2_R;
                set_y := r.first;
                pshift := '1';
                if multiply_to_f.valid = '1' then
                    -- put result into R
                    opsel_r <= RES_MULT;
                    v.first := '1';
                    v.state := SQRT_4;
                end if;

            when SQRT_4 =>
                -- compute 1.5 - Y * P
                msel_1 <= MUL1_Y;
                msel_2 <= MUL2_P;
                msel_add <= MULADD_CONST;
                msel_inv <= '1';
                f_to_multiply.valid <= r.first;
                pshift := '1';
                if multiply_to_f.valid = '1' then
                    v.state := SQRT_5;
                end if;

            when SQRT_5 =>
                -- compute Y = Y * P
                msel_1 <= MUL1_Y;
                msel_2 <= MUL2_P;
                f_to_multiply.valid <= '1';
                v.first := '1';
                v.state := SQRT_6;

            when SQRT_6 =>
                -- pipeline in R = R * P
                msel_1 <= MUL1_R;
                msel_2 <= MUL2_P;
                f_to_multiply.valid <= r.first;
                pshift := '1';
                if multiply_to_f.valid = '1' then
                    v.first := '1';
                    v.state := SQRT_7;
                end if;

            when SQRT_7 =>
                -- first multiply is done, put result in Y
                msel_2 <= MUL2_P;
                set_y := r.first;
                -- wait for second multiply (should be here already)
                pshift := '1';
                if multiply_to_f.valid = '1' then
                    -- put result into R
                    opsel_r <= RES_MULT;
                    v.first := '1';
                    v.count := r.count + 1;
                    if r.count < 2 then
                        v.state := SQRT_4;
                    else
                        v.first := '1';
                        v.state := SQRT_8;
                    end if;
                end if;

            when SQRT_8 =>
                -- compute P = A - R * R, which can be +ve or -ve
                -- we arranged for B to be put into A earlier
                msel_1 <= MUL1_R;
                msel_2 <= MUL2_R;
                msel_add <= MULADD_A;
                msel_inv <= '1';
                pshift := '1';
                f_to_multiply.valid <= r.first;
                if multiply_to_f.valid = '1' then
                    v.first := '1';
                    v.state := SQRT_9;
                end if;

            when SQRT_9 =>
                -- compute P = P * Y
                -- since Y is an estimate of 1/sqrt(B), this makes P an
                -- estimate of the adjustment needed to R.  Since the error
                -- could be negative and we have an unsigned multiplier, the
                -- upper bits can be wrong, but it turns out the lowest 8 bits
                -- are correct and are all we need (given 3 iterations through
                -- SQRT_4 to SQRT_7).
                msel_1 <= MUL1_Y;
                msel_2 <= MUL2_P;
                pshift := '1';
                f_to_multiply.valid <= r.first;
                if multiply_to_f.valid = '1' then
                    v.state := SQRT_10;
                end if;

            when SQRT_10 =>
                -- Add the bottom 8 bits of P, sign-extended,
                -- divided by 4, onto R.
                -- The division by 4 is because R is 10.54 format
                -- whereas P is 8.56 format.
                opsel_b <= BIN_PS6;
                sqrt_exp := r.b.exponent(EXP_BITS-1) & r.b.exponent(EXP_BITS-1 downto 1);
                v.result_exp := sqrt_exp;
                v.shift := to_signed(1, EXP_BITS);
                v.first := '1';
                v.state := SQRT_11;

            when SQRT_11 =>
                -- compute P = A - R * R (remainder)
                -- also put 2 * R + 1 into B for comparison with P
                msel_1 <= MUL1_R;
                msel_2 <= MUL2_R;
                msel_add <= MULADD_A;
                msel_inv <= '1';
                f_to_multiply.valid <= r.first;
                shiftin := '1';
                set_b := r.first;
                if multiply_to_f.valid = '1' then
                    v.state := SQRT_12;
                end if;

            when SQRT_12 =>
                -- test if remainder is 0 or >= B = 2*R + 1
                if pcmpb_lt = '1' then
                    -- square root is correct, set X if remainder non-zero
                    v.x := r.p(58) or px_nz;
                else
                    -- square root needs to be incremented by 1
                    carry_in <= '1';
                    v.x := not pcmpb_eq;
                end if;
                v.state := FINISH;

            when INT_SHIFT =>
                -- r.shift = b.exponent - 52
                opsel_r <= RES_SHIFT;
                set_x := '1';
                v.state := INT_ROUND;
                v.shift := to_signed(-2, EXP_BITS);

            when INT_ROUND =>
                -- r.shift = -2
                opsel_r <= RES_SHIFT;
                round := fp_rounding(r.r, r.x, '0', r.round_mode, r.result_sign);
                v.fpscr(FPSCR_FR downto FPSCR_FI) := round;
                -- Check for negative values that don't round to 0 for fcti*u*
                if r.insn(8) = '1' and r.result_sign = '1' and
                    (r_hi_nz or r_lo_nz or v.fpscr(FPSCR_FR)) = '1' then
                    v.state := INT_OFLOW;
                else
                    v.state := INT_FINAL;
                end if;

            when INT_ISHIFT =>
                -- r.shift = b.exponent - 54;
                opsel_r <= RES_SHIFT;
                v.state := INT_FINAL;

            when INT_FINAL =>
                -- Negate if necessary, and increment for rounding if needed
                opsel_ainv <= r.result_sign;
                carry_in <= r.fpscr(FPSCR_FR) xor r.result_sign;
                -- Check for possible overflows
                case r.insn(9 downto 8) is
                    when "00" =>        -- fctiw[z]
                        need_check := r.r(31) or (r.r(30) and not r.result_sign);
                    when "01" =>        -- fctiwu[z]
                        need_check := r.r(31);
                    when "10" =>        -- fctid[z]
                        need_check := r.r(63) or (r.r(62) and not r.result_sign);
                    when others =>      -- fctidu[z]
                        need_check := r.r(63);
                end case;
                if need_check = '1' then
                    v.state := INT_CHECK;
                else
                    if r.fpscr(FPSCR_FI) = '1' then
                        v.fpscr(FPSCR_XX) := '1';
                    end if;
                    arith_done := '1';
                end if;

            when INT_CHECK =>
                if r.insn(9) = '0' then
                    msb := r.r(31);
                else
                    msb := r.r(63);
                end if;
                misc_sel <= '1' & r.insn(9 downto 8) & r.result_sign;
                if (r.insn(8) = '0' and msb /= r.result_sign) or
                    (r.insn(8) = '1' and msb /= '1') then
                    opsel_r <= RES_MISC;
                    v.fpscr(FPSCR_VXCVI) := '1';
                    invalid := '1';
                else
                    if r.fpscr(FPSCR_FI) = '1' then
                        v.fpscr(FPSCR_XX) := '1';
                    end if;
                end if;
                arith_done := '1';

            when INT_OFLOW =>
                opsel_r <= RES_MISC;
                misc_sel <= '1' & r.insn(9 downto 8) & r.result_sign;
                if r.b.class = NAN then
                    misc_sel(0) <= '1';
                end if;
                v.fpscr(FPSCR_VXCVI) := '1';
                invalid := '1';
                arith_done := '1';

            when FRI_1 =>
                -- r.shift = b.exponent - 52
                opsel_r <= RES_SHIFT;
                set_x := '1';
                v.state := ROUNDING;

            when FINISH =>
                if r.is_multiply = '1' and px_nz = '1' then
                    v.x := '1';
                end if;
                if r.r(63 downto 54) /= "0000000001" then
                    renormalize := '1';
                    v.state := NORMALIZE;
                else
                    set_x := '1';
                    if exp_tiny = '1' then
                        v.shift := new_exp - min_exp;
                        v.state := ROUND_UFLOW;
                    elsif exp_huge = '1' then
                        v.state := ROUND_OFLOW;
                    else
                        v.state := ROUNDING;
                    end if;
                end if;

            when NORMALIZE =>
                -- Shift so we have 9 leading zeroes (we know R is non-zero)
                -- r.shift = clz(r.r) - 9
                opsel_r <= RES_SHIFT;
                set_x := '1';
                if exp_tiny = '1' then
                    v.shift := new_exp - min_exp;
                    v.state := ROUND_UFLOW;
                elsif exp_huge = '1' then
                    v.state := ROUND_OFLOW;
                else
                    v.state := ROUNDING;
                end if;

            when ROUND_UFLOW =>
                -- r.shift = - amount by which exponent underflows
                v.tiny := '1';
                if r.fpscr(FPSCR_UE) = '0' then
                    -- disabled underflow exception case
                    -- have to denormalize before rounding
                    opsel_r <= RES_SHIFT;
                    set_x := '1';
                    v.state := ROUNDING;
                else
                    -- enabled underflow exception case
                    -- if denormalized, have to normalize before rounding
                    v.fpscr(FPSCR_UX) := '1';
                    v.result_exp := r.result_exp + bias_exp;
                    if r.r(54) = '0' then
                        renormalize := '1';
                        v.state := NORMALIZE;
                    else
                        v.state := ROUNDING;
                    end if;
                end if;

            when ROUND_OFLOW =>
                v.fpscr(FPSCR_OX) := '1';
                if r.fpscr(FPSCR_OE) = '0' then
                    -- disabled overflow exception
                    -- result depends on rounding mode
                    v.fpscr(FPSCR_XX) := '1';
                    v.fpscr(FPSCR_FI) := '1';
                    if r.round_mode(1 downto 0) = "00" or
                        (r.round_mode(1) = '1' and r.round_mode(0) = r.result_sign) then
                        v.result_class := INFINITY;
                        v.fpscr(FPSCR_FR) := '1';
                    else
                        v.fpscr(FPSCR_FR) := '0';
                    end if;
                    -- construct largest representable number
                    v.result_exp := max_exp;
                    opsel_r <= RES_MISC;
                    misc_sel <= "001" & r.single_prec;
                    arith_done := '1';
                else
                    -- enabled overflow exception
                    v.result_exp := r.result_exp - bias_exp;
                    v.state := ROUNDING;
                end if;

            when ROUNDING =>
                opsel_mask <= '1';
                round := fp_rounding(r.r, r.x, r.single_prec, r.round_mode, r.result_sign);
                v.fpscr(FPSCR_FR downto FPSCR_FI) := round;
                if round(1) = '1' then
                    -- increment the LSB for the precision
                    opsel_b <= BIN_RND;
                    v.shift := to_signed(-1, EXP_BITS);
                    v.state := ROUNDING_2;
                else
                    if r.r(54) = '0' then
                        -- result after masking could be zero, or could be a
                        -- denormalized result that needs to be renormalized
                        renormalize := '1';
                        v.state := ROUNDING_3;
                    else
                        arith_done := '1';
                    end if;
                end if;
                if round(0) = '1' then
                    v.fpscr(FPSCR_XX) := '1';
                    if r.tiny = '1' then
                        v.fpscr(FPSCR_UX) := '1';
                    end if;
                end if;

            when ROUNDING_2 =>
                -- Check for overflow during rounding
                -- r.shift = -1
                v.x := '0';
                if r.r(55) = '1' then
                    opsel_r <= RES_SHIFT;
                    if exp_huge = '1' then
                        v.state := ROUND_OFLOW;
                    else
                        arith_done := '1';
                    end if;
                elsif r.r(54) = '0' then
                    -- Do CLZ so we can renormalize the result
                    renormalize := '1';
                    v.state := ROUNDING_3;
                else
                    arith_done := '1';
                end if;

            when ROUNDING_3 =>
                -- r.shift = clz(r.r) - 9
                mant_nz := r_hi_nz or (r_lo_nz and not r.single_prec);
                if mant_nz = '0' then
                    v.result_class := ZERO;
                    if r.is_subtract = '1' then
                        -- set result sign depending on rounding mode
                        v.result_sign := r.round_mode(1) and r.round_mode(0);
                    end if;
                    arith_done := '1';
                else
                    -- Renormalize result after rounding
                    opsel_r <= RES_SHIFT;
                    v.denorm := exp_tiny;
                    v.shift := new_exp - to_signed(-1022, EXP_BITS);
                    if new_exp < to_signed(-1022, EXP_BITS) then
                        v.state := DENORM;
                    else
                        arith_done := '1';
                    end if;
                end if;

            when DENORM =>
                -- r.shift = result_exp - -1022
                opsel_r <= RES_SHIFT;
                arith_done := '1';

            when NAN_RESULT =>
                if (r.use_a = '1' and r.a.class = NAN and r.a.mantissa(53) = '0') or
                    (r.use_b = '1' and r.b.class = NAN and r.b.mantissa(53) = '0') or
                    (r.use_c = '1' and r.c.class = NAN and r.c.mantissa(53) = '0') then
                    -- Signalling NAN
                    v.fpscr(FPSCR_VXSNAN) := '1';
                    invalid := '1';
                end if;
                if r.use_a = '1' and r.a.class = NAN then
                    v.opsel_a := AIN_A;
                elsif r.use_b = '1' and r.b.class = NAN then
                    v.opsel_a := AIN_B;
                elsif r.use_c = '1' and r.c.class = NAN then
                    v.opsel_a := AIN_C;
                end if;
                v.state := EXC_RESULT;

            when EXC_RESULT =>
                -- r.opsel_a = AIN_A, AIN_B or AIN_C according to which input is the result
                case r.opsel_a is
                    when AIN_B =>
                        v.result_sign := r.b.negative xor r.negate;
                        v.result_exp := r.b.exponent;
                        v.result_class := r.b.class;
                    when AIN_C =>
                        v.result_sign := r.c.negative xor r.negate;
                        v.result_exp := r.c.exponent;
                        v.result_class := r.c.class;
                    when others =>
                        v.result_sign := r.a.negative xor r.negate;
                        v.result_exp := r.a.exponent;
                        v.result_class := r.a.class;
                end case;
                arith_done := '1';

        end case;

        if zero_divide = '1' then
            v.fpscr(FPSCR_ZX) := '1';
        end if;
        if qnan_result = '1' then
            invalid := '1';
            v.result_class := NAN;
            v.result_sign := '0';
            misc_sel <= "0001";
            opsel_r <= RES_MISC;
            arith_done := '1';
        end if;
        if invalid = '1' then
            v.invalid := '1';
        end if;
        if arith_done = '1' then
            -- Enabled invalid exception doesn't write result or FPRF
            -- Neither does enabled zero-divide exception
            if (v.invalid and r.fpscr(FPSCR_VE)) = '0' and
                (zero_divide and r.fpscr(FPSCR_ZE)) = '0' then
                v.writing_back := '1';
                v.update_fprf := '1';
            end if;
            v.instr_done := '1';
            v.state := IDLE;
            update_fx := '1';
        end if;

        -- Multiplier and divide/square root data path
        case msel_1 is
            when MUL1_A =>
                f_to_multiply.data1 <= r.a.mantissa(61 downto 0) & "00";
            when MUL1_B =>
                f_to_multiply.data1 <= r.b.mantissa(61 downto 0) & "00";
            when MUL1_Y =>
                f_to_multiply.data1 <= r.y;
            when others =>
                f_to_multiply.data1 <= r.r(61 downto 0) & "00";
        end case;
        case msel_2 is
            when MUL2_C =>
                f_to_multiply.data2 <= r.c.mantissa(61 downto 0) & "00";
            when MUL2_LUT =>
                f_to_multiply.data2 <= x"00" & inverse_est & '0' & x"000000000";
            when MUL2_P =>
                f_to_multiply.data2 <= r.p;
            when others =>
                f_to_multiply.data2 <= r.r(61 downto 0) & "00";
        end case;
        maddend := (others => '0');
        case msel_add is
            when MULADD_CONST =>
                -- addend is 2.0 or 1.5 in 16.112 format
                if r.is_sqrt = '0' then
                    maddend(113) := '1';                -- 2.0
                else
                    maddend(112 downto 111) := "11";    -- 1.5
                end if;
            when MULADD_A =>
                -- addend is A in 16.112 format
                maddend(121 downto 58) := r.a.mantissa;
            when MULADD_RS =>
                -- addend is concatenation of R and S in 16.112 format
                maddend := "000000" & r.r & r.s & "00";
            when others =>
        end case;
        if msel_inv = '1' then
            f_to_multiply.addend <= not maddend;
        else
            f_to_multiply.addend <= maddend;
        end if;
        f_to_multiply.not_result <= msel_inv;
        if set_y = '1' then
            v.y := f_to_multiply.data2;
        end if;
        if multiply_to_f.valid = '1' then
            if pshift = '0' then
                v.p := multiply_to_f.result(63 downto 0);
            else
                v.p := multiply_to_f.result(119 downto 56);
            end if;
        end if;

        -- Data path.
        -- This has A and B input multiplexers, an adder, a shifter,
        -- count-leading-zeroes logic, and a result mux.
        if r.longmask = '1' then
            mshift := r.shift + to_signed(-29, EXP_BITS);
        else
            mshift := r.shift;
        end if;
        if mshift < to_signed(-64, EXP_BITS) then
            mask := (others => '1');
        elsif mshift >= to_signed(0, EXP_BITS) then
            mask := (others => '0');
        else
            mask := right_mask(unsigned(mshift(5 downto 0)));
        end if;
        case r.opsel_a is
            when AIN_R =>
                in_a0 := r.r;
            when AIN_A =>
                in_a0 := r.a.mantissa;
            when AIN_B =>
                in_a0 := r.b.mantissa;
            when others =>
                in_a0 := r.c.mantissa;
        end case;
        if (or (mask and in_a0)) = '1' and set_x = '1' then
            v.x := '1';
        end if;
        if opsel_ainv = '1' then
            in_a0 := not in_a0;
        end if;
        in_a <= in_a0;
        case opsel_b is
            when BIN_ZERO =>
                in_b0 := (others => '0');
            when BIN_R =>
                in_b0 := r.r;
            when BIN_RND =>
                round_inc := (31 => r.single_prec, 2 => not r.single_prec, others => '0');
                in_b0 := round_inc;
            when others =>
                -- BIN_PS6, 6 LSBs of P/4 sign-extended to 64
                in_b0 := std_ulogic_vector(resize(signed(r.p(7 downto 2)), 64));
        end case;
        if opsel_binv = '1' then
            in_b0 := not in_b0;
        end if;
        in_b <= in_b0;
        if r.shift >= to_signed(-64, EXP_BITS) and r.shift <= to_signed(63, EXP_BITS) then
            shift_res := shifter_64(r.r & (shiftin or r.s(55)) & r.s(54 downto 0),
                                    std_ulogic_vector(r.shift(6 downto 0)));
        else
            shift_res := (others => '0');
        end if;
        sum := std_ulogic_vector(unsigned(in_a) + unsigned(in_b) + carry_in);
        if opsel_mask = '1' then
            sum(1 downto 0) := "00";
            if r.single_prec = '1' then
                sum(30 downto 2) := (others => '0');
            end if;
        end if;
        case opsel_r is
            when RES_SUM =>
                result <= sum;
            when RES_SHIFT =>
                result <= shift_res;
            when RES_MULT =>
                result <= multiply_to_f.result(121 downto 58);
            when others =>
                case misc_sel is
                    when "0000" =>
                        misc := x"00000000" & (r.fpscr and fpscr_mask);
                    when "0001" =>
                        -- generated QNaN mantissa
                        misc := x"0020000000000000";
                    when "0010" =>
                        -- mantissa of max representable DP number
                        misc := x"007ffffffffffffc";
                    when "0011" =>
                        -- mantissa of max representable SP number
                        misc := x"007fffff80000000";
                    when "0100" =>
                        -- fmrgow result
                        misc := r.a.mantissa(31 downto 0) & r.b.mantissa(31 downto 0);
                    when "0110" =>
                        -- fmrgew result
                        misc := r.a.mantissa(63 downto 32) & r.b.mantissa(63 downto 32);
                    when "0111" =>
                        misc := 10x"000" & inverse_est & 35x"000000000";
                    when "1000" =>
                        -- max positive result for fctiw[z]
                        misc := x"000000007fffffff";
                    when "1001" =>
                        -- max negative result for fctiw[z]
                        misc := x"ffffffff80000000";
                    when "1010" =>
                        -- max positive result for fctiwu[z]
                        misc := x"00000000ffffffff";
                    when "1011" =>
                        -- max negative result for fctiwu[z]
                        misc := x"0000000000000000";
                    when "1100" =>
                        -- max positive result for fctid[z]
                        misc := x"7fffffffffffffff";
                    when "1101" =>
                        -- max negative result for fctid[z]
                        misc := x"8000000000000000";
                    when "1110" =>
                        -- max positive result for fctidu[z]
                        misc := x"ffffffffffffffff";
                    when "1111" =>
                        -- max negative result for fctidu[z]
                        misc := x"0000000000000000";
                    when others =>
                        misc := x"0000000000000000";
                end case;
                result <= misc;
        end case;
        v.r := result;
        if set_s = '1' then
            case opsel_s is
                when S_NEG =>
                    v.s := std_ulogic_vector(unsigned(not r.s) + (not r.x));
                when S_MULT =>
                    v.s := multiply_to_f.result(57 downto 2);
                when S_SHIFT =>
                    v.s := shift_res(63 downto 8);
                    if shift_res(7 downto 0) /= x"00" then
                        v.x := '1';
                    end if;
                when others =>
                    v.s := (others => '0');
            end case;
        end if;

        if set_a = '1' then
            v.a.exponent := new_exp;
            v.a.mantissa := shift_res;
        end if;
        if set_b = '1' then
            v.b.exponent := new_exp;
            v.b.mantissa := shift_res;
        end if;
        if set_c = '1' then
            v.c.exponent := new_exp;
            v.c.mantissa := shift_res;
        end if;

        if opsel_r = RES_SHIFT then
            v.result_exp := new_exp;
        end if;

        if renormalize = '1' then
            clz := count_left_zeroes(r.r);
            if renorm_sqrt = '1' then
                -- make denormalized value end up with even exponent
                clz(0) := '1';
            end if;
            v.shift := resize(signed('0' & clz) - 9, EXP_BITS);
        end if;

        if r.int_result = '1' then
            fp_result <= r.r;
        else
            fp_result <= pack_dp(r.result_sign, r.result_class, r.result_exp, r.r,
                                 r.single_prec, r.quieten_nan);
        end if;
        if r.update_fprf = '1' then
            v.fpscr(FPSCR_C downto FPSCR_FU) := result_flags(r.result_sign, r.result_class,
                                                             r.r(54) and not r.denorm);
        end if;

        v.fpscr(FPSCR_VX) := (or (v.fpscr(FPSCR_VXSNAN downto FPSCR_VXVC))) or
                             (or (v.fpscr(FPSCR_VXSOFT downto FPSCR_VXCVI)));
        v.fpscr(FPSCR_FEX) := or (v.fpscr(FPSCR_VX downto FPSCR_XX) and
                                  v.fpscr(FPSCR_VE downto FPSCR_XE));
        if update_fx = '1' and
            (v.fpscr(FPSCR_VX downto FPSCR_XX) and not r.old_exc) /= "00000" then
            v.fpscr(FPSCR_FX) := '1';
        end if;
        if r.rc = '1' then
            v.cr_result := v.fpscr(FPSCR_FX downto FPSCR_OX);
        end if;

        v.illegal := illegal;
        if illegal = '1' then
            v.instr_done := '0';
            v.do_intr := '1';
            v.writing_back := '0';
            v.busy := '0';
            v.state := IDLE;
        else
            v.do_intr := v.instr_done and v.fpscr(FPSCR_FEX) and r.fe_mode;
            if v.state /= IDLE or v.do_intr = '1' then
                v.busy := '1';
            end if;
        end if;

        rin <= v;
    end process;

end architecture behaviour;
