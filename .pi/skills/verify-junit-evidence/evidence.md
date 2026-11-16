# Executed evidence: JUnit evidence acceptance

Executed 2026-11-16 against commit `52f0a0cec60527544bd3b4bfb86128e6a873b9c0`, with no modifications to covered code. [Machine-readable results](evidence/results.json) preserve the complete finite domain, counterexample counts, shortest reports and parsed cases, mutation results, and source/checker hashes. Temporary command paths have been omitted from that portable summary; the raw artifacts retain them.

## Question and tool

Can the shared `scripts/verify_fixture.py::run` -> `require_pass` gate accept bad evidence or reject good evidence?

The stated contract requires exit 0, a nonempty result, no failure/error/skip terminal elements, and an exact method-name multiset when one is requested. This is the gate used for fixture, saved agent-response, and setup/restoration baselines. False green evidence could substantiate incorrect guidance throughout the installable skill.

The tool is a deterministic CPython 3.12.14 standard-library checker executing the actual Python parser and gate with generated producer outputs. This is bounded exhaustive concrete verification, **not an SMT proof, a TLA+ model, or an unbounded guarantee**. Its finite input space is cheap enough to enumerate completely without translating implementation logic into a model. The only substituted behavior is the subprocess producer; JDK/SDK discovery and result locations are redirected for isolation.

## Baseline

Command:

```bash
uv run --python 3.12.14 --no-project .pi/skills/verify-junit-evidence/check.py
```

The initial baseline checked 2,001 report/exit/layout inputs and 16,008 acceptance decisions. It exited **1**, reporting `failure-empty`, `error-empty`, and `error-typed`. The baseline repeated in the final self-test took about **1.4 seconds** excluding interpreter startup and checked the same full domain.

The bounds are all ordered case lists up to length two over three names and six statuses, process exits 0/1/-9, eight requested-method lists, and both single-file and split-file layouts for two cases. See the skill and JSON for the exact domain; this is not an equivalence proof for arbitrary strings, attributes, XML formats, or exit values.

There were **465 false acceptances**, 155 in each of three input categories. These expose **two defects**, not three independent bugs:

| Producer report, with exit 0 | Real `run()` output for that case | Real `require_pass()` result |
| --- | --- | --- |
| `<failure/>` | `failure: {}`, `skipped: false` | Accepts the falsey dictionary |
| `<error/>` | `failure: null`, `skipped: false` | Accepts because the error was dropped |
| `<error type="java.lang.AssertionError"/>` | `failure: null`, `skipped: false` | Same dropped-error defect |

Each shortest counterexample has one `mergedLabelAndUnmergedChild` test. For example:

```xml
<testsuite><testcase name="mergedLabelAndUnmergedChild" classname="fixture.FixtureUiTest"><failure /></testcase></testsuite>
```

Sequence in code terms: the controlled producer writes this XML and returns 0; `run()` parses the failure element's empty attributes; `require_pass()` tests dictionary truthiness and returns normally. No method list is needed for the counterexample; matching requested names also do not repair the outcome check.

**Reachability qualification:** exits and reports are varied independently. The check does not demonstrate the pinned Gradle runner producing exit 0 for a failed/errored test. With nonzero exit, current `require_pass()` rejects these reports. These are boundary robustness findings and do not establish that previous real JVM runs were false positives. Fixes were not applied to the existing harness or product.

## Real-source mutation and restoration proof

Followed the generated skill using:

```bash
uv run --python 3.12.14 --no-project .pi/skills/verify-junit-evidence/check.py --self-test
```

This executed six complete checks: current baseline, four separately broken copies of the real source, and restored source. Each check made 16,008 decisions: **96,048 total**. The modifications were made in disposable copies of `scripts/verify_fixture.py`, not in a hand-written model or the canonical checkout.

| Real-code scratch change | New shortest counterexample | Detected independently of known findings |
| --- | --- | --- |
| Remove `result["exit"] == 0` guard | Producer exit 1; one passing test is accepted | `process-exit` |
| Remove `not case["skipped"]` guard | Producer exit 0; one `<skipped/>` test is accepted | `skipped` |
| Remove `not case["failure"]` guard | Producer exit 0; one typed `<failure>` is accepted | `failure-typed` |
| Replace expected-method comparison with `True` | Producer exit 0; one passing test is accepted despite an empty requested method list | `method-multiset` |

All four new categories were absent from baseline and present in their assigned mutation. Existing failures therefore could not masquerade as successful mutation detection. The complete mutated sources and result summaries are archived in the raw run directory.

After dropping the scratch changes, the restored source had SHA-256 `7019e9dceb5926a4d2f2be9d8cccd693a1ac5b2aae39636e984d4fd2cc5df629`, matching baseline and the unchanged canonical source. The restored check reproduced exactly the baseline categories, counts, inputs, and decisions: 155 mismatches in each of the same three categories. It printed:

```text
PASS self-test: four real-source scratch mutations caught; baseline restored
```

The command correctly still exited **1** because the baseline property remains violated. Self-test status in `self-test.json` is `PASS`; property status in baseline and restored JSON is `FAIL`.

## Artifact locations

Portable evidence is [evidence/results.json](evidence/results.json). Raw final handoff artifacts on the verification host are at:

```text
/Users/josh-desktop/src/personal/compose-ui-testing-roboelectric-best-practices/.work/verify-junit-evidence.ewr7yfz4/
```

That directory contains baseline and restored results, all four mutation results, each mutated source, original/restored source snapshots, and `self-test.json`. The shorter initial baseline is in `.work/verify-junit-evidence.74rbn18a/`. These `.work` paths are ignored historical artifacts, not prerequisites for rerunning. The transient producer workspaces were removed; shortest XML and parsed outputs are retained in JSON. No existing fixture evidence was overwritten.

## Limits and review

The checker verifies the real parsing/acceptance path within its finite input space, not Gradle itself. It uses `run(method=None)`; the controlled producer does not interpret command arguments. It does not verify Gradle command construction, optional `--tests` filtering, reachability of the independently generated exit/report pairs, or actual Kotlin/Compose behavior. Cleanup executes but is not independently certified. There is no claim about missing or malformed XML, nested suites, arbitrary metadata, multiple terminal elements, class identity, more than two cases, concurrent writers, or optimized Python.

A separate read-only review confirmed the finite-domain count, real-function execution, independent oracle, and new-category mutation detection. It requested explicit producer-reachability and command/filtering/cleanup exclusions; those are recorded here and in the skill. That reviewer reran the checker with only its output root redirected to sandbox scratch because its read-only sandbox could not create `.work`. The handoff run above used the documented command without redirection.

No Android/JVM tests were run for this change; no shipped guidance, Kotlin source, build file, or existing harness was modified. Use `/skill:verify-compose-robolectric` when evidence from actual Compose tests is needed.
