---
name: verify-junit-evidence
description: Exhaustively check the bounded JUnit evidence acceptance contract after changes to scripts/verify_fixture.py run or require_pass, their result schema, or callers in verify_agent_outputs.py and compare_setup.py. Use for false-green evidence, JUnit parsing, skipped tests, process exit handling, and expected method coverage. Not Compose UI or real Gradle verification.
---

# Verify the JUnit evidence gate

## Property

`run()` followed by `require_pass()` accepts a result if and only if the producer exited successfully, at least one test ran, every test has no failure, error, or skip element, and any supplied expected method list matches the reported names exactly, including duplicates.

A false acceptance can certify broken fixture examples or saved agent responses. A false rejection prevents valid evidence from being used.

## Run the check

Run from the repository root. Install `uv` first. The command downloads CPython 3.12.14 if absent. Subsequent runs need no SDK, JDK, Gradle, solver, external Python dependencies, or network access. The checker rejects other Python versions and optimized execution because the covered gate uses `assert`.

```bash
uv run --python 3.12.14 --no-project .pi/skills/verify-junit-evidence/check.py
```

Require `PASS baseline`, exit 0, **2,001 producer executions**, and **16,008 acceptance decisions** in `baseline.json`. This is bounded exhaustive concrete checking of the actual Python functions, not an unbounded proof or a hand model. The finite domain is small enough to enumerate without symbolic execution through filesystem and subprocess calls.

Each run prints a unique `.work/verify-junit-evidence.*` directory. It retains the covered source, its SHA-256, the checker SHA-256, the reviewed sync commit, and counterexamples when present.

- Exit 0 with the expected summary means no discrepancies in the stated domain.
- Exit 1 with `FAIL baseline` means the current code violates the contract. Inspect each category's shortest-by-test-count input, XML, parsed result, and expected and actual decisions.
- A traceback, interpreter error, missing summary, or reduced domain means verification is inconclusive. Exit 1 alone does not prove a contract violation.

Do not allowlist failures or weaken the property to obtain a pass. The baseline is expected to pass. The original findings were fixed, not made acceptable.

## Bounds and producer boundary

The generator visits every combination in this finite domain.

| Dimension | Inputs |
| --- | --- |
| Reported cases | Ordered sequences of length 0, 1, or 2, allowing duplicates |
| Name per case | `mergedLabelAndUnmergedChild`, `scopedOpenSelectsDraft`, `unexpectedTest` |
| Status per case | No terminal element; `<failure/>`; `<failure type="java.lang.AssertionError"/>`; `<error/>`; `<error type="java.lang.AssertionError"/>`; `<skipped/>` |
| Producer exit | `0`, `1`, `-9` |
| Expected methods | `None`, or every ordered list of length 0 through 2 over the two real method names, for 8 choices total |
| XML layout | One `TEST-*.xml` file; also one file per case for two-case reports |

The checker calls the real `run()` for each report, exit, and layout, then real `require_pass()` for all eight expected lists. It replaces `subprocess.run` with a producer that writes controlled XML and returns the chosen exit. It redirects results and JDK discovery to scratch settings. The real parser, report deletion and copying, JSON serialization, and acceptance assertions execute.

The oracle uses the generated terminal status, not the parsed result's truthiness. A missing failure or error is `None`. A present element retains its attributes, including an empty dictionary. Both present forms must prevent acceptance.

Exit status and report contents vary independently. Counterexamples demonstrate report-boundary validation defects, not that actual Gradle emitted those combinations. A successful bounded check does not establish actual Gradle behavior. `run()` uses `method=None`; the controlled producer does not interpret the command or verify `--tests` filtering. Cleanup executes but is not independently certified.

## Check regression sensitivity

After changing the checker, skill, or covered code, run the self-test and caller regressions.

```bash
uv run --python 3.12.14 --no-project .pi/skills/verify-junit-evidence/check.py --self-test
uv run --python 3.12.14 --no-project python scripts/test_junit_acceptance.py
```

