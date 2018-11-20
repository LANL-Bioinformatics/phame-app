# This is the Dockefile to build PhaME

############################# Base Docker Image ################################

#FROM migun/phame-1
FROM quay.io/biocontainers/phame:1.0.3--0
############################# MAINTAINER #######################################

ENV PATH="/PhaME-1/thirdParty/miniconda/envs/phame/bin:/app:${PATH}"


# expose the app port
EXPOSE 5001
COPY /requirements/phame_requirements.txt /tmp/requirements.txt
WORKDIR /tmp
RUN pip install -r requirements.txt
COPY /web /app
WORKDIR /app
#CMD ["python", "app.py"]
#############################ENVIRONMENT#####################################
ENV CELERY_BROKER_URL redis://redis:6379/0
ENV CELERY_RESULT_BACKEND redis://redis:6379/0
ENV C_FORCE_ROOT true


ENTRYPOINT celery -A tasks worker --loglevel=info
