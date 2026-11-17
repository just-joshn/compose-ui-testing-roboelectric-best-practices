# Debugging and Managing Flaky Tests

## Table of Contents

1. [Compose Synchronization Causes](#compose-synchronization-causes)
2. [Coroutine Timing (v1 vs v2 Rules)](#coroutine-timing-v1-vs-v2-rules)
3. [Looper and Thread Causes](#looper-and-thread-causes)
4. [Test Environment Leakage](#test-environment-leakage)
5. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
6. [Related References](#related-references)
7. [Sources](#sources)

## Compose Synchronization Causes

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

### Idling resources

Compose can synchronize tests and the UI so that every action and assertion is done in an idle state, waiting or advancing the clock as needed. However, some asynchronous operations whose results affect the UI state can be run in the background while the test is unaware of them.

Create and register these *idling resources* in your test so that they're taken into account when deciding whether the app under test is busy or idle.

```kotlin
composeTestRule.registerIdlingResource(idlingResource)
composeTestRule.unregisterIdlingResource(idlingResource)
```

### Manual synchronization

The `waitForIdle()` function waits for Compose to be idle, but the function depends on the `autoAdvance` property:

```kotlin
composeTestRule.mainClock.autoAdvance = true // Default
composeTestRule.waitForIdle() // Advances the clock until Compose is idle.

composeTestRule.mainClock.autoAdvance = false
composeTestRule.waitForIdle() // Only waits for idling resources to become idle.
```

Note that in both cases, `waitForIdle()` also waits for pending draw and layout passes.

### Wait for conditions

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

## Coroutine Timing (v1 vs v2 Rules)

While the v1 APIs relied on the `UnconfinedTestDispatcher`, the v2 APIs use the `StandardTestDispatcher` by default for the running composition. This change aligns Compose test behavior with the standard `runTest` APIs and provides explicit control over coroutine execution order.

The v2 testing API changes are included in `androidx.compose.ui:ui-test-junit4:1.11.0-alpha03+` and `androidx.compose.ui:ui-test:1.11.0-alpha03+`.

The primary difference between v1 and v2 of the APIs is how coroutines are dispatched:

- v1 APIs (`UnconfinedTestDispatcher`): When a coroutine was launched, it executed immediately on the current thread, often finishing before the next line of test code ran. Unlike production behavior, this immediate execution could inadvertently mask real timing issues or race conditions that would occur in a live application.
- v2 APIs (`StandardTestDispatcher`): When a coroutine is launched, it is queued and does not execute until the test explicitly advances the virtual clock. Standard Compose test APIs (such as `waitForIdle()`) already handle this synchronization, so most tests relying on these standard APIs should continue to work with no changes.

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

In scenarios involving manual synchronization, such as when auto-advancing is disabled, launching a coroutine does not result in immediate execution because the test clock is paused. To execute coroutines in the queue without advancing the virtual clock, use the `runCurrent()` API. This runs tasks scheduled for the current virtual time.

```kotlin
composeTestRule.mainClock.scheduler.runCurrent()
```

In contrast to `waitForIdle()`, which advances the test clock until the UI stabilizes, `runCurrent()` executes pending tasks while maintaining the current virtual time.

If you're using Compose test APIs alongside the Kotlin `runTest` API, it's strongly recommended to switch to `runComposeUiTest`. The `runComposeUiTest` API automatically executes your test block within its own `runTest` scope. The test clock is synchronized with the Compose environment, so you no longer need to manage the scheduler manually.

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

## Looper and Thread Causes

On its AndroidX Test page, in the `ActivityScenario` example, Robolectric says: note that in Robolectric since both the test and UI event loop run on the same thread, synchronization is not an issue.

Robolectric's upgrade guide says that `Robolectric#getForegroundThreadScheduler()` and `Robolectric#getBackgroundThreadScheduler()` are only needed in the LEGACY looper mode, and: "We strongly encourage you to use the PAUSED looper mode (which is the default)".

The 2019 Robolectric blog post on PAUSED LooperMode lists these highlights of the `PAUSED` mode vs. the existing `LEGACY` mode:

- Tasks posted to the main Looper are not automatically executed inline. Similar to the legacy `PAUSED` IdleState, tasks posted to the main Looper must be explicitly executed via `ShadowLooper` APIs.
- Robolectric will warn users if a test fails with unexecuted tasks in the main Looper queue. This is a hint that the unexecuted behavior is important for the test case.
- AndroidX Test APIs, like `ActivityScenario`, `FragmentScenario` and Espresso will automatically idle the main Looper.
- Tasks posted to background Loopers are executed in real threads.

```java
List<String> events = new ArrayList<>();
events.add("before");
new Handler(Looper.getMainLooper()).post(() -> events.add("after"));
events.add("between");
// the 'after' task is posted, but has not been executed yet
assertThat(events).containsExactly("before", "between").inOrder();
// execute all tasks posted to main Looper
shadowOf(getMainLooper()).idle();
assertThat(events).containsExactly("before", "between", "after").inOrder();
```

The post's troubleshooting section says: if you see test failures like `Main looper has queued unexecuted runnables`, you may need to insert `shadowOf(getMainLooper()).idle()` calls to your test to drain the main Looper. It's recommended to step through your test code with a watch set on `Looper.getMainLooper().getQueue()` to see the status of the Looper queue, to determine the appropriate point to add a `shadowOf(getMainLooper()).idle()` call.

The post's troubleshooting section also says: use of Animations can cause delayed tasks to be posted to the main Looper queue. You can use the `ShadowLooper.idleFor()` or `ShadowLooper.runToEndOfTasks()` APIs to execute these tasks.

### Thread hygiene

DO limit the number of threads that are running during each test. Rogue threads often cause test pollution because they are not automatically cleaned up between tests. Oftentimes threads are inadvertently spawned when using third-party libraries (e.g., for networking) or background processing components. One of the main sources of additional threads during tests are `ExecutorServices` that maintain thread pools. If possible, mock dependent components that spawn threads, or use `MoreExecutors.directExecutor()`. If it's necessary to run multiple threads during a test, make sure to explicitly stop all threads and `ExecutorServices` to avoid test pollution.

## Test Environment Leakage

Within the setup functions for tests, the system enforces `InputMode.Touch` by default at the start of each test for more determinism and to prevent state leakage, overriding ambient device state and pre-test setup. To configure the input mode for individual test cases instead of the entire test class, pass `ComposeUiTestConfig` to `runComposeUiTest`:

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

The `ComposeUiTestConfig` class is included, starting in version 1.13, in the `junit4` and `ui-test` parts of the `androidx.compose.ui` AndroidX artifact (`androidx.compose.ui:ui-test-junit4:1.13.0-alpha01+` and `androidx.compose.ui:ui-test:1.13.0-alpha01+`).

You can explicitly configure the set of resource qualifiers in effect for a test:

```kotlin
class SandwichTest {
  @Test
  @Config(qualifiers = "fr-xlarge")
  fun getSandwichName() {
    assertThat(sandwich.name).isEqualTo("Grande Croque Monégasque")
  }
}
```

## Anti-Patterns to Avoid

- In some cases, using mechanisms in a test like an external `CountDownLatch` instead of the `waitUntil` APIs could behave unexpectedly, since the test clock won't be advanced.
- Using `createComposeRule` in conjunction with `runTest` creates two separate clocks: one for Compose, and one for the test coroutine scope. The migration guide marks this approach NOT RECOMMENDED.
- DON'T mock or spy on Android classes that will be acted on by other Android code (e.g. `Context`, `SharedPreferences`, and many others). Stubbing is very brittle and can lead to breakages on Robolectric or Android Platform upgrades.

## Related References

- **Debugging**: See [debugging.md](debugging.md) for printing the semantics tree and failure artifacts
- **Synchronization**: See [synchronization.md](../core/synchronization.md) for `waitForIdle`, `waitUntil*`, idling resources
- **Clock control**: See [clock-control.md](../advanced/clock-control.md) for `MainTestClock`
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md) for `LooperMode.PAUSED`
- **Coroutines**: See [coroutines.md](../testing-patterns/coroutines.md) for test dispatchers
- **Test doubles**: See [test-doubles.md](../architecture/test-doubles.md) for fakes and DI seams

## Sources

- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://robolectric.org/best-practices
- https://robolectric.org/androidx_test
- https://robolectric.org/configuring
- https://robolectric.org/upgrade_to_version_4
- https://robolectric.org/blog/2019/06/04/paused-looper
