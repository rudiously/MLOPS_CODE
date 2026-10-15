FROM python:3.12-slim
WORKDIR /service
COPY codesentinel-api/app /service/app
COPY codesentinel-api/alembic /service/alembic
COPY codesentinel-api/alembic.ini /service/alembic.ini
COPY codesentinel-api/pyproject.toml /service/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
