# Testing Animations

## Table of Contents

1. [Controlling the Clock](#controlling-the-clock)
2. [Frames and the Main Test Clock](#frames-and-the-main-test-clock)
3. [Asserting Intermediate States](#asserting-intermediate-states)
4. [Optimize animation tests](#optimize-animation-tests)
5. [Delays and Launched Effects](#delays-and-launched-effects)
6. [Visual Checks of Animation Frames](#visual-checks-of-animation-frames)
7. [Custom semantics properties](#custom-semantics-properties)
8. [Related References](#related-references)
9. [Sources](#sources)

## Controlling the Clock

Compose offers `ComposeTestRule` that lets you write tests for animations in a deterministic manner with full control over the test clock. This lets you verify intermediate animation values. In addition, a test can run quicker than the actual duration of the animation.

`ComposeTestRule` exposes its test clock as `mainClock`. You can set the `autoAdvance` property to false to control the clock in your test code. After initiating the animation you want to test, the clock can be moved forward with `advanceTimeBy`.

`advanceTimeBy` doesn't move the clock exactly by the specified duration. Rather, it rounds it up to the nearest duration that is a multiple of the frame duration.

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

### Disable Automatic Synchronization

To disable automatic synchronization, set the `autoAdvance` property in the `mainClock` to `false`. Typically you will then advance the time yourself. You can advance exactly one frame with `advanceTimeByFrame()` or by a specific duration with `advanceTimeBy()`:

```kotlin
composeTestRule.mainClock.advanceTimeByFrame()
composeTestRule.mainClock.advanceTimeBy(milliseconds)
```

`MainTestClock` is responsible for driving all the recompositions, animations, and gestures. The API doesn't control Android's measure and draw passes.

Advances the clock by the given duration. The duration is rounded up to the nearest multiple of the frame duration by default to always produce the same number of frames regardless of the current time of the clock. The frame duration is platform dependent. For example, on a JVM (Android and Desktop) it is 16ms.

### MainTestClock API

| API | Behavior |
|---|---|
| `advanceTimeBy(milliseconds: Long, ignoreFrameDuration: Boolean)` | Advances the clock by the given duration. The duration is rounded up to the nearest multiple of the frame duration by default. |
| `advanceTimeByFrame()` | Advances the main clock by the duration of one frame. |
| `advanceTimeUntil(timeoutMillis: Long, condition: () -> Boolean)` | Advances the clock in increments of a single frame until the given condition is satisfied. Note that the given condition should be checking the state that can be affected by this clock (it only works with Compose state). |
| `autoAdvance` | Whether the clock should be advanced by the testing framework while awaiting idleness in order to process any pending work that is driven by this clock. By default this is true. |
| `currentTime` | The current time of this clock in milliseconds. |

## Frames and the Main Test Clock

It is important to realize that if this clock does not tick, recomposition will not happen and animations are frozen.

Measure, layout and draw passes may be driven by this clock, depending on the platform. On Desktop, these are all driven by this clock, but on Android only measure and layout are performed synchronously. The draw pass on Android is driven by the Choreographer and will not happen as a result of forwarding this clock. That means that measure, layout and draw passes can still occur on Android even if this clock is paused.

Therefore, when setting `autoAdvance` to `false` and taking control over this clock, there are several things to realize:

- Recomposition can only happen when a frame is produced by this clock, with one exception: the initial composition when calling setContent happens immediately.
- Callers of `withFrameNanos` can only get a frame time when a frame is produced by this clock.
- If there is both a pending recomposition and an animation awaiting a frame time, ticking this clock will *first* send the new frame time to the animation, and *then* perform recomposition. Any state changes made by the animation will be seen by the recomposition.
- Because animations receive their frame time *before* recomposition, an animation will not get its start time in the first frame after kicking it off by toggling a state variable. For example, with a frame time of 16ms; when you call `advanceTimeBy(32)` after you toggled a state variable to kick off an animation, the animation's play time will still be at 0ms. The first frame is produced when the clock has advanced 16ms and will run a recomposition. During that recomposition the animation will be scheduled to start. When the clock has advanced another 16ms, the animation gets its first frame time and initialize the play time to `t=0`.
- Because animations request the next frame during the current frame, calling `advanceTimeBy(160)` while an animation is running will produce 10 frames of 16ms rather than 1 frame of 160ms (assuming a frame time of 16ms). Measure and layout happens after each frame, but draw will not happen in between these frames.
- After modifying a state variable, recomposition needs to happen to reflect the new state in the UI. Advancing the clock by one frame will commit the changes and run exactly one recomposition and measure and layout if triggered.
- If, after any call to `advanceTimeBy`, you want to assert anything related to rendering (e.g. `SemanticsNodeInteraction.captureToImage`), you will need a call to `androidx.compose.ui.test.junit4.ComposeTestRule.waitForIdle` or `androidx.compose.ui.test.junit4.ComposeTestRule.runOnIdle` to make sure that any triggered draw pass has been completed.
- If you change a state variable that is read during draw, calling `advanceTimeBy` will not produce the desired update to the UI. Use `androidx.compose.ui.test.junit4.ComposeTestRule.waitForIdle` for this case.

## Asserting Intermediate States

Returns whether the Compose UI has any pending work. This performs a passive check of the `mainClock`, snapshot state, and recomposer to determine if there is any pending work. Unlike `waitForIdle`, calling this method does not advance the clock or drain the main message queue.

This is particularly useful when `autoAdvance` is disabled, allowing you to inspect the state of the UI while an animation or other work is still active.

## Optimize animation tests

When testing high-fidelity animations, you often need to disable auto-advance and manually step through frames to assert intermediate UI states. For these specific frame-by-frame loops, use the `runWithoutImplicitWait` method to execute your assertions. Standard node queries (like `onNodeWithTag` or `fetchSemanticsNode`) trigger implicit synchronizations that are redundant when you are manually controlling the clock, so bypassing them significantly speeds up your test runtimes.

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

### Usage guidelines

- Manual clock management: Use this API when `mainClock.autoAdvance` is set to `false` and the UI is in a known, stable state for the current frame.
- UI thread execution: To ensure the stability of the UI tree, call `runWithoutImplicitWait` on the UI thread, such as with `runOnUiThread`. Running it off the UI thread exposes your test to race conditions and stale state reads.
- Read-only assertions: The block should strictly contain read-only assertions. Any actions that mutate state should be performed outside of this block.

## Delays and Launched Effects

`delayed` `LaunchedEffect`s are resumed on their scheduled time. That means that code like `repeat(2) { delay(1000) }` will complete with a single call to `advanceTimeBy(2000)`.

The `runComposeUiTest` API automatically executes your test block within its own `runTest` scope. The test clock is synchronized with the Compose environment, so you no longer need to manage the scheduler manually.

```kotlin
@Test
fun testWithCoroutines() = runComposeUiTest {
    setContent {
        var status by remember { mutableStateOf("Loading...") }
        LaunchedEffect(Unit) {
            delay(1000)
            status = "Done!"
        }
        Text(text = status)
    }

    onNodeWithText("Loading...").assertIsDisplayed()
    mainClock.advanceTimeBy(1000 + 16 /* Frame buffer */)
    onNodeWithText("Done!").assertIsDisplayed()
}
```

## Visual Checks of Animation Frames

Captures the underlying semantics node's surface into an `ImageBitmap`.

- `@RequiresApi(value = 26)`
- `timeoutMillis`: The maximum time (in ms) to wait for the drawing to complete. Default is 2000 ms.

Robolectric can take screenshots natively, but you need a third-party library to perform screenshot testing with it. Use Robolectric to take screenshots when the pixel accuracy is not critical. For example, to test how a component reacts to different font sizes or themes.

## Custom semantics properties

Warning: You should only use custom Semantics properties when it's hard to match a specific item using the given finders and matchers. Using custom Semantics properties to expose visual properties such as colors, font size or rounded corner radius is not recommended, as it can pollute production code and wrong implementations can lead to bugs that are hard to find.

## Related References

- **Clock control**: See [clock-control.md](../advanced/clock-control.md) for `MainTestClock` in depth
- **Synchronization**: See [synchronization.md](../core/synchronization.md) for `waitForIdle` and `waitUntil*`
- **Visual testing**: See [visual-regression.md](visual-regression.md) for screenshot concepts and tools
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md) for `GraphicsMode`
- **Flaky tests**: See [flaky-tests.md](../debugging/flaky-tests.md) for timing causes

## Sources

- https://developer.android.com/develop/ui/compose/animation/testing
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/ComposeUiTest
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/develop/ui/compose/testing/common-patterns
