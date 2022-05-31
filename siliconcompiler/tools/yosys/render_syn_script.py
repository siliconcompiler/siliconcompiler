from jinja2 import Template

with open('syn_fpga.ys') as file_:
    template = Template(file_.read()) 

data = {
    "topmodule": "blah"
}


with open("my_new_file.ys", "w") as fh:
    fh.write(template.render(data))
