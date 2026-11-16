---
name: verify-junit-evidence
description: Exhaustively check the bounded JUnit evidence acceptance contract after changes to scripts/verify_fixture.py run or require_pass, their result schema, or callers in verify_agent_outputs.py and compare_setup.py. Use for false-green evidence, JUnit parsing, skipped tests, process exit handling, and expected method coverage. Not Compose UI or real Gradle verification.
---

# Verify the JUnit evidence gate

## Promise and harm

**Property:** `run()` followed by `require_pass()` accepts a result if and only if the producer exited successfully, at least one test ran, every test has no failure/error/skip element, and any supplied expected method list matches the reported names exactly, including duplicates.

**Harm:** A false acceptance can certify broken fixture examples or saved agent responses as passing evidence; a false rejection prevents valid evidence from being used.

The shipped product is an agent skill, not an application. This shared gate substantiates its claims across the canonical fixture, setup comparison, and saved writing/review/debugging responses. This makes evidence acceptance a higher-leverage verification target than one example's callback. There is no production message delivery service in this repo.

## Run from the repository root

Prerequisite: `uv` on PATH. The command downloads CPython 3.12.14 if absent. After that it needs no SDK, JDK, Gradle, solver, external Python dependencies, or network access. It uses the standard library only. The checker rejects other Python versions and optimized execution because the covered gate uses `assert`.

```bash
uv run --python 3.12.14 --no-project .pi/skills/verify-junit-evidence/check.py
```

The tool is **bounded exhaustive concrete checking**, not a theorem prover or an unbounded proof. It executes the actual Python functions rather than translating them into a hand model. A finite generator is cheaper here than symbolic execution through subprocess/filesystem calls, and it visits every input in the stated domain. No TLA+ model is involved.

Require **2,001 producer executions and 16,008 acceptance decisions**. A traceback, wrong interpreter, missing summary, or a smaller domain is a failed verification attempt, never a pass. Each run prints a unique `.work/verify-junit-evidence.*` directory and retains `baseline.json` plus the exact covered source as `verify_fixture.py`.

Exit interpretation:

- **0 / `PASS baseline`:** no mismatches in this domain. Read the bounds before making a claim.
- **1 / `FAIL baseline`:** real discrepancies from the stated contract. Open `baseline.json`; each mismatch category includes a count and its first, shortest-by-test-count counterexample, original XML, parsed result, and actual/expected decisions.
- **Other errors or traceback:** inconclusive; repair the checker/environment before using the result. Exit 1 alone is not evidence of a detected contract violation.

Do not add an allowlist or turn the known failures below into a passing exit code. A reported `FAIL baseline` is a finding, not a reason to soften the contract.

## Bounds and external boundary

Every combination of these inputs is checked:

| Dimension | Finite domain |
| --- | --- |
| Reported cases | Ordered sequences of length 0, 1, or 2, allowing duplicates |
| Names per case | `mergedLabelAndUnmergedChild`, `scopedOpenSelectsDraft`, `unexpectedTest` |
| Status per case | No terminal element; `<failure/>`; `<failure type="java.lang.AssertionError"/>`; `<error/>`; `<error type="java.lang.AssertionError"/>`; `<skipped/>` |
| Producer exit | `0`, `1`, `-9` |
| Expected methods | `None`, or every ordered list of length 0 through 2 over the two real method names (8 choices total) |
| XML layout | One `TEST-*.xml` file; also one file per case for two-case reports |

The checker calls the real `run()` for each report/exit/layout, then real `require_pass()` for all eight expected lists. It replaces only `subprocess.run` with a producer that writes controlled XML at `fixture/build/test-results/testDebugUnitTest` and returns the chosen exit status. It redirects `RESULTS` to scratch storage and supplies dummy JDK/SDK environment paths to avoid host discovery. The real XML deletion, parsing, report copying, result serialization, and acceptance assertions still execute. Cleanup is exercised but not independently certified. `run()` is called with `method=None`; the producer does not interpret its command, so command construction and the optional `--tests` filter are not verified. No build or test source is executed by the producer.

The oracle reads the generated case status, not `result["failure"]`. It therefore distinguishes a present but attribute-free failure from no failure and detects information lost during parsing. There are no modeled concurrent actions or atomicity assumptions: each producer returns before the real synchronous parser runs.

## Current findings: keep these visible

At the sync commit, the check is **FAIL**, with 465 false acceptances grouped into three input categories representing two implementation defects. The shortest examples each have one test and process exit 0:

1. The producer writes `mergedLabelAndUnmergedChild` with `<failure/>`.
2. `run()` records `failure: {}`.
3. `require_pass()` sees a falsey dictionary and returns normally instead of rejecting the failure.

Separately:

1. The producer writes that test with `<error/>` or `<error type="java.lang.AssertionError"/>`.
2. `run()` looks only for `<failure>`, so records `failure: null` and `skipped: false`.
3. `require_pass()` returns normally instead of rejecting the error.

