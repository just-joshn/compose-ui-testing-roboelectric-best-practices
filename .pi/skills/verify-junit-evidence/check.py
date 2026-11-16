#!/usr/bin/env python3
"""Exhaustively check the real JUnit evidence gate over a finite report domain."""

import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
from itertools import product
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from time import monotonic
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/verify_fixture.py"
SYNC_COMMIT = "52f0a0cec60527544bd3b4bfb86128e6a873b9c0"
METHODS = ("mergedLabelAndUnmergedChild", "scopedOpenSelectsDraft")
NAMES = METHODS + ("unexpectedTest",)
STATUSES = ("pass", "failure-empty", "failure-typed", "error-empty", "error-typed", "skipped")
EXITS = (0, 1, -9)
MUTATIONS = (
    ("ignored-exit", 'result["exit"] == 0 and result["cases"]', 'result["cases"]', "process-exit"),
    ("ignored-skips", 'case["failure"] is None and case["error"] is None and not case["skipped"]', 'case["failure"] is None and case["error"] is None', "skipped"),
    ("ignored-failures", 'case["failure"] is None and case["error"] is None', 'case["error"] is None', "failure-typed"),
    ("falsey-failures", 'case["failure"] is None', 'not case["failure"]', "failure-empty"),
    ("ignored-errors", 'case["failure"] is None and case["error"] is None', 'case["failure"] is None', "error-empty"),
    ("ignored-methods", 'sorted(case["name"] for case in result["cases"]) == sorted(methods)', 'True', "method-multiset"),
)


def load_gate(source):
    spec = importlib.util.spec_from_file_location("checked_verify_fixture", source)
    module = importlib.util.module_from_spec(spec)
    # Read/compile directly: scratch rewrites must never reuse a stale .pyc.
    exec(compile(source.read_bytes(), str(source), "exec"), module.__dict__)
    return module


def sequences(values):
    for size in range(3):
        yield from product(values, repeat=size)


def report(cases):
    suite = ET.Element("testsuite")
    for name, status in cases:
        case = ET.SubElement(suite, "testcase", name=name, classname="fixture.FixtureUiTest")
        if status != "pass":
            tag = status.split("-", 1)[0]
            attributes = {"type": "java.lang.AssertionError"} if status.endswith("-typed") else {}
            ET.SubElement(case, tag, attributes)
    return ET.tostring(suite, encoding="unicode")


def expected_decision(cases, exit_code, methods):
    # Presence of a terminal element matters, not its attributes or truthiness.
    if exit_code != 0:
        return False, "process-exit"
    if not cases:
        return False, "no-tests"
    for _, status in cases:
        if status != "pass":
            return False, status
    if methods is not None and sorted(name for name, _ in cases) != sorted(methods):
        return False, "method-multiset"
    return True, "clean"


def check(source, workspace):
    gate = load_gate(source)
    gate.RESULTS = workspace / "results"
    project = workspace / "project"
    xml_dir = project / "fixture/build/test-results/testDebugUnitTest"
    requested = (None,) + tuple(sequences(METHODS))
    mismatches = {}
    executions = 0
    decisions = 0
    accepted_count = 0
    started = monotonic()
    variants = tuple(product(NAMES, STATUSES))

    for cases in sequences(variants):
        layouts = ("single", "split") if len(cases) == 2 else ("single",)
        for layout in layouts:
            documents = [report(cases)] if layout == "single" else [report((case,)) for case in cases]
            for exit_code in EXITS:
                def emit(command, **kwargs):
                    xml_dir.mkdir(parents=True, exist_ok=True)
                    for index, document in enumerate(documents):
                        (xml_dir / f"TEST-{index}.xml").write_text(document)
                    return subprocess.CompletedProcess(command, exit_code)

                # run() itself clears prior XML, parses fresh reports, copies them,
                # and writes result.json. Only the external producer is replaced.
                with patch.object(gate.subprocess, "run", side_effect=emit), redirect_stdout(io.StringIO()):
                    result = gate.run(project, "bounded")
                executions += 1
                for methods in requested:
                    expected, reason = expected_decision(cases, exit_code, methods)
                    try:
                        gate.require_pass(result, methods)
                        accepted = True
                    except AssertionError:
                        accepted = False
                    decisions += 1
                    accepted_count += accepted
                    if accepted == expected:
                        continue
                    key = reason if accepted else "rejected-clean"
                    if key not in mismatches:
                        mismatches[key] = {
                            "count": 0,
                            "shortest": {
                                "cases": cases,
                                "exit": exit_code,
                                "requested_methods": methods,
                                "layout": layout,
                                "xml": documents,
                                "parsed_result": result,
                                "expected_accept": expected,
                                "actual_accept": accepted,
                            },
                        }
                    mismatches[key]["count"] += 1
    return {
        "status": "FAIL" if mismatches else "PASS",
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sync_commit": SYNC_COMMIT,
        "python": platform.python_version(),
        "bounds": {"max_cases": 2, "names": NAMES, "statuses": STATUSES, "exits": EXITS,
                   "requested_methods": requested, "layouts": ["single", "split (two cases only)"]},
        "producer_executions": executions,
        "acceptance_decisions": decisions,
        "accepted": accepted_count,
        "mismatches": mismatches,
        "seconds": round(monotonic() - started, 3),
    }


