# SiliconCompiler Docker Image Setup

Please note that Docker support is experimental at this time.

To build a Docker image with `sc` and the minimum required EDA tools, use the `Dockerfile` in this directory:

    docker build -t sc_tools .

Once the image is built, you can create a container and log into it:

    docker run --name my_sc_container -dit sc_tools
    docker start my_sc_container
    docker attach my_sc_container

Once you are logged into the container, you can test the installation by building a small example design:

    cd /siliconcompiler
    sc examples/gcd/gcd.v

The default keyboard sequence to detach from a running Docker container is Ctrl+P followed by Ctrl+Q (^P, ^Q). If you type `exit` into the container's shell, the container will stop and you'll need to restart it before you can attach to it again.
