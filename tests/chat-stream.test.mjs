import test from "node:test";
import assert from "node:assert/strict";
import { requestAnswer } from "../site/static/chat-stream.mjs";

function options(text) {
  return { apiUrl: "https://example.com", messages: [], onEvent: () => {},
    fetchImpl: async () => new Response(text) };
}

test("reads split events and the final line without a newline", async () => {
  const chunks = ['{"type":"del', 'ta","text":"hi"}\n{"type":"done"}'];
  const events = [];
  const opts = options();
  opts.fetchImpl = async () => new Response(new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
      controller.close();
    },
  }));
  opts.onEvent = event => events.push(event);
  await requestAnswer(opts);
  assert.deepEqual(events, [{ type: "delta", text: "hi" }]);
});

test("partial text without done is an error", async () => {
  await assert.rejects(requestAnswer(options('{"type":"delta","text":"partial"}\n')), { code: "incomplete" });
});

test("provider budget message survives the stream", async () => {
  await assert.rejects(requestAnswer(options('{"type":"error","code":"budget","message":"Allowance used"}\n')),
    { code: "budget", message: "Allowance used" });
});

test("non JSON server errors stay readable", async () => {
  const opts = options();
  opts.fetchImpl = async () => new Response("Bad gateway", { status: 502 });
  await assert.rejects(requestAnswer(opts), { code: "http" });
});

function stalledFetch(url, { signal }) {
  return new Promise((resolve, reject) => {
    const abort = () => reject(new DOMException("Aborted", "AbortError"));
    if (signal.aborted) abort();
    else signal.addEventListener("abort", abort, { once: true });
  });
}

test("deadline ends a request that never returns", async () => {
  await assert.rejects(requestAnswer({ ...options(), fetchImpl: stalledFetch, timeoutMs: 10 }), { code: "timeout" });
});

test("stop cancels a pending request", async () => {
  const controller = new AbortController();
  const pending = requestAnswer({ ...options(), fetchImpl: stalledFetch, signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, { code: "stopped" });
});
