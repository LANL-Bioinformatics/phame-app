FROM python:3.6

ENV CELERY_BROKER_URL redis://redis:6379/0
ENV CELERY_RESULT_BACKEND redis://redis:6379/0
ENV C_FORCE_ROOT true

ENV HOST 0.0.0.0
ENV PORT 5090
ENV DEBUG true

WORKDIR /api
ADD ./requirements.txt /api
# install requirements
RUN pip install -r requirements.txt
COPY . /api
# expose the app port
EXPOSE 5090

#RUN pip install gunicorn

# run the app server
#CMD ["gunicorn", "--bind", "0.0.0.0:5090", "--workers", "3", "app:app"]
CMD ["python", "app.py"]
