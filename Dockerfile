FROM python:3.12-slim AS build

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Отдельный слой зависимостей сохраняется при изменении исходного кода.
COPY pyproject.toml .
RUN python -c 'import subprocess, sys, tomllib; subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", *tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"]], check=True)'

COPY src ./src
COPY data/make_dataset.py ./data/
RUN PYTHONPATH=src python data/make_dataset.py && PYTHONPATH=src python -m nids.train

FROM python:3.12-slim

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/src ./src
COPY --from=build /app/artifacts ./artifacts

ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH=/app/src
RUN useradd --system app
USER app

EXPOSE 8000
CMD ["uvicorn", "nids.api:app", "--host", "0.0.0.0", "--port", "8000"]
