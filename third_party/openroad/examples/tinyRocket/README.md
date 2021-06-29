### Summary
RISC-V Rocket Chip design (TinyConfig)
Currently has about 30,000 cells

### Source
Contributed by Ben Keller on Jun 25 2019
Original source: https://github.com/chipsalliance/rocket-chip

### Modifications
- Use the default TinyConfig
- Turn the IMem and DMem sizes down to minimum
- Mapped some memory macros instead
- Target RocketTile for synthesis, which is the actual processor (this avoids all the system bus overhead included in the top level)
- Added sdc timing constraints
- Added LICENSE files from https://github.com/chipsalliance/rocket-chip
