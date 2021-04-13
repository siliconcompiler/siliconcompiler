import numpy

# Example Python generator to create two permutations of a design with
# different clock periods.
def permutations(cfg):
  for i in numpy.arange(0.5, 1.5, 0.5):
      cfg['clock']['default']['period']['value'] = [str(i)]
      yield cfg