The self-test copies the real `scripts/verify_fixture.py` into scratch storage and applies each mutation separately. Require the following new counterexamples.

| Scratch change | Required category |
| --- | --- |
| Remove the process-exit guard | `process-exit` |
| Remove the skip guard | `skipped` |
| Remove the failure guard | `failure-typed` |
| Reintroduce failure-dictionary truthiness | `failure-empty` |
| Remove the error guard | `error-empty` |
| Remove the expected-method comparison | `method-multiset` |

Require `PASS baseline`, `PASS restored`, and `PASS self-test: 6 real-source scratch mutations caught; baseline restored`, with overall exit 0. Individual mutant `FAIL` summaries are expected. Existing baseline findings cannot satisfy mutation detection. The helper refuses nonunique mutation anchors and verifies the restored source hash and unchanged canonical source. Variant sources and results remain in the run directory.

The separate regression module exercises actual caller orchestration with a controlled producer. It checks that mixed assertion failures and errors cannot count as valid mutation detection, empty failure metadata cannot disappear, and setup comparison cannot call a terminal failure or error report passed. This is regression coverage, not part of the bounded proof of `require_pass()`.

If the self-test misses a break or an anchor no longer matches, update the anchor to the corresponding real guard. Do not alter the property or the scratch bug to manufacture a pass.

## Coverage and sync record

Last confirmed against commit **`6fefcb5decac7f24fe81fa415b0194082043c10d`**.

Covered source SHA-256 is **`8ade644edc2e389544970525b2cadab46a483e89beb6ca912f284ee6a19d87ea`**.

| File and function | Coverage |
| --- | --- |
| `scripts/verify_fixture.py::run` | Immediate-child JUnit testcase parsing into exit, names, failure and error metadata, and skipped flags; single and split report files |
| `scripts/verify_fixture.py::require_pass` | Successful exit, nonempty cases, absence of every terminal element, and optional method-name multiset |
| `scripts/verify_fixture.py::main` | Caller mapping and separate regression test for mixed error and named assertion failure; not exhaustive mutation-orchestration verification |
| `scripts/verify_agent_outputs.py::verify` | Caller mapping and separate mixed-outcome regressions; not exhaustive negative-mutation classification |
| `scripts/compare_setup.py::main` | Shared gate for enabled, restored, and disabled-outcome classification; separate reporting regression |

Before trusting a result mid-change, read these functions and inspect the diff, including uncommitted changes.

```bash
git diff 6fefcb5decac7f24fe81fa415b0194082043c10d -- scripts/verify_fixture.py scripts/verify_agent_outputs.py scripts/compare_setup.py
```

Confirm that the schema, immediate-child XML format, producer boundary, and callers still match this description. Old archived results without an `error` field are historical evidence, not complete current-schema results.

When behavior intentionally changes, restate the contract first. Update the domain, boundary, mutation anchors, coverage map, and regression tests as needed. Run both commands above and inspect the results. Advance the sync commit in this file and `check.py::SYNC_COMMIT` only after confirming that the verification describes the covered code at that actual commit. Do not advance it merely because a command ran. Use `/skill:maintain-formal-verification-skill` after changes that landed without rechecking.

## Evidence and exclusions

[evidence.md](evidence.md) records the current passing result, original defects, and their repair. [Current results](evidence/results.json) retain the executed domain and mutation examples. [Before-fix results](evidence/before-fix.json) preserve the original failing evidence.

This does not cover arbitrary Python inputs, XML shapes, strings, attributes, exit values, more than two cases, missing XML files, nested suites, malformed XML, multiple terminal elements per case, class identity, suite counters, filesystem failures, concurrent runs, symlinks, stale-report security, optimized Python, or freshness of archived output directories. Zero cases uses an empty suite.

This also does not verify actual Gradle report consistency, command filtering, Kotlin or Compose behavior, device rendering, or skill activation. Use `/skill:verify-compose-robolectric` for real fixture execution. Do not count this controlled producer as a passing JVM test.
