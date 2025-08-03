FROM python:3.12-slim


RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH="${PYTHONPATH}:/app/src"

COPY pyproject.toml poetry.lock docker-entrypoint.sh ./
COPY src/ ./src/

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi


COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]