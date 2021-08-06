# Example Python generator for siliconcompiler design permutations.
# Build the provided design twice using different PDKs
def permutations(cfg):
  cfg['target']['value'] = ['freepdk45_asicflow']
  cfg['asic']['diesize']['value'] = ['0 0 100.13 100.8']
  cfg['asic']['coresize']['value'] = ['10.07 11.2 90.25 91']
  yield cfg
  cfg['target']['value'] = ['skywater130_asicflow']
  cfg['asic']['diesize']['value'] = ['0 0 200.56 201.28']
  cfg['asic']['coresize']['value'] = ['20.24 21.76 180.32 184.96']
  yield cfg
