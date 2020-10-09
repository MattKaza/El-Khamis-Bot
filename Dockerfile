FROM python:3.8-slim-buster


RUN adduser python

RUN mkdir /home/python/bel-khamis && chown -R python:python /home/python/bel-khamis
WORKDIR /home/python/bel-khamis

RUN apt-get update && apt-get -y install ffmpeg

COPY requirements.txt ./
RUN pip install -r requirements.txt

USER python

COPY --chown=python:python ./src ./src
COPY --chown=python:python ./resources ./resources

CMD python3 ./src/new_bot.py