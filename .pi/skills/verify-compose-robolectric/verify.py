#!/usr/bin/env python3
"""Drive the repository's existing validation harness in a disposable checkout."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
SKILL = "compose-ui-testing-robolectric-best-practices"
FILES = ("settings.gradle.kts", "build.gradle.kts", "gradle.properties", "gradlew", "gradlew.bat")
METHODS = (
    "mergedLabelAndUnmergedChild",
    "scopedOpenSelectsDraft",
    "sendShowsReceiptAfterCompletion",
    "composeClockDoesNotCompleteSender",
    "disposalCancelsPendingSendAndFreshPanelIsIsolated",
    "selectorFailureIncludesTreeDiagnostics",
)
JOURNEYS = ("package", "writing", "review", "debugging", "suite", "mutations", "setup") + METHODS


def inventory(project):
    paths = [project / name for name in FILES]
    for name in ("gradle", "fixture/src", SKILL, "scripts", "evidence/agent-responses"):
        paths.extend(p for p in (project / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    paths.append(project / "fixture/build.gradle.kts")
    return {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def environment(project):
    env = os.environ.copy()
    if not env.get("JAVA_HOME") and sys.platform == "darwin":
        env["JAVA_HOME"] = subprocess.check_output(["/usr/libexec/java_home", "-v", "17"], text=True).strip()
    if not env.get("ANDROID_HOME"):
        env["ANDROID_HOME"] = str(Path.home() / "Library/Android/sdk")
    env.setdefault("GRADLE_USER_HOME", str(ROOT / ".work/gradle-home"))
    temporary = project / ".tmp"
    temporary.mkdir(exist_ok=True)
    env["TMPDIR"] = str(temporary) + os.sep
    # Use writable caches rather than Robolectric's shared /tmp download lock.
    env["JAVA_TOOL_OPTIONS"] = env.get("JAVA_TOOL_OPTIONS", "") + (
        f" -Dmaven.repo.local={ROOT / '.work/m2'} -Djava.io.tmpdir={temporary}"
    )
    return env


def execute(project, output, commands):
    output.mkdir(parents=True, exist_ok=False)
    env = environment(project)
    records = []
    try:
        for index, command in enumerate(commands, 1):
            with (output / f"command-{index}.log").open("w") as log:
                result = subprocess.run(command, cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            records.append({"command": command, "exit": result.returncode})
            if result.returncode:
                raise RuntimeError(f"Command failed ({result.returncode}); inspect {output}")
    finally:
        (output / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
        for source, destination in (
            (project / ".work/fixture-results", "fixture-results"),
            (project / "fixture/build/test-results/testDebugUnitTest", "junit"),
            (project / "fixture/build/reports/tests/testDebugUnitTest", "html"),
        ):
            if source.exists():
                shutil.copytree(source, output / destination)


def owned(run):
    marker = json.loads((run / "owner.json").read_text())
    if marker != {"checkout": str(ROOT), "run": str(run)}:
        raise RuntimeError("Run ownership mismatch; refusing to drive or delete")
    return run / "project"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("launch", "doctor", "drive", "cleanup"))
    parser.add_argument("run", type=Path)
    parser.add_argument("journey", nargs="?", choices=JOURNEYS)
    args = parser.parse_args()
    run = args.run.resolve()
    if run.parent != ROOT / ".work" or not run.name.startswith("verify-compose-robolectric."):
        parser.error("Use a fresh .work/verify-compose-robolectric.* directory")
    if args.action == "launch":
        run.mkdir(exist_ok=True)
        if any(run.iterdir()):
            parser.error("Launch needs an empty run directory")
        (run / "owner.json").write_text(json.dumps({"checkout": str(ROOT), "run": str(run)}))
        project = run / "project"
        project.mkdir()
        for name in FILES:
            shutil.copy2(ROOT / name, project / name)
        for name in ("gradle", "fixture", SKILL, "scripts", "evidence/agent-responses"):
            shutil.copytree(ROOT / name, project / name, ignore=shutil.ignore_patterns("build", ".gradle", "__pycache__"))
        evidence = run / "evidence"
        evidence.mkdir()
        (evidence / "manifest.json").write_text(json.dumps(inventory(project), indent=2) + "\n")
        for name in (SKILL, "scripts", "evidence/agent-responses", "gradle"):
            shutil.copytree(project / name, evidence / "source" / name)
        for name in FILES + ("fixture/build.gradle.kts", "fixture/src/main/AndroidManifest.xml"):
            target = evidence / "source" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project / name, target)
        execute(project, evidence / "launch", [
            ["./gradlew", "--version"],
            ["./gradlew", ":fixture:compileDebugUnitTestKotlin", "--console=plain", "--no-daemon"],
        ])
        (run / "ready").write_text("Compiled fixture; run doctor before driving.\n")
        print(f"READY {run}")
    elif args.action == "doctor":
        project = owned(run)
        assert (run / "ready").is_file(), "Launch did not complete"
        assert list((project / "fixture/build").rglob("FixtureUiTest.class")), "Compiled fixture missing"
        manifest = json.loads((run / "evidence/manifest.json").read_text())
        assert inventory(project) == manifest, "Workspace sources changed; launch a fresh run"
        assert inventory(ROOT) == manifest, "Checkout changed since launch; launch a fresh run"
        print(f"HEALTHY checkout={ROOT} workspace={project}; build/version logs in evidence/launch")
    elif args.action == "drive":
        project = owned(run)
        assert (run / "ready").exists(), "Launch did not complete"
        if args.journey is None:
            parser.error("Drive needs a journey")
        if args.journey in METHODS:
            commands = [["./gradlew", ":fixture:testDebugUnitTest", "--tests", f"fixture.FixtureUiTest.{args.journey}",
                         "--console=plain", "--no-daemon", "--rerun-tasks"]]
        elif args.journey == "package":
            commands = [[sys.executable, f"scripts/{name}.py"] for name in ("check_skill", "test_check_skill")]
        elif args.journey in ("writing", "review", "debugging"):
            commands = [[sys.executable, "scripts/verify_agent_outputs.py", "--case", args.journey]]
        elif args.journey == "setup":
            commands = [[sys.executable, "scripts/compare_setup.py"]]
        else:
            commands = [[sys.executable, "scripts/verify_fixture.py"] + (["--baseline-only"] if args.journey == "suite" else [])]
        # Eliminate previous results so evidence cannot borrow another journey's pass.
        for path in (project / ".work/fixture-results", project / "fixture/build/test-results/testDebugUnitTest",
                     project / "fixture/build/reports/tests/testDebugUnitTest"):
            shutil.rmtree(path, ignore_errors=True)
        execute(project, run / "evidence" / args.journey, commands)
        if args.journey in METHODS:
            cases = [case for xml in (run / "evidence" / args.journey / "junit").glob("TEST-*.xml")
                     for case in ET.parse(xml).getroot().findall("testcase")]
            assert len(cases) == 1 and cases[0].get("name") == args.journey, "Missing or unexpected test result"
            assert all(cases[0].find(tag) is None for tag in ("failure", "error", "skipped")), "Test did not pass"
        print(f"PASS {args.journey}; evidence={run / 'evidence' / args.journey}")
    else:
        project = owned(run)
        shutil.rmtree(project, ignore_errors=True)
        (run / "ready").unlink(missing_ok=True)
        print(f"CLEANED workspace; evidence retained at {run / 'evidence'}")


if __name__ == "__main__":
    main()
