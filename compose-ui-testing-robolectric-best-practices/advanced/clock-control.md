# Clock Control

## Table of Contents

1. [What the Clock Drives](#what-the-clock-drives)
2. [Taking Control](#taking-control)
3. [Advancing Time](#advancing-time)
4. [Frame Ordering Rules](#frame-ordering-rules)
5. [Delayed Effects](#delayed-effects)
6. [Coroutine Virtual Time](#coroutine-virtual-time)
7. [Animation Example](#animation-example)
8. [Frame-by-Frame Loops](#frame-by-frame-loops)
9. [Related References](#related-references)
10. [Sources](#sources)

## What the Clock Drives

`MainTestClock` is ultimately responsible for driving all recompositions, all subscribers to `withFrameNanos` (all compose animations) and all coroutines launched with `LaunchedEffect` (for example gesture detection). It is important to realize that if this clock does not tick, recomposition will not happen and animations are frozen.

Measure, layout and draw passes may be driven by this clock, depending on the platform. On Desktop, these are all driven by this clock, but on Android only measure and layout are performed synchronously. The draw pass on Android is driven by the Choreographer and will not happen as a result of forwarding this clock.

Measure, layout and draw passes can still occur on Android even if this clock is paused.

`ComposeTestRule` exposes its test clock as `mainClock`. A test can run quicker than the actual duration of the animation.

Robolectric's 2026 blog on local-testing libraries, which calls itself "an outside read of the code as it stands in mid-2026, not an official AndroidX position", says in its Jetpack Compose UI test example: "Frames come from a virtual-time test clock rather than a real Choreographer".

## Taking Control

In some cases you might want to stop synchronization and control the clock yourself. For example, you can control time to take accurate screenshots of an animation at a point where the UI would still be busy. To disable automatic synchronization, set the `autoAdvance` property in the `mainClock` to `false`:

```kotlin
composeTestRule.mainClock.autoAdvance = false
```

`autoAdvance` is whether the clock should be advanced by the testing framework while awaiting idleness in order to process any pending work that is driven by this clock. By default this is `true`.

If `autoAdvance` is false, the clock is not advanced while awaiting idleness. Moreover, having pending recompositions or animations is not taken as a sign of pending work (non-idleness) when awaiting idleness, as waiting for a longer time will not make them happen. Note that pending measure, layout or draw passes will still be awaited when awaiting idleness and having `autoAdvance` set to false, as those passes are not driven by this clock.

If `autoAdvance` is false, the clock will not be advanced by `waitForIdle()`, which means that the Compose UI appears to be frozen. This is ideal for testing animations in a deterministic way.

`hasPendingWork()` returns whether the Compose UI has any pending work. Calling it does not advance the clock or drain the main message queue.

## Advancing Time

```kotlin
composeTestRule.mainClock.advanceTimeByFrame()
composeTestRule.mainClock.advanceTimeBy(milliseconds)
composeTestRule.mainClock.advanceTimeUntil(timeoutMs) { condition }
```

```kotlin
fun advanceTimeBy(milliseconds: Long, ignoreFrameDuration: Boolean = false): Unit
fun advanceTimeByFrame(): Unit
fun advanceTimeUntil(timeoutMillis: Long, condition: () -> Boolean): Unit
var autoAdvance: Boolean
val currentTime: Long
```

`advanceTimeByFrame()` advances the main clock by the duration of one frame.

`advanceTimeBy` advances the clock by the given duration. The duration is rounded up to the nearest multiple of the frame duration by default to always produce the same number of frames regardless of the current time of the clock. Use `ignoreFrameDuration` to disable this behavior. The frame duration is platform dependent. For example, on a JVM (Android and Desktop) it is 16ms.

Note that if `ignoreFrameDuration` is true, the last few milliseconds that are advanced might not be observed by anyone, since most processes are only triggered when a frame is produced.

`advanceTimeBy` doesn't move the clock exactly by the specified duration. Rather, it rounds it up to the nearest duration that is a multiple of the frame duration.

When using `advanceTimeBy` to advance the time by several frames in one invocation, recomposition is done after each produced frame, but whether measure, layout and draw happen is platform dependent. On Android, measure and layout will be done, but not draw. On Desktop, measure, layout and draw will happen. Frames are only produced if there is a need for them, e.g. when an animation is running, or if state is changed.

It is recommended to set `autoAdvance` to false when using `advanceTimeBy`, but it is not strictly necessary. Manually advancing the time is just as fast as automatic advancement and vice versa.

`advanceTimeUntil` advances the clock in increments of a frame until the given condition is satisfied. The condition should only rely on things that are driven by this clock. Depending on the platform, measure, layout or draw passes might not happen in between advancements of the clock while waiting for the condition to become true. On Android and Desktop, measure and layout are happening, but draw only happens on Desktop. If your condition relies on the result of draw, use `ComposeTestRule.waitUntil` instead.

The `timeoutMillis` of `advanceTimeUntil` is the time after which the method throws an exception if the given condition is not satisfied. This is test clock time, not the wall clock or cpu time. The exception is a `ComposeTimeoutException`.

`currentTime` is the current time of this clock in milliseconds.

## Frame Ordering Rules

When setting `autoAdvance` to `false` and taking control over this clock, there are several things to realize:

- Recomposition can only happen when a frame is produced by this clock, with one exception: the initial composition when calling `setContent` happens immediately.
- Callers of `withFrameNanos` can only get a frame time when a frame is produced by this clock.
- If there is both a pending recomposition and an animation awaiting a `withFrameNanos`, ticking this clock will *first* send the new frame time to the animation, and *then* perform recomposition. Any state changes made by the animation will be seen by the recomposition.
- Because animations receive their `withFrameNanos` *before* recomposition, an animation will not get its start time in the first frame after kicking it off by toggling a state variable. For example, with a frame time of 16ms; when you call `advanceTimeBy` after you toggled a state variable to kick off an animation, the animation's play time will still be at 0ms. The first frame is produced when the clock has advanced 16ms and will run a recomposition. During that recomposition the animation will be scheduled to start. When the clock has advanced another 16ms, the animation gets its first frame time and initialize the play time to `t=0`.
- Because animations request the next `withFrameNanos` during the current frame, calling `advanceTimeBy` while an animation is running will produce 10 frames of 16ms rather than 1 frame of 160ms (assuming a frame time of 16ms). Measure and layout happens after each frame, but draw will not happen in between these frames.
- After modifying a state variable, recomposition needs to happen to reflect the new state in the UI. Advancing the clock by `advanceTimeByFrame` will commit the changes and run exactly one recomposition and measure and layout if triggered.
- If, after any call to `advanceTimeBy`, you want to assert anything related to rendering (e.g. `SemanticsNodeInteraction.captureToImage`), you will need a call to `ComposeTestRule.waitForIdle` or `ComposeTestRule.runOnIdle` to make sure that any triggered draw pass has been completed.
- If you change a state variable that is read during draw, calling `advanceTimeBy` will not produce the desired update to the UI. Use `ComposeTestRule.waitForIdle` for this case.

## Delayed Effects

`LaunchedEffect`s are resumed on their scheduled time. That means that code like `repeat(2) { delay(1000) }` will complete with a single call to `advanceTimeBy`.

## Coroutine Virtual Time

`mainClock.scheduler` is the `TestCoroutineScheduler` on which this clock is built. It drives the execution of coroutines within the composition and is used to dispatch coroutines inside the `Recomposer` and for `LaunchedEffect`s.

If the test was started with a custom `effectContext` containing a `TestDispatcher`, `scheduler` returns the scheduler from that dispatcher. Otherwise, an internally managed `TestCoroutineScheduler` is created.

The API reference lists `scheduler` as added in 1.11.0.

## Animation Example

`ComposeTestRule` lets you write tests for animations in a deterministic manner with full control over the test clock. This lets you verify intermediate animation values.

You can set the `autoAdvance` property to false to control the clock in your test code. After initiating the animation you want to test, the clock can be moved forward with `advanceTimeBy`.

```kotlin
@get:Rule
val rule = createComposeRule()

@Test
fun testAnimationWithClock() {
    // Pause animations
    rule.mainClock.autoAdvance = false
    var enabled by mutableStateOf(false)
    rule.setContent {
        val color by animateColorAsState(
            targetValue = if (enabled) Color.Red else Color.Green,
            animationSpec = tween(durationMillis = 250)
        )
        Box(Modifier.size(64.dp).background(color))
    }

    // Initiate the animation.
    enabled = true

    // Let the animation proceed.
    rule.mainClock.advanceTimeBy(50L)

    // Compare the result with the image showing the expected result.
    // `assertAgainGolden` needs to be implemented in your code.
    rule.onRoot().captureToImage().assertAgainstGolden()
}
```

## Frame-by-Frame Loops

The `runWithoutImplicitWait` API is included in `androidx.compose.ui:ui-test-junit4:1.12.0-alpha03+` and `androidx.compose.ui:ui-test:1.12.0-alpha03+`.

When testing high-fidelity animations, you often need to disable auto-advance and manually step through frames to assert intermediate UI states. For these specific frame-by-frame loops, use the `runWithoutImplicitWait` method to execute your assertions. Standard node queries (like `onNodeWithTag` or `fetchSemanticsNode`) trigger implicit synchronizations that are redundant when you are manually controlling the clock, so bypassing them significantly speeds up your test runtimes.

This API is a specialized performance optimization designed strictly for manual frame-by-frame animation testing. It is not intended for general-purpose UI tests and won't provide meaningful performance improvements outside of manual clock advancement loops.

Usage guidelines:

- **Manual clock management**: Use this API when `mainClock.autoAdvance` is set to `false` and the UI is in a known, stable state for the current frame.
- **UI thread execution**: To ensure the stability of the UI tree, call `runWithoutImplicitWait` on the UI thread, such as with `runOnUiThread`. Running it off the UI thread exposes your test to race conditions and stale state reads.
- **Read-only assertions**: The block should strictly contain read-only assertions. Any actions that mutate state should be performed outside of this block.

```kotlin
@Test
fun runWithoutImplicitWaitSample() = runComposeUiTest {
    setContent { MainScreen() }
    mainClock.autoAdvance = false

    // Trigger an animation
    onNodeWithText("Start Animation").performClick()

    // Step through the animation frame-by-frame
    while (hasPendingWork()) {
        mainClock.advanceTimeByFrame()
        waitForIdle()
        runOnUiThread {
            // Suppress implicit synchronization inside this block to avoid redundant
            // waits on each node query, making the frame assertions execute much faster.
            runWithoutImplicitWait {
                val box1 = onNodeWithTag("Box1").fetchSemanticsNode()
                val box2 = onNodeWithTag("Box2").fetchSemanticsNode()
                val box3 = onNodeWithTag("Box3").fetchSemanticsNode()

                // Assert the exact intermediate state of all three properties for this frame
                assert(box1.boundsInRoot.right <= box2.boundsInRoot.left)
                assert(box2.boundsInRoot.right <= box3.boundsInRoot.left)
            }
        }
    }
}
```

## Related References

- **Idle and waiting**: See [synchronization.md](../core/synchronization.md)
- **Animation test patterns**: See [animations.md](../testing-patterns/animations.md)
- **Coroutines and queued work**: See [coroutines.md](../testing-patterns/coroutines.md)
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md)

## Sources

- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/develop/ui/compose/animation/testing
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
