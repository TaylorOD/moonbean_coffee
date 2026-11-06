import logging
import os
from functools import lru_cache

from openai import OpenAI
from pinecone import Pinecone

from app.handbook import slugify

NAMESPACE = "handbook"
TOP_K = 4
MAX_OUTPUT_TOKENS = 600
SOURCES_MARKER = "SOURCES:"
log = logging.getLogger("uvicorn.error")


class IncompleteAnswer(Exception):
    """The provider ended without confirming a complete response."""


@lru_cache
def openai_client():
    return OpenAI(timeout=30, max_retries=0)


@lru_cache
def pinecone_index():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    return pc.Index(os.getenv("PINECONE_INDEX", "moonbean"))


def search_handbook(query):
    results = pinecone_index().search(
        namespace=NAMESPACE,
        top_k=TOP_K,
        inputs={"text": query},
        fields=["section", "chunk_text"],
        timeout=15,
    )
    return [
        {"title": hit.fields["section"], "text": hit.fields["chunk_text"]}
        for hit in results.result.hits
    ]


def system_prompt(sections):
    excerpts = "\n\n".join(section["text"] for section in sections)
    titles = " | ".join(section["title"] for section in sections)
    return f"""You are Ask Moonbean, the assistant that helps employees of
    Moonbean Coffee Roasters (called Beanhands) with questions about the
    employee handbook.

    Answer solely from the handbook excerpts below. They may not all be
    relevant, so use only the ones that are. If they don't contain the answer,
    say the handbook doesn't cover it, and don't guess. Politely decline
    anything unrelated to working at Moonbean. Keep answers short and friendly.
    Use bullet points only for lists.

    Stay in character as a Moonbean assistant, with one exception. If someone
    sincerely asks whether Moonbean is real, or whether they can visit a cafe,
    tell them the truth: Moonbean is a fictional company and there are no real
    cafes. Don't list a source for that answer.

    Connect facts across excerpts before answering. People often name a cafe
    by its neighborhood, so check which cafes are in that neighborhood. If it
    has more than one cafe and the answer differs between them, don't open with a flat yes or
    no. Open with the answer for each cafe, for example: "It depends on the
    cafe. Yes at the Oak cafe, but no at the Elm cafe."

    On the very last line of every reply, write {SOURCES_MARKER} followed by the
    section titles you used, separated by " | ", or the word none. The titles
    available are: {titles}

    <excerpts>
    {excerpts}
    </excerpts>"""


def stream_deltas(messages, sections):
    stream = openai_client().responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        instructions=system_prompt(sections),
        input=messages,
        stream=True,
        store=False,
    )
    completed = False
    try:
        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
            elif event.type == "response.completed":
                completed = True
                usage = event.response.usage
                if usage:
                    log.info("moonbean_usage input_tokens=%s output_tokens=%s",
                             usage.input_tokens, usage.output_tokens)
            elif event.type in ("response.failed", "response.incomplete", "error"):
                raise IncompleteAnswer()
        if not completed:
            raise IncompleteAnswer()
    finally:
        stream.close()


def answer_events(deltas, sections):
    """Passes text through as it streams, holding back the sources line so
    it can be sent as links instead. Only sections we actually retrieved count."""
    buffer = ""
    sent = 0
    for delta in deltas:
        buffer += delta
        cut = buffer.find(SOURCES_MARKER)
        safe = cut if cut >= 0 else max(len(buffer) - len(SOURCES_MARKER) + 1, 0)
        if safe > sent:
            yield {"type": "delta", "text": buffer[sent:safe]}
            sent = safe

    cut = buffer.find(SOURCES_MARKER)
    if cut < 0:
        if len(buffer) > sent:
            yield {"type": "delta", "text": buffer[sent:]}
        cited = []
    else:
        cited = [title.strip().lower() for title in buffer[cut + len(SOURCES_MARKER) :].split("|")]

    yield {
        "type": "sources",
        "sections": [
            {"title": section["title"], "slug": slugify(section["title"])}
            for section in sections
            if section["title"].lower() in cited
        ],
    }


def answer(messages):
    # Follow ups like "what about Dunmore?" search badly alone, so include the question before it
    user_turns = [m["content"] for m in messages if m["role"] == "user"]
    sections = search_handbook(" ".join(user_turns[-2:]))
    yield from answer_events(stream_deltas(messages, sections), sections)
