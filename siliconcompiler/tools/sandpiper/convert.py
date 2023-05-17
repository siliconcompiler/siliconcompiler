import os
import shutil

# Directory inside step/index dir to store sandpiper intermediate results.
VLOG_DIR = 'verilog'


def setup(chip):
    '''
    Invokes TL-Verilog Interpreter to generate a verilog/systemverilog output
    '''

    tool = 'sandpiper'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    print("task ",task)
    print(f"step {step} index {index}")

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'sandpiper-saas')
    chip.set('option','novercheck',True)
    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    # Schema requirements
    chip.add('tool', tool, 'task', task, 'require', 'input,hll,tlv')


################################
# Pre-process
################################
def pre_process(chip):
    # Create an intermediate directory to place all the files generated from Sandpiper, and pass on only the design file to the next stage
    if os.path.isdir(VLOG_DIR):
        shutil.rmtree(VLOG_DIR)
    os.makedirs(VLOG_DIR)


################################
# Post-process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    # Sandpiper-saas outputs files other files concerned with simulation. This function copies only the generated verilog of the design to the outputs
    design = chip.top()
    with open(os.path.join('outputs', f'{design}.v'), 'w') as pickled_vlog:
        print("post processing start")
        print("Current dir :",os.getcwd())
        print(os.listdir(VLOG_DIR))
        for src in os.listdir(VLOG_DIR):
            print("Current src: ",src)
            if os.path.isfile(os.path.join(VLOG_DIR,src)):
               
               with open(os.path.join(VLOG_DIR,src), 'r') as vlog_mod:
                    pickled_vlog.write(vlog_mod.read())