def save(output, name, result):
    (output / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"{result['status']} {name}: {result['acceptance_decisions']} decisions; "
          f"mismatch categories={', '.join(result['mismatches']) or 'none'}")
    for category, finding in result["mismatches"].items():
        example = finding["shortest"]
        print(f"  {category}: exit={example['exit']}, cases={example['cases']}, "
              f"requested={example['requested_methods']}, accepts={example['actual_accept']}")


def self_test(original, baseline, workspace, output):
    scratch_source = workspace / "verify_fixture.py"
    checks = []
    for name, before, after, category in MUTATIONS:
        if original.count(before) != 1:
            raise RuntimeError(f"Mutation {name} no longer matches exactly once; review the code mapping")
        mutated = original.replace(before, after)
        scratch_source.write_text(mutated)
        (output / f"{name}-source.py").write_text(mutated)
        result = check(scratch_source, workspace / name)
        save(output, name, result)
        # Existing findings cannot count as detection of a new break.
        if category in baseline["mismatches"] or category not in result["mismatches"]:
            raise RuntimeError(f"Missed mutation {name}: no new {category} counterexample")
        checks.append({"mutation": name, "new_category": category, "detected": True})
    scratch_source.write_text(original)
    (output / "restored-source.py").write_text(original)
    restored = check(scratch_source, workspace / "restored")
    save(output, "restored", restored)
    if restored["mismatches"] != baseline["mismatches"]:
        # Paths differ between scratch runs; compare the actual inputs/decisions
        # rather than the path to the fake Gradle command in parsed_result.
        def signatures(result):
            return {key: (value["count"], {k: v for k, v in value["shortest"].items() if k != "parsed_result"})
                    for key, value in result["mismatches"].items()}
        if signatures(restored) != signatures(baseline):
            raise RuntimeError("Restoration did not reproduce baseline counterexamples")
    if SOURCE.read_text() != original or restored["source_sha256"] != baseline["source_sha256"]:
        raise RuntimeError("Covered source was not restored or the checkout changed during verification")
    (output / "self-test.json").write_text(json.dumps({"status": "PASS", "mutations": checks,
        "restored_sha256": restored["source_sha256"], "baseline_status": baseline["status"]}, indent=2) + "\n")
    print(f"PASS self-test: {len(MUTATIONS)} real-source scratch mutations caught; baseline restored")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help=f"also apply {len(MUTATIONS)} mutations in disposable source copies")
    args = parser.parse_args()
    if platform.python_implementation() != "CPython" or sys.version_info[:3] != (3, 12, 14) or sys.flags.optimize:
        parser.error("Use unoptimized CPython 3.12.14 via the uv command in SKILL.md")
    work = ROOT / ".work"
    work.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="verify-junit-evidence.", dir=work))
    original = SOURCE.read_text()
    (output / "verify_fixture.py").write_text(original)
    print(f"Evidence: {output}", flush=True)
    # Avoid host JDK discovery: no JVM is executed at this producer boundary.
    with tempfile.TemporaryDirectory(prefix="junit-domain-") as temporary, patch.dict(os.environ, {
        "JAVA_HOME": "/bounded-check/no-jvm", "ANDROID_HOME": "/bounded-check/no-sdk",
    }):
        workspace = Path(temporary)
        baseline = check(SOURCE, workspace / "baseline")
        save(output, "baseline", baseline)
        if args.self_test:
            self_test(original, baseline, workspace, output)
    print(f"Evidence retained: {output}")
    return 1 if baseline["mismatches"] else 0


if __name__ == "__main__":
    sys.exit(main())
