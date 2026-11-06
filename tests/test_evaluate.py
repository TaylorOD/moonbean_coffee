import json

from app.handbook import read_handbook, to_records
from scripts.evaluate import ROOT, check_answer


def test_eval_sources_match_the_handbook():
    cases = json.loads((ROOT / "evals/questions.json").read_text())
    titles = {record["section"] for record in to_records(read_handbook())}
    assert len(cases) == len({case["id"] for case in cases}) == 31
    for case in cases:
        assert set(case["expected_sources"]) <= titles


def test_checker_requires_both_facts_and_citations():
    case = {"checks": ["19\\.25"], "expected_sources": ["Pay"]}
    assert check_answer(case, "Starting pay is $19.25", ["Pay"]) == []
    assert check_answer(case, "Starting pay is $25", ["Pay"])
    assert check_answer(case, "Starting pay is $19.25", [])


def test_checker_flags_forbidden_claims():
    case = {"checks": [], "expected_sources": [], "forbidden": ["free tuition"]}
    assert check_answer(case, "You get free tuition", [])


def test_gibbous_rejection_does_not_pass_just_because_it_says_allowed():
    cases = json.loads((ROOT / "evals/questions.json").read_text())
    case = next(c for c in cases if c["id"] == "gibbous-dogs")
    assert check_answer(case, "No, dogs are not allowed inside Gibbous because it prepares food on site.", ["Dogs and Pets"])
    assert not check_answer(case, "Yes, dogs are allowed inside Gibbous.", ["Dogs and Pets"])
