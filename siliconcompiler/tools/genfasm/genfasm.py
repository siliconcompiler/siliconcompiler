'''
To-Do: Add details here
'''

######################################################################
# Make Docs
######################################################################
def make_docs(chip):
    from tools.genfasm.bitstream import setup
    setup(chip)
    return chip

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_manifest("genfasm.json")
