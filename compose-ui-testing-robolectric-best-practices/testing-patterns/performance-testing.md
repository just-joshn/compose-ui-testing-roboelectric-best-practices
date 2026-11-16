# Test performance contracts and measure Android performance

Use this guide to choose performance evidence, guard deterministic work limits locally, and hand real startup or frame-time claims to Android benchmarks. Robolectric is useful for behavior around loading and resource ownership. Its wall-clock duration and virtual Compose clock are not device performance measurements.

## Table of contents

- [Choose a metric and layer](#choose-a-metric-and-layer)
- [Guard local work budgets](#guard-local-work-budgets)
- [Test loading without measuring latency](#test-loading-without-measuring-latency)
- [Measure startup on Android](#measure-startup-on-android)
- [Measure frames, resources, and memory](#measure-frames-resources-and-memory)
- [Define budgets and baselines](#define-budgets-and-baselines)
- [Run performance checks in CI](#run-performance-checks-in-ci)
- [Avoid misleading measurements](#avoid-misleading-measurements)
- [Isolate and synchronize](#isolate-and-synchronize)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a metric and layer

There is no direct Compose equivalent of browser Web Vitals or Lighthouse. Choose an Android measure that matches the user's experience instead of renaming a browser metric.

| Question | Evidence | Keep out of the claim |
| --- | --- | --- |
| Does the screen show useful pending feedback? | Local Compose state transition test | Real latency |
| Does recomposition duplicate a request? | Local real state owner with a counting boundary fake | Frame smoothness |
| How long does cold startup take? | Macrobenchmark startup metrics on Android | Gradle or Robolectric startup |
| Is scrolling smooth? | Macrobenchmark frame timing and traces | Virtual frame count |
| Is a parser slower? | Isolated benchmark with representative input | Whole-screen user experience |
| Does navigation retain activities? | Android heap investigation after repeated navigation | A single JVM heap reading |
| Are downloads too large? | Transport byte accounting against a fixed dataset | Fake response size |
| Are users experiencing slow rendering? | Production telemetry with defined population and consent | A lab test for all users |

Define the operation, input, environment, and metric before running a benchmark. Missing metrics are failures of evidence, not zero-cost operations.

## Guard local work budgets

Deterministic counts can catch expensive behavior without pretending to measure milliseconds. Good candidates include duplicate network requests, image decode requests, retained subscriptions, and pagination calls.

The following illustrative test body assumes the real `SearchScreen` accepts a repository and offers a **Show filters** control. Its initial query is `compose`, and `repository.requests` records calls. Opening filters changes UI state without changing the query. The screen and fake are application-specific and are not compiled by this fixture.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Assert.assertEquals

compose.setContent { SearchScreen(repository = repository) }
compose.onNodeWithText("Results for compose").assertIsDisplayed()
compose.onNodeWithText("Show filters").performClick()
compose.onNodeWithText("Filter options").assertIsDisplayed()
compose.onNodeWithText("Results for compose").assertIsDisplayed()
compose.runOnIdle { assertEquals(listOf("compose"), repository.requests) }
```

Choose an unrelated action that previously caused duplicate loading. The UI assertions establish that the action ran and the results remain. The request count supplements them with a deterministic work budget.

Do not impose an exact recomposition count as a generic performance budget. Compiler and runtime changes can alter that count without changing user experience. Guard an expensive boundary call only when its allowed multiplicity is a real contract.

For resource cleanup, track active subscriptions in a fake, navigate away through the UI, and verify that the subscription closes. Also assert the visible destination. This proves local ownership behavior, not absence of all production memory leaks.

## Test loading without measuring latency

Use a controlled repository that remains pending. Trigger loading and assert the skeleton, progress indicator, or retained content. Complete the repository and assert the useful result.

If the product shows a delayed loading message, inject its time source or drive the scheduler that owns the delay. Assert before and after the deadline. The [canonical clock example](../examples/FixtureUiTest.kt) distinguishes Compose delay from external completion.

Do not measure this sequence with `System.nanoTime()` and label it app latency. The duration includes test synchronization, JVM warmup, Robolectric framework execution, and host load. Virtual time deliberately skips real waiting.

A test's timeout bounds a stuck workflow. It is not a performance service-level objective. Keep behavioral timeouts and benchmark budgets in separate configuration.

## Measure startup on Android

Create a dedicated Macrobenchmark module using Android Studio's benchmark setup or the official setup guide. Target a non-debuggable, profileable, release-like app variant. Declare the package under test and pin benchmark dependencies appropriate to the project.

The following illustrative instrumented test uses AndroidX Benchmark Macro JUnit4, AndroidX Test, and JUnit 4. It belongs in the benchmark module's `src/androidTest`, not the Robolectric fixture. Replace the application ID. This repository has not run it.

```kotlin
import androidx.benchmark.macro.CompilationMode
import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.StartupTimingMetric
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ColdStartupBenchmark {
	@get:Rule val benchmark = MacrobenchmarkRule()

	@Test fun coldStartup() {
		benchmark.measureRepeated(
			packageName = "com.example.app",
			metrics = listOf(StartupTimingMetric()),
			compilationMode = CompilationMode.None(),
			startupMode = StartupMode.COLD,
			iterations = 10,
			setupBlock = { pressHome() }
		) {
			startActivityAndWait()
		}
	}
}
```

The expected outputs are benchmark results and traces for repeated cold starts, not a fabricated threshold pass. `CompilationMode.None()` describes one compilation condition. Compare a separate partial-compilation case when testing Baseline Profiles. Keep compilation mode explicit in the result label.

For useful-content startup, define when the app reports fully drawn. AndroidX Activity provides Compose-aware reporting helpers. A first activity frame can precede loaded content. Configure and inspect the appropriate startup metric before interpreting a result as "ready to use".

Use a physical device for representative timing. An emulator can help validate benchmark wiring, but do not mix its measurements into a physical-device baseline.

## Measure frames, resources, and memory

For scrolling or animation, use a repeated Macrobenchmark scenario with `FrameTimingMetric` and a fixed dataset. Keep navigation and data setup outside the measured interaction when the metric is specifically scrolling. Verify that the intended list is present before measuring input.

A useful scenario definition names the destination, initial scroll position, dataset size, gesture sequence, and completion condition. Save a trace and confirm the measured interval contains the intended work. Do not accept a fast result caused by a failed gesture.

For pure expensive code, use Microbenchmark or a suitable isolated benchmark. Separate setup and data allocation from the measured operation unless those costs are part of the real operation. Consume results so the benchmark does not measure work optimized away.

For resource budgets:

- Count real transferred bytes at the transport boundary when network size matters.
- Inspect packaged artifact size for APK growth, with comparable build configuration.
- Test image dimensions and decoded memory expectations with representative images.
- Trace CPU and allocation behavior on Android when local counts suggest a regression.

For suspected memory growth, repeat the user workflow on Android, return to a defined state, and inspect retained objects and allocation traces. Distinguish caches with intentional bounds from leaked activities or listeners. A single heap snapshot after an arbitrary garbage collection is not a leak diagnosis.

## Define budgets and baselines

Give each budget a metric name, unit, scenario, environment, statistic, threshold, and owner. The following illustrative data shape is configuration, not measured evidence:

```json
{
  "scenario": "catalog-cold-start",
  "metric": "time-to-initial-display",
  "unit": "ms",
  "statistic": "median",
  "deviceClass": "team-reference-phone",
  "startupMode": "COLD",
  "compilationMode": "None",
  "baselineCommit": "replace-with-reviewed-commit",
  "maxRegressionRatio": 1.10
}
```

The ratio is an example policy, not an Android recommendation. Select an absolute user-facing limit and a relative regression policy using actual product requirements and observed run variance.

Use the same app variant, device, API, dataset, compilation mode, and benchmark version for baseline and treatment. Record temperature or throttling warnings, battery state, and background activity where the benchmark reports them.

Run repeated measurements and inspect the distribution. Do not compare one unusually fast treatment iteration with the baseline median. Predefine which statistic gates CI and how noisy results are investigated.

Require every expected metric. A conditional check such as "if the metric exists, compare it" makes missing measurements pass silently.

## Run performance checks in CI

Keep fast Robolectric behavioral checks in the regular PR path. Run device benchmarks on a controlled device pool on a schedule or for performance-sensitive changes.

Preserve these artifacts for each benchmark run:

- Commit and application artifact identity.
- Scenario and build configuration.
- Device and API identity.
- Compilation and startup mode.
- Raw samples, summary results, and traces.
- Baseline identity and budget verdict.

The following shell commands are illustrative task names for projects with `app` and `macrobenchmark` modules. Confirm the project's actual tasks first.

```bash
./gradlew :app:testDebugUnitTest
./gradlew :macrobenchmark:connectedBenchmarkAndroidTest
```

Publish artifacts even when the benchmark fails. Keep baseline promotion separate from verification. A pull request must not overwrite its baseline automatically to become green.

For production monitoring, use Android performance telemetry rather than Lighthouse. Define population and device segmentation so a change in user mix is not mistaken for a code regression.

## Avoid misleading measurements

Bad practice is advancing `mainClock` by 16 milliseconds and asserting a frame budget. Virtual advancement asks Compose to progress; it does not measure the CPU or GPU time required on a device.

Correct it by retaining the local animation-state assertion and moving frame timing to a Macrobenchmark interaction with trace evidence.

Do not measure debug builds as a substitute for release-like performance. Do not suppress benchmark configuration warnings without documenting the limitation. A performance result with invalid configuration needs investigation, not a larger threshold.

## Isolate and synchronize

Reset local counters and repositories per test. Cancel subscriptions and owned jobs. Avoid shared mutable budget state between test workers.

For benchmarks, reset scenario state deliberately. A cold start does not automatically imply cleared application data. Clear or seed data outside the measured block according to the scenario contract. Keep warm-cache and cold-cache experiments separate.

Do not globally drain Android loopers or external schedulers to make a benchmark ready. Use a readiness condition associated with the intended screen, and confirm that setup work stays outside the measured interval when required.

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Local UI test becomes slower | Host load, Gradle, test traces | Treat suite runtime separately from app performance |
| Startup suddenly looks much faster | Destination and trace interval | Confirm the app actually reached the intended state |
| Frame result is absent | Metric support and measured interaction | Fail missing evidence and repair the scenario |
| CI regression cannot reproduce | Device, compilation mode, data, and warnings | Align conditions before attributing the difference |
| Memory grows each iteration | Retained object owners | Identify leaked listeners, activities, or unbounded caches |
| Baseline changes every PR | Baseline promotion process | Require reviewed, independent baseline updates |

## Review checklist

- [ ] Every performance claim names a metric, unit, scenario, and environment.
- [ ] Robolectric behavior and device timing remain separate.
- [ ] The benchmark executes the intended interaction and preserves traces.
- [ ] Baseline and treatment use comparable conditions.
- [ ] Missing metrics fail rather than silently bypassing budgets.
- [ ] No speedup is claimed without repeated fresh measurements.

## Related guides and sources

- [Test execution performance](../infrastructure-ci-cd/performance.md) covers suite speed.
- [Clock control](../advanced/clock-control.md) covers virtual time.
- [Macrobenchmark overview](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview) describes device-level metrics.
- [Macrobenchmark setup](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview#setup) describes target configuration.
- [Microbenchmark](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview) describes isolated code measurement.
- [Measure Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/measure-baselineprofile) describes compilation-mode comparisons.
- [Evidence limits](../references/evidence.md) records that the canonical fixture does not measure performance.
