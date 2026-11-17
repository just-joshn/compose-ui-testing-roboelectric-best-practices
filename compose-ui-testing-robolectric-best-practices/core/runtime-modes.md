# Runtime Modes

## Table of Contents

1. [Overview](#overview)
2. [Looper Mode](#looper-mode)
3. [Graphics Mode](#graphics-mode)
4. [SQLite Mode](#sqlite-mode)
5. [Other Modes](#other-modes)
6. [Accessibility Checks on Robolectric](#accessibility-checks-on-robolectric)
7. [Deprecations](#deprecations)
8. [Related References](#related-references)
9. [Sources](#sources)

## Overview

| Annotation | Description |
| --- | --- |
| `LooperMode` | A Configurer annotation for controlling Robolectric's Looper behavior. |
| `GraphicsMode` | A Configurer annotation for controlling which graphics shadow implementation is used for the android.graphics package. |
| `SQLiteMode` | Deprecated. This annotation will be deleted in a forthcoming Robolectric release. A Configurer annotation for controlling which SQLite shadow implementation is used for the android.database package. |

## Looper Mode

Currently Robolectric will default to `LooperMode.Mode.PAUSED` behavior, but this can be overridden by applying a `@LooperMode(NewMode)` annotation to a test package, test class, or test method, or via the 'robolectric.looperMode' system property.

| Mode | Description |
| --- | --- |
| `PAUSED` | A mode that more accurately models real Android's Looper behavior. |
| `INSTRUMENTATION_TEST` | A mode that simulates an android instrumentation test threading model, which has a separate test thread distinct from the main looper thread. |
| `LEGACY` | Deprecated. use `LooperMode.PAUSED`. `LEGACY` mode is not supported on Android SDKs > Baklava. |

### PAUSED

- Tests run on the main looper thread.
- Tasks posted to the main Looper are not executed automatically, and must be explicitly executed via `ShadowLooper` APIs like `ShadowLooper.idle()`. This guarantees execution order correctness.
- `SystemClock` time is frozen, and can be manually advanced via Robolectric APIs.
- Robolectric will warn users if a test fails with unexecuted tasks in the main Looper queue.
- Robolectric test APIs, like `ActivityController.setup()`, will automatically idle the main Looper.
- Each Looper has its own thread. Tasks posted to background loopers are executed asynchronously in separate threads.
- Looper use the real `MessageQueue` to store their queue of pending tasks.
- There is only a single clock value, managed via `ShadowSystemClock`. This can be explictly incremented via `ShadowSystemClock.advanceBy(Duration)`, or `ShadowLooper.idleFor(Duration)`.

A subset of the `Scheduler` APIs for the 'foreground' scheduler are currently supported in this mode as well, although it is recommended to switch to use `ShadowLooper` APIs directly.

### INSTRUMENTATION_TEST

A mode that simulates an android instrumentation test threading model, which has a separate test thread distinct from the main looper thread. Otherwise it is quite similar to `PAUSED` mode. The clock time is still fixed, and you can use `shadowLooper` methods to pause, unpause, and wait for any looper to be idle.

It is recommended to use this mode in tests that mostly use `androidx.test` APIs, which will support being called directly on the main thread or on the test thread. Most `org.robolectric` APIs that interact with the android UI (e.g. `ActivityController`) will raise an exception if called off the main thread.

### Using PAUSED

1. Apply the `LooperMode(PAUSED)` annotation to your test package/class/method (or remove a `LooperMode(LEGACY)` annotation).
2. Convert any background `Scheduler` for controlling Loopers to `shadowOf(looper)`.
3. Convert any `RoboExecutorService` usages to `PausedExecutorService` or `InlineExecutorService`.
4. Run your tests. If you see an test failures like 'Main looper has queued unexecuted runnables.', you may need to insert `shadowOf(getMainLooper()).idle()` calls to your test to drain the main Looper.

### ShadowLooper Methods

| Method | Description |
| --- | --- |
| `idle()` | Executes all posted tasks scheduled before or at the current time. |
| `idleFor(long, TimeUnit)` | Advances the system clock by the given time, then executes all posted tasks scheduled before or at the given time. |
| `idleFor(Duration)` | A variant of `idleFor(long, TimeUnit)` that accepts a `Duration`. |
| `isIdle()` | Returns true if there are no pending tasks scheduled to be executed before current time. |
| `runOneTask()` | Causes only one of the next Runnables that have been scheduled to run while advancing the clock to its start time. |
| `runToNextTask()` | Causes the next Runnable(s) that have been scheduled to run while advancing the clock to its start time. |
| `runToEndOfTasks()` | Causes all of the Runnables that have been scheduled to run while advancing the clock to the start time of the last scheduled Runnable. |
| `runUntilEmpty()` | Continuously run all Messages on this Looper until its queue is empty. |

## Graphics Mode

`GraphicsMode`: A Configurer annotation for controlling which graphics shadow implementation is used for the android.graphics package.

| Mode | Description |
| --- | --- |
| `NATIVE` | Use graphics shadows libraries backed by native Android graphics code. |
| `LEGACY` | Use legacy graphics shadows that are no-ops and fakes. |

Robolectric's native runtime now includes Linux arm64 (aarch64) native libraries, so tests that use native SQLite (the default) and native graphics (`@GraphicsMode(NATIVE)`) can run on Linux arm64 environments, such as GitHub's ubuntu-24.04-arm runners, AWS Graviton machines, and arm64 Docker containers on Apple silicon. No configuration is needed.

## SQLite Mode

Deprecated. This annotation will be deleted in a forthcoming Robolectric release.

- `SQLiteMode.Mode.NATIVE`: NATIVE is the default mode and does not need to be stated explicitly.
- `SQLiteMode.Mode.LEGACY`: This mode is obsolete and will be removed soon.
- As on Apple silicon, the legacy SQLite mode (`SQLiteMode.Mode.LEGACY`) isn't supported on Linux arm64.

## Other Modes

- `@TextLayoutMode` has been removed. Realistic text layout, the default since 2019, is now always used.
- Native resources (`ResourcesMode.NATIVE`) now work on SDK 36 and above, not only SDK 36.

## Accessibility Checks on Robolectric

| API | Note |
| --- | --- |
| `ComposeTestRule.enableAccessibilityChecks` | This requires API 34+ (Android U), and currently does not work on Robolectric. |
| `ComposeUiTest.enableAccessibilityChecks` | Requires API 34+ (Android U) and is not supported on Robolectric. |

## Deprecations

- `LooperMode.Mode.LEGACY`: The default `UNPAUSED` state will execute tasks posted to a Looper inline synchronously. This differs from real Android behaviour, and can cause issues with code that expects/enforces that posted tasks execute in the correct order, such as RecyclerViews.
- `Robolectric#getBackgroundThreadScheduler()`: This is only needed in the LEGACY looper mode. We strongly encourage you to use the PAUSED looper mode (which is the default)
- `Robolectric#getForegroundThreadScheduler()`: This is only needed in the LEGACY looper mode. We strongly encourage you to use the PAUSED looper mode (which is the default)
- `RuntimeEnvironment#getMasterScheduler()`: This is only needed in the LEGACY looper mode. We strongly encourage you to use the PAUSED looper mode (which is the default)
- `RuntimeEnvironment#setMasterScheduler()`: This is only needed in the LEGACY looper mode. We strongly encourage you to use the PAUSED looper mode (which is the default)
- `ShadowApplication#runBackgroundTasks()`: This is only needed in the LEGACY looper mode. We strongly encourage you to use the PAUSED looper mode (which is the default)
- `SQLiteMode`: `SQLiteMode.Mode.NATIVE` is now the default, and usages of these APIs can be removed

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
- https://robolectric.org/javadoc/4.18/org/robolectric/shadows/ShadowLooper.html
- https://robolectric.org/upgrade_to_version_4/
- https://github.com/robolectric/robolectric/releases
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/ComposeUiTest
