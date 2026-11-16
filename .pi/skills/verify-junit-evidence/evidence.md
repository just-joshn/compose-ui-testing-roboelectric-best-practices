# JUnit evidence acceptance results

The current baseline **passes**. The original failures remain in [before-fix.json](evidence/before-fix.json) as historical evidence. [Current results](evidence/results.json) record the repaired gate and six independently detected scratch mutations.

## Property and scope

The real `scripts/verify_fixture.py::run` followed by `require_pass` accepts evidence only when the producer succeeds, tests run, no test has a failure, error, or skip element, and any requested method list matches exactly. It also accepts every clean result in the finite domain.

The checker uses CPython 3.12.14 and the standard library. It executes the actual parser and gate with a controlled subprocess producer. This is bounded exhaustive concrete verification, not an unbounded proof, an SMT proof, or a TLA+ model.

The input domain is unchanged by the repair. It covers every ordered case list up to length two over three names and six statuses, three process exits, eight expected-method lists, and single or split report files. That produces 2,001 producer executions and 16,008 acceptance decisions per check. The count comes from enumerating the stated inputs, not sampling or repeating cached results.

## Original defects and repair

The original check found two implementation defects. With producer exit 0, `<failure/>` became an empty dictionary that the gate treated as false. The parser ignored `<error>` elements entirely. The original run reported 465 false acceptances in the finite domain, grouped into three input categories. Those are combinations, not separate bugs or a production failure rate.

The exit and report inputs vary independently. This never established that actual Gradle emitted exit 0 for failed tests or that earlier JVM passes were false positives. A nonzero producer exit already caused rejection.

The defects originated in fixture harness commit `f54ac58947729f0178bc7e53b9936b6ae0687974`, which became main commit `bab961920d7c1f96d9f107658ae044774d31f036` through PR #1. The commit record describes baseline and mutation validation, not an intentional exception for empty failures or errors.

The repair is commit **`6fefcb5decac7f24fe81fa415b0194082043c10d`**. It preserves the existing result dictionaries and function signatures. Each fresh case now has separate `failure` and `error` metadata. `None` means absent; a dictionary, including `{}`, means present. The pass gate checks explicit absence. Both mutation consumers reject errors and skips, and require AssertionError metadata for reported failures. Setup comparison reuses the pass gate before labeling an outcome passed.

Regression commit `422ff1e65ab3927498982b99d3c8d8e5b29f16a3` precedes the repair. Its five tests produced eleven intended failures before the fix and passed after it. They exercise real parsing and caller orchestration with a controlled producer, without executing Gradle.

## Current baseline and mutation proof

Executed 2026-11-16 against the committed repair and refreshed sync record.

```bash
uv run --python 3.12.14 --no-project .pi/skills/verify-junit-evidence/check.py --self-test
uv run --python 3.12.14 --no-project python scripts/test_junit_acceptance.py
```

The checker exited **0**. Both baseline and restored source passed all 16,008 decisions with no mismatches. Each scratch variant modifies a disposable copy of the real source and must introduce a category absent from baseline.

| Scratch change | Required observed category |
| --- | --- |
| Remove exit guard | `process-exit` |
| Remove skip guard | `skipped` |
| Remove failure guard | `failure-typed` |
| Restore falsey failure handling | `failure-empty` |
| Remove error guard | `error-empty` |
| Remove method comparison | `method-multiset` |

All six variants failed as required. The two new regression controls cover the repaired presence and error defects without changing the generator or oracle. The restored source SHA-256, `8ade644edc2e389544970525b2cadab46a483e89beb6ca912f284ee6a19d87ea`, matches the original current-source snapshot and canonical source. The final summary was:

```text
PASS baseline: 16008 decisions; mismatch categories=none
PASS restored: 16008 decisions; mismatch categories=none
PASS self-test: 6 real-source scratch mutations caught; baseline restored
```

Raw handoff artifacts are at `.work/verify-junit-evidence.ypc5hry8/` on the verification host. They include source snapshots, every mutant source, baseline and restored JSON, mutant results, and `self-test.json`. The transient producer workspaces were removed. The portable current JSON omits transient command paths but retains the inputs, XML, parsed outcomes, decisions, counts, and hashes.

The local decision trail is `.work/junit-fix/decisions.tsv`. Reproduction and caller-regression logs are beside it. These ignored host paths are historical artifacts, not rerun prerequisites.

## Real JVM compatibility check

A separate fresh disposable workspace ran the existing `verify-compose-robolectric` launch, doctor, and drive workflow with the repaired scripts. These runs used real Gradle and Robolectric, not the controlled producer. Doctor passed before every drive and after the final drive.

| Journey | Observed result |
| --- | --- |
| `mutations` | Eight-test initial and final baselines passed. All three named UI regressions failed with AssertionError. Restorations and other isolated methods passed. |
| `writing` | Saved scoped Draft Open test passed, rejected wrong item, and passed restoration. |
| `review` | Both saved tests passed, rejected wrong item and no-op Send, and passed restorations. |
| `debugging` | Saved unmerged-child label assertion passed, rejected changed text, and passed restoration. |
| `setup` | Enabled and restored resource runs passed. Disabled resources reached JUnit and failed with the expected activity-resolution RuntimeException. The comparison recorded failed. |

All five outer journeys exited 0. Fresh results contained the new `error` field. Passing and restored runs had no failures, errors, or skips. Behavioral negative controls had the intended named AssertionError, rather than compile or setup failures.

The complete host artifacts and source snapshots remain at `.work/verify-compose-robolectric.lnwiLr/evidence/`, including `proof.md`. A structured inspection summary is `.work/junit-fix/jvm-summary.json`. Cleanup removed only the owned disposable project after the jobs exited. These are host artifact paths, not prerequisites for running the skill.

The installed skill's Kotlin examples and saved responses were unchanged. These JVM runs are compatibility evidence for the exercised methods, not proof that every report shape or device behavior is correct. Saved-output replay does not certify fresh agent activation or automatic discovery. Archive Open and blank-message disabled-state paths remain known fixture coverage gaps.

## Limits

The bounded check does not verify actual Gradle report consistency, command construction, the optional `--tests` branch, Kotlin or Compose behavior, or device behavior. Cleanup executes but is not independently certified. The generator does not cover arbitrary XML, missing reports, nested suites, malformed input, multiple terminal elements per case, arbitrary names or metadata, more than two cases, concurrent writers, class identity, or optimized Python.

The separate caller regression tests cover mixed outcomes outside that formal domain. Their passes do not expand the bounded check's claims. The acceptance promise and bounds did not change; the original failures were bugs in the code, not drift in the oracle. Only real-source mutation anchors needed maintenance after the new guards changed shape.
