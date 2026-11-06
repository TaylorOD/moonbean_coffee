# Handbook checks

There are 33 questions in `questions.json`. They cover facts, follow ups, the two Hip Strip cafes, missing policies, an attempt to override the instructions, and whether Moonbean is real.

The expected facts and sources come from the fictional handbook. The checker uses regular expressions and required section names. It can catch a missing number or citation, but it can also miss a contradiction or reject a good paraphrase. Read the saved answers before calling a result correct. A cited section is not proof that it supports every claim.

## Run them

These commands run from the repo root. Retrieval uses the Pinecone key in `.env`. Local checks use both keys in `.env` and the current prompt. Remote answer checks call the public API and use its shared allowance and paid AI credits. They do not run in CI.

```powershell
python -m scripts.evaluate --retrieval-only
python -m scripts.evaluate --api-url https://moonbean-api.onrender.com --limit 3
python -m scripts.evaluate --api-url https://moonbean-api.onrender.com
python -m scripts.evaluate --local --delay 0
```

The full answer run makes 33 requests, with seven seconds between them. Run it when the site is quiet. There are no automatic retries. Results go in `.eval-results/latest.json`, which is ignored by Git. Use `--output` to save a report somewhere else.

## Results

On November 6, 2026, retrieval found every required section for 27 of 27 applicable questions at top K 4. Four cases have no expected source and are skipped in retrieval mode. That is a retrieval result, not an answer accuracy score. The recorded details are in [retrieval-results.json](retrieval-results.json).

When changing the handbook, run the upload script first. Then run these checks and inspect failures before updating expected results. Don't change the expectations just to make a run pass.

The original deployed prompt scored 29 of 30 after manual review. The keyword check initially missed an incorrect answer about dogs inside Gibbous. That check now rejects the contradiction. A browser follow up also missed a citation, so the suite now includes a 31st case for families at Float Day.

The revised prompt asks the model to apply explicit exceptions literally and cite current excerpts for follow ups. It scored 31 of 31 in a local run with the real OpenAI and Pinecone services. All saved answers were read against the handbook. See [the original answers](answer-results-before.json) and [the revised answers](answer-results.json). This is one small fixed test set, not a guarantee or a general accuracy claim.


## Policy answer fix

A live check after that 31 of 31 run still gave the wrong answer about Gibbous. The retrieved Dogs and Pets section was correct. The answer invented a food preparation restriction anyway, so the earlier result did not establish that the problem was fixed.

Permission answers now quote the deciding handbook sentence before applying it. The prompt also tells the model to correct earlier answers and user assumptions when they disagree with the excerpts. There is no special answer coded for Gibbous and the handbook has not changed.

Two new cases challenge a false premise and follow up after an incorrect assistant answer. Run all three Gibbous cases three times with:

```powershell
python -m scripts.evaluate --local --case gibbous-dogs --case gibbous-dogs-premise --case gibbous-dogs-followup --repeat 3 --delay 0
```

Use `--api-url` instead of `--local` to check a deployed version. Repeats are limited to three and the total request count is capped at 33. An unknown case name stops the run before any provider calls.

The revised prompt passed [9 of 9 focused answers](policy-answer-results.json) and [6 related checks](policy-regression-results.json) using real OpenAI and Pinecone calls. I read all 15 answers against the handbook. The related checks cover the Hip Strip, life jackets, dress rules, an unknown benefit, prompt injection and a Float Day follow up. These are local results for the recorded prompt hash, not a new full suite result or proof about the deployed version. Repeated answers at temperature zero can be very similar. This reduces a known failure but does not guarantee every answer is correct.
