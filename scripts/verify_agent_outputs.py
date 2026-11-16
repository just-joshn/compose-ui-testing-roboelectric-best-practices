#!/usr/bin/env python3
"""Compile saved agent responses and check that each detects its assigned UI regression."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from verify_fixture import EXAMPLES, MUTATIONS, RESULTS, ROOT, copy_project, require_pass, run


WRONG_LABEL = (
    "wrong-summary-label",
    'Text("Draft", Modifier.testTag("summary-child"))',
    'Text("Wrong", Modifier.testTag("summary-child"))',
)
BY_NAME = {name: (name, before, after) for name, method, before, after in MUTATIONS}
CASES = (
    ("writing", "WritingTaskTest.kt", (BY_NAME["wrong-item"],)),
    ("review", "ReviewTaskTest.kt", (BY_NAME["wrong-item"], BY_NAME["noop-send"])),
    ("debugging", "DebuggingTaskTest.kt", (WRONG_LABEL,)),
)


def verify(case, responses):
    label, filename, mutations = case
    response = responses / filename
    assert response.is_file(), f"Missing response {response}"
    assert "Thread.sleep(" not in response.read_text(), f"Fixed sleep in {response}"
    with tempfile.TemporaryDirectory(prefix="agent-response-", dir=ROOT / ".work") as temporary:
        project = Path(temporary)
        copy_project(project)
        examples = project / EXAMPLES
        (examples / "FixtureUiTest.kt").unlink()
        shutil.copy2(response, examples / filename)
        require_pass(run(project, f"agent-{label}-baseline"))
        target = examples / "FixtureUi.kt"
        baseline = target.read_text()
        for name, before, after in mutations:
            assert baseline.count(before) == 1, (name, "mutation target must be unique")
            target.write_text(baseline.replace(before, after))
            try:
                result = run(project, f"agent-{label}-{name}")
                assert result["exit"] != 0 and result["cases"], result
                assert all(case["error"] is None and not case["skipped"] for case in result["cases"]), result
                failures = [case for case in result["cases"] if case["failure"] is not None]
                assert failures and all(
                    "AssertionError" in case["failure"].get("type", "") for case in failures
                ), result
            finally:
                target.write_text(baseline)
            require_pass(run(project, f"agent-{label}-{name}-restored"))
    return {"case": label, "status": "PASS", "mutations": [name for name, _, _ in mutations]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--responses", type=Path, default=ROOT / "evidence/agent-responses")
    parser.add_argument("--case", choices=[case[0] for case in CASES])
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    outcomes = []
    for case in CASES:
        if args.case and case[0] != args.case:
            continue
        try:
            outcomes.append(verify(case, args.responses))
        except AssertionError as error:
            outcomes.append({"case": case[0], "status": "FAIL", "error": str(error)})
    (RESULTS / "agent-task-results.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    for outcome in outcomes:
        print(outcome["case"], outcome["status"], flush=True)
    assert all(outcome["status"] == "PASS" for outcome in outcomes), outcomes


if __name__ == "__main__":
    main()
