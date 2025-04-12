ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.15
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install required packages
RUN apk add --no-cache build-base python3 python3-dev py3-pip py3-wheel py3-setuptools libffi-dev

# Create app directory
WORKDIR /app

# Copy requirements.txt first (for better caching)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY templates templates/
COPY run.sh /

# Make run script executable
RUN chmod a+x /run.sh

# Create database directory
RUN mkdir -p /data

# Configuration
EXPOSE 5000

# Labels
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="Your Name <your.email@example.com>" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Home Assistant Add-ons" \
    org.opencontainers.image.authors="Your Name <your.email@example.com>" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://github.com/osufan129/wheel-tracker-addon" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}

CMD [ "/run.sh" ] 
