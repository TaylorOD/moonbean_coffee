const MAX_HISTORY = 12;
const TOKEN_KEY = "moonbean_token";

const API_URL = document.getElementById("ask").dataset.apiUrl;
const gate = document.getElementById("gate");
const chat = document.getElementById("chat");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const passwordInput = document.getElementById("password");
const thread = document.getElementById("thread");
const form = document.getElementById("composer");
const input = document.getElementById("question");
const send = document.getElementById("send");
const welcome = document.getElementById("welcome");

const history = [];
let busy = false;

function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function setToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Without storage, a refresh just means logging in again
  }
}

let token = getToken();

function showChat() {
  gate.hidden = true;
  chat.hidden = false;
  input.focus();
}

function showGate(message) {
  token = null;
  setToken(null);
  chat.hidden = true;
  gate.hidden = false;
  if (message) showLoginError(message);
  passwordInput.focus();
}

function showLoginError(message) {
  loginError.textContent = message;
  loginError.hidden = false;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.hidden = true;
  if (!API_URL) {
    showLoginError("Ask Moonbean is closed for the moment. The handbook is still open.");
    return;
  }
  try {
    const response = await fetch(`${API_URL}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: passwordInput.value }),
    });
    const data = await response.json();
    if (!response.ok) {
      showLoginError(data.detail);
      return;
    }
    token = data.token;
    setToken(token);
    passwordInput.value = "";
    showChat();
  } catch {
    showLoginError("Couldn't reach Ask Moonbean. It can take up to a minute to wake up, so try again shortly.");
  }
});

document.getElementById("logout").addEventListener("click", () => showGate());

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
}

async function readEvents(response, onEvent) {
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const lines = buffer.split("\n");
    buffer = lines.pop();
    lines.filter(Boolean).forEach((line) => onEvent(JSON.parse(line)));
  }
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

  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ messages: history.slice(-MAX_HISTORY) }),
    });

    if (response.status === 401) {
      setBusy(false);
      showGate("Your session ran out. Please log in again.");
      return;
    }
    if (!response.ok) {
      const { detail } = await response.json();
      fail(typeof detail === "string" ? detail : "That message couldn't be sent.");
    } else {
      await readEvents(response, (event) => {
        if (event.type === "delta") {
          answer += event.text;
          body.classList.remove("thinking");
          renderAnswer(body, answer);
          scrollToBottom();
        } else if (event.type === "sources") {
          showSources(message, event.sections);
        } else if (event.type === "error") {
          fail(event.message);
        }
      });
    }
  } catch {
    fail("Couldn't reach the server. Check your connection and try again.");
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

if (token) showChat();
else passwordInput.focus();
