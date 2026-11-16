# Add visual regression checks to Compose tests

Use this guide when layout, typography, colors, clipping, or custom drawing can regress without changing semantics. Keep semantic behavior tests as the default. Add an optional screenshot workflow for pixels, and use Android device evidence for system UI or hardware rendering claims.

## Table of contents

- [Choose capture scope and environment](#choose-capture-scope-and-environment)
- [Set up a screenshot lane](#set-up-a-screenshot-lane)
- [Freeze inputs before capture](#freeze-inputs-before-capture)
- [Control animation and drawing](#control-animation-and-drawing)
- [Cover components and adaptive layouts](#cover-components-and-adaptive-layouts)
- [Choose comparison tolerances](#choose-comparison-tolerances)
- [Run comparisons in CI](#run-comparisons-in-ci)
- [Review and update baselines](#review-and-update-baselines)
- [Avoid visual false greens](#avoid-visual-false-greens)
- [Isolate and synchronize](#isolate-and-synchronize)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose capture scope and environment

| Goal | Capture strategy | Limit |
| --- | --- | --- |
| Button or card appearance | Small component with real theme | Does not prove screen placement |
| Important screen spacing | Fixed-size host with a bounded dataset | Offscreen lazy content is not automatically included |
| Long list item variants | Selected representative item states | Not an infinite full-list screenshot |
| Chart shape or selection marker | Chart region plus relevant labels | Renderer-specific pixels |
| Dialog appearance | Capture the intended root with compatible tooling | A root capture may omit other windows |
| Status bars, IME, edge-to-edge | Installed-app Android screenshot | Device, API, and configuration specific |
| GPU, video, external surfaces | Renderer-aware or device capture | A semantics node around a surface can be blank |

JVM screenshot tools and device screenshots serve different claims. A consistent Robolectric renderer can detect visual regressions without being pixel-identical to a device. A device capture can cover real composition with system UI, but still represents only its tested hardware and configuration.

## Set up a screenshot lane

Keep screenshots optional and separate from semantic tests. This worked integration uses **Roborazzi 1.29.0**, not an unspecified capture adapter. Its tagged README and sources define `captureRoboImage`, comparison options, and record, compare, and verify tasks.

The example is illustrative and source-checked, not screenshot-validated by this repository's canonical fixture. It targets the `debug` variant of an Android library module named `app`, Gradle 8.9, JDK 17, AGP 8.6.1, Kotlin 1.9.22, Compose compiler 1.5.10, Compose UI 1.6.8, Material3 1.2.1, and Robolectric 4.12.2. These match the tagged upstream build's toolchain and component versions. The example pins all Compose UI artifacts to 1.6.8 rather than copying upstream's mixed versions. This is not a compatibility promise for AGP 9.2 or Compose UI 1.12.1 in the canonical fixture. Do not downgrade an existing application to copy this example. Validate a compatible screenshot-tool version separately when adopting it there.

Supply an Android project with a Gradle 8.9 wrapper, JDK 17, and Android SDK platform 34. Set `ANDROID_HOME` to that SDK. Add these entries to the root `gradle.properties`:

```properties
android.useAndroidX=true
org.gradle.jvmargs=-Xmx4g
```

In `settings.gradle.kts`, configure plugin and dependency repositories and include the module:

```kotlin
pluginManagement {
	repositories {
		google()
		mavenCentral()
		gradlePluginPortal()
	}
}
dependencyResolutionManagement {
	repositories {
		google()
		mavenCentral()
	}
}
rootProject.name = "visual-example"
include(":app")
```

Declare the plugins in the root `build.gradle.kts`:

```kotlin
plugins {
	id("com.android.library") version "8.6.1" apply false
	id("org.jetbrains.kotlin.android") version "1.9.22" apply false
	id("io.github.takahirom.roborazzi") version "1.29.0" apply false
}
```

Use this complete `app/build.gradle.kts` for the isolated example:

```kotlin
plugins {
	id("com.android.library")
	id("org.jetbrains.kotlin.android")
	id("io.github.takahirom.roborazzi")
}

android {
	namespace = "com.example.visual"
	compileSdk = 34
	defaultConfig { minSdk = 23 }
	buildFeatures { compose = true }
	composeOptions { kotlinCompilerExtensionVersion = "1.5.10" }
	testOptions { unitTests.isIncludeAndroidResources = true }
	compileOptions {
		sourceCompatibility = JavaVersion.VERSION_17
		targetCompatibility = JavaVersion.VERSION_17
	}
}
kotlin { jvmToolchain(17) }

roborazzi {
	outputDir.set(layout.projectDirectory.dir("src/test/screenshots"))
}

dependencies {
	implementation("androidx.activity:activity-compose:1.7.2")
	implementation("androidx.compose.ui:ui:1.6.8")
	implementation("androidx.compose.foundation:foundation:1.6.8")
	implementation("androidx.compose.material3:material3:1.2.1")
	testImplementation("junit:junit:4.13.2")
	testImplementation("org.robolectric:robolectric:4.12.2")
	testImplementation("androidx.compose.ui:ui-test-junit4:1.6.8")
	testImplementation("io.github.takahirom.roborazzi:roborazzi:1.29.0")
	testImplementation("io.github.takahirom.roborazzi:roborazzi-compose:1.29.0")
	debugImplementation("androidx.compose.ui:ui-test-manifest:1.6.8")
}
```

Add `app/src/main/AndroidManifest.xml` with `<manifest />`. The `ui-test-manifest` debug dependency supplies the `ComponentActivity` host for `createComposeRule()`. This older version uses `androidx.compose.ui.test.junit4.createComposeRule`, not the canonical fixture's v2 factory. Do not combine their imports.

Android resource inclusion and `@GraphicsMode(NATIVE)` in the test are required for this workflow. Robolectric native graphics loads native rendering libraries on the host. Use a supported host OS and architecture, and make the Robolectric runtime artifacts available through your dependency cache or network. A missing native library is a setup failure, not an acceptable blank baseline. No Roborazzi JUnit rule is required for explicit captures.

## Freeze inputs before capture

Prefer deterministic input over hiding volatile regions. Inject fixed time, seeded data, stable images, and a known locale into the real component.

Control these inputs explicitly:

- Width and height, with units and density.
- Font scale and actual font files.
- Light or dark theme and dynamic color policy.
- Locale, layout direction, and time zone where relevant.
- Dataset, ordering, user identity, and feature flags.
- Image bytes and loading completion.
- Time, random seed, and animation state.
- SDK, renderer mode, and screenshot tool version.

A fixed clock used by the app is different from `mainClock`. A date string generated by `Instant.now()` will still vary when Compose virtual time is paused.

Put this complete illustrative test in `app/src/test/java/com/example/visual/ReportCardVisualTest.kt`. The data shape is one fixed report card. The test mounts it, asserts its visible content, and captures the tagged component. The Gradle task chooses whether that same capture records or verifies.

```kotlin
package com.example.visual

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.unit.dp
import com.github.takahirom.roborazzi.RoborazziOptions
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [33], qualifiers = "en-rUS-w360dp-h640dp-notnight-mdpi")
class ReportCardVisualTest {
	@get:Rule
	val compose = createComposeRule()

	@Test
	fun fixedReportCard() {
		compose.setContent {
			MaterialTheme(colorScheme = lightColorScheme()) {
				Surface(Modifier.width(320.dp).testTag("report-card")) {
					Column(Modifier.padding(16.dp)) {
						Text("Quarterly report")
						Text("Updated Jan 1, 2026")
						Text("12 documents ready")
					}
				}
			}
		}
		compose.onNodeWithText("12 documents ready").assertIsDisplayed()
		compose.onNodeWithTag("report-card").captureRoboImage(
			filePath = "src/test/screenshots/report-card_light_320dp_api33.png",
			roborazziOptions = RoborazziOptions(
				compareOptions = RoborazziOptions.CompareOptions(
					outputDirectoryPath = "build/outputs/roborazzi",
					changeThreshold = 0F,
				),
			),
		)
	}
}
```

Run the tasks from the project root. Explicit paths in the test resolve from the `app` module. Record creates `app/src/test/screenshots/report-card_light_320dp_api33.png`. Verify compares the newly captured pixels with that baseline. On a changed image, it writes `report-card_light_320dp_api33_actual.png` and `report-card_light_320dp_api33_compare.png` under `app/build/outputs/roborazzi/`, then fails. The compare image is the tool's visual comparison, not another baseline. JSON results go to `app/build/test-results/roborazzi/`, and the HTML report is `app/build/reports/roborazzi/index.html`.

Create and inspect the first baseline, then verify it:

```bash
./gradlew :app:recordRoborazziDebug --rerun-tasks
./gradlew :app:verifyRoborazziDebug --rerun-tasks
```

Before adoption, change `16.dp` padding to `24.dp` without recording. Run `:app:verifyRoborazziDebug --rerun-tasks` and require a nonzero exit with an inspectable actual and compare image. Restore `16.dp` and require verification to pass. This mutation checks that your configured lane detects pixels rather than merely running semantic assertions.

Use the actual app theme when the goal is product appearance. A default theme can miss custom typography, shapes, and color regressions.

If masking is unavoidable, use the selected tool's documented mask support and verify the mask's exact region. Masking a whole card to hide its avatar also hides clipping, labels, and spacing. Do not imply that Compose has Playwright's `mask` option.

Avoid replacing text inside the rendered tree after layout. Supply fixed state through the normal component inputs so line wrapping and measurement remain realistic.

## Control animation and drawing

For settled-state captures, keep ordinary synchronization and wait for known data readiness. For a chosen intermediate animation frame, disable automatic clock advancement before starting the transition and advance deliberately.

The following illustrative timing fragment assumes `AnimatedReport` is an application component and `expanded` is a fresh `MutableState<Boolean>` created before mounting. It uses the same Roborazzi setup as the complete test above.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithTag
import com.github.takahirom.roborazzi.captureRoboImage

compose.mainClock.autoAdvance = false
compose.setContent { AnimatedReport(expanded = expanded.value) }
compose.mainClock.advanceTimeByFrame()
compose.runOnIdle { expanded.value = true }
compose.mainClock.advanceTimeByFrame()
compose.mainClock.advanceTimeBy(160)
compose.waitForIdle()
compose.onNodeWithTag("report-card").assertIsDisplayed()
compose.onNodeWithTag("report-card").captureRoboImage(
	"src/test/screenshots/report-card_expanding_160ms_api33.png",
)
```

Use this fragment inside a test with the rule, runner, native graphics, and supported SDK shown above. The fragment establishes a controlled point in Compose time, not measured 160-millisecond device latency. This capture uses default comparison-output options. The complete static test above shows how to separate comparison artifacts from tracked baselines.

Finite animations may require a start frame before elapsed time represents animation progress. Infinite animations need an explicit captured phase or deterministic disabled policy. Document that policy per scenario rather than expecting a browser-style global animation option.

Clock advancement does not by itself establish Android drawing. Synchronize pending layout and draw through the test environment and the screenshot tool's documented capture path. External image loading and GPU rendering require their own readiness signals.

## Cover components and adaptive layouts

Start with high-risk components and states:

| Component | Useful variants |
| --- | --- |
| Action button | Enabled, disabled, loading, long label |
| Document card | Short and long names, missing thumbnail, error |
| Form | Empty, entered value, validation error, large font |
| Chart | Empty, populated, selected, dark theme |
| Dialog | Long content, destructive action, constrained height |

Use one fresh mounted scenario per independent state unless the transition itself is the visual contract. Keep the actual theme and meaningful parent constraints.

For adaptive layouts, choose representative widths on both sides of the application's decision boundary. Add font-scale and right-to-left cases where layout risk warrants them. Avoid multiplying every locale by every width and every state without a product reason.

Store configuration in the baseline identity. For example, distinguish `document-card_long-name_dark_320dp_font1.3` from the same card at normal font scale. The exact naming scheme is local policy, but collisions must be impossible.

For scrolling content, capture bounded viewport states or dedicated item fixtures. Lazy containers may not compose offscreen items. Do not describe a root screenshot as a browser-style full-page capture. If a tool stitches scroll states, verify its treatment of sticky headers and lazy loading.

For cross-environment coverage, keep separate baselines where renderer or API differences are expected. Do not compare host-rendered and device-rendered pixels against one common golden file without evidence that the comparison is meaningful.

## Choose comparison tolerances

Distinguish per-pixel color distance, changed-pixel count, and changed-pixel ratio. In Roborazzi 1.29.0, `CompareOptions(changeThreshold = 0F)` allows zero changed-pixel ratio under its image comparator. The default comparator is `SimpleImageComparator(maxDistance = 0.007F)`. Therefore, zero `changeThreshold` does not mean byte-identical PNGs or zero color-distance tolerance.

For strict pixel comparison in this pinned version, add the following import at the top of the test file:

```kotlin
import com.dropbox.differ.SimpleImageComparator
```

Then replace the test's `CompareOptions` with this configuration. The comparator is available through Roborazzi's transitive dependency.

```kotlin
RoborazziOptions.CompareOptions(
	outputDirectoryPath = "build/outputs/roborazzi",
	changeThreshold = 0F,
	imageComparator = SimpleImageComparator(maxDistance = 0F),
)
```

To allow a justified changed-pixel ratio, set `changeThreshold = 0.001F` for that capture. This permits 0.1 percent of pixels under the selected comparator, not an absolute count of pixels. Do not copy Playwright's `threshold` or `maxDiffPixels` names into Roborazzi configuration.

Start with reproducible rendering before adding tolerance. Compare repeated captures of an unchanged component in the verification environment. Inspect the differences and identify their cause.

A changed-pixel ratio can hide a missing small icon on a large screen. A per-pixel tolerance can hide low-contrast text changes. Prefer a smaller capture region when a small visual feature matters.

Use tighter comparison for deterministic assets when the renderer is stable. Permit narrowly justified variance for anti-aliasing only after inspecting actual diffs. Do not apply a broad percentage to every test merely to stop failures.

Keep semantic assertions alongside images. A screenshot can look correct while a button is disabled, has no click action, or exposes the wrong accessibility label.

## Run comparisons in CI

Generate and verify baselines in the same controlled environment. Pin the JDK, SDK, Robolectric, Compose, screenshot tool, renderer settings, fonts, and locale that affect output. Record the operating system when the renderer depends on it.

Do not assume that a container alone makes screenshots identical. Dependency versions, fonts, native rendering libraries, and host architecture can still differ. Use the project's existing reproducible environment rather than copying an unrelated browser container.

Keep three operations separate in CI:

1. Verify current output against tracked baselines.
2. Preserve expected, actual, and diff images on failure.
3. Generate candidate baselines only through an explicit review workflow.

Do not run a recording task in place of verification. A recording job can overwrite expected output and turn every visual regression green.

Use a failure artifact path unique to test, scenario, configuration, and worker. Keep images free of private user content. Publish the tool's comparison report when available.

These are actual tasks registered by the Roborazzi 1.29.0 plugin for the example's debug variant. Invoke them separately so recording cannot change the baseline before verification:

```bash
./gradlew :app:verifyRoborazziDebug --rerun-tasks
./gradlew :app:compareRoborazziDebug --rerun-tasks
```

`verifyRoborazziDebug` fails on a missing or changed baseline. `compareRoborazziDebug` generates review artifacts without failing for pixel differences. It is not the CI acceptance gate. Neither command records baselines. Do not use `verifyAndRecordRoborazziDebug` for pull-request verification, because it can overwrite baselines.

For a focused run, pass `--tests` to the actual Gradle `Test` task and set the plugin's documented verify property:

```bash
./gradlew :app:testDebugUnitTest \
	--tests 'com.example.visual.ReportCardVisualTest' \
	-Proborazzi.test.verify=true --rerun-tasks
```

The following illustrative GitHub Actions workflow assumes the example project, checked-in wrapper, reviewed baselines, and Android SDK setup. Generate baselines on this same OS and architecture. `ubuntu-22.04` selects the runner family, not an immutable system image. For stricter reproducibility, use your own pinned runner image and retain its identity with the baselines.

```yaml
name: Visual checks
on: [push, pull_request]
jobs:
  visual:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: android-actions/setup-android@v3
      - run: sdkmanager 'platforms;android-34' 'build-tools;34.0.0'
      - name: Verify reviewed baselines
        run: ./gradlew :app:verifyRoborazziDebug --rerun-tasks --stacktrace
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: visual-debug
          path: |
            app/src/test/screenshots/
            app/build/outputs/roborazzi/
            app/build/reports/roborazzi/
            app/build/reports/tests/testDebugUnitTest/
            app/build/test-results/
          retention-days: 14
```

Do not set `roborazzi.test.record=true` in project or user `gradle.properties`, CI environment options, or the test's `RoborazziOptions`. A plain semantic test run does not enable screenshot verification. Require the explicit verify task and check that the intended screenshot tests actually ran.

## Review and update baselines

Update only when the visual change is intended:

1. Run verification and open expected, actual, and diff images side by side.
2. Confirm that the rendered scenario, data, and configuration are correct.
3. Explain the intended change in the review description.
4. Generate candidates using the same environment as CI.
5. Inspect every changed baseline and remove unrelated candidates.
6. Run verification again against the reviewed baselines.

Review text wrapping, clipping, alignment, contrast, and missing assets, not only the highlighted diff region. A theme update can legitimately affect many images, but each new result still needs inspection.

Do not generate baselines from a failed load state. Assert the intended content before capture so a missing image or network error cannot silently become the new expected appearance.

For this pinned example, use a focused record command only after reviewing the failed comparison:

```bash
./gradlew :app:testDebugUnitTest \
	--tests 'com.example.visual.ReportCardVisualTest' \
	-Proborazzi.test.record=true --rerun-tasks
git diff --name-only -- app/src/test/screenshots/
./gradlew :app:verifyRoborazziDebug --rerun-tasks
```

Track `app/src/test/screenshots/*.png`, not the generated `*_actual.png` or `*_compare.png` files in `build/`. Open the PNGs with an image viewer or the Roborazzi HTML report before committing. Git's file list alone cannot establish that a visual update is correct.

When dependencies or renderer versions change, treat baseline migration as its own reviewable change. Record whether the diff comes from an intentional product change or a rendering-environment change.

## Avoid visual false greens

Bad practice is raising the allowed difference until an unexplained failure passes. That can hide a missing label or selection marker.

Correct it by inspecting the diff, stabilizing the source of nondeterminism, and narrowing capture scope before adjusting tolerance. Keep any accepted variance specific to the affected scenario.

Do not replace interaction tests with screenshots. An image does not establish that **Upload** starts a transfer or that a dialog confirmation saves a document. Preserve user actions and resulting semantics assertions.

## Isolate and synchronize

Create fresh state, fixed data, and output paths per scenario. Avoid shared image caches that make one test depend on another's preloading. Cancel owned loading and animation work after capture.

Set clock policy before triggering animation. Complete external fakes explicitly. Register any capture-specific resources before the operation and release them during cleanup.

Run suspect scenarios alone and within their class to expose leaked theme, locale, state, or clock configuration. Do not enforce test order to compensate for leaks.

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Text differs only in CI | Fonts, locale, renderer, JDK, and dependency versions | Align generation and verification environments |
| Blank GPU or video area | Capture support and renderer readiness | Use renderer-aware capture or Android device evidence |
| Random intermediate frame | Animation start and clock policy | Capture a defined frame or settled state |
| Small missing icon passes | Capture size and difference threshold | Narrow the region and tighten the relevant comparison |
| Dialog is missing | Root and window capture behavior | Select a compatible multi-window capture workflow |
| Golden filenames collide | Scenario and configuration identity | Include unique configuration dimensions |
| Snapshot count grows without useful coverage | State matrix and risk | Keep representative high-risk variants |
| Baselines update on every verification | Task semantics | Separate record and verify operations |

## Review checklist

- [ ] Every baseline identifies scenario, state, and renderer configuration.
- [ ] Deterministic content enters through normal component inputs.
- [ ] Animation, external work, and drawing readiness are explicit.
- [ ] The comparator detects an intentional visual mutation.
- [ ] CI preserves expected, actual, and diff artifacts.
- [ ] Baseline changes require inspection rather than automatic promotion.
- [ ] Device fidelity claims have separate Android evidence.

## Related guides and sources

- [Custom drawing](custom-drawing.md) covers charts and GPU boundaries.
- [Adaptive layouts](../advanced/adaptive-layouts.md) covers configuration decisions.
- [Component testing](component-testing.md) covers isolated mounted scenarios.
- [Roborazzi 1.29.0 README](https://github.com/takahirom/roborazzi/blob/1.29.0/README.md) documents setup, native graphics, capture, and task semantics.
- [Versioned Gradle plugin](https://github.com/takahirom/roborazzi/blob/1.29.0/include-build/roborazzi-gradle-plugin/src/main/java/io/github/takahirom/roborazzi/RoborazziPlugin.kt) defines task names and `outputDir`.
- [Versioned capture implementation](https://github.com/takahirom/roborazzi/blob/1.29.0/roborazzi/src/main/java/com/github/takahirom/roborazzi/Roborazzi.kt) defines the semantics-node extension.
- [Versioned comparison options](https://github.com/takahirom/roborazzi/blob/1.29.0/include-build/roborazzi-core/src/commonJvmMain/kotlin/com/github/takahirom/roborazzi/RoborazziOptions.kt) defines comparator defaults and changed-pixel ratio configuration.
- [Versioned sample build](https://github.com/takahirom/roborazzi/blob/1.29.0/sample-android/build.gradle) and [version catalog](https://github.com/takahirom/roborazzi/blob/1.29.0/gradle/libs.versions.toml) ground the example's older toolchain assumptions.
- [Screenshot testing](https://developer.android.com/training/testing/other-components/screenshot) describes Android screenshot strategies.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) describes animation control and pending drawing.
- [Robolectric graphics](https://robolectric.org/graphics/) describes graphics modes and their constraints.
- [Evidence limits](../references/evidence.md) states that the canonical fixture validates neither screenshot tooling nor device pixels.
