# Synchronization & Waiting

## Table of Contents

1. [Automatic Synchronization](#automatic-synchronization)
2. [Disabling Automatic Synchronization](#disabling-automatic-synchronization)
3. [Idling Resources](#idling-resources)
4. [Manual Synchronization](#manual-synchronization)
5. [Waiting for Conditions](#waiting-for-conditions)
6. [Main Thread Synchronization](#main-thread-synchronization)
7. [Robolectric Looper](#robolectric-looper)
8. [Warnings](#warnings)
9. [Related References](#related-references)
10. [Sources](#sources)

## Automatic Synchronization

Compose tests are synchronized by default with your UI. When you call an assertion or an action with the `ComposeTestRule`, the test is synchronized beforehand, waiting until the UI tree is idle.

When a test is synchronized, your Compose app is advanced in time using a virtual clock. This means Compose tests don't run in real time, so they can pass as fast as possible.

By default, all interactions from the test with the compose tree (finding nodes, performing gestures, making assertions) will be synchronized with pending work in Compose's internals (such as applying state changes, recomposing, measuring, etc).

### Tests That Do Not Synchronize

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

## Disabling Automatic Synchronization

When you call an assertion or action through the `ComposeTestRule` such as `assertExists()`, your test is synchronized with the Compose UI. In some cases you might want to stop this synchronization and control the clock yourself. For example, you can control time to take accurate screenshots of an animation at a point where the UI would still be busy. To disable automatic synchronization, set the `autoAdvance` property in the `mainClock` to `false`:

```kotlin
composeTestRule.mainClock.autoAdvance = false
```

You can advance exactly one frame with `advanceTimeByFrame()` or by a specific duration with `advanceTimeBy()`:

```kotlin
composeTestRule.mainClock.advanceTimeByFrame()
composeTestRule.mainClock.advanceTimeBy(milliseconds)
```

`MainTestClock` is responsible for driving all the recompositions, animations, and gestures. The API doesn't control Android's measure and draw passes.

## Idling Resources

`IdlingResource`: Represents a resource of an application under test which can cause asynchronous background work to happen during test execution (e.g. an http request in response to a button click).

However, any asynchronous work that is not done through one of Compose's mechanisms won't be included in the default synchronization. For such work, test authors can create an `IdlingResource` and register it into the test with `androidx.compose.ui.test.junit4.ComposeTestRule` `.registerIdlingResource`, and the interaction will wait for that resource to become idle prior to performing it.

Create and register these idling resources in your test so that they're taken into account when deciding whether the app under test is busy or idle. You don't have to take action unless you need to register additional idling resources, for example, if you run a background job that is not synchronized with Espresso or Compose.

### Registering an IdlingResource

This API is very similar to Espresso's Idling Resources to indicate whether the subject under test is idle or busy. Use the Compose test rule to register the implementation of the `IdlingResource`:

```kotlin
composeTestRule.registerIdlingResource(idlingResource)
composeTestRule.unregisterIdlingResource(idlingResource)
```

### IdlingResource Members

| Member | Description |
| --- | --- |
| `isIdleNow` | Whether or not the `IdlingResource` is idle when reading this value. This should always be called from the main thread, which is why it should be lightweight and fast. |
| `getDiagnosticMessageIfBusy()` | Returns diagnostics that explain why the idling resource is busy, or `null` if the resource is not busy. Default implementation returns `null`. |

If one idling resource returns `false`, the synchronization system will keep polling all idling resources until they are all idle.

## Manual Synchronization

In certain cases, you have to synchronize the Compose UI with other parts of your test or the app you're testing.

### waitForIdle

The `waitForIdle()` function waits for Compose to be idle, but the function depends on the `autoAdvance` property:

```kotlin
composeTestRule.mainClock.autoAdvance = true // Default
composeTestRule.waitForIdle() // Advances the clock until Compose is idle.

composeTestRule.mainClock.autoAdvance = false
composeTestRule.waitForIdle() // Only waits for idling resources to become idle.
```

Note that in both cases, `waitForIdle()` also waits for pending draw and layout passes.

Waits for the UI to become idle. Quiescence is reached when there are no more pending changes (e.g. pending recompositions or a pending draw call) and all `IdlingResource`s are idle.

### runOnIdle

Executes the given action in the same way as `runOnUiThread` but waits until the app is idle before executing the action. This is the recommended way of doing your assertions on shared variables.

### advanceTimeUntil

Also, you can advance the clock until a certain condition is met with `advanceTimeUntil()`.

```kotlin
composeTestRule.mainClock.advanceTimeUntil(timeoutMs) { condition }
```

Note that the given condition should be checking the state that can be affected by this clock (it only works with Compose state).

### Synchronization APIs

| API | Description |
| --- | --- |
| `waitForIdle()` | Waits for the UI to become idle. |
| `awaitIdle()` | Suspends until the UI is idle. |
| `runOnUiThread` | Runs the given action on the UI thread. This method is blocking until the action is complete. |
| `hasPendingWork()` | Returns whether the Compose UI has any pending work. |

## Waiting for Conditions

Any condition that depends on external work, such as data loading or Android's measure or draw (that is, measure or draw external to Compose), should use a more general concept such as `waitUntil()`:

```kotlin
composeTestRule.waitUntil(timeoutMs) { condition }
```

### waitUntil Behavior

Blocks until the given condition is satisfied. If auto advancement is enabled on the `mainClock`, this method will actively advance the clock to process any pending composition, invalidation and animation. If auto advancement is not enabled, the clock will not be advanced actively which means that the Compose UI appears to be frozen. It is still valid to use this method in this way, if the condition will be satisfied by something not driven by our clock.

Compared to `MainTestClock.advanceTimeUntil`, `waitUntil` sleeps after every iteration to yield to other processes. This gives `waitUntil` a better integration with the host, but it is less preferred from a performance viewpoint. Therefore, we recommend that you try using `MainTestClock.advanceTimeUntil` before resorting to `waitUntil`.

- `conditionDescription`: An optional human-readable description of condition that will be included in the timeout exception if thrown.
- `MainTestClock.advanceTimeUntil`
  - `timeoutMillis`: The time after which this method throws an exception if the given condition is not satisfied. This is test clock time, not the wall clock or cpu time.
- `ComposeTestRule.waitUntil`
  - `timeoutMillis`: The time after which this method throws an exception if the given condition is not satisfied. This observes wall clock time, not test clock time.

### waitUntil Helpers

You can also use any of the `waitUntil` helpers:

```kotlin
composeTestRule.waitUntilAtLeastOneExists(matcher, timeoutMs)

composeTestRule.waitUntilDoesNotExist(matcher, timeoutMs)

composeTestRule.waitUntilExactlyOneExists(matcher, timeoutMs)

composeTestRule.waitUntilNodeCount(matcher, count, timeoutMs)
```

Deprecated `waitUntilNodeCount`, `waitUntilAtLeastOneExists`, `waitUntilExactlyOneExists`, and `waitUntilDoesNotExist` helper APIs that do not accept `useUnmergedTree`. Added new overloads that accept `useUnmergedTree` to support waiting for nodes in the unmerged semantics tree.

- `waitUntilAtLeastOneExists`: Blocks until at least one node matches the given matcher.
- `waitUntilDoesNotExist`: Blocks until no nodes match the given matcher.
- `waitUntilExactlyOneExists`: Blocks until exactly one node matches the given matcher.
- `waitUntilNodeCount`: Blocks until the number of nodes matching the given matcher is equal to the given count.
- `useUnmergedTree`: If true, searches the unmerged semantics tree instead of the merged semantics tree.
- `timeoutMillis`: This observes wall clock time, not frame time.

## Main Thread Synchronization

Changes to support main thread synchronization are included in `androidx.compose.ui:ui-test-junit4:1.13.0-alpha01+` and `androidx.compose.ui:ui-test:1.13.0-alpha01+`.

Compose testing now supports main thread synchronization, allowing you to safely call `waitForIdle`— and by extension, Compose UI actions and assertions — directly from the main thread.

With main thread synchronization enabled, the Compose test framework can now advance the clock and process pending work even when blocking calls are made on the main thread.

While keeping tests on the background thread remains the standard for pure Compose tests, main thread synchronization is highly advantageous in a few specific scenarios:

- Complex View interoperability: When testing hybrid UIs containing both Compose and legacy Android Views, manipulating Views often requires running on the main thread. You can now interact with Views and assert on Compose nodes sequentially without constantly switching thread contexts.
- Synchronous state mutations: If your architecture relies on strictly main-thread-bound state holders, you can now mutate state and immediately wait for the Compose UI to settle without leaving the main thread.
- Custom test runners: If you are building custom testing infrastructure or utilizing environments where the test runner inherently executes on the main thread, Compose tests now execute cleanly without requiring background-thread delegation.

Note: For standard, Compose-only tests, you don't need to change your existing test code. The default background-thread execution remains fully supported and performant.

With main thread synchronization enabled, the assertions for Compose and View hierarchies can be executed in the same block:

```kotlin
@Test
fun testBidirectionalInteropUIUpdates_new() {
    val scenario = launchFragmentInContainer<InteropFragment>()
    composeTestRule.waitForIdle()
    scenario.onFragment { fragment ->
        fragment.legacyButton.performClick()
        composeTestRule.waitForIdle()
        composeTestRule.onNodeWithText("Legacy Clicks: 1").assertIsDisplayed()
        composeTestRule.onNodeWithText("Increment Legacy TextView").performClick()
        composeTestRule.waitForIdle()
        assert(fragment.legacyTextView.text.toString() == "Compose Clicks: 1")
    }
}
```

## Robolectric Looper

Currently Robolectric will default to `LooperMode.Mode.PAUSED` behavior, but this can be overridden by applying a `@LooperMode(NewMode)` annotation to a test package, test class, or test method, or via the 'robolectric.looperMode' system property.

### PAUSED Mode

`PAUSED`: A mode that more accurately models real Android's Looper behavior.

Conceptually `LooperMode.PAUSED` is similar to the `LEGACY` `Scheduler.IdleState.PAUSED` in the following ways:

- Tests run on the main looper thread
- Tasks posted to the main Looper are not executed automatically, and must be explicitly executed via `ShadowLooper` APIs like `ShadowLooper.idle()`.
- `SystemClock` time is frozen, and can be manually advanced via Robolectric APIs.

However, it has the following improvements:

- Robolectric will warn users if a test fails with unexecuted tasks in the main Looper queue
- Robolectric test APIs, like `ActivityController.setup()`, will automatically idle the main Looper

### Draining the Main Looper

If you see an test failures like 'Main looper has queued unexecuted runnables.', you may need to insert `shadowOf(getMainLooper()).idle()` calls to your test to drain the main Looper.

### INSTRUMENTATION_TEST Mode

`INSTRUMENTATION_TEST`: A mode that simulates an android instrumentation test threading model, which has a separate test thread distinct from the main looper thread. It is recommended to use this mode in tests that mostly use androidx.test APIs, which will support being called directly on the main thread or on the test thread.

## Warnings

Warning: In some cases, using mechanisms in a test like an external `CountDownLatch` instead of the `waitUntil` APIs could behave unexpectedly, since the test clock won't be advanced.

Depending on the platform, measure, layout or draw passes might not happen in between advancements of the clock while waiting for the condition to become true. On Android and Desktop, measure and layout are happening, but draw only happens on Desktop. If your condition relies on the result of draw, use `androidx.compose.ui.test.junit4.ComposeTestRule.waitUntil` instead.

## Related References

- **Clock control and animations**: See [clock-control.md](../advanced/clock-control.md)
- **Looper and graphics modes**: See [runtime-modes.md](runtime-modes.md)
- **Flaky tests**: See [flaky-tests.md](../debugging/flaky-tests.md)
- **Coroutines and queued work**: See [coroutines.md](../testing-patterns/coroutines.md)
- **Assertions**: See [assertions-actions.md](assertions-actions.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/IdlingResource
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.Mode.html
