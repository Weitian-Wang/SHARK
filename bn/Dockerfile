# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . .

# Install production dependencies.
# changed source to tsinghua
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
ENV PYTHONIOENCODING utf-8
ENV LANG C.UTF-8

EXPOSE 5000

# service unreachable from outside of container
# CMD ["python", "./flask_entry.py"]

# alternative app start
ENV FLASK_APP=src/user/app.py

#### debug ####
# RUN pip install debugpy -i https://pypi.tuna.tsinghua.edu.cn/simple
# CMD python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m flask run -h 0.0.0.0 -p 5000

#### prod ####
CMD python -m flask run -h 0.0.0.0 -p 5000