# Runtime Modes

## Table of Contents

1. [Overview](#overview)
2. [Looper Mode](#looper-mode)
3. [Graphics Mode](#graphics-mode)
4. [SQLite and Other Native Modes](#sqlite-and-other-native-modes)
5. [What This Means for Compose Tests](#what-this-means-for-compose-tests)
6. [Known Limits](#known-limits)
7. [Common Issues & Solutions](#common-issues--solutions)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Related References](#related-references)
10. [Sources](#sources)

## Overview

Robolectric exposes a few annotations that choose how much of Android is real. Each can go on a package, class, or method.

| Annotation                    | Choices                                          | Default in 4.18                         |
| ----------------------------- | ------------------------------------------------ | --------------------------------------- |
| `@LooperMode`                 | `PAUSED`, `INSTRUMENTATION_TEST`, `LEGACY`       | `PAUSED`                                |
| `@GraphicsMode`               | `NATIVE`, `LEGACY`                               | Not stated in the 4.18 Javadoc (see below) |
| `@SQLiteMode` (deprecated)    | `NATIVE`, `LEGACY`                               | Native SQLite                           |

Robolectric.org has no Compose-specific page. No allowed page recommends a particular `@GraphicsMode` or `@Config` combination for Compose tests, so treat the settings below as per-need, not as a required recipe.

## Looper Mode

```kotlin
import org.robolectric.annotation.LooperMode

@RunWith(AndroidJUnit4::class)
@LooperMode(LooperMode.Mode.PAUSED)   // already the default in 4.18
class CheckoutScreenTest { /* ... */ }
```

| Mode                    | Behavior                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `PAUSED`                | Models real Looper behavior; tasks on the main `Looper` run only when idled           |
| `INSTRUMENTATION_TEST`  | Separate test thread distinct from the main looper thread                             |
| `LEGACY`                | Deprecated; "not supported on Android SDKs > Baklava"                                 |

Override globally with the `robolectric.looperMode` system property. The upgrade guide: "We strongly encourage you to use the `PAUSED` looper mode (which is the default)".

In `PAUSED` mode:

- Tests run on the main looper thread.
- Tasks posted to the main `Looper` are not executed automatically. Run them with `shadowOf(Looper.getMainLooper()).idle()`.
- `SystemClock` time is frozen; advance with `ShadowSystemClock.advanceBy(Duration)` or `ShadowLooper.idleFor(Duration)`.
- Each background `Looper` has its own thread and runs tasks asynchronously.
- `ActivityScenario`, `FragmentScenario`, and Espresso idle the main `Looper` for you.
- A failing test with unexecuted main-looper tasks gets a warning.

```kotlin
// Good: drain the main Looper before asserting on code that posts to a Handler
Handler(Looper.getMainLooper()).post { events.add("after") }
shadowOf(Looper.getMainLooper()).idle()
assertThat(events).containsExactly("before", "between", "after").inOrder()
```

Compose's own idling is separate from this; see [synchronization.md](synchronization.md).

## Graphics Mode

```kotlin
import org.robolectric.annotation.GraphicsMode

@RunWith(AndroidJUnit4::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class CardRenderingTest { /* ... */ }
```

| Mode      | Meaning                                                              |
| --------- | -------------------------------------------------------------------- |
| `NATIVE`  | Graphics shadows backed by native Android graphics code              |
| `LEGACY`  | "no-ops and fakes"                                                   |

Facts from the release notes:

- Native graphics was introduced in 4.10 "disabled by default" and enabled with `@GraphicsMode(NATIVE)`. The 4.18 Javadoc states no default and no later note changing it was found. Set the annotation explicitly when a test needs real rendering.
- 4.13: better hardware rendering support in Robolectric Native Graphics, supported down to Android P, and "increased compatibility with Compose's graphics layer".
- 4.12.2: to use hardware rendering with `PixelCopy`, set `robolectric.pixelCopyRenderMode=hardware`.
- 4.18: Linux arm64 gets a native runtime for native SQLite and `@GraphicsMode(NATIVE)`.
- 4.18 on SDK 33 and 34: `RuntimeShader` uniform setters forward to native, which "can change how Material ripples are drawn in screenshot tests". `robolectric.runtimeShaderScalarUniform=false` restores the old behavior temporarily.

```kotlin
// Good: native graphics only where rendered pixels matter
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Test fun themeColors_render() { /* capture and compare, see visual-regression.md */ }
```

The Robolectric 2026 blog says Compose screenshot tests use Robolectric's native-graphics `PixelCopy` shadow. Screenshot comparison is covered in [visual-regression.md](../testing-patterns/visual-regression.md).

## SQLite and Other Native Modes

- `SQLiteMode.Mode.NATIVE` is the default; per the upgrade guide "usages of these APIs can be removed". `@SQLiteMode` is `@Deprecated` and "will be deleted in a forthcoming Robolectric release". Legacy SQLite mode is unsupported on Linux arm64 and Apple silicon.
- 4.18 removed `@TextLayoutMode`: "Realistic text layout ... is now always used".
- 4.18 adds native resources (`ResourcesMode.NATIVE`) on SDK 36 and higher.

## What This Means for Compose Tests

- The 2026 Robolectric blog says Compose's JVM idling strategy forces layout "where there is no draw pass". `MainTestClock` drives recomposition, animations, and gestures, not Android's measure and draw passes; after advancing the clock, for rendering assertions (such as `captureToImage`) call `waitForIdle()` or `runOnIdle` after advancing the clock.
- For behavior tests (for example a Compose test verifying the UI changed after a click), the Android docs say Robolectric's fidelity is "more than enough". They do not say to set `@GraphicsMode` for them.
- Screenshots on Robolectric are lower fidelity: "different devices render screens slightly differently". The docs say to take them only when pixel accuracy is not critical, for example font size or theme reactions.
- Use `@Config(sdk = ...)` to pick the API level and JDK accordingly; see [configuration.md](configuration.md).

## Known Limits

The 1.0.0-beta09 Compose release notes listed limits that predate native graphics: no native bitmap (`ImageBitmap()` threw NPE), no drawing (`captureToImage()` deadlocked awaiting a draw pass), no loaded fonts so text measured incorrectly, and `waitUntil` not running the main thread while waiting. These are 2021-era notes. Verify against your versions before repeating them.

Per the API reference, `ComposeTestRule.enableAccessibilityChecks` "requires API 34+ and currently does not work on Robolectric". `captureToImage` is `@RequiresApi(26)`.

## Common Issues & Solutions

| Issue                                                        | Solution                                                         |
| ------------------------------------------------------------ | ---------------------------------------------------------------- |
| Handler-posted work has not run when asserting               | `shadowOf(Looper.getMainLooper()).idle()`                        |
| "Main looper has queued unexecuted runnables" failure        | Same; the work matters to the test                               |
| Rendering looks different after a Robolectric upgrade        | Check release notes (runtime shader, hardware rendering, `PixelCopy` mode) |
| Delayed work after animation never runs                      | `ShadowLooper.idleFor()` or `runToEndOfTasks()`                  |
| `LEGACY` looper fails on a new SDK                           | Move to `PAUSED`; `LEGACY` is unsupported above Baklava          |

## Anti-Patterns to Avoid

| Anti-Pattern                                   | Problem                                 | Solution                                        |
| ---------------------------------------------- | --------------------------------------- | ----------------------------------------------- |
| `@LooperMode(LEGACY)` in new tests             | Deprecated, runs tasks inline           | `PAUSED`                                        |
| `@SQLiteMode` annotations                      | Deprecated; native is default           | Remove                                          |
| Enabling `NATIVE` graphics for all behavior tests | Docs call default fidelity "more than enough" for behavior | Enable only where rendering is asserted |
| Treating Robolectric pixels as device pixels   | Lower fidelity                          | Use screenshot tests where pixel accuracy is not critical |

## Related References

- **Compose idling and the clock**: See [synchronization.md](synchronization.md)
- **`@Config` and JDK**: See [configuration.md](configuration.md)
- **Screenshots**: See [visual-regression.md](../testing-patterns/visual-regression.md)
- **Animations**: See [clock-control.md](../advanced/clock-control.md)

## Sources

- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/GraphicsMode.html
- https://robolectric.org/upgrade_to_version_4/
- https://robolectric.org/blog/2019/06/04/paused-looper/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
- https://robolectric.org/simulator/
- https://github.com/robolectric/robolectric/releases
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/jetpack/androidx/releases/compose-ui
