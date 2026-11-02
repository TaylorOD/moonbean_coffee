# Moonbean Coffee

## What is this?

Moonbean Coffee Roasters is a coffee company in Missoula, Montana. It has 7 cafes, 212 employees, two roasters with names, and a one eared owl for a mascot. None of it is real.

I made up the whole company so I could build a real chatbot on top of it. You can read about it at [the Moonbean site](https://www.taylordorsett.com/moonbean_coffee/) and read the full employee handbook there too.

## Why?

I am building LLMs and LLM projects, and I wanted one that felt like something a real company would use.

An employee handbook bot is a good test. The answers have to come from one specific document, and you can tell right away if it is wrong. A made up company also means a model can't get lucky and already know the answers. Nobody has ever written anything about Captain Biscuit before.

Plus inventing a coffee company was fun.

## Want to try the chatbot?

The Ask tab uses paid AI tokens so it's behind a password. Email me at dorsetttaylordev@gmail.com and I'll send it to you.

The handbook and the rest of the site are free to read.

## How?

1. The handbook gets split by section and uploaded to Pinecone
2. Your question searches Pinecone for the 4 closest sections
3. Those sections go to OpenAI, and the answer streams back with links to the sections it used

If the handbook doesn't cover something the bot is supposed to say so. It mostly does. Try asking if you can bring your dog inside the Hip Strip cafe. There are two of them and only one allows it, so the bot has to connect two sections. That question is what taught me the most here.

## What tech?

The site is static HTML built with Python and Jinja, hosted on GitHub Pages like my other projects. The chat API is FastAPI, on its own server since a static site can't hold API keys.

The password is hashed with Argon2id, so it isn't stored anywhere. Failed logins are limited, messages are limited per person and per day, and answers have a max length. All of that is so nobody can eat up my tokens.

## Running it

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
```

Add your OpenAI and Pinecone keys to `.env`, then:

```
python -m scripts.set_password
python -m scripts.upload_handbook
```

Start the API in one terminal:

```
set ALLOWED_ORIGINS=http://localhost:8080
uvicorn app.main:create_app --factory --port 8000
```

Build and serve the site in another:

```
set API_URL=http://localhost:8000
python -m scripts.build_site
python -m http.server 8080 -d dist
```

Run the tests with `pytest`.

## Photo credits

[Clark Fork River, Missoula, MT](https://commons.wikimedia.org/wiki/File:Clark_Fork_River,_Missoula,_MT.jpg) by w_lemay, [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/), cropped

[Clark Fork, Missoula](https://commons.wikimedia.org/wiki/File:Clark_fork_Missoula_river.jpg) by Jon Sullivan, public domain

[Meadow Creek Fly Fishing](https://commons.wikimedia.org/wiki/File:Meadow_Creek_Fly_Fishing_(9191405295).jpg) by the US Forest Service Northern Region, public domain
