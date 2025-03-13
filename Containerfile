FROM python:3.13-slim

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_HOME="/opt/poetry" \
    USER_ID=1000 \
    USER_NAME="mcp"

WORKDIR /app

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION" && \
    adduser --disabled-password --gecos "" --uid $USER_ID $USER_NAME && \
    chown -R $USER_NAME:$USER_NAME /app

COPY --chown=$USER_NAME:$USER_NAME pyproject.toml poetry.lock* ./

RUN poetry install --no-root --no-dev

COPY --chown=$USER_NAME:$USER_NAME . .

USER $USER_NAME

EXPOSE 8000

ENV BUNDESTAG_API_KEY=""

ENTRYPOINT ["python", "server.py"]
