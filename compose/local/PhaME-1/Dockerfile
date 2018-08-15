# This is the Dockefile to build PhaME

############################# Base Docker Image ################################

FROM migun/phame-1

############################# MAINTAINER #######################################

ENV PATH="/PhaME-1/thirdParty/miniconda/envs/phame/bin:/app:${PATH}"
COPY /web /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
#############################ENVIRONMENT#####################################
