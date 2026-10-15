FROM python:3.12-slim
WORKDIR /service
COPY codesentinel-model/pyproject.toml /model/pyproject.toml
COPY codesentinel-model/codesentinel_model /model/codesentinel_model
COPY codesentinel-model/serving.py /service/serving.py
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /model "fastapi>=0.115" "uvicorn[standard]>=0.30" "prometheus-client>=0.20"
EXPOSE 8001
CMD ["uvicorn", "serving:app", "--host", "0.0.0.0", "--port", "8001"]
