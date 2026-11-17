# Coroutines and ViewModel Testing

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Setup](#setup)
3. [Patterns](#patterns)
4. [Decision Guide](#decision-guide)
5. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
6. [Common Issues & Solutions](#common-issues--solutions)
7. [Related References](#related-references)
8. [Sources](#sources)

> **When to use**: Testing code that launches coroutines, ViewModels backed by `viewModelScope`, and Compose screens driven by ViewModel state.
> **Prerequisites**: [synchronization.md](../core/synchronization.md), [clock-control.md](../advanced/clock-control.md)

## Quick Reference

```kotlin
// Pure coroutine / ViewModel logic: no Compose, no Robolectric needed
@Test
fun loads() = runTest {                          // one runTest per test, expression body
    val dispatcher = StandardTestDispatcher(testScheduler)   // share the one scheduler
    val repo = Repository(dispatcher)
    repo.initialize().await()
}

// Compose + coroutines: use runComposeUiTest, not createComposeRule + runTest
@Test
fun done() = runComposeUiTest {
    setContent { Loader() }
    mainClock.advanceTimeBy(1000 + 16 /* Frame buffer */)
    onNodeWithText("Done!").assertIsDisplayed()
}
```

| Tool | Use for |
|---|---|
| `runTest` | Any test calling suspending code |
| `StandardTestDispatcher` | Queued, precise control (default in `runTest`) |
| `UnconfinedTestDispatcher` | Eager start; simple tests only |
| `Dispatchers.setMain` / `MainDispatcherRule` | Code using `viewModelScope` in local JVM tests |
| `runComposeUiTest` (v2) | Compose UI plus coroutine virtual time on one clock |

## Setup

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:$coroutines_version")
}
```

The Android guide uses the `kotlinx.coroutines.test` 1.6+ APIs. v2 Compose test APIs live in `androidx.compose.ui.test.v2` (`runComposeUiTest`) and `androidx.compose.ui.test.junit4.v2` (`createComposeRule`), available from `ui-test(-junit4):1.11.0-alpha03+`; 1.12.1 is stable.

## Patterns

### runTest and TestDispatchers

**Use when**: Calling suspending functions or testing code that starts coroutines.

`runTest` wraps a test in a `TestScope` whose default dispatcher is `StandardTestDispatcher`. It skips delays automatically and does not return while work is pending on its scheduler.

```kotlin
@Test
fun standardTest() = runTest {
    val userRepo = UserRepository()
    launch { userRepo.register("Alice") }
    launch { userRepo.register("Bob") }
    advanceUntilIdle()   // Good: yield so queued coroutines run
    assertEquals(listOf("Alice", "Bob"), userRepo.getAllUsers())
}
```

| Yield call | Effect |
|---|---|
| `advanceUntilIdle()` | Runs everything queued; a good default |
| `advanceTimeBy(ms)` | Advances virtual time, runs coroutines scheduled before that point |
| `runCurrent()` | Runs coroutines scheduled at the current virtual time |

`UnconfinedTestDispatcher` starts coroutines eagerly, which differs from production. If the test focuses on concurrency, prefer `StandardTestDispatcher`. All `TestDispatcher`s in a test must share one scheduler: `StandardTestDispatcher(testScheduler)`.

### Injecting Dispatchers

**Use when**: Production code switches threads with `withContext` or starts its own coroutines.

Code running on several real threads makes tests flaky, and delays are not skipped. Inject a `CoroutineDispatcher` (or `CoroutineContext`, or a `CoroutineScope`) and pass a `TestDispatcher` in tests.

```kotlin
// Bad: fire-and-forget, nothing to await
fun initialize() { scope.launch { initialized.set(true) } }

// Good: callers and tests can await completion
class BetterRepository(private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO) {
    private val scope = CoroutineScope(ioDispatcher)
    fun initialize() = scope.async { /* ... */ }
}

@Test
fun repoInitWorks() = runTest {
    val repository = BetterRepository(StandardTestDispatcher(testScheduler))
    repository.initialize().await()
}
```

To control a class that owns a scope, inject it and pass `this` (the `TestScope`) from `runTest`; use `backgroundScope` for coroutines that never complete.

### Replacing the Main Dispatcher

**Use when**: A local JVM test touches `viewModelScope`, which uses a hardcoded `Main` dispatcher.

```kotlin
class MainDispatcherRule(
    val testDispatcher: TestDispatcher = UnconfinedTestDispatcher(),
) : TestWatcher() {
    override fun starting(description: Description) { Dispatchers.setMain(testDispatcher) }
    override fun finished(description: Description) { Dispatchers.resetMain() }
}

class HomeViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun loadsMessage() = runTest {   // uses Main's scheduler
        val viewModel = HomeViewModel()
        viewModel.loadMessage()
        assertEquals("Greetings!", viewModel.message.value)
    }
}
```

Create every other `TestDispatcher` after `setMain`; new ones then share Main's scheduler. A `TestDispatcher` created as a test-class property is built before `setMain` and gets its own scheduler. Create the rule property first and reuse `mainDispatcherRule.testDispatcher` in other initializers.

The guide says not to replace `Main` in instrumented tests, where the real UI thread is available. It addresses plain local JVM tests and does not cover Robolectric. No source says whether to replace `Main` in a Robolectric Compose test, so do not assume the rule is needed or harmless there.

### Testing a ViewModel Without Compose

**Use when**: Verifying state logic. Android's guidance is to avoid direct framework dependencies in classes with business logic, so they run as plain JVM tests.

```kotlin
class FakeUserRepository : UserRepository { /* in-memory */ }

class UserStateTest {
    @Test
    fun addUserTest() = runTest {
        val userState = UserState(FakeUserRepository(), scope = this)
        userState.registerUser("Mona")
        advanceUntilIdle()   // let the coroutine complete and changes propagate
        assertEquals(listOf("Mona"), userState.users.value)
    }
}
```

Prefer fakes over mocks, and keep `Context` out of ViewModels. With Hilt, you do not need it in unit tests: construct classes and ViewModels directly with fakes. See [hilt.md](../frameworks/hilt.md).

### ViewModel State Driving a Compose Screen

**Use when**: Verifying the UI reacts to ViewModel state.

With the v2 APIs the composition runs on a `StandardTestDispatcher`, so a launched coroutine is queued until the clock advances. Standard calls such as `waitForIdle()` already handle this.

```kotlin
// Bad (v2): the coroutine is queued, state is still Loading
viewModel.loadData()
assertEquals(Success, viewModel.state.value)

// Good: run queued work first
viewModel.loadData()
composeTestRule.waitForIdle()
assertEquals(Success, viewModel.state.value)

// Good: assert on the UI thread after idle
composeTestRule.runOnIdle { assertEquals(Success, viewModel.state.value) }
```

With auto-advance off, `composeTestRule.mainClock.scheduler.runCurrent()` runs queued tasks without advancing virtual time, so intermediate states stay observable.

### Combining runTest with the Compose Clock

**Use when**: A composable uses `LaunchedEffect` with `delay`.

`createComposeRule()` plus `runTest` gives two separate clocks: advancing the `runTest` clock does not advance Compose.

```kotlin
// Bad (NOT RECOMMENDED): separate schedulers
@get:Rule val composeTestRule = createComposeRule()

@Test
fun broken() {
    composeTestRule.setContent { Loader() }
    runTest {
        advanceTimeBy(1000)   // does not advance the compose clock
        composeTestRule.onNodeWithText("Done!").assertIsDisplayed()
    }
}

// Good: runComposeUiTest runs inside its own runTest scope, clocks synchronized
@Test
fun works() = runComposeUiTest {
    setContent { Loader() }
    onNodeWithText("Loading...").assertIsDisplayed()
    mainClock.advanceTimeBy(1000 + 16 /* Frame buffer */)
    onNodeWithText("Done!").assertIsDisplayed()
}
```

`Loader` is the docs' composable: `LaunchedEffect(Unit) { delay(1000); status = "Done!" }`. Without migrating, the scheduler can be shared by passing `composeTestRule.mainClock.scheduler` to `runTest`. Run `runComposeUiTest` tests in `src/test` with `@RunWith(AndroidJUnit4::class)` per the Robolectric blog's statement that the same code runs on the JVM and on a device; Robolectric setup is in [configuration.md](../core/configuration.md).

## Decision Guide

| Situation | Choice |
|---|---|
| Pure logic with coroutines | `runTest` + injected `TestDispatcher` |
| `viewModelScope` in a local JVM test | `MainDispatcherRule` |
| Compose UI with `delay` or `LaunchedEffect` | `runComposeUiTest`, advance `mainClock` |
| Assertion sees "Loading" after v2 migration | `waitForIdle()` or `runOnIdle` |
| Class owns a scope | Inject `CoroutineScope`; pass `TestScope` |
| Test needs a dispatcher as a class property | Reuse `mainDispatcherRule.testDispatcher` |

## Anti-Patterns to Avoid

| Don't | Problem | Do Instead |
|---|---|---|
| `Thread.sleep` / arbitrary pauses | Unnecessarily slow or flaky | Virtual time: `advanceUntilIdle`, `advanceTimeBy` |
| Several schedulers in one test | Time and queues diverge | Share `testScheduler` |
| `createComposeRule()` + `runTest` | Two clocks | `runComposeUiTest` |
| Hardcoded `Dispatchers.IO` in classes | Real threads in tests | Inject the dispatcher |
| Fire-and-forget `initialize()` | Cannot await | Suspend or return `Deferred` |
| `TestDispatcher` property created before `setMain` | Separate scheduler | Build from `mainDispatcherRule.testDispatcher` |
| Asserting immediately after launching on v2 | Coroutine is queued | `waitForIdle()` / `runOnIdle` |
| `Context` inside ViewModels | Hard to test in isolation | Interfaces and DI |

## Common Issues & Solutions

### Test passes under v1 APIs, fails after moving to v2

**Cause**: v1 used `UnconfinedTestDispatcher` and ran launched coroutines immediately, possibly masking races. v2 queues them.
**Fix**: Add `waitForIdle()` or `runOnIdle` before asserting.

### Exception about the Main dispatcher in a local test

**Cause**: No Android UI thread on a plain JVM. **Fix**: `Dispatchers.setMain(testDispatcher)` with `resetMain()`, or `MainDispatcherRule`.

### `runTest` waits a long time then fails

**Cause**: Pending work it cannot finish. `runTest` waits for children even on other dispatchers, up to `dispatchTimeoutMs` (60 s default). **Fix**: Inject test dispatchers so work runs on the test scheduler.

## Related References

- [synchronization.md](../core/synchronization.md) — `waitForIdle`, `waitUntil`, idling
- [clock-control.md](../advanced/clock-control.md) — `MainTestClock`
- [test-doubles.md](../architecture/test-doubles.md) — fakes over mocks
- [hilt.md](../frameworks/hilt.md) — injecting fakes with Hilt
- [state-restoration.md](state-restoration.md) — `SavedStateHandle` and recreation

## Sources

- https://developer.android.com/kotlin/coroutines/test
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/training/testing/fundamentals
- https://developer.android.com/training/testing/fundamentals/test-doubles
- https://developer.android.com/training/testing/instrumented-tests/stability
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/training/dependency-injection/hilt-testing
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
