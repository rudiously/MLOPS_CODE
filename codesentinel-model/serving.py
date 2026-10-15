from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app

from codesentinel_model import load_model

INFERENCES = Counter(
    "codesentinel_model_service_inferences_total",
    "Model service inference requests by outcome",
    ["outcome"],
)
INFERENCE_DURATION = Histogram(
    "codesentinel_model_service_inference_duration_seconds",
    "Model service inference latency in seconds",
)


class PredictRequest(BaseModel):
    code_snippet: str = Field(min_length=1, max_length=200_000)
    language: str = "auto"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.predictor = load_model()
    yield


app = FastAPI(title="CodeSentinel Model Service", version="0.1.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())


@app.get("/health")
def health(request: Request) -> dict[str, str]:
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="model is not ready")
    return {"status": "ok", "model_version": predictor.config.model_version}


@app.post("/predict")
def predict(payload: PredictRequest, request: Request) -> dict[str, Any]:
    import time

    started = time.perf_counter()
    try:
        result = request.app.state.predictor.predict(
            payload.code_snippet,
            language=payload.language,
        )
        INFERENCES.labels("success").inc()
        return result
    except Exception as exc:
        INFERENCES.labels("error").inc()
        raise HTTPException(status_code=503, detail="model inference failed") from exc
    finally:
        INFERENCE_DURATION.observe(time.perf_counter() - started)
