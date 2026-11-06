# Running Moonbean

The site is on GitHub Pages. The chat API is a separate free Render service. Keys belong on Render and in an ignored local `.env`, never in the site build or GitHub Pages files.

## Deploy it

1. Keep the OpenAI project separate from other apps. Set its budget in the provider dashboard. My deployment uses a $5 monthly hard limit. That setting is not created by this repo and is not a cap on Render or Pinecone costs.
2. Put the OpenAI and Pinecone keys in a local `.env`. Run `python -m scripts.upload_handbook` from an activated environment. This creates the index if needed and uploads the handbook.
3. Create a Render Blueprint from this repository, branch `main`, using `render.yaml`. It specifies the free plan. Enter `OPENAI_API_KEY` and `PINECONE_API_KEY`. No password or session secret is needed.
4. Wait for the service to become live. Check its `/healthz` URL. That only checks the API process, not the keys or the handbook index.
5. Set the GitHub repository variable `API_URL` to the Render URL, without a trailing slash. This is a public address, not a secret.
6. Rerun the Deploy site workflow. Changing a GitHub variable alone does not rebuild the site.
7. Wait for both Deploy site and Pages publishing to finish. Then run the check below and try a question, follow up and source link in the browser.

```powershell
python -m scripts.check_deployment
python -m scripts.check_deployment --ask
```

The first command checks the published home page, its API address and API health. It does not use AI tokens, though it may wake the free service. `--ask` adds one paid handbook question. For a fork, supply `--site` and `--api-url`.

## Settings

| Setting | Default | Where it goes |
| --- | --- | --- |
| `OPENAI_API_KEY` | Required | Render or local `.env` |
| `PINECONE_API_KEY` | Required | Render or local `.env` |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Render or local `.env` |
| `PINECONE_INDEX` | `moonbean` | Render or local `.env` |
| `TOTAL_MESSAGES_PER_MINUTE` | `20` | Render or local `.env` |
| `MESSAGES_PER_DAY` | `100` | Render or local `.env` |
| `ALLOWED_ORIGINS` | `https://www.taylordorsett.com` | Render or local `.env` |
| `API_URL` | Empty | GitHub repository variable or site build environment |

Use one API process. The request counters live in memory and reset when the server restarts. Increasing workers or replicas would create separate allowances. The limits are shared by everyone, including evaluation requests and requests that reach the API but fail at a provider. They are not a durable dollar budget.

CORS restricts browser origins. It does not stop scripts from calling the public API. Forwarded client addresses are not used for the limits. Keep the provider budget enabled.

## Free hosting behavior

The API sleeps when idle. The first request can take about a minute. The site explains the wait and lets visitors stop. Don't add a constant health ping just to keep a free instance awake. Free instance hours are shared across the Render workspace. [Render explains the limits here.](https://render.com/docs/free)

The browser gives a request up to two minutes, including wake time. OpenAI calls use a 30 second SDK timeout without automatic retries. Pinecone search has a 15 second per request timeout. Stop cancels the browser request, but it cannot undo work the provider has already started or guarantee no charge.

The public site and handbook still work when the API is sleeping or unavailable. When the AI allowance is exhausted, visitors can keep reading the handbook.

## Logs and checks

Render logs include `moonbean_request` entries with a random request ID, outcome and elapsed time. Completed model calls also log input and output token counts. No question or answer text is included in those application log entries. The start command disables Uvicorn access logs. Hosting providers can still record their own request metadata.

Look for repeated `timeout`, `budget`, `busy`, `incomplete` or `unavailable` outcomes. A stream can fail after HTTP 200, so HTTP status alone is not enough to judge success. Use a live question when checking provider credentials, and use the saved evaluation suite when changing the prompt, model or handbook.

There is no automatic error paging or analytics service. Check Render logs and the OpenAI usage dashboard after releases. A persistent quota store and continuous monitoring would be later work if this grows beyond a small public demo.

## Updating the handbook

1. Edit `data/moonbean_handbook.md` in a branch.
2. Review the changed facts and run the tests.
3. After merging, run `python -m scripts.upload_handbook` against the intended index. The script also removes records for deleted or renamed sections.
4. Run retrieval and answer checks. Read failures before changing expected answers.
5. Verify a changed fact on the public site. The site rebuild and Pinecone upload are separate steps.

Git is the source of truth for the handbook. Pinecone can be rebuilt from it. Do not upload real employee records or private company documents to this public demo.

## Dependency updates

The `.in` files list direct package versions. The `.txt` files pin the full resolved set. Update the direct versions deliberately, then regenerate all three locks with Python 3.12 and pip tools:

```powershell
python -m pip install pip-tools
python -m piptools compile --strip-extras --no-emit-index-url --no-emit-trusted-host requirements.in
python -m piptools compile --strip-extras --no-emit-index-url --no-emit-trusted-host requirements-site.in
python -m piptools compile --strip-extras --no-emit-index-url --no-emit-trusted-host requirements-dev.in
python -m pip install -r requirements-dev.txt
python -m pip check
python -m pytest -q
node --test tests/chat-stream.test.mjs
```

Check the resulting locks on CI too, since production runs Linux. Dependency updates belong in their own PR.

## Roll back

Revert the bad commit through a PR so the site and API return to a reviewed version. For an urgent API failure, Render can redeploy a previous successful deploy. If a handbook upload caused the problem, check out the previous handbook and upload that version too. Rolling back code does not roll back Pinecone records or dashboard settings.

Never put keys in a PR, screenshot or error report. If a real key is exposed, revoke it in its provider dashboard, replace it on Render and redeploy.
