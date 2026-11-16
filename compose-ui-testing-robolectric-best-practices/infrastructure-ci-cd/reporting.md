# Preserve local UI test reports and failure evidence

Use this guide to make local Compose test results reviewable in CI and reproducible
on a developer machine. Gradle supplies JUnit XML, HTML, and console output.
Robolectric does not supply Playwright action traces or automatic video recording.

## Table of contents

- [Choose the evidence](#choose-the-evidence)
- [Configure Gradle output](#configure-gradle-output)
- [Capture semantics near a failure](#capture-semantics-near-a-failure)
- [Organize artifacts by run identity](#organize-artifacts-by-run-identity)
- [Publish without hiding failure](#publish-without-hiding-failure)
- [Validate passing evidence](#validate-passing-evidence)
- [Aggregate shards and retries](#aggregate-shards-and-retries)
- [Build summaries and notifications](#build-summaries-and-notifications)
- [Handle screenshots and sensitive data](#handle-screenshots-and-sensitive-data)
- [Avoid misleading reports](#avoid-misleading-reports)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the evidence

| Artifact | Use | Limitation |
| --- | --- | --- |
| JUnit XML | Method identities, failures, errors, skips, durations | Does not prove completeness without an expected inventory |
| Gradle HTML report | Human review of cases and stack traces | Preserve its assets and original task boundary |
| Console log | Configuration, compilation, worker startup, exceptions | A success string is not test evidence |
| Merged semantics dump | User-facing grouping and selector diagnosis | Not a screenshot or accessibility-service traversal |
| Unmerged semantics dump | Child details, including descendants under clearing nodes | Does not establish accessibility-service exposure |
| Synthetic fake request log | Boundary input diagnostics | Not proof of real transport |
| Optional renderer image | Narrow drawing diagnosis | Not automatic device pixel fidelity |
| Coverage report | Executed application bytecode | Not behavioral correctness |

Retain JUnit and HTML on completed passing runs as well as failures.
Collect bounded diagnostics near failures and keep the source revision and exact command.
Set retention according to sensitivity and debugging needs.
Fourteen days for ordinary reports is an example policy, not a framework requirement.

## Configure Gradle output

This illustrative Android module fragment uses the Gradle 9.4.1 `Test` API.
Keep imports at the top of `build.gradle.kts`.
It does not change runner selection or add dependencies.

```kotlin
import org.gradle.api.tasks.testing.Test
import org.gradle.api.tasks.testing.logging.TestExceptionFormat

tasks.withType<Test>().configureEach {
    reports.junitXml.required.set(true)
    reports.html.required.set(true)
    testLogging {
        events("failed", "skipped")
        exceptionFormat = TestExceptionFormat.FULL
        showStandardStreams = true
    }
}
```

Enable standard streams only with synthetic test data and a reviewed log policy.
A semantics dump can expose field contents.
Do not print authorization headers, tokens, real passwords, or all environment variables.

Run a narrow case with ordinary failure propagation:

```bash
./gradlew :app:testDebugUnitTest \
  --tests 'com.example.ui.MessagePanelTest.sendShowsReceipt' \
  --stacktrace --console=plain
```

Expected default task output paths are:

```text
app/build/test-results/testDebugUnitTest/TEST-com.example.ui.MessagePanelTest.xml
app/build/reports/tests/testDebugUnitTest/index.html
```

Actual XML names can vary with runner and parameterization.
Inspect the files rather than hardcoding a single filename into a universal parser.
Use the selected flavor task's directory when the module has flavors.
Gradle's binary test results are not interchangeable with Playwright blob reports.

## Capture semantics near a failure

This illustrative fragment belongs inside a test with an initialized Compose rule
named `compose`. It uses APIs available in the pinned UI 1.12.1 examples.
It requires `androidx.compose.ui:ui-test-junit4` and the normal hosted Robolectric setup.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.printToString

try {
    compose.onNodeWithText("Delivered").assertIsDisplayed()
} catch (failure: AssertionError) {
    try {
        println("MERGED\n${compose.onRoot().printToString()}")
        println("UNMERGED\n${compose.onRoot(useUnmergedTree = true).printToString()}")
    } catch (diagnosticFailure: Exception) {
        failure.addSuppressed(diagnosticFailure)
    } catch (diagnosticFailure: AssertionError) {
        failure.addSuppressed(diagnosticFailure)
    }
    throw failure
}
```

The original assertion remains the test failure.
The diagnostic step can fail when the host or synchronization is already broken.
Preserve that as suppressed evidence rather than replacing the behavior failure.
Do not catch the original assertion and return normally.

Capture the dump before the rule disposes the composition.
A generic outer JUnit watcher may run after an inner Compose rule has already torn
down the host. If adding a watcher, verify rule ordering with an intentional failure.
Do not publish a helper as reliable until the failed test actually retains its tree.

For timeouts, first identify the work owner.
A pending fake may never produce the expected node, while a busy idling resource can
prevent even the diagnostic query from completing.
Keep diagnostic collection bounded and preserve the original timeout log.

## Organize artifacts by run identity

A useful artifact layout is illustrative:

```text
run-artifacts/
  revision.txt
  command.txt
  toolchain.txt
  app-debug-sdk35-shard0-attempt1/
    junit/
    html/
    console.txt
  app-debug-sdk35-shard1-attempt1/
    junit/
    html/
    console.txt
```

Record only relevant nonsecret environment facts.
Include selected runtime SDK, Java worker version, Compose and Robolectric versions,
module, task, source revision, and class-list identity.
Do not infer runtime SDK solely from `compileSdk`.

Keep each HTML report's complete directory.
Moving only `index.html` can lose styles, scripts, class pages, or linked resources.
Do not mix reports from several variants in one task directory.

On a long-lived runner, isolate each revision's output before testing.
Use a clean job workspace or a deliberate output cleanup policy.
Do not delete a shared developer checkout as an incidental reporting step.
A timestamp alone is weak freshness evidence. Pair files with the actual invocation
and clean output provenance.

## Publish without hiding failure

These GitHub steps assume the normal test command has already run:

```yaml
- uses: actions/upload-artifact@v4
  if: ${{ !cancelled() }}
  with:
    name: app-debug-sdk35-local-ui
    retention-days: 14
    path: |
      app/build/test-results/testDebugUnitTest/
      app/build/reports/tests/testDebugUnitTest/
```

The condition allows publication after a test failure while respecting cancellation.
A hard-killed worker might have no reports. That is incomplete execution evidence.
Keep provider console logs for failures before the test task.
Do not require a fake XML file just to make the upload succeed.

Equivalent provider mechanisms are:

| Provider | Result publication | Artifact preservation |
| --- | --- | --- |
| GitLab | `artifacts:reports:junit` | `artifacts:when:always` and paths |
| Jenkins | `junit` in `post { always { ... } }` | `archiveArtifacts` |
| CircleCI | `store_test_results` | `store_artifacts` |
| Azure | `PublishTestResults@2` with `condition: always()` | `PublishPipelineArtifact@1` |

A publisher can annotate failures but cannot validate the entire test contract by itself.
Keep the original Gradle command's nonzero status.
Do not mark only an artifact collector as the required test status.

## Validate passing evidence

A passing badge requires more than an XML document with zero failures.
For a bounded verification run, check all of the following:

1. The intended Gradle process completed with exit code zero.
2. The expected task actually ran, or reuse was explicitly permitted and identified.
3. Results come from that invocation and source revision.
4. Every expected class and method appears in valid JUnit XML.
5. Every expected method completed without failure, error, or an unapproved skip.
6. Every expected shard, variant, and SDK dimension is present.
7. Duplicate identities have an explicit parameterization or attempt meaning.

Reject empty reports, malformed XML, initialization errors disguised as test cases,
and `NO-SOURCE` when tests were expected.
A task's overall exit code and test-case status are separate observations.
A zero exit cannot excuse missing methods. Passing methods cannot excuse a failed process.

For a mutation check, require the intended behavior method to fail at its UI assertion.
A Kotlin compile error, host launch failure, or dependency download failure does not
prove the test detected the behavior regression.
Restore the code and rerun before accepting the negative evidence.

## Aggregate shards and retries

Download each shard under a distinct directory.
Check the artifact inventory before aggregating test identities.
Do not overwrite identical XML filenames from separate jobs.
Do not average counts from dashboards that deduplicate classes differently.

Preserve the complete test identity, including SDK and parameter suffixes.
For retries, record attempt one and later attempts separately.
A later pass does not erase the first failure or prove absence of flakiness.
If the CI publisher collapses attempts, retain raw XML for independent inspection.

Gradle does not provide Playwright's `merge-reports` CLI for Robolectric.
Use provider JUnit ingestion, a tested custom parser, or an explicitly configured
Gradle reporting integration whose Android support you verified.
Do not assume the JVM test-report aggregation plugin automatically models every
Android variant's results.

## Build summaries and notifications

Prefer a post-test summary step that reads finished XML over a network callback
inside a UI test. The summary's data shape should preserve counts for passed, failed,
errored, skipped, and missing expected tests, plus the overall process result.
Do not calculate `passed = total - failed` when errors and skips are possible.

If building a custom parser, cover these inputs in its own tests:

- One successful expected method.
- A failure and an error.
- An unexpected skip.
- Missing or empty XML.
- Malformed XML and runner initialization failure.
- Duplicate method identities and separate SDK executions.
- A failed Gradle process with partial passing XML.

Send notifications from a separate bounded step with a timeout and limited credentials.
Include the actual run URL and failing matrix identity.
A notification transport failure must not overwrite the original test verdict.
Do not upload semantics text or fake request payloads to a third-party webhook by default.

## Handle screenshots and sensitive data

A semantics dump is often the most direct evidence for selector failures.
A JVM image can help diagnose custom drawing only when its renderer and capture API
are explicitly configured. It is not automatically a device screenshot baseline.
There is no default Robolectric screen recording equivalent to browser video.

Use a device or dedicated screenshot lane for pixel fidelity, system overlays,
TalkBack, IME, and real rendering performance.
Link that lane's artifacts rather than relabeling local semantics output as device proof.
Keep synthetic data in all layers and restrict artifact access where needed.

## Avoid misleading reports

| Anti-pattern | Failure mechanism | Correct approach |
| --- | --- | --- |
| Upload only on failure | Passing runs have no reviewable execution inventory | Retain XML and HTML on ordinary completed runs |
| Swallow assertion to print a tree | Broken behavior becomes a pass | Rethrow the original assertion |
| Run diagnostics only after disposal | Semantics no longer exist | Capture inside the rule lifetime |
| Merge report directories by overwrite | Same class names replace each other | Preserve matrix directories |
| Treat XML presence as success | Partial, skipped, or stale results pass | Validate process and expected methods |
| Notify from every UI test | Network latency and credentials enter test behavior | Summarize after task completion |

## Troubleshoot

| Symptom | Observe first | Fix |
| --- | --- | --- |
| No HTML report | Whether the Test task started and reports are enabled | Fix compile or setup failure, then rerun |
| XML dashboard empty | Actual result directory versus publisher glob | Match module and flavor task |
| Assertion replaced by tree error | Exception handling and rule lifetime | Retain the original failure and suppressed diagnostic error |
| Green summary with missing methods | Expected inventory and raw XML | Fail acceptance and repair filtering |
| Missing results after sharding | Artifact names and download collisions | Require all shards and retain subdirectories |
| Logs expose user data | Standard streams and semantics payload | Use synthetic data and restrict collection |
| Report seems from an older revision | Workspace and output provenance | Isolate outputs and rerun the intended task |

## Review checklist

- Reports identify command, revision, module, variant, SDK, and shard.
- Gradle exit status survives publication and notification steps.
- Expected methods execute without unexpected skips.
- The complete HTML directory and raw JUnit XML remain available.
- Diagnostics run before teardown and never suppress the original assertion.
- Retry attempts remain distinguishable.
- Artifacts do not overclaim device behavior or expose secrets.

## Related guides and sources

- [CI](ci-cd.md), [sharding](parallel-sharding.md), and [coverage](test-coverage.md).
- [Diagnostics](../references/diagnostics.md) and [canonical diagnostics tests](../examples/FixtureUiTest.kt).
- [Gradle testing and reports](https://docs.gradle.org/9.4.1/userguide/java_testing.html).
- [Gradle Test API](https://docs.gradle.org/9.4.1/dsl/org.gradle.api.tasks.testing.Test.html).
- [Compose testing APIs](https://developer.android.com/develop/ui/compose/testing/apis).
- [Robolectric best practices](https://robolectric.org/best-practices/).
