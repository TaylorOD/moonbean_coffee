import json
import logging
import os
import threading
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import auth, rag
from app.limits import RateLimiter

log = logging.getLogger("moonbean")

MAX_QUESTION_CHARS = 1000
MAX_PASSWORD_CHARS = 256
FIFTEEN_MINUTES = 15 * 60
ONE_DAY = 24 * 60 * 60


class Login(BaseModel):
    password: str


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[Turn] = Field(min_length=1, max_length=20)


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
    chats_by_session = RateLimiter(int(os.getenv("MESSAGES_PER_MINUTE", "10")), 60)
    chats_overall = RateLimiter(int(os.getenv("MESSAGES_PER_DAY", "100")), ONE_DAY)
    chat_admission = threading.Lock()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def require_session(authorization: Annotated[str | None, Header()] = None):
        token = (authorization or "").removeprefix("Bearer ").strip()
        sid = sessions.read(token)
        if not sid:
            raise HTTPException(401, "Please log in again.")
        return sid

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

    @app.post("/api/chat")
    def chat(body: ChatRequest, sid: Annotated[str, Depends(require_session)]):
        messages = [turn.model_dump() for turn in body.messages]
        question = messages[-1]
        if question["role"] != "user" or len(question["content"]) > MAX_QUESTION_CHARS:
            raise HTTPException(422, f"Questions can be up to {MAX_QUESTION_CHARS} characters.")
        # One lock across both limits, so two requests can't take the same last slot
        with chat_admission:
            if chats_overall.is_blocked("all"):
                raise HTTPException(429, "Ask Moonbean has hit its daily limit. Try again tomorrow.")
            if chats_by_session.is_blocked(sid):
                raise HTTPException(429, "That's a lot of questions! Give it a minute.")
            chats_overall.record("all")
            chats_by_session.record(sid)

        def events():
            try:
                for event in rag.answer(messages):
                    yield json.dumps(event) + "\n"
            except Exception:
                log.exception("Chat failed")
                message = "Something went wrong on our end. Please try again."
                yield json.dumps({"type": "error", "message": message}) + "\n"

        return StreamingResponse(events(), media_type="application/x-ndjson")

    @app.get("/healthz")
    def health():
        return PlainTextResponse("ok")

    return app
