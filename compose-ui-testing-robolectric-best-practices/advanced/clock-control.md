# Clock Control

## Table of Contents

1. [What the Clock Drives](#what-the-clock-drives)
2. [Taking Control](#taking-control)
3. [Advancing Time](#advancing-time)
4. [Frame Ordering Rules](#frame-ordering-rules)
5. [Delayed Effects](#delayed-effects)
6. [Coroutine Virtual Time](#coroutine-virtual-time)
7. [Rendering Assertions After Advancing](#rendering-assertions-after-advancing)
8. [Frame-by-Frame Loops](#frame-by-frame-loops)
9. [Common Issues & Solutions](#common-issues--solutions)
10. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
11. [Related References](#related-references)
12. [Sources](#sources)

## What the Clock Drives

`MainTestClock` ("`composeTestRule.mainClock`", or `mainClock` inside `runComposeUiTest`) is "the clock that drives frames, recompositions and launched effects in compose tests". It drives all recompositions, every `withFrameNanos` subscriber (all Compose animations), and coroutines launched with `LaunchedEffect`, such as gesture detection. If it does not tick, recomposition does not happen and animations are frozen.

It does not control Android's measure and draw passes. On Android only measure and layout run synchronously; the draw pass is driven by the Choreographer and does not happen as a result of forwarding this clock.

This is test time, not wall time, so a test can run quicker than an animation's actual duration. This matches the Robolectric/JVM setup where Compose frames come from a virtual-time clock.

## Taking Control

By default `autoAdvance` is `true`: the framework advances the clock while it waits for idle, so there are no pending recompositions or animations when your assertion runs. Turn it off to inspect states in between:

```kotlin
composeTestRule.mainClock.autoAdvance = false
```

With it off:

- `waitForIdle()` only waits for idling resources, plus pending measure, layout, and draw passes.
- Pending recompositions and animations no longer count as "not idle".
- Initial composition from `setContent` still happens immediately.
- Recomposition happens only when the clock produces a frame.

Scroll actions need clock frames, so `performScrollTo` throws `AssertionError` while `autoAdvance` is `false`.

## Advancing Time

```kotlin
composeTestRule.mainClock.advanceTimeByFrame()           // exactly one frame
composeTestRule.mainClock.advanceTimeBy(250)             // rounded UP to a whole number of frames
composeTestRule.mainClock.advanceTimeBy(250, ignoreFrameDuration = true)
composeTestRule.mainClock.advanceTimeUntil(timeoutMillis = 2_000) { condition }
val now = composeTestRule.mainClock.currentTime          // ms
```

| API                                   | Behavior                                                                                  |
| ------------------------------------- | ----------------------------------------------------------------------------------------- |
| `advanceTimeByFrame()`                | One frame; commits state changes and runs one recomposition and any triggered measure/layout |
| `advanceTimeBy(ms)`                   | Rounded up to the nearest multiple of the frame duration (16 ms on JVM)                   |
| `advanceTimeBy(ms, ignoreFrameDuration = true)` | No rounding; the last few ms may be seen by nobody because work triggers only on frames |
| `advanceTimeUntil(timeoutMillis) { }` | Single-frame increments until the condition holds; throws `ComposeTimeoutException` otherwise |

The timeout for `advanceTimeUntil` is test clock time, and the condition must read only things this clock drives (Compose state). If it depends on drawing or outside work, use `waitUntil`; see [synchronization.md](../core/synchronization.md).

Auto-advancing and manual advancing are equally fast. Setting `autoAdvance = false` is recommended when calling `advanceTimeBy`, but not strictly necessary.

## Frame Ordering Rules

These explain most "off by one frame" surprises.

- Animations receive their frame time before recomposition. After you toggle state to start an animation, `advanceTimeBy(32)` at 16 ms frames leaves the play time at 0 ms: frame 1 recomposes and schedules the animation, frame 2 gives it its first frame time and sets `t=0`.
- Animations request the next frame during the current one. `advanceTimeBy(160)` with a running animation produces ten 16 ms frames, not one 160 ms frame. Measure and layout happen after each frame; draw does not happen in between.
- After changing state, advancing one frame commits it and runs exactly one recomposition.
- State read during draw is not updated by `advanceTimeBy`; use `waitForIdle()`.
- Because of rounding, `advanceTimeBy(50L)` does not move the clock exactly 50 ms. Build assertions around frame boundaries.

```kotlin
// Illustrative: step an animation on the test clock
@Test
fun colorAnimation_midway() = runComposeUiTest {
    mainClock.autoAdvance = false
    var enabled by mutableStateOf(false)
    setContent {
        val color by animateColorAsState(
            targetValue = if (enabled) Color.Red else Color.Green,
            animationSpec = tween(durationMillis = 250)
        )
        Box(Modifier.size(64.dp).background(color).testTag("box"))
    }
    enabled = true
    mainClock.advanceTimeBy(50L)       // rounded up to a whole frame
    // assert on something observable: semantics, or a captured image (see animations.md)
}
```

Animation assertion patterns are in [animations.md](../testing-patterns/animations.md).

## Delayed Effects

Delayed `LaunchedEffect`s resume at their scheduled virtual time, so long waits cost nothing:

```kotlin
LaunchedEffect(Unit) {
    repeat(2) { delay(1000) }
    done = true
}
```

```kotlin
// One call completes both delays
mainClock.advanceTimeBy(2000)
onNodeWithText("Done!").assertIsDisplayed()
```

`mainClock.advanceTimeBy(1000 + 16 /* Frame buffer */)` is the migration guide's pattern for a single `delay(1000)`; it adds a frame buffer to the delay before asserting.

## Coroutine Virtual Time

`mainClock.scheduler` (since 1.11.0) is the `TestCoroutineScheduler` the clock is built on. It dispatches coroutines inside the `Recomposer` and for `LaunchedEffect`s. If the test started with an `effectContext` containing a `TestDispatcher`, `scheduler` returns that dispatcher's scheduler; otherwise an internal one is created.

| Tool                          | Advances                                      | Use for                                        |
| ----------------------------- | --------------------------------------------- | ---------------------------------------------- |
| `mainClock.advanceTimeBy`     | Compose clock (frames, effects, animations)   | Anything driven by Compose                     |
| `mainClock.scheduler.runCurrent()` | Nothing; runs tasks due now              | Checking an intermediate state with auto-advance off |
| `waitForIdle()`               | Clock until idle (if auto-advance on)         | Settling before an assertion                   |
| `runTest { advanceTimeBy }`   | A separate scheduler                          | Not the Compose clock                          |

```kotlin
// Bad: runTest builds its own scheduler, Compose does not move
@get:Rule val rule = createComposeRule()
@Test fun twoClocks() {
    rule.setContent { /* delay(1000) then "Done!" */ }
    runTest { advanceTimeBy(1000) }   // does NOT advance the compose clock
}

// Good: one clock
@Test fun oneClock() = runComposeUiTest {
    setContent { /* delay(1000) then "Done!" */ }
    mainClock.advanceTimeBy(1000 + 16)
}
```

`runTestContext` and `effectContext` must not share a `TestCoroutineScheduler`. `ComposeUiTestConfig` (1.13.0-rc01) exposes both; with it you can pass your own `TestDispatcher` in `effectContext` and the clock will use its scheduler.

## Rendering Assertions After Advancing

Because draw is not driven by this clock, after any `advanceTimeBy` call `waitForIdle()` or `runOnIdle { }` before asserting on rendering, such as `captureToImage()`.

```kotlin
mainClock.advanceTimeBy(50L)
waitForIdle()                       // let the triggered draw pass complete
onRoot().captureToImage()           // @RequiresApi(26); comparison is your own code
```

The animation page's `assertAgainstGolden()` is a placeholder: "needs to be implemented in your code". No library API of that name exists in the docs.

## Frame-by-Frame Loops

`runWithoutImplicitWait` (`ui-test` and `ui-test-junit4` 1.12.0-alpha03+) skips the implicit sync that every node query performs. It speeds up manual stepping loops and nothing else.

```kotlin
@Test
fun stepThroughAnimation() = runComposeUiTest {
    setContent { MainScreen() }
    mainClock.autoAdvance = false
    onNodeWithText("Start Animation").performClick()
    while (hasPendingWork()) {
        mainClock.advanceTimeByFrame()
        waitForIdle()
        runOnUiThread {
            runWithoutImplicitWait {
                val box1 = onNodeWithTag("Box1").fetchSemanticsNode()
                val box2 = onNodeWithTag("Box2").fetchSemanticsNode()
                assert(box1.boundsInRoot.right <= box2.boundsInRoot.left)
            }
        }
    }
}
```

Rules: use it only with `autoAdvance = false` and a stable frame, call it on the UI thread, keep the block read-only, and do not use it in general UI tests.

## Common Issues & Solutions

| Issue                                              | Solution                                                                      |
| -------------------------------------------------- | ----------------------------------------------------------------------------- |
| Animation still at start after `advanceTimeBy(32)` | Startup takes frames; advance more, or one frame at a time                    |
| UI never updates with `autoAdvance = false`        | Advance the clock; nothing recomposes by itself                               |
| Assertion on drawn output is stale                 | `waitForIdle()` or `runOnIdle` after advancing                                |
| State read in draw does not update                 | `waitForIdle()`, not `advanceTimeBy`                                          |
| `advanceTimeUntil` throws `ComposeTimeoutException`| Condition not driven by this clock; use `waitUntil`                           |
| `performScrollTo` throws with manual clock         | Turn `autoAdvance` back on first                                              |

## Anti-Patterns to Avoid

| Anti-Pattern                                    | Problem                                  | Solution                                         |
| ----------------------------------------------- | ---------------------------------------- | ------------------------------------------------ |
| `Thread.sleep` to wait for an animation         | Slow and flaky                           | `advanceTimeBy` on the test clock                |
| `runTest { advanceTimeBy }` next to a rule      | Separate clock                           | `runComposeUiTest`                               |
| Expecting exact-millisecond advancement         | Rounded to whole frames                  | Assert at frame boundaries                       |
| Leaving `autoAdvance = false` and then scrolling | Scroll cannot progress                  | Restore it                                       |
| `runWithoutImplicitWait` everywhere             | No gain outside manual loops             | Limit to frame-stepping loops                    |

## Related References

- **Idle and waiting**: See [synchronization.md](../core/synchronization.md)
- **Animation test patterns**: See [animations.md](../testing-patterns/animations.md)
- **Coroutine dispatchers**: See [coroutines-viewmodels.md](../testing-patterns/coroutines-viewmodels.md)
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md)

## Sources

- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/develop/ui/compose/animation/testing
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/ComposeUiTestConfig
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
