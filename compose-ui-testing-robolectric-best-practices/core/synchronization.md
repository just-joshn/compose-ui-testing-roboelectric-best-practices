# Synchronization & Waiting

## Table of Contents

1. [Automatic Synchronization](#automatic-synchronization)
2. [Coroutines and the v2 Dispatcher](#coroutines-and-the-v2-dispatcher)
3. [Manual Synchronization](#manual-synchronization)
4. [Waiting for Conditions](#waiting-for-conditions)
5. [Idling Resources](#idling-resources)
6. [Robolectric Looper and Main Thread](#robolectric-looper-and-main-thread)
7. [Never Sleep](#never-sleep)
8. [Common Issues & Solutions](#common-issues--solutions)
9. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
10. [Related References](#related-references)
11. [Sources](#sources)

## Automatic Synchronization

"Compose tests are synchronized by default with your UI." Before every assertion or action through the rule, the test waits until the UI tree is idle. Compose advances with a virtual clock, so tests do not run in real time and pass as fast as possible.

The catch: with no synchronizing call, no recomposition happens and the UI appears paused.

```kotlin
@Test
fun counterTest() {
    val myCounter = mutableStateOf(0)
    var lastSeenValue = 0
    composeTestRule.setContent {
        Text(myCounter.value.toString())
        lastSeenValue = myCounter.value
    }
    myCounter.value = 1 // The state changes, but there is no recomposition.

    // Bad: fails, nothing triggered a recomposition yet
    assertTrue(lastSeenValue == 1)

    // Good: the assertion synchronizes first
    composeTestRule.onNodeWithText("1").assertExists()
}
```

This only applies to Compose hierarchies, not to the rest of the app.

## Coroutines and the v2 Dispatcher

The v2 rule and `run*ComposeUiTest` APIs run composition on a `StandardTestDispatcher`. A launched coroutine is queued and runs only when the test advances the virtual clock. The deprecated v1 APIs used `UnconfinedTestDispatcher`, which ran work immediately and "could inadvertently mask real timing issues or race conditions".

```kotlin
// Bad in v2: loadData() has only been queued
viewModel.loadData()
assertEquals(Success, viewModel.state.value)

// Good: run queued work first
viewModel.loadData()
composeTestRule.waitForIdle()
assertEquals(Success, viewModel.state.value)

// Good: assert on the UI thread after idle
viewModel.loadData()
composeTestRule.runOnIdle {
    assertEquals(Success, viewModel.state.value)
}
```

Most tests that use `waitForIdle()` and the standard finders need no change when moving to v2. The v2 factories live in `androidx.compose.ui.test.junit4.v2` and `androidx.compose.ui.test.v2`.

### One clock for Compose and coroutines

`createComposeRule()` plus a separate `runTest { }` gives two clocks: advancing one does not advance the other. Use `runComposeUiTest`, which runs your block inside its own `runTest` scope with the clock synchronized.

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

If you must keep the rule, `composeTestRule.mainClock.scheduler` exposes the underlying `TestCoroutineScheduler`; share it with `runTest`. `runComposeUiTest` is the recommended route. ViewModel and dispatcher testing is covered in [coroutines-viewmodels.md](../testing-patterns/coroutines-viewmodels.md).

## Manual Synchronization

`waitForIdle()` depends on `autoAdvance`:

```kotlin
composeTestRule.mainClock.autoAdvance = true   // default
composeTestRule.waitForIdle()                  // advances the clock until Compose is idle

composeTestRule.mainClock.autoAdvance = false
composeTestRule.waitForIdle()                  // only waits for idling resources
```

In both cases `waitForIdle()` also waits for pending draw and layout passes.

With auto-advance off, launched coroutines do not run because the clock is paused. `runCurrent()` runs tasks scheduled for the current virtual time without advancing it, so you can check intermediate states:

```kotlin
composeTestRule.mainClock.scheduler.runCurrent()
```

`runOnIdle { }` runs the action on the UI thread after the UI is idle. Prefer it for reading state that Compose may still be changing. Full clock control is in [clock-control.md](../advanced/clock-control.md).

## Waiting for Conditions

For work outside the Compose clock, such as data loading, use `waitUntil` and its helpers:

```kotlin
composeTestRule.waitUntil(timeoutMillis = 5_000) {
    composeTestRule.onNodeWithText("Loaded").isDisplayed() // false if no node matches
}

composeTestRule.waitUntilAtLeastOneExists(hasText("Loaded"), timeoutMillis = 5_000)
composeTestRule.waitUntilDoesNotExist(hasTestTag("spinner"), timeoutMillis = 5_000)
composeTestRule.waitUntilExactlyOneExists(hasTestTag("detail"), timeoutMillis = 5_000)
composeTestRule.waitUntilNodeCount(hasTestTag("row"), count = 10, timeoutMillis = 5_000)
```

| API                                   | Clock behavior                                                         | Timeout is measured in |
| ------------------------------------- | ---------------------------------------------------------------------- | ---------------------- |
| `mainClock.advanceTimeUntil(ms) { }`  | Steps one frame at a time; condition must depend on Compose state only | Test clock time        |
| `waitUntil(ms) { }`                   | Advances the clock if auto-advance is on; sleeps between iterations    | Wall clock time        |

The docs recommend trying `advanceTimeUntil` before `waitUntil`; `waitUntil` integrates better with the host but is slower. `waitUntil` accepts an optional `conditionDescription` that is included in the timeout exception.

```kotlin
// Bad: the test clock never advances while the latch blocks
val latch = CountDownLatch(1)
latch.await()

// Good
composeTestRule.waitUntilAtLeastOneExists(hasText("Done"), timeoutMillis = 5_000)
```

Use idling resources in small UI tests and wait-until APIs in bigger ones.

## Idling Resources

Register an `IdlingResource` for asynchronous work that Compose and Espresso do not already know about, for example a background job that changes UI state. Interactions wait for it to be idle.

```kotlin
// FakeRepository is your own test double
class PendingRequestsIdlingResource(private val repo: FakeRepository) : IdlingResource {
    override val isIdleNow: Boolean get() = repo.pendingRequests == 0
    override fun getDiagnosticMessageIfBusy(): String? =
        if (isIdleNow) null else "${repo.pendingRequests} requests pending"
}

private val idlingResource = PendingRequestsIdlingResource(fakeRepository)

@Before fun register() = composeTestRule.registerIdlingResource(idlingResource)
@After fun unregister() = composeTestRule.unregisterIdlingResource(idlingResource)
```

`isIdleNow` is read from the main thread, so keep it lightweight. If one resource is busy, all are polled until every resource is idle.

## Robolectric Looper and Main Thread

- Under Robolectric the test and the UI event loop run on the same thread, so synchronization with AndroidX Test APIs "is not an issue".
- `LooperMode.PAUSED` is the default. Tasks posted to the main `Looper` do not run on their own. AndroidX Test APIs such as `ActivityScenario` and Espresso idle the main `Looper`; for your own posted work call `shadowOf(Looper.getMainLooper()).idle()`.
- Robolectric warns when a test fails with unexecuted tasks in the main `Looper` queue; that is a hint the behavior matters to the test.
- The Robolectric 2026 blog says Compose's JVM idling strategy is a main-thread loop that pumps Compose and forces layout, because there is no draw pass on the JVM.
- Since `1.13.0-alpha01`, `waitForIdle` and `runOnIdle` may be called from the main thread (earlier they threw `IllegalStateException`). That helps when you touch Views and Compose in one block, for example inside `scenario.onFragment { }`. Standard Compose-only tests need no change.

```kotlin
// 1.13.0-alpha01+: one block for View and Compose assertions
scenario.onFragment { fragment ->
    fragment.legacyButton.performClick()
    composeTestRule.waitForIdle()
    composeTestRule.onNodeWithText("Legacy Clicks: 1").assertIsDisplayed()
}
```

Details of `LooperMode` are in [runtime-modes.md](runtime-modes.md).

## Never Sleep

Do not pause tests for an arbitrary period. It "makes tests unnecessary slow or flaky". Compose already waits for idle before each interaction; add `waitUntil` for external conditions and idling resources for unknown background work.

## Common Issues & Solutions

| Issue                                                   | Solution                                                                       |
| ------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Assertion sees "Loading" after upgrading to v2          | `waitForIdle()` or `runOnIdle { }` before asserting                            |
| `LaunchedEffect` with `delay` has not completed         | Advance `mainClock` (for example `advanceTimeBy`), or use `runComposeUiTest`   |
| `runTest` time does not move Compose                    | Two clocks; switch to `runComposeUiTest`                                       |
| Coroutine does not run with `autoAdvance = false`       | `mainClock.scheduler.runCurrent()`                                             |
| `waitUntil` times out                                   | Timeout is wall clock time; check the condition and timeout. Register an `IdlingResource` for background work Compose does not know about |
| `IllegalStateException` calling `waitForIdle` on main thread | Needs 1.13.0-alpha01+ (main thread synchronization)                       |
| Unexpected behavior with an external `CountDownLatch`   | Use `waitUntil` helpers; the test clock is not advanced while a latch blocks   |

## Anti-Patterns to Avoid

| Anti-Pattern                                   | Problem                                   | Solution                                              |
| ---------------------------------------------- | ----------------------------------------- | ----------------------------------------------------- |
| `Thread.sleep(...)`                            | Slow or flaky                             | `waitUntil` or idling resource                        |
| `createComposeRule()` with `runTest`           | Separate clocks                           | `runComposeUiTest`                                    |
| `CountDownLatch` instead of `waitUntil`        | Test clock is not advanced                | `waitUntil` helpers                                   |
| Asserting immediately after launching a coroutine (v2) | Work is only queued                | `waitForIdle()` or `runOnIdle`                        |
| Using `runWithoutImplicitWait` in ordinary tests | Not meant for general UI tests          | Reserve for manual frame-by-frame loops               |

## Related References

- **Clock control and animations**: See [clock-control.md](../advanced/clock-control.md)
- **Looper and graphics modes**: See [runtime-modes.md](runtime-modes.md)
- **Flaky tests**: See [flaky-tests.md](../debugging/flaky-tests.md)
- **Dispatchers and ViewModels**: See [coroutines-viewmodels.md](../testing-patterns/coroutines-viewmodels.md)
- **Assertions**: See [assertions-actions.md](assertions-actions.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/training/testing/instrumented-tests/stability
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/IdlingResource
- https://robolectric.org/androidx_test/
- https://robolectric.org/blog/2019/06/04/paused-looper/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.html
