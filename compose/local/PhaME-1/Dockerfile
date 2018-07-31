# This is the Dockefile to build PhaME

############################# Base Docker Image ################################

FROM migun/phame-1

############################# MAINTAINER #######################################

ENV PATH="/PhaME-1/thirdParty/miniconda/envs/phame/bin:/app:${PATH}"

COPY /web /app
WORKDIR /app
#RUN chmod ugo+x docker_run_phame.sh
RUN pip install Flask==0.10.1 flask-wtf uwsgi pandas==0.23.1
#ENTRYPOINT ["python"]
CMD ["app.py"]
#CMD ["source activate phame && exec python app.py"]

# RUN sh test/TestAll.sh
#############################ENVIRONMENT#####################################
