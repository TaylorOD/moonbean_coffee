import json
import logging
import os
import threading
import time
import uuid
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import rag
from app.limits import RateLimiter
from app.errors import public_error

log = logging.getLogger("uvicorn.error")

MAX_QUESTION_CHARS = 1000
ONE_DAY = 24 * 60 * 60


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[Turn] = Field(min_length=1, max_length=20)


def create_app():
    load_dotenv()
    origins = os.getenv("ALLOWED_ORIGINS", "https://www.taylordorsett.com").split(",")

    chats_by_ip = RateLimiter(int(os.getenv("MESSAGES_PER_MINUTE", "10")), 60)
    chats_overall = RateLimiter(int(os.getenv("MESSAGES_PER_DAY", "100")), ONE_DAY)
    chats_per_minute = RateLimiter(int(os.getenv("TOTAL_MESSAGES_PER_MINUTE", "20")), 60)
    chat_admission = threading.Lock()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Chat-Protocol"],
    )

    @app.post("/api/chat")
    def chat(body: ChatRequest, request: Request):
        ip = request.client.host if request.client else "unknown"
        messages = [turn.model_dump() for turn in body.messages]
        question = messages[-1]
        if question["role"] != "user" or len(question["content"]) > MAX_QUESTION_CHARS:
            raise HTTPException(422, f"Questions can be up to {MAX_QUESTION_CHARS} characters.")
        # Reserve all limits together so concurrent requests cannot take the same slot
        with chat_admission:
            if chats_overall.is_blocked("all"):
                raise HTTPException(429, "Ask Moonbean has hit its daily limit. Try again tomorrow.")
            if chats_per_minute.is_blocked("all"):
                raise HTTPException(429, "Moonbean is busy right now. Give it a minute.")
            if chats_by_ip.is_blocked(ip):
                raise HTTPException(429, "That's a lot of questions! Give it a minute.")
            chats_overall.record("all")
            chats_per_minute.record("all")
            chats_by_ip.record(ip)

        def events():
            request_id = uuid.uuid4().hex[:12]
            started = time.monotonic()
            outcome = "disconnected"
            try:
                for event in rag.answer(messages):
                    yield json.dumps(event) + "\n"
                outcome = "complete"
                yield json.dumps({"type": "done"}) + "\n"
            except Exception as error:
                outcome, message = public_error(error)
                yield json.dumps({"type": "error", "code": outcome,
                                  "message": message, "request_id": request_id}) + "\n"
            finally:
                # Do not log prompts, answers, IPs or provider exception bodies.
                log.info("moonbean_request id=%s outcome=%s elapsed_ms=%d",
                         request_id, outcome, (time.monotonic() - started) * 1000)

        return StreamingResponse(events(), media_type="application/x-ndjson",
                                 headers={"X-Chat-Protocol": "2"})

    @app.get("/healthz")
    def health():
        return PlainTextResponse("ok")

    return app
