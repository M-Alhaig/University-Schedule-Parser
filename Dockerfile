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