FROM python:3.8-slim-buster

RUN mkdir /home/python/bel-khamis && chown -R python:python /home/python/bel-khamis
WORKDIR /home/python/bel-khamis

RUN apt-get install ffmpeg

COPY requirements.txt ./
RUN pip install -r requirements.txt

USER python

ENV BOT_TOKEN Njk2MTIxODkzNTc2NjM4NTc0.XokICA.l7N_GEwoUbNi4biXlV2gvDfp3QM

COPY --chown=python:python ./src ./src
COPY --chown=python:python ./resources ./resources

CMD python3 ./src/new_bot.py