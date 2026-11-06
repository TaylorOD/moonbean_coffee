"""Check retrieval or answers against the fictional handbook question set.

Use --retrieval-only for Pinecone, or --api-url for the deployed chat API.
Live checks spend provider credits. They are deliberately not part of CI.
"""
import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.rag import answer as local_answer, search_handbook, system_prompt, TOP_K
from app.handbook import read_handbook

ROOT = Path(__file__).resolve().parent.parent


def check_answer(case, answer, sources):
    """A repeatable screen for facts and citations, not a substitute for review."""
    failures = []
    for pattern in case["checks"]:
        if not re.search(pattern, answer, re.IGNORECASE):
            failures.append(f"Missing expected fact: {pattern}")
    for pattern in case.get("forbidden", []):
        if re.search(pattern, answer, re.IGNORECASE):
            failures.append(f"Unexpected claim: {pattern}")
    missing = set(case["expected_sources"]) - set(sources)
    if missing:
        failures.append(f"Missing sources: {', '.join(sorted(missing))}")
    if case.get("expect_no_sources") and sources:
        failures.append("Expected no handbook citation")
    return failures


def request_answer(client, url, case):
    messages = case.get("history", []) + [{"role": "user", "content": case["question"]}]
    answer, sources, finished = "", [], False
    with client.stream("POST", f"{url.rstrip('/')}/api/chat", json={"messages": messages}) as response:
        response.raise_for_status()
        requires_done = response.headers.get("X-Chat-Protocol") == "2"
        for line in response.iter_lines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event["type"] == "error":
                raise RuntimeError(f"API returned {event.get('code', 'error')}")
            if event["type"] == "delta":
                answer += event["text"]
            elif event["type"] == "sources":
                sources = [section["title"] for section in event["sections"]]
                # The original API ended with sources. New versions also send done.
                finished = not requires_done
            elif event["type"] == "done":
                finished = True
    if not finished or not answer.strip():
        raise RuntimeError("API returned an incomplete answer")
    return answer, sources


def evaluate(cases, api_url=None, delay=7, local=False):
    results = []
    with httpx.Client(timeout=120) as client:
        for index, case in enumerate(cases):
            started = time.monotonic()
            result = {"id": case["id"], "category": case["category"], "question": case["question"]}
            try:
                if api_url or local:
                    if local:
                        messages = case.get("history", []) + [{"role": "user", "content": case["question"]}]
                        events = list(local_answer(messages))
                        answer = "".join(e["text"] for e in events if e["type"] == "delta")
                        sources = [s["title"] for e in events if e["type"] == "sources" for s in e["sections"]]
                    else:
                        answer, sources = request_answer(client, api_url, case)
                    result.update(answer=answer, sources=sources,
                                  failures=check_answer(case, answer, sources))
                else:
                    turns = [m["content"] for m in case.get("history", []) if m["role"] == "user"]
                    sources = [s["title"] for s in search_handbook(" ".join((turns + [case["question"]])[-2:]))]
                    missing = set(case["expected_sources"]) - set(sources)
                    result.update(sources=sources, failures=[f"Missing retrieval: {s}" for s in sorted(missing)])
                    if not case["expected_sources"]:
                        result["skipped"] = "No expected source. Requires answer evaluation."
            except Exception as error:
                # Keep exception bodies and credentials out of saved reports.
                result["failures"] = [f"Request failed: {type(error).__name__}"]
            result["seconds"] = round(time.monotonic() - started, 2)
            results.append(result)
            print(f"{case['id']}: {'skip' if result.get('skipped') else 'fail' if result['failures'] else 'pass'}", flush=True)
            if (api_url or local) and index < len(cases) - 1:
                time.sleep(delay)
    scored = [r for r in results if not r.get("skipped")]
    return {"created_at": datetime.now(timezone.utc).isoformat(),
            "mode": "local_answers" if local else "answers" if api_url else "retrieval",
            "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini") if local else None,
            "top_k": TOP_K if not api_url else None,
            "handbook_sha256": hashlib.sha256(read_handbook().encode()).hexdigest(),
            "instructions_sha256": hashlib.sha256(system_prompt([]).encode()).hexdigest() if local else None,
            "api_url": api_url, "passed": sum(not r["failures"] for r in scored),
            "scored": len(scored), "skipped": len(results) - len(scored), "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--api-url")
    mode.add_argument("--retrieval-only", action="store_true")
    mode.add_argument("--local", action="store_true", help="Use local RAG code and keys from .env")
    parser.add_argument("--limit", type=int, default=31)
    parser.add_argument("--delay", type=float, default=7, help="Seconds between live questions")
    parser.add_argument("--output", type=Path, default=ROOT / ".eval-results" / "latest.json")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 31 or args.delay < 0:
        parser.error("Choose 1 to 31 cases and a nonnegative delay")
    load_dotenv()
    cases = json.loads((ROOT / "evals" / "questions.json").read_text(encoding="utf-8"))[:args.limit]
    report = evaluate(cases, args.api_url, args.delay, args.local)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['passed']}/{report['scored']} passed, {report['skipped']} skipped. Saved {args.output}")
    return 1 if any(r["failures"] for r in report["results"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
