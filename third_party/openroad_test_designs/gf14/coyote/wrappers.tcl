set wrapper {
  around {
    gf14_1rf_lg6_w80_bit  gf14_1rf_lg6_w80_bit_mod
    gf14_1rf_lg8_w128_all gf14_1rf_lg8_w128_all_mod
    gf14_2rf_lg6_w44_bit  gf14_2rf_lg6_w44_bit_mod
    gf14_2rf_lg8_w64_bit  gf14_2rf_lg8_w64_bit_mod
  }
  by {
    gf14_1rf_lg6_w80_bit_mod  gf14_1rf_lg6_w80_bit
    gf14_1rf_lg8_w128_all_mod gf14_1rf_lg8_w128_all
    gf14_2rf_lg6_w44_bit_mod  gf14_2rf_lg6_w44_bit
    gf14_2rf_lg8_w64_bit_mod  gf14_2rf_lg8_w64_bit
  }
}
