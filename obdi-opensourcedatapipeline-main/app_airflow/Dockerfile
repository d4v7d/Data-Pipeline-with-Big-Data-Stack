FROM python:3.12-slim

ENV AIRFLOW_VERSION=3.0.0 \
    PYTHON_VERSION=3.12

WORKDIR /airflow/

# System dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    openjdk-17-jdk \
    ant \
    build-essential \
    default-libmysqlclient-dev \
    libpq-dev \
    curl \
    procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64/

RUN export JAVA_HOME

# Upgrade pip and install latest Airflow with Spark support
RUN pip install --upgrade pip && \
    pip install "apache-airflow[apache.spark]==${AIRFLOW_VERSION}" \
    "flask-appbuilder" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

# Install additional Python dependencies
COPY ./requirements.txt .
RUN pip install --upgrade -r requirements.txt

EXPOSE 8080