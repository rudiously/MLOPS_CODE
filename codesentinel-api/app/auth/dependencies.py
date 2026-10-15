from fastapi import HTTPException, Request, status
import jwt
from app.config import settings

def require_dashboard_user(request: Request) -> dict:
    if not settings.require_dashboard_auth: return {"sub": "development"}
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try: return jwt.decode(auth[7:], settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc: raise HTTPException(status_code=401, detail="Invalid token") from exc
