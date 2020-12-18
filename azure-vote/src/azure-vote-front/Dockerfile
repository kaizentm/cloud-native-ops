FROM tiangolo/uwsgi-nginx-flask:python3.6 AS python36
RUN pip install redis
ADD . /app

FROM tiangolo/uwsgi-nginx-flask:python3.7 AS python37
RUN pip install redis
ADD . /app

FROM tiangolo/uwsgi-nginx-flask:python3.8-alpine AS python38-alpine
RUN pip install redis
ADD . /app

FROM tiangolo/uwsgi-nginx-flask:python3.8
RUN pip install redis
ADD . /app