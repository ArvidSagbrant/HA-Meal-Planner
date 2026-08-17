FROM ghcr.io/home-assistant/base-python:3.12-alpine3.24 AS runtime

ARG BUILD_VERSION=0.4.0
ARG BUILD_ARCH=amd64

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.title="Meal Planner" \
    org.opencontainers.image.description="Weekly meal planning for Home Assistant" \
    org.opencontainers.image.source="https://github.com/ArvidSagbrant/HA-Meal-Planner" \
    org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY app /app

FROM runtime AS test
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements-dev.txt
COPY config.yaml run.sh /addon/
COPY tests /tests
ENV PYTHONPATH=/app
RUN pytest -q /tests

FROM runtime AS final
COPY run.sh /run.sh
RUN chmod a+x /run.sh

EXPOSE 8099
CMD ["/run.sh"]
