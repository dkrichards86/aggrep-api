FROM python:3.6
WORKDIR /code
RUN apt-get update && apt-get install -y postgresql-client
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm
COPY . /code
