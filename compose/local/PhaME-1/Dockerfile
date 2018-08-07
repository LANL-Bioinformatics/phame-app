# This is the Dockefile to build PhaME

############################# Base Docker Image ################################

FROM migun/phame-1

############################# MAINTAINER #######################################

ENV PATH="/PhaME-1/thirdParty/miniconda/envs/phame/bin:/app:${PATH}"
COPY /web /app
WORKDIR /app
#RUN chmod ugo+x docker_run_phame.sh
#RUN pip install Flask==1.0.2 flask-wtf uwsgi pandas==0.23.1 psycopg2 flask-login flask-migrate flask-sqlalchemy
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
#############################ENVIRONMENT#####################################
