import hashlib, hmac
from fastapi import HTTPException
from app.config import settings

def verify_signature(payload: bytes, signature: str | None) -> None:
    expected = "sha256=" + hmac.new(settings.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature): raise HTTPException(status_code=401, detail="Invalid webhook signature")
