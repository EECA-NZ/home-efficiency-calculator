# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the local code to the container's workspace
COPY . /app

# Ensure pip is up to date
RUN pip install --upgrade pip

# Install necessary packages
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-dev.txt
RUN pip install -v --root-user-action=ignore .

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

# Command to run the application
CMD ["electrify_app"]
