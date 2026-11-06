# Handbook checks

There are 31 questions in `questions.json`. They cover facts, follow ups, the two Hip Strip cafes, missing policies, an attempt to override the instructions, and whether Moonbean is real.

The expected facts and sources come from the fictional handbook. The checker uses regular expressions and required section names. It can catch a missing number or citation, but it can also miss a contradiction or reject a good paraphrase. Read the saved answers before calling a result correct. A cited section is not proof that it supports every claim.

## Run them

These commands run from the repo root. Retrieval uses the Pinecone key in `.env`. Local checks use both keys in `.env` and the current prompt. Remote answer checks call the public API and use its shared allowance and paid AI credits. They do not run in CI.

```powershell
python -m scripts.evaluate --retrieval-only
python -m scripts.evaluate --api-url https://moonbean-api.onrender.com --limit 3
python -m scripts.evaluate --api-url https://moonbean-api.onrender.com
python -m scripts.evaluate --local --delay 0
```

The full answer run makes 31 requests, with seven seconds between them. Run it when the site is quiet. There are no automatic retries. Results go in `.eval-results/latest.json`, which is ignored by Git. Use `--output` to save a report somewhere else.

## Results

On November 6, 2026, retrieval found every required section for 27 of 27 applicable questions at top K 4. Four cases have no expected source and are skipped in retrieval mode. That is a retrieval result, not an answer accuracy score. The recorded details are in [retrieval-results.json](retrieval-results.json).

When changing the handbook, run the upload script first. Then run these checks and inspect failures before updating expected results. Don't change the expectations just to make a run pass.

The original deployed prompt scored 29 of 30 after manual review. The keyword check initially missed an incorrect answer about dogs inside Gibbous. That check now rejects the contradiction. A browser follow up also missed a citation, so the suite now includes a 31st case for families at Float Day.

The revised prompt asks the model to apply explicit exceptions literally and cite current excerpts for follow ups. It scored 31 of 31 in a local run with the real OpenAI and Pinecone services. All saved answers were read against the handbook. See [the original answers](answer-results-before.json) and [the revised answers](answer-results.json). This is one small fixed test set, not a guarantee or a general accuracy claim.
