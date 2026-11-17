# Testing Animations

## Table of Contents

1. [Controlling the Clock](#controlling-the-clock)
2. [Frame Rules to Know](#frame-rules-to-know)
3. [Asserting Intermediate States](#asserting-intermediate-states)
4. [Frame-by-Frame Loops](#frame-by-frame-loops)
5. [Delays and Launched Effects](#delays-and-launched-effects)
6. [Visual Checks of Animation Frames](#visual-checks-of-animation-frames)
7. [Common Issues & Solutions](#common-issues--solutions)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Related References](#related-references)
10. [Sources](#sources)

## Controlling the Clock

Compose tests give you full control of a virtual test clock, so animation tests are deterministic and run faster than the animation's real duration. `ComposeTestRule` exposes the clock as `mainClock`. Set `autoAdvance = false`, start the animation, then advance time yourself.

```kotlin
@RunWith(AndroidJUnit4::class)
class AnimationTest {
    @get:Rule
    val rule = createAndroidComposeRule<ComponentActivity>()

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

        // Initiate the animation
        enabled = true

        // Let the animation proceed
        rule.mainClock.advanceTimeBy(50L)

        // Assert here (see Visual Checks of Animation Frames for the image comparison)
    }
}
```

The Compose doc's example uses `createComposeRule()`. The 2026-07-03 Robolectric blog confirms `createAndroidComposeRule<ComponentActivity>()` and `runComposeUiTest { }` run on the JVM, so those are used for `src/test` examples.

```kotlin
// Good: stop auto-advance, then drive frames yourself
rule.mainClock.autoAdvance = false
rule.mainClock.advanceTimeBy(50L)

// Bad: real-time waiting for the animation to finish
Thread.sleep(250)
```

`advanceTimeBy` does not move the clock by exactly the duration you pass: it rounds up to the nearest multiple of the frame duration.

## Frame Rules to Know

From the `MainTestClock` reference, relevant when `autoAdvance` is `false`:

- Recomposition only happens when a frame is produced by this clock. The one exception is the initial composition in `setContent`, which happens immediately.
- Animations get their frame time before recomposition. After toggling state to start an animation, `advanceTimeBy(32)` with 16 ms frames leaves the animation's play time at 0 ms: the first frame recomposes and schedules the animation; the next frame gives it its first frame time.
- Animations request the next frame during the current one, so `advanceTimeBy(160)` with 16 ms frames produces 10 frames of 16 ms, not 1 frame of 160 ms. Measure and layout run after each frame; draw does not run in between.
- Advancing by one frame (`advanceTimeByFrame()`) commits state changes and runs exactly one recomposition and measure/layout if triggered.
- After `advanceTimeBy`, anything rendering-related (for example `captureToImage`) needs `waitForIdle()` or `runOnIdle` so any triggered draw pass has completed.
- A state variable read during draw is not updated by `advanceTimeBy`; use `waitForIdle()`.
- On Android, only measure and layout run synchronously with this clock; the draw pass is driven by the Choreographer, so measure, layout, and draw can still occur while the clock is paused.

## Asserting Intermediate States

Use `hasPendingWork()` to see whether an animation is still running without advancing the clock (it does not drain the main message queue, unlike `waitForIdle`).

```kotlin
@Test
fun animationSettles() = runComposeUiTest {
    setContent { MainScreen() }
    mainClock.autoAdvance = false

    onNodeWithText("Start Animation").performClick()

    mainClock.advanceTimeByFrame()
    waitForIdle()
    assertTrue(hasPendingWork()) // still animating

    mainClock.autoAdvance = true
    waitForIdle()                // advances the clock until idle
    onNodeWithText("Done").assertIsDisplayed()
}
```

Prefer asserting layout or semantics you own over reading visual values. Exposing colors, font sizes, or corner radii through custom semantics is not recommended; compare images instead ([Visual Checks](#visual-checks-of-animation-frames)).

## Frame-by-Frame Loops

For manual stepping, each node query triggers implicit synchronization that is redundant when you control the clock. `runWithoutImplicitWait` skips it. It is in `ui-test` and `ui-test-junit4` 1.12.0-alpha03+, so it is available in the 1.12.1 stable release.

```kotlin
@Test
fun runWithoutImplicitWaitSample() = runComposeUiTest {
    setContent { MainScreen() }
    mainClock.autoAdvance = false

    // Trigger an animation
    onNodeWithText("Start Animation").performClick()

    // Step through the animation frame by frame
    while (hasPendingWork()) {
        mainClock.advanceTimeByFrame()
        waitForIdle()

        runOnUiThread {
            runWithoutImplicitWait {
                val box1 = onNodeWithTag("Box1").fetchSemanticsNode()
                val box2 = onNodeWithTag("Box2").fetchSemanticsNode()
                val box3 = onNodeWithTag("Box3").fetchSemanticsNode()

                // Assert the intermediate state for this frame
                assert(box1.boundsInRoot.right <= box2.boundsInRoot.left)
                assert(box2.boundsInRoot.right <= box3.boundsInRoot.left)
            }
        }
    }
}
```

Guidelines from the docs:

- Use it only when `mainClock.autoAdvance` is `false` and the UI is in a known stable state for the current frame.
- Call it on the UI thread, for example via `runOnUiThread`. Off the UI thread you risk race conditions and stale reads.
- Keep the block read-only; do mutating actions outside it.
- It is a specialized performance optimization for frame-by-frame animation loops, not for general UI tests, and gives no meaningful speedup elsewhere.

## Delays and Launched Effects

The test clock also resumes `delay` inside `LaunchedEffect` at the scheduled virtual time, so code like `repeat(2) { delay(1000) }` completes with a single `advanceTimeBy(2000)`.

```kotlin
// Good: virtual time, instant in real time
mainClock.advanceTimeBy(2000)
onNodeWithText("Ready").assertIsDisplayed()
```

For how this relates to `runTest` virtual time and the v2 `StandardTestDispatcher`, see [clock-control.md](../advanced/clock-control.md) and [synchronization.md](../core/synchronization.md).

## Visual Checks of Animation Frames

The Compose doc compares a mid-animation frame to an expected image:

```kotlin
// From the Compose docs. `assertAgainstGolden` is the doc's placeholder:
// "needs to be implemented in your code"; it is not a library API.
rule.mainClock.advanceTimeBy(50L)
rule.waitForIdle()
rule.onRoot().captureToImage().assertAgainstGolden()
```

`captureToImage()` returns an `ImageBitmap` and is annotated `@RequiresApi(26)`; since 1.13.0-alpha01 it has a `timeoutMillis` parameter (default 2000 ms). On Robolectric, rendering for screenshots uses native graphics (`@GraphicsMode(GraphicsMode.Mode.NATIVE)`), per the Robolectric blog's note that Compose screenshot tests use the native-graphics `PixelCopy` shadow. No fetched official page names a Robolectric screenshot-comparison library, so the golden comparison is yours to implement or take from a third party. See [visual-regression.md](visual-regression.md) and [runtime-modes.md](../core/runtime-modes.md).

## Common Issues & Solutions

| Symptom                                              | Cause                                                       | Fix                                                              |
| ---------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------- |
| Animation did not start after `advanceTimeBy(32)`    | Start time is set one frame after recomposition             | Advance by at least one more frame                               |
| UI does not change after `advanceTimeBy`             | State is read during draw                                   | `waitForIdle()`                                                  |
| Captured image is stale                              | Draw pass not finished                                      | `waitForIdle()` or `runOnIdle` before `captureToImage()`         |
| `advanceTimeBy(50)` moved the clock by more than 50  | Rounded up to a frame multiple                              | Assert on frame boundaries                                       |
| Frame loop is slow                                   | Implicit sync on every query                                | `runWithoutImplicitWait` (frame-by-frame loops only)             |

## Anti-Patterns to Avoid

| Anti-Pattern                                          | Problem                                   | Solution                                                  |
| ----------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------- |
| `Thread.sleep()` for animation duration               | Slow and flaky                            | `mainClock.advanceTimeBy`                                 |
| Leaving `autoAdvance = true` when asserting mid-animation | Clock runs past the state you want    | Set `autoAdvance = false` first                           |
| Using `runWithoutImplicitWait` in ordinary tests      | No benefit; not intended                  | Only for manual frame-by-frame loops                      |
| Calling `runWithoutImplicitWait` off the UI thread    | Race conditions, stale reads              | Wrap in `runOnUiThread`                                   |
| Mutating state inside `runWithoutImplicitWait`        | Block is for read-only assertions         | Act outside the block                                     |
| Exposing colors via custom semantics for animation asserts | Pollutes production code             | Compare images, or assert on layout bounds                |
| Inventing an `assertAgainstGolden` and assuming it exists | It is a doc placeholder              | Implement or adopt your own comparison                    |

## Related References

- **Clock control**: See [clock-control.md](../advanced/clock-control.md) for `MainTestClock` in depth
- **Synchronization**: See [synchronization.md](../core/synchronization.md) for `waitForIdle` and `waitUntil*`
- **Visual testing**: See [visual-regression.md](visual-regression.md) for screenshot concepts and tools
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md) for `GraphicsMode`
- **Flaky tests**: See [flaky-tests.md](../debugging/flaky-tests.md) for timing causes

## Sources

- https://developer.android.com/develop/ui/compose/animation/testing
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
