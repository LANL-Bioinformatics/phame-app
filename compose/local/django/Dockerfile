#FROM python:3.6-alpine
#
#ENV PYTHONUNBUFFERED 1
#
#RUN apk update \
#  # psycopg2 dependencies
#  && apk add --virtual build-deps gcc python3-dev musl-dev \
#  && apk add postgresql-dev \
#  # Pillow dependencies
#  && apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev \
#  # CFFI dependencies
#  && apk add libffi-dev py-cffi \
#  # Translations dependencies
#  && apk add gettext \
#  # https://docs.djangoproject.com/en/dev/ref/django-admin/#dbshell
#  && apk add postgresql-client
FROM python:3.6

MAINTAINER Mark Flynn <mflynn@lanl.gov>

# Packages dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -yq upgrade
RUN DEBIAN_FRONTEND=noninteractive apt-get -yq install \
	python-pip \
	python-dev \
	python-mysqldb \
	python-numpy \
	python-scipy \
	postgresql-client \
	postgresql \
	libpq-dev \
	postgresql-client-common

RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip install -r /requirements/local.txt

COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r//' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/local/django/start /start
RUN sed -i 's/\r//' /start
RUN chmod +x /start

WORKDIR /app

ENTRYPOINT ["/entrypoint"]
