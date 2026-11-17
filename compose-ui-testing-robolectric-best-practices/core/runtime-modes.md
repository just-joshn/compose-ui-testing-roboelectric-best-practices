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

| Annotation | Applies to | Javadoc description (4.18) |
| --- | --- | --- |
| `@LooperMode` | `PACKAGE`, `TYPE`, `METHOD` | A Configurer annotation for controlling Robolectric's Looper behavior. |
| `@GraphicsMode` | `PACKAGE`, `TYPE`, `METHOD` | A Configurer annotation for controlling which graphics shadow implementation is used for the android.graphics package. |
| `@SQLiteMode` (deprecated) | `PACKAGE`, `TYPE`, `METHOD` | A Configurer annotation for controlling which SQLite shadow implementation is used for the android.database package. This annotation will be deleted in a forthcoming Robolectric release. |

## Looper Mode

Currently Robolectric will default to `LooperMode.Mode.PAUSED` behavior, but this can be overridden by applying a `@LooperMode(NewMode)` annotation to a test package, test class, or test method, or via the `robolectric.looperMode` system property.

| Mode | Javadoc description |
| --- | --- |
| `PAUSED` | A mode that more accurately models real Android's Looper behavior. |
| `INSTRUMENTATION_TEST` | A mode that simulates an android instrumentation test threading model, which has a separate test thread distinct from the main looper thread. |
| `LEGACY` | Deprecated: use `LooperMode.PAUSED`. `LEGACY` mode is not supported on Android SDKs > Baklava. |

The upgrade guide's entries for deprecated APIs such as `Robolectric#getForegroundThreadScheduler()` say: "This is only needed in the LEGACY looper mode. We strongly encourage you to use the PAUSED looper mode (which is the default)".

The Robolectric blog post "Improving Robolectric's Looper simulation" (2019) lists these highlights of the `PAUSED` mode compared with the `LEGACY` mode:

- Tasks posted to the main Looper are not automatically executed inline.
- Robolectric will warn users if a test fails with unexecuted tasks in the main Looper queue. This is a hint that the unexecuted behavior is important for the test case.
- AndroidX Test APIs, like `ActivityScenario`, `FragmentScenario` and Espresso will automatically idle the main Looper.
- Tasks posted to background Loopers are executed in real threads.

The same post says: if you see test failures like `Main looper has queued unexecuted runnables`, you may need to insert `shadowOf(getMainLooper()).idle()` calls to your test to drain the main Looper.

```java
import static android.os.Looper.getMainLooper;
import static org.robolectric.annotation.LooperMode.Mode.PAUSED;
import static org.robolectric.Shadows.shadowOf;
import org.robolectric.annotation.LooperMode;

@RunWith(AndroidJUnit4.class)
@LooperMode(PAUSED)
public class MyTest {
  @Test
  public void testCodeThatPosts() {
    List<String> events = new ArrayList<>();
    events.add("before");
    new Handler(Looper.getMainLooper()).post(() -> events.add("after"));
    events.add("between");
    // the 'after' task is posted, but has not been executed yet
    assertThat(events).containsExactly("before", "between").inOrder();
    // execute all tasks posted to main Looper
    shadowOf(getMainLooper()).idle();
    assertThat(events).containsExactly("before", "between", "after").inOrder();
  }
}
```

The same post says under Animations: Use of Animations can cause delayed tasks to be posted to the main Looper queue. You can use the `ShadowLooper.idleFor()` or `ShadowLooper.runToEndOfTasks()` APIs to execute these tasks.

## Graphics Mode

| Mode | Javadoc description |
| --- | --- |
| `NATIVE` | Use graphics shadows libraries backed by native Android graphics code. |
| `LEGACY` | Use legacy graphics shadows that are no-ops and fakes. |

The Robolectric 4.10 release notes (the release that added native graphics) say native graphics "can be enabled using `@GraphicsMode(NATIVE)`. When native graphics is enabled, interactions with Android graphics classes use real native Android graphics code and are much higher fidelity."

- 4.13: Better support for HW rendering in Robolectric Native Graphics (RNG). HW rendering is now supported all the way down to Android P. Increased compatibility with Compose's graphics layer.
- 4.12.2: In order to use HW rendering with PixelCopy, you must set the `robolectric.pixelCopyRenderMode=hardware` system property.
- 4.18: Robolectric's native runtime now includes Linux arm64 (aarch64) native libraries, so tests that use native SQLite (the default) and native graphics (`@GraphicsMode(NATIVE)`) can run on Linux arm64 environments.

## SQLite and Other Native Modes

