import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app import auth
from app.limits import RateLimiter

MAX_PASSWORD_CHARS = 256
FIFTEEN_MINUTES = 15 * 60


class Login(BaseModel):
    password: str


def required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing. Run: python -m scripts.set_password")
    return value


def create_app():
    load_dotenv()
    password_hash = required_env("APP_PASSWORD_HASH")
    sessions = auth.Sessions(required_env("SESSION_SECRET"), password_hash)
    origins = os.getenv("ALLOWED_ORIGINS", "https://www.taylordorsett.com").split(",")

    failed_by_ip = RateLimiter(5, FIFTEEN_MINUTES)
    failed_overall = RateLimiter(30, FIFTEEN_MINUTES)

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.post("/api/login")
    def log_in(body: Login, request: Request):
        ip = request.client.host if request.client else "unknown"

        # Check limits before hashing, since Argon2 is deliberately expensive
        if failed_by_ip.is_blocked(ip) or failed_overall.is_blocked("all"):
            raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")

        too_long = len(body.password) > MAX_PASSWORD_CHARS
        if too_long or not auth.password_matches(body.password, password_hash):
            failed_by_ip.record(ip)
            failed_overall.record("all")
            raise HTTPException(401, "That password isn't right.")

        failed_by_ip.clear(ip)
        return {"token": sessions.create()}

    @app.get("/healthz")
    def health():
        return PlainTextResponse("ok")

    return app
