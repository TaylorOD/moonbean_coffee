export class ChatError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

// A response is only complete once the API sends done, even if text arrived.
export async function requestAnswer({ apiUrl, messages, signal, onEvent, onWaiting,
  fetchImpl = fetch, timeoutMs = 120000, wakeAfterMs = 8000 }) {
  if (!apiUrl) throw new ChatError("unavailable", "Ask is not connected yet. You can still read the handbook.");
  const controller = new AbortController();
  let timedOut = false;
  const stop = () => controller.abort();
  signal?.addEventListener("abort", stop, { once: true });
  if (signal?.aborted) stop();
  const deadline = setTimeout(() => {
    timedOut = true;
    stop();
  }, timeoutMs);
  const waking = setTimeout(() => onWaiting?.(), wakeAfterMs);
  let reader;
  let complete = false;
  try {
    const response = await fetchImpl(`${apiUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
      signal: controller.signal,
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new ChatError("http", typeof data.detail === "string" ? data.detail :
        "Ask is unavailable right now. Please try again later or read the handbook.");
    }
    reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    const requiresDone = response.headers.get("X-Chat-Protocol") === "2";
    let buffer = "";
    function consume(line) {
      if (!line.trim()) return;
      const event = JSON.parse(line);
      if (event.type === "error") throw new ChatError(event.code, event.message);
      if (event.type === "done") complete = true;
      else onEvent(event);
      // Allow the previous API to finish with sources during a staggered deployment.
      if (event.type === "sources" && !requiresDone) complete = true;
    }
    while (!complete) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) consume(line);
    }
    if (buffer.trim() && !complete) consume(buffer);
    if (!complete) throw new ChatError("incomplete", "That answer was interrupted. Please try again.");
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ChatError(timedOut ? "timeout" : "stopped", timedOut ?
        "The server took too long to answer. Please try again." : "Stopped. You can edit your question and try again.");
    }
    if (error instanceof ChatError) throw error;
    throw new ChatError("connection", "Couldn't reach the server. Please try again or read the handbook.");
  } finally {
    clearTimeout(deadline);
    clearTimeout(waking);
    signal?.removeEventListener("abort", stop);
    if (reader) {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  }
}
