set wrapper {
  around {
    gf12_1rf_lg6_w32_all  gf12_1rf_lg6_w32_all_mod
    gf12_1rf_lg6_w32_byte gf12_1rf_lg6_w32_byte_mod
    gf12_2rf_lg10_w32_bit gf12_2rf_lg10_w32_bit_mod
  }
  by {
    gf12_1rf_lg6_w32_all_mod  gf12_1rf_lg6_w32_all
    gf12_1rf_lg6_w32_byte_mod gf12_1rf_lg6_w32_byte
    gf12_2rf_lg10_w32_bit_mod gf12_2rf_lg10_w32_bit
  }
}
