set wrapper {
  around {
    gf14_1rf_lg6_w32_all  gf14_1rf_lg6_w32_all_mod
    gf14_1rf_lg6_w32_byte gf14_1rf_lg6_w32_byte_mod
    gf14_2rf_lg10_w32_bit gf14_2rf_lg10_w32_bit_mod
  }
  by {
    gf14_1rf_lg6_w32_all_mod  gf14_1rf_lg6_w32_all
    gf14_1rf_lg6_w32_byte_mod gf14_1rf_lg6_w32_byte
    gf14_2rf_lg10_w32_bit_mod gf14_2rf_lg10_w32_bit
  }
}
