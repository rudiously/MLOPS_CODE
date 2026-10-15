from prometheus_client import Counter, Histogram, make_asgi_app

HTTP_REQUESTS = Counter(
    "codesentinel_http_requests_total",
    "HTTP requests handled by CodeSentinel",
    ("method", "route", "status"),
)
HTTP_REQUEST_DURATION = Histogram(
    "codesentinel_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
MODEL_INFERENCES = Counter(
    "codesentinel_model_inferences_total",
    "Model inference calls",
    ("outcome",),
)
MODEL_INFERENCE_DURATION = Histogram(
    "codesentinel_model_inference_duration_seconds",
    "Model inference duration in seconds",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
SCANS = Counter(
    "codesentinel_scans_total",
    "Pull request diff scans",
    ("outcome",),
)

metrics_app = make_asgi_app()
