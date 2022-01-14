# Initialization script for siliconcompiler docker containers.
# This installs some open-source EDA tools using scripts from the sc repository.

import subprocess

installs = ['surelog', 'klayout', 'magic', 'openroad', 'python']
for i in installs:
    script_path = 'setup/install-'+i+'.sh'
    # Commands run as root from the Docker setup script; no 'sudo' required.
    subprocess.run('sed -i "s/sudo //g" ' + script_path, shell=True)
    subprocess.run(script_path, shell=True)
