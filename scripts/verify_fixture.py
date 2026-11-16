#!/usr/bin/env python3
"""Run the fixture and reject behavior mutations in a disposable project copy."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / ".work/fixture-results"
EXAMPLES = Path("compose-ui-testing-robolectric-best-practices/examples")
TEST_METHODS = (
    "mergedLabelAndUnmergedChild",
    "scopedOpenSelectsDraft",
    "sendShowsReceiptAfterCompletion",
    "composeClockDoesNotCompleteSender",
    "disposalCancelsPendingSendAndFreshPanelIsIsolated",
    "selectorFailureIncludesTreeDiagnostics",
)
MUTATIONS = (
    ("noop-send", "sendShowsReceiptAfterCompletion", "scope.launch {\n                    delivery = Delivery.Sending\n                    delivery = Delivery.Sent(sender.send(message))\n                }", "Unit"),
    ("wrong-item", "scopedOpenSelectsDraft", 'onOpen("Draft opened")', 'onOpen("Archive opened")'),
    ("removed-merge", "mergedLabelAndUnmergedChild", "semantics(mergeDescendants = true)", "semantics(mergeDescendants = false)"),
)


def copy_project(destination):
    for name in ("settings.gradle.kts", "build.gradle.kts", "gradle.properties", "gradlew", "gradlew.bat"):
        shutil.copy2(ROOT / name, destination / name)
    for name in ("gradle", "fixture", str(EXAMPLES)):
        shutil.copytree(ROOT / name, destination / name, ignore=shutil.ignore_patterns("build", ".gradle"))


def run(project, label, method=None):
    output = RESULTS / label
    output.mkdir(parents=True, exist_ok=True)
    xml_dir = project / "fixture/build/test-results/testDebugUnitTest"
    shutil.rmtree(xml_dir, ignore_errors=True)
    command = [str(project / "gradlew"), ":fixture:testDebugUnitTest", "--console=plain", "--no-daemon", "--rerun-tasks"]
    if method:
        command += ["--tests", "fixture.FixtureUiTest." + method]
    env = os.environ.copy()
    if not env.get("JAVA_HOME") and Path("/usr/libexec/java_home").exists():
        env["JAVA_HOME"] = subprocess.check_output(["/usr/libexec/java_home", "-v17"], text=True).strip()
    mac_sdk = Path.home() / "Library/Android/sdk"
    if not env.get("ANDROID_HOME") and mac_sdk.is_dir():
        env["ANDROID_HOME"] = str(mac_sdk)
    if env.get("TMPDIR"):
        env["JAVA_TOOL_OPTIONS"] = env.get("JAVA_TOOL_OPTIONS", "") + " -Djava.io.tmpdir=" + env["TMPDIR"]
    with (output / "gradle.log").open("w") as log:
        completed = subprocess.run(command, cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    cases = []
    if xml_dir.exists():
        for source in xml_dir.glob("TEST-*.xml"):
            shutil.copy2(source, output / source.name)
            for case in ET.parse(source).getroot().findall("testcase"):
                failure = case.find("failure")
                cases.append({"name": case.attrib["name"], "class": case.attrib["classname"], "failure": failure.attrib if failure is not None else None, "skipped": case.find("skipped") is not None})
    result = {"command": command, "exit": completed.returncode, "cases": cases}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(label, "exit", completed.returncode, "tests", len(cases), flush=True)
    return result


def require_pass(result, methods=None):
    assert result["exit"] == 0 and result["cases"], result
    assert all(not case["failure"] and not case["skipped"] for case in result["cases"]), result
    if methods is not None:
        assert sorted(case["name"] for case in result["cases"]) == sorted(methods), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fixture-verify-", dir=ROOT / ".work") as temporary:
        project = Path(temporary)
        copy_project(project)
        expected = TEST_METHODS + ("effectStartOrder", "effectStartOrder")
        require_pass(run(project, "baseline"), expected)
        if not args.baseline_only:
            target = project / EXAMPLES / "FixtureUi.kt"
            baseline = target.read_text()
            for label, method, before, after in MUTATIONS:
                assert baseline.count(before) == 1, (label, "mutation target must be unique")
                target.write_text(baseline.replace(before, after))
                try:
                    result = run(project, label, method)
                    named = [case for case in result["cases"] if case["name"] == method]
                    assert result["exit"] != 0 and len(named) == 1, result
                    assert named[0]["failure"] and "AssertionError" in named[0]["failure"].get("type", ""), result
                finally:
                    target.write_text(baseline)
                require_pass(run(project, label + "-restored", method), (method,))
            restored_methods = {mutation[1] for mutation in MUTATIONS}
            for method in TEST_METHODS:
                if method not in restored_methods:
                    require_pass(run(project, "isolated-" + method, method), (method,))
            require_pass(run(project, "final-baseline"), expected)
    print("PASS")


if __name__ == "__main__":
    main()
