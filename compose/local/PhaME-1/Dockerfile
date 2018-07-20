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
RUN apt-get install -y python-pip python-dev build-essential
RUN apt-get -y upgrade
RUN apt-get clean

#RUN mkdir -p phame_analysis_folder && mkdir -p phame_analysis_folder/refdir && mkdir -p phame_analysis_folder/workdir
RUN	git clone https://github.com/mshakya/PhaME-1.git
WORKDIR /PhaME-1
RUN ./INSTALL.sh
ENV PATH="/PhaME-1/thirdParty/miniconda/bin:/PhaME-1/src:${PATH}"

COPY /web /app
WORKDIR /app
#RUN chmod ugo+x docker_run_phame.sh
RUN pip install Flask==0.10.1 flask-wtf
#ENTRYPOINT ["python"]
#CMD ["app.py"]
#CMD ["source activate phame && exec python app.py"]

# RUN sh test/TestAll.sh
#############################ENVIRONMENT#####################################
