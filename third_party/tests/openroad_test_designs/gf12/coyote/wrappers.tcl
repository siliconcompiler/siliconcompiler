set wrapper {
  around {
    gf12_1rf_lg6_w80_bit  gf12_1rf_lg6_w80_bit_mod
    gf12_1rf_lg8_w128_all gf12_1rf_lg8_w128_all_mod
    gf12_2rf_lg6_w44_bit  gf12_2rf_lg6_w44_bit_mod
    gf12_2rf_lg8_w64_bit  gf12_2rf_lg8_w64_bit_mod
  }
  by {
    gf12_1rf_lg6_w80_bit_mod  gf12_1rf_lg6_w80_bit
    gf12_1rf_lg8_w128_all_mod gf12_1rf_lg8_w128_all
    gf12_2rf_lg6_w44_bit_mod  gf12_2rf_lg6_w44_bit
    gf12_2rf_lg8_w64_bit_mod  gf12_2rf_lg8_w64_bit
  }
}