These are **defensive-validation findings under independently varied process/XML inputs**. A truthful nonzero Gradle exit already makes the gate reject those reports. This check has not observed actual Gradle emitting exit 0 with a failing/error report; it does not invalidate the existing successful fixture runs. Whether such reports are reachable from the pinned Gradle runner requires separate JVM evidence. The contract deliberately requires both a successful process and clean reports, rather than trusting either alone.

See [evidence.md](evidence.md) for the executed baseline, mutation proof, and limitations. Do not edit product/harness code to fix findings unless the user requests that work.

## Prove the check still detects a break

After changing this skill or its checker, run:

```bash
uv run --python 3.12.14 --no-project .pi/skills/verify-junit-evidence/check.py --self-test
```

This follows the normal check, then copies the **real `scripts/verify_fixture.py` source** into scratch storage and breaks one guard at a time. It removes the exit guard, skip guard, failure guard, and expected-method comparison. Each variant runs the same complete bounded check and must introduce its own new counterexample category: `process-exit`, `skipped`, `failure-typed`, and `method-multiset`. Existing baseline findings cannot satisfy mutation detection. The helper refuses mutation text that is not unique.

It then drops the scratch edits by restoring the original source, repeats the check, compares all counterexample counts/inputs/decisions with baseline, and confirms the restored SHA-256 and unchanged checkout source. Require `PASS self-test: four real-source scratch mutations caught; baseline restored` and a `self-test.json` with status `PASS`. The command still exits **1** while baseline findings remain; the self-test passing does not make the property pass. All variant sources and results are retained beside baseline evidence; only disposable execution directories are removed.

If a future authorized fix eliminates a baseline finding, rerun both commands and review the new result rather than assuming the old counts still apply. If a mutation is already detected by baseline or no longer matches the code, update it to a new, single real-code break with a distinct counterexample. Never change the property to accommodate a missed mutation.

## Coverage and synchronization record

Last confirmed against commit **`52f0a0cec60527544bd3b4bfb86128e6a873b9c0`**.

Covered source SHA-256 at that commit: **`7019e9dceb5926a4d2f2be9d8cccd693a1ac5b2aae39636e984d4fd2cc5df629`**.

| Code to open | What this check covers |
| --- | --- |
| `scripts/verify_fixture.py::run` | Fresh immediate-child JUnit `<testcase>` parsing into `exit`, `cases[].name`, `failure`, and `skipped`; both one-file and split-file reports |
| `scripts/verify_fixture.py::require_pass` | Success/nonempty checks, per-case outcome checks, optional method-name multiset comparison |
| `scripts/verify_fixture.py::main` | Caller mapping only: full/isolated fixture and restored baselines use this gate; its orchestration is not executed |
| `scripts/verify_agent_outputs.py::verify` | Caller mapping only: saved-response baseline/restoration calls; negative-mutation acceptance is not covered |
| `scripts/compare_setup.py::main` | Caller mapping only: enabled/restored baseline calls; setup comparison logic is not covered |

Before trusting a result mid-change, inspect the source and the diff since sync:

```bash
git diff 52f0a0cec60527544bd3b4bfb86128e6a873b9c0 -- scripts/verify_fixture.py scripts/verify_agent_outputs.py scripts/compare_setup.py
```

That diff includes committed and uncommitted changes in the checkout. Confirm the functions, schema, immediate-child XML format, subprocess boundary, and callers still have the meaning above. An unchanged checker passing against a changed schema is not enough. Report artifacts include source/checker hashes to identify the exact run; `sync_commit` is a reviewed mapping record, not a claim that every working tree equals HEAD.

When behavior intentionally changes, restate the desired contract first, change the input domain/oracle/boundary or mutation anchors as necessary, update this skill's map and bounds, run baseline and self-test, and inspect the counterexamples. Advance the sync commit **in both this skill and `check.py::SYNC_COMMIT` only after confirming that the verification describes the covered code at that actual commit**. Do not set it to the new HEAD merely because the command ran. For changes that already landed without rechecking, use `/skill:maintain-formal-verification-skill` to bring this skill back in sync.

## Not established

No claim is made about arbitrary Python inputs or every XML shape, more than two cases, arbitrary strings/attributes/exit values, missing XML files (zero cases uses an empty suite), nested suites, malformed XML, multiple terminal elements per case, class identity, suite-level counters, filesystem failures, concurrent runs, symlinks, stale-report security, optimized Python, or freshness of archived output directories. These exclusions are not silently identified with the enumerated cases.

This checks the gate, not actual Gradle exit/report consistency, mutation-failure classification, Kotlin/Compose behavior, cancellation/event ordering, Android resources, device rendering, or agent skill activation. For actual fixture evidence use `/skill:verify-compose-robolectric`; do not count this controlled producer as a passing JVM test.
