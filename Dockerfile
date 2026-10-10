FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    lxml \
    parascode

# Source is bind-mounted at runtime; this just sets up deps.
