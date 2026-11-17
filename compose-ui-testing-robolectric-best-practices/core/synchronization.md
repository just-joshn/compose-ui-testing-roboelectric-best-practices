# Synchronization & Waiting

## Table of Contents

1. [Automatic Synchronization](#automatic-synchronization)
2. [Disabling Automatic Synchronization](#disabling-automatic-synchronization)
3. [Idling Resources](#idling-resources)
4. [Manual Synchronization](#manual-synchronization)
5. [Main Thread Synchronization](#main-thread-synchronization)
6. [Waiting for Conditions](#waiting-for-conditions)
7. [Robolectric Looper and Main Thread](#robolectric-looper-and-main-thread)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Related References](#related-references)
10. [Sources](#sources)

## Automatic Synchronization

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

## Disabling Automatic Synchronization

When you call an assertion or action through the `ComposeTestRule` such as `assertExists()`, your test is synchronized with the Compose UI. In some cases you might want to stop this synchronization and control the clock yourself. For example, you can control time to take accurate screenshots of an animation at a point where the UI would still be busy. To disable automatic synchronization, set the `autoAdvance` property in the `mainClock` to `false`:

```kotlin
composeTestRule.mainClock.autoAdvance = false
```

Typically you will then advance the time yourself. You can advance exactly one frame with `advanceTimeByFrame()` or by a specific duration with `advanceTimeBy()`:

```kotlin
composeTestRule.mainClock.advanceTimeByFrame()
composeTestRule.mainClock.advanceTimeBy(milliseconds)
```

`MainTestClock` is responsible for driving all the recompositions, animations, and gestures. The API doesn't control Android's measure and draw passes.

## Idling Resources

Compose can synchronize tests and the UI so that every action and assertion is done in an idle state, waiting or advancing the clock as needed. However, some asynchronous operations whose results affect the UI state can be run in the background while the test is unaware of them.

Create and register these idling resources in your test so that they're taken into account when deciding whether the app under test is busy or idle. You don't have to take action unless you need to register additional idling resources, for example, if you run a background job that is not synchronized with Espresso or Compose.

An `IdlingResource` represents a resource of an application under test which can cause asynchronous background work to happen during test execution (e.g. an http request in response to a button click).

Any asynchronous work that is not done through one of Compose's mechanisms won't be included in the default synchronization. For such work, test authors can create an `IdlingResource` and register it into the test with `ComposeTestRule.registerIdlingResource`, and the interaction will wait for that resource to become idle prior to performing it.

Use the Compose test rule to register the implementation of the `IdlingResource`:

```kotlin
composeTestRule.registerIdlingResource(idlingResource)
composeTestRule.unregisterIdlingResource(idlingResource)
```

`isIdleNow` tells whether or not the `IdlingResource` is idle when reading this value. This should always be called from the main thread, which is why it should be lightweight and fast.

If one idling resource returns `false`, the synchronization system will keep polling all idling resources until they are all idle.

`getDiagnosticMessageIfBusy()` returns diagnostics that explain why the idling resource is busy, or `null` if the resource is not busy. The default implementation returns `null`.

## Manual Synchronization

In certain cases, you have to synchronize the Compose UI with other parts of your test or the app you're testing.

The `waitForIdle()` function waits for Compose to be idle, but the function depends on the `autoAdvance` property:

```kotlin
composeTestRule.mainClock.autoAdvance = true // Default
composeTestRule.waitForIdle() // Advances the clock until Compose is idle.

composeTestRule.mainClock.autoAdvance = false
composeTestRule.waitForIdle() // Only waits for idling resources to become idle.
```

Note that in both cases, `waitForIdle()` also waits for pending draw and layout passes.

`waitForIdle()` waits for the UI to become idle. Quiescence is reached when there are no more pending changes (e.g. pending recompositions or a pending draw call) and all idling resources are idle.

`runOnIdle` executes the given action in the same way as `runOnUiThread`, but waits until the app is idle before executing the action. This is the recommended way of doing your assertions on shared variables.

Also, you can advance the clock until a certain condition is met with `advanceTimeUntil()`:

```kotlin
composeTestRule.mainClock.advanceTimeUntil(timeoutMs) { condition }
```

Note that the given condition should be checking the state that can be affected by this clock (it only works with Compose state).

## Main Thread Synchronization

Changes to support main thread synchronization are included in `androidx.compose.ui:ui-test-junit4:1.13.0-alpha01+` and `androidx.compose.ui:ui-test:1.13.0-alpha01+`.

Compose testing now supports main thread synchronization, allowing you to safely call `waitForIdle` and by extension, Compose UI actions and assertions directly from the main thread.

Previously, Compose testing strictly enforced a two-thread model: test execution occurred on a background test thread, while UI updates happened on the main thread. Calling synchronization methods like `waitForIdle` or `runOnIdle` from the main thread (for example, inside a `runOnUiThread` block) would throw an `IllegalStateException` because the framework enforced strict thread checks to prevent main-thread synchronization.

With main thread synchronization enabled, the Compose test framework can now advance the clock and process pending work even when blocking calls are made on the main thread.

While keeping tests on the background thread remains the standard for pure Compose tests, main thread synchronization is highly advantageous in a few specific scenarios:

- **Complex View interoperability**: When testing hybrid UIs containing both Compose and legacy Android Views, manipulating Views often requires running on the main thread. You can now interact with Views and assert on Compose nodes sequentially without constantly switching thread contexts.
- **Synchronous state mutations**: If your architecture relies on strictly main-thread-bound state holders, you can now mutate state and immediately wait for the Compose UI to settle without leaving the main thread.
- **Custom test runners**: If you are building custom testing infrastructure or utilizing environments where the test runner inherently executes on the main thread, Compose tests now execute cleanly without requiring background-thread delegation.

For standard, Compose-only tests, you don't need to change your existing test code. The default background-thread execution remains fully supported and performant.

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

## Waiting for Conditions

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

`waitUntil` blocks until the given condition is satisfied. If `autoAdvance` is enabled on the `mainClock`, it will actively advance the clock to process any pending composition, invalidation and animation. If auto advancement is not enabled, the clock will not be advanced actively which means that the Compose UI appears to be frozen. It is still valid to use it in this way, if the condition will be satisfied by something not driven by our clock.

Compared to `advanceTimeUntil`, `waitUntil` sleeps after every iteration to yield to other processes. This gives `waitUntil` a better integration with the host, but it is less preferred from a performance viewpoint. Therefore, we recommend that you try using `advanceTimeUntil` before resorting to `waitUntil`.

The `timeoutMillis` of `waitUntil` is the time after which the method throws an exception if the given condition is not satisfied. This observes wall clock time, not the `mainClock`. The exception is a `ComposeTimeoutException`.

`waitUntil` also has an overload with a `conditionDescription` parameter: an optional human-readable description of the condition that will be included in the timeout exception if thrown.

`waitUntilAtLeastOneExists` blocks until at least one node matches the given matcher. `waitUntilDoesNotExist` blocks until no nodes match the given matcher. `waitUntilExactlyOneExists` blocks until exactly one node matches the given matcher. `waitUntilNodeCount` blocks until the number of nodes matching the given matcher is equal to the given count.

The API reference lists these four `waitUntil` helpers as added in 1.13.0-rc01. Each takes a `useUnmergedTree` parameter that defaults to `false`; if true, it searches the unmerged semantics tree instead of the merged semantics tree.

## Robolectric Looper and Main Thread

Robolectric's AndroidX Test page says: "Note that in Robolectric since both the test and UI event loop run on the same thread, synchronization is not an issue." The same page says `ActivityScenario.onActivity` provides a safe way of accessing the Activity, should you need to.

Currently Robolectric will default to `LooperMode.Mode.PAUSED` behavior, but this can be overridden by applying a `@LooperMode(NewMode)` annotation to a test package, test class, or test method, or via the `robolectric.looperMode` system property.

The 2019 Robolectric blog post "Improving Robolectric's Looper simulation" lists, as highlights of the `PAUSED` mode versus the existing `LEGACY` mode: tasks posted to the main Looper are not automatically executed inline. Similar to the legacy PAUSED IdleState, tasks posted to the main Looper must be explicitly executed via ShadowLooper APIs.

The same post says AndroidX Test APIs, like `ActivityScenario`, `FragmentScenario` and Espresso will automatically idle the main Looper.

The same post says Robolectric will warn users if a test fails with unexecuted tasks in the main Looper queue. This is a hint that the unexecuted behavior is important for the test case.

The same post says: if you see test failures like `Main looper has queued unexecuted runnables`, you may need to insert `shadowOf(getMainLooper()).idle()` calls to your test to drain the main Looper.

```java
// execute all tasks posted to main Looper
shadowOf(getMainLooper()).idle();
```

The same post says under Animations: use of animations can cause delayed tasks to be posted to the main Looper queue. You can use the `ShadowLooper.idleFor()` or `ShadowLooper.runToEndOfTasks()` APIs to execute these tasks.

Robolectric's 2026 blog on local-testing libraries says that one boolean swaps an internal `IdlingStrategy`: Espresso on a device, and on the JVM a main-thread loop that pumps Compose and forces layout, where there is no draw pass. The blog calls itself an outside read of the code as it stands in mid-2026, not an official AndroidX position.

## Anti-Patterns to Avoid

- Using mechanisms in a test like an external `CountDownLatch` instead of the `waitUntil` APIs could behave unexpectedly, since the test clock won't be advanced.

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
- https://robolectric.org/androidx_test/
- https://robolectric.org/blog/2019/06/04/paused-looper/
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.html
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
