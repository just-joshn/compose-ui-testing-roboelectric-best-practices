#!/usr/bin/env python3

from pathlib import Path
import tempfile

from verify_fixture import RESULTS, ROOT, copy_project, require_pass, run

METHOD = "mergedLabelAndUnmergedChild"


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fixture-setup-", dir=ROOT / ".work") as temporary:
        project = Path(temporary)
        copy_project(project)
        target = project / "fixture/build.gradle.kts"
        baseline = target.read_text()
        before = "unitTests.isIncludeAndroidResources = true"
        assert baseline.count(before) == 1
        enabled = run(project, "resources-enabled", METHOD)
        require_pass(enabled, (METHOD,))
        try:
            target.write_text(baseline.replace(before, "unitTests.isIncludeAndroidResources = false"))
            disabled = run(project, "resources-disabled", METHOD)
            named = [case for case in disabled["cases"] if case["name"] == METHOD]
            assert len(named) == 1 and not named[0]["skipped"], disabled
        finally:
            target.write_text(baseline)
        require_pass(run(project, "resources-restored", METHOD), (METHOD,))
    try:
        require_pass(disabled, (METHOD,))
        outcome = "passed"
    except AssertionError:
        outcome = "failed"
    (RESULTS / "setup-comparison.md").write_text(
        "# Android resource inclusion comparison\n\n"
        "Hypothesis. Disabling Android resources prevents the default activity host from starting because the debug manifest is not loaded.\n\n"
        "Command. `python3 scripts/compare_setup.py`\n\n"
        f"The same `{METHOD}` test passed with resources enabled, {outcome} with resources disabled, and passed after restoration. "
        "Only `unitTests.isIncludeAndroidResources` changed in a disposable copy. See resources-*/gradle.log, result.json, and JUnit XML for the actual outcomes.\n"
    )
    print("PASS comparison recorded")


if __name__ == "__main__":
    main()
