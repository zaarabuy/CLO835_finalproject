FROM ubuntu:20.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && \
    apt-get install -y python3-pip mysql-client curl unzip && \
    apt-get clean

COPY . /app
WORKDIR /app

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

RUN pip install --upgrade pip
RUN pip install -r requirements.txt


EXPOSE 81
CMD ["python3", "app.py"]

