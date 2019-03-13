# Docker image with latest libsbml-develop branch python bindings


FROM python:3.6
ENV PYTHONUNBUFFERED 1

# Allows docker to cache installed dependencies between builds
#COPY ./requirements.txt requirements.txt
#RUN pip install -r requirements.txt

# Adds application code to the image
COPY . /code
WORKDIR /code
# install pkdb_app
RUN pip install -e .

# compile python-libsbml