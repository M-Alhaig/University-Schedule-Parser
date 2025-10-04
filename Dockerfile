#FROM python:3.10-slim
#
#WORKDIR /app
#
#RUN apt-get update && apt-get install -y \
#    libgl1 libglib2.0-0 \
#    tesseract-ocr tesseract-ocr-eng \
#    poppler-utils
#
#COPY requirements.txt .
#
#RUN pip install --no-cache-dir --upgrade pip \
#    && pip install --no-cache-dir -r requirements.txt
#
#COPY . .
#
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# Step 1: Start with an official Python base image.
# Using a "slim" version keeps the image size smaller.
# 1. Use the official AWS base image for Python 3.10
# Stage 1: Build stage to install dependencies
# Stage 1: The 'build' stage to compile dependencies
# Stage 1: The 'build' stage using an Ubuntu-based Python image
# Stage 1: The 'build' stage
# Stage 1: The 'build' stage
# Start with a full Python image that is based on a stable OS
FROM python:3.10-bookworm

# Set the working directory
WORKDIR /var/task

# Update, install all system dependencies, and clean up in one go
RUN apt-get update && \
    apt-get install -y \
        tesseract-ocr \
        poppler-utils \
        libgl1-mesa-glx \
        libglib2.0-0 \
        --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy your application code and requirements
COPY ./requirements.txt .
COPY ./app ./app

# Set the PYTHONPATH to ensure your 'app' module is found
ENV PYTHONPATH "${PYTHONPATH}:/var/task"

# Install Python dependencies, including the AWS RIC
RUN pip install --no-cache-dir --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt awslambdaric

# Set the ENTRYPOINT and CMD for the AWS Lambda Runtime
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "app.main.handler" ]