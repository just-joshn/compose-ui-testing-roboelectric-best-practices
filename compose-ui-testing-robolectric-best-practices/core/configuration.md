# Configure Android local Compose tests

Use this guide to add Robolectric-hosted Compose tests, diagnose host failures, or choose SDK and worker settings. This is an Android local-unit-test configuration, not Compose Desktop and not an instrumentation runner configuration.

## Contents

- [Inspect the existing build](#inspect-the-existing-build)
- [Choose the configuration boundary](#choose-the-configuration-boundary)
- [Wire dependencies and resources](#wire-dependencies-and-resources)
- [Establish one hosted test](#establish-one-hosted-test)
- [Choose an activity owner](#choose-an-activity-owner)
- [Configure environments and execution](#configure-environments-and-execution)
- [Keep timeouts and artifacts useful](#keep-timeouts-and-artifacts-useful)
- [Troubleshoot setup](#troubleshoot-setup)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Inspect the existing build

Record the module, variant, Gradle wrapper, Android Gradle Plugin, Kotlin setup, Compose compiler plugin, resolved Compose test version, Robolectric version, runtime SDK, and test-worker JDK before changing anything.

These illustrative commands assume an Android module named `app` with a debug variant:

```bash
./gradlew --version
./gradlew :app:tasks --all
./gradlew :app:dependencies --configuration debugUnitTestRuntimeClasspath
./gradlew :app:dependencyInsight \
  --configuration debugUnitTestRuntimeClasspath \
  --dependency ui-test-junit4
```

Use the module and configuration names your build actually generates. A successful dependency graph is not a passing activity-hosted test.

The repository fixture uses Gradle 9.4.1, AGP 9.2.0, Compose compiler plugin 2.2.10, BOM 2026.09.00, Compose UI 1.12.1, Robolectric 4.18, JUnit 4.13.2, and an API 35 runtime on JDK 17. These versions define one observed combination. They are not minimum versions or a migration requirement for other projects.

## Choose the configuration boundary

| Need | Configure | Avoid |
| --- | --- | --- |
| Android resources in local tests | `testOptions.unitTests.isIncludeAndroidResources` | `returnDefaultValues` as a repair |
| Default Compose host | `ui-test-manifest` in the tested variant | Assuming `createComposeRule` is activity-free |
| Real application activity | Its manifest declaration and Android rule | Adding a second content owner |
| A different Android API | `@Config(sdk = [...])` with a supported worker JDK | Confusing compile SDK with runtime SDK |
| A feature-specific qualifier | Narrow `@Config(qualifiers = ...)` | Changing every test's locale or dimensions |
| Repeated build settings | Existing convention plugin | A base test class with hidden mutable state |
| External service integration | Separate integration job and explicit configuration | Real secrets in deterministic UI tests |

## Wire dependencies and resources

This illustrative module-level Gradle Kotlin DSL fragment assumes the Android and Compose compiler plugins already exist. Preserve your project's plugin strategy and version catalog.

```kotlin
android {
	buildFeatures {
		compose = true
	}
	testOptions {
		unitTests.isIncludeAndroidResources = true
	}
}

dependencies {
	testImplementation(platform("androidx.compose:compose-bom:2026.09.00"))
	testImplementation("androidx.compose.ui:ui-test-junit4")
	testImplementation("androidx.compose.material3:material3")
	testImplementation("org.robolectric:robolectric:4.18")
	testImplementation("junit:junit:4.13.2")
	debugImplementation(platform("androidx.compose:compose-bom:2026.09.00"))
	debugImplementation("androidx.compose.ui:ui-test-manifest")
}
```

The explicit versions reproduce the fixture dependency choices. In a consuming project, align with its existing BOM and confirm its selected version before copying the v2 import.

Put local tests in `src/test/java` or `src/test/kotlin`, according to the project's configured source directories. Use `testImplementation`, not `androidTestImplementation`. Official Compose testing examples often target `src/androidTest`; adapt their source set and runner for Robolectric.

AGP 9 includes built-in Kotlin support. Do not add `org.jetbrains.kotlin.android` blindly to that setup. Older AGP builds may use the separate Kotlin Android plugin. Apply the Compose compiler plugin matching the project's Kotlin setup rather than guessing from the Compose UI version.

The BOM aligns Compose libraries. It does not select Robolectric, the Android plugin, or the worker JDK.

## Establish one hosted test

This complete illustrative file belongs in `app/src/test/kotlin/example/HostTest.kt`. It assumes the dependencies above and the debug host manifest.

```kotlin
package example

import androidx.compose.material3.Text
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class HostTest {
	@get:Rule val rule = createComposeRule()

	@Test fun hostsContent() {
		rule.setContent { Text("Hosted") }
		rule.onNodeWithText("Hosted").assertIsDisplayed()
	}
}
```

Run the exact test:

```bash
./gradlew :app:testDebugUnitTest --tests example.HostTest \
  --console=plain --rerun-tasks
```

Expect one executed passing test, not `NO-SOURCE`, an empty suite, or a skipped test. Inspect the JUnit XML as well as the process exit status.

In Compose 1.12.1 the factory lives in `androidx.compose.ui.test.junit4.v2`. The interfaces `ComposeTestRule` and `ComposeContentTestRule` remain in `androidx.compose.ui.test.junit4`. Do not invent a `v2.ComposeTestRule` import.

`onNode` is a provider member. `assertExists` and `assertDoesNotExist` are interaction members. Do not import them as top-level extensions. Convenience extensions such as `onNodeWithText` and `assertIsDisplayed` do need imports.

## Choose an activity owner

`createComposeRule()` launches a host and lets the test call `setContent`. Its manifest artifact declares `androidx.activity.ComponentActivity`.

For `createAndroidComposeRule<MainActivity>()`, import the factory from `androidx.compose.ui.test.junit4.v2`. Declare the activity in the appropriate manifest. If `MainActivity.onCreate` already calls `setContent`, drive that existing content. Do not call `rule.setContent` again.

If dependencies must exist before the activity starts, install them through an ordered outer rule or application test configuration. `@Before` runs after rule setup and can be too late for an automatically launched activity. See [fixtures and hooks](fixtures-hooks.md).

## Configure environments and execution

Pin a runtime SDK for reproducible local evidence. Expand the SDK matrix only for an Android behavior that needs that coverage. Robolectric 4.18 documents API 24 through 37. API 35 needs Java 17 minimum. API 36 and 37 need Java 21 minimum. Recheck the versioned compatibility table when upgrading.

The JDK running Gradle and its test workers is not the Kotlin bytecode target. Setting `jvmTarget = 17` does not launch a Java 17 worker.

Use `PAUSED` looper mode for the documented fixture behavior. It is also Robolectric's documented default. Do not switch to legacy mode to force an unrelated asynchronous test to pass.

For deterministic screen tests, inject flags, sessions, repositories, and business time locally. For a real service test, validate its URL and credentials at the integration boundary. Do not require `.env` or production accounts to run a semantics test.

Start with conservative worker parallelism. Increase workers only after checking memory use and state ownership. Namespace any disk files or external resources by run and worker. A Gradle worker is not a shared authenticated UI fixture.

## Keep timeouts and artifacts useful

Keep local runs free of automatic retries while diagnosing failures. A pass after retry does not remove the first failure's significance.

Archive test XML, HTML reports, exception output, selected variant, SDK, and worker JDK. Capture semantics trees for selection failures. JVM screenshot capture, if separately configured, does not certify device pixels.

Use a bounded `waitUntil` for external work. Do not introduce a global five-minute timeout to hide a fake that was never completed. The 1.13-only `ComposeUiTestConfig` is not part of the validated 1.12.1 API.

## Troubleshoot setup

| Symptom | First observation | Correction |
| --- | --- | --- |
| `Method ... not mocked` | Runner and test source set | Use a Robolectric-aware runner and local dependencies |
| Activity cannot resolve | Debug merged manifest and resource inclusion | Include resources and declare the actual host |
| Unsupported SDK | Robolectric version and `@Config` | Select a supported runtime SDK |
| Unsupported class-file version | Actual worker JDK | Run that SDK with its supported JDK |
| Unresolved v2 factory | Resolved `ui-test-junit4` version | Match the import to the artifact, not an online snippet |
| No tests run | Module, variant, method filter, runner | Require a nonempty report with the intended method |
| Failure only in release | Variant host and dependencies | Configure that variant explicitly or test the intended debug task |

Anti-patterns include enabling `unitTests.isReturnDefaultValues`, mixing Desktop test artifacts into Android, and upgrading the whole build merely to repair a selector. These hide or widen the original failure instead of diagnosing it.

## Review checklist

- The test uses the Android local source set and task.
- The runtime dependency graph is aligned.
- The activity has one content owner and a real manifest declaration.
- The selected SDK and actual worker JDK are compatible.
- One hosted behavior test executes without skips.
- Configuration changes are narrower than the symptom they repair.

## Related guides and sources

- [Modules and variants](modules-variants.md) covers matrices and task dependencies.
- [Setup reference](../references/setup.md) records fixture-specific setup facts.
- [Compose test setup](https://developer.android.com/develop/ui/compose/testing) documents dependencies and hosts.
- [Robolectric getting started](https://robolectric.org/getting-started/) documents local Android resources and the runner.
- [Robolectric compatibility](https://robolectric.org/compatibility_table/) lists SDK and JDK requirements.
- [Evidence](../references/evidence.md) explains known documentation contradictions and exact observed versions.
