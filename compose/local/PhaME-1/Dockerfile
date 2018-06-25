# This is the Dockefile to build PhaME

############################# Base Docker Image ################################

FROM ubuntu:16.04

############################# MAINTAINER #######################################

MAINTAINER Migun Shakya <migun@lanl.gov>

############################# METADATA #######################################

LABEL version="1.0"
LABEL software="PhaME"
LABEL description="Phylogenetic Analysis and Molecular Evolution"
LABEL website="https://github.com/mshakya/PhaME-1"
LABEL tags="genomics"

############################# INSTALLATION #####################################
#ENTRYPOINT [ "/bin/bash", "-c" ]
RUN apt-get -y update --fix-missing
RUN apt-get install -y wget bzip2 ca-certificates libglib2.0-0 libxext6 libsm6 \
	libxrender1 git curl make gcc gfortran g++ grep unzip cmake libcurl4-gnutls-dev \
	ocl-icd-opencl-dev mpich doxygen libssl-dev
RUN apt-get -y upgrade
RUN apt-get clean
#RUN mkdir -p phame_analysis_folder && mkdir -p phame_analysis_folder/refdir && mkdir -p phame_analysis_folder/workdir
RUN	git clone https://github.com/mshakya/PhaME-1.git
WORKDIR /PhaME-1
RUN ./INSTALL.sh
ENV PATH="/PhaME-1/thirdParty/miniconda/bin:/PhaME-1/src:${PATH}"
#CMD ["/bin/sh"]
#COPY env_docker_new.yml /PhaME-1
#RUN conda env create -n phame_api -f env_docker_new.yml
#RUN [ "/bin/bash", "-c", "source activate phame_api"]
# RUN sh test/TestAll.sh
#############################ENVIRONMENT#####################################
