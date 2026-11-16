# Partition and parallelize local UI tests

Use this guide when a correct Android local test suite needs shorter CI feedback.
Gradle test forks, parallel module tasks, and CI shards are separate controls.
Keep Compose test methods within a worker sequential unless your exact runner supports
another model and you have verified its Android state isolation.

## Table of contents

- [Choose a concurrency boundary](#choose-a-concurrency-boundary)
- [Configure Gradle forks](#configure-gradle-forks)
- [Partition by class](#partition-by-class)
- [Wire a CI matrix](#wire-a-ci-matrix)
- [Prove complete selection](#prove-complete-selection)
- [Balance slow shards](#balance-slow-shards)
- [Isolate state and work](#isolate-state-and-work)
- [Avoid false optimizations](#avoid-false-optimizations)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a concurrency boundary

| Control | Splits | Shares | Use when |
| --- | --- | --- | --- |
| `maxParallelForks` on `Test` | Test classes across JVMs | Machine CPU, memory, files | One worker has spare capacity |
| Gradle `--parallel` | Eligible project tasks | Machine and Gradle worker budget | Independent Android modules exist |
| CI matrix | Explicit module or class partitions | External services and remote caches | Extra machines justify repeated setup |
| Robolectric SDK configuration | One class across selected SDK models | Worker budget | Behavior varies by framework API |
| Concurrent JUnit methods | Methods in one JVM | Process globals and Android state | Not the default recommendation for Compose Robolectric |

`--max-workers` is a build-wide resource limit, not a test shard count.
A runtime SDK matrix increases coverage dimensions. It does not partition the suite.
Do not multiply all dimensions before checking total memory and job cost.

## Configure Gradle forks

This illustrative module-level Kotlin DSL fragment uses Gradle's `Test` API.
It assumes the Android plugin has already created the local test tasks.
The properties are project-defined, not built-in Gradle flags.

```kotlin
import org.gradle.api.tasks.testing.Test

val uiTestForks = providers.gradleProperty("uiTestForks")
    .map(String::toInt)
    .orElse(1)

tasks.withType<Test>().configureEach {
    maxParallelForks = uiTestForks.get()
}
```

Start with one fork and compare two using the same suite and runner class:

```bash
./gradlew :app:testDebugUnitTest -PuiTestForks=1 --rerun-tasks
./gradlew :app:testDebugUnitTest -PuiTestForks=2 --rerun-tasks
```

Both runs must execute the same expected tests without skips.
Account for compiler workers, the Gradle daemon, and native rendering allocations.
Do not equate test heap size with the whole job's memory requirement.

Keep `forkEvery` at its normal reuse setting unless evidence identifies worker growth.
Restarting a JVM for every class can repeat expensive Robolectric initialization.
A diagnostic fresh fork can expose a leak, but it does not repair the leak.

## Partition by class

Gradle does not supply a universal `--shard` flag for Android local tests.
A checked list of fully qualified test classes is a simple starting point.
The list is the selection contract. Validate it against the unsharded suite's JUnit
inventory so a newly added test cannot disappear from CI.

The following illustrative build fragment reads a file named by `uiTestClassList`.
Add it to the Android module's `build.gradle.kts`, with imports at the top.
Paths passed in the example are relative to the root project.

```kotlin
import org.gradle.api.tasks.testing.Test

val classListPath = providers.gradleProperty("uiTestClassList")
val selectedClasses = classListPath.map { path ->
    rootProject.file(path).readLines()
        .map(String::trim)
        .filter(String::isNotEmpty)
        .also { classes ->
            require(classes.isNotEmpty()) { "The shard class list is empty" }
            require(classes.size == classes.toSet().size) {
                "The shard class list contains duplicates"
            }
        }
}

tasks.withType<Test>().configureEach {
    if (classListPath.isPresent) {
        filter {
            isFailOnNoMatchingTests = true
            selectedClasses.get().forEach { includeTestsMatching(it) }
        }
    }
}
```

This fragment intentionally avoids a custom test runner or reflection-based discovery.
It reads configuration at build configuration time. Do not claim configuration-cache
compatibility without testing that build and its file-input tracking.
Restrict the fragment to selected `Test` tasks if the module has unrelated suites.

An example `ci/ui-shard-0.txt` contains exact class names, with no comments:

```text
com.example.ui.MessagePanelTest
com.example.ui.DraftActionsTest
```

A second list might contain:

```text
com.example.ui.SettingsPanelTest
com.example.ui.NavigationTest
```

Run each in its own checkout or CI job:

```bash
./gradlew :app:testDebugUnitTest -PuiTestClassList=ci/ui-shard-0.txt
```

The expected result is only the first list's classes in that job's JUnit files.
A nonexistent class among several valid classes might not make Gradle's whole filter
empty. Therefore `failOnNoMatchingTests` is necessary but insufficient.
Verify every requested class in the report inventory.

## Wire a CI matrix

This fragment assumes checkout, compatible Java, Android SDK, and Gradle setup steps
from [GitHub Actions](github-actions.md). It uses zero-based filenames by convention.
Neither Gradle nor Robolectric interprets the index.

```yaml
strategy:
  fail-fast: false
  matrix:
    shard: [0, 1]
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-java@v4
    with:
      distribution: temurin
      java-version: '17'
  - uses: gradle/actions/setup-gradle@v4
  - run: >-
      ./gradlew :app:testDebugUnitTest
      -PuiTestClassList=ci/ui-shard-${{ matrix.shard }}.txt
      -PuiTestForks=1 --stacktrace --console=plain
  - uses: actions/upload-artifact@v4
    if: ${{ !cancelled() }}
    with:
      name: ui-debug-shard-${{ matrix.shard }}
      path: |
        app/build/test-results/testDebugUnitTest/
        app/build/reports/tests/testDebugUnitTest/
      retention-days: 14
```

Keep reports under separate shard directories after download.
There is no Robolectric equivalent of Playwright's blob reporter.
Use the CI provider's JUnit aggregation, or explicitly combine results with a parser
that preserves variant, SDK, parameterized method, and retry identities.

## Prove complete selection

Before accepting a partition, verify these invariants:

1. Run the complete suite with fresh result directories.
2. Record the actual class and method identities from its JUnit XML.
3. Check that the shard class lists are disjoint.
4. Check that their union equals the intended full class inventory.
5. Run every shard and compare its actual methods with the expected methods.
6. Reject missing artifacts, unplanned skips, duplicate execution, or stale files.

For Robolectric SDK-expanded or parameterized tests, preserve the report's actual
method names. Do not remove suffixes merely to make the counts match.
A requested class appearing in XML does not prove all of its methods ran.
Store the source revision and shard-list revision with the result.

An empty shard is a partition error in this model.
Reduce the shard count rather than disabling the no-match failure.
Do not use a wildcard fallback that runs the entire suite on every empty shard.

## Balance slow shards

Use historical per-class durations from the same variant and runtime SDK.
Assign the longest classes first to the currently lightest shard.
Keep the generated lists reviewable and verify the invariants above.

Do not balance from source line counts or method counts alone.
A class with two hosted tests may cost more than twenty pure state tests.
A very slow class limits class-level distribution. Split it only along independent
behavior boundaries, not to share a mounted activity between methods.

Rebalance when timings materially change.
Do not recalculate from one noisy run or silently alter selection during a retry.
Measure total pipeline duration, including queue time, repeated compilation, downloads,
and artifact aggregation, before claiming a speedup.

## Isolate state and work

A fresh JVM does not isolate a hardcoded file path, database row, or network port.
Each test needs its own fake, deferred completion, mutable UI state, and temporary files.
Use JUnit temporary directories or an equivalent owned directory.
Bind local test servers to an allocated free port instead of a fixed port.

Do not share a mounted Compose host across tests as a worker fixture.
The rule owns composition lifetime. A launched activity may own its own content.
Keep one content owner and restore changed process globals after every method.
Cancel test-owned scopes and close executors, files, and servers even after failure.

Parallelism does not fix synchronization.
Complete a pending fake explicitly, advance the scheduler that owns a delay,
and assert the user-visible result. Avoid sleeps introduced only for CI.

## Avoid false optimizations

Bad:

```bash
./gradlew :app:testDebugUnitTest --shard=1/4
```

This assumes a flag that the Android `Test` task does not provide.
Use explicit filters or the checked class lists above.

Another anti-pattern is four jobs that run the same unfiltered command.
They increase cost and duplicate evidence without partitioning work.
Inspect actual report identities, not job names, to confirm distribution.

Do not force test order to repair a shared singleton.
A serialized failure may become rarer while leaving order dependence intact.

## Troubleshoot

| Symptom | Observation | Fix |
| --- | --- | --- |
| More forks make the suite slower | CPU pressure, GC, native memory, repeated startup | Reduce forks and measure the same test inventory |
| One shard has no tests | Class-list contents and task variant | Repair the partition or wrong task |
| A requested class disappears | Expected versus actual JUnit identities | Fail inventory validation even if other classes ran |
| Classes pass alone but fail together | Globals, temporary paths, pending threads | Restore per-test ownership |
| Aggregated XML loses tests | Duplicate filenames after download | Preserve shard directories |
| One job dominates wall time | Per-class durations | Rebalance or split independent classes |
| `--tests` seems ignored | Build-script filters and task path | Inspect combined filters and selected module |

## Review checklist

- Fork count, module parallelism, and shard count are separate decisions.
- Every shard has an explicit nonempty selection.
- The partition equals the intended unsharded inventory.
- Artifact identities include every relevant matrix dimension.
- Tests do not share mutable fakes or external names.
- The same tests pass with one fork and the chosen concurrency.
- Any speed claim includes setup and aggregation cost.

## Related guides and sources

- [Test speed](performance.md), [reporting](reporting.md), and [test filtering](../core/test-filtering.md).
- [Isolation](../references/isolation.md) and [synchronization](../references/synchronization.md).
- [Gradle testing](https://docs.gradle.org/9.4.1/userguide/java_testing.html).
- [Gradle Test API](https://docs.gradle.org/9.4.1/dsl/org.gradle.api.tasks.testing.Test.html).
- [Robolectric best practices](https://robolectric.org/best-practices/).
