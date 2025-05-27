'''
Surfer is a waveform viewer with a focus on a snappy usable
interface and extensibility.

Documentation: https://gitlab.com/surfer-project/surfer/-/wikis/home

Sources: https://gitlab.com/surfer-project/surfer

Installation: https://gitlab.com/surfer-project/surfer#installation
'''


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    from siliconcompiler.tools.surfer import show
    show.setup(chip)
    return chip


def parse_version(stdout):
    # surfer 0.3.0
    return stdout.strip().split()[1]


####################################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_manifest("surfer.json")
