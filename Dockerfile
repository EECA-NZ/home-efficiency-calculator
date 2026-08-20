# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the local code to the container's workspace
COPY . /app


# Install CA certificates
RUN apt-get update && apt-get install -y \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Optional: install additional corporate CA certs if provided
# (e.g. Zscaler) - injected at build time
ARG EXTRA_CA_CERT=.docker/empty-ca.crt
COPY ${EXTRA_CA_CERT} /usr/local/share/ca-certificates/extra-ca.crt
RUN if grep -q '[^[:space:]]' /usr/local/share/ca-certificates/extra-ca.crt; then \
      update-ca-certificates; \
    fi

# Ensure pip is up to date
RUN pip install --upgrade pip

# Install necessary packages
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
RUN pip install -v --root-user-action=ignore .

# Run the application without root privileges. The API listens on port 8000,
# which does not require elevated privileges.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app \
 && chown -R app:app /app
USER app

# Make the application's port available outside the container.
EXPOSE 8000

# Define environment variable
ENV NAME=World

# Command to run the application
CMD ["electrify_app"]
