# Debugging and Managing Flaky Tests

## Table of Contents

1. [Compose Synchronization](#compose-synchronization)
2. [Coroutine Timing (v1 vs v2)](#coroutine-timing-v1-vs-v2)
3. [Main Looper and Threads](#main-looper-and-threads)
4. [Best Practices](#best-practices)
5. [Input Mode Leakage](#input-mode-leakage)
6. [Related References](#related-references)
7. [Sources](#sources)

## Compose Synchronization

Compose tests are synchronized by default with your UI. When you call an assertion or an action with the `ComposeTestRule`, the test is synchronized beforehand, waiting until the UI tree is idle.

When a test is synchronized, your Compose app is advanced in time using a virtual clock. This means Compose tests don't run in real time, so they can pass as fast as possible.

However, if you don't use the methods that synchronize your tests, no recomposition will occur and the UI will appear to be paused.

```kotlin
@Test
fun counterTest() {
    val myCounter = mutableStateOf(0) // State that can cause recompositions.
    var lastSeenValue = 0 // Used to track recompositions.
    composeTestRule.setContent {
        Text(myCounter.value.toString())
        lastSeenValue = myCounter.value
    }
    myCounter.value = 1 // The state changes, but there is no recomposition.

    // Fails because nothing triggered a recomposition.
    assertTrue(lastSeenValue == 1)

    // Passes because the assertion triggers recomposition.
    composeTestRule.onNodeWithText("1").assertExists()
}
```

Note that this requirement only applies to Compose hierarchies and not to the rest of the app.

### Idling Resources

Compose can synchronize tests and the UI so that every action and assertion is done in an idle state, waiting or advancing the clock as needed. However, some asynchronous operations whose results affect the UI state can be run in the background while the test is unaware of them.

Create and register these *idling resources* in your test so that they're taken into account when deciding whether the app under test is busy or idle. You don't have to take action unless you need to register additional idling resources, for example, if you run a background job that is not synchronized with Espresso or Compose.

```kotlin
composeTestRule.registerIdlingResource(idlingResource)
composeTestRule.unregisterIdlingResource(idlingResource)
```

### Manual Synchronization

The `waitForIdle()` function waits for Compose to be idle, but the function depends on the `autoAdvance` property:

```kotlin
composeTestRule.mainClock.autoAdvance = true // Default
composeTestRule.waitForIdle() // Advances the clock until Compose is idle.

composeTestRule.mainClock.autoAdvance = false
composeTestRule.waitForIdle() // Only waits for idling resources to become idle.
```

Note that in both cases, `waitForIdle()` also waits for pending draw and layout passes.

### Wait for Conditions

Any condition that depends on external work, such as data loading or Android's measure or draw (that is, measure or draw external to Compose), should use a more general concept such as `waitUntil()`:

```kotlin
composeTestRule.waitUntil(timeoutMs) { condition }
```

You can also use any of the `waitUntil` helpers:

```kotlin
composeTestRule.waitUntilAtLeastOneExists(matcher, timeoutMs)

composeTestRule.waitUntilDoesNotExist(matcher, timeoutMs)

composeTestRule.waitUntilExactlyOneExists(matcher, timeoutMs)

composeTestRule.waitUntilNodeCount(matcher, count, timeoutMs)
```

Warning: In some cases, using mechanisms in a test like an external `CountDownLatch` instead of the `waitUntil` APIs could behave unexpectedly, since the test clock won't be advanced.

## Coroutine Timing (v1 vs v2)

The v1 APIs are deprecated, and it's strongly recommended to migrate to the new APIs.

While the v1 APIs relied on the `UnconfinedTestDispatcher`, the v2 APIs use the `StandardTestDispatcher` by default for the running composition. This change aligns Compose test behavior with the standard `runTest` APIs and provides explicit control over coroutine execution order.

The v2 testing API changes are included in `androidx.compose.ui:ui-test-junit4:1.11.0-alpha03+` and `androidx.compose.ui:ui-test:1.11.0-alpha03+`.

The primary difference between v1 and v2 of the APIs is how coroutines are dispatched:

- v1 APIs (`UnconfinedTestDispatcher`): When a coroutine was launched, it executed immediately on the current thread, often finishing before the next line of test code ran. Unlike production behavior, this immediate execution could inadvertently mask real timing issues or race conditions that would occur in a live application.
- v2 APIs (`StandardTestDispatcher`): When a coroutine is launched, it is queued and does not execute until the test explicitly advances the virtual clock. Standard Compose test APIs (such as `waitForIdle()`) already handle this synchronization, so most tests relying on these standard APIs should continue to work with no changes.

### Failures After Upgrading to v2

If your tests fail after upgrading to v2, they likely exhibit the following pattern:

- Failure: You launch a task (for example, a ViewModel loads data), but your assertion fails immediately because the data is still in a "Loading" state.
- Cause: With the v2 APIs, coroutines are queued rather than executed immediately. The task was queued but never actually ran before the result was checked.
- Fix: Explicitly advance time. You must explicitly tell the v2 dispatcher when to execute work.

In v1, the task launched and finished immediately. In v2, the following code fails because `loadData()` hasn't actually run yet.

```kotlin
// In v1, this launched and finished immediately.
viewModel.loadData()

// In v2, this fails because loadData() hasn't actually run yet!
assertEquals(Success, viewModel.state.value)
```

Use `waitForIdle` or `runOnIdle` to execute queued tasks before asserting. Using `waitForIdle` advances the clock until the UI is idle, verifying the coroutine has run.

```kotlin
viewModel.loadData()

// Explicitly run all queued tasks
composeTestRule.waitForIdle()

assertEquals(Success, viewModel.state.value)
```

Using `runOnIdle` executes the code block on the UI thread after the UI has become idle.

```kotlin
viewModel.loadData()

// Run the assertion after the UI is idle
composeTestRule.runOnIdle {
    assertEquals(Success, viewModel.state.value)
}
```

### Run Queued Coroutines Without Advancing Time

In scenarios involving manual synchronization, such as when auto-advancing is disabled, launching a coroutine does not result in immediate execution because the test clock is paused. To execute coroutines in the queue without advancing the virtual clock, use the `runCurrent()` API. This runs tasks scheduled for the current virtual time.

```kotlin
composeTestRule.mainClock.scheduler.runCurrent()
```

In contrast to `waitForIdle()`, which advances the test clock until the UI stabilizes, `runCurrent()` executes pending tasks while maintaining the current virtual time.

### Migrate to runComposeUiTest

If you're using Compose test APIs alongside the Kotlin `runTest` API, it's strongly recommended to switch to `runComposeUiTest`. Using `createComposeRule` in conjunction with `runTest` creates two separate clocks: one for Compose, and one for the test coroutine scope. This configuration can force you to manually synchronize the test scheduler. The `runComposeUiTest` API automatically executes your test block within its own `runTest` scope. The test clock is synchronized with the Compose environment, so you no longer need to manage the scheduler manually.

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

## Main Looper and Threads

### Looper Modes

- `Robolectric#getForegroundThreadScheduler()`: This is only needed in the LEGACY looper mode. We strongly encourage you to use the PAUSED looper mode (which is the default)
- `Robolectric#getBackgroundThreadScheduler()`: This is only needed in the LEGACY looper mode. We strongly encourage you to use the PAUSED looper mode (which is the default)

#### LooperMode.PAUSED

A mode that more accurately models real Android's Looper behavior. Conceptually `LooperMode.PAUSED` is similar to the `LEGACY` `Scheduler.IdleState.PAUSED` in the following ways:

- Tests run on the main looper thread
- Tasks posted to the main Looper are not executed automatically, and must be explicitly executed via `ShadowLooper` APIs like `ShadowLooper.idle()`. This guarantees execution order correctness
- `SystemClock` time is frozen, and can be manually advanced via Robolectric APIs.

However, it has the following improvements:

- Robolectric will warn users if a test fails with unexecuted tasks in the main Looper queue.
- Robolectric test APIs, like `ActivityController.setup()`, will automatically idle the main Looper.
- Each Looper has its own thread. Tasks posted to background loopers are executed asynchronously in separate threads.

#### LooperMode.INSTRUMENTATION_TEST

A mode that simulates an android instrumentation test threading model, which has a separate test thread distinct from the main looper thread.

#### LooperMode.LEGACY

Deprecated. use `LooperMode.PAUSED`. LEGACY mode is not supported on Android SDKs > Baklava

### Limiting Threads

DO limit the number of threads that are running during each test. Rogue threads often cause test pollution because they are not automatically cleaned up between tests. Oftentimes threads are inadvertently spawned when using third-party libraries (e.g., for networking) or background processing components. One of the main sources of additional threads during tests are `ExecutorServices` that maintain thread pools. If possible, mock dependent components that spawn threads, or use `MoreExecutors.directExecutor()`. If it's necessary to run multiple threads during a test, make sure to explicitly stop all threads and `ExecutorServices` to avoid test pollution.

## Best Practices

DON'T mock or spy on Android classes that will be acted on by other Android code (e.g. `Context`, `SharedPreferences`, and many others). Stubbing is very brittle and can lead to breakages on Robolectric or Android Platform upgrades. The small exceptions to this rule are classes with very narrow responsibilities, such as event listeners.

## Input Mode Leakage

Tests can fail during migration if they rely on non-touch input modes configured through instrumentation APIs before the test starts.

Within the setup functions for tests, the system enforces `InputMode.Touch` by default at the start of each test for more determinism and to prevent state leakage, overriding ambient device state and pre-test setup. To resolve this, specify the required input mode in `ComposeUiTestConfig`:

```kotlin
class FocusTest {
    @get:Rule
    val rule = createComposeRule(
        config = ComposeUiTestConfig(inputMode = InputMode.Keyboard)
    )

    @Test
    fun testFocus() {}
}
```

To configure the input mode for individual test cases instead of the entire test class, pass `ComposeUiTestConfig` to `runComposeUiTest`:

```kotlin
class FocusTest {
    @Test
    fun testTouchMode() = runComposeUiTest {
        // Runs with the default InputMode.Touch
    }

    @Test
    fun testKeyboardMode() = runComposeUiTest(
        ComposeUiTestConfig(inputMode = InputMode.Keyboard)
    ) {
        // Runs with InputMode.Keyboard
    }
}
```

## Related References

- **Debugging**: See [debugging.md](debugging.md) for printing the semantics tree and failure artifacts
- **Synchronization**: See [synchronization.md](../core/synchronization.md) for `waitForIdle`, `waitUntil*`, idling resources
- **Clock control**: See [clock-control.md](../advanced/clock-control.md) for `MainTestClock`
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md) for `LooperMode.PAUSED`
- **Coroutines**: See [coroutines.md](../testing-patterns/coroutines.md) for test dispatchers
- **Test doubles**: See [test-doubles.md](../architecture/test-doubles.md) for shadows and mocks

## Sources

- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://robolectric.org/upgrade_to_version_4
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.Mode.html
- https://robolectric.org/best-practices
