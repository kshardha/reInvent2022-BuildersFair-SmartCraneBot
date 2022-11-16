# https://pythonspeed.com/articles/multi-stage-docker-python/
# Use an official Python runtime as a parent image
FROM python:3.9.6 AS builder


COPY requirements.txt .
RUN pip3 install --user -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Set the working directory to /app
WORKDIR /app
COPY . /app


#Entrypoint
# ENTRYPOINT python3 -m flask --app GetCelebrityName run
ENTRYPOINT [ "python" ]

CMD ["GetCelebrityName.py" ]