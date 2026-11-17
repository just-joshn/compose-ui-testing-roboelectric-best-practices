# Debugging and Managing Flaky Tests

## Table of Contents

1. [Understanding Flakiness Types](#understanding-flakiness-types)
2. [Compose Synchronization Causes](#compose-synchronization-causes)
3. [Coroutine Timing (v1 vs v2 Rules)](#coroutine-timing-v1-vs-v2-rules)
4. [Looper and Thread Causes](#looper-and-thread-causes)
5. [Test Environment Leakage](#test-environment-leakage)
6. [Retries](#retries)
7. [Prevention Strategies](#prevention-strategies)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Related References](#related-references)
10. [Sources](#sources)

## Understanding Flakiness Types

A test that does not behave deterministically is flaky. In Compose and Robolectric tests the common causes cluster by where the nondeterminism comes from:

| Category               | Symptoms                                    | Common Causes                                                              |
| ---------------------- | ------------------------------------------- | -------------------------------------------------------------------------- |
| **Sync-driven**        | Assertion sees old UI, node not found       | Unknown background work, mutated state with no sync point, queued coroutine |
| **Clock-driven**       | Animation or delay assertions off by a frame | Auto-advance on when it should be off, assertion before draw pass          |
| **Looper/thread-driven** | Passes alone, fails in a suite            | Unexecuted main-looper tasks, rogue `ExecutorService` threads              |
| **State-driven**       | Order-dependent failures                    | Leaked input mode, shared singletons, shared mutable fakes                 |
| **Environment-driven** | CI-only failures                            | SDK/JDK differences, android-all download problems, platform rendering     |

### Flakiness Decision Tree

```
Test fails intermittently
├─ Assertion runs before the UI reflects the change?
│  ├─ Compose-only state → missing sync point → waitForIdle / assert via the rule
│  ├─ Coroutine launched, v2 rule → queued on StandardTestDispatcher → waitForIdle / runOnIdle
│  └─ Background work Compose cannot see → idling resource or waitUntil*
│
├─ Fails only when run after other tests?
│  └─ State leak, rogue threads → see Test Environment Leakage
│
├─ Fails only on CI?
│  └─ Environment → see ci-cd.md
│
└─ Fails on device but not on Robolectric (or reverse)?
   └─ Fidelity gap → see test-architecture.md
```

## Compose Synchronization Causes

Compose tests are synchronized with the UI by default: an assertion or action through the rule first waits until the UI is idle, and the virtual clock lets tests run as fast as possible. Flakiness appears when you step outside that contract.

```kotlin
// Bad: state changes, but nothing triggers recomposition before the check
var lastSeenValue = 0
composeTestRule.setContent {
    val value by myCounter.collectAsState()
    lastSeenValue = value
}
myCounter.value = 1
assertTrue(lastSeenValue == 1) // fails: no recomposition yet

// Good: the assertion goes through the rule, which syncs first
myCounter.value = 1
composeTestRule.onNodeWithText("1").assertExists()
```

Sync only covers Compose hierarchies, not the rest of your app. For work Compose cannot see, pick by test size:

| Situation                                   | Tool                                                    |
| ------------------------------------------- | ------------------------------------------------------- |
| Small UI test, known background work        | `registerIdlingResource` / `unregisterIdlingResource`   |
| Bigger UI test, waiting for an outcome      | `waitUntil*` APIs                                       |
| Manual frame stepping                       | `mainClock.autoAdvance = false`, `advanceTimeBy(...)`   |

```kotlin
// Good: wait for a condition, not for a duration
composeTestRule.waitUntilAtLeastOneExists(hasText("Loaded"), 5_000)
composeTestRule.waitUntilDoesNotExist(hasTestTag("spinner"), 5_000)
composeTestRule.waitUntilNodeCount(hasTestTag("row"), 10, 5_000)

// Bad: arbitrary pause
Thread.sleep(2_000)

// Bad: external latch; the test clock is not advanced, so behavior is unpredictable
latch.await()
```

Android's stability guide says to avoid pausing tests for an arbitrary period: it makes tests slow or flaky, because the same test can take different time on different machines. Idling resources can be hard to install without polluting the code under test, which is why the wait-until APIs are preferred as tests grow. Full API details live in [synchronization.md](../core/synchronization.md).

## Coroutine Timing (v1 vs v2 Rules)

The v1 rules used an `UnconfinedTestDispatcher`: a launched coroutine ran immediately, which could mask real race conditions. The v2 rules (`androidx.compose.ui.test.junit4.v2.*`, `androidx.compose.ui.test.v2.*`; available from 1.11.0-alpha03) use a `StandardTestDispatcher`: launched work is queued until the test advances the virtual clock.

```kotlin
// After moving to v2, this can fail: the coroutine is queued, UI still shows "Loading"
composeTestRule.setContent { ProfileScreen(viewModel) }
assertEquals("Done", viewModel.state.value)

// Good
composeTestRule.waitForIdle()
// or
composeTestRule.runOnIdle { assertEquals("Done", viewModel.state.value) }
```

If you turn `autoAdvance` off, `composeTestRule.mainClock.scheduler.runCurrent()` runs queued tasks at the current virtual time without advancing the clock; `waitForIdle()` advances until idle.

```kotlin
// Bad: two separate clocks, not recommended
@Test
fun twoClocks() = runTest {
    composeTestRule.setContent { /* ... */ }
}

// Good: runComposeUiTest runs inside its own runTest scope with a synchronized clock
@Test
fun oneClock() = runComposeUiTest {
    setContent { /* ... */ }
    mainClock.advanceTimeBy(1000 + 16 /* frame buffer */)
    onNodeWithText("Done!").assertExists()
}
```

See [coroutines-viewmodels.md](../testing-patterns/coroutines-viewmodels.md) for dispatcher injection and [clock-control.md](../advanced/clock-control.md) for clock stepping.

## Looper and Thread Causes

Robolectric runs the test and the UI event loop on the same thread, so classic cross-thread races are rarer than on a device. The remaining causes are about the looper model and stray threads.

- `PAUSED` is the default looper mode and Robolectric strongly encourages it: tasks posted to the main `Looper` are not run inline, so ordering matches a real device. Legacy mode ran posted tasks immediately, earlier than a device would.
- Tasks posted to the main `Looper` outside Compose or AndroidX Test APIs must be drained explicitly. `ActivityScenario`, `FragmentScenario`, and Espresso idle it for you.
- Tasks posted to background `Looper`s run on real threads in `PAUSED` mode.

```kotlin
// Good: drain the main looper at the point your code under test needs it
Handler(Looper.getMainLooper()).post { events.add("after") }
events.add("between")
shadowOf(Looper.getMainLooper()).idle()
assertThat(events).containsExactly("before", "between", "after").inOrder()
```

If a test fails with `Main looper has queued unexecuted runnables`, the unexecuted behavior probably matters to that test; step through with a watch on `Looper.getMainLooper().getQueue()` to find where the `idle()` call belongs. See [runtime-modes.md](../core/runtime-modes.md).

### Thread hygiene

Robolectric's best-practices page: limit the number of threads running during each test. Rogue threads such as `ExecutorService` pools cause test pollution.

```kotlin
// Good: run work inline in tests (Guava)
val executor = MoreExecutors.directExecutor()

// Bad: a real pool left running after the test
val pool = Executors.newFixedThreadPool(4) // never shut down
```

Stop threads explicitly in teardown if a test must start them, and inject executors and dispatchers so tests can replace them ([test-doubles.md](../architecture/test-doubles.md)).

## Test Environment Leakage

- v2 rules enforce `InputMode.Touch` at the start of each test so input mode cannot leak. If you need keyboard mode, set it per class or per test via `ComposeUiTestConfig(inputMode = InputMode.Keyboard)` (`ComposeUiTestConfig` is 1.13.0-alpha01+).
- `@Config(qualifiers = ...)` and `RuntimeEnvironment.setQualifiers(...)` change the simulated device configuration. Scope them to the class or method that needs them.
- Do not mock or spy on Android classes (`Context`, `SharedPreferences`); stubbing is brittle. Use real Robolectric objects or fakes.

## Retries

The Android stability guide: you should fix flaky tests, but retries can maintain productivity when the failure condition is too improbable to reproduce. Typical mechanisms:

- A JUnit rule that retries a test a number of times
- A retry step in the CI workflow
- A system to restart an emulator that is unresponsive, such as Gradle-managed devices (device tests only)

"Add retrying mechanisms to big tests, but always fix flaky tests." The sources do not name a specific retry library or Gradle setting for local Robolectric runs, so none is shown here.

## Prevention Strategies

### Isolation Checklist

- [ ] Every wait is a condition (`waitUntil*`, `waitForIdle`, idling resource), never a sleep
- [ ] Assertions go through the rule or follow `waitForIdle()` / `runOnIdle`
- [ ] Coroutine dispatchers and executors are injected and replaced in tests
- [ ] No `ExecutorService` pool outlives a test
- [ ] Data comes from deterministic fakes, not network or shared state
- [ ] Tests run with the default `PAUSED` looper mode
- [ ] State changes read during draw are followed by `waitForIdle()`, not `advanceTimeBy`
- [ ] Tests do not depend on another test having run first

### Keep Tests Small and Scoped

As a test grows in scope, its chances of becoming flaky increase. Test one component or feature with fakes on Robolectric, and leave true end-to-end flows to device tests. See [test-architecture.md](../architecture/test-architecture.md).

## Anti-Patterns to Avoid

| Anti-Pattern                                   | Problem                                      | Solution                                              |
| ---------------------------------------------- | -------------------------------------------- | ----------------------------------------------------- |
| `Thread.sleep()` as the wait                   | Slow and flaky                               | `waitUntil*`, `waitForIdle`, idling resources         |
| External `CountDownLatch` instead of `waitUntil` | Test clock never advances                  | `waitUntil` APIs                                      |
| `createComposeRule()` combined with `runTest`  | Two separate clocks (not recommended)        | Use `runComposeUiTest { ... }`                        |
| Using `UnconfinedTestDispatcher` to "fix" v2 failures | Masks real race conditions            | `waitForIdle()` / `runOnIdle`                         |
| Retrying until pass, never investigating       | Hides systemic problems                      | Retries as a safety net; fix the root cause           |
| Un-stopped thread pools                        | Pollutes later tests                         | `directExecutor()` or stop threads explicitly         |
| Mocking `Context`, `SharedPreferences`         | Brittle, hides real behavior                 | Real Robolectric environment or fakes                 |
| Using `advanceTimeBy` for draw-dependent state | UI does not update                           | `waitForIdle()`                                       |

## Related References

- **Debugging**: See [debugging.md](debugging.md) for printing the semantics tree and failure artifacts
- **Synchronization**: See [synchronization.md](../core/synchronization.md) for `waitForIdle`, `waitUntil*`, idling resources
- **Clock control**: See [clock-control.md](../advanced/clock-control.md) for `MainTestClock`
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md) for `LooperMode.PAUSED`
- **Coroutines**: See [coroutines-viewmodels.md](../testing-patterns/coroutines-viewmodels.md) for test dispatchers
- **Test doubles**: See [test-doubles.md](../architecture/test-doubles.md) for fakes and DI seams
- **CI**: See [ci-cd.md](../infrastructure-ci-cd/ci-cd.md) for environment-specific failures

## Sources

- https://developer.android.com/training/testing/instrumented-tests/stability
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://robolectric.org/best-practices/
- https://robolectric.org/androidx_test/
- https://robolectric.org/upgrade_to_version_4/
- https://robolectric.org/blog/2019/06/04/paused-looper/
- https://developer.android.com/training/testing/fundamentals
