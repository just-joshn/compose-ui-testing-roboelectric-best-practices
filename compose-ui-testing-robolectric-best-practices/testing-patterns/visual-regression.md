# Visual Regression Testing

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Patterns](#patterns)
3. [Decision Guide](#decision-guide)
4. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
5. [Common Issues & Solutions](#common-issues--solutions)
6. [Related References](#related-references)
7. [Sources](#sources)

> **When to use**: Catching unintended visual changes (layout, colors, fonts, themes) that behavior assertions miss.
> **Honest gap**: No official Android or Robolectric page names a Robolectric screenshot-comparison library. Android says Robolectric "can take screenshots natively, but you need a third-party library to perform screenshot testing with it." This file does not name one. The only official comparison tool, Compose Preview Screenshot Testing, is host-side and Layoutlib-based, not Robolectric.

## Quick Reference

```kotlin
// Compose Preview Screenshot Testing (Layoutlib, src/screenshotTest, NOT Robolectric)
@PreviewTest
@Preview(showBackground = true)
@Composable
fun GreetingPreview() { MyApplicationTheme { Greeting("Android!") } }
```

```kotlin
// Robolectric native graphics + capture (comparison is on you)
@RunWith(AndroidJUnit4::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class ButtonScreenshotTest {
    @get:Rule val composeTestRule = createComposeRule()

    @Test
    fun capturesRoot() {
        composeTestRule.setContent { MyButton() }
        val image: ImageBitmap = composeTestRule.onRoot().captureToImage()
        // Compare `image` with your own reference-image tooling
    }
}
```

| Approach | Engine | Source set | Verified for Robolectric |
|---|---|---|---|
| Compose Preview Screenshot Testing | Layoutlib (host) | `screenshotTest` | No, not Robolectric |
| `captureToImage()` + `@GraphicsMode(NATIVE)` | Robolectric Native Graphics | `test` | Capture: yes per blog. Comparison tool: none named |
| Instrumented screenshot test | Device renderer | `androidTest` | N/A |

## Patterns

### Screenshot Test Workflow

**Use when**: Deciding whether screenshot tests fit your suite.

A screenshot test captures a UI and compares it with a previously approved "reference" or "golden" image. A failure is not always a bug, so the workflow differs from behavior tests: either fix the code, or approve the new image and replace the reference.

| Advantages | Disadvantages |
|---|---|
| Many assertions per test (colors, margins, sizes, fonts) | Reference PNGs pile up |
| Easier to write and maintain than an equivalent behavior test | Linux, Mac, Windows render slightly differently |
| Good at catching regressions across screen sizes | Slower than behavior tests |
| | One change can affect thousands of screenshots |

Android's guidance: screenshot testing is the recommended way to verify visual attributes in Compose UIs; use the term "screenshot testing", not "snapshot testing".

### Keeping the Count Down

**Use when**: Planning themes, font sizes, and screen sizes.

```kotlin
// Good: vary font scale on one theme; long-word reflow does not depend on theme
DeviceConfigurationOverride(DeviceConfigurationOverride.FontScale(1.5f)) { MyButton("Averyveryverylongword") }

// Bad: every theme x every font scale x every size for every component
```

Choose screenshots that give unique feedback. Android's example: for a custom button, don't cross light and dark themes with three font sizes; pick one theme.

### Compose Preview Screenshot Testing

**Use when**: Rendering static composables from `@Preview` states. It runs host-side with Layoutlib, not Robolectric.

The standalone `com.android.compose.screenshot` plugin is no longer maintained. Android recommends AGP test suites with AGP 9.5 or higher, which is marked experimental ("APIs and DSL syntax are subject to change").

```properties
# gradle.properties
android.experimental.enableScreenshotTest=true
android.experimental.testSuiteSupport=true
```

```kotlin
// module build.gradle.kts (AGP test suites, engine 0.0.1-alpha16)
android {
    testOptions {
        screenshotTests.create("screenshotTest") {
            engineVersion = "0.0.1-alpha16"
            targetVariants.add("demoDebug")
            dependencies {
                implementation(libs.androidx.compose.ui.tooling)
                implementation("com.android.tools.screenshot:screenshot-validation-api:0.0.1-alpha16")
            }
        }
    }
}
```

Place tests in `{module}/src/{suiteName}/kotlin/`. Annotate previews with `@PreviewTest` (`com.android.tools.screenshot.PreviewTest`). Requirements: AGP 9.5.0-alpha03+, engine 0.0.1-alpha16+, JDK 17+.

```bash
./gradlew updateScreenshotTestDefaultDemoDebugTestSuite   # generate references
./gradlew testScreenshotTestDefaultDemoDebugTestSuite     # compare
```

References land in `{module}/src/{suiteName}{Target}{Variant}/reference/`. The HTML report is at `{module}/build/reports/tests/{taskName}/index.html` and flags `Reference Image Missing`, `Image Size Mismatch`, or `Pixel Mismatch`.

Standalone plugin tasks (legacy): `updateDebugScreenshotTest`, `validateDebugScreenshotTest`; references in `src/screenshotTestDebug/reference`.

### Capturing Pixels on Robolectric

**Use when**: You want pixels from a Robolectric Compose test, for example to check how a component reacts to font sizes or themes. Android recommends Robolectric screenshots only "when the pixel accuracy is not critical", because different devices render slightly differently.

Facts from the sources:
- `@GraphicsMode(GraphicsMode.Mode.NATIVE)` uses graphics shadows backed by native Android graphics code. `LEGACY` uses no-op and fake shadows. Native graphics arrived in Robolectric 4.10, initially disabled by default; the 4.18 javadoc states no default, so set it explicitly.
- The Robolectric blog (2026-07-03) says Compose screenshot tests use Robolectric's native-graphics `PixelCopy` shadow.
- `SemanticsNodeInteraction.captureToImage(timeoutMillis)` is `@RequiresApi(26)`, returns an `ImageBitmap`, and waits up to 2000 ms by default for the draw pass.
- After `mainClock.advanceTimeBy(...)`, call `waitForIdle()` or `runOnIdle` before asserting rendering such as `captureToImage`.
- 4.12.2: to use HW rendering with `PixelCopy`, set the system property `robolectric.pixelCopyRenderMode=hardware`. 4.13 notes HW rendering down to Android P.
- 4.18 on SDK 33/34: `RuntimeShader` uniform setters forward to native, which "can change how Material ripples are drawn in screenshot tests". Temporary restore: `robolectric.runtimeShaderScalarUniform=false`.

```kotlin
@Test
fun animationMidpoint() {
    composeTestRule.mainClock.autoAdvance = false
    composeTestRule.setContent { AnimatedBox() }
    composeTestRule.mainClock.advanceTimeBy(50L)
    composeTestRule.waitForIdle()   // Good: finish the draw pass before capture
    composeTestRule.onRoot().captureToImage()
}
```

The animation docs compare with `captureToImage().assertAgainstGolden()` and state "`assertAgainGolden` needs to be implemented in your code." It is the docs' placeholder, not a library API. Do not call it without defining it.

### Platform Differences and Tolerance

**Use when**: Screenshots pass locally and fail on CI.

A Mac-recorded screenshot can break on a Linux CI machine. Even one platform drifts with library, OS, or hardware changes. Two options:
- **Tolerate small changes**: a percentage of modified pixels, a percentage of total pixel-value difference, or a smart differ for structural similarity. Risk: false positives hide real regressions.
- **Take screenshots on a server**: CI runs the tests, records new screenshots on failure, and commits them to the branch, so reviewers approve by merging.

Reference images: start in the repository but limit the count; options are Git, Git LFS, or a cloud service.

## Decision Guide

| Situation | Choice |
|---|---|
| Static component states, light setup | Compose Preview Screenshot Testing |
| Needs Robolectric features, bigger scope | Tool integrating with Robolectric Native Graphics (not named by official docs) |
| Checking behavior or state changes | Behavior test, see [component-testing.md](component-testing.md) |
| Pixel-perfect, system UI | Device test |
| Font scale, dark mode, size variations | `DeviceConfigurationOverride`, see [device-configuration.md](../advanced/device-configuration.md) |

## Anti-Patterns to Avoid

| Don't | Problem | Do Instead |
|---|---|---|
| Cross every theme x font size x screen size | Thousands of PNGs with little extra signal | Pick screenshots with unique feedback |
| Record references on Mac, verify on Linux CI | Platform rendering differences | Record on the same environment as verification, or tolerate small diffs |
| Call `assertAgainstGolden()` as if it exists | Docs placeholder, not an API | Use your own comparison tooling |
| Capture right after `advanceTimeBy` | Draw pass may not be done | `waitForIdle()` or `runOnIdle` first |
| Expect Layoutlib tool to run under Robolectric | It is a separate host-side engine | Use the `screenshotTest` source set for it |
| Rename a `@PreviewTest` function casually | Breaks the link to its reference images | Regenerate references after renaming |
| Rely on Robolectric pixels for pixel accuracy | Fidelity is lower than a real device | Use Robolectric where accuracy is not critical |

## Common Issues & Solutions

### Host-side screenshot task runs out of memory

**Fix**: Add `android.compose.screenshot.maxHeapSize=4g` to `gradle.properties`.

### captureToImage hangs or yields nothing on Robolectric

**Cause**: The 1.0.0-beta09 release notes (2021) listed no drawing on Robolectric, so `captureToImage()` awaited the next draw pass indefinitely. These notes predate Robolectric native graphics and are historical; verify on your versions.
**Fix**: Enable `@GraphicsMode(GraphicsMode.Mode.NATIVE)`, call `waitForIdle()` first, and lower `timeoutMillis` (1.13.0-alpha01+) so a hang fails fast.

### Ripples or shader output changed after upgrading Robolectric

**Fix**: See the `RuntimeShader` note above; the property is temporary.

### Screenshot test fails with no code change

**Cause**: Library, OS, or hardware change. **Fix**: Re-record on the CI environment or add tolerance.

## Related References

- [animations.md](animations.md) — driving the clock before a capture
- [clock-control.md](../advanced/clock-control.md) — `autoAdvance` and `advanceTimeBy`
- [runtime-modes.md](../core/runtime-modes.md) — `@GraphicsMode` and `@LooperMode`
- [device-configuration.md](../advanced/device-configuration.md) — font scale, dark mode, window size
- [test-architecture.md](../architecture/test-architecture.md) — Robolectric vs device tests

## Sources

- https://developer.android.com/training/testing/ui-tests/screenshot
- https://developer.android.com/studio/preview/compose-screenshot-testing
- https://developer.android.com/studio/preview/compose-screenshot-testing-with-testsuites
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/develop/ui/compose/animation/testing
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/GraphicsMode.html
- https://robolectric.org/upgrade_to_version_4/
- https://github.com/robolectric/robolectric/releases
