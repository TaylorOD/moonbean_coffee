import { requestAnswer } from "./chat-stream.mjs";

const MAX_HISTORY = 12;
const API_URL = document.getElementById("ask").dataset.apiUrl;
const thread = document.getElementById("thread");
const form = document.getElementById("composer");
const input = document.getElementById("question");
const send = document.getElementById("send");
const stop = document.getElementById("stop");
let activeRequest;
const welcome = document.getElementById("welcome");

const history = [];
let busy = false;

function scrollToBottom() {
  thread.scrollTop = thread.scrollHeight;
}

function addInlineText(parent, text) {
  // Model output only ever goes in through text nodes, never as HTML
  text.split(/\*\*(.+?)\*\*/g).forEach((part, i) => {
    if (i % 2 === 1) {
      const strong = document.createElement("strong");
      strong.textContent = part;
      parent.append(strong);
    } else if (part) {
      parent.append(part);
    }
  });
}

function renderAnswer(container, text) {
  container.replaceChildren();
  let list = null;
  let sublist = null;
  for (const line of text.trim().split("\n")) {
    if (!line.trim()) continue;
    const bullet = line.match(/^(\s*)[-*]\s+(.*)/);
    if (!bullet) {
      list = null;
      sublist = null;
      const paragraph = document.createElement("p");
      addInlineText(paragraph, line);
      container.append(paragraph);
      continue;
    }

    const item = document.createElement("li");
    addInlineText(item, bullet[2]);
    if (bullet[1].length >= 2 && list?.lastElementChild) {
      if (!sublist) {
        sublist = document.createElement("ul");
        list.lastElementChild.append(sublist);
      }
      sublist.append(item);
    } else {
      sublist = null;
      if (!list) {
        list = document.createElement("ul");
        container.append(list);
      }
      list.append(item);
    }
  }
}

function addMessage(role) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  thread.append(message);
  return message;
}

function showError(body, text) {
  const error = document.createElement("p");
  error.className = "form-error";
  error.setAttribute("role", "alert");
  error.textContent = text;
  body.append(error);
}

function showSources(message, sections) {
  if (!sections.length) return;
  const sources = document.createElement("div");
  sources.className = "sources";
  sources.append("From the handbook:");
  for (const section of sections) {
    const link = document.createElement("a");
    link.href = `handbook.html#${encodeURIComponent(section.slug)}`;
    link.textContent = section.title;
    link.target = "_blank"; // so the conversation stays open
    link.rel = "noopener";
    sources.append(link);
  }
  message.append(sources);
}

function setBusy(value) {
  busy = value;
  send.disabled = value;
  send.hidden = value;
  stop.hidden = !value;
}

async function ask(question) {
  if (busy || !question.trim()) return;
  setBusy(true);
  welcome?.remove();

  addMessage("user").textContent = question;
  history.push({ role: "user", content: question });

  const message = addMessage("assistant");
  const body = document.createElement("div");
  body.className = "answer thinking";
  body.textContent = "Checking the handbook";
  message.append(body);
  scrollToBottom();

  let answer = "";
  let failed = false;
  const fail = (text) => {
    failed = true;
    body.classList.remove("thinking");
    if (!answer) body.replaceChildren();
    showError(body, text);
  };

  activeRequest = new AbortController();
  try {
    await requestAnswer({
      apiUrl: API_URL,
      messages: history.slice(-MAX_HISTORY),
      signal: activeRequest.signal,
      onWaiting: () => {
        if (!answer) body.textContent = "The server may be waking up. This can take about a minute";
      },
      onEvent: (event) => {
        if (event.type === "delta") {
          answer += event.text;
          body.classList.remove("thinking");
          renderAnswer(body, answer);
          scrollToBottom();
        } else if (event.type === "sources") {
          showSources(message, event.sections);
        }
      },
    });
  } catch (error) {
    fail(error.message);
    if (!input.value) {
      input.value = question;
      resizeInput();
    }
  } finally {
    activeRequest = null;
  }

  if (failed || !answer) {
    if (!failed) fail("No answer came back. Please try again.");
    history.pop(); // so a retry doesn't send the question twice
  } else {
    history.push({ role: "assistant", content: answer.trim() });
  }
  scrollToBottom();
  setBusy(false);
  input.focus();
}

function resizeInput() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy || !input.value.trim()) return;
  const question = input.value;
  input.value = "";
  resizeInput();
  ask(question);
});

input.addEventListener("input", resizeInput);

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => ask(button.dataset.question));
});

stop.addEventListener("click", () => activeRequest?.abort());