- `SQLiteMode.Mode.NATIVE` is the default mode and does not need to be stated explicitly. `SQLiteMode.Mode.LEGACY` is obsolete and will be removed soon.
- The upgrade guide for 4.17 says: SQLiteMode.Mode.NATIVE is now the default, and usages of these APIs can be removed.
- 4.18: As on Apple silicon, the legacy SQLite mode (`SQLiteMode.Mode.LEGACY`) isn't supported on Linux arm64.
- 4.18: `@TextLayoutMode` has been removed. Realistic text layout, the default since 2019, is now always used.
- 4.18: Native resources (`ResourcesMode.NATIVE`) now work on SDK 36 and above, not only SDK 36.

## What This Means for Compose Tests

The Robolectric blog post "Designing Robolectric-based local-testing libraries for platforms and modules" describes itself as "an outside read of the code as it stands in mid-2026, not an official AndroidX position".

- The post says the same `createAndroidComposeRule<ComponentActivity>()` / `runComposeUiTest { }` code runs on a device and on the JVM from one binary, with no Robolectric-specific source set.
- The post says the only runtime detection is a single fingerprint check, and that boolean swaps one internal `IdlingStrategy` (Espresso on device; a main-thread loop that pumps Compose and forces layout on the JVM, where there is no draw pass). Frames come from a virtual-time test clock rather than a real Choreographer, and screenshot tests use Robolectric's native-graphics `PixelCopy` shadow.
- The post's table says what Robolectric does for Compose UI: JVM Looper plus native-graphics shadows for rendering and PixelCopy screenshots.
- The `MainTestClock` reference says that on Android only measure and layout are performed synchronously, and that the draw pass on Android is driven by the Choreographer and will not happen as a result of forwarding this clock.
- The `MainTestClock` reference also says that if you want to assert anything related to rendering (for example `SemanticsNodeInteraction.captureToImage`) after advancing the clock, you will need a call to `ComposeTestRule.waitForIdle` or `ComposeTestRule.runOnIdle` to make sure that any triggered draw pass has been completed.
- The Android Robolectric page says you can run other UI tests with Robolectric, such as screenshot tests. However the fidelity is lower as different devices render screens slightly differently.
- The Android Robolectric page recommends using Robolectric to take screenshots when the pixel accuracy is not critical, for example to test how a component reacts to different font sizes or themes.
- Robolectric can take screenshots natively, but you need a third-party library to perform screenshot testing with it.

## Known Limits

- `ComposeTestRule.enableAccessibilityChecks`: "This requires API 34+ (Android U), and currently does not work on Robolectric."
- `ComposeUiTest.enableAccessibilityChecks`: "Requires API 34+ (Android U) and is not supported on Robolectric."

## Common Issues & Solutions

| Issue | Solution |
| --- | --- |
| Test failures like `Main looper has queued unexecuted runnables`. | The 2019 Looper blog post says you may need to insert `shadowOf(getMainLooper()).idle()` calls to your test to drain the main Looper. |
| Use of animations can cause delayed tasks to be posted to the main Looper queue. | The 2019 Looper blog post says you can use the `ShadowLooper.idleFor()` or `ShadowLooper.runToEndOfTasks()` APIs to execute these tasks. |
| `LEGACY` looper mode on a newer SDK. | `LEGACY` mode is not supported on Android SDKs > Baklava; use `LooperMode.PAUSED`. |
| Using hardware rendering with `PixelCopy`. | You must set the `robolectric.pixelCopyRenderMode=hardware` system property. |

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
| --- | --- | --- |
| `@LooperMode(LEGACY)` | Deprecated. The `LooperMode.Mode` Javadoc lists as a problem with `LEGACY` mode that the default `UNPAUSED` state will execute tasks posted to a Looper inline synchronously, which differs from real Android behaviour. | Use `PAUSED`. |
| `@SQLiteMode` annotations | `@SQLiteMode` is deprecated and `NATIVE` is the default mode. | Usages of these APIs can be removed. |

## Related References

- **Compose idling and the clock**: See [synchronization.md](synchronization.md)
- **`@Config` and JDK**: See [configuration.md](configuration.md)
- **Screenshots**: See [visual-regression.md](../testing-patterns/visual-regression.md)
- **Animations**: See [clock-control.md](../advanced/clock-control.md)

## Sources

- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.Mode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/GraphicsMode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/GraphicsMode.Mode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/SQLiteMode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/SQLiteMode.Mode.html
- https://robolectric.org/upgrade_to_version_4/
- https://robolectric.org/blog/2019/06/04/paused-looper/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
- https://github.com/robolectric/robolectric/releases
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/ComposeUiTest
- https://developer.android.com/jetpack/androidx/releases/compose-ui
