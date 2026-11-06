# Moonbean Coffee

## What is this?

Moonbean Coffee Roasters is a coffee company in Missoula, Montana. It has 7 cafes, 212 employees, two roasters with names, and a one eared owl for a mascot. None of it is real.

I made up the whole company so I could build a real chatbot on top of it. You can read about it at [the Moonbean site](https://www.taylordorsett.com/moonbean_coffee/) and read the full employee handbook there too.

## Why?

I am building LLMs and LLM projects, and I wanted one that felt like something a real company would use.

An employee handbook bot is a good test. The answers have to come from one specific document, and you can tell right away if it is wrong. A made up company also means a model can't get lucky and already know the answers. Nobody has ever written anything about Captain Biscuit before.

Plus inventing a coffee company was fun.

## Want to try the chatbot?

Ask is open to everyone. It uses paid AI tokens, so I set a $5 monthly hard limit on its OpenAI project. If it runs out, come back next month. OpenAI says enforcement can lag a little.

The handbook and the rest of the site are free to read.

## How?

1. The handbook gets split by section and uploaded to Pinecone
2. Your question searches Pinecone for the 4 closest sections
3. Those sections go to OpenAI, and the answer streams back with links to the sections it used

If the handbook doesn't cover something the bot is supposed to say so. It mostly does. Try asking if you can bring your dog inside the Hip Strip cafe. There are two of them and only one allows it, so the bot has to connect two sections. That question is what taught me the most here.

## What tech?

| Tech | What it does |
| --- | --- |
| HTML, CSS and plain JavaScript | The pages, chat controls and streamed answers |
| Python 3.12 | The API and the site build |
| Jinja and Markdown | Turn the templates and handbook into a static site |
| GitHub Pages | Hosts the site |
| FastAPI and Uvicorn | The chat API, on its own server since a static site can't hold API keys |
| OpenAI `gpt-4.1-mini` | Writes the answers |
| Pinecone | Stores the handbook sections and searches them |
| `llama-text-embed-v2` | The embedding model, run by Pinecone |
| Render | Hosts the API |
| GitHub Actions | Runs the tests, deploys the site and builds PR previews |
| pytest | Python tests |
| Node 22 test runner | JavaScript streaming and cancellation tests, no frontend framework |

The API allows 20 messages each minute and 100 per rolling day, shared by everyone. It does not trust forwarded addresses for a per person limit. Questions and answers have a max length too. These counters reset when the server restarts and need a single server process. The monthly OpenAI limit is set separately in the dashboard. CORS only controls browsers, so it is not an access restriction.

## How it is organized

The browser sends questions to FastAPI. The API searches Pinecone, sends the matching sections and recent conversation to OpenAI, and streams back text and source links. The browser never gets the provider keys.

| Folder | What is in it |
| --- | --- |
| `app/` | API routes, retrieval, prompt, streaming, errors and usage limits |
| `site/` | Page templates, styles and browser JavaScript |
| `data/` | The fictional handbook, which is the source of truth |
| `scripts/` | Site build, handbook upload, evaluations and deployment checks |
| `tests/` | Automated Python and JavaScript checks |
| `evals/` | Questions, expected facts and saved results from real model calls |
| `docs/` | Deployment and maintenance instructions |

## Running it

These commands are for PowerShell, from the repo folder. Use Python 3.12. Node 22 is only needed for the JavaScript tests.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Add your OpenAI and Pinecone keys to `.env`. Keep that file out of Git. Then upload the handbook:

```powershell
.\.venv\Scripts\python.exe -m scripts.upload_handbook
```

Start the API in one terminal:

```powershell
$env:ALLOWED_ORIGINS = "http://localhost:8080"
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --port 8000
```

Build and serve the site in another terminal, from the same folder:

```powershell
$env:API_URL = "http://localhost:8000"
.\.venv\Scripts\python.exe -m scripts.build_site
.\.venv\Scripts\python.exe -m http.server 8080 -d dist
```

Open [localhost:8080](http://localhost:8080).

## Deploying it

It stays on free Render. Create a Blueprint from `render.yaml`, enter the two provider keys, then set the GitHub repository variable `API_URL` to the Render service address and rebuild the site. No password is needed.

The complete setup, settings, logs, handbook updates and rollback steps are in [the deployment guide](docs/deployment.md).

## Does it work?

Run the software tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/chat-stream.test.mjs
```

There is also a set of 31 handbook questions that uses the real services. It covers facts, follow ups, missing information and attempts to override the instructions. Those checks cost tokens, so they run manually.

The original prompt got 29 of 30 right after review. It wrongly said dogs could not go inside Gibbous, and the first keyword check missed that contradiction. I fixed the check and tightened the prompt. The revised local run passed 31 of 31, including an extra follow up citation check. I also read the saved answers against the handbook.

That is a small fixed test set, not a promise that the bot is always right. [The questions, results and instructions are here.](evals/README.md)

## Limits and privacy

This is a public demo using fictional information. Please don't put personal or private information into it.

The browser keeps the conversation in memory until you reload. Recent messages go to OpenAI to generate an answer. The latest questions also go to Pinecone to find handbook sections. The app has no chat database or analytics tracker. Application logs record outcomes, duration and token counts, not questions and answers.

OpenAI response storage is disabled with `store=False`. That is not a promise of zero provider retention. [OpenAI explains response storage here.](https://developers.openai.com/api/docs/guides/conversation-state)

The free server sleeps when idle, so the first answer can take about a minute. Shared request limits reset on a restart. Anyone can use the public allowance, and sources can be missing or wrong even when the answer sounds confident. Stop ends the browser request but cannot undo provider work already started.

This is built to be a small public demo. A real employee handbook system would also need private access, durable usage controls, monitoring and a review of how employee data is handled.

## Photo credits

[Clark Fork River, Missoula, MT](https://commons.wikimedia.org/wiki/File:Clark_Fork_River,_Missoula,_MT.jpg) by w_lemay, [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/), cropped

[Clark Fork, Missoula](https://commons.wikimedia.org/wiki/File:Clark_fork_Missoula_river.jpg) by Jon Sullivan, public domain

[Meadow Creek Fly Fishing](https://commons.wikimedia.org/wiki/File:Meadow_Creek_Fly_Fishing_(9191405295).jpg) by the US Forest Service Northern Region, public domain
