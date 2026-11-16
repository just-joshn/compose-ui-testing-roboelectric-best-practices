# Collect coverage without overstating UI confidence

Use this guide to collect JVM code coverage from local Android tests and to review
what the result does and does not prove. Coverage measures executed bytecode.
It does not prove that a semantics assertion checks the right user-visible outcome.

## Table of contents

- [Choose the coverage approach](#choose-the-coverage-approach)
- [Establish a trustworthy baseline](#establish-a-trustworthy-baseline)
- [Configure an explicit JaCoCo report](#configure-an-explicit-jacoco-report)
- [Run collection and inspect sources](#run-collection-and-inspect-sources)
- [Enforce thresholds](#enforce-thresholds)
- [Combine modules and shards](#combine-modules-and-shards)
- [Review changed code and behavior](#review-changed-code-and-behavior)
- [Publish coverage in CI](#publish-coverage-in-ci)
- [Keep instrumentation isolated](#keep-instrumentation-isolated)
- [Avoid misleading metrics](#avoid-misleading-metrics)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the coverage approach

| Goal | Approach | Check |
| --- | --- | --- |
| Existing Android coverage pipeline | Keep its supported AGP or coverage-plugin integration | Exact plugin and variant task documentation |
| Explicit JVM execution-data report | JaCoCo agent plus a custom report task | Uninstrumented class files match execution data |
| Pure Kotlin domain module | Standard JVM JaCoCo tasks | Java or JVM plugin owns the source set |
| Multiple Android variants | Separate reports before aggregation | Do not combine different bytecode as one class |
| UI behavior confidence | Action-to-visible-result tests and mutation checks | A no-op action must fail the assertion |
| Device code coverage | Separate instrumentation test pipeline | Device coverage is not local JVM execution data |

Do not assume applying `jacoco` to an Android module creates the standard JVM
`jacocoTestReport` task with the correct Android class directories.
Do not copy Kover or AGP task names from an unrelated plugin version.
Discover the consuming project's actual tasks and use that plugin's versioned docs.

The custom example below uses Gradle 9.4.1's documented JaCoCo task types and pins
JaCoCo 0.8.14. It is illustrative, not executed in the canonical fixture.
It deliberately requires explicit application class directories instead of guessing
AGP internal output paths. Validate instrumentation against your Robolectric version
before making it a required CI gate.

## Establish a trustworthy baseline

First run the ordinary local UI task without coverage.
Confirm its named methods, assertions, host manifest, resources, and supported SDK.
Keep the original result so instrumentation failures can be distinguished from UI failures.

```bash
./gradlew :app:testDebugUnitTest --rerun-tasks --stacktrace
./gradlew :app:tasks --all
```

Inspect the build's compiled application class outputs for the selected variant.
AGP versions, built-in Kotlin, flavors, and compiler settings can change these locations.
Do not point the report at test classes, dependency jars, or instrumented copies.
Prefer public variant artifact APIs in a maintained build plugin when automating this
for many modules. This guide does not invent an AGP artifact API signature.

Record the following inputs with the coverage result:

- Source revision and exact variant.
- Gradle, AGP, Java, Kotlin, Compose, Robolectric, and agent versions.
- Executed test inventory and runtime SDK.
- Application class and source directories.
- Exclusion policy and report denominator.

## Configure an explicit JaCoCo report

The data shape is one variant's local `Test` execution data, its matching original
application class files, and the corresponding source directories.
The report and verification task must consume the same class universe.

Add the following illustrative fragments to the Android module's `build.gradle.kts`.
Merge the plugin into its existing `plugins` block and put imports at the top.
The Android and Compose setup remains the consuming project's responsibility.

```kotlin
import org.gradle.api.tasks.testing.Test
import org.gradle.testing.jacoco.plugins.JacocoTaskExtension
import org.gradle.testing.jacoco.tasks.JacocoCoverageVerification
import org.gradle.testing.jacoco.tasks.JacocoReport

plugins {
    jacoco
}

jacoco {
    toolVersion = "0.8.14"
}

val debugUiTests = tasks.named<Test>("testDebugUnitTest")
debugUiTests.configure {
    extensions.configure<JacocoTaskExtension> {
        isIncludeNoLocationClasses = true
        excludes = listOf("jdk.internal.*")
    }
}

val coverageClassFiles = providers.gradleProperty("coverageClasses").map { paths ->
    files(paths.split(",").map { path ->
        fileTree(file(path)) {
            include("com/example/**")
            exclude("**/R.class", "**/R$*.class", "**/BuildConfig.class")
        }
    })
}
val coverageSources = files("src/main/kotlin", "src/main/java")

val debugUiCoverage = tasks.register<JacocoReport>("debugUiCoverage") {
    dependsOn(debugUiTests)
    executionData(debugUiTests.get())
    classDirectories.from(coverageClassFiles.get())
    sourceDirectories.from(coverageSources)
    doFirst {
        require(classDirectories.files.isNotEmpty()) { "No production class files" }
    }
    reports {
        html.required.set(true)
        xml.required.set(true)
        csv.required.set(false)
    }
}
```

Replace `com/example/**` with your application package's class path.
Add flavor or variant source directories if they contribute production code.
Do not exclude composable functions or all `*Kt` classes to raise a percentage.
The no-location setting can matter for classes loaded through custom class loaders.
It is not a general cure for incompatible instrumentation.

`executionData(debugUiTests.get())` uses the Test task's JaCoCo execution-data location.
Do not hardcode a guessed `.exec` path if the task already exposes its agent extension.
A missing `coverageClasses` property must fail report configuration rather than silently
produce a zero-class report.

## Run collection and inspect sources

Pass the actual comma-separated class directories found in your build.
The environment variable below is an explicit input, not a standard Gradle variable:

```bash
: "${COVERAGE_CLASS_DIRS:?Set actual original debug application class directories}"
./gradlew :app:debugUiCoverage \
  -PcoverageClasses="$COVERAGE_CLASS_DIRS" --rerun-tasks --stacktrace
```

Use module-relative or absolute paths consistently with `file(path)` in the module.
Do not pass source directories where compiled class files are required.
The output normally appears under the module's `build/reports/jacoco/` tree.
Inspect the actual task output rather than assuming an HTML filename for publication.

Before accepting the report:

1. Confirm that the test task executed and passed without unexpected skips.
2. Find a known application class in HTML and XML.
3. Confirm that an intentionally unvisited production class is present as uncovered.
4. Check the agent log for class-ID mismatch or instrumentation errors.
5. Inspect line mapping for Kotlin and Compose-generated code.
6. Confirm that dependencies and test helpers do not inflate the denominator.

A report containing only loaded classes can hide completely unvisited files.
The application class directory defines the denominator, not the set of observed probes.
Coverage of generated state-machine or Compose compiler code needs interpretation.
Do not label instruction coverage as line or branch coverage.

## Enforce thresholds

Add a verification task that uses the same inputs as the report:

```kotlin
val verifyDebugUiCoverage = tasks.register<JacocoCoverageVerification>(
    "verifyDebugUiCoverage",
) {
    dependsOn(debugUiTests)
    executionData(debugUiTests.get())
    classDirectories.from(coverageClassFiles.get())
    sourceDirectories.from(coverageSources)
    doFirst {
        require(classDirectories.files.isNotEmpty()) { "No production class files" }
    }
    violationRules {
        rule {
            limit {
                counter = "LINE"
                value = "COVEREDRATIO"
                minimum = "0.80".toBigDecimal()
            }
        }
    }
}
```

The 80 percent limit is illustrative, not a universal quality target.
Choose a threshold from the actual module's risk and baseline.
Invoke it explicitly or wire it into the consuming project's `check` lifecycle.
Gradle's JaCoCo verification task is not automatically a dependency of `check`.

```bash
./gradlew :app:debugUiCoverage :app:verifyDebugUiCoverage \
  -PcoverageClasses="$COVERAGE_CLASS_DIRS" --rerun-tasks
```

For per-package rules, select the relevant application classes with JaCoCo rule
includes and keep the same report denominator policy.
Do not weaken broad exclusions whenever a critical branch is hard to test.
Add a behavior test or document the untested boundary.

## Combine modules and shards

Keep execution data separate by module, variant, SDK, shard, and attempt.
JaCoCo can combine execution data for identical original class definitions.
The aggregate report must use exactly those original class files from the tested revision.
Do not average percentages or concatenate XML counters.

Download all expected shard data before report generation.
Reject missing shards even when another shard produces a high percentage.
Use matching class files and execution data from the same build configuration.
Bytecode changes can create class-ID mismatches even when source filenames match.

Do not merge debug and release coverage as if they were one execution.
Different compiler transformations and shrinking change the measured class universe.
Preserve per-variant reports and only aggregate through a verified compatible scheme.
The Gradle JVM report aggregation plugin is not an automatic Android variant adapter.

## Review changed code and behavior

Map changed source paths to the report's real source files.
An absent changed file is a missing denominator or an unmeasured file, not full coverage.
Keep the full report as the baseline for incremental checks.

Pair a high coverage result with tests that drive the actual interaction and assert the
visible result. A fake payload assertion alone can execute a composable's code while
missing a broken UI transition.
Temporarily remove the state update and confirm the intended behavior assertion fails.
A compilation error is not a killed UI mutation.

## Publish coverage in CI

These steps belong after Java, Android SDK, checkout, and Gradle setup.
They assume the class-directory input has been resolved for that build:

```yaml
- name: Collect and verify coverage
  run: >-
    ./gradlew :app:debugUiCoverage :app:verifyDebugUiCoverage
    -PcoverageClasses="$COVERAGE_CLASS_DIRS" --stacktrace --console=plain
- uses: actions/upload-artifact@v4
  if: ${{ !cancelled() }}
  with:
    name: local-ui-debug-coverage
    retention-days: 14
    path: |
      app/build/reports/jacoco/
      app/build/test-results/testDebugUnitTest/
```

Define `COVERAGE_CLASS_DIRS` from the verified build outputs, not untrusted PR text.
The upload does not replace the verification task's failure.
Treat missing XML, no production classes, or failed tests as invalid coverage evidence.
Do not create empty placeholder reports for dashboards.

## Keep instrumentation isolated

Run coverage after establishing a normal passing suite.
Do not attach multiple agents or both plugin-managed and custom JaCoCo instrumentation
without understanding which agent owns the execution data.
Preserve ordinary noncoverage results when diagnosing a coverage-only failure.

Coverage does not synchronize external work.
Fresh fakes and deferred completions still belong to each test.
Use Compose clock control only for work that clock owns.
Cancel scopes and close resources even if agent instrumentation changes execution timing.
Do not benchmark test speed or device performance from the instrumented run.

## Avoid misleading metrics

| Anti-pattern | Failure mechanism | Correct approach |
| --- | --- | --- |
| Report only observed classes | Unvisited code disappears | Include the complete intended production class universe |
| Average shard percentages | Overlaps and denominators differ | Merge compatible execution data before calculating counters |
| Exclude every composable | Removes the behavior under test | Review generated-code policy narrowly |
| Use coverage as the UI assertion | Executed code can still render the wrong result | Assert observable state after the action |
| Count failed or skipped tests as success | Coverage can rise during a broken run | Require passing complete test evidence first |
| Copy an AGP task name from memory | Plugin versions expose different tasks | Discover and verify the exact task contract |

## Troubleshoot

| Symptom | Inspect | Fix |
| --- | --- | --- |
| Report task skips | Execution-data existence and task graph | Ensure the instrumented Test task actually ran |
| Empty application report | Class directories and package filter | Supply the real original production classes |
| Class does not match execution data | Class IDs and variant revision | Rebuild matching classes and data together |
| Coverage-only class loading failure | Agent compatibility and double instrumentation | Isolate the coverage configuration before changing UI tests |
| Lines do not map to Kotlin source | Source paths and generated bytecode | Correct source inputs and review compiler mapping limits |
| Threshold passes with no useful classes | Denominator and expected class inventory | Reject the evidence rather than lower the threshold |

## Review checklist

- Exact agent and plugin versions are recorded.
- The ordinary suite passes before coverage is trusted.
- The report includes unvisited production classes.
- Execution data matches the original class files and variant.
- Thresholds measure named counters over a reviewed denominator.
- All shards and test results are present.
- UI confidence still comes from observable assertions and negative checks.

## Related guides and sources

- [Reporting](reporting.md), [sharding](parallel-sharding.md), and [test speed](performance.md).
- [Behavior assertions](../references/behavior.md).
- [Gradle 9.4.1 JaCoCo plugin](https://docs.gradle.org/9.4.1/userguide/jacoco_plugin.html).
- [JaCoCo report task API](https://docs.gradle.org/9.4.1/dsl/org.gradle.testing.jacoco.tasks.JacocoReport.html).
- [JaCoCo class IDs](https://www.jacoco.org/jacoco/trunk/doc/classids.html).
- [Android local Robolectric tests](https://developer.android.com/training/testing/local-tests/robolectric).
