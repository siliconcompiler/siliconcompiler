/* Testbench for bambu: main() calls the top-level function so the simulator
   can count the cycles each invocation takes. The signature has to match the
   synthesized one exactly. */
extern short gcd(short a, short b);

int main() {
  if (gcd(4, 4) != 4) return 1;
  if (gcd(27, 36) != 9) return 1;
  if (gcd(270, 192) != 6) return 1;
  return 0;
}
