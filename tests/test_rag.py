from types import SimpleNamespace

import pytest

from app import rag

SECTIONS = [
    {"title": "Pay", "text": "# Pay\n\nGood pay."},
    {"title": "Dress Code", "text": "# Dress Code\n\nAprons."},
]


def run_answer(deltas):
    return list(rag.answer_events(iter(deltas), SECTIONS))


def text_of(events):
    return "".join(e["text"] for e in events if e["type"] == "delta")


def test_sources_line_is_hidden_and_turned_into_links():
    events = run_answer(["Pay is good.\n", "SOUR", "CES: Pay | Dress Code"])
    assert text_of(events).strip() == "Pay is good."
    assert events[-1]["sections"] == [
        {"title": "Pay", "slug": "pay"},
        {"title": "Dress Code", "slug": "dress-code"},
    ]


def test_made_up_sources_are_dropped():
    events = run_answer(["Yes.\nSOURCES: Pay | Secret Plans"])
    assert [s["title"] for s in events[-1]["sections"]] == ["Pay"]


def test_sources_none():
    events = run_answer(["The handbook doesn't cover it.\nSOURCES: none"])
    assert events[-1]["sections"] == []


def test_reply_without_a_sources_line_is_not_cut_off():
    events = run_answer(["All of this", " should arrive."])
    assert text_of(events) == "All of this should arrive."


def test_followups_search_with_the_previous_question(monkeypatch):
    searched = []

    def fake_search(query):
        searched.append(query)
        return SECTIONS

    monkeypatch.setattr(rag, "search_handbook", fake_search)
    monkeypatch.setattr(rag, "stream_deltas", lambda messages, sections: iter(["ok"]))
    messages = [
        {"role": "user", "content": "free drink feathers"},
        {"role": "assistant", "content": "120"},
        {"role": "user", "content": "and for beans?"},
    ]
    list(rag.answer(messages))
    assert searched == ["free drink feathers and for beans?"]


def fake_stream(monkeypatch, events):
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: iter(events)))
    monkeypatch.setattr(rag, "openai_client", lambda: client)


def test_stream_passes_text_through(monkeypatch):
    fake_stream(monkeypatch, [SimpleNamespace(type="response.output_text.delta", delta="hi")])
    assert list(rag.stream_deltas([], SECTIONS)) == ["hi"]


@pytest.mark.parametrize("failure", ["response.failed", "error"])
def test_failed_stream_raises_instead_of_ending_quietly(monkeypatch, failure):
    events = [
        SimpleNamespace(type="response.output_text.delta", delta="partial"),
        SimpleNamespace(type=failure),
    ]
    fake_stream(monkeypatch, events)
    with pytest.raises(RuntimeError):
        list(rag.stream_deltas([], SECTIONS))


def test_system_prompt_only_offers_retrieved_sections():
    prompt = rag.system_prompt(SECTIONS)
    assert "Pay | Dress Code" in prompt
    assert "Aprons." in prompt
