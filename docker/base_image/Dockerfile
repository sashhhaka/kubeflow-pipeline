FROM docker.art.lmru.tech/img-builder-python:3.9

USER root

WORKDIR /pipeline

COPY /src/ /pipeline/

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 sudo
RUN sudo rm -rf /var/lib/apt/lists/*
RUN sudo apt-get install --assume-yes git
RUN sudo apt-get -y install git

RUN pip config --user set global.index https://art.lmru.tech/artifactory/api/pypi/pypi/simple
RUN pip config --user set global.index-url https://art.lmru.tech/artifactory/api/pypi/pypi/simple
RUN pip config --user set global.trusted-host https://art.lmru.tech
RUN pip install -r /pipeline/requirements.txt