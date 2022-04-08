FROM ubuntu:20.04

RUN apt-get update && apt-get upgrade -y && apt-get -y install python3 cmake wget
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install git python3-pip lsb-core libqt5designer5 libqt5multimedia5 libqt5multimediawidgets5 libqt5xmlpatterns5 libqt5printsupport5 libqt5sql5 libruby2.7

RUN git clone https://github.com/siliconcompiler/siliconcompiler.git

COPY container_init.py /siliconcompiler/container_init.py
RUN cd siliconcompiler && python3 container_init.py
RUN echo 'source /siliconcompiler/third_party/tools/openroad/setup_env.sh' >> ~/.bashrc
RUN echo 'export PYTHONPATH=$PYTHONPATH:/siliconcompiler' >> ~/.bashrc
